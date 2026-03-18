"""
sintactico.py — Analizador Sintáctico (descenso recursivo).

Gramática soportada (basada en el material del curso):
  programa     → sentencia*
  sentencia    → declaracion | asignacion | if_stmt | while_stmt
               | for_stmt | return_stmt | bloque | llamada ';'
  declaracion  → tipo IDENTIFICADOR ('=' expr)? ';'
  asignacion   → IDENTIFICADOR op_asig expr ';'
  if_stmt      → 'if' '(' expr ')' bloque ('else' bloque)?
  while_stmt   → 'while' '(' expr ')' bloque
  for_stmt     → 'for' '(' sentencia expr ';' expr ')' bloque
  return_stmt  → 'return' expr? ';'
  bloque       → '{' sentencia* '}'
  expr         → comparacion (('&&'|'||') comparacion)*
  comparacion  → suma (('=='|'!='|'<'|'>'|'<='|'>=') suma)*
  suma         → termino (('+'|'-') termino)*
  termino      → factor (('*'|'/'|'%') factor)*
  factor       → NÚMERO | CADENA | BOOL | NULO
               | IDENTIFICADOR ('(' args ')')?
               | '(' expr ')'
"""

from typing import List, Optional, Tuple
from tipos_token import Token


# ─────────────────────────────────────────────
#  NODO DEL ÁRBOL SINTÁCTICO
# ─────────────────────────────────────────────

class Nodo:
    def __init__(self, etiqueta: str, hijos: list = None, linea: int = 0):
        self.etiqueta = etiqueta
        self.hijos    = hijos or []
        self.linea    = linea

    def __repr__(self):
        return f"Nodo({self.etiqueta!r}, hijos={len(self.hijos)})"


# ─────────────────────────────────────────────
#  PARSER
# ─────────────────────────────────────────────

