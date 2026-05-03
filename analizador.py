"""
analizador.py — Lógica principal del analizador léxico.

Es el módulo que "lee" el código fuente carácter a carácter (en realidad
token a token mediante regex) y produce tres resultados:
  - tokens_unicos : lista de Token sin duplicados, en orden de aparición.
  - frecuencias   : cuántas veces aparece cada (tipo, valor) en el fuente.
  - errores       : mensajes de error por caracteres no reconocidos.

Expone dos funciones públicas:
  analizar()          → para la interfaz gráfica (tokens únicos + frecuencias)
  analizar_completo() → para el parser sintáctico (todos los tokens, con repetidos)
"""

from typing import Dict, List, Tuple

# Token      → clase que almacena tipo, valor, línea y columna
# conjuntos  → usados para reclasificar IDENTIFICADOR al tipo correcto
from tipos_token import Token, PALABRAS_CLAVE, LITERALES_BOOLEANOS, LITERALES_NULOS

# PATRON_MAESTRO es la expresión regular compilada que reconoce todos
# los tipos de token en una sola pasada sobre el código fuente.
from reglas import PATRON_MAESTRO


# ─────────────────────────────────────────────
#  NORMALIZACIÓN DE NOMBRES DE TIPO
# ─────────────────────────────────────────────

# Los nombres de grupo en reglas.py usan tildes y nombres largos porque
# son válidos en Python, pero la interfaz gráfica y el parser esperan
# nombres cortos y sin tildes para usarlos como claves de diccionario y
# tags de Tkinter. Este mapa hace la traducción en un único lugar.
#
# Ejemplo: 'OPERADOR_ASIGNACIÓN' → 'OPERADOR_ASIG'
#          'LITERAL_NUMÉRICO'    → 'LITERAL_NUM'
_NORMALIZAR = {
    'OPERADOR_ASIGNACIÓN': 'OPERADOR_ASIG',
    'OPERADOR_RELACIONAL': 'OPERADOR_REL',
    'OPERADOR_LÓGICO':     'OPERADOR_LOG',
    'OPERADOR_ARITMÉTICO': 'OPERADOR_ARIT',
    'OPERADOR_INCREMENTO': 'OPERADOR_INCR',
    'OPERADOR_BITWISE':    'OPERADOR_BIT',
    'LITERAL_NUMÉRICO':    'LITERAL_NUM',
}


def _normalizar_tipo(tipo: str) -> str:
    """
    Traduce el nombre de tipo interno (con tildes, largo) al nombre
    canónico que usan la interfaz y el parser.

    Si el tipo no está en el mapa de traducción lo devuelve sin cambios,
    de modo que tipos como 'IDENTIFICADOR' o 'DELIMITADOR' pasan intactos.
    """
    return _NORMALIZAR.get(tipo, tipo)


# ─────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────

