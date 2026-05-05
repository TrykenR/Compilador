"""reglas.py — Patrones regex para cada tipo de token y patrón maestro compilado."""

import re

# ── Reglas (nombre, patrón) ───────────────────────────────────────────────────
# El orden importa: los patrones más específicos/largos deben ir ANTES
# que los más cortos que compartan prefijo (ej: /* antes de /, ++ antes de +).

REGLAS = [
    # Comentarios — deben preceder al operador '/' para no fragmentarlo.
    ('COMENTARIO_MULTILINEA', r'/\*[\s\S]*?\*/'),   # /* ... */  (no codicioso)
    ('COMENTARIO_LINEA',      r'//[^\n]*'),          # // hasta fin de línea

    # Cadenas con soporte de secuencias de escape (\n, \", \\, …)
    ('LITERAL_CADENA',
     r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\''),

    # Números: float+exp > int+exp > float > int  (de más a menos específico)
    ('LITERAL_NUMÉRICO',
     r'\d+\.\d+([eE][+\-]?\d+)?|\d+[eE][+\-]?\d+|\d+'),

    # ++ y -- antes que + y - para evitar tokenizar ++ como dos '+'
    ('OPERADOR_INCREMENTO',   r'\+\+|--'),

    # Asignaciones simples y compuestas (=, +=, -=, …); lookahead evita confundir con ==
    ('OPERADOR_ASIGNACIÓN',   r'[+\-*/%&|^]?=(?!=)'),

    # Relacionales de dos caracteres antes que < y >
    ('OPERADOR_RELACIONAL',   r'==|!=|<=|>=|<|>'),

    # Lógicos: && y || antes que & y |
    ('OPERADOR_LÓGICO',       r'&&|\|\||!'),

    ('OPERADOR_ARITMÉTICO',   r'[+\-*/%]'),

    # Bitwise después de && / || para no confundir & con && ni | con ||
    ('OPERADOR_BITWISE',      r'[&|^~]|<<|>>'),

    # Delimitadores de puntuación (incluye '.' para acceso a miembro)
    ('DELIMITADOR',           r'[(){}\[\];,\.]'),

    # Espacios y tabulaciones: se descartan sin generar token
    ('SEPARADOR',             r'[ \t]+'),

    # Saltos de línea: \r\n antes de \r (Windows primero)
    ('NUEVA_LÍNEA',           r'\n|\r\n|\r'),

    # Identificadores: letra/_ inicial, luego alfanumérico/_; admite tildes y ñ
    ('IDENTIFICADOR',
     r'[a-zA-Z_áéíóúÁÉÍÓÚñÑüÜ][a-zA-Z0-9_áéíóúÁÉÍÓÚñÑüÜ]*'),

    # Comodín — captura cualquier carácter no reconocido; SIEMPRE al final
    ('DESCONOCIDO', r'.'),
]

# ── Patrón maestro (compilado una sola vez al importar) ───────────────────────
# Cada regla se convierte en un grupo con nombre: (?P<NOMBRE>patrón)
# re.MULTILINE → ^ y $ reconocen inicio/fin de cada línea.
# re.DOTALL    → '.' captura '\n', necesario para el comodín.
PATRON_MAESTRO = re.compile(
    '|'.join(f'(?P<{nombre}>{patron})' for nombre, patron in REGLAS),
    re.MULTILINE | re.DOTALL,
)
