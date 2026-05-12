import sys
import os
import tkinter as tk
from tkinter import ttk
from typing import List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analizador import analizar, analizar_completo
from sintactico import analizar_sintactico, Nodo
from semantico import analizar_semantico


# ══════════════════════════════════════════════════════════════════════════════
#  PALETA DE COLORES Y TIPOGRAFÍA
# ══════════════════════════════════════════════════════════════════════════════

BG      = "#1e1e2e"   # fondo editor (oscuro)
BG_UI   = "#ffffff"   # fondo UI general
FG      = "#cdd6f4"   # texto base del editor
SURFACE = "#f0f0f0"
BORDER  = "#d0d0d0"
MUTED   = "#666666"
ACCENT  = "#1a1a2e"
BTN_FG  = "#ffffff"
SEL_BG  = "#44475a"
SEL_FG  = "#f8f8f2"

MONO    = ("Courier New", 11)
MONO_SM = ("Courier New", 10)
MONO_LG = ("Courier New", 12)
SANS    = ("Helvetica", 10)
SANS_B  = ("Helvetica", 10, "bold")

# ══════════════════════════════════════════════════════════════════════════════
#  COLORES SYNTAX HIGHLIGHTING
#  Paleta Dracula / VS Code Dark+:
#    Palabras clave estructurales → púrpura bold   #bd93f9
#    Builtins (print, len, range) → cian           #8be9fd
#    Identificadores usuario      → blanco humo    #f8f8f2
#    Números                      → naranja        #ffb86c
#    Cadenas                      → verde          #50fa7b
#    Booleanos / None             → naranja bold   #ffb86c bold
#    Operadores                   → rosa           #ff79c6
#    Operadores lógicos           → púrpura bold   #bd93f9
#    Delimitadores                → gris claro     #cccccc
#    Comentarios                  → gris azulado   #6272a4 italic
#    Errores                      → rojo           #ff5555
# ══════════════════════════════════════════════════════════════════════════════

SH: dict = {
    "PALABRA_CLAVE":    {"foreground": "#bd93f9", "font": ("Courier New", 12, "bold")},
    "BUILTIN":          {"foreground": "#8be9fd", "font": ("Courier New", 12)},
    "IDENTIFICADOR":    {"foreground": "#f8f8f2", "font": ("Courier New", 12)},
    "LITERAL_NUM":      {"foreground": "#ffb86c", "font": ("Courier New", 12)},
    "LITERAL_CADENA":   {"foreground": "#50fa7b", "font": ("Courier New", 12)},
    "LITERAL_BOOLEANO": {"foreground": "#ffb86c", "font": ("Courier New", 12, "bold")},
    "LITERAL_NULO":     {"foreground": "#ffb86c", "font": ("Courier New", 12, "italic")},
    "OPERADOR_ASIG":    {"foreground": "#ff79c6", "font": ("Courier New", 12)},
    "OPERADOR_REL":     {"foreground": "#ff79c6", "font": ("Courier New", 12)},
    "OPERADOR_LOG":     {"foreground": "#bd93f9", "font": ("Courier New", 12, "bold")},
    "OPERADOR_ARIT":    {"foreground": "#ff79c6", "font": ("Courier New", 12)},
    "OPERADOR_INCR":    {"foreground": "#ff79c6", "font": ("Courier New", 12, "bold")},
    "OPERADOR_BIT":     {"foreground": "#ff79c6", "font": ("Courier New", 12)},
    "DELIMITADOR":      {"foreground": "#cccccc", "font": ("Courier New", 12)},
    "COMENTARIO":       {"foreground": "#6272a4", "font": ("Courier New", 12, "italic")},
    "DESCONOCIDO":      {"foreground": "#ff5555", "font": ("Courier New", 12)},
}

