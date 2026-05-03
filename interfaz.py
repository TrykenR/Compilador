"""
interfaz.py — Interfaz gráfica de escritorio del Compilador.

Construye una ventana Tkinter con dos paneles principales:
  - Panel izquierdo: editor de código fuente con numeración de líneas.
  - Panel derecho:   resultados del análisis en cuatro pestañas:
      · Tokens       — tabla de tokens únicos con frecuencia visual.
      · Estadísticas — tarjetas de resumen y gráfico de barras por categoría.
      · Árbol Sint.  — visualización gráfica del AST sobre un canvas scrollable.
      · Errores      — lista de errores léxicos y sintácticos con colores.

Requiere Python 3.8+ con Tkinter (incluido en la instalación estándar).

Ejecución:
    python interfaz.py

Módulos necesarios en la misma carpeta:
    tipos_token.py  |  reglas.py  |  analizador.py  |  sintactico.py

Correcciones aplicadas:
  - Bug crítico: _fill_tokens usaba clave string "tipo|||valor" pero frecuencias
    usa tupla (tipo, valor) → siempre mostraba freq=1.
  - Bug: importación duplicada de tokenizador en run() → usa analizar_completo().
  - Bug: tab_frames["arbol"] se referenciaba antes de ser definido.
  - Bug: layout del árbol era recursivo → RecursionError con código profundo.
  - Bug: _update_line_nums borraba incorrectamente al reducir líneas.
  - Mejora: soporte para nuevos tipos de token (OPERADOR_INCR, OPERADOR_BIT…).
  - Mejora: run() envuelto en try/except para capturar errores internos.
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List

# Asegura que Python encuentre los módulos del compilador aunque la carpeta
# de trabajo del intérprete no sea la misma que la del script.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# analizar()          → tokens únicos + frecuencias, para la interfaz
# analizar_completo() → todos los tokens con repetidos, para el parser
from analizador import analizar, analizar_completo
from sintactico import analizar_sintactico, Nodo


# ══════════════════════════════════════════════════════════════════════════════
#  PALETA DE COLORES Y TIPOGRAFÍA
# ══════════════════════════════════════════════════════════════════════════════
#
# Se definen como constantes de módulo para que cualquier cambio de paleta
# se propague a toda la UI desde un único lugar, sin tocar cada widget.
# La paleta es blanco/negro para máxima legibilidad y aspecto "editor de código".

BG      = "#ffffff"   # fondo principal de la ventana y paneles
FG      = "#000000"   # texto principal
SURFACE = "#f0f0f0"   # fondo de superficies secundarias (cabeceras, barras)
BORDER  = "#000000"   # color de los separadores de 1px entre secciones
MUTED   = "#555555"   # texto secundario (etiquetas, números de línea)
ACCENT  = "#000000"   # color de acento para el botón principal "Analizar"
BTN_FG  = "#ffffff"   # texto del botón principal (contraste sobre ACCENT)
SEL_BG  = "#000000"   # fondo de texto seleccionado en el editor
SEL_FG  = "#ffffff"   # texto seleccionado en el editor

# Tuplas de fuente para Tkinter: (familia, tamaño) o (familia, tamaño, estilo)
MONO    = ("Courier New", 11)           # monoespaciada estándar
MONO_SM = ("Courier New", 10)           # monoespaciada pequeña (listas, barra estado)
MONO_LG = ("Courier New", 12)           # monoespaciada grande (editor de código)
SANS    = ("Helvetica", 10)             # sans-serif para botones y etiquetas
SANS_B  = ("Helvetica", 10, "bold")     # sans-serif negrita para pestaña activa


# ══════════════════════════════════════════════════════════════════════════════
#  ESTILOS VISUALES POR TIPO DE TOKEN
# ══════════════════════════════════════════════════════════════════════════════
#
# Diccionario que mapea cada tipo de token a un dict de opciones de Tkinter
# Text tag (font, foreground). Se registra en el widget token_list una sola
# vez al construir la pestaña; al insertar texto en _fill_tokens() se aplican
# por nombre. Los tipos no presentes en este dict reciben el tag "muted".

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


# ══════════════════════════════════════════════════════════════════════════════
#  VENTANA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

class Compilador(tk.Tk):
    """
    Ventana principal de la aplicación. Hereda de tk.Tk para ser ella misma
    la ventana raíz del bucle de eventos de Tkinter, evitando crear una
    instancia separada de Tk.

    La construcción de la UI se divide en métodos privados (_build_*) para
    mantener __init__ limpio y que cada sección sea fácil de localizar y
    modificar de forma independiente.
    """

    def __init__(self):
        super().__init__()
        self.title("Compilador — Léxico & Sintáctico")
        self.configure(bg=BG)
        self.geometry("1200x700")   # tamaño inicial en píxeles
        self.minsize(900, 560)      # tamaño mínimo para que la UI no se rompa

        # Contador de líneas del editor; se inicializa en 0 para que la primera
        # llamada a _update_line_nums() lo detecte como cambio y dibuje todos.
        self._last_line_count = 0

        self._build_ui()      # construir todos los widgets
        self._apply_style()   # aplicar tema TTK a las scrollbars

    # ══════════════════════════════════════════════════════════════════════════
    #  CONSTRUCCIÓN DE LA UI
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        """
        Orquesta la construcción de toda la interfaz en este orden:
          1. Barra superior (título + botones)
          2. Separador horizontal de 1px
          3. Cuerpo principal (editor | separador vertical | resultados)
          4. Barra de estado inferior

        El orden de las llamadas a pack() importa: Tkinter apila los widgets
        en el orden en que se registran. La barra de estado debe empaquetarse
        con side="bottom" ANTES de que el cuerpo principal use expand=True,
        para que ocupe su espacio fijo al fondo sin ser desplazada.
        """
        # ── Barra superior ────────────────────────────────────────────────────
        top = tk.Frame(self, bg=BG, pady=8, padx=16)
        top.pack(fill="x", side="top")

        tk.Label(top, text="COMPILADOR", font=("Helvetica", 14, "bold"),
                 bg=BG, fg=FG).pack(side="left")
        tk.Label(top, text="  Léxico · Sintáctico", font=("Helvetica", 10),
                 bg=BG, fg=MUTED).pack(side="left")

        # El botón "Analizar" se guarda en self.btn_run para poder
        # deshabilitarlo en el futuro si fuera necesario (ej: durante análisis).
        # command=self.run lo conecta directamente al método de análisis.
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

        # Frame de 1px de alto que actúa como línea divisoria visual
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        # ── Cuerpo principal ──────────────────────────────────────────────────
        # expand=True hace que este frame crezca para llenar el espacio disponible
        # entre la barra superior y la barra de estado.
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        self._build_editor(body)
        # Separador vertical de 1px entre el editor y el panel de resultados
        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y")
        self._build_results(body)

        # ── Barra de estado ───────────────────────────────────────────────────
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")
        status_bar = tk.Frame(self, bg=SURFACE, pady=4, padx=12)
        status_bar.pack(fill="x", side="bottom")

        # lbl_status (izquierda): "Listo", "✓ Análisis completado" o descripción de error
        self.lbl_status = tk.Label(status_bar, text="Listo", font=MONO_SM,
                                   bg=SURFACE, fg=MUTED, anchor="w")
        self.lbl_status.pack(side="left")

        # lbl_stats (derecha): conteo de tokens únicos y total de apariciones
        self.lbl_stats = tk.Label(status_bar, text="", font=MONO_SM,
                                  bg=SURFACE, fg=MUTED, anchor="e")
        self.lbl_stats.pack(side="right")

    def _build_editor(self, parent):
        """
        Construye el panel izquierdo: editor de código con numeración de líneas.

        Estructura interna:
          frame
          ├── hdr          (cabecera: etiqueta "CÓDIGO FUENTE" + posición cursor)
          └── edit_frame   (contenedor horizontal)
              ├── line_nums   (widget Text de solo lectura con los números)
              ├── separador   (Frame de 1px)
              └── editor      (widget Text editable)
          └── hscroll      (scrollbar horizontal bajo el editor)

        Se usa un widget Text para los números de línea (en lugar de un Label)
        porque permite scroll sincronizado con el editor y actualización
        incremental línea a línea sin reescribir todo el contenido.
        """
        frame = tk.Frame(parent, bg=BG)
        frame.pack(side="left", fill="both", expand=True)

        # Cabecera del panel
        hdr = tk.Frame(frame, bg=SURFACE, pady=5, padx=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="CÓDIGO FUENTE", font=MONO_SM,
                 bg=SURFACE, fg=MUTED).pack(side="left")
        # Indicador de posición del cursor, ej: "L5  C12"
        self.lbl_cursor = tk.Label(hdr, text="L1  C1", font=MONO_SM,
                                   bg=SURFACE, fg=MUTED)
        self.lbl_cursor.pack(side="right")

        edit_frame = tk.Frame(frame, bg=BG)
        edit_frame.pack(fill="both", expand=True)

        # Columna de números de línea.
        # width=4 da espacio visual para hasta 9999 líneas.
        # state="disabled" evita que el usuario escriba en ella.
        # takefocus=False impide que reciba el foco al pulsar Tab.
        # cursor="arrow" cambia el cursor del ratón para dejar claro que no es editable.
        self.line_nums = tk.Text(
            edit_frame, width=4, bg=SURFACE, fg=MUTED,
            font=MONO, state="disabled", relief="flat",
            padx=4, takefocus=False, cursor="arrow"
        )
        self.line_nums.pack(side="left", fill="y")
        # Separador visual de 1px entre los números y el editor
        tk.Frame(edit_frame, bg=BORDER, width=1).pack(side="left", fill="y")

        # Editor principal.
        # wrap="none" + scrollbar horizontal permite ver líneas largas sin truncarlas.
        # undo=True activa deshacer/rehacer con Ctrl+Z / Ctrl+Y.
        # insertbackground define el color del cursor de inserción de texto.
        self.editor = tk.Text(
            edit_frame, wrap="none", bg=BG, fg=FG,
            font=MONO_LG, relief="flat", padx=12, pady=8,
            insertbackground=FG, selectbackground=SEL_BG,
            selectforeground=SEL_FG, undo=True
        )
        self.editor.pack(side="left", fill="both", expand=True)

        # Scrollbar horizontal vinculada bidireccionalamente con el editor:
        # xscrollcommand notifica a la barra cuando el editor se desplaza;
        # command mueve el editor cuando el usuario arrastra la barra.
        hscroll = tk.Scrollbar(frame, orient="horizontal",
                               command=self.editor.xview)
        hscroll.pack(fill="x")
        self.editor.configure(xscrollcommand=hscroll.set)

        # Insertar el código de ejemplo al abrir la aplicación
        self.editor.insert("1.0", self._ejemplo())

        # ── Bindings del editor ──────────────────────────────────────────────
        # KeyRelease y ButtonRelease: actualizar líneas y cursor tras cualquier
        # pulsación de tecla o clic. Se usan los eventos "release" (no "press")
        # para que el widget ya haya procesado el carácter antes de que leamos
        # el contenido actualizado.
        self.editor.bind("<KeyRelease>",     self._on_key)
        self.editor.bind("<ButtonRelease>",  self._on_key)
        # Ctrl+Enter lanza el análisis sin necesidad de hacer clic en el botón.
        # El lambda descarta el objeto Event que Tkinter pasa automáticamente.
        self.editor.bind("<Control-Return>", lambda e: self.run())
        # Tab inserta 4 espacios en lugar del comportamiento por defecto (cambio de foco).
        self.editor.bind("<Tab>",            self._tab)
        # MouseWheel (Windows/macOS) y Button-4/5 (Linux) sincronizan el scroll
        # del widget de números de línea con el del editor.
        self.editor.bind("<MouseWheel>",     self._sync_scroll)
        self.editor.bind("<Button-4>",       self._sync_scroll)  # rueda arriba en Linux
        self.editor.bind("<Button-5>",       self._sync_scroll)  # rueda abajo en Linux

        # Dibujar los números de línea del código de ejemplo ya insertado
        self._update_line_nums()

    def _build_results(self, parent):
        """
        Construye el panel derecho: barra de pestañas + contenedor de pestañas.

        Las pestañas se implementan manualmente (sin ttk.Notebook) para tener
        control total sobre el estilo visual. Cada pestaña es un Frame que
        se muestra u oculta mediante pack() / pack_forget().

        CORRECCIÓN importante: self.tab_frames se inicializa aquí como dict
        vacío ANTES de llamar a _build_tab_*, porque esos métodos escriben
        en él. El bug original intentaba leer el dict antes de crearlo.

        El lambda en command=lambda n=nombre: ... captura 'nombre' POR VALOR
        en cada iteración del bucle. Sin el 'n=nombre', todos los botones
        capturarían la misma referencia a 'nombre' (la del último ciclo del for).
        """
        frame = tk.Frame(parent, bg=BG)
        frame.pack(side="left", fill="both", expand=True)

        tab_bar = tk.Frame(frame, bg=SURFACE)
        tab_bar.pack(fill="x")

        self.tab_btns    = {}   # nombre → widget Button de la pestaña
        self.tab_frames  = {}   # nombre → Frame con el contenido (inicializado ANTES de _build_tab_*)
        self.current_tab = tk.StringVar(value="tokens")

        for nombre, label in [("tokens", "Tokens"), ("stats", "Estadísticas"),
                               ("arbol",  "Árbol Sint."), ("errores", "Errores")]:
            btn = tk.Button(
                tab_bar, text=label, font=SANS,
                bg=SURFACE, fg=MUTED, relief="flat",
                padx=14, pady=6, cursor="hand2",
                command=lambda n=nombre: self._show_tab(n)  # n=nombre: captura por valor
            )
            btn.pack(side="left")
            self.tab_btns[nombre] = btn

        # Línea inferior de la barra de pestañas como separador visual
        tk.Frame(tab_bar, bg=BORDER, height=1).pack(side="bottom", fill="x")

        # Contenedor donde los frames de cada pestaña se muestran y ocultan
        self.tab_frame = tk.Frame(frame, bg=BG)
        self.tab_frame.pack(fill="both", expand=True)

        # Construir el contenido de cada pestaña (cada uno escribe en self.tab_frames)
        self._build_tab_tokens()
        self._build_tab_stats()
        self._build_tab_arbol()
        self._build_tab_errores()

        self._show_tab("tokens")   # mostrar la primera pestaña al arrancar

    # ── Construcción de pestañas ──────────────────────────────────────────────

    def _build_tab_tokens(self):
        """
        Pestaña "Tokens": tabla de tres columnas (tipo, valor, apariciones).

        Se usa un widget Text en lugar de Treeview o Listbox porque permite
        aplicar tags de color y fuente a fragmentos individuales dentro de
        una misma fila, coloreando cada token según su categoría sin necesidad
        de widgets adicionales.

        Los tags se registran aquí con tag_configure() una sola vez;
        _fill_tokens() los referencia por nombre al insertar el texto.
        Los widgets Text necesitan state="disabled" para que el usuario
        no pueda editarlos; _fill_tokens() los habilita brevemente para escribir.
        """
        f = tk.Frame(self.tab_frame, bg=BG)
        self.tab_frames["tokens"] = f   # registrar en el dict compartido

        # Cabecera fija de columnas (no se desplaza con el scroll de la lista)
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

        # cursor="arrow" indica visualmente que este Text no es editable.
        # La conexión bidireccional scrollbar ↔ widget:
        #   yscrollcommand → el widget notifica a la barra su posición actual
        #   vsb.config(command=...) → la barra mueve el widget al arrastrarse
        self.token_list = tk.Text(
            list_frame, wrap="none", bg=BG, fg=FG,
            font=MONO_SM, relief="flat", padx=8, pady=4,
            state="disabled", yscrollcommand=vsb.set,
            cursor="arrow"
        )
        self.token_list.pack(fill="both", expand=True)
        vsb.config(command=self.token_list.yview)

        # Registrar un tag por cada tipo de token; el operador ** desempaqueta
        # el dict de opciones (font, foreground) como argumentos de keyword.
        for tipo, cfg in TOKEN_TAGS.items():
            self.token_list.tag_configure(tipo, **cfg)
        # Tags auxiliares para texto atenuado y filas sin categoría conocida
        self.token_list.tag_configure("muted",  foreground=MUTED)
        self.token_list.tag_configure("sep",     foreground="#cccccc")
        self.token_list.tag_configure("stripe",  background="#f8f8f8")

    def _build_tab_stats(self):
        """
        Pestaña "Estadísticas": tarjetas de resumen + gráfico de barras por categoría.

        Las barras se implementan con Canvas rectangles en lugar de una librería
        externa para no añadir dependencias. La proporción de cada barra es
        relativa a la categoría más frecuente (100% del ancho disponible = 200px).

        El patrón Frame-dentro-de-Canvas (stats_inner) permite que la zona
        de barras sea scrollable aunque contenga widgets Tkinter reales:
          Canvas → create_window(stats_inner) → stats_inner contiene las filas.
        El binding <Configure> en stats_inner recalcula scrollregion cada vez
        que se añaden o eliminan filas al rellenar con nuevos datos.
        """
        f = tk.Frame(self.tab_frame, bg=BG)
        self.tab_frames["stats"] = f

        # cards_frame: contenedor horizontal de las cuatro tarjetas numéricas de resumen
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
                                      highlightthickness=0,   # sin borde del canvas
                                      yscrollcommand=vsb.set)
        self.stats_canvas.pack(fill="both", expand=True)
        vsb.config(command=self.stats_canvas.yview)

        # Frame embebido en el canvas mediante create_window:
        # esto permite colocar widgets Tkinter reales dentro de una zona scrollable,
        # algo que no es posible colocando widgets directamente sobre el canvas.
        self.stats_inner = tk.Frame(self.stats_canvas, bg=BG)
        self.stats_canvas.create_window((0, 0), window=self.stats_inner, anchor="nw")
        # Recalcular el área scrollable cada vez que stats_inner cambia de tamaño
        self.stats_inner.bind("<Configure>",
            lambda e: self.stats_canvas.configure(
                scrollregion=self.stats_canvas.bbox("all")))

    def _build_tab_arbol(self):
        """
        Pestaña "Árbol Sint.": visualización gráfica del AST en un canvas scrollable.

        Se usa un Canvas en lugar de widgets porque el árbol puede ser
        arbitrariamente grande y necesita scrollbars en ambas dimensiones.
        Los nodos se dibujan con create_rectangle + create_text y las aristas
        con create_line; todo se borra y redibuja en cada análisis.

        El scroll con rueda del ratón se implementa manualmente porque Tkinter
        no lo conecta automáticamente a los Canvas:
          e.delta / 120 da unidades de desplazamiento en Windows/macOS.
          En Linux se usan Button-4 / Button-5 que el editor también maneja.
        """
        f = tk.Frame(self.tab_frame, bg=BG)
        self.tab_frames["arbol"] = f   # debe asignarse AQUÍ, dentro del método

        wrap = tk.Frame(f, bg=BG)
        wrap.pack(fill="both", expand=True)

        # Scrollbars en ambas dimensiones para árboles anchos y profundos
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

        # Scroll vertical con rueda del ratón: int(-1*(e.delta/120)) convierte
        # el delta de Windows/macOS en unidades de desplazamiento con dirección correcta.
        self.tree_canvas.bind("<MouseWheel>", lambda e:
            self.tree_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    def _build_tab_errores(self):
        """
        Pestaña "Errores": lista de errores léxicos y sintácticos con colores.

        Usa un widget Text con tres tags diferenciados visualmente:
          "err"  → rojo para cada mensaje de error individual.
          "ok"   → gris para el mensaje de "sin errores" y los separadores.
          "head" → negrita para los encabezados de sección.

        wrap="word" evita que los mensajes de error largos corten palabras
        al final de la línea visible.
        """
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
        """
        Muestra el frame de la pestaña indicada y oculta los demás.

        pack_forget() desvincula un frame del gestor de geometría SIN
        destruirlo ni borrar su contenido; pack() lo vuelve a mostrar.
        Esto hace el cambio de pestaña instantáneo: los datos ya renderizados
        no necesitan recalcularse.

        Al mismo tiempo se actualiza el estilo visual del botón activo
        (fondo blanco, negrita, relieve "groove") frente a los inactivos
        (fondo gris, texto atenuado, sin relieve).
        """
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
        """
        Lanza el análisis léxico y sintáctico sobre el código del editor
        y distribuye los resultados a cada pestaña.

        Flujo de ejecución:
          1. analizar()            → tokens únicos + frecuencias (para la tabla y stats)
          2. analizar_completo()   → todos los tokens con repetidos (para el parser)
          3. analizar_sintactico() → AST + errores sintácticos
          4. _fill_*               → poblar cada pestaña con sus resultados
          5. Actualizar barra de estado con totales y color de errores

        El parámetro '_' absorbe el objeto Event que Tkinter pasa automáticamente
        cuando run() es invocado desde el binding Ctrl+Enter.

        El try/except exterior captura cualquier excepción inesperada (errores
        internos del compilador) y la muestra en la barra de estado en lugar
        de dejar caer la aplicación silenciosamente.
        """
        # "end-1c" excluye el salto de línea final que Tkinter siempre añade al Text
        codigo = self.editor.get("1.0", "end-1c")
        if not codigo.strip():
            return   # no analizar si el editor está vacío o solo tiene espacios

        try:
            # Paso 1 — léxico para la interfaz: deduplicado + frecuencias
            tokens_unicos, frecuencias, lex_errors = analizar(codigo)

            # Paso 2 — léxico completo para el parser: todos los tokens con repetidos
            tokens_full, _ = analizar_completo(codigo)

            # Paso 3 — sintáctico: construye el AST y acumula errores sintácticos
            arbol, sin_errors = analizar_sintactico(tokens_full)

            all_errors = lex_errors + sin_errors

            # Paso 4 — distribuir resultados a cada pestaña
            self._fill_tokens(tokens_unicos, frecuencias)
            self._fill_stats(tokens_unicos, frecuencias, all_errors)
            self._fill_arbol(arbol, sin_errors)
            self._fill_errores(lex_errors, sin_errors)

            # Paso 5 — actualizar barra de estado
            total_ap = sum(frecuencias.values())
            if all_errors:
                self.lbl_status.configure(
                    text=f"⚠  {len(all_errors)} error(es) encontrado(s)", fg="#cc0000")
            else:
                self.lbl_status.configure(
                    text="✓  Análisis completado sin errores", fg=MUTED)
            self.lbl_stats.configure(
                text=f"{len(tokens_unicos)} tokens únicos  ·  {total_ap} apariciones")

            # Colorear el botón de "Errores" en rojo si hay errores, gris si no
            self.tab_btns["errores"].configure(
                fg="#cc0000" if all_errors else MUTED)

        except Exception as exc:
            import traceback
            self.lbl_status.configure(
                text=f"⚠  Error interno: {exc}", fg="#cc0000")
            traceback.print_exc()   # volcar la traza completa en consola para depuración

    # ══════════════════════════════════════════════════════════════════════════
    #  MÉTODOS DE RELLENO DE PESTAÑAS
    # ══════════════════════════════════════════════════════════════════════════

    def _fill_tokens(self, tokens, frecuencias):
        """
        Rellena la tabla de la pestaña "Tokens" con una fila por token único.

        Cada fila contiene tres segmentos insertados con su tag de color:
          · Tipo   (22 chars, alineado a la izquierda)
          · Valor  (22 chars, alineado a la izquierda)
          · Número de apariciones + barra proporcional de 16 bloques (█/░)

        La barra es proporcional al token MÁS frecuente del análisis actual
        (max_freq = 100% = 16 bloques). round() evita que tokens con frecuencia
        muy baja pero distinta de cero queden en 0 bloques por truncamiento.

        CORRECCIÓN del bug original: la clave debe ser la tupla (tipo, valor),
        igual que en analizador.py. Usar el string "tipo|||valor" causaba que
        frecuencias.get() nunca encontrara la clave y devolviera siempre 1.

        El widget se habilita (state="normal") para escribir, se limpia,
        se rellena y se vuelve a deshabilitar (state="disabled") para que
        el usuario no pueda editar la tabla manualmente.
        """
        tl = self.token_list
        tl.configure(state="normal")
        tl.delete("1.0", "end")

        # default=1 evita ZeroDivisionError si frecuencias está vacío
        max_freq = max(frecuencias.values(), default=1)

        for tok in tokens:
            clave = (tok.tipo, tok.valor)     # TUPLA, no string
            freq  = frecuencias.get(clave, 1)
            tag   = tok.tipo if tok.tipo in TOKEN_TAGS else "muted"

            tl.insert("end", f"{tok.tipo:<22}", tag)
            tl.insert("end", f"  {tok.valor:<22}", tag)

            # Barra proporcional de 16 bloques: █ = lleno, ░ = vacío
            bar_filled = round((freq / max_freq) * 16)
            bar = "█" * bar_filled + "░" * (16 - bar_filled)
            tl.insert("end", f"  {freq:>3}  ", "muted")
            tl.insert("end", bar, tag)
            tl.insert("end", "\n")

        if not tokens:
            tl.insert("end", "  Sin tokens encontrados\n", "muted")

        tl.configure(state="disabled")

    def _fill_stats(self, tokens, frecuencias, errores):
        """
        Rellena la pestaña "Estadísticas" con tarjetas de resumen y barras.

        Tarjetas de resumen: se destruyen y recrean en cada análisis llamando
        a winfo_children() + destroy() en cards_frame. Cada tarjeta es un Frame
        con dos Labels apilados: el número grande arriba y la etiqueta abajo.

        Barras horizontales: se dibujan con dos create_rectangle() por fila
        sobre un Canvas de 220px de ancho. El par simula la barra bicolor:
          Rectángulo 1: (0, 4, bar_w, 14)    → parte llena en negro
          Rectángulo 2: (bar_w, 4, 220, 14)  → parte vacía en gris claro
        max(bar_w, 2) garantiza que la barra siempre tenga al menos 2px de ancho
        y sea visible aunque el conteo sea muy pequeño frente a max_cnt.

        Las categorías se muestran ordenadas de mayor a menor frecuencia
        para que la distribución sea legible de un vistazo.
        """
        # Destruir tarjetas anteriores antes de crear las nuevas
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

        # Destruir filas de barras anteriores
        for w in self.stats_inner.winfo_children():
            w.destroy()

        if not cats:
            return

        max_cnt     = max(cats.values())
        # Orden descendente: la categoría más frecuente aparece arriba
        sorted_cats = sorted(cats.items(), key=lambda x: -x[1])

        for tipo, cnt in sorted_cats:
            row = tk.Frame(self.stats_inner, bg=BG, pady=4, padx=16)
            row.pack(fill="x")
            tk.Label(row, text=f"{tipo:<26}", font=MONO_SM,
                     bg=BG, fg=FG, anchor="w", width=26).pack(side="left")

            # Barra proporcional: 200px = 100% (categoría con max_cnt tokens)
            bar_w = int((cnt / max_cnt) * 200)
            c = tk.Canvas(row, bg=BG, height=16, width=220,
                          highlightthickness=0, relief="flat")
            c.pack(side="left")
            c.create_rectangle(0, 4, max(bar_w, 2), 14, fill=FG, outline="")
            c.create_rectangle(bar_w, 4, 220, 14, fill=SURFACE, outline="")

            tk.Label(row, text=f"{cnt:>4}", font=MONO_SM,
                     bg=BG, fg=MUTED, width=4).pack(side="left", padx=6)

    def _fill_arbol(self, raiz: Nodo, errores: List[str]):
        """
        Dibuja el AST sobre el canvas de la pestaña "Árbol Sint.".

        Algoritmo de layout en dos fases iterativas para evitar RecursionError
        con árboles profundos (bug del layout recursivo original):

          Fase 1 — post-order iterativo (pila con flag 'procesado'):
            Calcula el ancho mínimo necesario para cada subárbol, de abajo
            a arriba. Un nodo hoja ocupa exactamente NODE_W; un nodo interno
            ocupa la suma de los anchos de sus hijos más los gaps entre ellos.
            La tupla (nodo, procesado) en la pila simula el post-order: la
            primera vez se marca procesado=False y se empujan los hijos;
            la segunda vez (procesado=True) los anchos de los hijos ya están
            listos en el diccionario 'anchos'.

          Fase 2 — BFS top-down (cola):
            Distribuye las coordenadas (x, y) de cada nodo usando los anchos
            calculados. El nodo raíz recibe un margen izquierdo de 20px;
            cada nodo padre reparte su espacio horizontal entre sus hijos
            de izquierda a derecha según sus anchos individuales.

        Renderizado en dos pasadas separadas:
          1. Aristas (líneas grises entre centros de nodos): se dibujan PRIMERO
             para que queden visualmente detrás de los rectángulos.
          2. Nodos (rectángulos + texto): se dibujan encima de las aristas.

        El color de cada rectángulo sigue la jerarquía semántica del nodo:
          Negro       → raíz "programa"
          Gris oscuro → "bloque"
          Gris medio  → sentencias de control (if, while, for, return…)
          Gris claro  → declaraciones y asignaciones (decl, func, asig…)
          Blanco      → expresiones, operadores y nodos hoja
        """
        canvas = self.tree_canvas
        canvas.delete("all")   # limpiar el canvas antes de redibujar

        # Dimensiones de cada nodo y separaciones entre ellos
        NODE_W, NODE_H = 120, 28   # ancho y alto de cada rectángulo
        H_GAP, V_GAP   = 14,  54   # separación horizontal entre hermanos y vertical entre niveles

        posiciones = {}   # {id(nodo): (x, y)} — esquina superior izquierda

        def layout_iterativo(root: Nodo):
            """
            Calcula posiciones en dos fases usando id(nodo) como clave,
            lo que identifica cada objeto por identidad de memoria y permite
            que varios nodos con la misma etiqueta coexistan sin colisión.
            """
            # ── Fase 1: anchos en post-order ────────────────────────────────
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
                    # reversed: los hijos se procesan de izquierda a derecha
                    for hijo in reversed(nodo.hijos):
                        pila.append((hijo, False))

            # ── Fase 2: coordenadas en BFS top-down ─────────────────────────
            cola = [(root, 0, 20)]   # (nodo, profundidad, x_inicial)
            while cola:
                nodo, prof, x_ini = cola.pop(0)
                # Centrar el nodo en el espacio que le corresponde
                x_centro = x_ini + anchos[id(nodo)] // 2
                cy = prof * V_GAP
                posiciones[id(nodo)] = (x_centro - NODE_W // 2, cy)

                # Repartir el espacio entre los hijos de izquierda a derecha
                x_cursor = x_ini
                for hijo in nodo.hijos:
                    cola.append((hijo, prof + 1, x_cursor))
                    x_cursor += anchos[id(hijo)] + H_GAP

        layout_iterativo(raiz)

        if not posiciones:
            canvas.create_text(20, 20, text="(árbol vacío)", anchor="nw",
                               font=MONO_SM, fill=MUTED)
            return

        # Calcular el área total para configurar scrollregion del canvas.
        # scrollregion define el área virtual que el canvas puede mostrar con scroll.
        all_x   = [p[0] for p in posiciones.values()]
        all_y   = [p[1] for p in posiciones.values()]
        total_w = max(all_x) + NODE_W + 40   # +40px de margen derecho
        total_h = max(all_y) + NODE_H + 40   # +40px de margen inferior
        canvas.configure(scrollregion=(0, 0, total_w, total_h))

        # Desplazar la vista para que la raíz quede visible desde el inicio.
        # Sin esto, el canvas parte desde x=0, que corresponde a nodos hoja del
        # subárbol más profundo, haciendo que el árbol parezca invertido.
        # xview_moveto(fracción) recibe un valor [0.0, 1.0] del ancho virtual total.
        raiz_x = posiciones[id(raiz)][0]
        fraccion_inicio = max(0.0, (raiz_x - 20) / total_w)
        canvas.xview_moveto(fraccion_inicio)

        # ── Pasada 1: dibujar aristas (quedan detrás de los rectángulos) ────
        # Se conecta el borde inferior del padre con el borde superior del hijo.
        pila = [raiz]
        while pila:
            nodo = pila.pop()
            if id(nodo) not in posiciones:
                continue
            px, py = posiciones[id(nodo)]
            pcx = px + NODE_W // 2   # centro X del padre
            pcy = py + NODE_H        # borde inferior del padre
            for hijo in nodo.hijos:
                if id(hijo) not in posiciones:
                    continue
                hx, hy = posiciones[id(hijo)]
                hcx = hx + NODE_W // 2   # centro X del hijo
                canvas.create_line(pcx, pcy, hcx, hy, fill="#888888", width=1)
                pila.append(hijo)

        # ── Pasada 2: dibujar nodos encima de las aristas ────────────────────
        pila = [raiz]
        while pila:
            nodo = pila.pop()
            if id(nodo) not in posiciones:
                continue
            x, y = posiciones[id(nodo)]
            etq  = nodo.etiqueta
            # Truncar etiquetas largas para que quepan dentro del rectángulo
            if len(etq) > 16:
                etq = etq[:15] + "…"

            # Color según la categoría semántica del nodo
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

        # Nota al pie del canvas si hay errores sintácticos y el árbol es parcial
        if errores:
            canvas.create_text(
                10, total_h - 10,
                text=f"⚠  {len(errores)} error(es) sintáctico(s) — árbol puede ser parcial",
                font=("Courier New", 9), fill="#cc0000", anchor="sw"
            )

    def _fill_errores(self, lex_errors, sin_errors):
        """
        Rellena la pestaña "Errores" con los mensajes agrupados por fase.

        Si no hay errores muestra un único mensaje de confirmación en gris.
        Si los hay, los separa en dos secciones con encabezado en negrita
        (ERRORES LÉXICOS / ERRORES SINTÁCTICOS) y cada mensaje en rojo.

        El widget se habilita para escritura, se limpia, se rellena
        y se vuelve a deshabilitar en cada llamada.
        """
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

    # ══════════════════════════════════════════════════════════════════════════
    #  UTILIDADES DEL EDITOR
    # ══════════════════════════════════════════════════════════════════════════

    def _on_key(self, _=None):
        """
        Manejador compartido para los eventos KeyRelease y ButtonRelease del editor.
        Se llama tras cualquier pulsación de tecla o clic del ratón para mantener
        sincronizados los números de línea y el indicador de posición del cursor.
        El parámetro '_' absorbe el objeto Event que Tkinter pasa automáticamente.
        """
        self._update_line_nums()
        self._update_cursor()

    def _tab(self, e):
        """
        Intercepta la tecla Tab para insertar 4 espacios en la posición
        del cursor en lugar del comportamiento por defecto de Tkinter,
        que mueve el foco al siguiente widget.
        "break" como valor de retorno detiene la propagación del evento,
        impidiendo que Tkinter lo procese de la manera habitual.
        """
        self.editor.insert("insert", "    ")
        return "break"

    def _update_line_nums(self):
        """
        Actualiza el widget de números de línea de forma incremental.

        En lugar de borrar y reescribir todo el contenido en cada tecla
        (lo que congelaría la UI con archivos de muchas líneas), solo añade
        los números nuevos al final o elimina los sobrantes desde el final.

        Tkinter indexa el contenido de un Text como "línea.columna" (base 1).
        "end-1c" devuelve la posición del último carácter excluyendo el \\n
        final que Tkinter añade internamente; su parte de línea (.split(".")[0])
        da el número total de líneas reales del editor.

        Al aumentar líneas: se insertan solo los números faltantes al final.
        Al reducir líneas: se borra desde "{new_count+1}.0" hasta "end",
        eliminando exactamente las líneas sobrantes sin tocar las anteriores.
        """
        new_count = int(self.editor.index("end-1c").split(".")[0])
        old_count = self._last_line_count

        if new_count != old_count:
            self.line_nums.configure(state="normal")

            if new_count > old_count:
                # Concatenar solo los números nuevos al final del widget
                nuevas    = "\n".join(str(i) for i in range(old_count + 1, new_count + 1))
                separador = "\n" if old_count > 0 else ""   # evitar \n inicial si estaba vacío
                self.line_nums.insert("end", separador + nuevas)
            else:
                # Borrar desde la primera línea sobrante hasta el final
                self.line_nums.delete(f"{new_count + 1}.0", "end")

            self.line_nums.configure(state="disabled")
            self._last_line_count = new_count

        # Sincronizar el scroll de los números con la posición actual del editor.
        # yview() devuelve (top, bottom) como fracciones [0.0, 1.0];
        # yview_moveto(top) desplaza el widget al mismo punto de vista.
        self.line_nums.yview_moveto(self.editor.yview()[0])

    def _update_cursor(self):
        """
        Actualiza el indicador "L5  C12" en la cabecera del editor.
        editor.index("insert") devuelve la posición del cursor como "línea.columna"
        donde la columna es base 0; se suma 1 al mostrarlo para que sea base 1.
        """
        pos  = self.editor.index("insert")
        l, c = pos.split(".")
        self.lbl_cursor.configure(text=f"L{l}  C{int(c)+1}")

    def _sync_scroll(self, _=None):
        """
        Sincroniza el scroll vertical del widget de números de línea con el
        del editor cuando el usuario usa la rueda del ratón o las scrollbars.
        Se invoca desde los bindings de MouseWheel, Button-4 y Button-5.
        """
        self.line_nums.yview_moveto(self.editor.yview()[0])

    def limpiar(self):
        """
        Resetea la aplicación a su estado inicial vacío.

        Borra el contenido del editor y de todas las pestañas de resultados,
        y restablece los textos de la barra de estado.

        Los widgets Text necesitan habilitarse (state="normal") antes de
        poder borrarse y deshabilitarse de nuevo (state="disabled") después.
        Los contenedores dinámicos (cards_frame, stats_inner) se limpian
        destruyendo todos sus hijos con winfo_children() + destroy().
        """
        self.editor.delete("1.0", "end")
        self._last_line_count = 0     # resetear el contador para que _update_line_nums funcione
        self._update_line_nums()

        self.token_list.configure(state="normal")
        self.token_list.delete("1.0", "end")
        self.token_list.configure(state="disabled")

        # Destruir todos los widgets hijos de los contenedores de datos dinámicos
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
        # Restaurar el color de todos los botones de pestaña a gris
        for btn in self.tab_btns.values():
            btn.configure(fg=MUTED)

    # ── Estilo TTK ────────────────────────────────────────────────────────────

    def _apply_style(self):
        """
        Aplica el tema visual a los widgets TTK (scrollbars).

        Los widgets ttk.Scrollbar tienen su propio sistema de temas
        independiente de los colores de tk.Widget, por lo que necesitan
        configurarse por separado mediante ttk.Style.
        theme_use("default") selecciona el tema base de Tkinter sobre el que
        se aplican los overrides de configure(), evitando el aspecto del
        tema nativo del sistema operativo que ignoraría estos colores.
        """
        s = ttk.Style(self)
        s.theme_use("default")
        s.configure("TScrollbar", background=SURFACE, troughcolor=BG,
                    arrowcolor=MUTED, bordercolor=BG, relief="flat")

    # ── Código de ejemplo ─────────────────────────────────────────────────────

    @staticmethod
    def _ejemplo():
        """
        Devuelve el código fuente de ejemplo que se carga al abrir la aplicación.

        Es un método estático porque no necesita acceder a ningún atributo de
        la instancia (self); no tiene estado propio.
        La barra invertida al inicio del string multilínea evita que el texto
        empiece con un salto de línea vacío, ya que la apertura del triple
        comilla va seguida inmediatamente del primer carácter de contenido.
        """
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
#  PUNTO DE ENTRADA
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # La guarda __name__ == "__main__" evita que la ventana se abra si este
    # módulo es importado desde otro archivo (ej: en tests unitarios) en lugar
    # de ejecutarse directamente desde la terminal.
    app = Compilador()
    app.mainloop()   # inicia el bucle de eventos de Tkinter; bloquea hasta cerrar la ventana
    