def analizar(
    codigo: str,
) -> Tuple[List[Token], Dict[Tuple[str, str], int], List[str]]:
    """
    Analiza léxicamente el código fuente y devuelve tres estructuras:

      tokens_unicos — lista de Token sin duplicados (se guarda solo la
                      primera aparición de cada par tipo+valor).
                      Usada por la interfaz para mostrar la tabla de tokens.

      frecuencias   — diccionario {(tipo, valor): cantidad} que cuenta
                      cuántas veces aparece cada token en el fuente.
                      La clave es una tupla, no un string, para evitar
                      colisiones entre tokens con el mismo valor pero
                      distinto tipo (ej: 'int' como PALABRA_CLAVE vs IDENTIFICADOR).

      errores       — lista de strings con mensajes de error léxico
    """
    tokens_unicos: List[Token]                = []
    frecuencias:   Dict[Tuple[str, str], int] = {}

    # Set auxiliar de claves (tipo, valor) ya registradas.
    # Permite comprobar duplicados en O(1) sin recorrer tokens_unicos.
    vistos: set    = set()
    errores: List[str] = []

    # linea e inicio_linea se actualizan cada vez que se detecta un
    # salto de línea, para calcular la columna de cada token.
    linea        = 1
    inicio_linea = 0   # posición absoluta (en el string) del inicio de la línea actual

    # finditer recorre el código de izquierda a derecha
    # En cada iteración, match corresponde al siguiente token encontrado
    for match in PATRON_MAESTRO.finditer(codigo):
        tipo  = match.lastgroup          # nombre del grupo de captura que encajó
        valor = match.group()            # texto exacto del token en el fuente
        col   = match.start() - inicio_linea + 1  # columna (base 1)

        # ── Actualizar contador de líneas ──────────────────────────────────
        # NUEVA_LÍNEA no genera token; solo avanza el contador y mueve
        # inicio_linea al primer carácter de la línea siguiente.
        if tipo == 'NUEVA_LÍNEA':
            linea += 1
            inicio_linea = match.end()
            continue

        # ── Descartar espacios y tabulaciones ─────────────────────────────
        # Los separadores no aportan información semántica; se descartan.
        if tipo == 'SEPARADOR':
            continue

        # ── Descartar comentarios contando sus saltos de línea ────────────
        # Los comentarios no generan token, pero pueden ocupar varias líneas
        # (especialmente los multilinea), así que hay que actualizar el
        # contador de líneas antes de descartarlos.
        if tipo in ('COMENTARIO_LINEA', 'COMENTARIO_MULTILINEA'):
            # Se cuentan los tres tipos de salto para soportar Windows y Mac clásico.
            # Nota: \r\n cuenta como DOS caracteres (\r y \n), pero rfind encontrará
            # el \n, que es el último de los dos, con lo que inicio_linea queda bien.
            lineas_en_comentario = valor.count('\n') + valor.count('\r\n') + valor.count('\r')
            linea += lineas_en_comentario

            # Si el comentario contiene saltos, actualizar inicio_linea al
            # carácter que sigue al último salto dentro del comentario.
            if '\n' in valor or '\r' in valor:
                ultimo_salto = max(
                    valor.rfind('\n'),
                    valor.rfind('\r')
                )
                inicio_linea = match.start() + ultimo_salto + 1
            continue

        # ── Normalizar nombre de tipo ──────────────────────────────────────
        # Convierte 'OPERADOR_ASIGNACIÓN' → 'OPERADOR_ASIG', etc.
        # Debe hacerse antes de la reclasificación para que los tipos
        # almacenados en tokens_unicos ya usen el nombre canónico.
        tipo = _normalizar_tipo(tipo)

        # ── Reclasificar identificadores ───────────────────────────────────
        # El regex no puede distinguir por sí solo entre un identificador
        # de usuario y una palabra reservada del lenguaje, porque ambos
        # siguen el mismo patrón alfanumérico. La distinción se hace aquí.
        if tipo == 'IDENTIFICADOR':
            if valor in PALABRAS_CLAVE:
                tipo = 'PALABRA_CLAVE'
            elif valor in LITERALES_BOOLEANOS:
                tipo = 'LITERAL_BOOLEANO'
            elif valor in LITERALES_NULOS:
                tipo = 'LITERAL_NULO'

        # ── Registrar errores por caracteres desconocidos ─────────────────
        # DESCONOCIDO es el comodín de reglas.py: captura todo lo que ninguna
        # otra regla reconoció.
        if tipo == 'DESCONOCIDO':
            # repr() para caracteres no imprimibles (ej: '\x00') en lugar de
            # intentar mostrar el glifo que quizás no existe en la fuente.
            char_repr = repr(valor) if not valor.isprintable() else f"'{valor}'"
            errores.append(
                f"⚠  Error léxico en línea {linea}, col {col}: "
                f"carácter inesperado {char_repr}"
            )

        # ── Acumular frecuencia y registrar token único ────────────────────
        # La clave es la tupla (tipo, valor), no solo el valor, para que
        # tokens con el mismo texto pero distinto tipo se cuenten por separado.
        clave = (tipo, valor)
        frecuencias[clave] = frecuencias.get(clave, 0) + 1

        # Solo se añade a tokens_unicos la primera vez que se ve este token.
        # Las apariciones posteriores solo incrementan el contador en frecuencias.
        if clave not in vistos:
            vistos.add(clave)
            tokens_unicos.append(Token(tipo, valor, linea, col))

    return tokens_unicos, frecuencias, errores


# ─────────────────────────────────────────────
#  TOKENIZAR SIN DEDUPLICAR (para el parser)
# ─────────────────────────────────────────────

def analizar_completo(codigo: str) -> Tuple[List[Token], List[str]]:
    """
    Versión del analizador léxico que devuelve TODOS los tokens en orden,
    incluidas las repeticiones. El parser sintáctico la necesita porque
    trabaja sobre la secuencia completa del fuente.

    La lógica interna es idéntica a analizar(), pero sin el mecanismo de
    de duplicación.

    Devuelve (tokens_completos, errores_lexicos).
    """
    tokens: List[Token] = []
    errores: List[str]  = []

    linea        = 1
    inicio_linea = 0

    for match in PATRON_MAESTRO.finditer(codigo):
        tipo  = match.lastgroup
        valor = match.group()
        col   = match.start() - inicio_linea + 1

        # Saltos de línea: actualizar contadores y descartar
        if tipo == 'NUEVA_LÍNEA':
            linea += 1
            inicio_linea = match.end()
            continue

        # Espacios y tabulaciones: descartar sin registrar
        if tipo == 'SEPARADOR':
            continue

        # Comentarios: contar saltos de línea internos y descartar
        if tipo in ('COMENTARIO_LINEA', 'COMENTARIO_MULTILINEA'):
            lineas_en_comentario = valor.count('\n')
            linea += lineas_en_comentario
            if '\n' in valor:
                # Mover inicio_linea al carácter tras el último salto del comentario
                inicio_linea = match.start() + valor.rfind('\n') + 1
            continue

        # Normalizar nombre de tipo (tildes → forma corta)
        tipo = _normalizar_tipo(tipo)

        # Reclasificar identificadores que sean palabras reservadas
        if tipo == 'IDENTIFICADOR':
            if valor in PALABRAS_CLAVE:
                tipo = 'PALABRA_CLAVE'
            elif valor in LITERALES_BOOLEANOS:
                tipo = 'LITERAL_BOOLEANO'
            elif valor in LITERALES_NULOS:
                tipo = 'LITERAL_NULO'

        # Registrar error léxico si el carácter no fue reconocido
        if tipo == 'DESCONOCIDO':
            char_repr = repr(valor) if not valor.isprintable() else f"'{valor}'"
            errores.append(
                f"⚠  Error léxico en línea {linea}, col {col}: "
                f"carácter inesperado {char_repr}"
            )

        # A diferencia de analizar(), aquí se añaden TODOS los tokens,
        # incluyendo repeticiones, para que el parser reciba la secuencia completa.
        tokens.append(Token(tipo, valor, linea, col))

    return tokens, errores
