"""
sintactico.py — Analizador Sintáctico (descenso recursivo).

Gramática soportada (extendida y corregida):
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

Correcciones aplicadas:
  - Bug: frecuencias.get(clave, 1) en interfaz usaba clave string, no tupla
  - Bug: tipos de token inconsistentes (OPERADOR_ASIG vs OPERADOR_ASIGNACIÓN)
  - Bug: parser no manejaba do-while, switch, break, continue, ++/--, ternario
  - Bug: bloque_o_sent faltaba — if/while sin llaves crasheaba
  - Bug: recursión infinita si tokens desconocidos en secuencia
  - Bug: for sin init (for(;;)) no estaba contemplado
  - Mejora: recuperación de errores más robusta con sincronización
"""

from typing import List, Optional, Tuple
from tipos_token import Token, TIPOS_PRIMITIVOS


# ─────────────────────────────────────────────
#  NODO DEL ÁRBOL SINTÁCTICO
# ─────────────────────────────────────────────

class Nodo:
    """Nodo del AST (Árbol de Sintaxis Abstracta)."""

    def __init__(self, etiqueta: str, hijos: list = None, linea: int = 0):
        self.etiqueta = etiqueta
        self.hijos    = hijos if hijos is not None else []
        self.linea    = linea

    def __repr__(self):
        return f"Nodo({self.etiqueta!r}, hijos={len(self.hijos)})"

    def __str__(self):
        return self._str_indent(0)

    def _str_indent(self, nivel: int) -> str:
        indent = "  " * nivel
        resultado = f"{indent}{self.etiqueta}"
        for hijo in self.hijos:
            resultado += "\n" + hijo._str_indent(nivel + 1)
        return resultado


# ─────────────────────────────────────────────
#  PARSER
# ─────────────────────────────────────────────

