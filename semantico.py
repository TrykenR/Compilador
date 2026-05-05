"""semantico.py — Analizador Semántico corregido (parámetros de funciones)"""

from typing import List, Dict, Tuple, Optional
from sintactico import Nodo


# ─────────────────────────────────────────────
#  TABLA DE SÍMBOLOS
# ─────────────────────────────────────────────

class Simbolo:
    def __init__(self, nombre: str, tipo: str, categoria: str,
                 linea: int, usado: bool = False):
        self.nombre    = nombre
        self.tipo      = tipo
        self.categoria = categoria
        self.linea     = linea
        self.usado     = usado

    def __repr__(self):
        return f"Simbolo({self.nombre!r}, {self.tipo}, {self.categoria}, L{self.linea})"


class TablaSimbolos:
    def __init__(self):
        self.ambitos: List[Dict[str, Simbolo]] = [{}]
        self.historial: List[Simbolo] = []

    def entrar_ambito(self):
        self.ambitos.append({})

    def salir_ambito(self):
        return self.ambitos.pop() if len(self.ambitos) > 1 else {}

    def declarar(self, simbolo: Simbolo) -> bool:
        ambito_actual = self.ambitos[-1]
        if simbolo.nombre in ambito_actual:
            return False
        ambito_actual[simbolo.nombre] = simbolo
        self.historial.append(simbolo)
        return True

    def buscar(self, nombre: str) -> Optional[Simbolo]:
        for ambito in reversed(self.ambitos):
            if nombre in ambito:
                return ambito[nombre]
        return None

    def marcar_usado(self, nombre: str):
        for ambito in reversed(self.ambitos):
            if nombre in ambito:
                ambito[nombre].usado = True
                return

    def simbolos_no_usados(self) -> List[Simbolo]:
        return [s for s in self.historial if not s.usado and s.categoria == 'variable']

    def todos(self) -> List[Simbolo]:
        return list(self.historial)


# ─────────────────────────────────────────────
#  BUILT-INS
# ─────────────────────────────────────────────

_BUILTINS = {
    'print', 'range', 'len', 'int', 'float', 'str', 'list', 'dict', 'set', 'tuple',
    'type', 'input', 'sum', 'min', 'max', 'abs', 'sorted', 'zip', 'enumerate',
    'map', 'filter', 'any', 'all', 'open', 'dividir', 'main', '__name__', '__main__'
}


# ─────────────────────────────────────────────
#  INFERENCIA SIMPLE DE TIPOS
# ─────────────────────────────────────────────

def _inferir_tipo(valor: str) -> str:
    if valor.isdigit():
        return 'int'
    if valor.replace('.', '', 1).replace('-', '', 1).isdigit():
        return 'float'
    if valor.startswith(('"', "'")):
        return 'str'
    if valor in ('True', 'False'):
        return 'bool'
    return '?'


# ─────────────────────────────────────────────
#  ANALIZADOR SEMÁNTICO
# ─────────────────────────────────────────────

