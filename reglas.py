"""reglas.py — Patrones regex para Python."""

import re

REGLAS = [
    # Comentarios Python: # hasta fin de línea
    ('COMENTARIO_LINEA',      r'#[^\n]*'),

    # Cadenas: soporta "simple", 'simple', """triple""", '''triple'''
    ('LITERAL_CADENA',
     r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\''),

    # Números Python (int, float, bin, oct, hex, complex, con _)
    ('LITERAL_NUMÉRICO',
     r'0[bB][01_]+|0[oO][0-7_]+|0[xX][0-9a-fA-F_]+|\d[\d_]*\.\d[\d_]*([eE][+\-]?\d+)?'
     r'|\d[\d_]*[eE][+\-]?\d+|\d[\d_]*[jJ]|\d[\d_]*'),

    # Operadores de dos caracteres (de más específico a menos)
    ('OPERADOR_INCREMENTO',   r'\+\+|--|\*\*|//'),
    ('OPERADOR_ASIGNACIÓN',   r'//=| \*\*=|<<=|>>=|&=|\|=|\^=|\+=|-=|\*=|/=|%=|@=|='),
    ('OPERADOR_RELACIONAL',   r'==|!=|<=|>=|<>|<|>'),
    ('OPERADOR_LÓGICO',       r'&&|\|\||and|or|not'),
    ('OPERADOR_ARITMÉTICO',   r'[+\-*/%]|@'),
    ('OPERADOR_BITWISE',      r'[&|^~]|<<|>>'),

    # Delimitadores (incluye : para bloques Python)
    ('DELIMITADOR',           r'[(){}\[\];,:.]'),

    # Espacios y tabulaciones (se descartan)
    ('SEPARADOR',             r'[ \t]+'),

    # Saltos de línea
    ('NUEVA_LÍNEA',           r'\n|\r\n|\r'),

    # Identificadores (admite Unicode)
    ('IDENTIFICADOR',
     r'[a-zA-Z_áéíóúÁÉÍÓÚñÑüÜ][a-zA-Z0-9_áéíóúÁÉÍÓÚñÑüÜ]*'),

    # Comodín
    ('DESCONOCIDO', r'.'),
]

PATRON_MAESTRO = re.compile(
    '|'.join(f'(?P<{nombre}>{patron})' for nombre, patron in REGLAS),
    re.MULTILINE | re.DOTALL,
)
