"""
reporte.py — Utilidades para mostrar resultados del análisis léxico.

Contiene:
  - estadisticas()     → conteo de tokens únicos por categoría
  - imprimir_reporte() → salida formateada en consola con frecuencias
"""

from collections import Counter
from typing import Dict, List, Tuple

from tipos_token import Token


SEP   = "─" * 72
DOBLE = "═" * 72


# ─────────────────────────────────────────────
#  ESTADÍSTICAS POR CATEGORÍA
# ─────────────────────────────────────────────

def estadisticas(tokens: List[Token]) -> dict:
    """Devuelve un diccionario {tipo: cantidad de tokens únicos} ordenado."""
    conteo = Counter(t.tipo for t in tokens)
    return dict(sorted(conteo.items()))


# ─────────────────────────────────────────────
#  REPORTE EN CONSOLA
# ─────────────────────────────────────────────

def imprimir_reporte(
    tokens:      List[Token],
    frecuencias: Dict[Tuple[str, str], int],
    errores:     List[str],
    nombre:      str = ""
) -> None:
    """Imprime la tabla de tokens únicos con su frecuencia, estadísticas y errores."""

    # Encabezado
    print(f"\n{DOBLE}")
    print(f"  ANALIZADOR LÉXICO — Compiladores")
    if nombre:
        print(f"  Fuente: {nombre}")
    print(DOBLE)

    # Tabla de tokens únicos
    print(f"\n{'TOKENS ÚNICOS DETECTADOS':^72}")
    print(f"  {'TIPO':<28}  {'VALOR':<22}  {'APARICIONES':>11}")
    print(SEP)
    for tok in tokens:
        # CORRECCIÓN: la clave es una tupla (tipo, valor), no string
        freq  = frecuencias.get((tok.tipo, tok.valor), 1)
        barra = '▪' * min(freq, 20)
        print(f"  {tok.tipo:<28}  {tok.valor:<22}  {freq:>5}  {barra}")
    print(SEP)

    total_unicos    = len(tokens)
    total_aparicion = sum(frecuencias.values())
    print(f"\n  Tokens únicos    : {total_unicos}")
    print(f"  Total apariciones: {total_aparicion}")

    # Estadísticas por categoría
    print(f"\n{'ESTADÍSTICAS POR CATEGORÍA':^72}")
    print(SEP)
    for tipo, cantidad in estadisticas(tokens).items():
        barra = '█' * min(cantidad, 40)
        print(f"  {tipo:<28} {cantidad:>4}  {barra}")

    # Errores
    if errores:
        print(f"\n{'ERRORES LÉXICOS':^72}")
        print(SEP)
        for e in errores:
            print(f"  {e}")
    else:
        print("\n  ✓ Sin errores léxicos detectados.")

    print(f"\n{DOBLE}\n")
    