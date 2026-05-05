"""analizador.py — Analizador léxico adaptado a Python."""

from typing import Dict, List, Tuple

from tipos_token import Token, PALABRAS_CLAVE, LITERALES_BOOLEANOS, LITERALES_NULOS
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
    FIX: la versión original sumaba \n + \r\n + \r por separado, lo que
    hacía que \r\n contara doble (\r\n aparece en count('\n') Y count('\r\n')).
    Ahora se normaliza primero y se cuenta una sola vez.
    """
    return texto.replace('\r\n', '\n').replace('\r', '\n').count('\n')


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
    inicio_linea = 0   # posición absoluta del inicio de la línea actual

    for match in PATRON_MAESTRO.finditer(codigo):
        tipo  = match.lastgroup
        valor = match.group()
        col   = match.start() - inicio_linea + 1

        # Salto de línea: actualizar contadores y descartar
        if tipo == 'NUEVA_LÍNEA':
            linea += 1
            inicio_linea = match.end()
            continue

        # Espacios/tabulaciones: descartar
        if tipo == 'SEPARADOR':
            continue

        # Comentarios: contar sus saltos internos y descartar
        if tipo in ('COMENTARIO_LINEA', 'COMENTARIO_MULTILINEA'):
            linea += _contar_saltos(valor)
            if '\n' in valor or '\r' in valor:
                # Mover inicio_linea al carácter tras el último salto del comentario
                ultimo = max(valor.rfind('\n'), valor.rfind('\r'))
                inicio_linea = match.start() + ultimo + 1
            continue

        tipo = _normalizar_tipo(tipo)

        # Reclasificar identificadores que son palabras reservadas
        if tipo == 'IDENTIFICADOR':
            if valor in PALABRAS_CLAVE:
                tipo = 'PALABRA_CLAVE'
            elif valor in LITERALES_BOOLEANOS:
                tipo = 'LITERAL_BOOLEANO'
            elif valor in LITERALES_NULOS:
                tipo = 'LITERAL_NULO'

        # Registrar error léxico por carácter no reconocido
        if tipo == 'DESCONOCIDO':
            char_repr = repr(valor) if not valor.isprintable() else f"'{valor}'"
            errores.append(
                f"⚠  Error léxico en línea {linea}, col {col}: "
                f"carácter inesperado {char_repr}"
            )

        clave = (tipo, valor)
        frecuencias[clave] = frecuencias.get(clave, 0) + 1

        # Solo añadir a tokens_unicos la primera vez que se ve este par (tipo, valor)
        if clave not in vistos:
            vistos.add(clave)
            tokens_unicos.append(Token(tipo, valor, linea, col))

    return tokens_unicos, frecuencias, errores


# ── analizar_completo() ───────────────────────────────────────────────────────

def analizar_completo(codigo: str) -> Tuple[List[Token], List[str]]:
    """
    Igual que analizar() pero devuelve TODOS los tokens en orden, incluidas
    las repeticiones. El parser sintáctico necesita la secuencia completa.
    Devuelve (tokens_completos, errores_lexicos).
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
            linea += _contar_saltos(valor)   # FIX: igual que en analizar()
            if '\n' in valor or '\r' in valor:
                ultimo = max(valor.rfind('\n'), valor.rfind('\r'))
                inicio_linea = match.start() + ultimo + 1
            continue

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

        # A diferencia de analizar(), aquí se guardan TODOS los tokens
        tokens.append(Token(tipo, valor, linea, col))

    return tokens, errores
