"""tipos_token.py — Clase Token y vocabulario del lenguaje."""

from dataclasses import dataclass
from typing import Optional  # noqa: F401  (disponible para extensiones)


# ── Vocabulario ───────────────────────────────────────────────────────────────

# Palabras reservadas; el léxico reclasifica IDENTIFICADOR → PALABRA_CLAVE.
PALABRAS_CLAVE = {
    'if', 'else', 'while', 'for', 'return',
    'int', 'float', 'string', 'bool', 'void',
    'class', 'def', 'import', 'print', 'include',
    'main', 'struct', 'switch', 'case', 'break',
    'continue', 'do', 'function', 'var', 'let', 'const',
    'char', 'double', 'long',          # FIX: faltaban en la lista original
}

# Reclasificados desde IDENTIFICADOR → LITERAL_BOOLEANO
LITERALES_BOOLEANOS = {'true', 'false', 'True', 'False'}

# Reclasificados desde IDENTIFICADOR → LITERAL_NULO
LITERALES_NULOS = {'null', 'None', 'nil'}

# Subconjunto usado por el parser para detectar inicio de declaración.
TIPOS_PRIMITIVOS = {'int', 'float', 'string', 'bool', 'void', 'char', 'double', 'long'}


# ── Token ─────────────────────────────────────────────────────────────────────

@dataclass
class Token:
    """Unidad léxica mínima: tipo, texto, posición en el fuente."""
    tipo:    str
    valor:   str
    linea:   int
    columna: int

    def __str__(self) -> str:
        # Formato tabular para reportes en consola.
        return (
            f"[Línea {self.linea:>3}, Col {self.columna:>3}]"
            f"  {self.tipo:<28} → '{self.valor}'"
        )

    def __repr__(self) -> str:
        return f"Token({self.tipo!r}, {self.valor!r}, L{self.linea}:C{self.columna})"
    