"""
sintactico.py — Analizador Sintáctico por descenso recursivo.

Toma la lista de tokens producida por el analizador léxico y construye
un AST (Árbol de Sintaxis Abstracta) que representa la estructura
jerárquica del programa.

La técnica usada es descenso recursivo predictivo: cada construcción
gramatical (expresión, sentencia, bloque…) tiene su propio método en
el Parser. Cada método mira el token actual con peek() y decide qué
rama de la gramática aplicar sin necesidad de retroceder.

Gramática soportada:
  programa     → sentencia*
  sentencia    → declaracion | asignacion | if_stmt | while_stmt
               | for_stmt | do_while_stmt | switch_stmt
               | return_stmt | break_stmt | continue_stmt
               | bloque | llamada ';' | expr ';'
  declaracion  → tipo IDENTIFICADOR ('=' expr)? ';'
               | tipo IDENTIFICADOR '(' params ')' bloque      ← función
  asignacion   → IDENTIFICADOR op_asig expr ';'
               | IDENTIFICADOR '++' ';'
               | IDENTIFICADOR '--' ';'
  if_stmt      → 'if' '(' expr ')' bloque_o_sent ('else' bloque_o_sent)?
  while_stmt   → 'while' '(' expr ')' bloque_o_sent
  do_while     → 'do' bloque 'while' '(' expr ')' ';'
  for_stmt     → 'for' '(' (decl_for | asig_for | ';') expr? ';' expr? ')' bloque_o_sent
  switch_stmt  → 'switch' '(' expr ')' '{' case* default? '}'
  return_stmt  → 'return' expr? ';'
  bloque       → '{' sentencia* '}'
  expr         → asignacion_expr | logico_o
  logico_o     → logico_y ('||' logico_y)*
  logico_y     → igualdad ('&&' igualdad)*
  igualdad     → comparacion (('=='|'!=') comparacion)*
  comparacion  → suma (('<'|'>'|'<='|'>=') suma)*
  suma         → termino (('+'|'-') termino)*
  termino      → factor (('*'|'/'|'%') factor)*
  unario       → ('!'|'-'|'+'|'++'|'--') factor | postfijo
  factor       → NÚMERO | CADENA | BOOL | NULO
               | IDENTIFICADOR ('(' args ')')? ('[' expr ']')*
               | '(' expr ')'
"""

from typing import List, Optional, Tuple

# TIPOS_PRIMITIVOS: conjunto de palabras clave que inician una declaración
# (int, float, void…). Se importa desde tipos_token para mantener una
# única fuente de verdad compartida con el léxico.
from tipos_token import Token, TIPOS_PRIMITIVOS


# ─────────────────────────────────────────────
#  NODO DEL ÁRBOL SINTÁCTICO
# ─────────────────────────────────────────────

class Nodo:
    """
    Nodo del AST (Árbol de Sintaxis Abstracta).

    Cada nodo representa una construcción del lenguaje: un programa,
    una función, una sentencia if, una expresión aritmética, un literal…

    Atributos:
        etiqueta — nombre descriptivo del nodo, ej: 'if', 'func int main',
                   'asig =', '+', '42', 'resultado'.
        hijos    — lista de Nodo hijos que forman la subestructura.
                   Un nodo hoja (literal, identificador) tiene hijos = [].
        linea    — línea del fuente donde aparece esta construcción,
                   útil para mensajes de error y para la interfaz gráfica.
    """

    def __init__(self, etiqueta: str, hijos: list = None, linea: int = 0):
        self.etiqueta = etiqueta
        # Se evita usar [] como valor por defecto en la firma porque en Python
        # los valores mutables por defecto se comparten entre todas las llamadas.
        self.hijos    = hijos if hijos is not None else []
        self.linea    = linea

    def __repr__(self):
        """Representación compacta para depuración en el REPL."""
        return f"Nodo({self.etiqueta!r}, hijos={len(self.hijos)})"

    def __str__(self):
        """Árbol completo en texto indentado, útil para volcados en consola."""
        return self._str_indent(0)

    def _str_indent(self, nivel: int) -> str:
        """
        Construye recursivamente la representación en árbol indentado.
        Cada nivel añade dos espacios de sangría para mostrar la jerarquía.
        Ejemplo para 'int x = 5;':
            decl int
              x
              5
        """
        indent    = "  " * nivel
        resultado = f"{indent}{self.etiqueta}"
        for hijo in self.hijos:
            resultado += "\n" + hijo._str_indent(nivel + 1)
        return resultado


# ─────────────────────────────────────────────
#  PARSER
# ─────────────────────────────────────────────

