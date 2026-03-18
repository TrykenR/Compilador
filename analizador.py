"""
analizador.py — Lógica principal del analizador léxico.

Recorre el código fuente usando el patrón maestro y produce
una lista de Token, reclasificando identificadores que resulten
ser palabras clave, literales booleanos o literales nulos.
"""

from typing import List, Tuple

from tipos_token import Token, PALABRAS_CLAVE, LITERALES_BOOLEANOS, LITERALES_NULOS
from reglas  import PATRON_MAESTRO


# ─────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────

def analizar(codigo: str) -> Tuple[List[Token], List[str]]:
    """
    Analiza el código fuente y devuelve:
      - lista de Token reconocidos
      - lista de mensajes de error léxico
    """
    tokens:  List[Token] = []
    errores: List[str]   = []
    linea        = 1
    inicio_linea = 0

    for match in PATRON_MAESTRO.finditer(codigo):
        tipo  = match.lastgroup
        valor = match.group()
        col   = match.start() - inicio_linea + 1

        # ── Actualizar contador de líneas ──────────────────
        if tipo == 'NUEVA_LÍNEA':
            linea += 1
            inicio_linea = match.end()
            continue

        # ── Descartar espacios y tabulaciones ──────────────
        if tipo == 'SEPARADOR':
            continue

        # ── Descartar comentarios (contar sus saltos) ──────
        if tipo in ('COMENTARIO_LINEA', 'COMENTARIO_MULTILINEA'):
            linea += valor.count('\n')
            continue

        # ── Reclasificar identificadores ───────────────────
        if tipo == 'IDENTIFICADOR':
            if valor in PALABRAS_CLAVE:
                tipo = 'PALABRA_CLAVE'
            elif valor in LITERALES_BOOLEANOS:
                tipo = 'LITERAL_BOOLEANO'
            elif valor in LITERALES_NULOS:
                tipo = 'LITERAL_NULO'

        # ── Registrar error para caracteres desconocidos ───
        if tipo == 'DESCONOCIDO':
            errores.append(
                f"⚠  Error léxico en línea {linea}, col {col}: "
                f"carácter inesperado '{valor}'"
            )

        tokens.append(Token(tipo, valor, linea, col))

    return tokens, errores
