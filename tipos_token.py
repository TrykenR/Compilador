"""tipos_token.py — Clase Token y vocabulario del lenguaje Python."""

from dataclasses import dataclass
from typing import Optional

# ── Vocabulario Python ───────────────────────────────────────────────────────

PALABRAS_CLAVE = {
    'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break',
    'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'finally',
    'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal',
    'not', 'or', 'pass', 'raise', 'return', 'try', 'while', 'with', 'yield'
}

LITERALES_BOOLEANOS = {'True', 'False', 'true', 'false'}
LITERALES_NULOS = {'None', 'null', 'nil'}

# Tipos comunes usados en hints y declaraciones (para semántico)
TIPOS_PRIMITIVOS = {'int', 'float', 'str', 'bool', 'list', 'dict', 'tuple', 'set', 'None'}


@dataclass
class Token:
    """Unidad léxica mínima: tipo, texto, posición en el fuente."""
    tipo:    str
    valor:   str
    linea:   int
    columna: int

    def __str__(self) -> str:
        return f"[Línea {self.linea:>3}, Col {self.columna:>3}]  {self.tipo:<28} → '{self.valor}'"

    def __repr__(self) -> str:
        return f"Token({self.tipo!r}, {self.valor!r}, L{self.linea}:C{self.columna})"
    