"""tipos_token.py — Clase Token y vocabulario del lenguaje Python."""

from dataclasses import dataclass

# ── Vocabulario Python ───────────────────────────────────────────────────────

# Palabras clave estructurales del lenguaje (control de flujo, definición, etc.)
# NOTA: True, False, None se clasifican como literales, no como palabras clave.
#       and, or, not se clasifican como OPERADOR_LOG (ya los captura reglas.py).
PALABRAS_CLAVE = {
    'as', 'assert', 'async', 'await', 'break',
    'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'finally',
    'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal',
    'pass', 'raise', 'return', 'try', 'while', 'with', 'yield',
}

LITERALES_BOOLEANOS = {'True', 'False'}
LITERALES_NULOS     = {'None'}

# Tipos primitivos usados en hints (para el semántico)
TIPOS_PRIMITIVOS = {'int', 'float', 'str', 'bool', 'list', 'dict', 'tuple', 'set', 'None'}

# Funciones y clases builtin de Python
BUILTINS = {
    # I/O
    'print', 'input',
    # Tipos / conversión
    'int', 'float', 'str', 'bool', 'bytes', 'bytearray',
    'list', 'tuple', 'set', 'frozenset', 'dict',
    'complex', 'memoryview',
    # Iteración y secuencias
    'range', 'enumerate', 'zip', 'map', 'filter', 'reversed', 'sorted',
    'iter', 'next', 'slice',
    # Numéricos y comparación
    'abs', 'divmod', 'pow', 'round', 'max', 'min', 'sum',
    # Introspección y atributos
    'type', 'isinstance', 'issubclass', 'id', 'hash', 'dir', 'vars',
    'getattr', 'setattr', 'delattr', 'hasattr', 'callable',
    # Objetos y clases
    'object', 'super', 'property', 'classmethod', 'staticmethod',
    # Cadenas y representación
    'repr', 'ascii', 'chr', 'ord', 'format', 'bin', 'oct', 'hex',
    # Colecciones y funcionales
    'len', 'any', 'all', 'open', 'eval', 'exec', 'compile',
    # Módulos e importación
    '__import__', 'globals', 'locals',
    # Errores comunes (usados como identificadores frecuentes)
    'Exception', 'ValueError', 'TypeError', 'KeyError', 'IndexError',
    'AttributeError', 'RuntimeError', 'StopIteration', 'NotImplementedError',
    'OSError', 'IOError', 'FileNotFoundError', 'PermissionError',
    'OverflowError', 'ZeroDivisionError', 'MemoryError', 'RecursionError',
    'AssertionError', 'ImportError', 'ModuleNotFoundError',
    'NameError', 'UnboundLocalError', 'SyntaxError', 'IndentationError',
    'UnicodeError', 'UnicodeDecodeError', 'UnicodeEncodeError',
    'GeneratorExit', 'SystemExit', 'KeyboardInterrupt',
    'BaseException', 'ArithmeticError', 'LookupError', 'BufferError',
    # Constantes builtin
    'NotImplemented', 'Ellipsis', '__debug__',
    # Misc
    'breakpoint', 'help', 'quit', 'exit',
}


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
    