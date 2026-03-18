"""
token.py — Definición de la clase Token y constantes del lenguaje.

Categorías según el material de Compiladores
(Robert Damian Quintero Laverde):
  IDENTIFICADOR, LITERAL_*, OPERADOR_*, PALABRA_CLAVE,
  DELIMITADOR, SEPARADOR, COMENTARIO, DESCONOCIDO
"""

from dataclasses import dataclass


# ─────────────────────────────────────────────
#  VOCABULARIO DEL LENGUAJE
# ─────────────────────────────────────────────

PALABRAS_CLAVE = {
    'if', 'else', 'while', 'for', 'return',
    'int', 'float', 'string', 'bool', 'void',
    'class', 'def', 'import', 'print', 'include',
    'main', 'struct', 'switch', 'case', 'break',
    'continue', 'do', 'function', 'var', 'let', 'const'
}

LITERALES_BOOLEANOS = {'true', 'false', 'True', 'False'}
LITERALES_NULOS     = {'null', 'None', 'nil'}


# ─────────────────────────────────────────────
#  CLASE TOKEN
# ─────────────────────────────────────────────

@dataclass
class Token:
    tipo: str
    valor: str
    linea: int
    columna: int

    def __str__(self):
        return (
            f"[Línea {self.linea:>3}, Col {self.columna:>3}]"
            f"  {self.tipo:<28} → '{self.valor}'"
        )
