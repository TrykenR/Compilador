"""
semantico.py — Analizador Semántico.

Recorre el AST producido por el parser sintáctico y verifica:
  1. Variables declaradas antes de usarse.
  2. Variables no declaradas dos veces en el mismo ámbito.
  3. Compatibilidad de tipos en asignaciones y operaciones.
  4. Funciones llamadas con el número correcto de argumentos.
  5. Uso de return dentro de funciones (y tipo de retorno).
  6. Variables declaradas pero nunca usadas (advertencia).
  7. Operaciones con tipos incompatibles (ej: string + int).

Expone una función pública:
    analizar_semantico(arbol, tokens) → (tabla_simbolos, advertencias, errores)
"""

from typing import List, Dict, Tuple, Optional
from sintactico import Nodo


# ─────────────────────────────────────────────
#  TABLA DE SÍMBOLOS
# ─────────────────────────────────────────────

class Simbolo:
    """Entrada en la tabla de símbolos."""
    def __init__(self, nombre: str, tipo: str, categoria: str,
                 linea: int, usado: bool = False, params: list = None):
        self.nombre    = nombre
        self.tipo      = tipo        # 'int', 'float', 'string', 'bool', 'void', '?'
        self.categoria = categoria   # 'variable', 'funcion', 'parametro'
        self.linea     = linea
        self.usado     = usado
        self.params    = params or []  # para funciones: lista de tipos de parámetros

    def __repr__(self):
        return f"Simbolo({self.nombre!r}, {self.tipo}, {self.categoria}, L{self.linea})"


class TablaSimbolos:
    """
    Tabla de símbolos con soporte de ámbitos anidados (scopes).
    Cada ámbito es un diccionario nombre→Simbolo apilado en self.ambitos.
    El ámbito 0 es el global; cada bloque/función añade uno nuevo.
    """

    def __init__(self):
        self.ambitos: List[Dict[str, Simbolo]] = [{}]  # ámbito global
        self.historial: List[Simbolo] = []             # todos los símbolos registrados

    def entrar_ambito(self):
        self.ambitos.append({})

    def salir_ambito(self) -> Dict[str, Simbolo]:
        return self.ambitos.pop() if len(self.ambitos) > 1 else {}

    def declarar(self, simbolo: Simbolo) -> bool:
        """
        Declara un símbolo en el ámbito actual.
        Devuelve False si ya existía en este mismo ámbito (redeclaración).
        """
        ambito_actual = self.ambitos[-1]
        if simbolo.nombre in ambito_actual:
            return False
        ambito_actual[simbolo.nombre] = simbolo
        self.historial.append(simbolo)
        return True

    def buscar(self, nombre: str) -> Optional[Simbolo]:
        """Busca un símbolo de adentro hacia afuera (ámbito más cercano primero)."""
        for ambito in reversed(self.ambitos):
            if nombre in ambito:
                return ambito[nombre]
        return None

    def marcar_usado(self, nombre: str):
        """Marca un símbolo como usado en cualquier ámbito donde se encuentre."""
        for ambito in reversed(self.ambitos):
            if nombre in ambito:
                ambito[nombre].usado = True
                return

    def simbolos_no_usados(self) -> List[Simbolo]:
        """Devuelve variables declaradas pero nunca referenciadas."""
        return [
            s for s in self.historial
            if not s.usado and s.categoria in ('variable', 'parametro')
        ]

    def todos(self) -> List[Simbolo]:
        return list(self.historial)


# ─────────────────────────────────────────────
#  INFERENCIA DE TIPOS
# ─────────────────────────────────────────────

# Reglas de promoción de tipos para operaciones aritméticas.
# Si los operandos son de tipos diferentes, el resultado adopta el más general.
_PROMOCION = {
    ('int',    'float'):  'float',
    ('float',  'int'):    'float',
    ('int',    'int'):    'int',
    ('float',  'float'):  'float',
    ('string', 'string'): 'string',
    ('bool',   'bool'):   'bool',
}

# Operadores que solo tienen sentido entre tipos numéricos
_OP_NUMERICOS = {'+', '-', '*', '/', '%', '<', '>', '<=', '>='}
# Operadores que pueden aplicarse a cualquier tipo comparable
_OP_IGUALDAD  = {'==', '!='}
# Operadores lógicos: operandos deben ser bool o numérico
_OP_LOGICOS   = {'&&', '||'}