TIPOS_PRIMITIVOS = {'int', 'float', 'string', 'bool', 'void'}

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens  = tokens
        self.pos     = 0
        self.errores: List[str] = []

    # ── utilidades ────────────────────────────

    def peek(self) -> Optional[Token]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self) -> Optional[Token]:
        tok = self.peek()
        if tok:
            self.pos += 1
        return tok

    def esperar(self, tipo: str, valor: str = None) -> Optional[Token]:
        tok = self.peek()
        if tok and tok.tipo == tipo and (valor is None or tok.valor == valor):
            return self.consume()
        ubicacion = f"línea {tok.linea}" if tok else "fin de archivo"
        esperado  = f"'{valor}'" if valor else tipo
        encontrado = f"'{tok.valor}'" if tok else "EOF"
        self.errores.append(
            f"Error sintáctico en {ubicacion}: "
            f"se esperaba {esperado}, se encontró {encontrado}"
        )
        return None

    def coincidir(self, tipo: str, valor: str = None) -> bool:
        tok = self.peek()
        if tok and tok.tipo == tipo and (valor is None or tok.valor == valor):
            self.consume()
            return True
        return False

    def val_en(self, *valores) -> bool:
        tok = self.peek()
        return tok is not None and tok.valor in valores

    # ── EXPRESIONES ───────────────────────────

    def expr(self) -> Nodo:
        izq = self.comparacion()
        while self.val_en('&&', '||'):
            op  = self.consume()
            der = self.comparacion()
            izq = Nodo(op.valor, [izq, der], op.linea)
        return izq

    def comparacion(self) -> Nodo:
        izq = self.suma()
        while self.val_en('==', '!=', '<', '>', '<=', '>='):
            op  = self.consume()
            der = self.suma()
            izq = Nodo(op.valor, [izq, der], op.linea)
        return izq

    def suma(self) -> Nodo:
        izq = self.termino()
        while self.val_en('+', '-'):
            op  = self.consume()
            der = self.termino()
            izq = Nodo(op.valor, [izq, der], op.linea)
        return izq

    def termino(self) -> Nodo:
        izq = self.factor()
        while self.val_en('*', '/', '%'):
            op  = self.consume()
            der = self.factor()
            izq = Nodo(op.valor, [izq, der], op.linea)
        return izq

    def factor(self) -> Nodo:
        tok = self.peek()
        if tok is None:
            return Nodo('ε')

        # literal
        if tok.tipo in ('LITERAL_NUMÉRICO', 'LITERAL_CADENA',
                        'LITERAL_BOOL', 'LITERAL_NULO'):
            self.consume()
            return Nodo(tok.valor, [], tok.linea)

        # identificador o llamada a función
        if tok.tipo == 'IDENTIFICADOR':
            self.consume()
            if self.val_en('('):
                self.consume()      # (
                args = self._args()
                self.esperar('DELIMITADOR', ')')
                return Nodo(f"{tok.valor}(...)", args, tok.linea)
            return Nodo(tok.valor, [], tok.linea)

        # expresión entre paréntesis
        if tok.valor == '(':
            self.consume()
            nodo = self.expr()
            self.esperar('DELIMITADOR', ')')
            return nodo

        # signo negativo
        if tok.valor == '-':
            self.consume()
            return Nodo('neg', [self.factor()], tok.linea)

        self.consume()
        return Nodo(tok.valor, [], tok.linea)

    def _args(self) -> List[Nodo]:
        args = []
        while self.peek() and self.peek().valor != ')':
            args.append(self.expr())
            if not self.coincidir('DELIMITADOR', ','):
                break
        return args

    # ── SENTENCIAS ────────────────────────────

    def bloque(self) -> Nodo:
        self.esperar('DELIMITADOR', '{')
        hijos = []
        while self.peek() and self.peek().valor != '}':
            s = self.sentencia()
            if s:
                hijos.append(s)
            else:
                break
        self.esperar('DELIMITADOR', '}')
        return Nodo('bloque', hijos)

    def sentencia(self) -> Optional[Nodo]:
        tok = self.peek()
        if tok is None or tok.valor == '}':
            return None

        # ── if ──────────────────────────────
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor == 'if':
            self.consume()
            self.esperar('DELIMITADOR', '(')
            cond = self.expr()
            self.esperar('DELIMITADOR', ')')
            then = self.bloque()
            hijos = [Nodo('condición', [cond], tok.linea), then]
            if self.peek() and self.peek().valor == 'else':
                self.consume()
                hijos.append(Nodo('else', [self.bloque()], tok.linea))
            return Nodo('if', hijos, tok.linea)

        # ── while ────────────────────────────
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor == 'while':
            self.consume()
            self.esperar('DELIMITADOR', '(')
            cond = self.expr()
            self.esperar('DELIMITADOR', ')')
            return Nodo('while',
                        [Nodo('condición', [cond], tok.linea), self.bloque()],
                        tok.linea)

        # ── for ──────────────────────────────
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor == 'for':
            self.consume()
            self.esperar('DELIMITADOR', '(')
            init = self.sentencia()
            cond = self.expr()
            self.esperar('DELIMITADOR', ';')
            inc  = self.expr()
            self.esperar('DELIMITADOR', ')')
            cuerpo = self.bloque()
            return Nodo('for', [
                Nodo('init', [init] if init else []),
                Nodo('cond', [cond]),
                Nodo('inc',  [inc]),
                cuerpo
            ], tok.linea)

        # ── return ────────────────────────────
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor == 'return':
            self.consume()
            if self.peek() and self.peek().valor == ';':
                self.consume()
                return Nodo('return', [], tok.linea)
            val = self.expr()
            self.coincidir('DELIMITADOR', ';')
            return Nodo('return', [val], tok.linea)

        # ── bloque ────────────────────────────
        if tok.valor == '{':
            return self.bloque()

        # ── declaración: tipo id ... ──────────
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor in TIPOS_PRIMITIVOS:
            tipo_tok = self.consume()
            id_tok   = self.peek()
            if id_tok and id_tok.tipo == 'IDENTIFICADOR':
                self.consume()
                # función
                if self.val_en('('):
                    self.consume()
                    params = []
                    while self.peek() and self.peek().valor != ')':
                        pt = self.consume()
                        pi = self.consume()
                        params.append(Nodo(f"{pt.valor} {pi.valor if pi else '?'}"))
                        self.coincidir('DELIMITADOR', ',')
                    self.esperar('DELIMITADOR', ')')
                    cuerpo = self.bloque()
                    return Nodo(f"func {tipo_tok.valor} {id_tok.valor}",
                                params + [cuerpo], tipo_tok.linea)
                # variable
                hijos = [Nodo(id_tok.valor, [], id_tok.linea)]
                if self.val_en('='):
                    self.consume()
                    hijos.append(self.expr())
                self.coincidir('DELIMITADOR', ';')
                return Nodo(f"decl {tipo_tok.valor}", hijos, tipo_tok.linea)

        # ── asignación / llamada ──────────────
        if tok.tipo == 'IDENTIFICADOR':
            self.consume()
            # asignación compuesta
            if self.peek() and self.peek().tipo == 'OPERADOR_ASIG':
                op  = self.consume()
                val = self.expr()
                self.coincidir('DELIMITADOR', ';')
                return Nodo(f"asig {op.valor}",
                            [Nodo(tok.valor, [], tok.linea), val], tok.linea)
            # llamada
            if self.val_en('('):
                self.consume()
                args = self._args()
                self.esperar('DELIMITADOR', ')')
                self.coincidir('DELIMITADOR', ';')
                return Nodo(f"llamada {tok.valor}", args, tok.linea)
            self.coincidir('DELIMITADOR', ';')
            return Nodo(tok.valor, [], tok.linea)

        # ── avanzar para no quedar en bucle ───
        self.consume()
        return None

    # ── PROGRAMA ──────────────────────────────

    def parsear(self) -> Tuple[Nodo, List[str]]:
        hijos = []
        while self.peek():
            s = self.sentencia()
            if s:
                hijos.append(s)
        return Nodo('programa', hijos), self.errores


# ─────────────────────────────────────────────
#  FUNCIÓN DE ACCESO RÁPIDO
# ─────────────────────────────────────────────

def analizar_sintactico(tokens: List[Token]) -> Tuple[Nodo, List[str]]:
    """Recibe la lista de tokens del léxico y devuelve (árbol, errores)."""
    # Desduplicar: reconstruir lista completa (el parser necesita todos los tokens)
    return Parser(tokens).parsear()