# Color de barra en Estadísticas (mismo color que el editor para coherencia)
CAT_COLOR: dict = {
    "PALABRA_CLAVE":    "#bd93f9",
    "BUILTIN":          "#8be9fd",
    "IDENTIFICADOR":    "#f8f8f2",
    "LITERAL_NUM":      "#ffb86c",
    "LITERAL_CADENA":   "#50fa7b",
    "LITERAL_BOOLEANO": "#ffb86c",
    "LITERAL_NULO":     "#ffb86c",
    "OPERADOR_ASIG":    "#ff79c6",
    "OPERADOR_REL":     "#ff79c6",
    "OPERADOR_LOG":     "#bd93f9",
    "OPERADOR_ARIT":    "#ff79c6",
    "OPERADOR_INCR":    "#ff79c6",
    "OPERADOR_BIT":     "#ff79c6",
    "DELIMITADOR":      "#888888",
    "DESCONOCIDO":      "#ff5555",
}

# ══════════════════════════════════════════════════════════════════════════════
#  ESTILOS SEMÁNTICOS
# ══════════════════════════════════════════════════════════════════════════════

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
        self.configure(bg=BG_UI)
        self.geometry("1280x720")
        self.minsize(960, 580)
        self._last_line_count = 0
        self._highlight_job   = None
        self._build_ui()
        self._apply_style()
        self.after(100, self._highlight_now)

    # ══════════════════════════════════════════════════════════════════════════
    #  CONSTRUCCIÓN DE LA UI
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        top = tk.Frame(self, bg=BG_UI, pady=8, padx=16)
        top.pack(fill="x", side="top")

        tk.Label(top, text="COMPILADOR", font=("Helvetica", 14, "bold"),
                 bg=BG_UI, fg="#1a1a2e").pack(side="left")
        tk.Label(top, text="  Léxico · Sintáctico · Semántico", font=("Helvetica", 10),
                 bg=BG_UI, fg=MUTED).pack(side="left")

        self.btn_run = tk.Button(
            top, text="▶  Analizar  (Ctrl+Enter)",
            font=SANS_B, bg=ACCENT, fg=BTN_FG,
            relief="flat", padx=14, pady=4, cursor="hand2",
            command=self.run
        )
        self.btn_run.pack(side="right")

        tk.Button(
            top, text="Limpiar", font=SANS, bg=SURFACE, fg="#1a1a2e",
            relief="flat", padx=10, pady=4, cursor="hand2",
            command=self.limpiar
        ).pack(side="right", padx=8)

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        body = tk.Frame(self, bg=BG_UI)
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

        hdr = tk.Frame(frame, bg="#13131f", pady=5, padx=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="CÓDIGO FUENTE", font=MONO_SM,
                 bg="#13131f", fg="#6272a4").pack(side="left")
        self.lbl_cursor = tk.Label(hdr, text="L1  C1", font=MONO_SM,
                                   bg="#13131f", fg="#6272a4")
        self.lbl_cursor.pack(side="right")

        edit_frame = tk.Frame(frame, bg=BG)
        edit_frame.pack(fill="both", expand=True)

        self.line_nums = tk.Text(
            edit_frame, width=4, bg="#13131f", fg="#44475a",
            font=MONO, state="disabled", relief="flat",
            padx=4, takefocus=False, cursor="arrow"
        )
        self.line_nums.pack(side="left", fill="y")
        tk.Frame(edit_frame, bg="#44475a", width=1).pack(side="left", fill="y")

        self.editor = tk.Text(
            edit_frame, wrap="none", bg=BG, fg=FG,
            font=MONO_LG, relief="flat", padx=12, pady=8,
            insertbackground="#f8f8f2",
            selectbackground=SEL_BG,
            selectforeground=SEL_FG,
            undo=True
        )
        self.editor.pack(side="left", fill="both", expand=True)

        vsb = tk.Scrollbar(edit_frame, orient="vertical",
                           command=self._on_vscroll)
        vsb.pack(side="right", fill="y")
        self.editor.configure(yscrollcommand=vsb.set)

        hscroll = tk.Scrollbar(frame, orient="horizontal",
                               command=self.editor.xview)
        hscroll.pack(fill="x")
        self.editor.configure(xscrollcommand=hscroll.set)

        # Registrar todos los tags de syntax highlighting
        for tipo, cfg in SH.items():
            self.editor.tag_configure(tipo, **cfg)

        self.editor.insert("1.0", self._ejemplo())

        self.editor.bind("<KeyRelease>",     self._on_key)
        self.editor.bind("<ButtonRelease>",  self._on_key)
        self.editor.bind("<Control-Return>", lambda e: self.run())
        self.editor.bind("<Tab>",            self._tab)
        self.editor.bind("<MouseWheel>",     self._sync_scroll)
        self.editor.bind("<Button-4>",       self._sync_scroll)
        self.editor.bind("<Button-5>",       self._sync_scroll)

        self._update_line_nums()

    def _on_vscroll(self, *args):
        self.editor.yview(*args)
        self.line_nums.yview(*args)

    def _build_results(self, parent):
        frame = tk.Frame(parent, bg=BG_UI)
        frame.pack(side="left", fill="both", expand=True)

        tab_bar = tk.Frame(frame, bg=SURFACE)
        tab_bar.pack(fill="x")

        self.tab_btns    = {}
        self.tab_frames  = {}
        self.current_tab = tk.StringVar(value="stats")

        pestanas = [
            ("stats",     "Estadísticas"),
            ("arbol",     "Árbol Sint."),
            ("semantico", "Semántico"),
            ("errores",   "Errores"),
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

        self.tab_frame = tk.Frame(frame, bg=BG_UI)
        self.tab_frame.pack(fill="both", expand=True)

        self._build_tab_stats()
        self._build_tab_arbol()
        self._build_tab_semantico()
        self._build_tab_errores()

        self._show_tab("stats")

    # ── Construcción de pestañas ──────────────────────────────────────────────

    def _build_tab_stats(self):
        f = tk.Frame(self.tab_frame, bg=BG_UI)
        self.tab_frames["stats"] = f

        self.cards_frame = tk.Frame(f, bg=BG_UI, pady=12, padx=16)
        self.cards_frame.pack(fill="x")

        tk.Frame(f, bg=BORDER, height=1).pack(fill="x", padx=16)
        tk.Label(f, text="DISTRIBUCIÓN POR CATEGORÍA",
                 font=("Courier New", 9, "bold"), bg=BG_UI, fg=MUTED,
                 anchor="w", padx=16, pady=8).pack(fill="x")

        bar_wrap = tk.Frame(f, bg=BG_UI)
        bar_wrap.pack(fill="both", expand=True)
        vsb = tk.Scrollbar(bar_wrap, orient="vertical")
        vsb.pack(side="right", fill="y")

        self.stats_canvas = tk.Canvas(bar_wrap, bg=BG_UI, relief="flat",
                                      highlightthickness=0,
                                      yscrollcommand=vsb.set)
        self.stats_canvas.pack(fill="both", expand=True)
        vsb.config(command=self.stats_canvas.yview)

        self.stats_inner = tk.Frame(self.stats_canvas, bg=BG_UI)
        self.stats_canvas.create_window((0, 0), window=self.stats_inner, anchor="nw")
        self.stats_inner.bind("<Configure>",
            lambda e: self.stats_canvas.configure(
                scrollregion=self.stats_canvas.bbox("all")))

    def _build_tab_arbol(self):
        f = tk.Frame(self.tab_frame, bg=BG_UI)
        self.tab_frames["arbol"] = f

        wrap = tk.Frame(f, bg=BG_UI)
        wrap.pack(fill="both", expand=True)

        vsb = tk.Scrollbar(wrap, orient="vertical")
        hsb = tk.Scrollbar(wrap, orient="horizontal")
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")

        self.tree_canvas = tk.Canvas(
            wrap, bg=BG_UI, relief="flat", highlightthickness=0,
            yscrollcommand=vsb.set, xscrollcommand=hsb.set
        )
        self.tree_canvas.pack(fill="both", expand=True)
        vsb.config(command=self.tree_canvas.yview)
        hsb.config(command=self.tree_canvas.xview)

        self.tree_canvas.bind("<MouseWheel>", lambda e:
            self.tree_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    def _build_tab_semantico(self):
        f = tk.Frame(self.tab_frame, bg=BG_UI)
        self.tab_frames["semantico"] = f

        hdr = tk.Frame(f, bg=SURFACE, pady=4, padx=8)
        hdr.pack(fill="x")
        for txt, w in [("SÍMBOLO", 20), ("TIPO", 10), ("CATEGORÍA", 14), ("LÍNEA", 7), ("USADO", 7)]:
            tk.Label(hdr, text=txt, font=("Courier New", 9, "bold"),
                     bg=SURFACE, fg=MUTED, width=w, anchor="w").pack(side="left")
        tk.Frame(f, bg=BORDER, height=1).pack(fill="x")

        sym_frame = tk.Frame(f, bg=BG_UI)
        sym_frame.pack(fill="both", expand=True)
        vsb1 = tk.Scrollbar(sym_frame, orient="vertical")
        vsb1.pack(side="right", fill="y")

        self.sym_list = tk.Text(
            sym_frame, wrap="none", bg=BG_UI, fg="#000000",
            font=MONO_SM, relief="flat", padx=8, pady=4,
            state="disabled", yscrollcommand=vsb1.set,
            cursor="arrow", height=10
        )
        self.sym_list.pack(fill="both", expand=True)
        vsb1.config(command=self.sym_list.yview)

        for tag, cfg in SEM_TAGS.items():
            self.sym_list.tag_configure(tag, **cfg)

        tk.Frame(f, bg=BORDER, height=1).pack(fill="x")
        tk.Label(f, text="ADVERTENCIAS Y ERRORES SEMÁNTICOS",
                 font=("Courier New", 9, "bold"), bg=BG_UI, fg=MUTED,
                 anchor="w", padx=8, pady=6).pack(fill="x")
        tk.Frame(f, bg=BORDER, height=1).pack(fill="x")

        msg_frame = tk.Frame(f, bg=BG_UI)
        msg_frame.pack(fill="both", expand=True)
        vsb2 = tk.Scrollbar(msg_frame, orient="vertical")
        vsb2.pack(side="right", fill="y")

        self.sem_msg = tk.Text(
            msg_frame, wrap="word", bg=BG_UI, fg="#000000",
            font=MONO_SM, relief="flat", padx=8, pady=4,
            state="disabled", yscrollcommand=vsb2.set,
            cursor="arrow"
        )
        self.sem_msg.pack(fill="both", expand=True)
        vsb2.config(command=self.sem_msg.yview)

        for tag, cfg in SEM_TAGS.items():
            self.sem_msg.tag_configure(tag, **cfg)

    def _build_tab_errores(self):
        f = tk.Frame(self.tab_frame, bg=BG_UI)
        self.tab_frames["errores"] = f

        wrap = tk.Frame(f, bg=BG_UI)
        wrap.pack(fill="both", expand=True)
        vsb = tk.Scrollbar(wrap, orient="vertical")
        vsb.pack(side="right", fill="y")

        self.err_text = tk.Text(
            wrap, wrap="word", bg=BG_UI, fg="#000000",
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
                btn.configure(bg=BG_UI, fg="#1a1a2e", font=SANS_B, relief="groove")
            else:
                btn.configure(bg=SURFACE, fg=MUTED, font=SANS, relief="flat")
        self.current_tab.set(nombre)

    # ══════════════════════════════════════════════════════════════════════════
    #  SYNTAX HIGHLIGHTING EN TIEMPO REAL
    # ══════════════════════════════════════════════════════════════════════════

    def _schedule_highlight(self):
        """Programa el resaltado con debounce de 80 ms para no saturar la UI."""
        if self._highlight_job is not None:
            self.after_cancel(self._highlight_job)
        self._highlight_job = self.after(80, self._highlight_now)

    def _highlight_now(self):
        """
        Aplica syntax highlighting completo al editor.
        Usa PATRON_MAESTRO y _clasificar_identificador del analizador léxico,
        garantizando que los colores son 100% coherentes con el análisis.
        """
        self._highlight_job = None
        codigo = self.editor.get("1.0", "end-1c")

        # Limpiar tags anteriores
        for tipo in SH:
            self.editor.tag_remove(tipo, "1.0", "end")

        if not codigo.strip():
            return

        try:
            from reglas import PATRON_MAESTRO
            from analizador import _clasificar_identificador

            _NORM = {
                'OPERADOR_ASIGNACIÓN': 'OPERADOR_ASIG',
                'OPERADOR_RELACIONAL': 'OPERADOR_REL',
                'OPERADOR_LÓGICO':     'OPERADOR_LOG',
                'OPERADOR_ARITMÉTICO': 'OPERADOR_ARIT',
                'OPERADOR_INCREMENTO': 'OPERADOR_INCR',
                'OPERADOR_BITWISE':    'OPERADOR_BIT',
                'LITERAL_NUMÉRICO':    'LITERAL_NUM',
            }

            linea        = 1
            inicio_linea = 0

            for match in PATRON_MAESTRO.finditer(codigo):
                tipo  = match.lastgroup
                valor = match.group()

                # ── Saltos de línea ────────────────────────────────────────
                if tipo == 'NUEVA_LÍNEA':
                    linea += 1
                    inicio_linea = match.end()
                    continue

                if tipo == 'SEPARADOR':
                    continue

                # ── Comentarios: resaltar span completo ────────────────────
                if tipo in ('COMENTARIO_LINEA', 'COMENTARIO_MULTILINEA'):
                    col_ini   = match.start() - inicio_linea
                    start_idx = f"{linea}.{col_ini}"

                    saltos = valor.replace('\r\n', '\n').replace('\r', '\n').count('\n')
                    if saltos == 0:
                        end_idx = f"{linea}.{col_ini + len(valor)}"
                    else:
                        ultimo  = max(valor.rfind('\n'), valor.rfind('\r'))
                        end_col = len(valor) - ultimo - 1
                        end_idx = f"{linea + saltos}.{end_col}"

                    self.editor.tag_add("COMENTARIO", start_idx, end_idx)

                    linea += saltos
                    if '\n' in valor or '\r' in valor:
                        ultimo = max(valor.rfind('\n'), valor.rfind('\r'))
                        inicio_linea = match.start() + ultimo + 1
                    continue

                # ── Normalizar y clasificar ────────────────────────────────
                tipo = _NORM.get(tipo, tipo)

                if tipo == 'IDENTIFICADOR':
                    tipo = _clasificar_identificador(valor)

                if tipo not in SH:
                    continue

                # ── Aplicar tag en el widget ───────────────────────────────
                col       = match.start() - inicio_linea
                start_idx = f"{linea}.{col}"
                end_idx   = f"{linea}.{col + len(valor)}"
                self.editor.tag_add(tipo, start_idx, end_idx)

        except Exception:
            pass  # No romper la UI si algo falla internamente

    # ══════════════════════════════════════════════════════════════════════════
    #  ANÁLISIS PRINCIPAL
    # ══════════════════════════════════════════════════════════════════════════

    def run(self, _=None):
        codigo = self.editor.get("1.0", "end-1c")
        if not codigo.strip():
            return

        self._highlight_now()

        try:
            tokens_unicos, frecuencias, lex_errors = analizar(codigo)
            tokens_full, _ = analizar_completo(codigo)

            arbol, sin_errors = analizar_sintactico(tokens_full)
            tabla, sem_warns, sem_errors = analizar_semantico(arbol)

            all_errors = lex_errors + sin_errors + sem_errors

            self._fill_stats(tokens_unicos, frecuencias, all_errors)
            self._fill_arbol(arbol, sin_errors)
            self._fill_semantico(tabla, sem_warns, sem_errors)
            self._fill_errores(lex_errors, sin_errors, sem_errors)

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

            self.tab_btns["errores"].configure(
                fg="#cc0000" if all_errors else MUTED)
            self.tab_btns["semantico"].configure(
                fg="#cc0000" if sem_errors else
                   "#996600" if sem_warns else MUTED)

        except Exception as exc:
            import traceback
            self.lbl_status.configure(
                text=f"⚠  Error interno: {exc}", fg="#cc0000")
            traceback.print_exc()

    # ══════════════════════════════════════════════════════════════════════════
    #  RELLENO DE PESTAÑAS
    # ══════════════════════════════════════════════════════════════════════════

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
                     bg=SURFACE, fg="#1a1a2e").pack()
            tk.Label(card, text=label, font=("Courier New", 9),
                     bg=SURFACE, fg=MUTED).pack()

        for w in self.stats_inner.winfo_children():
            w.destroy()

        if not cats:
            return

        max_cnt     = max(cats.values())
        sorted_cats = sorted(cats.items(), key=lambda x: -x[1])

        for tipo, cnt in sorted_cats:
            row = tk.Frame(self.stats_inner, bg=BG_UI, pady=4, padx=16)
            row.pack(fill="x")

            # Punto de color igual al usado en el editor
            color = CAT_COLOR.get(tipo, "#888888")
            dot = tk.Canvas(row, bg=BG_UI, width=12, height=16,
                            highlightthickness=0)
            dot.pack(side="left")
            dot.create_oval(1, 4, 11, 14, fill=color, outline="")

            tk.Label(row, text=f"{tipo:<24}", font=MONO_SM,
                     bg=BG_UI, fg="#1a1a2e", anchor="w", width=24).pack(side="left")

            bar_w = int((cnt / max_cnt) * 200)
            c = tk.Canvas(row, bg=BG_UI, height=16, width=220,
                          highlightthickness=0, relief="flat")
            c.pack(side="left")
            c.create_rectangle(0, 4, max(bar_w, 2), 14, fill=color, outline="")
            c.create_rectangle(bar_w, 4, 220, 14, fill=SURFACE, outline="")

            tk.Label(row, text=f"{cnt:>4}", font=MONO_SM,
                     bg=BG_UI, fg=MUTED, width=4).pack(side="left", padx=6)

    def _fill_arbol(self, raiz: Nodo, errores: List[str]):
        canvas = self.tree_canvas
        canvas.delete("all")

        NODE_W, NODE_H = 120, 28
        H_GAP, V_GAP   = 14, 54

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
                        total  = sum(anchos[id(h)] for h in nodo.hijos)
                        total += H_GAP * (len(nodo.hijos) - 1)
                        anchos[id(nodo)] = max(total, NODE_W)
                else:
                    pila.append((nodo, True))
                    for hijo in reversed(nodo.hijos):
                        pila.append((hijo, False))

            cola = [(root, 0, 20)]
            while cola:
                nodo, prof, x_ini = cola.pop(0)
                x_centro = x_ini + anchos[id(nodo)] // 2
                cy = prof * V_GAP
                posiciones[id(nodo)] = (x_centro - NODE_W // 2, cy)

                x_cursor = x_ini
                hijos = nodo.hijos if nodo.etiqueta.startswith('asig') else reversed(nodo.hijos)
                for hijo in hijos:
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
        canvas.xview_moveto(max(0.0, (raiz_x - 20) / total_w))

        pila = [raiz]
        while pila:
            nodo = pila.pop()
            if id(nodo) not in posiciones:
                continue
            px, py = posiciones[id(nodo)]
            pcx = px + NODE_W // 2
            pcy = py + NODE_H
            hijos = nodo.hijos if nodo.etiqueta.startswith('asig') else reversed(nodo.hijos)
            for hijo in hijos:
                if id(hijo) not in posiciones:
                    continue
                hx, hy = posiciones[id(hijo)]
                canvas.create_line(pcx, pcy, hx + NODE_W // 2, hy,
                                   fill="#888888", width=1)
                pila.append(hijo)

        pila = [raiz]
        while pila:
            nodo = pila.pop()
            if id(nodo) not in posiciones:
                continue
            x, y = posiciones[id(nodo)]
            etq  = nodo.etiqueta[:15] + "…" if len(nodo.etiqueta) > 16 else nodo.etiqueta

            if nodo.etiqueta == "programa":
                bg_col, fg_col, borde = "#1a1a2e", "#ffffff", "#bd93f9"
            elif nodo.etiqueta == "bloque":
                bg_col, fg_col, borde = "#333333", "#ffffff", "#44475a"
            elif any(nodo.etiqueta.startswith(k) for k in
                     ("if", "while", "for", "return", "do-while", "switch")):
                bg_col, fg_col, borde = "#44475a", "#bd93f9", "#6272a4"
            elif any(nodo.etiqueta.startswith(k) for k in
                     ("decl ", "func ", "proto ", "asig", "llamada")):
                bg_col, fg_col, borde = "#f0f0f0", "#1a1a2e", "#d0d0d0"
            elif nodo.etiqueta in ("condición", "else", "init", "cond", "inc",
                                   "case", "default", "break", "continue"):
                bg_col, fg_col, borde = "#dddddd", "#000000", "#888888"
            else:
                bg_col, fg_col, borde = "#ffffff", "#333333", "#cccccc"

            canvas.create_rectangle(x, y, x + NODE_W, y + NODE_H,
                                    fill=bg_col, outline=borde, width=1)
            canvas.create_text(x + NODE_W // 2, y + NODE_H // 2,
                               text=etq, font=("Courier New", 9),
                               fill=fg_col, anchor="center")

            hijos = nodo.hijos if nodo.etiqueta.startswith('asig') else reversed(nodo.hijos)
            for hijo in hijos:
                pila.append(hijo)

        if errores:
            canvas.create_text(
                10, total_h - 10,
                text=f"⚠  {len(errores)} error(es) sintáctico(s)",
                font=("Courier New", 9), fill="#cc0000", anchor="sw"
            )

    def _fill_semantico(self, tabla, advertencias: List[str], errores: List[str]):
        sl = self.sym_list
        sl.configure(state="normal")
        sl.delete("1.0", "end")

        simbolos = tabla.todos()
        if simbolos:
            for sim in simbolos:
                cat_tag   = sim.categoria
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
        self._schedule_highlight()

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

        self.line_nums.configure(state="normal")
        self.line_nums.delete("1.0", "end")
        self.line_nums.configure(state="disabled")

        self._update_line_nums()

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
        s.configure("TScrollbar", background=SURFACE, troughcolor=BG_UI,
                    arrowcolor=MUTED, bordercolor=BG_UI, relief="flat")

    @staticmethod
    def _ejemplo():
        return """\
# Ejemplo de código Python
def saludar(nombre):
    mensaje = "Hola, " + nombre
    print(mensaje)
    return mensaje

x = 42
y = 3.14
resultado = x + y

if resultado > 40:
    print("Grande")
elif resultado == 40:
    print("Exacto")
else:
    print("Pequeño")

for i in range(10):
    if i % 2 == 0:
        print(i)

lista = [1, 2, 3]
largo = len(lista)
"""


# ══════════════════════════════════════════════════════════════════════════════
#  PUNTO DE ENTRADA
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = Compilador()
    app.mainloop()
    