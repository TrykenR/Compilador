import tkinter as tk
from tkinter import filedialog
from lexico.analizador import Lexer

def analizar():
    ruta = filedialog.askopenfilename()
    lexer = Lexer(ruta)
    tokens = lexer.tokenize()

    output.delete("1.0", tk.END)
    for t in tokens:
        output.insert(tk.END, str(t) + "\n")

def run():
    root = tk.Tk()
    root.title("Compilador")

    btn = tk.Button(root, text="Cargar archivo", command=analizar)
    btn.pack()

    global output
    output = tk.Text(root, height=20, width=60)
    output.pack()

    root.mainloop()
    