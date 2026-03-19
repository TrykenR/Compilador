"""
analizador.py — Lógica principal del analizador léxico.

Recorre el código fuente usando el patrón maestro y produce:
  - Una lista de Token únicos (sin repeticiones por valor+tipo).
  - Un diccionario de frecuencias {(tipo, valor): cantidad}.
  - Una lista de mensajes de error léxico.

Correcciones aplicadas:
  - Nombres de tipo normalizados (LITERAL_BOOLEANO, OPERADOR_ASIG, etc.)
  - Soporte para nuevos tipos de operadores (OPERADOR_INCREMENTO, OPERADOR_BITWISE)
  - Manejo correcto de saltos de línea Windows (\r\n) y Mac clásico (\r)
"""

from typing import Dict, List, Tuple

from tipos_token import Token, PALABRAS_CLAVE, LITERALES_BOOLEANOS, LITERALES_NULOS
from reglas      import PATRON_MAESTRO


# ─────────────────────────────────────────────
#  NORMALIZACIÓN DE NOMBRES DE TIPO
#  (garantiza coherencia entre léxico e interfaz)
# ─────────────────────────────────────────────

# Mapa interno → nombre canónico expuesto al resto del sistema
_NORMALIZAR = {
    'OPERADOR_ASIGNACIÓN': 'OPERADOR_ASIG',
    'OPERADOR_RELACIONAL': 'OPERADOR_REL',
    'OPERADOR_LÓGICO':     'OPERADOR_LOG',
    'OPERADOR_ARITMÉTICO': 'OPERADOR_ARIT',
    'OPERADOR_INCREMENTO': 'OPERADOR_INCR',
    'OPERADOR_BITWISE':    'OPERADOR_BIT',
    'LITERAL_NUMÉRICO':    'LITERAL_NUM',
}


def _normalizar_tipo(tipo: str) -> str:
    return _NORMALIZAR.get(tipo, tipo)


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
    tokens_unicos: List[Token]                = []
    frecuencias:   Dict[Tuple[str, str], int] = {}
    vistos:        set                        = set()
    errores:       List[str]                  = []

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
            lineas_en_comentario = valor.count('\n') + valor.count('\r\n') + valor.count('\r')
            linea += lineas_en_comentario
            # Actualizar inicio_linea si el comentario termina con salto
            if '\n' in valor or '\r' in valor:
                ultimo_salto = max(
                    valor.rfind('\n'),
                    valor.rfind('\r')
                )
                inicio_linea = match.start() + ultimo_salto + 1
            continue

        # ── Normalizar nombre de tipo ──────────────────────
        tipo = _normalizar_tipo(tipo)

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
            # Solo reportar si el carácter es imprimible y no es espacio raro
            char_repr = repr(valor) if not valor.isprintable() else f"'{valor}'"
            errores.append(
                f"⚠  Error léxico en línea {linea}, col {col}: "
                f"carácter inesperado {char_repr}"
            )

        # ── Acumular frecuencia y registrar si es nuevo ────
        clave = (tipo, valor)
        frecuencias[clave] = frecuencias.get(clave, 0) + 1

        if clave not in vistos:
            vistos.add(clave)
            tokens_unicos.append(Token(tipo, valor, linea, col))

    return tokens_unicos, frecuencias, errores


# ─────────────────────────────────────────────
#  TOKENIZAR SIN DEDUPLICAR (para el parser)
# ─────────────────────────────────────────────

def analizar_completo(codigo: str) -> Tuple[List[Token], List[str]]:
    """
    Versión del léxico que retorna TODOS los tokens (con repetidos),
    necesaria para el analizador sintáctico.

    Retorna (tokens_completos, errores_lexicos).
    """
    tokens: List[Token] = []
    errores: List[str]  = []

    linea        = 1
    inicio_linea = 0

    for match in PATRON_MAESTRO.finditer(codigo):
        tipo  = match.lastgroup
        valor = match.group()
        col   = match.start() - inicio_linea + 1

        if tipo == 'NUEVA_LÍNEA':
            linea += 1
            inicio_linea = match.end()
            continue

        if tipo == 'SEPARADOR':
            continue

        if tipo in ('COMENTARIO_LINEA', 'COMENTARIO_MULTILINEA'):
            lineas_en_comentario = valor.count('\n')
            linea += lineas_en_comentario
            if '\n' in valor:
                inicio_linea = match.start() + valor.rfind('\n') + 1
            continue

        # Normalizar
        tipo = _normalizar_tipo(tipo)

        if tipo == 'IDENTIFICADOR':
            if valor in PALABRAS_CLAVE:
                tipo = 'PALABRA_CLAVE'
            elif valor in LITERALES_BOOLEANOS:
                tipo = 'LITERAL_BOOLEANO'
            elif valor in LITERALES_NULOS:
                tipo = 'LITERAL_NULO'

        if tipo == 'DESCONOCIDO':
            char_repr = repr(valor) if not valor.isprintable() else f"'{valor}'"
            errores.append(
                f"⚠  Error léxico en línea {linea}, col {col}: "
                f"carácter inesperado {char_repr}"
            )

        tokens.append(Token(tipo, valor, linea, col))

    return tokens, errores
