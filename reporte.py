"""
reporte.py — Utilidades para mostrar los resultados del análisis léxico
             en la consola (salida de texto plano).

Este módulo es independiente de la interfaz gráfica: se puede usar desde
la terminal para depurar o para ejecutar el compilador en modo headless
(sin ventana), pasándole directamente el resultado de analizador.analizar().

Contiene dos funciones públicas:
  estadisticas()     → agrupa los tokens únicos por categoría y los cuenta.
  imprimir_reporte() → imprime la tabla completa con frecuencias y errores.
"""

# Counter es un dict especializado que cuenta ocurrencias de elementos.
# Equivale a hacer un diccionario y sumar manualmente, pero en una línea.
from collections import Counter
from typing import Dict, List, Tuple

from tipos_token import Token


# Separadores visuales reutilizados en varias secciones del reporte.
# Se definen como constantes para que cambiar el ancho (72) afecte
# a todo el reporte desde un único punto.
SEP   = "─" * 72   # separador de sección simple
DOBLE = "═" * 72   # separador de encabezado / cierre principal


# ─────────────────────────────────────────────
#  ESTADÍSTICAS POR CATEGORÍA
# ─────────────────────────────────────────────

def estadisticas(tokens: List[Token]) -> dict:
    """
    Cuenta cuántos tokens únicos hay de cada categoría (tipo).

    Recibe la lista de tokens sin duplicados producida por analizar() y
    devuelve un diccionario ordenado alfabéticamente por tipo:
        {'DELIMITADOR': 5, 'IDENTIFICADOR': 3, 'PALABRA_CLAVE': 4, ...}

    Nota: cuenta tokens únicos, no apariciones totales. Para el total
    de apariciones se usa sum(frecuencias.values()) en imprimir_reporte().
    """
    # La expresión generadora (t.tipo for t in tokens) extrae solo el campo
    # tipo de cada Token sin construir una lista intermedia en memoria.
    conteo = Counter(t.tipo for t in tokens)

    # sorted() sobre un dict devuelve sus claves ordenadas; al pasarlo a
    # dict() se reconstruye el diccionario en ese nuevo orden.
    return dict(sorted(conteo.items()))


# ─────────────────────────────────────────────
#  REPORTE EN CONSOLA
# ─────────────────────────────────────────────

def imprimir_reporte(
    tokens:      List[Token],               # tokens únicos de analizar()
    frecuencias: Dict[Tuple[str, str], int], # dict {(tipo, valor): cantidad}
    errores:     List[str],                  # mensajes de error léxico
    nombre:      str = ""                    # nombre del archivo fuente (opcional)
) -> None:
    """
    Imprime en consola el reporte completo del análisis léxico con tres
    secciones: tabla de tokens, estadísticas por categoría y errores.

    Parámetros:
        tokens      — lista de Token únicos, en orden de primera aparición.
        frecuencias — dict con clave (tipo, valor) y valor entero; es la
                      misma estructura devuelta por analizar().
        errores     — lista de strings con mensajes de error léxico.
        nombre      — nombre del archivo fuente que se muestra en el encabezado;
                      si está vacío, la línea "Fuente: ..." no se imprime.
    """

    # ── Encabezado ────────────────────────────────────────────────────────────
    print(f"\n{DOBLE}")
    print(f"  ANALIZADOR LÉXICO — Compiladores")
    # El nombre del archivo es opcional; si no se pasa, no se imprime la línea.
    if nombre:
        print(f"  Fuente: {nombre}")
    print(DOBLE)

    # ── Tabla de tokens únicos ────────────────────────────────────────────────
    # :^72 centra el texto en un campo de 72 caracteres.
    print(f"\n{'TOKENS ÚNICOS DETECTADOS':^72}")

    # Encabezados de columna con alineación fija para que coincidan
    # con los valores que se imprimen en el bucle de abajo.
    print(f"  {'TIPO':<28}  {'VALOR':<22}  {'APARICIONES':>11}")
    print(SEP)

    for tok in tokens:
        # La clave es tupla (tipo, valor), igual que en analizador.py.
        # Si por algún motivo no se encuentra, se asume 1 como fallback.
        freq  = frecuencias.get((tok.tipo, tok.valor), 1)

        # Barra visual proporcional: cada ▪ representa una aparición.
        # Se limita a 20 para que no desborde la línea con tokens muy frecuentes.
        barra = '▪' * min(freq, 20)

        # :<28 alinea tipo a la izquierda en 28 caracteres.
        # :<22 alinea valor a la izquierda en 22 caracteres.
        # :>5  alinea la frecuencia a la derecha en 5 dígitos.
        print(f"  {tok.tipo:<28}  {tok.valor:<22}  {freq:>5}  {barra}")

    print(SEP)

    # Totales debajo de la tabla
    total_unicos    = len(tokens)
    total_aparicion = sum(frecuencias.values())   # suma todas las frecuencias
    print(f"\n  Tokens únicos    : {total_unicos}")
    print(f"  Total apariciones: {total_aparicion}")

    # ── Estadísticas por categoría ────────────────────────────────────────────
    print(f"\n{'ESTADÍSTICAS POR CATEGORÍA':^72}")
    print(SEP)
    for tipo, cantidad in estadisticas(tokens).items():
        # Barra de bloques proporcional; se limita a 40 para ajustarse a la
        # anchura de la consola sin que tipos muy frecuentes rompan el formato.
        barra = '█' * min(cantidad, 40)
        print(f"  {tipo:<28} {cantidad:>4}  {barra}")

    # ── Errores léxicos ───────────────────────────────────────────────────────
    if errores:
        print(f"\n{'ERRORES LÉXICOS':^72}")
        print(SEP)
        for e in errores:
            print(f"  {e}")
    else:
        # Confirmación explícita de que el análisis fue limpio.
        print("\n  ✓ Sin errores léxicos detectados.")

    print(f"\n{DOBLE}\n")
    