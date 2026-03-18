"""
analizador.py — Lógica principal del analizador léxico.

Recorre el código fuente usando el patrón maestro y produce:
  - Una lista de Token únicos (sin repeticiones por valor+tipo).
  - Un diccionario de frecuencias {(tipo, valor): cantidad}.
  - Una lista de mensajes de error léxico.
"""

from typing import Dict, List, Tuple

from tipos_token import Token, PALABRAS_CLAVE, LITERALES_BOOLEANOS, LITERALES_NULOS
from reglas      import PATRON_MAESTRO


# ─────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────

def analizar(
    codigo: str,
) -> Tuple[List[Token], Dict[Tuple[str, str], int], List[str]]:
    """
    Analiza el código fuente y devuelve:
      - tokens_unicos  : lista de Token sin duplicados (primera aparición).
      - frecuencias    : dict {(tipo, valor): cantidad de apariciones}.
      - errores        : lista de mensajes de error léxico.
    """
    tokens_unicos: List[Token]                    = []
    frecuencias:   Dict[Tuple[str, str], int]     = {}
    vistos:        set                            = set()   # claves (tipo, valor) ya registradas
    errores:       List[str]                      = []

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

        # ── Acumular frecuencia y registrar si es nuevo ────
        clave = (tipo, valor)
        frecuencias[clave] = frecuencias.get(clave, 0) + 1

        if clave not in vistos:
            vistos.add(clave)
            tokens_unicos.append(Token(tipo, valor, linea, col))

    return tokens_unicos, frecuencias, errores
