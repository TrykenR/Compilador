"""
interfaz.py — Interfaz de escritorio del Compilador.
Requiere Python 3.8+ con Tkinter (incluido por defecto).

Ejecución:
    python interfaz.py

Módulos necesarios en la misma carpeta:
    tipos_token.py  |  reglas.py  |  analizador.py  |  sintactico.py
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from typing import List

# ── imports del compilador ────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from analizador  import analizar
from sintactico  import analizar_sintactico, Nodo

# ══════════════════════════════════════════════════════════════════════════════
#  PALETA BLANCO/NEGRO
# ══════════════════════════════════════════════════════════════════════════════

BG       = "#ffffff"   # fondo general
FG       = "#000000"   # texto principal
SURFACE  = "#f0f0f0"   # paneles secundarios
BORDER   = "#000000"   # bordes
MUTED    = "#555555"   # texto secundario
ACCENT   = "#000000"   # acento (botones)
BTN_FG   = "#ffffff"   # texto de botones
SEL_BG   = "#000000"   # selección
SEL_FG   = "#ffffff"

MONO     = ("Courier New", 11)
MONO_SM  = ("Courier New", 10)
MONO_LG  = ("Courier New", 12)
SANS     = ("Helvetica", 10)
SANS_B   = ("Helvetica", 10, "bold")
SANS_LG  = ("Helvetica", 13, "bold")

# ══════════════════════════════════════════════════════════════════════════════
#  COLORES POR TIPO DE TOKEN  (texto negro sobre fondo blanco = tags)
# ══════════════════════════════════════════════════════════════════════════════

TOKEN_TAGS = {
    "PALABRA_CLAVE":    {"font": ("Courier New", 11, "bold"),   "foreground": "#000000"},
    "IDENTIFICADOR":    {"font": ("Courier New", 11),           "foreground": "#000000"},
    "LITERAL_NUMÉRICO": {"font": ("Courier New", 11),           "foreground": "#333333"},
    "LITERAL_CADENA":   {"font": ("Courier New", 11, "italic"), "foreground": "#333333"},
    "LITERAL_BOOL":     {"font": ("Courier New", 11, "bold"),   "foreground": "#000000"},
    "LITERAL_NULO":     {"font": ("Courier New", 11, "italic"), "foreground": "#555555"},
    "OPERADOR_ASIG":    {"font": ("Courier New", 11, "bold"),   "foreground": "#000000"},
    "OPERADOR_REL":     {"font": ("Courier New", 11, "bold"),   "foreground": "#000000"},
    "OPERADOR_LOG":     {"font": ("Courier New", 11, "bold"),   "foreground": "#000000"},
    "OPERADOR_ARIT":    {"font": ("Courier New", 11),           "foreground": "#000000"},
    "DELIMITADOR":      {"font": ("Courier New", 11),           "foreground": "#555555"},
    "DESCONOCIDO":      {"font": ("Courier New", 11),           "foreground": "#ff0000"},
}

# ══════════════════════════════════════════════════════════════════════════════
#  VENTANA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

class Compilador(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Compilador — Léxico & Sintáctico")
        self.configure(bg=BG)
        self.geometry("1200x700")
        self.minsize(900, 560)

        self._build_ui()
        self._apply_style()

    # ── construcción de la UI ─────────────────────────────────────────────────

    def _build_ui(self):
        # ── barra superior ────────────────────
        top = tk.Frame(self, bg=BG, pady=8, padx=16)
        top.pack(fill="x", side="top")

        tk.Label(top, text="COMPILADOR", font=("Helvetica", 14, "bold"),
                 bg=BG, fg=FG).pack(side="left")
        tk.Label(top, text="  Léxico · Sintáctico", font=("Helvetica", 10),
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

        # ── separador ─────────────────────────
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        # ── cuerpo principal ──────────────────
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        # editor izquierda
        self._build_editor(body)

        # separador vertical
        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y")

        # resultados derecha
        self._build_results(body)

        # ── barra de estado ───────────────────
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

        # header del panel
        hdr = tk.Frame(frame, bg=SURFACE, pady=5, padx=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="CÓDIGO FUENTE", font=MONO_SM,
                 bg=SURFACE, fg=MUTED).pack(side="left")
        self.lbl_cursor = tk.Label(hdr, text="L1  C1", font=MONO_SM,
                                   bg=SURFACE, fg=MUTED)
        self.lbl_cursor.pack(side="right")

        # números de línea + editor
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

        # scrollbar horizontal
        hscroll = tk.Scrollbar(frame, orient="horizontal",
                               command=self.editor.xview)
        hscroll.pack(fill="x")
        self.editor.configure(xscrollcommand=hscroll.set)

        # texto inicial de ejemplo
        self.editor.insert("1.0", self._ejemplo())

        # eventos
        self.editor.bind("<KeyRelease>", self._on_key)
        self.editor.bind("<ButtonRelease>", self._on_key)
        self.editor.bind("<Control-Return>", lambda e: self.run())
        self.editor.bind("<Tab>", self._tab)
        self.editor.bind("<MouseWheel>", self._sync_scroll)
        self.editor.bind("<Button-4>",   self._sync_scroll)
        self.editor.bind("<Button-5>",   self._sync_scroll)
        self._update_line_nums()

    def _build_results(self, parent):
        frame = tk.Frame(parent, bg=BG)
        frame.pack(side="left", fill="both", expand=True)

        # pestañas
        tab_bar = tk.Frame(frame, bg=SURFACE)
        tab_bar.pack(fill="x")

        self.tab_btns = {}
        self.current_tab = tk.StringVar(value="tokens")
        for nombre, label in [("tokens","Tokens"), ("stats","Estadísticas"),
                               ("arbol","Árbol Sint."), ("errores","Errores")]:
            btn = tk.Button(
                tab_bar, text=label, font=SANS,
                bg=SURFACE, fg=MUTED, relief="flat",
                padx=14, pady=6, cursor="hand2",
                command=lambda n=nombre: self._show_tab(n)
            )
            btn.pack(side="left")
            self.tab_btns[nombre] = btn

        tk.Frame(tab_bar, bg=BORDER, height=1).pack(side="bottom", fill="x")

        # contenedor de pestañas
        self.tab_frame = tk.Frame(frame, bg=BG)
        self.tab_frame.pack(fill="both", expand=True)

        self._build_tab_tokens()
        self._build_tab_stats()
        self._build_tab_arbol()
        self._build_tab_errores()

        self._show_tab("tokens")

    # ── pestañas ──────────────────────────────────────────────────────────────

    def _build_tab_tokens(self):
        f = tk.Frame(self.tab_frame, bg=BG)
        self.tab_frames = {"tokens": f}

        # encabezado de columnas
        hdr = tk.Frame(f, bg=SURFACE, pady=4, padx=8)
        hdr.pack(fill="x")
        for txt, w in [("TIPO", 22), ("VALOR", 22), ("APARICIONES", 12)]:
            tk.Label(hdr, text=txt, font=("Courier New", 9, "bold"),
                     bg=SURFACE, fg=MUTED, width=w, anchor="w").pack(side="left")

        tk.Frame(f, bg=BORDER, height=1).pack(fill="x")

        # lista con scrollbar
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

        # registrar tags visuales
        for tipo, cfg in TOKEN_TAGS.items():
            self.token_list.tag_configure(tipo, **cfg)
        self.token_list.tag_configure("muted",  foreground=MUTED)
        self.token_list.tag_configure("sep",     foreground="#cccccc")
        self.token_list.tag_configure("stripe",  background="#f8f8f8")

    def _build_tab_stats(self):
        f = tk.Frame(self.tab_frame, bg=BG)
        self.tab_frames["stats"] = f

        # tarjetas de resumen
        self.cards_frame = tk.Frame(f, bg=BG, pady=12, padx=16)
        self.cards_frame.pack(fill="x")

        tk.Frame(f, bg=BORDER, height=1).pack(fill="x", padx=16)

        tk.Label(f, text="DISTRIBUCIÓN POR CATEGORÍA",
                 font=("Courier New", 9, "bold"), bg=BG, fg=MUTED,
                 anchor="w", padx=16, pady=8).pack(fill="x")

        # canvas para barras
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
        self.stats_canvas.create_window((0,0), window=self.stats_inner, anchor="nw")
        self.stats_inner.bind("<Configure>",
            lambda e: self.stats_canvas.configure(
                scrollregion=self.stats_canvas.bbox("all")))

    def _build_tab_arbol(self):
        f = tk.Frame(self.tab_frame, bg=BG)
        self.tab_frames["arbol"] = f

        # canvas scrollable para el árbol
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
            self.tree_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

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

    # ── cambio de pestaña ─────────────────────────────────────────────────────

    def _show_tab(self, nombre):
        for n, frm in self.tab_frames.items():
            frm.pack_forget()
        self.tab_frames[nombre].pack(fill="both", expand=True)
        for n, btn in self.tab_btns.items():
            if n == nombre:
                btn.configure(bg=BG, fg=FG, font=SANS_B,
                              relief="groove")
            else:
                btn.configure(bg=SURFACE, fg=MUTED, font=SANS,
                              relief="flat")
        self.current_tab.set(nombre)

    # ── ANÁLISIS ─────────────────────────────────────────────────────────────

    def run(self, _=None):
        codigo = self.editor.get("1.0", "end-1c")
        if not codigo.strip():
            return

        # léxico
        tokens_unicos, frecuencias, lex_errors = analizar(codigo)

        # para el sintáctico necesitamos todos los tokens (sin deduplicar)
        # reutilizamos el mismo analizador con código completo
        from analizador import analizar as _analizar_full
        # Reconstruir lista completa sin dedup para el parser
        tokens_full = _tokens_sin_dedup(codigo)
        arbol, sin_errors = analizar_sintactico(tokens_full)

        all_errors = lex_errors + sin_errors

        # poblar vistas
        self._fill_tokens(tokens_unicos, frecuencias)
        self._fill_stats(tokens_unicos, frecuencias, all_errors)
        self._fill_arbol(arbol, sin_errors)
        self._fill_errores(lex_errors, sin_errors)

        # estado
        total_ap = sum(frecuencias.values())
        if all_errors:
            self.lbl_status.configure(
                text=f"⚠  {len(all_errors)} error(es) encontrado(s)", fg="#cc0000")
        else:
            self.lbl_status.configure(
                text="✓  Análisis completado sin errores", fg=MUTED)
        self.lbl_stats.configure(
            text=f"{len(tokens_unicos)} tokens únicos  ·  {total_ap} apariciones")

        # resaltar tab errores si hay errores
        self.tab_btns["errores"].configure(
            fg="#cc0000" if all_errors else MUTED)

    # ── LLENAR TOKENS ─────────────────────────────────────────────────────────

    def _fill_tokens(self, tokens, frecuencias):
        tl = self.token_list
        tl.configure(state="normal")
        tl.delete("1.0", "end")

        max_freq = max((v for v in frecuencias.values()), default=1)

        for i, tok in enumerate(tokens):
            clave = f"{tok.tipo}|||{tok.valor}"
            freq  = frecuencias.get(clave, 1)
            tag   = tok.tipo if tok.tipo in TOKEN_TAGS else "muted"

            # columna tipo
            tipo_txt = f"{tok.tipo:<22}"
            tl.insert("end", tipo_txt, tag)

            # columna valor
            valor_txt = f"  {tok.valor:<22}"
            tl.insert("end", valor_txt, tag)

            # columna apariciones: barra simple
            bar_filled = round((freq / max_freq) * 16)
            bar = "█" * bar_filled + "░" * (16 - bar_filled)
            tl.insert("end", f"  {freq:>3}  ", "muted")
            tl.insert("end", bar, tag)
            tl.insert("end", "\n")

        if not tokens:
            tl.insert("end", "  Sin tokens encontrados\n", "muted")

        tl.configure(state="disabled")

    # ── LLENAR ESTADÍSTICAS ───────────────────────────────────────────────────

    def _fill_stats(self, tokens, frecuencias, errores):
        # tarjetas
        for w in self.cards_frame.winfo_children():
            w.destroy()

        total_ap  = sum(frecuencias.values())
        cats      = {}
        for tok in tokens:
            cats[tok.tipo] = cats.get(tok.tipo, 0) + 1

        resumen = [
            ("Tokens únicos",   str(len(tokens))),
            ("Total aparic.",   str(total_ap)),
            ("Categorías",      str(len(cats))),
            ("Errores",         str(len(errores))),
        ]
        for label, val in resumen:
            card = tk.Frame(self.cards_frame, bg=SURFACE,
                            relief="solid", bd=1, padx=16, pady=10)
            card.pack(side="left", padx=8, pady=4)
            tk.Label(card, text=val, font=("Helvetica", 22, "bold"),
                     bg=SURFACE, fg=FG).pack()
            tk.Label(card, text=label, font=("Courier New", 9),
                     bg=SURFACE, fg=MUTED).pack()

        # barras
        for w in self.stats_inner.winfo_children():
            w.destroy()

        if not cats:
            return

        max_cnt = max(cats.values())
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
            c.create_rectangle(0, 4, max(bar_w, 2), 14,
                                fill=FG, outline="")
            c.create_rectangle(bar_w, 4, 220, 14,
                                fill=SURFACE, outline="")

            tk.Label(row, text=f"{cnt:>4}", font=MONO_SM,
                     bg=BG, fg=MUTED, width=4).pack(side="left", padx=6)

    # ── LLENAR ÁRBOL SINTÁCTICO ────────────────────────────────────────────────

    def _fill_arbol(self, raiz: Nodo, errores: List[str]):
        canvas = self.tree_canvas
        canvas.delete("all")

        # calcular posiciones con DFS
        NODE_W, NODE_H = 110, 26
        H_GAP, V_GAP   = 18,  52

        posiciones = {}   # id(nodo) → (cx, cy)

        def layout(nodo: Nodo, profundidad: int, x_offset: float):
            if not nodo.hijos:
                posiciones[id(nodo)] = (x_offset, profundidad * V_GAP)
                return x_offset, x_offset + NODE_W
            x_ini = x_offset
            child_centers = []
            for hijo in nodo.hijos:
                _, x_fin = layout(hijo, profundidad + 1, x_offset)
                cx = posiciones[id(hijo)][0]
                child_centers.append(cx)
                x_offset = x_fin + H_GAP
            mid = (child_centers[0] + child_centers[-1]) / 2
            posiciones[id(nodo)] = (mid, profundidad * V_GAP)
            return x_ini, x_offset - H_GAP

        layout(raiz, 0, 20)

        # márgenes
        all_x = [p[0] for p in posiciones.values()]
        all_y = [p[1] for p in posiciones.values()]
        total_w = max(all_x) + NODE_W + 40
        total_h = max(all_y) + NODE_H + 40

        canvas.configure(scrollregion=(0, 0, total_w, total_h))

        # dibujar aristas primero
        def draw_edges(nodo):
            px, py = posiciones[id(nodo)]
            pcx = px + NODE_W // 2
            pcy = py + NODE_H
            for hijo in nodo.hijos:
                hx, hy = posiciones[id(hijo)]
                hcx = hx + NODE_W // 2
                canvas.create_line(
                    pcx, pcy, hcx, hy,
                    fill="#888888", width=1
                )
                draw_edges(hijo)

        draw_edges(raiz)

        # dibujar nodos
        def draw_nodes(nodo):
            x, y = posiciones[id(nodo)]
            etq = nodo.etiqueta
            if len(etq) > 14:
                etq = etq[:13] + "…"

            # estilo según tipo
            if nodo.etiqueta == "programa":
                bg_col, fg_col, borde = "#000000", "#ffffff", "#000000"
            elif nodo.etiqueta in ("bloque",):
                bg_col, fg_col, borde = "#333333", "#ffffff", "#000000"
            elif nodo.etiqueta.startswith(("if","while","for","return")):
                bg_col, fg_col, borde = "#555555", "#ffffff", "#000000"
            elif nodo.etiqueta.startswith(("decl ","func ","asig")):
                bg_col, fg_col, borde = "#f0f0f0", "#000000", "#000000"
            elif nodo.etiqueta in ("condición","else","init","cond","inc"):
                bg_col, fg_col, borde = "#dddddd", "#000000", "#888888"
            else:
                bg_col, fg_col, borde = "#ffffff", "#000000", "#aaaaaa"

            canvas.create_rectangle(
                x, y, x + NODE_W, y + NODE_H,
                fill=bg_col, outline=borde, width=1
            )
            canvas.create_text(
                x + NODE_W // 2, y + NODE_H // 2,
                text=etq,
                font=("Courier New", 9),
                fill=fg_col, anchor="center"
            )
            for hijo in nodo.hijos:
                draw_nodes(hijo)

        draw_nodes(raiz)

        # nota de errores encima del árbol
        if errores:
            canvas.create_text(
                10, total_h - 10,
                text=f"⚠  {len(errores)} error(es) sintáctico(s) — árbol puede ser parcial",
                font=("Courier New", 9), fill="#cc0000", anchor="sw"
            )

    # ── LLENAR ERRORES ────────────────────────────────────────────────────────

    def _fill_errores(self, lex_errors, sin_errors):
        et = self.err_text
        et.configure(state="normal")
        et.delete("1.0", "end")

        if not lex_errors and not sin_errors:
            et.insert("end", "✓  Sin errores léxicos ni sintácticos.\n", "ok")
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

        et.configure(state="disabled")

    # ── UTILIDADES EDITOR ─────────────────────────────────────────────────────

    def _on_key(self, _=None):
        self._update_line_nums()
        self._update_cursor()

    def _tab(self, e):
        self.editor.insert("insert", "    ")
        return "break"

    def _update_line_nums(self):
        """Actualiza números de línea de forma incremental.

        En lugar de borrar y reescribir todo el widget en cada tecla
        (lo que congela Tkinter con muchas líneas), solo agrega o quita
        las líneas que cambiaron respecto al estado anterior.
        """
        new_count = int(self.editor.index("end-1c").split(".")[0])
        old_count = getattr(self, "_last_line_count", 0)

        if new_count != old_count:
            self.line_nums.configure(state="normal")

            if new_count > old_count:
                # Agregar solo las líneas nuevas al final
                nuevas = "\n".join(str(i) for i in range(old_count + 1, new_count + 1))
                separador = "\n" if old_count > 0 else ""
                self.line_nums.insert("end", separador + nuevas)
            else:
                # Eliminar solo las líneas sobrantes desde el final
                self.line_nums.delete(f"{new_count + 1}.0", "end")

            self.line_nums.configure(state="disabled")
            self._last_line_count = new_count

        # Sincronizar scroll siempre
        self.line_nums.yview_moveto(self.editor.yview()[0])

    def _update_cursor(self):
        pos   = self.editor.index("insert")
        l, c  = pos.split(".")
        self.lbl_cursor.configure(text=f"L{l}  C{int(c)+1}")

    def _sync_scroll(self, e):
        self.line_nums.yview_moveto(self.editor.yview()[0])

    def limpiar(self):
        self.editor.delete("1.0", "end")
        self._update_line_nums()
        self.token_list.configure(state="normal")
        self.token_list.delete("1.0", "end")
        self.token_list.configure(state="disabled")
        for w in self.cards_frame.winfo_children():
            w.destroy()
        for w in self.stats_inner.winfo_children():
            w.destroy()
        self.tree_canvas.delete("all")
        self.err_text.configure(state="normal")
        self.err_text.delete("1.0", "end")
        self.err_text.configure(state="disabled")
        self.lbl_status.configure(text="Listo", fg=MUTED)
        self.lbl_stats.configure(text="")

    # ── ESTILO TTK ────────────────────────────────────────────────────────────

    def _apply_style(self):
        s = ttk.Style(self)
        s.theme_use("default")
        s.configure("TScrollbar", background=SURFACE, troughcolor=BG,
                    arrowcolor=MUTED, bordercolor=BG, relief="flat")

    # ── EJEMPLO ───────────────────────────────────────────────────────────────

    @staticmethod
    def _ejemplo():
        return """\
