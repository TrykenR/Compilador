"""
interfaz.py — Interfaz gráfica de escritorio del Compilador.

Construye una ventana Tkinter con dos paneles principales:
  - Panel izquierdo: editor de código fuente con numeración de líneas.
  - Panel derecho:   resultados del análisis en cinco pestañas:
      · Tokens       — tabla de tokens únicos con frecuencia visual.
      · Estadísticas — tarjetas de resumen y gráfico de barras por categoría.
      · Árbol Sint.  — visualización gráfica del AST sobre un canvas scrollable.
      · Semántico    — tabla de símbolos, advertencias y errores semánticos.
      · Errores      — lista de errores léxicos y sintácticos con colores.
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analizador import analizar, analizar_completo
from sintactico import analizar_sintactico, Nodo
from semantico import analizar_semantico


# ══════════════════════════════════════════════════════════════════════════════
#  PALETA DE COLORES Y TIPOGRAFÍA
# ══════════════════════════════════════════════════════════════════════════════

BG      = "#ffffff"
FG      = "#000000"
SURFACE = "#f0f0f0"
BORDER  = "#000000"
MUTED   = "#555555"
ACCENT  = "#000000"
BTN_FG  = "#ffffff"
SEL_BG  = "#000000"
SEL_FG  = "#ffffff"

MONO    = ("Courier New", 11)
MONO_SM = ("Courier New", 10)
MONO_LG = ("Courier New", 12)
SANS    = ("Helvetica", 10)
SANS_B  = ("Helvetica", 10, "bold")


# ══════════════════════════════════════════════════════════════════════════════
#  ESTILOS VISUALES POR TIPO DE TOKEN
# ══════════════════════════════════════════════════════════════════════════════

TOKEN_TAGS = {
    "PALABRA_CLAVE":    {"font": ("Courier New", 11, "bold"),   "foreground": "#000000"},
    "IDENTIFICADOR":    {"font": ("Courier New", 11),           "foreground": "#000000"},
    "LITERAL_NUM":      {"font": ("Courier New", 11),           "foreground": "#333333"},
    "LITERAL_CADENA":   {"font": ("Courier New", 11, "italic"), "foreground": "#333333"},
    "LITERAL_BOOLEANO": {"font": ("Courier New", 11, "bold"),   "foreground": "#000000"},
    "LITERAL_NULO":     {"font": ("Courier New", 11, "italic"), "foreground": "#555555"},
    "OPERADOR_ASIG":    {"font": ("Courier New", 11, "bold"),   "foreground": "#000000"},
    "OPERADOR_REL":     {"font": ("Courier New", 11, "bold"),   "foreground": "#000000"},
    "OPERADOR_LOG":     {"font": ("Courier New", 11, "bold"),   "foreground": "#000000"},
    "OPERADOR_ARIT":    {"font": ("Courier New", 11),           "foreground": "#000000"},
    "OPERADOR_INCR":    {"font": ("Courier New", 11, "bold"),   "foreground": "#000000"},
    "OPERADOR_BIT":     {"font": ("Courier New", 11),           "foreground": "#444444"},
    "DELIMITADOR":      {"font": ("Courier New", 11),           "foreground": "#555555"},
    "DESCONOCIDO":      {"font": ("Courier New", 11),           "foreground": "#ff0000"},
}

# Colores por categoría de símbolo en la tabla semántica
SEM_TAGS = {
    "variable":  {"foreground": "#000000"},
    "funcion":   {"foreground": "#000000", "font": ("Courier New", 10, "bold")},
    "parametro": {"foreground": "#333333"},
    "warn":      {"foreground": "#996600", "font": ("Courier New", 10)},
    "err_sem":   {"foreground": "#cc0000", "font": ("Courier New", 10)},
    "ok_sem":    {"foreground": MUTED,     "font": ("Courier New", 10)},
    "head_sem":  {"foreground": "#000000", "font": ("Courier New", 10, "bold")},
    "muted_sem": {"foreground": MUTED,     "font": ("Courier New", 10)},
}


# ══════════════════════════════════════════════════════════════════════════════
#  VENTANA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

class Compilador(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Compilador — Léxico · Sintáctico · Semántico")
        self.configure(bg=BG)
        self.geometry("1280x720")
        self.minsize(960, 580)
        self._last_line_count = 0
        self._build_ui()
        self._apply_style()

    # ══════════════════════════════════════════════════════════════════════════
    #  CONSTRUCCIÓN DE LA UI
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        top = tk.Frame(self, bg=BG, pady=8, padx=16)
        top.pack(fill="x", side="top")

        tk.Label(top, text="COMPILADOR", font=("Helvetica", 14, "bold"),
                 bg=BG, fg=FG).pack(side="left")
        tk.Label(top, text="  Léxico · Sintáctico · Semántico", font=("Helvetica", 10),
                 bg=BG, fg=MUTED).pack(side="left")

        self.btn_run = tk.Button(
            top, text="▶  Analizar  (Ctrl+Enter)",
            font=SANS_B, bg=ACCENT, fg=BTN_FG,
            relief="flat", padx=14, pady=4, cursor="hand2",
            command=self.run
        )
        self.btn_run.pack(side="right")

        tk.Button(
            top, text="Limpiar", font=SANS, bg=SURFACE, fg=FG,
            relief="flat", padx=10, pady=4, cursor="hand2",
            command=self.limpiar
        ).pack(side="right", padx=8)

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        self._build_editor(body)
        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y")
        self._build_results(body)

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")
        status_bar = tk.Frame(self, bg=SURFACE, pady=4, padx=12)
        status_bar.pack(fill="x", side="bottom")

        self.lbl_status = tk.Label(status_bar, text="Listo", font=MONO_SM,
                                   bg=SURFACE, fg=MUTED, anchor="w")
        self.lbl_status.pack(side="left")

        self.lbl_stats = tk.Label(status_bar, text="", font=MONO_SM,
                                  bg=SURFACE, fg=MUTED, anchor="e")
        self.lbl_stats.pack(side="right")

    def _build_editor(self, parent):
        frame = tk.Frame(parent, bg=BG)
        frame.pack(side="left", fill="both", expand=True)

        hdr = tk.Frame(frame, bg=SURFACE, pady=5, padx=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="CÓDIGO FUENTE", font=MONO_SM,
                 bg=SURFACE, fg=MUTED).pack(side="left")
        self.lbl_cursor = tk.Label(hdr, text="L1  C1", font=MONO_SM,
                                   bg=SURFACE, fg=MUTED)
        self.lbl_cursor.pack(side="right")

        edit_frame = tk.Frame(frame, bg=BG)
        edit_frame.pack(fill="both", expand=True)

        self.line_nums = tk.Text(
            edit_frame, width=4, bg=SURFACE, fg=MUTED,
            font=MONO, state="disabled", relief="flat",
            padx=4, takefocus=False, cursor="arrow"
        )
        self.line_nums.pack(side="left", fill="y")
        tk.Frame(edit_frame, bg=BORDER, width=1).pack(side="left", fill="y")

        self.editor = tk.Text(
            edit_frame, wrap="none", bg=BG, fg=FG,
            font=MONO_LG, relief="flat", padx=12, pady=8,
            insertbackground=FG, selectbackground=SEL_BG,
            selectforeground=SEL_FG, undo=True
        )
        self.editor.pack(side="left", fill="both", expand=True)

        hscroll = tk.Scrollbar(frame, orient="horizontal",
                               command=self.editor.xview)
        hscroll.pack(fill="x")
        self.editor.configure(xscrollcommand=hscroll.set)

        self.editor.insert("1.0", self._ejemplo())

        self.editor.bind("<KeyRelease>",     self._on_key)
        self.editor.bind("<ButtonRelease>",  self._on_key)
        self.editor.bind("<Control-Return>", lambda e: self.run())
        self.editor.bind("<Tab>",            self._tab)
        self.editor.bind("<MouseWheel>",     self._sync_scroll)
        self.editor.bind("<Button-4>",       self._sync_scroll)
        self.editor.bind("<Button-5>",       self._sync_scroll)

        self._update_line_nums()

    def _build_results(self, parent):
        frame = tk.Frame(parent, bg=BG)
        frame.pack(side="left", fill="both", expand=True)

        tab_bar = tk.Frame(frame, bg=SURFACE)
        tab_bar.pack(fill="x")

        self.tab_btns    = {}
        self.tab_frames  = {}
        self.current_tab = tk.StringVar(value="tokens")

        pestanas = [
            ("tokens",   "Tokens"),
            ("stats",    "Estadísticas"),
            ("arbol",    "Árbol Sint."),
            ("semantico","Semántico"),
            ("errores",  "Errores"),
        ]

        for nombre, label in pestanas:
            btn = tk.Button(
                tab_bar, text=label, font=SANS,
                bg=SURFACE, fg=MUTED, relief="flat",
                padx=14, pady=6, cursor="hand2",
                command=lambda n=nombre: self._show_tab(n)
            )
            btn.pack(side="left")
            self.tab_btns[nombre] = btn

        tk.Frame(tab_bar, bg=BORDER, height=1).pack(side="bottom", fill="x")

        self.tab_frame = tk.Frame(frame, bg=BG)
        self.tab_frame.pack(fill="both", expand=True)

        self._build_tab_tokens()
        self._build_tab_stats()
        self._build_tab_arbol()
        self._build_tab_semantico()
        self._build_tab_errores()

        self._show_tab("tokens")

    # ── Construcción de pestañas ──────────────────────────────────────────────

    def _build_tab_tokens(self):
        f = tk.Frame(self.tab_frame, bg=BG)
        self.tab_frames["tokens"] = f

        hdr = tk.Frame(f, bg=SURFACE, pady=4, padx=8)
        hdr.pack(fill="x")
        for txt, w in [("TIPO", 22), ("VALOR", 22), ("APARICIONES", 12)]:
            tk.Label(hdr, text=txt, font=("Courier New", 9, "bold"),
                     bg=SURFACE, fg=MUTED, width=w, anchor="w").pack(side="left")
        tk.Frame(f, bg=BORDER, height=1).pack(fill="x")

        list_frame = tk.Frame(f, bg=BG)
        list_frame.pack(fill="both", expand=True)
        vsb = tk.Scrollbar(list_frame, orient="vertical")
        vsb.pack(side="right", fill="y")

        self.token_list = tk.Text(
            list_frame, wrap="none", bg=BG, fg=FG,
            font=MONO_SM, relief="flat", padx=8, pady=4,
            state="disabled", yscrollcommand=vsb.set,
            cursor="arrow"
        )
        self.token_list.pack(fill="both", expand=True)
        vsb.config(command=self.token_list.yview)

        for tipo, cfg in TOKEN_TAGS.items():
            self.token_list.tag_configure(tipo, **cfg)
        self.token_list.tag_configure("muted",  foreground=MUTED)
        self.token_list.tag_configure("sep",     foreground="#cccccc")
        self.token_list.tag_configure("stripe",  background="#f8f8f8")

    def _build_tab_stats(self):
        f = tk.Frame(self.tab_frame, bg=BG)
        self.tab_frames["stats"] = f

        self.cards_frame = tk.Frame(f, bg=BG, pady=12, padx=16)
        self.cards_frame.pack(fill="x")

        tk.Frame(f, bg=BORDER, height=1).pack(fill="x", padx=16)
        tk.Label(f, text="DISTRIBUCIÓN POR CATEGORÍA",
                 font=("Courier New", 9, "bold"), bg=BG, fg=MUTED,
                 anchor="w", padx=16, pady=8).pack(fill="x")

        bar_wrap = tk.Frame(f, bg=BG)
        bar_wrap.pack(fill="both", expand=True)
        vsb = tk.Scrollbar(bar_wrap, orient="vertical")
        vsb.pack(side="right", fill="y")

        self.stats_canvas = tk.Canvas(bar_wrap, bg=BG, relief="flat",
                                      highlightthickness=0,
                                      yscrollcommand=vsb.set)
        self.stats_canvas.pack(fill="both", expand=True)
        vsb.config(command=self.stats_canvas.yview)

        self.stats_inner = tk.Frame(self.stats_canvas, bg=BG)
        self.stats_canvas.create_window((0, 0), window=self.stats_inner, anchor="nw")
        self.stats_inner.bind("<Configure>",
            lambda e: self.stats_canvas.configure(
                scrollregion=self.stats_canvas.bbox("all")))

    def _build_tab_arbol(self):
        f = tk.Frame(self.tab_frame, bg=BG)
        self.tab_frames["arbol"] = f

        wrap = tk.Frame(f, bg=BG)
        wrap.pack(fill="both", expand=True)

        vsb = tk.Scrollbar(wrap, orient="vertical")
        hsb = tk.Scrollbar(wrap, orient="horizontal")
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")

        self.tree_canvas = tk.Canvas(
            wrap, bg=BG, relief="flat", highlightthickness=0,
            yscrollcommand=vsb.set, xscrollcommand=hsb.set
        )
        self.tree_canvas.pack(fill="both", expand=True)
        vsb.config(command=self.tree_canvas.yview)
        hsb.config(command=self.tree_canvas.xview)

        self.tree_canvas.bind("<MouseWheel>", lambda e:
            self.tree_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    def _build_tab_semantico(self):
        """
        Pestaña 'Semántico': dividida en dos zonas verticales.
          - Zona superior: tabla de símbolos (nombre, tipo, categoría, línea).
          - Zona inferior: advertencias y errores semánticos separados.
        Misma estética que el resto: fondo blanco, monoespaciada, sin bordes.
        """
        f = tk.Frame(self.tab_frame, bg=BG)
        self.tab_frames["semantico"] = f

        # ── Cabecera tabla de símbolos ────────────────────────────────────────
        hdr = tk.Frame(f, bg=SURFACE, pady=4, padx=8)
        hdr.pack(fill="x")
        for txt, w in [("SÍMBOLO", 20), ("TIPO", 10), ("CATEGORÍA", 14), ("LÍNEA", 7), ("USADO", 7)]:
            tk.Label(hdr, text=txt, font=("Courier New", 9, "bold"),
                     bg=SURFACE, fg=MUTED, width=w, anchor="w").pack(side="left")
        tk.Frame(f, bg=BORDER, height=1).pack(fill="x")

        # ── Lista de símbolos ─────────────────────────────────────────────────
        sym_frame = tk.Frame(f, bg=BG)
        sym_frame.pack(fill="both", expand=True)
        vsb1 = tk.Scrollbar(sym_frame, orient="vertical")
        vsb1.pack(side="right", fill="y")

        self.sym_list = tk.Text(
            sym_frame, wrap="none", bg=BG, fg=FG,
            font=MONO_SM, relief="flat", padx=8, pady=4,
            state="disabled", yscrollcommand=vsb1.set,
            cursor="arrow", height=10
        )
        self.sym_list.pack(fill="both", expand=True)
        vsb1.config(command=self.sym_list.yview)

        # Registrar tags de la tabla semántica
        for tag, cfg in SEM_TAGS.items():
            self.sym_list.tag_configure(tag, **cfg)

        # ── Separador ─────────────────────────────────────────────────────────
        tk.Frame(f, bg=BORDER, height=1).pack(fill="x")
        tk.Label(f, text="ADVERTENCIAS Y ERRORES SEMÁNTICOS",
                 font=("Courier New", 9, "bold"), bg=BG, fg=MUTED,
                 anchor="w", padx=8, pady=6).pack(fill="x")
        tk.Frame(f, bg=BORDER, height=1).pack(fill="x")

        # ── Lista de advertencias/errores semánticos ──────────────────────────
        msg_frame = tk.Frame(f, bg=BG)
        msg_frame.pack(fill="both", expand=True)
        vsb2 = tk.Scrollbar(msg_frame, orient="vertical")
        vsb2.pack(side="right", fill="y")

        self.sem_msg = tk.Text(
            msg_frame, wrap="word", bg=BG, fg=FG,
            font=MONO_SM, relief="flat", padx=8, pady=4,
            state="disabled", yscrollcommand=vsb2.set,
            cursor="arrow"
        )
        self.sem_msg.pack(fill="both", expand=True)
        vsb2.config(command=self.sem_msg.yview)

        for tag, cfg in SEM_TAGS.items():
            self.sem_msg.tag_configure(tag, **cfg)

    def _build_tab_errores(self):
        f = tk.Frame(self.tab_frame, bg=BG)
        self.tab_frames["errores"] = f

        wrap = tk.Frame(f, bg=BG)
        wrap.pack(fill="both", expand=True)
        vsb = tk.Scrollbar(wrap, orient="vertical")
        vsb.pack(side="right", fill="y")

        self.err_text = tk.Text(
            wrap, wrap="word", bg=BG, fg=FG,
            font=MONO_SM, relief="flat", padx=12, pady=8,
            state="disabled", yscrollcommand=vsb.set
        )
        self.err_text.pack(fill="both", expand=True)
        vsb.config(command=self.err_text.yview)

        self.err_text.tag_configure("err",  foreground="#cc0000",
                                    font=("Courier New", 10))
        self.err_text.tag_configure("ok",   foreground=MUTED,
                                    font=("Courier New", 10))
        self.err_text.tag_configure("head", font=("Courier New", 10, "bold"))

    # ── Cambio de pestaña ─────────────────────────────────────────────────────

    def _show_tab(self, nombre):
        for frm in self.tab_frames.values():
            frm.pack_forget()
        self.tab_frames[nombre].pack(fill="both", expand=True)

        for n, btn in self.tab_btns.items():
            if n == nombre:
                btn.configure(bg=BG, fg=FG, font=SANS_B, relief="groove")
            else:
                btn.configure(bg=SURFACE, fg=MUTED, font=SANS, relief="flat")
        self.current_tab.set(nombre)

    # ══════════════════════════════════════════════════════════════════════════
    #  ANÁLISIS PRINCIPAL
    # ══════════════════════════════════════════════════════════════════════════

    def run(self, _=None):
        codigo = self.editor.get("1.0", "end-1c")
        if not codigo.strip():
            return

        try:
            # Léxico
            tokens_unicos, frecuencias, lex_errors = analizar(codigo)
            tokens_full, _ = analizar_completo(codigo)

            # Sintáctico
            arbol, sin_errors = analizar_sintactico(tokens_full)

            # Semántico
            tabla, sem_warns, sem_errors = analizar_semantico(arbol)

            all_errors = lex_errors + sin_errors + sem_errors

            # Poblar pestañas
            self._fill_tokens(tokens_unicos, frecuencias)
            self._fill_stats(tokens_unicos, frecuencias, all_errors)
            self._fill_arbol(arbol, sin_errors)
            self._fill_semantico(tabla, sem_warns, sem_errors)
            self._fill_errores(lex_errors, sin_errors, sem_errors)

            # Barra de estado
            total_ap = sum(frecuencias.values())
            if all_errors:
                self.lbl_status.configure(
                    text=f"⚠  {len(all_errors)} error(es) encontrado(s)", fg="#cc0000")
            elif sem_warns:
                self.lbl_status.configure(
                    text=f"ℹ  {len(sem_warns)} advertencia(s) semántica(s)", fg="#996600")
            else:
                self.lbl_status.configure(
                    text="✓  Análisis completado sin errores", fg=MUTED)

            self.lbl_stats.configure(
                text=f"{len(tokens_unicos)} tokens únicos  ·  "
                     f"{total_ap} apariciones  ·  "
                     f"{len(tabla.todos())} símbolos")

            # Color del botón de errores
            self.tab_btns["errores"].configure(
                fg="#cc0000" if all_errors else MUTED)
            # Color del botón semántico
            self.tab_btns["semantico"].configure(
                fg="#cc0000" if sem_errors else
                   "#996600" if sem_warns else MUTED)

        except Exception as exc:
            import traceback
            self.lbl_status.configure(
                text=f"⚠  Error interno: {exc}", fg="#cc0000")
            traceback.print_exc()

    # ══════════════════════════════════════════════════════════════════════════
    #  MÉTODOS DE RELLENO DE PESTAÑAS
    # ══════════════════════════════════════════════════════════════════════════

    def _fill_tokens(self, tokens, frecuencias):
        tl = self.token_list
        tl.configure(state="normal")
        tl.delete("1.0", "end")

        max_freq = max(frecuencias.values(), default=1)

        for tok in tokens:
            clave = (tok.tipo, tok.valor)
            freq  = frecuencias.get(clave, 1)
            tag   = tok.tipo if tok.tipo in TOKEN_TAGS else "muted"

            tl.insert("end", f"{tok.tipo:<22}", tag)
            tl.insert("end", f"  {tok.valor:<22}", tag)

            bar_filled = round((freq / max_freq) * 16)
            bar = "█" * bar_filled + "░" * (16 - bar_filled)
            tl.insert("end", f"  {freq:>3}  ", "muted")
            tl.insert("end", bar, tag)
            tl.insert("end", "\n")

        if not tokens:
            tl.insert("end", "  Sin tokens encontrados\n", "muted")

        tl.configure(state="disabled")

    def _fill_stats(self, tokens, frecuencias, errores):
        for w in self.cards_frame.winfo_children():
            w.destroy()

        total_ap = sum(frecuencias.values())
        cats: dict = {}
        for tok in tokens:
            cats[tok.tipo] = cats.get(tok.tipo, 0) + 1

        resumen = [
            ("Tokens únicos", str(len(tokens))),
            ("Total aparic.", str(total_ap)),
            ("Categorías",    str(len(cats))),
            ("Errores",       str(len(errores))),
        ]
        for label, val in resumen:
            card = tk.Frame(self.cards_frame, bg=SURFACE,
                            relief="solid", bd=1, padx=16, pady=10)
            card.pack(side="left", padx=8, pady=4)
            tk.Label(card, text=val, font=("Helvetica", 22, "bold"),
                     bg=SURFACE, fg=FG).pack()
            tk.Label(card, text=label, font=("Courier New", 9),
                     bg=SURFACE, fg=MUTED).pack()

        for w in self.stats_inner.winfo_children():
            w.destroy()

        if not cats:
            return

        max_cnt     = max(cats.values())
        sorted_cats = sorted(cats.items(), key=lambda x: -x[1])

        for tipo, cnt in sorted_cats:
            row = tk.Frame(self.stats_inner, bg=BG, pady=4, padx=16)
            row.pack(fill="x")
            tk.Label(row, text=f"{tipo:<26}", font=MONO_SM,
                     bg=BG, fg=FG, anchor="w", width=26).pack(side="left")

            bar_w = int((cnt / max_cnt) * 200)
            c = tk.Canvas(row, bg=BG, height=16, width=220,
                          highlightthickness=0, relief="flat")
            c.pack(side="left")
            c.create_rectangle(0, 4, max(bar_w, 2), 14, fill=FG, outline="")
            c.create_rectangle(bar_w, 4, 220, 14, fill=SURFACE, outline="")

            tk.Label(row, text=f"{cnt:>4}", font=MONO_SM,
                     bg=BG, fg=MUTED, width=4).pack(side="left", padx=6)

    def _fill_arbol(self, raiz: Nodo, errores: List[str]):
        canvas = self.tree_canvas
        canvas.delete("all")

        NODE_W, NODE_H = 120, 28
        H_GAP, V_GAP   = 14,  54

        posiciones = {}

        def layout_iterativo(root: Nodo):
            anchos = {}
            pila   = [(root, False)]
            while pila:
                nodo, procesado = pila.pop()
                if procesado:
                    if not nodo.hijos:
                        anchos[id(nodo)] = NODE_W
                    else:
                        # === AQUÍ ESTÁ LA CORRECCIÓN ===
                        # Cambiamos reversed → orden normal para que quede "al revés" del anterior
                        total  = sum(anchos[id(h)] for h in nodo.hijos)
                        total += H_GAP * (len(nodo.hijos) - 1)
                        anchos[id(nodo)] = max(total, NODE_W)
                else:
                    pila.append((nodo, True))
                    # === CAMBIO PRINCIPAL ===
                    for hijo in nodo.hijos:          # ← antes estaba reversed
                        pila.append((hijo, False))

            # Posicionamiento (también en orden normal)
            cola = [(root, 0, 20)]
            while cola:
                nodo, prof, x_ini = cola.pop(0)
                x_centro = x_ini + anchos[id(nodo)] // 2
                cy = prof * V_GAP
                posiciones[id(nodo)] = (x_centro - NODE_W // 2, cy)

                x_cursor = x_ini
                for hijo in nodo.hijos:              # ← también aquí orden normal
                    cola.append((hijo, prof + 1, x_cursor))
                    x_cursor += anchos[id(hijo)] + H_GAP

            return anchos

        layout_iterativo(raiz)

        if not posiciones:
            canvas.create_text(20, 20, text="(árbol vacío)", anchor="nw",
                               font=MONO_SM, fill=MUTED)
            return

        all_x   = [p[0] for p in posiciones.values()]
        all_y   = [p[1] for p in posiciones.values()]
        total_w = max(all_x) + NODE_W + 40
        total_h = max(all_y) + NODE_H + 40
        canvas.configure(scrollregion=(0, 0, total_w, total_h))

        raiz_x = posiciones[id(raiz)][0]
        fraccion_inicio = max(0.0, (raiz_x - 20) / total_w)
        canvas.xview_moveto(fraccion_inicio)

        pila = [raiz]
        while pila:
            nodo = pila.pop()
            if id(nodo) not in posiciones:
                continue
            px, py = posiciones[id(nodo)]
            pcx = px + NODE_W // 2
            pcy = py + NODE_H
            for hijo in nodo.hijos:
                if id(hijo) not in posiciones:
                    continue
                hx, hy = posiciones[id(hijo)]
                hcx = hx + NODE_W // 2
                canvas.create_line(pcx, pcy, hcx, hy, fill="#888888", width=1)
                pila.append(hijo)

        pila = [raiz]
        while pila:
            nodo = pila.pop()
            if id(nodo) not in posiciones:
                continue
            x, y = posiciones[id(nodo)]
            etq  = nodo.etiqueta
            if len(etq) > 16:
                etq = etq[:15] + "…"

            if nodo.etiqueta == "programa":
                bg_col, fg_col, borde = "#000000", "#ffffff", "#000000"
            elif nodo.etiqueta == "bloque":
                bg_col, fg_col, borde = "#333333", "#ffffff", "#000000"
            elif any(nodo.etiqueta.startswith(k) for k in
                     ("if", "while", "for", "return", "do-while", "switch")):
                bg_col, fg_col, borde = "#555555", "#ffffff", "#000000"
            elif any(nodo.etiqueta.startswith(k) for k in
                     ("decl ", "func ", "proto ", "asig", "llamada")):
                bg_col, fg_col, borde = "#f0f0f0", "#000000", "#000000"
            elif nodo.etiqueta in ("condición", "else", "init", "cond", "inc",
                                   "case", "default", "break", "continue"):
                bg_col, fg_col, borde = "#dddddd", "#000000", "#888888"
            else:
                bg_col, fg_col, borde = "#ffffff", "#000000", "#aaaaaa"

            canvas.create_rectangle(x, y, x + NODE_W, y + NODE_H,
                                    fill=bg_col, outline=borde, width=1)
            canvas.create_text(x + NODE_W // 2, y + NODE_H // 2,
                               text=etq, font=("Courier New", 9),
                               fill=fg_col, anchor="center")
            for hijo in nodo.hijos:
                pila.append(hijo)

        if errores:
            canvas.create_text(
                10, total_h - 10,
                text=f"⚠  {len(errores)} error(es) sintáctico(s) — árbol puede ser parcial",
                font=("Courier New", 9), fill="#cc0000", anchor="sw"
            )

    def _fill_semantico(self, tabla, advertencias: List[str], errores: List[str]):
        """
        Rellena la pestaña semántica con:
          - Tabla de símbolos: cada símbolo en una fila con tipo, categoría, línea y uso.
          - Advertencias en amarillo oscuro.
          - Errores semánticos en rojo.
        """
        # ── Tabla de símbolos ─────────────────────────────────────────────────
        sl = self.sym_list
        sl.configure(state="normal")
        sl.delete("1.0", "end")

        simbolos = tabla.todos()
        if simbolos:
            for sim in simbolos:
                cat_tag = sim.categoria  # 'variable', 'funcion', 'parametro'
                usado_txt = "✓" if sim.usado else "✗"
                usado_tag = "muted_sem" if sim.usado else "err_sem"

                sl.insert("end", f"{sim.nombre:<20}", cat_tag)
                sl.insert("end", f"{sim.tipo:<10}", "muted_sem")
                sl.insert("end", f"{sim.categoria:<14}", cat_tag)
                sl.insert("end", f"L{sim.linea:<6}", "muted_sem")
                sl.insert("end", f"{usado_txt}\n", usado_tag)
        else:
            sl.insert("end", "  Sin símbolos registrados\n", "muted_sem")

        sl.configure(state="disabled")

        # ── Advertencias y errores semánticos ─────────────────────────────────
        sm = self.sem_msg
        sm.configure(state="normal")
        sm.delete("1.0", "end")

        if not advertencias and not errores:
            sm.insert("end", "✓  Sin advertencias ni errores semánticos.\n", "ok_sem")
        else:
            if errores:
                sm.insert("end", "ERRORES SEMÁNTICOS\n", "head_sem")
                sm.insert("end", "─" * 60 + "\n", "muted_sem")
                for e in errores:
                    sm.insert("end", f"  {e}\n", "err_sem")
                sm.insert("end", "\n")
            if advertencias:
                sm.insert("end", "ADVERTENCIAS\n", "head_sem")
                sm.insert("end", "─" * 60 + "\n", "muted_sem")
                for w in advertencias:
                    sm.insert("end", f"  {w}\n", "warn")

        sm.configure(state="disabled")

    def _fill_errores(self, lex_errors, sin_errors, sem_errors=None):
        sem_errors = sem_errors or []
        et = self.err_text
        et.configure(state="normal")
        et.delete("1.0", "end")

        if not lex_errors and not sin_errors and not sem_errors:
            et.insert("end", "✓  Sin errores léxicos, sintácticos ni semánticos.\n", "ok")
        else:
            if lex_errors:
                et.insert("end", "ERRORES LÉXICOS\n", "head")
                et.insert("end", "─" * 60 + "\n", "ok")
                for e in lex_errors:
                    et.insert("end", f"  {e}\n", "err")
                et.insert("end", "\n")
            if sin_errors:
                et.insert("end", "ERRORES SINTÁCTICOS\n", "head")
                et.insert("end", "─" * 60 + "\n", "ok")
                for e in sin_errors:
                    et.insert("end", f"  {e}\n", "err")
                et.insert("end", "\n")
            if sem_errors:
                et.insert("end", "ERRORES SEMÁNTICOS\n", "head")
                et.insert("end", "─" * 60 + "\n", "ok")
                for e in sem_errors:
                    et.insert("end", f"  {e}\n", "err")

        et.configure(state="disabled")

    # ══════════════════════════════════════════════════════════════════════════
    #  UTILIDADES DEL EDITOR
    # ══════════════════════════════════════════════════════════════════════════

    def _on_key(self, _=None):
        self._update_line_nums()
        self._update_cursor()

    def _tab(self, e):
        self.editor.insert("insert", "    ")
        return "break"

    def _update_line_nums(self):
        new_count = int(self.editor.index("end-1c").split(".")[0])
        old_count = self._last_line_count

        if new_count != old_count:
            self.line_nums.configure(state="normal")

            if new_count > old_count:
                nuevas    = "\n".join(str(i) for i in range(old_count + 1, new_count + 1))
                separador = "\n" if old_count > 0 else ""
                self.line_nums.insert("end", separador + nuevas)
            else:
                self.line_nums.delete(f"{new_count + 1}.0", "end")

            self.line_nums.configure(state="disabled")
            self._last_line_count = new_count

        self.line_nums.yview_moveto(self.editor.yview()[0])

    def _update_cursor(self):
        pos  = self.editor.index("insert")
        l, c = pos.split(".")
        self.lbl_cursor.configure(text=f"L{l}  C{int(c)+1}")

    def _sync_scroll(self, _=None):
        self.line_nums.yview_moveto(self.editor.yview()[0])

    def limpiar(self):
        self.editor.delete("1.0", "end")
        self._last_line_count = 0

        # Borrar explícitamente el contenido del widget de números de línea
        self.line_nums.configure(state="normal")
        self.line_nums.delete("1.0", "end")
        self.line_nums.configure(state="disabled")

        self._update_line_nums()

        self.token_list.configure(state="normal")
        self.token_list.delete("1.0", "end")
        self.token_list.configure(state="disabled")

        for w in self.cards_frame.winfo_children():
            w.destroy()
        for w in self.stats_inner.winfo_children():
            w.destroy()

        self.tree_canvas.delete("all")

        self.sym_list.configure(state="normal")
        self.sym_list.delete("1.0", "end")
        self.sym_list.configure(state="disabled")

        self.sem_msg.configure(state="normal")
        self.sem_msg.delete("1.0", "end")
        self.sem_msg.configure(state="disabled")

        self.err_text.configure(state="normal")
        self.err_text.delete("1.0", "end")
        self.err_text.configure(state="disabled")

        self.lbl_status.configure(text="Listo", fg=MUTED)
        self.lbl_stats.configure(text="")
        for btn in self.tab_btns.values():
            btn.configure(fg=MUTED)

    def _apply_style(self):
        s = ttk.Style(self)
        s.theme_use("default")
        s.configure("TScrollbar", background=SURFACE, troughcolor=BG,
                    arrowcolor=MUTED, bordercolor=BG, relief="flat")

    @staticmethod
    def _ejemplo():
        return """\
def main():
    b = 0
    if b == 0:
        return "NO SE PUEDE DIVIDIR ENTRE 0"
    else:
        resultado = dividir(10, b)
        print("Resultado:", resultado)
    
    for i in range(10):
        resultado += i
    return 0

if __name__ == "__main__":
    main()
"""


# ══════════════════════════════════════════════════════════════════════════════
#  PUNTO DE ENTRADA
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = Compilador()
    app.mainloop()
    