def _tipo_compatible(t1: str, t2: str, op: str) -> Tuple[bool, str]:
    """
    Comprueba si la operación `t1 op t2` es válida y devuelve (ok, tipo_resultado).
    '?' significa tipo desconocido (error previo); se acepta para no encadenar errores.
    """
    if '?' in (t1, t2):
        return True, '?'

    if op in _OP_NUMERICOS:
        if t1 in ('int', 'float') and t2 in ('int', 'float'):
            return True, _PROMOCION.get((t1, t2), 'float')
        # Permitir concatenación de string con +
        if op == '+' and t1 == 'string' and t2 == 'string':
            return True, 'string'
        return False, '?'

    if op in _OP_IGUALDAD:
        return True, 'bool'

    if op in _OP_LOGICOS:
        return True, 'bool'

    return True, '?'


# ─────────────────────────────────────────────
#  ANALIZADOR SEMÁNTICO
# ─────────────────────────────────────────────

class AnalizadorSemantico:
    """
    Recorre el AST en profundidad y verifica las reglas semánticas.
    Usa la tabla de símbolos para rastrear declaraciones y usos.
    """

    def __init__(self):
        self.tabla    = TablaSimbolos()
        self.errores:      List[str] = []
        self.advertencias: List[str] = []
        # Pila de tipos de retorno esperados (una por cada función anidada)
        self._retorno_esperado: List[str] = []
        # Conjunto de funciones conocidas con sus aridades (nombre → n_params)
        self._funciones: Dict[str, int] = {}
        # Funciones built-in que siempre existen
        self._builtins = {
            'printf': -1,   # -1 = variádica (cualquier n de args)
            'scanf':  -1,
            'dividir': 2,
            'malloc': 1,
            'free':   1,
            'strlen': 1,
            'strcpy': 2,
        }

    # ── Helpers de error ──────────────────────────────────────────────────────

    def _error(self, msg: str, linea: int = 0):
        prefijo = f"línea {linea}: " if linea else ""
        self.errores.append(f"⚠  Error semántico en {prefijo}{msg}")

    def _advertencia(self, msg: str, linea: int = 0):
        prefijo = f"línea {linea}: " if linea else ""
        self.advertencias.append(f"ℹ  Advertencia en {prefijo}{msg}")

    # ── Extracción de tipo desde etiqueta de nodo ─────────────────────────────

    def _tipo_de_decl(self, etiqueta: str) -> str:
        """Extrae el tipo de una etiqueta como 'decl int' → 'int'."""
        for t in ('int', 'float', 'string', 'bool', 'void', 'char', 'double', 'long'):
            if etiqueta.startswith(f'decl {t}') or etiqueta.startswith(f'func {t}') \
               or etiqueta.startswith(f'proto {t}'):
                return t
        return '?'

    def _nombre_de_func(self, etiqueta: str) -> str:
        """Extrae el nombre de 'func int main' → 'main'."""
        partes = etiqueta.split()
        return partes[2] if len(partes) >= 3 else '?'

    # ── Recorrido principal ───────────────────────────────────────────────────

    def analizar(self, raiz: Nodo):
        """Punto de entrada: recorre el AST completo."""
        self._visitar(raiz)
        # Advertencias por variables no usadas (al final, cuando el scope global cierra)
        for s in self.tabla.simbolos_no_usados():
            self._advertencia(
                f"'{s.nombre}' declarado como {s.tipo} pero nunca usado", s.linea)
        return self.tabla, self.advertencias, self.errores

    def _visitar(self, nodo: Nodo) -> str:
        """
        Visita un nodo y devuelve su tipo inferido.
        Despacha al método específico según la etiqueta del nodo.
        """
        if nodo is None:
            return '?'
        etq = nodo.etiqueta

        # ── Programa / bloque ─────────────────────────────────────────────────
        if etq == 'programa':
            for hijo in nodo.hijos:
                self._visitar(hijo)
            return 'void'

        if etq == 'bloque':
            self.tabla.entrar_ambito()
            for hijo in nodo.hijos:
                self._visitar(hijo)
            ambito_saliente = self.tabla.salir_ambito()
            # Advertencias por no usados en este ámbito
            for s in ambito_saliente.values():
                if not s.usado and s.categoria in ('variable', 'parametro'):
                    self._advertencia(
                        f"'{s.nombre}' ({s.tipo}) declarado pero nunca usado", s.linea)
            return 'void'

        # ── Declaración de variable: "decl int", "decl float", etc. ──────────
        if etq.startswith('decl ') and not etq.startswith('decl ') or \
           any(etq == f'decl {t}' for t in
               ('int','float','string','bool','void','char','double','long')):
            return self._visitar_decl_var(nodo)

        # ── Declaración de función / prototipo ────────────────────────────────
        if etq.startswith('func '):
            return self._visitar_func(nodo)
        if etq.startswith('proto '):
            return self._visitar_proto(nodo)

        # ── Asignación ────────────────────────────────────────────────────────
        if etq.startswith('asig '):
            return self._visitar_asig(nodo)

        # ── Llamada a función ─────────────────────────────────────────────────
        if etq.startswith('llamada '):
            return self._visitar_llamada(nodo)
        if etq.endswith('(...)'):
            return self._visitar_llamada_expr(nodo)

        # ── Operadores binarios ───────────────────────────────────────────────
        if etq in ('+', '-', '*', '/', '%', '<', '>', '<=', '>=', '==', '!=', '&&', '||'):
            return self._visitar_binario(nodo)

        # ── Operadores unarios ────────────────────────────────────────────────
        if etq.startswith('unario ') or etq == 'neg':
            t = self._visitar(nodo.hijos[0]) if nodo.hijos else '?'
            return t

        # ── Post/pre incremento ───────────────────────────────────────────────
        if etq.startswith('post') or etq.startswith('pre'):
            return self._visitar(nodo.hijos[0]) if nodo.hijos else '?'

        # ── Control de flujo ─────────────────────────────────────────────────
        if etq == 'if':
            return self._visitar_if(nodo)
        if etq == 'while':
            return self._visitar_while(nodo)
        if etq == 'for':
            return self._visitar_for(nodo)
        if etq == 'do-while':
            return self._visitar_do_while(nodo)
        if etq == 'switch':
            self._visitar_hijos(nodo)
            return 'void'

        # ── Return ────────────────────────────────────────────────────────────
        if etq == 'return':
            return self._visitar_return(nodo)

        # ── Identificador (uso de variable) ───────────────────────────────────
        # Un nodo hoja cuya etiqueta no encaja en ningún patrón es un identificador
        if not nodo.hijos and etq not in ('ε', 'condición', 'else',
                                           'init', 'cond', 'inc', 'break', 'continue'):
            return self._visitar_identificador_o_literal(nodo)

        # ── Nodos contenedor (condición, else, init, cond, inc…) ─────────────
        self._visitar_hijos(nodo)
        return '?'

    def _visitar_hijos(self, nodo: Nodo):
        for hijo in nodo.hijos:
            self._visitar(hijo)

    # ── Visitores específicos ─────────────────────────────────────────────────

    def _visitar_decl_var(self, nodo: Nodo) -> str:
        tipo = self._tipo_de_decl(nodo.etiqueta)
        nombre_registrado = False

        for hijo in nodo.hijos:
            # El PRIMER hijo sin hijos propios es el nombre de la variable
            if not nombre_registrado and not hijo.hijos \
                    and not hijo.etiqueta.startswith('decl'):
                nombre = hijo.etiqueta
                # Verificar que sea un identificador real, no un literal
                es_literal = False
                try:
                    float(nombre)
                    es_literal = True
                except ValueError:
                    pass
                if nombre.startswith('"') or nombre.startswith("'"):
                    es_literal = True
                if nombre in ('true','false','True','False','null','None','nil'):
                    es_literal = True

                if not es_literal:
                    sim = Simbolo(nombre, tipo, 'variable', nodo.linea)
                    if not self.tabla.declarar(sim):
                        self._error(
                            f"'{nombre}' ya fue declarado en este ámbito", nodo.linea)
                    nombre_registrado = True
                else:
                    # Es un literal usado como inicializador directo
                    self._visitar(hijo)
            else:
                # Todo lo demás es el inicializador
                t_init = self._visitar(hijo)
                if hijo.etiqueta.startswith('decl'):
                    continue
                if t_init != '?' and tipo != '?' and t_init != tipo:
                    if not (tipo == 'float' and t_init == 'int'):
                        self._advertencia(
                            f"inicializador de tipo '{t_init}' asignado a '{tipo}'",
                            nodo.linea)
        return tipo

    def _visitar_func(self, nodo: Nodo) -> str:
        tipo_ret = self._tipo_de_decl(nodo.etiqueta)
        nombre   = self._nombre_de_func(nodo.etiqueta)

        # Registrar la función en el ámbito global
        params_nodos = [h for h in nodo.hijos if not h.etiqueta == 'bloque'
                        and h.etiqueta != 'ε']
        n_params = len([h for h in nodo.hijos if h.etiqueta != 'bloque'
                        and not h.etiqueta.startswith('decl')])
        sim = Simbolo(nombre, tipo_ret, 'funcion', nodo.linea,
                      usado=True, params=[])
        self.tabla.declarar(sim)
        self._funciones[nombre] = len(params_nodos)

        # Nuevo ámbito para el cuerpo de la función
        self.tabla.entrar_ambito()
        self._retorno_esperado.append(tipo_ret)

        # Registrar parámetros
        for param in nodo.hijos:
            if param.etiqueta == 'bloque':
                break
            partes = param.etiqueta.split()
            if len(partes) == 2:
                p_tipo, p_nombre = partes
                self.tabla.declarar(
                    Simbolo(p_nombre, p_tipo, 'parametro', param.linea, usado=False))

        # Visitar el bloque del cuerpo
        for hijo in nodo.hijos:
            if hijo.etiqueta == 'bloque':
                # Visitar directamente los hijos del bloque sin crear otro ámbito
                for s in hijo.hijos:
                    self._visitar(s)
                break

        self._retorno_esperado.pop()
        ambito = self.tabla.salir_ambito()
        for s in ambito.values():
            if not s.usado and s.categoria == 'parametro':
                self._advertencia(
                    f"parámetro '{s.nombre}' de '{nombre}' nunca usado", s.linea)
        return tipo_ret

    def _visitar_proto(self, nodo: Nodo) -> str:
        tipo_ret = self._tipo_de_decl(nodo.etiqueta)
        nombre   = self._nombre_de_func(nodo.etiqueta)
        sim = Simbolo(nombre, tipo_ret, 'funcion', nodo.linea, usado=True)
        self.tabla.declarar(sim)
        self._funciones[nombre] = len(nodo.hijos)
        return tipo_ret

    def _visitar_asig(self, nodo: Nodo) -> str:
        if len(nodo.hijos) < 2:
            return '?'
        izq = nodo.hijos[0]
        der = nodo.hijos[1]

        # Marcar la variable del lado izquierdo como usada
        nombre_var = izq.etiqueta
        sim = self.tabla.buscar(nombre_var)
        if sim is None:
            self._error(f"'{nombre_var}' usado sin declarar", nodo.linea)
            t_izq = '?'
        else:
            self.tabla.marcar_usado(nombre_var)
            t_izq = sim.tipo

        t_der = self._visitar(der)

        # Verificar compatibilidad de tipos en la asignación
        if t_izq != '?' and t_der != '?' and t_izq != t_der:
            if not (t_izq == 'float' and t_der == 'int'):
                self._advertencia(
                    f"asignación de '{t_der}' a variable de tipo '{t_izq}' "
                    f"('{nombre_var}')", nodo.linea)
        return t_izq

    def _visitar_llamada(self, nodo: Nodo) -> str:
        nombre = nodo.etiqueta.replace('llamada ', '')
        return self._verificar_llamada(nombre, nodo.hijos, nodo.linea)

    def _visitar_llamada_expr(self, nodo: Nodo) -> str:
        nombre = nodo.etiqueta.replace('(...)', '')
        return self._verificar_llamada(nombre, nodo.hijos, nodo.linea)

    def _verificar_llamada(self, nombre: str, args: list, linea: int) -> str:
        # Visitar los argumentos primero
        for arg in args:
            self._visitar(arg)

        # Funciones built-in
        if nombre in self._builtins:
            esperados = self._builtins[nombre]
            if esperados != -1 and len(args) != esperados:
                self._error(
                    f"'{nombre}' espera {esperados} argumento(s), "
                    f"se pasaron {len(args)}", linea)
            return '?'

        # Buscar en tabla de símbolos
        sim = self.tabla.buscar(nombre)
        if sim is None:
            self._error(f"función '{nombre}' no declarada", linea)
            return '?'

        self.tabla.marcar_usado(nombre)

        # Verificar aridad
        if nombre in self._funciones:
            esperados = self._funciones[nombre]
            if len(args) != esperados:
                self._error(
                    f"'{nombre}' espera {esperados} argumento(s), "
                    f"se pasaron {len(args)}", linea)

        return sim.tipo

    def _visitar_binario(self, nodo: Nodo) -> str:
        t1 = self._visitar(nodo.hijos[0]) if len(nodo.hijos) > 0 else '?'
        t2 = self._visitar(nodo.hijos[1]) if len(nodo.hijos) > 1 else '?'
        ok, t_res = _tipo_compatible(t1, t2, nodo.etiqueta)
        if not ok:
            self._error(
                f"operación '{nodo.etiqueta}' entre tipos incompatibles "
                f"'{t1}' y '{t2}'", nodo.linea)
        return t_res

    def _visitar_if(self, nodo: Nodo) -> str:
        for hijo in nodo.hijos:
            if hijo.etiqueta == 'condición':
                t_cond = self._visitar(hijo.hijos[0]) if hijo.hijos else '?'
                if t_cond not in ('bool', 'int', '?'):
                    self._advertencia(
                        f"condición de 'if' es de tipo '{t_cond}', "
                        f"se esperaba bool o int", nodo.linea)
            elif hijo.etiqueta == 'else':
                self._visitar(hijo.hijos[0]) if hijo.hijos else None
            else:
                self._visitar(hijo)
        return 'void'

    def _visitar_while(self, nodo: Nodo) -> str:
        for hijo in nodo.hijos:
            if hijo.etiqueta == 'condición':
                t_cond = self._visitar(hijo.hijos[0]) if hijo.hijos else '?'
                if t_cond not in ('bool', 'int', '?'):
                    self._advertencia(
                        f"condición de 'while' es de tipo '{t_cond}'", nodo.linea)
            else:
                self._visitar(hijo)
        return 'void'

    def _visitar_for(self, nodo: Nodo) -> str:
        self.tabla.entrar_ambito()
        for hijo in nodo.hijos:
            self._visitar(hijo)
        ambito = self.tabla.salir_ambito()
        for s in ambito.values():
            if not s.usado and s.categoria == 'variable':
                self._advertencia(
                    f"'{s.nombre}' declarado en 'for' pero nunca usado", s.linea)
        return 'void'

    def _visitar_do_while(self, nodo: Nodo) -> str:
        self._visitar_hijos(nodo)
        return 'void'

    def _visitar_return(self, nodo: Nodo) -> str:
        t_val = self._visitar(nodo.hijos[0]) if nodo.hijos else 'void'
        if self._retorno_esperado:
            esperado = self._retorno_esperado[-1]
            if esperado == 'void' and t_val != 'void' and t_val != '?':
                self._advertencia(
                    f"función void devuelve un valor de tipo '{t_val}'", nodo.linea)
            elif esperado != 'void' and t_val == 'void':
                self._advertencia(
                    f"función '{esperado}' retorna sin valor", nodo.linea)
            elif t_val != '?' and esperado != '?' and t_val != esperado:
                if not (esperado == 'float' and t_val == 'int'):
                    self._advertencia(
                        f"return de tipo '{t_val}' en función de tipo '{esperado}'",
                        nodo.linea)
        return t_val

    def _visitar_identificador_o_literal(self, nodo: Nodo) -> str:
        etq = nodo.etiqueta

        # Literales numéricos
        try:
            int(etq)
            return 'int'
        except ValueError:
            pass
        try:
            float(etq)
            return 'float'
        except ValueError:
            pass

        # Literales de cadena
        if etq.startswith('"') or etq.startswith("'"):
            return 'string'

        # Literales booleanos
        if etq in ('true', 'false', 'True', 'False'):
            return 'bool'

        # Literales nulos
        if etq in ('null', 'None', 'nil'):
            return '?'

        # Identificador: buscar en tabla
        sim = self.tabla.buscar(etq)
        if sim is not None:
            self.tabla.marcar_usado(etq)
            return sim.tipo
        else:
            # Solo reportar error si parece un identificador real (no ε u otros)
            if etq not in ('ε', '', 'condición', 'else', 'init', 'cond', 'inc',
                           'break', 'continue', 'case', 'default', 'expr-sw',
                           'ternario', 'índice') and etq[0].isalpha():
                self._error(f"'{etq}' usado sin declarar", nodo.linea)
            return '?'


# ─────────────────────────────────────────────
#  FUNCIÓN PÚBLICA
# ─────────────────────────────────────────────

def analizar_semantico(
    arbol: Nodo,
) -> Tuple['TablaSimbolos', List[str], List[str]]:
    """
    Interfaz pública del módulo semántico.

    Recibe el nodo raíz del AST y devuelve:
        tabla       — TablaSimbolos con todos los símbolos registrados
        advertencias — lista de mensajes de advertencia
        errores      — lista de mensajes de error semántico
    """
    analizador = AnalizadorSemantico()
    return analizador.analizar(arbol)