int main() {
    int b = 0;
    float resultado;
    if (b == 0) {
        return "NO SE PUEDE DIVIDIR ENTRE 0";
    } else {
        resultado = dividir(10, b);
        printf("Resultado: ", resultado);
    }
    for (int i = 0; i < 10; i++) {
        resultado += i;
    }
    return 0;
}"""


# ══════════════════════════════════════════════════════════════════════════════
#  TOKENIZAR SIN DEDUPLICAR (para el parser)
# ══════════════════════════════════════════════════════════════════════════════

def _tokens_sin_dedup(codigo: str):
    """Versión del léxico que retorna TODOS los tokens (con repetidos)."""
    import re
    from tipos_token import (Token, PALABRAS_CLAVE,
                             LITERALES_BOOLEANOS, LITERALES_NULOS)
    from reglas import PATRON_MAESTRO

    tokens = []
    linea = 1
    inicio_linea = 0

    for match in PATRON_MAESTRO.finditer(codigo):
        tipo  = match.lastgroup
        valor = match.group()
        col   = match.start() - inicio_linea + 1

        if tipo == 'NUEVA_LÍNEA':
            linea += 1; inicio_linea = match.end(); continue
        if tipo == 'SEPARADOR': continue
        if tipo in ('COMENTARIO_LINEA', 'COMENTARIO_MULTILINEA'):
            linea += valor.count('\n'); continue

        if tipo == 'IDENTIFICADOR':
            if valor in PALABRAS_CLAVE:         tipo = 'PALABRA_CLAVE'
            elif valor in LITERALES_BOOLEANOS:  tipo = 'LITERAL_BOOL'
            elif valor in LITERALES_NULOS:      tipo = 'LITERAL_NULO'

        tokens.append(Token(tipo, valor, linea, col))

    return tokens


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRADA
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = Compilador()
    app.mainloop()
    