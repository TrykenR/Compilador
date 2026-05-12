"""analizador.py — Analizador léxico adaptado a Python."""

from typing import Dict, List, Tuple

from tipos_token import Token, PALABRAS_CLAVE, LITERALES_BOOLEANOS, LITERALES_NULOS, BUILTINS
from reglas import PATRON_MAESTRO

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


def _contar_saltos(texto: str) -> int:
    """
    Cuenta saltos de línea en un bloque de texto (ej: comentario multilinea).
    Normaliza \r\n y \r antes de contar para evitar doble conteo.
    """
    return texto.replace('\r\n', '\n').replace('\r', '\n').count('\n')


def _clasificar_identificador(valor: str) -> str:
    """
    Dado el texto de un IDENTIFICADOR, devuelve el tipo correcto.
    Orden de precedencia:
      1. Literales booleanos  (True, False)
      2. Literales nulos      (None)
      3. Palabras clave       (if, def, class, return, …)
      4. Operadores lógicos   (and, or, not) — ya capturados por regex,
         pero por si acaso llegan como IDENTIFICADOR
      5. Builtins             (print, len, range, …)
      6. IDENTIFICADOR        (cualquier otro nombre)
    """
    if valor in LITERALES_BOOLEANOS:
        return 'LITERAL_BOOLEANO'
    if valor in LITERALES_NULOS:
        return 'LITERAL_NULO'
    if valor in PALABRAS_CLAVE:
        return 'PALABRA_CLAVE'
    if valor in {'and', 'or', 'not'}:
        return 'OPERADOR_LOG'
    if valor in BUILTINS:
        return 'BUILTIN'
    return 'IDENTIFICADOR'


# ── analizar() ────────────────────────────────────────────────────────────────

def analizar(
    codigo: str,
) -> Tuple[List[Token], Dict[Tuple[str, str], int], List[str]]:
    """
    Analiza léxicamente el código y devuelve:
      tokens_unicos — lista de Token sin duplicados (primera aparición).
      frecuencias   — {(tipo, valor): cantidad} de cada token en el fuente.
      errores       — mensajes de error léxico.
    """
    tokens_unicos: List[Token]                = []
    frecuencias:   Dict[Tuple[str, str], int] = {}
    vistos:        set                         = set()
    errores:       List[str]                   = []

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
            linea += _contar_saltos(valor)
            if '\n' in valor or '\r' in valor:
                ultimo = max(valor.rfind('\n'), valor.rfind('\r'))
                inicio_linea = match.start() + ultimo + 1
            continue

        tipo = _normalizar_tipo(tipo)

        if tipo == 'IDENTIFICADOR':
            tipo = _clasificar_identificador(valor)

        if tipo == 'DESCONOCIDO':
            char_repr = repr(valor) if not valor.isprintable() else f"'{valor}'"
            errores.append(
                f"⚠  Error léxico en línea {linea}, col {col}: "
                f"carácter inesperado {char_repr}"
            )

        clave = (tipo, valor)
        frecuencias[clave] = frecuencias.get(clave, 0) + 1

        if clave not in vistos:
            vistos.add(clave)
            tokens_unicos.append(Token(tipo, valor, linea, col))

    return tokens_unicos, frecuencias, errores


# ── analizar_completo() ───────────────────────────────────────────────────────

def analizar_completo(codigo: str) -> Tuple[List[Token], List[str]]:
    """
    Igual que analizar() pero devuelve TODOS los tokens en orden, incluidas
    las repeticiones. El parser sintáctico necesita la secuencia completa.
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
            linea += _contar_saltos(valor)
            if '\n' in valor or '\r' in valor:
                ultimo = max(valor.rfind('\n'), valor.rfind('\r'))
                inicio_linea = match.start() + ultimo + 1
            continue

        tipo = _normalizar_tipo(tipo)

        if tipo == 'IDENTIFICADOR':
            tipo = _clasificar_identificador(valor)

        if tipo == 'DESCONOCIDO':
            char_repr = repr(valor) if not valor.isprintable() else f"'{valor}'"
            errores.append(
                f"⚠  Error léxico en línea {linea}, col {col}: "
                f"carácter inesperado {char_repr}"
            )

        tokens.append(Token(tipo, valor, linea, col))

    return tokens, errores
