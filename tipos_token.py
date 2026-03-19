"""
tipos_token.py — Definición de la clase Token y constantes del lenguaje.

Este módulo es la base de todo el compilador: define la unidad mínima
de información (Token) y los conjuntos de palabras reservadas que el
analizador léxico necesita para reclasificar identificadores.
"""

# dataclass genera automáticamente __init__, __eq__ y __hash__ a partir
# de los atributos declarados, evitando escribirlos a mano.
# field y Optional se importan por si se necesitan en extensiones futuras.
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────
#  VOCABULARIO DEL LENGUAJE
# ─────────────────────────────────────────────

# Palabras reservadas del lenguaje. El léxico las detecta primero como
# IDENTIFICADOR y luego las reclasifica a PALABRA_CLAVE si su valor
# aparece aquí. Se usa un set para que la búsqueda sea O(1).
PALABRAS_CLAVE = {
    'if', 'else', 'while', 'for', 'return',
    'int', 'float', 'string', 'bool', 'void',
    'class', 'def', 'import', 'print', 'include',
    'main', 'struct', 'switch', 'case', 'break',
    'continue', 'do', 'function', 'var', 'let', 'const'
}

# Literales booleanos
# Se reclasifican desde IDENTIFICADOR a LITERAL_BOOLEANO durante el análisis.
LITERALES_BOOLEANOS = {'true', 'false', 'True', 'False'}

# Representaciones del valor nulo
# Se reclasifican desde IDENTIFICADOR a LITERAL_NULO durante el análisis.
LITERALES_NULOS = {'null', 'None', 'nil'}

# Subconjunto de PALABRAS_CLAVE que el parser trata como inicio de una
# declaración de variable o función (ej: "int x = 5;", "void f() { }").
# Definirlo aquí garantiza que léxico y parser compartan la misma lista.
TIPOS_PRIMITIVOS = {'int', 'float', 'string', 'bool', 'void', 'char', 'double', 'long'}


# ─────────────────────────────────────────────
#  CLASE TOKEN
# ─────────────────────────────────────────────

@dataclass
class Token:
    """
    Unidad léxica mínima del código fuente.

    Cada vez que el analizador léxico reconoce una secuencia de caracteres
    con significado (palabra, número, operador, delimitador…) crea un Token
    con estos cuatro campos:

        tipo    — categoría semántica asignada por el léxico
        valor   — texto exacto tal como aparece en el fuente
        linea   — número de línea donde empieza el token
        columna — posición horizontal dentro de esa línea
    """
    tipo:    str
    valor:   str
    linea:   int
    columna: int

    def __str__(self):
        """
        Formato tabular legible para reportes en consola.

        Ejemplo de salida:
            [Línea   3, Col   5]  PALABRA_CLAVE              → 'int'

        :>3 alinea los números a la derecha en 3 dígitos.
        :<28 alinea el tipo a la izquierda en 28 caracteres,
        de modo que la flecha → siempre queda en la misma columna.
        """
        return (
            f"[Línea {self.linea:>3}, Col {self.columna:>3}]"
            f"  {self.tipo:<28} → '{self.valor}'"
        )

    def __repr__(self):
        """
        Representación compacta para depuración (aparece en trazas y logs).

        Ejemplo: Token('IDENTIFICADOR', 'resultado', L7:C5)

        !r rodea las cadenas con comillas, distinguiendo valores numéricos
        de cadenas de texto en la salida del intérprete.
        """
        return f"Token({self.tipo!r}, {self.valor!r}, L{self.linea}:C{self.columna})"
    