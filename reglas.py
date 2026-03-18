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
    # Comentarios
    ('COMENTARIO_MULTILINEA', r'/\*[\s\S]*?\*/'),
    ('COMENTARIO_LINEA',      r'//[^\n]*'),

    # Literales de cadena
    ('LITERAL_CADENA',        r'"[^"]*"|\'[^\']*\''),

    # Literales numéricos  (float antes que int)
    ('LITERAL_NUMÉRICO',      r'\d+\.\d+|\d+'),

    # Operadores — multicarácter antes que simple
    ('OPERADOR_ASIGNACIÓN',   r'[+\-*/%]?=(?!=)'),   # =  +=  -=  *=  /=
    ('OPERADOR_RELACIONAL',   r'==|!=|<=|>=|<|>'),
    ('OPERADOR_LÓGICO',       r'&&|\|\||!'),
    ('OPERADOR_ARITMÉTICO',   r'[+\-*/%]'),

    # Delimitadores
    ('DELIMITADOR',           r'[(){}\[\];,]'),

    # Separadores (espacios y tabulaciones)
    ('SEPARADOR',             r'[ \t]+'),

    # Salto de línea (solo para contar líneas)
    ('NUEVA_LÍNEA',           r'\n'),

    # Identificadores / palabras clave / booleanos / nulos
    ('IDENTIFICADOR',
     r'[a-zA-Z_áéíóúÁÉÍÓÚñÑ][a-zA-Z0-9_áéíóúÁÉÍÓÚñÑ]*'),

    # Cualquier carácter no reconocido
    ('DESCONOCIDO',           r'.'),
]


# ─────────────────────────────────────────────
#  PATRÓN MAESTRO (compilado una sola vez)
# ─────────────────────────────────────────────

PATRON_MAESTRO = re.compile(
    '|'.join(f'(?P<{nombre}>{patron})' for nombre, patron in REGLAS),
    re.MULTILINE
)
