"""
reporte.py — Utilidades para mostrar resultados del análisis léxico.

Contiene:
  - estadisticas()     → conteo de tokens por categoría
  - imprimir_reporte() → salida formateada en consola
"""

from collections import Counter
from typing import List
from tipos_token import Token


SEP  = "─" * 65
DOBLE = "═" * 65


# ─────────────────────────────────────────────
#  ESTADÍSTICAS
# ─────────────────────────────────────────────

def estadisticas(tokens: List[Token]) -> dict:
    """Devuelve un diccionario {tipo: cantidad} ordenado alfabéticamente."""
    conteo = Counter(t.tipo for t in tokens)
    return dict(sorted(conteo.items()))


# ─────────────────────────────────────────────
#  REPORTE EN CONSOLA
# ─────────────────────────────────────────────

def imprimir_reporte(
    tokens:  List[Token],
    errores: List[str],
    nombre:  str = ""
) -> None:
    """Imprime en consola la tabla de tokens, estadísticas y errores."""

    # Encabezado
    print(f"\n{DOBLE}")
    print(f"  ANALIZADOR LÉXICO — Compiladores")
    if nombre:
        print(f"  Fuente: {nombre}")
    print(DOBLE)

    # Tabla de tokens
    print(f"\n{'TOKENS ENCONTRADOS':^65}")
    print(SEP)
    for tok in tokens:
        print(tok)
    print(SEP)
    print(f"\nTotal de tokens: {len(tokens)}")

    # Estadísticas
    print(f"\n{'ESTADÍSTICAS POR CATEGORÍA':^65}")
    print(SEP)
    for tipo, cantidad in estadisticas(tokens).items():
        barra = '█' * cantidad
        print(f"  {tipo:<28} {cantidad:>4}  {barra}")

    # Errores
    if errores:
        print(f"\n{'ERRORES LÉXICOS':^65}")
        print(SEP)
        for e in errores:
            print(f"  {e}")
    else:
        print("\n  ✓ Sin errores léxicos detectados.")

    print(f"\n{DOBLE}\n")
