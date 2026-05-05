"""sintactico.py — Parser por descenso recursivo que produce un AST.

Gramática soportada (simplificada):
  programa  → sentencia*
  sentencia → decl | asig | if | while | for | do-while | switch
            | return | break | continue | bloque | llamada';' | expr';'
  expr      → ternario | asig_inline | logico_o
  logico_o  → logico_y  ('||' logico_y)*
  logico_y  → igualdad  ('&&' igualdad)*
  igualdad  → comparacion (('=='|'!=') comparacion)*
  comparacion → suma (('<'|'>'|'<='|'>=') suma)*
  suma      → termino   (('+'|'-') termino)*
  termino   → unario    (('*'|'/'|'%') unario)*
  unario    → ('!'|'~'|'-'|'++'|'--') factor | postfijo
  postfijo  → factor ('++'|'--'|'['expr']'|'.id')*
  factor    → literal | '('expr')' | id'('args')' | id | kw
"""

from typing import List, Optional, Tuple

from tipos_token import Token, TIPOS_PRIMITIVOS


# ── Nodo del AST ──────────────────────────────────────────────────────────────

class Nodo:
    """Nodo del Árbol de Sintaxis Abstracta."""

    def __init__(self, etiqueta: str, hijos: list = None, linea: int = 0):
        self.etiqueta = etiqueta
        self.hijos    = hijos if hijos is not None else []
        self.linea    = linea

    def __repr__(self) -> str:
        return f"Nodo({self.etiqueta!r}, hijos={len(self.hijos)})"

    def __str__(self) -> str:
        return self._str_indent(0)

    def _str_indent(self, nivel: int) -> str:
        indent    = "  " * nivel
        resultado = f"{indent}{self.etiqueta}"
        for hijo in self.hijos:
            resultado += "\n" + hijo._str_indent(nivel + 1)
        return resultado


# ── Tokens de sincronización para recuperación de errores ────────────────────
_SYNC_TOKENS = {'}', ';', 'if', 'while', 'for', 'return', 'int', 'float',
                'string', 'bool', 'void', 'else', 'do', 'switch'}


# ── Parser ────────────────────────────────────────────────────────────────────