class AnalizadorSemantico:
    def __init__(self):
        self.tabla = TablaSimbolos()
        self.errores: List[str] = []
        self.advertencias: List[str] = []

    def _error(self, msg: str, linea: int = 0):
        prefijo = f"línea {linea}: " if linea else ""
        self.errores.append(f"⚠  Error semántico en {prefijo}{msg}")

    def _advertencia(self, msg: str, linea: int = 0):
        prefijo = f"línea {linea}: " if linea else ""
        self.advertencias.append(f"ℹ  Advertencia en {prefijo}{msg}")

    def analizar(self, raiz: Nodo):
        self._visitar(raiz)
        for s in self.tabla.simbolos_no_usados():
            self._advertencia(f"'{s.nombre}' declarado pero nunca usado", s.linea)
        return self.tabla, self.advertencias, self.errores

    def _visitar(self, nodo: Nodo) -> str:
        if not nodo or nodo.etiqueta == 'ε':
            return '?'

        etq = nodo.etiqueta.strip()

        if etq in ('init', 'iterable', 'condición', 'inc', 'cond', 'else', 'elif'):
            self._visitar_hijos(nodo)
            return '?'

        # ==================== FUNCIÓN def ====================
        if etq.startswith(('func ', 'def')):
            return self._visitar_func(nodo)

        # ==================== ASIGNACIÓN ====================
        if etq.startswith('asig ') or '=' in etq:
            if nodo.hijos:
                izq = nodo.hijos[0]
                if isinstance(izq, Nodo) and not izq.hijos and izq.etiqueta[0].isalpha():
                    nombre = izq.etiqueta
                    if nombre not in _BUILTINS:
                        tipo = _inferir_tipo(nodo.hijos[1].etiqueta) if len(nodo.hijos) > 1 else '?'
                        self.tabla.declarar(Simbolo(nombre, tipo, 'variable', nodo.linea))
                        self.tabla.marcar_usado(nombre)
            self._visitar_hijos(nodo)
            return '?'

        # ==================== FOR ====================
        if etq.startswith('for'):
            for hijo in nodo.hijos:
                if hijo.etiqueta == 'init' and hijo.hijos:
                    var = hijo.hijos[0]
                    if var and not var.hijos and var.etiqueta[0].isalpha():
                        nombre = var.etiqueta
                        if nombre not in _BUILTINS:
                            self.tabla.declarar(Simbolo(nombre, 'int', 'variable', nodo.linea))
                            self.tabla.marcar_usado(nombre)
            self._visitar_hijos(nodo)
            return '?'

        # ==================== LLAMADA ====================
        if etq.startswith('llamada ') or etq.endswith('(...)'):
            nombre = etq.replace('llamada ', '').replace('(...)', '')
            if nombre not in _BUILTINS and not self.tabla.buscar(nombre):
                self._error(f"función '{nombre}' no declarada", nodo.linea)
            self._visitar_hijos(nodo)
            return '?'

        # ==================== IDENTIFICADOR ====================
        if not nodo.hijos and etq and etq[0].isalpha():
            nombre = etq
            if nombre not in _BUILTINS and not self.tabla.buscar(nombre):
                if nombre not in {'def', 'if', 'else', 'elif', 'for', 'in', 'while', 'return', 'and', 'or', 'not', 'pass'}:
                    self._error(f"'{nombre}' usado sin declarar", nodo.linea)
            else:
                self.tabla.marcar_usado(nombre)
            return '?'

        self._visitar_hijos(nodo)
        return '?'

    def _visitar_func(self, nodo: Nodo):
        # Extraer nombre de la función
        nombre = nodo.etiqueta.split()[-1] if ' ' in nodo.etiqueta else nodo.etiqueta
        self.tabla.declarar(Simbolo(nombre, 'function', 'funcion', nodo.linea, usado=True))

        self.tabla.entrar_ambito()

        # === REGISTRAR PARÁMETROS (¡ESTA ES LA CORRECCIÓN PRINCIPAL!) ===
        for hijo in nodo.hijos:
            if hijo.etiqueta != 'bloque':          # todo antes del cuerpo es parámetro
                param_name = hijo.etiqueta
                if param_name and param_name[0].isalpha():
                    self.tabla.declarar(Simbolo(param_name, '?', 'parametro', nodo.linea))

        # Visitar el cuerpo de la función
        self._visitar_hijos(nodo)

        self.tabla.salir_ambito()
        return 'function'

    def _visitar_hijos(self, nodo: Nodo):
        for hijo in nodo.hijos:
            self._visitar(hijo)


# ─────────────────────────────────────────────
#  FUNCIÓN PÚBLICA
# ─────────────────────────────────────────────

def analizar_semantico(arbol: Nodo) -> Tuple['TablaSimbolos', List[str], List[str]]:
    analizador = AnalizadorSemantico()
    return analizador.analizar(arbol)