# Conjunto de valores de token que se usan como puntos de sincronización
# durante la recuperación de errores. Cuando el parser encuentra un error,
# avanza hasta el siguiente token de este conjunto para retomar el análisis
# en un estado conocido y seguir reportando más errores en lugar de abortar.
_SYNC_TOKENS = {'}', ';', 'if', 'while', 'for', 'return', 'int', 'float',
                'string', 'bool', 'void', 'else', 'do', 'switch'}


class Parser:
    """
    Analizador sintáctico por descenso recursivo.

    Mantiene un cursor (pos) sobre la lista de tokens y avanza a medida
    que va reconociendo construcciones gramaticales. Si encuentra algo
    inesperado, registra el error y aplica recuperación de pánico para
    continuar analizando el resto del código.
    """

    def __init__(self, tokens: List[Token]):
        self.tokens  = tokens
        self.pos     = 0                  # índice del token actual
        self.errores: List[str] = []
        self._panic_mode = False          # reservado para recuperación futura

    # ══════════════════════════════════════════
    #  UTILIDADES BÁSICAS
    # ══════════════════════════════════════════

    def peek(self, offset: int = 0) -> Optional[Token]:
        """
        Devuelve el token en la posición actual + offset SIN consumirlo.
        Permite mirar uno o dos tokens adelante para decidir qué regla aplicar.
        Devuelve None si el offset apunta más allá del final de la lista.
        """
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else None

    def consume(self) -> Optional[Token]:
        """
        Devuelve el token actual y avanza el cursor al siguiente.
        Es la única forma de "leer" un token del flujo.
        Devuelve None si ya no quedan tokens.
        """
        tok = self.peek()
        if tok:
            self.pos += 1
        return tok

    def hay_mas(self) -> bool:
        """True si el cursor aún apunta a un token válido."""
        return self.pos < len(self.tokens)

    def esperar(self, tipo: str, valor: str = None) -> Optional[Token]:
        """
        Versión estricta de consume(): consume el token si coincide con el
        tipo (y valor, si se especifica), o registra un error de sintaxis
        y devuelve None sin consumir nada.

        Se usa cuando ese token es OBLIGATORIO para que la construcción
        sea sintácticamente correcta, ej: esperar el ')' después de la
        condición de un if.
        """
        tok = self.peek()
        if tok and tok.tipo == tipo and (valor is None or tok.valor == valor):
            return self.consume()
        # Construir mensaje de error descriptivo con ubicación exacta
        ubicacion  = f"línea {tok.linea}, col {tok.columna}" if tok else "fin de archivo"
        esperado   = f"'{valor}'" if valor else tipo
        encontrado = f"'{tok.valor}' ({tok.tipo})" if tok else "EOF"
        self.errores.append(
            f"Error sintáctico en {ubicacion}: "
            f"se esperaba {esperado}, se encontró {encontrado}"
        )
        return None

    def coincidir(self, tipo: str, valor: str = None) -> bool:
        """
        Versión permisiva de consume(): consume el token si coincide
        y devuelve True, o devuelve False sin consumir ni registrar error.

        Se usa para tokens OPCIONALES, ej: el ';' al final de algunas
        construcciones donde es válido tanto incluirlo como omitirlo.
        """
        tok = self.peek()
        if tok and tok.tipo == tipo and (valor is None or tok.valor == valor):
            self.consume()
            return True
        return False

    def val_es(self, *valores) -> bool:
        """
        True si el token actual tiene alguno de los valores indicados.
        No consume el token. Útil para decisiones de tipo 'switch' sobre
        el texto del token sin importar su categoría.
        Ejemplo: self.val_es('+', '-') para detectar operadores de suma.
        """
        tok = self.peek()
        return tok is not None and tok.valor in valores

    def tipo_es(self, *tipos) -> bool:
        """
        True si el token actual pertenece a alguno de los tipos indicados.
        No consume el token. Útil cuando importa la categoría léxica
        pero no el valor concreto.
        Ejemplo: self.tipo_es('IDENTIFICADOR', 'LITERAL_NUM')
        """
        tok = self.peek()
        return tok is not None and tok.tipo in tipos

    def es_tipo_primitivo(self) -> bool:
        """
        True si el token actual es una palabra clave que puede iniciar
        una declaración de variable o función (int, float, void, etc.).
        Consulta TIPOS_PRIMITIVOS de tipos_token.py para no duplicar la lista.
        """
        tok = self.peek()
        return tok is not None and tok.tipo == 'PALABRA_CLAVE' and tok.valor in TIPOS_PRIMITIVOS

    def _sincronizar(self):
        """
        Recuperación de pánico: avanza el cursor descartando tokens hasta
        encontrar uno que pertenezca a _SYNC_TOKENS (puntos de sincronización).

        Se llama después de registrar un error para que el parser pueda
        retomar el análisis en un estado gramaticalmente conocido y
        seguir reportando más errores en lugar de detenerse en el primero.
        """
        while self.hay_mas():
            tok = self.peek()
            if tok.valor in _SYNC_TOKENS or (
                tok.tipo == 'DELIMITADOR' and tok.valor in ('{', '}', ';')
            ):
                break
            self.consume()

    # ══════════════════════════════════════════
    #  EXPRESIONES
    # ══════════════════════════════════════════
    #
    # Las expresiones se parsean siguiendo la jerarquía de precedencia
    # de operadores de menor a mayor. Cada método llama al siguiente nivel
    # para parsear su operando, luego revisa si hay operadores de su nivel
    # y construye el nodo binario correspondiente.
    #
    # Jerarquía (de menor a mayor precedencia):
    #   expr → logico_o → logico_y → igualdad → comparacion
    #        → suma → termino → unario → postfijo → factor
    #
    # Esta estructura garantiza que, por ejemplo, '*' agrupe más fuerte
    # que '+', y '+' más fuerte que '=='.

    def expr(self) -> Nodo:
        """
        Nivel raíz de expresión. Maneja:
          - Asignación inline con cualquier operador (=, +=, -=…),
            con asociatividad derecha: a = b = 5 → a = (b = 5).
          - Operador ternario: condicion ? si_verdadero : si_falso.
          - Todo lo demás se delega a logico_o().
        """
        izq = self.logico_o()

        # Asignación inline (en contexto de expresión, ej: dentro de f(x = 5))
        if self.peek() and self.peek().tipo == 'OPERADOR_ASIG':
            op  = self.consume()
            der = self.expr()   # llamada recursiva = asociatividad derecha
            return Nodo(f"asig {op.valor}", [izq, der], op.linea)

        # Operador ternario: cond ? entonces : sino
        if self.val_es('?'):
            self.consume()
            entonces = self.expr()
            # coincidir primero para no duplicar el error si ya está consumido
            self.esperar('DELIMITADOR', ':') if not self.coincidir('DELIMITADOR', ':') else None
            sino = self.expr()
            return Nodo('ternario', [izq, entonces, sino], izq.linea)

        return izq

    def logico_o(self) -> Nodo:
        """
        Operador || (OR lógico). Asociatividad izquierda.
        Ejemplo: a || b || c → (a || b) || c
        """
        izq = self.logico_y()
        while self.val_es('||'):
            op  = self.consume()
            der = self.logico_y()
            izq = Nodo('||', [izq, der], op.linea)   # el nuevo nodo pasa a ser el izq
        return izq

    def logico_y(self) -> Nodo:
        """
        Operador && (AND lógico). Asociatividad izquierda.
        Tiene mayor precedencia que ||: a || b && c → a || (b && c)
        porque && se resuelve primero en su propio nivel.
        """
        izq = self.igualdad()
        while self.val_es('&&'):
            op  = self.consume()
            der = self.igualdad()
            izq = Nodo('&&', [izq, der], op.linea)
        return izq

    def igualdad(self) -> Nodo:
        """
        Operadores == y != (comparación de igualdad). Asociatividad izquierda.
        Se separan de comparacion() para que tengan menor precedencia que < > <= >=.
        """
        izq = self.comparacion()
        while self.val_es('==', '!='):
            op  = self.consume()
            der = self.comparacion()
            izq = Nodo(op.valor, [izq, der], op.linea)
        return izq

    def comparacion(self) -> Nodo:
        """
        Operadores relacionales < > <= >= (orden). Asociatividad izquierda.
        Mayor precedencia que == y !=.
        """
        izq = self.suma()
        while self.val_es('<', '>', '<=', '>='):
            op  = self.consume()
            der = self.suma()
            izq = Nodo(op.valor, [izq, der], op.linea)
        return izq

    def suma(self) -> Nodo:
        """
        Operadores + y - (adición/sustracción). Asociatividad izquierda.
        Mayor precedencia que los relacionales.
        """
        izq = self.termino()
        while self.val_es('+', '-'):
            op  = self.consume()
            der = self.termino()
            izq = Nodo(op.valor, [izq, der], op.linea)
        return izq

    def termino(self) -> Nodo:
        """
        Operadores * / % (multiplicación/división/módulo). Asociatividad izquierda.
        Mayor precedencia que + y -: 2 + 3 * 4 → 2 + (3 * 4).
        """
        izq = self.unario()
        while self.val_es('*', '/', '%'):
            op  = self.consume()
            der = self.unario()
            izq = Nodo(op.valor, [izq, der], op.linea)
        return izq

    def unario(self) -> Nodo:
        """
        Operadores unarios prefijos: !, ~, negación aritmética (-), ++x, --x.

        El caso de '-' necesita cuidado: solo es unario si NO va precedido
        de otro operando (ej: en '5 - 3', el '-' es binario y lo maneja suma();
        aquí solo llegamos cuando no hay operando a la izquierda).
        peek(1) mira el token SIGUIENTE al '-' para evitar confusión con '--'.
        """
        tok = self.peek()
        if tok is None:
            return Nodo('ε')    # ε = nodo vacío, señal de expresión ausente

        # ! (negación lógica) y ~ (complemento a bits)
        if tok.valor in ('!', '~'):
            self.consume()
            return Nodo(f'unario {tok.valor}', [self.unario()], tok.linea)

        # Negación aritmética unaria: -x, -(a+b)
        # La guarda evita confundir con el operador '--'
        if tok.valor == '-' and (self.peek(1) is None or self.peek(1).valor not in ('+', '-')):
            self.consume()
            return Nodo('neg', [self.unario()], tok.linea)

        # Pre-incremento / pre-decremento: ++x, --x
        if tok.tipo == 'OPERADOR_INCR':
            op = self.consume()
            return Nodo(f'pre{op.valor}', [self.factor()], op.linea)

        return self.postfijo()

    def postfijo(self) -> Nodo:
        """
        Operadores postfijos que modifican una expresión ya parseada:
          - x++ / x--   (post-incremento / post-decremento)
          - arr[i]      (acceso a elemento de array)
          - obj.campo   (acceso a miembro de objeto/struct)

        El bucle while permite encadenarlos: arr[i].campo++ se parsea
        como (((arr)[i]).campo)++
        """
        nodo = self.factor()
        while True:
            tok = self.peek()
            if tok is None:
                break
            # Post-incremento / decremento: el nodo anterior pasa a ser el operando
            if tok.tipo == 'OPERADOR_INCR':
                op   = self.consume()
                nodo = Nodo(f'post{op.valor}', [nodo], op.linea)
            # Indexación de array: expr[índice]
            elif tok.valor == '[':
                self.consume()
                idx  = self.expr()
                self.esperar('DELIMITADOR', ']')
                nodo = Nodo('índice', [nodo, idx], tok.linea)
            # Acceso a miembro: expr.nombre
            elif tok.valor == '.':
                self.consume()
                miembro = self.esperar('IDENTIFICADOR')
                nombre  = miembro.valor if miembro else '?'
                nodo    = Nodo(f'.{nombre}', [nodo], tok.linea)
            else:
                break
        return nodo

    def factor(self) -> Nodo:
        """
        Unidad atómica de una expresión (el nivel más bajo de precedencia).
        Reconoce:
          - Literales numéricos, de cadena, booleanos y nulos.
          - Cast de tipo: (int) expr
          - Expresiones agrupadas entre paréntesis: (expr)
          - Identificadores solos: x
          - Llamadas a función: f(arg1, arg2)
          - Palabras clave usadas como valor (null, true… ya reclasificadas).
        Si no reconoce nada, devuelve un nodo ε sin consumir el token,
        para evitar bucles infinitos.
        """
        tok = self.peek()
        if tok is None:
            return Nodo('ε')

        # Literales: se crea un nodo hoja con el texto exacto del token
        if tok.tipo in ('LITERAL_NUM', 'LITERAL_CADENA',
                        'LITERAL_BOOLEANO', 'LITERAL_NULO'):
            self.consume()
            return Nodo(tok.valor, [], tok.linea)

        # Cast explícito de tipo: (int)expr, (float)x
        # Se detecta mirando tres tokens adelante: '(' tipo ')'
        if tok.valor == '(' and self.peek(1) and self.peek(1).valor in TIPOS_PRIMITIVOS:
            sig = self.peek(2)
            if sig and sig.valor == ')':
                self.consume()              # consume '('
                tipo_cast = self.consume()  # consume el tipo
                self.consume()              # consume ')'
                return Nodo(f'cast({tipo_cast.valor})', [self.unario()], tok.linea)

        # Expresión entre paréntesis para agrupar y cambiar precedencia
        if tok.valor == '(':
            self.consume()
            if self.val_es(')'):    # paréntesis vacíos: ()
                self.consume()
                return Nodo('()', [], tok.linea)
            nodo = self.expr()
            self.esperar('DELIMITADOR', ')')
            return nodo

        # Identificador solo o llamada a función
        if tok.tipo == 'IDENTIFICADOR':
            self.consume()
            if self.val_es('('):    # si le sigue '(' es una llamada a función
                self.consume()
                args = self._args()
                self.esperar('DELIMITADOR', ')')
                return Nodo(f"{tok.valor}(...)", args, tok.linea)
            return Nodo(tok.valor, [], tok.linea)   # identificador simple

        # Palabras clave que en este contexto son valores (ya reclasificadas)
        if tok.tipo == 'PALABRA_CLAVE':
            self.consume()
            return Nodo(tok.valor, [], tok.linea)

        # Nada reconocido: devolver nodo vacío SIN consumir para no perder el token
        return Nodo('ε')

    def _args(self) -> List[Nodo]:
        """
        Parsea la lista de argumentos de una llamada a función: arg1, arg2, …
        Se detiene al encontrar ')' o al acabar los tokens.
        Cada argumento es una expresión completa; las comas son separadores.
        """
        args = []
        while self.hay_mas() and not self.val_es(')'):
            args.append(self.expr())
            if not self.coincidir('DELIMITADOR', ','):
                break   # sin coma → no hay más argumentos
        return args

    # ══════════════════════════════════════════
    #  SENTENCIAS
    # ══════════════════════════════════════════

    def bloque(self) -> Nodo:
        """
        Parsea un bloque de código delimitado por llaves: { sentencia* }
        Un bloque puede contener cero o más sentencias.
        Se usa como cuerpo de funciones, if, while, for, do-while y switch.
        """
        tok_inicio = self.peek()
        self.esperar('DELIMITADOR', '{')
        hijos = []
        # Leer sentencias hasta encontrar '}' o agotar los tokens
        while self.hay_mas() and not self.val_es('}'):
            s = self.sentencia()
            if s:
                hijos.append(s)
        self.esperar('DELIMITADOR', '}')
        return Nodo('bloque', hijos, tok_inicio.linea if tok_inicio else 0)

    def bloque_o_sent(self) -> Nodo:
        """
        Permite que if/while/for acepten tanto un bloque con llaves
        como una sentencia simple sin llaves.
        Ejemplo con llaves:   if (x) { y = 1; z = 2; }
        Ejemplo sin llaves:   if (x) y = 1;
        Sin este método, el parser anterior crasheaba con la segunda forma.
        """
        if self.val_es('{'):
            return self.bloque()
        s = self.sentencia()
        return s if s else Nodo('ε')

    def sentencia(self) -> Optional[Nodo]:
        """
        Punto de entrada para parsear cualquier sentencia.
        Actúa como cortafuegos: envuelve _sentencia_impl() en un try/except
        para que cualquier excepción inesperada durante el parseo sea
        capturada, registrada como error y el análisis pueda continuar
        con la siguiente sentencia tras sincronizar el cursor.
        """
        tok = self.peek()
        if tok is None or tok.valor == '}':
            return None

        try:
            return self._sentencia_impl()
        except Exception as exc:
            linea = tok.linea if tok else '?'
            self.errores.append(f"Error interno en línea {linea}: {exc}")
            self._sincronizar()
            return None

    def _sentencia_impl(self) -> Optional[Nodo]:
        """
        Implementación real del reconocimiento de sentencias.
        Mira el token actual y despacha al método correspondiente según
        la palabra clave o el tipo de token. El orden de los if importa:
        las construcciones más específicas van primero.
        """
        tok = self.peek()
        if tok is None or tok.valor == '}':
            return None

        # ── if ──────────────────────────────────────────────────────────────
        # Estructura: if (condición) bloque_o_sent [else bloque_o_sent]
        # El else es opcional; si existe, se incluye como tercer hijo del nodo.
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor == 'if':
            self.consume()
            self.esperar('DELIMITADOR', '(')
            cond  = self.expr()
            self.esperar('DELIMITADOR', ')')
            then  = self.bloque_o_sent()
            hijos = [Nodo('condición', [cond], tok.linea), then]
            if self.peek() and self.peek().valor == 'else':
                self.consume()
                hijos.append(Nodo('else', [self.bloque_o_sent()], tok.linea))
            return Nodo('if', hijos, tok.linea)

        # ── while ────────────────────────────────────────────────────────────
        # Estructura: while (condición) bloque_o_sent
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor == 'while':
            self.consume()
            self.esperar('DELIMITADOR', '(')
            cond   = self.expr()
            self.esperar('DELIMITADOR', ')')
            cuerpo = self.bloque_o_sent()
            return Nodo('while', [Nodo('condición', [cond], tok.linea), cuerpo], tok.linea)

        # ── do-while ─────────────────────────────────────────────────────────
        # Estructura: do bloque while (condición) ;
        # A diferencia del while, el cuerpo se ejecuta al menos una vez
        # porque la condición se evalúa DESPUÉS del bloque.
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor == 'do':
            self.consume()
            cuerpo = self.bloque()
            self.esperar('PALABRA_CLAVE', 'while')
            self.esperar('DELIMITADOR', '(')
            cond   = self.expr()
            self.esperar('DELIMITADOR', ')')
            self.coincidir('DELIMITADOR', ';')
            return Nodo('do-while', [cuerpo, Nodo('condición', [cond], tok.linea)], tok.linea)

        # ── for ──────────────────────────────────────────────────────────────
        # Estructura: for (init ; condición ; incremento) bloque_o_sent
        # Los tres componentes son opcionales: for(;;) es un bucle infinito válido.
        # El árbol resultante tiene cuatro hijos: init, cond, inc, cuerpo.
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor == 'for':
            self.consume()
            self.esperar('DELIMITADOR', '(')

            # init: puede ser una declaración ("int i = 0"), una asignación
            # ("i = 0"), o estar vacío (";")
            init = None
            if not self.val_es(';'):
                if self.es_tipo_primitivo():
                    init = self._decl_variable()        # int i = 0;
                elif self.peek() and self.peek().tipo == 'IDENTIFICADOR':
                    init = self._asignacion_o_llamada() # i = 0;
                else:
                    self.coincidir('DELIMITADOR', ';')  # otro caso: consumir ';'

            # condición (opcional): si el próximo token ya es ';', está vacía
            cond = Nodo('ε')
            if not self.val_es(';'):
                cond = self.expr()
            self.esperar('DELIMITADOR', ';')

            # incremento (opcional): si el próximo token ya es ')', está vacío
            inc = Nodo('ε')
            if not self.val_es(')'):
                inc = self.expr()
            self.esperar('DELIMITADOR', ')')

            cuerpo = self.bloque_o_sent()
            return Nodo('for', [
                Nodo('init', [init] if init else []),
                Nodo('cond', [cond]),
                Nodo('inc',  [inc]),
                cuerpo
            ], tok.linea)

        # ── switch ───────────────────────────────────────────────────────────
        # Estructura: switch (expr) { case valor: sentencias… default: sentencias… }
        # Cada case y el default se convierten en nodos hijos del switch.
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor == 'switch':
            self.consume()
            self.esperar('DELIMITADOR', '(')
            expr_sw = self.expr()
            self.esperar('DELIMITADOR', ')')
            self.esperar('DELIMITADOR', '{')
            casos = []
            while self.hay_mas() and not self.val_es('}'):
                ct = self.peek()
                if ct and ct.valor == 'case':
                    self.consume()
                    val_case = self.expr()
                    self.esperar('DELIMITADOR', ':')
                    stmts = []
                    # Las sentencias del case van hasta el siguiente case, default o '}'
                    while self.hay_mas() and not self.val_es('case', 'default', '}'):
                        s = self.sentencia()
                        if s:
                            stmts.append(s)
                    casos.append(Nodo('case', [val_case] + stmts, ct.linea))
                elif ct and ct.valor == 'default':
                    self.consume()
                    self.esperar('DELIMITADOR', ':')
                    stmts = []
                    while self.hay_mas() and not self.val_es('case', 'default', '}'):
                        s = self.sentencia()
                        if s:
                            stmts.append(s)
                    casos.append(Nodo('default', stmts, ct.linea))
                else:
                    self.consume()  # token inesperado dentro del switch: descartar
            self.esperar('DELIMITADOR', '}')
            return Nodo('switch', [Nodo('expr-sw', [expr_sw])] + casos, tok.linea)

        # ── return ───────────────────────────────────────────────────────────
        # Estructura: return [expr] ;
        # El valor de retorno es opcional (ej: en funciones void).
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor == 'return':
            self.consume()
            if self.val_es(';'):
                self.consume()
                return Nodo('return', [], tok.linea)   # return sin valor
            val = self.expr()
            self.coincidir('DELIMITADOR', ';')
            return Nodo('return', [val], tok.linea)

        # ── break ────────────────────────────────────────────────────────────
        # Sale del switch o bucle más cercano. No tiene expresión asociada.
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor == 'break':
            self.consume()
            self.coincidir('DELIMITADOR', ';')
            return Nodo('break', [], tok.linea)

        # ── continue ─────────────────────────────────────────────────────────
        # Salta a la siguiente iteración del bucle más cercano.
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor == 'continue':
            self.consume()
            self.coincidir('DELIMITADOR', ';')
            return Nodo('continue', [], tok.linea)

        # ── bloque anónimo ────────────────────────────────────────────────────
        # Un bloque puede aparecer solo, sin encabezado de control de flujo.
        if tok.valor == '{':
            return self.bloque()

        # ── declaración de tipo ───────────────────────────────────────────────
        # Inicia con un tipo primitivo: int x; float y = 3.14; void f() { }
        if self.es_tipo_primitivo():
            return self._decl_tipo()

        # ── identificador: asignación, ++/--, llamada a función ──────────────
        if tok.tipo == 'IDENTIFICADOR':
            return self._asignacion_o_llamada()

        # ── punto y coma suelto (sentencia vacía) ─────────────────────────────
        # Es sintácticamente válido en C/C++/Java: for(;;) usa esta regla.
        if tok.valor == ';':
            self.consume()
            return None

        # ── expresión suelta ──────────────────────────────────────────────────
        # Cualquier expresión usada como sentencia, ej: una llamada a función
        # sin asignación cuyo resultado se descarta: printf("hola");
        e = self.expr()
        self.coincidir('DELIMITADOR', ';')
        return e

    # ── Auxiliares de declaración / asignación ────────────────────────────────

    def _decl_tipo(self) -> Optional[Nodo]:
        """
        Parsea una declaración que empieza con un tipo primitivo.
        Distingue entre declaración de variable y declaración de función
        mirando si después del identificador hay un '(' o no.

        También acepta palabras clave como nombre (ej: 'main', 'print')
        porque en tipos_token.py están clasificadas como PALABRA_CLAVE,
        no como IDENTIFICADOR.
        """
        tipo_tok = self.consume()   # consume el tipo (int, float, void…)

        # El nombre puede ser IDENTIFICADOR o PALABRA_CLAVE (ej: 'main')
        id_tok = self.peek()
        if id_tok is None or id_tok.tipo not in ('IDENTIFICADOR', 'PALABRA_CLAVE'):
            self.errores.append(
                f"Error sintáctico en línea {tipo_tok.linea}: "
                f"se esperaba identificador después de '{tipo_tok.valor}'"
            )
            self.coincidir('DELIMITADOR', ';')
            return None

        self.consume()  # consume el nombre

        # Si le sigue '(' es una función o prototipo
        if self.val_es('('):
            self.consume()
            params = self._params_func()
            self.esperar('DELIMITADOR', ')')
            # Prototipo: declaración sin cuerpo, termina en ';'
            if self.val_es(';'):
                self.consume()
                return Nodo(f"proto {tipo_tok.valor} {id_tok.valor}", params, tipo_tok.linea)
            # Definición completa: con bloque de cuerpo
            cuerpo = self.bloque()
            return Nodo(f"func {tipo_tok.valor} {id_tok.valor}",
                        params + [cuerpo], tipo_tok.linea)

        # Si no hay '(' es una declaración de variable
        return self._decl_variable_cont(tipo_tok, id_tok)

    def _decl_variable(self) -> Optional[Nodo]:
        """
        Alias de _decl_tipo() para claridad cuando se llama desde el init del for.
        El for necesita parsear una declaración de variable sin ambigüedad con funciones.
        """
        return self._decl_tipo()

    def _decl_variable_cont(self, tipo_tok: Token, id_tok: Token) -> Nodo:
        """
        Continúa parseando una declaración de variable después de que
        'tipo' e 'identificador' ya han sido consumidos.

        Maneja:
          - Inicializador opcional:       int x = 5;
          - Declaración simple:           int x;
          - Declaración múltiple:         int a = 1, b, c = 3;
            Cada variable adicional se añade como un sub-nodo de declaración.
        """
        hijos = [Nodo(id_tok.valor, [], id_tok.linea)]  # primer identificador

        # Inicializador opcional con '='
        if self.val_es('='):
            self.consume()
            hijos.append(self.expr())

        # Variables adicionales separadas por coma en la misma declaración
        while self.val_es(','):
            self.consume()
            extra_id = self.esperar('IDENTIFICADOR')
            if extra_id:
                extra_hijos = [Nodo(extra_id.valor, [], extra_id.linea)]
                if self.val_es('='):
                    self.consume()
                    extra_hijos.append(self.expr())
                hijos.append(Nodo(f"decl {tipo_tok.valor}", extra_hijos, extra_id.linea))

        self.coincidir('DELIMITADOR', ';')
        return Nodo(f"decl {tipo_tok.valor}", hijos, tipo_tok.linea)

    def _params_func(self) -> List[Nodo]:
        """
        Parsea la lista de parámetros formales de una función: tipo id, tipo id, …
        Cada parámetro se convierte en un nodo con etiqueta "tipo nombre".
        Si el parámetro no tiene nombre (ej: en un prototipo como f(int, float))
        se crea el nodo solo con el tipo.
        """
        params = []
        while self.hay_mas() and not self.val_es(')'):
            pt = self.consume()   # tipo del parámetro
            pi = self.peek()
            if pi and pi.tipo == 'IDENTIFICADOR':
                self.consume()
                params.append(Nodo(f"{pt.valor} {pi.valor}", [], pt.linea))
            else:
                # Solo tipo, sin nombre (prototipo)
                params.append(Nodo(pt.valor if pt else '?', [], pt.linea if pt else 0))
            self.coincidir('DELIMITADOR', ',')
        return params

    def _asignacion_o_llamada(self) -> Optional[Nodo]:
        """
        Parsea las sentencias que empiezan con un identificador:
          - Asignación simple o compuesta:  x = 5;  x += 3;
          - Post-incremento / decremento:   x++;  i--;
          - Llamada a función:              printf("hola");
          - Acceso a miembro/índice + asignación: obj.campo = 1;  arr[i] = 2;

        Consume el identificador primero y luego decide qué construcción
        es mirando el token siguiente.
        """
        tok = self.consume()   # consume el IDENTIFICADOR

        # Asignación simple (=) o compuesta (+=, -=, *=, …)
        if self.peek() and self.peek().tipo == 'OPERADOR_ASIG':
            op  = self.consume()
            val = self.expr()
            self.coincidir('DELIMITADOR', ';')
            return Nodo(f"asig {op.valor}",
                        [Nodo(tok.valor, [], tok.linea), val], tok.linea)

        # Post-incremento o decremento como sentencia: x++;  i--;
        if self.peek() and self.peek().tipo == 'OPERADOR_INCR':
            op = self.consume()
            self.coincidir('DELIMITADOR', ';')
            return Nodo(f"post{op.valor}", [Nodo(tok.valor, [], tok.linea)], tok.linea)

        # Llamada a función: nombre(arg1, arg2, …)
        if self.val_es('('):
            self.consume()
            args = self._args()
            self.esperar('DELIMITADOR', ')')
            self.coincidir('DELIMITADOR', ';')
            return Nodo(f"llamada {tok.valor}", args, tok.linea)

        # Acceso encadenado a miembro (.) o índice ([]) antes de la asignación.
        # El bucle permite: obj.a.b[0] = val; — cada operador de acceso
        # envuelve al anterior como hijo, construyendo el árbol de abajo arriba.
        nodo_izq = Nodo(tok.valor, [], tok.linea)
        changed  = True
        while changed:
            changed = False
            if self.val_es('.'):
                self.consume()
                miembro  = self.esperar('IDENTIFICADOR')
                nombre   = miembro.valor if miembro else '?'
                nodo_izq = Nodo(f'.{nombre}', [nodo_izq], tok.linea)
                changed  = True
            elif self.val_es('['):
                self.consume()
                idx      = self.expr()
                self.esperar('DELIMITADOR', ']')
                nodo_izq = Nodo('índice', [nodo_izq, idx], tok.linea)
                changed  = True

        # Asignación al resultado del acceso encadenado
        if self.peek() and self.peek().tipo == 'OPERADOR_ASIG':
            op  = self.consume()
            val = self.expr()
            self.coincidir('DELIMITADOR', ';')
            return Nodo(f"asig {op.valor}", [nodo_izq, val], tok.linea)

        # Identificador suelto (sin operador siguiente): consumir ';' y devolver
        self.coincidir('DELIMITADOR', ';')
        return nodo_izq

    # ══════════════════════════════════════════
    #  PROGRAMA
    # ══════════════════════════════════════════

    def parsear(self) -> Tuple[Nodo, List[str]]:
        """
        Punto de entrada del parser. Parsea el programa completo como
        una secuencia de sentencias de nivel superior (funciones, variables
        globales…) y devuelve la raíz del AST.

        Incluye una protección contra bucles infinitos: si tras llamar a
        sentencia() el cursor no avanzó, significa que el token actual no
        pudo ser parseado por ninguna regla. En ese caso se registra el
        error y se fuerza el avance consumiendo el token problemático.
        """
        hijos = []
        while self.hay_mas():
            pos_antes = self.pos
            s = self.sentencia()
            if s:
                hijos.append(s)
            # Si el cursor no avanzó, el token no encajó en ninguna regla:
            # registrar error y consumir para no quedar atrapado.
            if self.pos == pos_antes and self.hay_mas():
                tok_stuck = self.peek()
                self.errores.append(
                    f"Error sintáctico en línea {tok_stuck.linea}: "
                    f"token inesperado '{tok_stuck.valor}' ({tok_stuck.tipo})"
                )
                self.consume()
        return Nodo('programa', hijos), self.errores


# ─────────────────────────────────────────────
#  FUNCIÓN DE ACCESO RÁPIDO
# ─────────────────────────────────────────────

def analizar_sintactico(tokens: List[Token]) -> Tuple[Nodo, List[str]]:
    """
    Interfaz pública del módulo. Recibe la lista completa de tokens
    producida por analizar_completo() y devuelve:
      - El nodo raíz 'programa' del AST construido.
      - La lista de mensajes de error sintáctico encontrados.

    Instancia el Parser internamente para que el llamador no tenga que
    conocer los detalles de implementación de la clase.
    """
    return Parser(tokens).parsear()
