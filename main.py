"""
main.py — Punto de entrada del Analizador Léxico.

Ejecuta tres ejemplos extraídos del material del curso
(Compiladores — Robert Damian Quintero Laverde) para
demostrar el funcionamiento del analizador.

Uso:
    python main.py
"""

import sys
import os

# Asegurar que los módulos del paquete sean encontrados
sys.path.insert(0, os.path.dirname(__file__))

from analizador import analizar
from reporte    import imprimir_reporte


# ─────────────────────────────────────────────
#  EJEMPLOS DE PRUEBA (del material del curso)
# ─────────────────────────────────────────────

EJEMPLO_1 = """
// Ejemplo del material: Posición = inicial + velocidad * 60
Posición = inicial + velocidad * 60
"""

EJEMPLO_2 = """
int main() {
    float dividir;
    int a;
    int b = 0;
    if (b == 0) {
        return "NO SE PUEDE DIVIDIR ENTRE 0";
    } else {
        float resultado = dividir(a, b);
        printf("Resultado: ", resultado);
    }
    return 0;
}
"""

EJEMPLO_3 = """
// Variables y operaciones
x = 42
totalCost = 3.14 * x
myFunction = true
nombre = "hello"
condicion = null

// Operadores relacionales y lógicos
if (x >= 10 && totalCost != 0) {
    for (int i = 0; i < x; i++) {
        totalCost += i;
    }
}
"""


# ─────────────────────────────────────────────
#  EJECUCIÓN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    ejemplos = [
        ("Ejemplo 1 — Expresión del material", EJEMPLO_1),
        ("Ejemplo 2 — Programa C (material)",  EJEMPLO_2),
        ("Ejemplo 3 — Código completo",        EJEMPLO_3),
    ]

    for nombre, codigo in ejemplos:
        tokens, frecuencias, errores = analizar(codigo)
        imprimir_reporte(tokens, frecuencias, errores, nombre)
        