class Parser:
    """Analizador sintáctico por descenso recursivo predictivo."""

    def __init__(self, tokens: List[Token]):
        self.tokens  = tokens
        self.pos     = 0
        self.errores: List[str] = []

    # ── Utilidades básicas ────────────────────────────────────────────────────

    def peek(self, offset: int = 0) -> Optional[Token]:
        """Token en pos+offset sin consumirlo; None si está fuera de rango."""
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else None

    def consume(self) -> Optional[Token]:
        """Devuelve el token actual y avanza el cursor."""
        tok = self.peek()
        if tok:
            self.pos += 1
        return tok

    def hay_mas(self) -> bool:
        return self.pos < len(self.tokens)

    def esperar(self, tipo: str, valor: str = None) -> Optional[Token]:
        """Consume el token si coincide; registra error y devuelve None si no."""
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
        """Consume el token si coincide (token opcional); sin error si no."""
        tok = self.peek()
        if tok and tok.tipo == tipo and (valor is None or tok.valor == valor):
            self.consume()
            return True
        return False

    def val_es(self, *valores) -> bool:
        """True si el valor del token actual es alguno de los indicados."""
        tok = self.peek()
        return tok is not None and tok.valor in valores

    def tipo_es(self, *tipos) -> bool:
        """True si el tipo del token actual es alguno de los indicados."""
        tok = self.peek()
        return tok is not None and tok.tipo in tipos

    def es_tipo_primitivo(self) -> bool:
        """True si el token actual es una palabra clave de tipo (int, float…)."""
        tok = self.peek()
        return tok is not None and tok.tipo == 'PALABRA_CLAVE' and tok.valor in TIPOS_PRIMITIVOS

    def _sincronizar(self):
        """Recuperación de pánico: avanza hasta el próximo token de sincronización."""
        while self.hay_mas():
            tok = self.peek()
            if tok.valor in _SYNC_TOKENS or (
                tok.tipo == 'DELIMITADOR' and tok.valor in ('{', '}', ';')
            ):
                break
            self.consume()

    # ── Expresiones (de menor a mayor precedencia) ────────────────────────────

    def expr(self) -> Nodo:
        """Raíz de expresión: maneja asignación inline y operador ternario."""
        izq = self.logico_o()

        # Asignación inline (asociatividad derecha: a = b = 5 → a = (b = 5))
        if self.peek() and self.peek().tipo == 'OPERADOR_ASIG':
            op  = self.consume()
            der = self.expr()
            return Nodo(f"asig {op.valor}", [izq, der], op.linea)

        # Operador ternario: cond ? entonces : sino
        if self.val_es('?'):
            self.consume()
            entonces = self.expr()
            if not self.coincidir('DELIMITADOR', ':'):
                self.esperar('DELIMITADOR', ':')
            sino = self.expr()
            return Nodo('ternario', [izq, entonces, sino], izq.linea)

        return izq

    def logico_o(self) -> Nodo:
        """|| con asociatividad izquierda."""
        izq = self.logico_y()
        while self.val_es('||'):
            op  = self.consume()
            der = self.logico_y()
            izq = Nodo('||', [izq, der], op.linea)
        return izq

    def logico_y(self) -> Nodo:
        """&& con asociatividad izquierda; mayor precedencia que ||."""
        izq = self.igualdad()
        while self.val_es('&&'):
            op  = self.consume()
            der = self.igualdad()
            izq = Nodo('&&', [izq, der], op.linea)
        return izq

    def igualdad(self) -> Nodo:
        """== y != ; menor precedencia que los relacionales."""
        izq = self.comparacion()
        while self.val_es('==', '!='):
            op  = self.consume()
            der = self.comparacion()
            izq = Nodo(op.valor, [izq, der], op.linea)
        return izq

    def comparacion(self) -> Nodo:
        """< > <= >= ; mayor precedencia que == y !=."""
        izq = self.suma()
        while self.val_es('<', '>', '<=', '>='):
            op  = self.consume()
            der = self.suma()
            izq = Nodo(op.valor, [izq, der], op.linea)
        return izq

    def suma(self) -> Nodo:
        """+ y - ; mayor precedencia que los relacionales."""
        izq = self.termino()
        while self.val_es('+', '-'):
            op  = self.consume()
            der = self.termino()
            izq = Nodo(op.valor, [izq, der], op.linea)
        return izq

    def termino(self) -> Nodo:
        """* / % ; mayor precedencia que + y -."""
        izq = self.unario()
        while self.val_es('*', '/', '%'):
            op  = self.consume()
            der = self.unario()
            izq = Nodo(op.valor, [izq, der], op.linea)
        return izq

    def unario(self) -> Nodo:
        """Operadores prefijos: !, ~, negación aritmética, ++x, --x."""
        tok = self.peek()
        if tok is None:
            return Nodo('ε')

        if tok.valor in ('!', '~'):
            self.consume()
            return Nodo(f'unario {tok.valor}', [self.unario()], tok.linea)

        # '-' unario: evitar confundir con '--'
        if tok.valor == '-' and (self.peek(1) is None or self.peek(1).valor not in ('+', '-')):
            self.consume()
            return Nodo('neg', [self.unario()], tok.linea)

        # Pre-incremento / decremento
        if tok.tipo == 'OPERADOR_INCR':
            op = self.consume()
            return Nodo(f'pre{op.valor}', [self.factor()], op.linea)

        return self.postfijo()

    def postfijo(self) -> Nodo:
        """x++, x--, arr[i], obj.campo — encadenables."""
        nodo = self.factor()
        while True:
            tok = self.peek()
            if tok is None:
                break
            if tok.tipo == 'OPERADOR_INCR':
                op   = self.consume()
                nodo = Nodo(f'post{op.valor}', [nodo], op.linea)
            elif tok.valor == '[':
                self.consume()
                idx  = self.expr()
                self.esperar('DELIMITADOR', ']')
                nodo = Nodo('índice', [nodo, idx], tok.linea)
            elif tok.valor == '.':
                self.consume()
                miembro = self.esperar('IDENTIFICADOR')
                nombre  = miembro.valor if miembro else '?'
                nodo    = Nodo(f'.{nombre}', [nodo], tok.linea)
            else:
                break
        return nodo

    def factor(self) -> Nodo:
        """Unidad atómica: literal, (expr), id, llamada, cast, kw-valor."""
        tok = self.peek()
        if tok is None:
            return Nodo('ε')

        # Literales
        if tok.tipo in ('LITERAL_NUM', 'LITERAL_CADENA', 'LITERAL_BOOLEANO', 'LITERAL_NULO'):
            self.consume()
            return Nodo(tok.valor, [], tok.linea)

        # Cast: (tipo)expr — detectado mirando tres tokens adelante
        if tok.valor == '(' and self.peek(1) and self.peek(1).valor in TIPOS_PRIMITIVOS:
            sig = self.peek(2)
            if sig and sig.valor == ')':
                self.consume()              # '('
                tipo_cast = self.consume()  # tipo
                self.consume()              # ')'
                return Nodo(f'cast({tipo_cast.valor})', [self.unario()], tok.linea)

        # Expresión agrupada
        if tok.valor == '(':
            self.consume()
            if self.val_es(')'):
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

        # Palabras clave usadas como valor (ya reclasificadas por el léxico)
        if tok.tipo == 'PALABRA_CLAVE':
            self.consume()
            return Nodo(tok.valor, [], tok.linea)

        return Nodo('ε')   # nada reconocido — no consumir para evitar bucles

    def _args(self) -> List[Nodo]:
        """Lista de argumentos separados por coma hasta encontrar ')'."""
        args = []
        while self.hay_mas() and not self.val_es(')'):
            args.append(self.expr())
            if not self.coincidir('DELIMITADOR', ','):
                break
        return args

    # ── Sentencias ────────────────────────────────────────────────────────────

    def bloque(self) -> Nodo:
        """{ sentencia* } — cuerpo de funciones, if, while, for…"""
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
        """Permite cuerpo con llaves ({ }) o sentencia simple sin llaves."""
        if self.val_es('{'):
            return self.bloque()
        s = self.sentencia()
        return s if s else Nodo('ε')

    def sentencia(self) -> Optional[Nodo]:
        """Envuelve _sentencia_impl en try/except para recuperarse de errores."""
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
        """Despacha al método correcto según el token actual."""
        tok = self.peek()
        if tok is None or tok.valor == '}':
            return None

        # if
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

        # while
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor == 'while':
            self.consume()
            self.esperar('DELIMITADOR', '(')
            cond   = self.expr()
            self.esperar('DELIMITADOR', ')')
            cuerpo = self.bloque_o_sent()
            return Nodo('while', [Nodo('condición', [cond], tok.linea), cuerpo], tok.linea)

        # do-while
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor == 'do':
            self.consume()
            cuerpo = self.bloque()
            self.esperar('PALABRA_CLAVE', 'while')
            self.esperar('DELIMITADOR', '(')
            cond   = self.expr()
            self.esperar('DELIMITADOR', ')')
            self.coincidir('DELIMITADOR', ';')
            return Nodo('do-while', [cuerpo, Nodo('condición', [cond], tok.linea)], tok.linea)

        # for — init puede ser decl, asig o vacío
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor == 'for':
            self.consume()
            self.esperar('DELIMITADOR', '(')
            init = None
            if not self.val_es(';'):
                if self.es_tipo_primitivo():
                    init = self._decl_variable()
                elif self.peek() and self.peek().tipo == 'IDENTIFICADOR':
                    init = self._asignacion_o_llamada()
                else:
                    self.coincidir('DELIMITADOR', ';')
            cond = Nodo('ε')
            if not self.val_es(';'):
                cond = self.expr()
            self.esperar('DELIMITADOR', ';')
            inc = Nodo('ε')
            if not self.val_es(')'):
                inc = self.expr()
            self.esperar('DELIMITADOR', ')')
            cuerpo = self.bloque_o_sent()
            return Nodo('for', [
                Nodo('init', [init] if init else []),
                Nodo('cond', [cond]),
                Nodo('inc',  [inc]),
                cuerpo,
            ], tok.linea)

        # switch
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
                    self.consume()   # token inesperado dentro del switch
            self.esperar('DELIMITADOR', '}')
            return Nodo('switch', [Nodo('expr-sw', [expr_sw])] + casos, tok.linea)

        # return [expr] ;
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor == 'return':
            self.consume()
            if self.val_es(';'):
                self.consume()
                return Nodo('return', [], tok.linea)
            val = self.expr()
            self.coincidir('DELIMITADOR', ';')
            return Nodo('return', [val], tok.linea)

        # break
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor == 'break':
            self.consume()
            self.coincidir('DELIMITADOR', ';')
            return Nodo('break', [], tok.linea)

        # continue
        if tok.tipo == 'PALABRA_CLAVE' and tok.valor == 'continue':
            self.consume()
            self.coincidir('DELIMITADOR', ';')
            return Nodo('continue', [], tok.linea)

        # Bloque anónimo
        if tok.valor == '{':
            return self.bloque()

        # Declaración de variable o función
        if self.es_tipo_primitivo():
            return self._decl_tipo()

        # Asignación, ++/--, llamada
        if tok.tipo == 'IDENTIFICADOR':
            return self._asignacion_o_llamada()

        # Sentencia vacía
        if tok.valor == ';':
            self.consume()
            return None

        # Expresión suelta (ej: llamada a función como sentencia)
        e = self.expr()
        self.coincidir('DELIMITADOR', ';')
        return e

    # ── Auxiliares ────────────────────────────────────────────────────────────

    def _decl_tipo(self) -> Optional[Nodo]:
        """Parsea declaración de variable o función tras consumir el tipo."""
        tipo_tok = self.consume()

        # El nombre puede ser IDENTIFICADOR o PALABRA_CLAVE (ej: 'main')
        id_tok = self.peek()
        if id_tok is None or id_tok.tipo not in ('IDENTIFICADOR', 'PALABRA_CLAVE'):
            self.errores.append(
                f"Error sintáctico en línea {tipo_tok.linea}: "
                f"se esperaba identificador después de '{tipo_tok.valor}'"
            )
            self.coincidir('DELIMITADOR', ';')
            return None
        self.consume()

        if self.val_es('('):
            # Función o prototipo
            self.consume()
            params = self._params_func()
            self.esperar('DELIMITADOR', ')')
            if self.val_es(';'):
                self.consume()
                return Nodo(f"proto {tipo_tok.valor} {id_tok.valor}", params, tipo_tok.linea)
            cuerpo = self.bloque()
            return Nodo(f"func {tipo_tok.valor} {id_tok.valor}",
                        params + [cuerpo], tipo_tok.linea)

        return self._decl_variable_cont(tipo_tok, id_tok)

    def _decl_variable(self) -> Optional[Nodo]:
        """Alias de _decl_tipo() usado desde el init del for."""
        return self._decl_tipo()

    def _decl_variable_cont(self, tipo_tok: Token, id_tok: Token) -> Nodo:
        """Continúa una declaración de variable después de consumir tipo e id."""
        hijos = [Nodo(id_tok.valor, [], id_tok.linea)]

        if self.val_es('='):
            self.consume()
            hijos.append(self.expr())

        # Declaración múltiple: int a = 1, b, c = 3;
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
        """Parámetros formales de función: tipo id, tipo id, …"""
        params = []
        while self.hay_mas() and not self.val_es(')'):
            pt = self.consume()
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
        """Parsea sentencias que empiezan con IDENTIFICADOR."""
        tok = self.consume()

        # Asignación simple o compuesta
        if self.peek() and self.peek().tipo == 'OPERADOR_ASIG':
            op  = self.consume()
            val = self.expr()
            self.coincidir('DELIMITADOR', ';')
            return Nodo(f"asig {op.valor}",
                        [Nodo(tok.valor, [], tok.linea), val], tok.linea)

        # Post-incremento/decremento como sentencia
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

        # Acceso encadenado (. o []) antes de asignación: obj.a[0] = val;
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

        if self.peek() and self.peek().tipo == 'OPERADOR_ASIG':
            op  = self.consume()
            val = self.expr()
            self.coincidir('DELIMITADOR', ';')
            return Nodo(f"asig {op.valor}", [nodo_izq, val], tok.linea)

        self.coincidir('DELIMITADOR', ';')
        return nodo_izq

    # ── Punto de entrada ──────────────────────────────────────────────────────

    def parsear(self) -> Tuple[Nodo, List[str]]:
        """
        Parsea el programa completo y devuelve (nodo_raíz, errores).
        Si tras sentencia() el cursor no avanzó, descarta el token
        problemático para evitar un bucle infinito.
        """
        hijos = []
        while self.hay_mas():
            pos_antes = self.pos
            s = self.sentencia()
            if s:
                hijos.append(s)
            if self.pos == pos_antes and self.hay_mas():
                tok_stuck = self.peek()
                self.errores.append(
                    f"Error sintáctico en línea {tok_stuck.linea}: "
                    f"token inesperado '{tok_stuck.valor}' ({tok_stuck.tipo})"
                )
                self.consume()
        return Nodo('programa', hijos), self.errores


# ── Función pública ───────────────────────────────────────────────────────────

def analizar_sintactico(tokens: List[Token]) -> Tuple[Nodo, List[str]]:
    """Interfaz pública: recibe tokens completos y devuelve (AST, errores)."""
    return Parser(tokens).parsear()
