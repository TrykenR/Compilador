"""
reglas.py — Patrones de expresiones regulares para cada tipo de token.

El orden de REGLAS es importante: los patrones más específicos
deben aparecer antes que los más generales para que el motor
de expresiones regulares les dé prioridad.
"""

import re


# ─────────────────────────────────────────────
#  REGLAS (nombre_token, patrón_regex)
# ─────────────────────────────────────────────

REGLAS = [
    # Comentarios (antes que operadores para evitar confusión con '/')
    ('COMENTARIO_MULTILINEA', r'/\*[\s\S]*?\*/'),
    ('COMENTARIO_LINEA',      r'//[^\n]*'),

    # Literales de cadena — soporta secuencias de escape (\n, \", etc.)
    ('LITERAL_CADENA',        r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\''),

    # Literales numéricos (float antes que int para evitar match parcial)
    ('LITERAL_NUMÉRICO',      r'\d+\.\d+([eE][+\-]?\d+)?|\d+[eE][+\-]?\d+|\d+'),

    # Operadores multicarácter ANTES que los de un solo carácter
    ('OPERADOR_INCREMENTO',   r'\+\+|--'),           # ++ y -- antes que + y -
    ('OPERADOR_ASIGNACIÓN',   r'[+\-*/%&|^]?=(?!=)'), # += -= *= /= %= &= |= ^= =
    ('OPERADOR_RELACIONAL',   r'==|!=|<=|>=|<|>'),
    ('OPERADOR_LÓGICO',       r'&&|\|\||!'),
    ('OPERADOR_ARITMÉTICO',   r'[+\-*/%]'),
    ('OPERADOR_BITWISE',      r'[&|^~]|<<|>>'),

    # Delimitadores (incluye punto para acceso a miembros)
    ('DELIMITADOR',           r'[(){}\[\];,\.]'),

    # Separadores (espacios y tabulaciones — NO saltos de línea)
    ('SEPARADOR',             r'[ \t]+'),

    # Salto de línea (solo para contar líneas, se descarta después)
    ('NUEVA_LÍNEA',           r'\n|\r\n|\r'),

    # Identificadores / palabras clave / booleanos / nulos
    # Soporta letras acentuadas y ñ para identificadores en español
    ('IDENTIFICADOR',
     r'[a-zA-Z_áéíóúÁÉÍÓÚñÑüÜ][a-zA-Z0-9_áéíóúÁÉÍÓÚñÑüÜ]*'),

    # Cualquier carácter no reconocido (siempre al final)
    ('DESCONOCIDO',           r'.'),
]


# ─────────────────────────────────────────────
#  PATRÓN MAESTRO (compilado una sola vez)
# ─────────────────────────────────────────────

PATRON_MAESTRO = re.compile(
    '|'.join(f'(?P<{nombre}>{patron})' for nombre, patron in REGLAS),
    re.MULTILINE | re.DOTALL
)