# Tokens de sincronización para recuperación de errores
_SYNC_TOKENS = {'}', ';', 'if', 'while', 'for', 'return', 'int', 'float',
                'string', 'bool', 'void', 'else', 'do', 'switch'}


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens  = tokens
        self.pos     = 0
        self.errores: List[str] = []
        self._panic_mode = False   # True cuando estamos recuperándonos de error

    # ══════════════════════════════════════════
    #  UTILIDADES BÁSICAS
    # ══════════════════════════════════════════

    def peek(self, offset: int = 0) -> Optional[Token]:
        """Devuelve el token en pos+offset sin consumirlo."""
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else None

    def consume(self) -> Optional[Token]:
        tok = self.peek()
        if tok:
            self.pos += 1
        return tok

    def hay_mas(self) -> bool:
        return self.pos < len(self.tokens)

    def esperar(self, tipo: str, valor: str = None) -> Optional[Token]:
        """Consume el token si coincide, o registra error y devuelve None."""
        tok = self.peek()
        if tok and tok.tipo == tipo and (valor is None or tok.valor == valor):
            return self.consume()
        ubicacion  = f"línea {tok.linea}, col {tok.columna}" if tok else "fin de archivo"
        esperado   = f"'{valor}'" if valor else tipo
        encontrado = f"'{tok.valor}' ({tok.tipo})" if tok else "EOF"
        self.errores.append(
            f"Error sintáctico en {ubicacion}: "
            f"se esperaba {esperado}, se encontró {encontrado}"
        )
        return None

    def coincidir(self, tipo: str, valor: str = None) -> bool:
        """Consume y devuelve True si coincide, sin generar error si no."""
        tok = self.peek()
        if tok and tok.tipo == tipo and (valor is None or tok.valor == valor):
            self.consume()
            return True
        return False

    def val_es(self, *valores) -> bool:
        tok = self.peek()
        return tok is not None and tok.valor in valores

    def tipo_es(self, *tipos) -> bool:
        tok = self.peek()
        return tok is not None and tok.tipo in tipos

    def es_tipo_primitivo(self) -> bool:
        tok = self.peek()
        return tok is not None and tok.tipo == 'PALABRA_CLAVE' and tok.valor in TIPOS_PRIMITIVOS

    def _sincronizar(self):
        """Avanza hasta un token de sincronización para recuperarse de un error."""
        while self.hay_mas():
            tok = self.peek()
            if tok.valor in _SYNC_TOKENS or tok.tipo == 'DELIMITADOR' and tok.valor in ('{', '}', ';'):
                break
            self.consume()

    # ══════════════════════════════════════════
    #  EXPRESIONES
    # ══════════════════════════════════════════

    def expr(self) -> Nodo:
        """Expresión completa, incluyendo asignación inline."""
        izq = self.logico_o()

        # Asignación inline: x = expr (en contexto de expresión, ej: f(x = 5))
        if self.peek() and self.peek().tipo == 'OPERADOR_ASIG':
            op  = self.consume()
            der = self.expr()  # asociatividad derecha
            return Nodo(f"asig {op.valor}", [izq, der], op.linea)

        # Operador ternario: cond ? a : b
        if self.val_es('?'):
            self.consume()
            entonces = self.expr()
            self.esperar('DELIMITADOR', ':') if not self.coincidir('DELIMITADOR', ':') else None
            sino = self.expr()
            return Nodo('ternario', [izq, entonces, sino], izq.linea)

        return izq

    def logico_o(self) -> Nodo:
        izq = self.logico_y()
        while self.val_es('||'):
            op  = self.consume()
            der = self.logico_y()
            izq = Nodo('||', [izq, der], op.linea)
        return izq

    def logico_y(self) -> Nodo:
        izq = self.igualdad()
        while self.val_es('&&'):
            op  = self.consume()
            der = self.igualdad()
            izq = Nodo('&&', [izq, der], op.linea)
        return izq

    def igualdad(self) -> Nodo:
        izq = self.comparacion()
        while self.val_es('==', '!='):
            op  = self.consume()
            der = self.comparacion()
            izq = Nodo(op.valor, [izq, der], op.linea)
        return izq

    def comparacion(self) -> Nodo:
        izq = self.suma()
        while self.val_es('<', '>', '<=', '>='):
            op  = self.consume()
            der = self.suma()
            izq = Nodo(op.valor, [izq, der], op.linea)
        return izq

    def suma(self) -> Nodo:
        izq = self.termino()
        while self.val_es('+', '-'):
            op  = self.consume()
            der = self.termino()
            izq = Nodo(op.valor, [izq, der], op.linea)
        return izq

    def termino(self) -> Nodo:
        izq = self.unario()
        while self.val_es('*', '/', '%'):
            op  = self.consume()
            der = self.unario()
            izq = Nodo(op.valor, [izq, der], op.linea)
        return izq

    def unario(self) -> Nodo:
        tok = self.peek()
        if tok is None:
            return Nodo('ε')

        # Operadores unarios prefijos
        if tok.valor in ('!', '~'):
            self.consume()
            return Nodo(f'unario {tok.valor}', [self.unario()], tok.linea)
        if tok.valor == '-' and (self.peek(1) is None or self.peek(1).valor not in ('+', '-')):
            # Negación unaria (no confundir con resta binaria en contexto)
            self.consume()
            return Nodo('neg', [self.unario()], tok.linea)
        if tok.tipo == 'OPERADOR_INCR':
            op = self.consume()
            return Nodo(f'pre{op.valor}', [self.factor()], op.linea)

        return self.postfijo()

    def postfijo(self) -> Nodo:
        nodo = self.factor()
        while True:
            tok = self.peek()
            if tok is None:
                break
            # Post-incremento / decremento
            if tok.tipo == 'OPERADOR_INCR':
                op = self.consume()
                nodo = Nodo(f'post{op.valor}', [nodo], op.linea)
            # Acceso a array
            elif tok.valor == '[':
                self.consume()
                idx = self.expr()
                self.esperar('DELIMITADOR', ']')
                nodo = Nodo('índice', [nodo, idx], tok.linea)
            # Acceso a miembro
            elif tok.valor == '.':
                self.consume()
                miembro = self.esperar('IDENTIFICADOR')
                nombre  = miembro.valor if miembro else '?'
                nodo = Nodo(f'.{nombre}', [nodo], tok.linea)
            else:
                break
        return nodo

    def factor(self) -> Nodo:
        tok = self.peek()
        if tok is None:
            return Nodo('ε')

        # Literales
        if tok.tipo in ('LITERAL_NUM', 'LITERAL_CADENA',
                        'LITERAL_BOOLEANO', 'LITERAL_NULO'):
            self.consume()
            return Nodo(tok.valor, [], tok.linea)

        # Cast: (tipo) expr
        if tok.valor == '(' and self.peek(1) and self.peek(1).valor in TIPOS_PRIMITIVOS:
            sig = self.peek(2)
            if sig and sig.valor == ')':
                self.consume()          # (
                tipo_cast = self.consume()
                self.consume()          # )
                return Nodo(f'cast({tipo_cast.valor})', [self.unario()], tok.linea)

        # Expresión entre paréntesis
        if tok.valor == '(':
            self.consume()
            if self.val_es(')'):        # paréntesis vacíos — vacío
                self.consume()
                return Nodo('()', [], tok.linea)
            nodo = self.expr()
            self.esperar('DELIMITADOR', ')')
            return nodo

        # Identificador o llamada a función
        if tok.tipo == 'IDENTIFICADOR':
            self.consume()
            if self.val_es('('):
                self.consume()
                args = self._args()
                self.esperar('DELIMITADOR', ')')
                return Nodo(f"{tok.valor}(...)", args, tok.linea)
            return Nodo(tok.valor, [], tok.linea)

        # Palabra clave usada como valor (ej: null, true, etc. ya reclasificados)
        if tok.tipo == 'PALABRA_CLAVE':
            self.consume()
            return Nodo(tok.valor, [], tok.linea)

        # No reconocido en expresión — devolver nodo vacío sin consumir
        return Nodo('ε')

    def _args(self) -> List[Nodo]:
        """Lista de argumentos de una llamada a función."""
        args = []
        while self.hay_mas() and not self.val_es(')'):
            args.append(self.expr())
            if not self.coincidir('DELIMITADOR', ','):
                break
        return args

    # ══════════════════════════════════════════
    #  SENTENCIAS
    # ══════════════════════════════════════════

    def bloque(self) -> Nodo:
        """'{' sentencia* '}'"""
        tok_inicio = self.peek()
        self.esperar('DELIMITADOR', '{')
        hijos = []
        while self.hay_mas() and not self.val_es('}'):
            s = self.sentencia()
            if s:
                hijos.append(s)
        self.esperar('DELIMITADOR', '}')
        return Nodo('bloque', hijos, tok_inicio.linea if tok_inicio else 0)

    def bloque_o_sent(self) -> Nodo:
        """Permite if/while/for sin llaves (sentencia simple)."""
        if self.val_es('{'):
            return self.bloque()
        s = self.sentencia()
        return s if s else Nodo('ε')

    def sentencia(self) -> Optional[Nodo]:
        tok = self.peek()
        if tok is None or tok.valor == '}':
            return None

        try:
            return self._sentencia_impl()
        except Exception as exc:
            # Recuperación ante excepción inesperada
            linea = tok.linea if tok else '?'
            self.errores.append(
                f"Error interno en línea {linea}: {exc}"
            )
            self._sincronizar()
            return None

    def _sentencia_impl(self) -> Optional[Nodo]:
        tok = self.peek()
        if tok is None or tok.valor == '}':
            return None

        # ── if ──────────────────────────────────────────────────────
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor == 'if':
            self.consume()
            self.esperar('DELIMITADOR', '(')
            cond = self.expr()
            self.esperar('DELIMITADOR', ')')
            then  = self.bloque_o_sent()
            hijos = [Nodo('condición', [cond], tok.linea), then]
            if self.peek() and self.peek().valor == 'else':
                self.consume()
                hijos.append(Nodo('else', [self.bloque_o_sent()], tok.linea))
            return Nodo('if', hijos, tok.linea)

        # ── while ───────────────────────────────────────────────────
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor == 'while':
            self.consume()
            self.esperar('DELIMITADOR', '(')
            cond = self.expr()
            self.esperar('DELIMITADOR', ')')
            cuerpo = self.bloque_o_sent()
            return Nodo('while', [Nodo('condición', [cond], tok.linea), cuerpo], tok.linea)

        # ── do-while ────────────────────────────────────────────────
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor == 'do':
            self.consume()
            cuerpo = self.bloque()
            self.esperar('PALABRA_CLAVE', 'while')
            self.esperar('DELIMITADOR', '(')
            cond = self.expr()
            self.esperar('DELIMITADOR', ')')
            self.coincidir('DELIMITADOR', ';')
            return Nodo('do-while', [cuerpo, Nodo('condición', [cond], tok.linea)], tok.linea)

        # ── for ─────────────────────────────────────────────────────
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor == 'for':
            self.consume()
            self.esperar('DELIMITADOR', '(')

            # init: declaración, asignación o vacío
            init = None
            if not self.val_es(';'):
                if self.es_tipo_primitivo():
                    init = self._decl_variable()
                elif self.peek() and self.peek().tipo == 'IDENTIFICADOR':
                    init = self._asignacion_o_llamada()
                else:
                    self.coincidir('DELIMITADOR', ';')

            # cond
            cond = Nodo('ε')
            if not self.val_es(';'):
                cond = self.expr()
            self.esperar('DELIMITADOR', ';')

            # inc
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

        # ── switch ──────────────────────────────────────────────────
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
                    while self.hay_mas() and not self.val_es('case', 'default', '}'):
                        s = self.sentencia()
                        if s: stmts.append(s)
                    casos.append(Nodo('case', [val_case] + stmts, ct.linea))
                elif ct and ct.valor == 'default':
                    self.consume()
                    self.esperar('DELIMITADOR', ':')
                    stmts = []
                    while self.hay_mas() and not self.val_es('case', 'default', '}'):
                        s = self.sentencia()
                        if s: stmts.append(s)
                    casos.append(Nodo('default', stmts, ct.linea))
                else:
                    self.consume()  # evitar bucle infinito
            self.esperar('DELIMITADOR', '}')
            return Nodo('switch', [Nodo('expr-sw', [expr_sw])] + casos, tok.linea)

        # ── return ──────────────────────────────────────────────────
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor == 'return':
            self.consume()
            if self.val_es(';'):
                self.consume()
                return Nodo('return', [], tok.linea)
            val = self.expr()
            self.coincidir('DELIMITADOR', ';')
            return Nodo('return', [val], tok.linea)

        # ── break ───────────────────────────────────────────────────
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor == 'break':
            self.consume()
            self.coincidir('DELIMITADOR', ';')
            return Nodo('break', [], tok.linea)

        # ── continue ────────────────────────────────────────────────
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor == 'continue':
            self.consume()
            self.coincidir('DELIMITADOR', ';')
            return Nodo('continue', [], tok.linea)

        # ── bloque anónimo ───────────────────────────────────────────
        if tok.valor == '{':
            return self.bloque()

        # ── declaración de tipo ──────────────────────────────────────
        if self.es_tipo_primitivo():
            return self._decl_tipo()

        # ── identificador: asignación, ++/--, llamada, expr ─────────
        if tok.tipo == 'IDENTIFICADOR':
            return self._asignacion_o_llamada()

        # ── punto y coma suelto (sentencia vacía) ────────────────────
        if tok.valor == ';':
            self.consume()
            return None

        # ── expresión suelta (ej: función sin asignación) ────────────
        e = self.expr()
        self.coincidir('DELIMITADOR', ';')
        return e

    # ── auxiliares de declaración / asignación ─────────────────────

    def _decl_tipo(self) -> Optional[Nodo]:
        """Declaración de variable o función: tipo id ..."""
        tipo_tok = self.consume()

        # Acepta IDENTIFICADOR o PALABRA_CLAVE como nombre
        # (ej: 'int main()' donde 'main' está clasificado como PALABRA_CLAVE)
        id_tok = self.peek()
        if id_tok is None or id_tok.tipo not in ('IDENTIFICADOR', 'PALABRA_CLAVE'):
            self.errores.append(
                f"Error sintáctico en línea {tipo_tok.linea}: "
                f"se esperaba identificador después de '{tipo_tok.valor}'"
            )
            self.coincidir('DELIMITADOR', ';')
            return None

        self.consume()  # consume identificador

        # Función
        if self.val_es('('):
            self.consume()
            params = self._params_func()
            self.esperar('DELIMITADOR', ')')
            # Prototipo (sin cuerpo)
            if self.val_es(';'):
                self.consume()
                return Nodo(f"proto {tipo_tok.valor} {id_tok.valor}", params, tipo_tok.linea)
            cuerpo = self.bloque()
            return Nodo(f"func {tipo_tok.valor} {id_tok.valor}",
                        params + [cuerpo], tipo_tok.linea)

        # Variable(s)
        return self._decl_variable_cont(tipo_tok, id_tok)

    def _decl_variable(self) -> Optional[Nodo]:
        """Declaración de variable (usada internamente en for init)."""
        return self._decl_tipo()

    def _decl_variable_cont(self, tipo_tok: Token, id_tok: Token) -> Nodo:
        """Continúa parseando tras 'tipo id' ya consumidos."""
        hijos = [Nodo(id_tok.valor, [], id_tok.linea)]

        # Inicializador opcional
        if self.val_es('='):
            self.consume()
            hijos.append(self.expr())

        # Más variables en la misma declaración: int a=1, b, c=3;
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
        """Parámetros formales: (tipo id, tipo id, ...)"""
        params = []
        while self.hay_mas() and not self.val_es(')'):
            # void o tipo primitivo
            pt = self.consume()
            pi = self.peek()
            if pi and pi.tipo == 'IDENTIFICADOR':
                self.consume()
                params.append(Nodo(f"{pt.valor} {pi.valor}", [], pt.linea))
            else:
                params.append(Nodo(pt.valor if pt else '?', [], pt.linea if pt else 0))
            self.coincidir('DELIMITADOR', ',')
        return params

    def _asignacion_o_llamada(self) -> Optional[Nodo]:
        """Maneja: id = expr; | id += expr; | id++; | id(...); | id;"""
        tok = self.consume()  # consume el IDENTIFICADOR

        # Asignación compuesta o simple
        if self.peek() and self.peek().tipo == 'OPERADOR_ASIG':
            op  = self.consume()
            val = self.expr()
            self.coincidir('DELIMITADOR', ';')
            return Nodo(f"asig {op.valor}",
                        [Nodo(tok.valor, [], tok.linea), val], tok.linea)

        # Post-incremento / decremento como sentencia
        if self.peek() and self.peek().tipo == 'OPERADOR_INCR':
            op = self.consume()
            self.coincidir('DELIMITADOR', ';')
            return Nodo(f"post{op.valor}", [Nodo(tok.valor, [], tok.linea)], tok.linea)

        # Llamada a función
        if self.val_es('('):
            self.consume()
            args = self._args()
            self.esperar('DELIMITADOR', ')')
            self.coincidir('DELIMITADOR', ';')
            return Nodo(f"llamada {tok.valor}", args, tok.linea)

        # Acceso a miembro o índice seguido de asignación
        # (ej: obj.campo = valor; o arr[i] = valor;)
        nodo_izq = Nodo(tok.valor, [], tok.linea)
        changed = True
        while changed:
            changed = False
            if self.val_es('.'):
                self.consume()
                miembro = self.esperar('IDENTIFICADOR')
                nombre  = miembro.valor if miembro else '?'
                nodo_izq = Nodo(f'.{nombre}', [nodo_izq], tok.linea)
                changed = True
            elif self.val_es('['):
                self.consume()
                idx = self.expr()
                self.esperar('DELIMITADOR', ']')
                nodo_izq = Nodo('índice', [nodo_izq, idx], tok.linea)
                changed = True

        if self.peek() and self.peek().tipo == 'OPERADOR_ASIG':
            op  = self.consume()
            val = self.expr()
            self.coincidir('DELIMITADOR', ';')
            return Nodo(f"asig {op.valor}", [nodo_izq, val], tok.linea)

        self.coincidir('DELIMITADOR', ';')
        return nodo_izq

    # ══════════════════════════════════════════
    #  PROGRAMA
    # ══════════════════════════════════════════

    def parsear(self) -> Tuple[Nodo, List[str]]:
        hijos = []
        while self.hay_mas():
            pos_antes = self.pos
            s = self.sentencia()
            if s:
                hijos.append(s)
            # Protección contra bucle infinito: si no avanzamos, forzar
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
    """Recibe la lista de tokens del léxico y devuelve (árbol, errores)."""
    return Parser(tokens).parsear()
