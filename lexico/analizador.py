from utilidades.manejo_de_buffers import FileReader
from lexico.tokens import KEYWORDS, OPERATORS, DELIMITERS

class Lexer:
    def __init__(self, file_path):
        self.reader = FileReader(file_path)

    def tokenize(self):
        tokens = []

        while True:
            char = self.reader.get_char()

            if char is None:
                break

            if char.isspace():
                continue

            # Identificadores
            if char.isalpha():
                current = char
                while True:
                    char = self.reader.get_char()
                    if char and (char.isalnum() or char == "_"):
                        current += char
                    else:
                        break

                if current in KEYWORDS:
                    tokens.append(("KEYWORD", current))
                else:
                    tokens.append(("IDENTIFIER", current))

            # Números
            elif char.isdigit():
                current = char
                while True:
                    char = self.reader.get_char()
                    if char and char.isdigit():
                        current += char
                    else:
                        break
                tokens.append(("NUMBER", current))

            # Operadores
            elif char in OPERATORS:
                tokens.append(("OPERATOR", char))

            # Delimitadores
            elif char in DELIMITERS:
                tokens.append(("DELIMITER", char))

            else:
                tokens.append(("UNKNOWN", char))

        return tokens
    