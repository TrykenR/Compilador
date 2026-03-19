"""
reglas.py — Patrones de expresiones regulares para cada tipo de token.

Define dos cosas:
  1. REGLAS: lista ordenada de pares (nombre, patrón_regex) que describe
     cómo luce cada tipo de token en el código fuente.
  2. PATRON_MAESTRO: una única expresión regular compilada que combina
     todas las reglas y se usa para recorrer el fuente de una sola pasada.
"""

# El módulo re de la biblioteca estándar provee el motor de expresiones
# regulares. No se necesita ninguna dependencia externa.
import re


# ─────────────────────────────────────────────
#  REGLAS (nombre_token, patrón_regex)
# ─────────────────────────────────────────────

# Cada entrada es una tupla (NOMBRE, patrón).
# NOMBRE se convierte en el nombre de grupo de captura (?P<NOMBRE>...)
# del patrón maestro; así, tras un match, match.lastgroup devuelve
# directamente el tipo de token sin lógica adicional.
REGLAS = [
    # ── Comentarios ──────────────────────────────────────────────────────────
    # Deben ir ANTES que el operador '/' para que "/* ... */" y "//"
    # no sean tokenizados como dos operadores de división separados.

    # Multilinea: captura todo entre /* y */ de forma no codiciosa (*?)
    # para que el primer */ cierre el comentario, no el último.
    # [\s\S] en lugar de . porque . no captura '\n' por defecto;
    # aunque usamos re.DOTALL, esta forma es más explícita y portátil.
    ('COMENTARIO_MULTILINEA', r'/\*[\s\S]*?\*/'),

    # Una línea: captura // y todo lo que sigue hasta (sin incluir) el '\n'.
    # [^\n]* es más seguro que .* porque el salto de línea lo contamos aparte.
    ('COMENTARIO_LINEA',      r'//[^\n]*'),

    # ── Literales de cadena ───────────────────────────────────────────────────
    # Soporta comillas dobles y simples, y secuencias de escape (\n, \", \\…).
    # Patrón: " [^"\\]* (\\. [^"\\]*)* "
    #   [^"\\]*   → cualquier carácter que no sea " ni \  (parte sin escape)
    #   \\.       → una barra invertida seguida de cualquier carácter (escape)
    #   el grupo (\\. [^"\\]*)* permite cero o más bloques "escape + texto"
    # Se repite la misma lógica para comillas simples con el operador |.
    ('LITERAL_CADENA',        r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\''),

    # ── Literales numéricos ───────────────────────────────────────────────────
    # Tres alternativas ordenadas de más a menos específica para evitar
    # que "3.14" sea reconocido como int "3", punto ".", int "14":
    #   1. Float con exponente:   1.5e-3  →  \d+\.\d+([eE][+\-]?\d+)?
    #   2. Int con exponente:     2e10    →  \d+[eE][+\-]?\d+
    #   3. Entero simple:         42      →  \d+
    ('LITERAL_NUMÉRICO',      r'\d+\.\d+([eE][+\-]?\d+)?|\d+[eE][+\-]?\d+|\d+'),

    # ── Operadores ────────────────────────────────────────────────────────────
    # Regla general: los operadores de DOS caracteres van siempre antes
    # que los de uno, porque si ++ llegara después de OPERADOR_ARITMÉTICO,
    # el '+' sería consumido primero y '++' nunca se reconocería completo.

    # ++ y -- (incremento / decremento), antes que + y -
    ('OPERADOR_INCREMENTO',   r'\+\+|--'),

    # Asignaciones simples y compuestas: =  +=  -=  *=  /=  %=  &=  |=  ^=
    # El grupo [+\-*/%&|^]? hace el prefijo opcional.
    # (?!=) es un lookahead negativo: evita que "==" sea consumido como "=" + "=".
    ('OPERADOR_ASIGNACIÓN',   r'[+\-*/%&|^]?=(?!=)'),

    # Operadores relacionales de dos caracteres (==, !=, <=, >=) antes que < y >
    ('OPERADOR_RELACIONAL',   r'==|!=|<=|>=|<|>'),

    # Operadores lógicos: && y || (dos caracteres) antes que sus variantes simples
    # \|\| necesita escapar | porque en regex | es el operador de alternancia
    ('OPERADOR_LÓGICO',       r'&&|\|\||!'),

    # Operadores aritméticos simples (un carácter cada uno)
    ('OPERADOR_ARITMÉTICO',   r'[+\-*/%]'),

    # Operadores a nivel de bit: & | ^ ~ << >>
    # Van después de && y || para no confundir & con && ni | con ||
    ('OPERADOR_BITWISE',      r'[&|^~]|<<|>>'),

    # ── Delimitadores ─────────────────────────────────────────────────────────
    # Caracteres de puntuación que estructuran el código sin ser operadores.
    # Se incluye el punto (.) para reconocer accesos a miembros: obj.campo
    ('DELIMITADOR',           r'[(){}\[\];,\.]'),

    # ── Espaciado ─────────────────────────────────────────────────────────────
    # Espacios y tabulaciones: se consumen y descartan; no producen token.
    # Los saltos de línea se tratan por separado para mantener el contador.
    ('SEPARADOR',             r'[ \t]+'),

    # Salto de línea en sus tres variantes:
    #   \n        → Unix / Linux / macOS moderno
    #   \r\n      → Windows  (debe ir ANTES que \r solo)
    #   \r        → Mac clásico (anterior a OS X)
    # El analizador léxico usa estos eventos para incrementar el número de línea
    # y luego los descarta; no generan token en la tabla de resultados.
    ('NUEVA_LÍNEA',           r'\n|\r\n|\r'),

    # ── Identificadores ───────────────────────────────────────────────────────
    # Empieza por letra o '_' (no puede comenzar con dígito).
    # Incluye letras acentuadas (á é í ó ú Á…) y ñ/Ñ/ü/Ü para permitir
    # identificadores escritos en español.
    # El léxico reclasifica este tipo a PALABRA_CLAVE, LITERAL_BOOLEANO
    # o LITERAL_NULO si el valor coincide con los conjuntos de tipos_token.py.
    ('IDENTIFICADOR',
     r'[a-zA-Z_áéíóúÁÉÍÓÚñÑüÜ][a-zA-Z0-9_áéíóúÁÉÍÓÚñÑüÜ]*'),

    # ── Comodín ───────────────────────────────────────────────────────────────
    # Captura cualquier carácter que no haya encajado con ninguna regla anterior.
    # El punto '.' con re.DOTALL captura incluso saltos de línea residuales.
    # El analizador lo registra como error léxico en lugar de ignorarlo.
    # SIEMPRE debe ser la última regla de la lista.
    ('DESCONOCIDO',           r'.'),
]


# ─────────────────────────────────────────────
#  PATRÓN MAESTRO (compilado una sola vez)
# ─────────────────────────────────────────────

# Se construye uniendo todas las reglas con | en una sola expresión regular.
# Cada regla se convierte en un grupo con nombre: (?P<NOMBRE>patrón)
# Ejemplo del resultado (simplificado):
#   (?P<COMENTARIO_MULTILINEA>/\*[\s\S]*?\*/)
#   |(?P<COMENTARIO_LINEA>//[^\n]*)
#   |(?P<LITERAL_CADENA>"[^"\\]*(?:\\.[^"\\]*)*"|...)
#   | ...
#
# re.MULTILINE — hace que ^ y $ reconozcan inicio/fin de cada línea,
#                no solo del string completo.
# re.DOTALL    — hace que '.' capture también '\n', necesario para que
#                DESCONOCIDO actúe como comodín total.
#
# Se compila UNA sola vez al importar el módulo; todas las llamadas
# posteriores reutilizan el mismo objeto compilado, evitando el coste
# de recompilar en cada análisis.
PATRON_MAESTRO = re.compile(
    '|'.join(f'(?P<{nombre}>{patron})' for nombre, patron in REGLAS),
    re.MULTILINE | re.DOTALL
)
