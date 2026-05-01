"""
theme.py — Joydip's PDF Suite
Shared colour palette, font helpers, ttk style application,
and reusable widget classes used by every app in the suite.
"""

import tkinter as tk
from tkinter import ttk, filedialog
import os

# ─── Colour tokens ────────────────────────────────────────────────────────────
BG    = "#0F1117"   # deepest background
SURF  = "#181C25"   # card / panel surface
SURF2 = "#1F2432"   # input fields, list boxes
BDR   = "#2C3044"   # borders and dividers
ACC   = "#4F8EF7"   # primary accent (blue)
ADIM  = "#1C3566"   # pressed accent
TXT   = "#E8EAF0"   # primary text
MUT   = "#7A8099"   # muted / label text
DIM   = "#3A3F52"   # very dim / disabled
OK    = "#4EBF85"   # success green
WARN  = "#E8A838"   # warning amber
ERR   = "#D95F6E"   # error red

# ─── Font helpers ─────────────────────────────────────────────────────────────
def F(size=11, bold=False):
    """Return a tkinter font tuple. Uses Inter if available, falls back gracefully."""
    weight = "bold" if bold else "normal"
    return ("Inter", size, weight)

def FM(size=10):
    """Monospace font for log output and code areas."""
    return ("JetBrains Mono", size, "normal")


# ─── Global ttk style application ─────────────────────────────────────────────
def apply(root):
    """Apply the suite-wide dark theme to a tkinter root window."""
    s = ttk.Style(root)
    s.theme_use("clam")
    root.configure(bg=BG)

    # ── Frames ──
    s.configure("TFrame",       background=BG)
    s.configure("Card.TFrame",  background=SURF)
    s.configure("Card2.TFrame", background=SURF2)

    # ── Labels ──
    s.configure("TLabel",         background=BG,   foreground=TXT, font=F(11))
    s.configure("Muted.TLabel",   background=BG,   foreground=MUT, font=F(10))
    s.configure("Title.TLabel",   background=BG,   foreground=TXT, font=F(15, True))
    s.configure("Card.TLabel",    background=SURF,  foreground=TXT, font=F(11))
    s.configure("CardMut.TLabel", background=SURF,  foreground=MUT, font=F(10))
    s.configure("Surf2.TLabel",   background=SURF2, foreground=TXT, font=F(11))
    s.configure("OK.TLabel",      background=BG,    foreground=OK,  font=F(10, True))
    s.configure("ERR.TLabel",     background=BG,    foreground=ERR, font=F(10, True))

    # ── Buttons (primary) ──
    s.configure("TButton",
                background=ACC, foreground=TXT,
                font=F(11, True), relief="flat",
                borderwidth=0, padding=(14, 7))
    s.map("TButton",
          background=[("active", "#6BA3FF"), ("pressed", ADIM),
                      ("disabled", DIM)])

    # ── Ghost button ──
    s.configure("Ghost.TButton",
                background=SURF2, foreground=MUT,
                font=F(10), relief="flat", borderwidth=0, padding=(10, 5))
    s.map("Ghost.TButton", background=[("active", BDR)])

    # ── Danger button ──
    s.configure("Danger.TButton",
                background="#5A1422", foreground=TXT,
                font=F(11, True), relief="flat", borderwidth=0, padding=(14, 7))
    s.map("Danger.TButton", background=[("active", ERR)])

    # ── Success button ──
    s.configure("Success.TButton",
                background="#1A4D33", foreground=TXT,
                font=F(11, True), relief="flat", borderwidth=0, padding=(14, 7))
    s.map("Success.TButton", background=[("active", OK)])

    # ── Entry ──
    s.configure("TEntry",
                fieldbackground=SURF2, foreground=TXT,
                insertcolor=TXT, font=F(11), relief="flat", borderwidth=0)

    # ── Combobox ──
    s.configure("TCombobox",
                fieldbackground=SURF2, foreground=TXT,
                background=SURF2, font=F(11), arrowcolor=MUT)
    s.map("TCombobox", fieldbackground=[("readonly", SURF2)],
          foreground=[("readonly", TXT)])

    # ── Scale ──
    s.configure("Horizontal.TScale",
                background=BG, troughcolor=BDR,
                sliderlength=18, sliderrelief="flat", borderwidth=0)

    # ── Scrollbar ──
    s.configure("TScrollbar",
                background=BDR, troughcolor=BG,
                relief="flat", borderwidth=0, arrowsize=0)

    # ── Progressbar ──
    s.configure("TProgressbar",
                background=ACC, troughcolor=BDR,
                borderwidth=0, thickness=6)

    # ── Checkbutton / Radiobutton ──
    s.configure("TCheckbutton", background=BG, foreground=TXT, font=F(11))
    s.map("TCheckbutton", background=[("active", BG)])
    s.configure("TRadiobutton", background=BG, foreground=TXT, font=F(11))
    s.map("TRadiobutton", background=[("active", BG)])

    # ── Notebook (tabs) ──
    s.configure("TNotebook",       background=BG, borderwidth=0)
    s.configure("TNotebook.Tab",
                background=SURF2, foreground=MUT,
                font=F(10), padding=(14, 7), borderwidth=0)
    s.map("TNotebook.Tab",
          background=[("selected", SURF)],
          foreground=[("selected", TXT)])

    return s


# ─── Reusable widget components ───────────────────────────────────────────────

class Btn(tk.Button):
    """
    Flat button with smooth hover effect and style variants.
    Styles: 'primary', 'secondary', 'danger', 'success', 'warn'
    """
    _PALETTES = {
        "primary":   (ACC,      "#6BA3FF", TXT),
        "secondary": (SURF2,    BDR,       MUT),
        "danger":    ("#5A1422", ERR,      TXT),
        "success":   ("#1A4D33", OK,       TXT),
        "warn":      ("#4D3500", WARN,     TXT),
    }

    def __init__(self, parent, text, cmd=None, style="primary", **kw):
        bg, hover, fg = self._PALETTES.get(style, self._PALETTES["primary"])
        super().__init__(
            parent, text=text, command=cmd,
            bg=bg, fg=fg, font=F(11, True),
            relief="flat", bd=0, padx=14, pady=7,
            cursor="hand2", activebackground=hover,
            activeforeground=fg, **kw
        )
        self.bind("<Enter>", lambda e: self.config(bg=hover))
        self.bind("<Leave>", lambda e: self.config(bg=bg))


class Slider(tk.Frame):
    """
    A labelled horizontal slider with a live numeric readout.
    Usage:  s = Slider(parent, "Opacity", 0, 100, 50, suffix="%")
            val = s.get()
    """
    def __init__(self, parent, label, from_=0, to=100, default=50,
                 fmt="{:.0f}", suffix="", bg=None, resolution=1, **kw):
        super().__init__(parent, bg=bg or BG)
        self._fmt = fmt
        self._sfx = suffix

        self.var = tk.DoubleVar(value=default)

        tk.Label(self, text=label, bg=bg or BG, fg=MUT,
                 font=F(10), width=16, anchor="w").pack(side="left")

        self.val_lbl = tk.Label(
            self, text=self._show(default), bg=bg or BG,
            fg=ACC, font=F(10, True), width=7, anchor="e"
        )
        self.val_lbl.pack(side="right")

        self.scale = tk.Scale(
            self, variable=self.var, from_=from_, to=to,
            orient="horizontal", bg=bg or BG, fg=TXT,
            troughcolor=BDR, activebackground=ACC,
            highlightthickness=0, bd=0, showvalue=False,
            resolution=resolution, command=self._update
        )
        self.scale.pack(side="left", fill="x", expand=True, padx=(0, 8))

    def _show(self, v):
        return self._fmt.format(float(v)) + self._sfx

    def _update(self, v):
        self.val_lbl.config(text=self._show(float(v)))

    def get(self):
        return self.var.get()

    def set(self, v):
        self.var.set(v)
        self.val_lbl.config(text=self._show(float(v)))


class FilePicker(tk.Frame):
    """
    A labelled file-picker row: shows file name, browse button.
    Set multiple=True for multi-file selection.
    """
    def __init__(self, parent, label="Input:", multiple=False,
                 types=(("PDF", "*.pdf"),), bg=None, **kw):
        super().__init__(parent, bg=bg or BG)
        self.multiple = multiple
        self.types = types
        self.paths = []

        tk.Label(self, text=label, bg=bg or BG, fg=MUT,
                 font=F(10), width=10, anchor="w").pack(side="left")

        self._var = tk.StringVar(value="No file selected")
        tk.Entry(
            self, textvariable=self._var, bg=SURF2, fg=MUT,
            font=F(10), relief="flat", bd=0, state="readonly"
        ).pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 8))

        Btn(self, "Browse", cmd=self._browse, style="secondary").pack(side="right")

    def _browse(self):
        if self.multiple:
            fs = filedialog.askopenfilenames(filetypes=self.types)
            if fs:
                self.paths = list(fs)
                self._var.set(f"{len(fs)} file(s) selected")
        else:
            f = filedialog.askopenfilename(filetypes=self.types)
            if f:
                self.paths = [f]
                self._var.set(os.path.basename(f))

    def get(self):
        return self.paths

    def clear(self):
        self.paths = []
        self._var.set("No file selected")


class OutputRow(tk.Frame):
    """
    Output filename + folder selector combo row.
    Call get_path() to get the full resolved output path.
    """
    def __init__(self, parent, default="output.pdf", bg=None):
        super().__init__(parent, bg=bg or BG)
        b = bg or BG
        self._name = tk.StringVar(value=default)
        self._dir  = tk.StringVar(value=os.path.expanduser("~/Desktop"))

        tk.Label(self, text="Save as:", bg=b, fg=MUT,
                 font=F(10)).pack(side="left", padx=(0, 6))
        tk.Entry(
            self, textvariable=self._name, bg=SURF2, fg=TXT,
            font=F(10), relief="flat", bd=0,
            insertbackground=TXT, width=22
        ).pack(side="left", ipady=5, padx=(0, 10))

        tk.Label(self, text="in:", bg=b, fg=MUT,
                 font=F(10)).pack(side="left")
        tk.Entry(
            self, textvariable=self._dir, bg=SURF2, fg=MUT,
            font=F(10), relief="flat", bd=0,
            state="readonly", width=28
        ).pack(side="left", fill="x", expand=True, ipady=5, padx=(6, 6))

        Btn(self, "📁", cmd=self._pick_dir, style="secondary").pack(side="right")

    def _pick_dir(self):
        d = filedialog.askdirectory(initialdir=self._dir.get())
        if d:
            self._dir.set(d)

    def get_path(self):
        name = self._name.get().strip() or "output"
        if not name.lower().endswith(".pdf"):
            name += ".pdf"
        return os.path.join(self._dir.get(), name)

    def set_name(self, name):
        self._name.set(name)


class Card(tk.Frame):
    """A surface-coloured card with a subtle border."""
    def __init__(self, parent, bg=None, pad=0, **kw):
        super().__init__(parent, bg=bg or SURF, bd=0,
                         highlightthickness=1,
                         highlightbackground=BDR, **kw)
        if pad:
            self.configure(padx=pad, pady=pad)


class Divider(tk.Frame):
    """A 1-pixel horizontal rule."""
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BDR, height=1, **kw)


class LogBox(tk.Frame):
    """
    A scrollable monospace text area for showing progress / log output.
    Call .append(text) to add a line; .clear() to reset.
    """
    def __init__(self, parent, height=6, bg=None, **kw):
        super().__init__(parent, bg=bg or SURF2, **kw)
        sb = tk.Scrollbar(self, bg=BDR)
        self.text = tk.Text(
            self, height=height, bg=SURF2, fg=MUT,
            font=FM(9), relief="flat", bd=0,
            state="disabled", wrap="word",
            yscrollcommand=sb.set, insertbackground=TXT
        )
        sb.config(command=self.text.yview)
        sb.pack(side="right", fill="y")
        self.text.pack(fill="both", expand=True, padx=10, pady=6)

    def append(self, line, color=None):
        self.text.config(state="normal")
        tag = None
        if color:
            tag = f"col_{color.replace('#','')}"
            self.text.tag_configure(tag, foreground=color)
        self.text.insert("end", line + "\n", tag)
        self.text.see("end")
        self.text.config(state="disabled")

    def clear(self):
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.config(state="disabled")


# ─── App shell helpers ────────────────────────────────────────────────────────

def make_window(title, w=780, h=600):
    """Create a themed root window, centred on screen."""
    root = tk.Tk()
    root.title(title)
    root.geometry(f"{w}x{h}")
    root.configure(bg=BG)
    root.minsize(620, 440)
    apply(root)
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")
    return root


def app_header(parent, title, subtitle="", icon=""):
    """
    Renders a consistent top header bar with a coloured left accent,
    app title, and optional subtitle line.
    """
    hdr = tk.Frame(parent, bg=SURF)
    hdr.pack(fill="x")
    tk.Frame(hdr, bg=ACC, width=4).pack(side="left", fill="y")
    inner = tk.Frame(hdr, bg=SURF, padx=18, pady=14)
    inner.pack(side="left", fill="both", expand=True)
    label = f"{icon}  {title}" if icon else title
    tk.Label(inner, text=label, bg=SURF, fg=TXT, font=F(14, True)).pack(anchor="w")
    if subtitle:
        tk.Label(inner, text=subtitle, bg=SURF, fg=MUT, font=F(10)).pack(anchor="w")
    Divider(parent).pack(fill="x")


def toast(parent, message, type_="info"):
    """
    Non-blocking corner toast notification that auto-dismisses after 2.5 s.
    type_ can be 'info', 'success', 'error', 'warning'.
    """
    colours = {"info": ACC, "success": OK, "error": ERR, "warning": WARN}
    c = colours.get(type_, ACC)

    win = tk.Toplevel(parent)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.configure(bg=SURF)

    tk.Frame(win, bg=c, width=4).pack(side="left", fill="y")
    inner = tk.Frame(win, bg=SURF, padx=14, pady=10)
    inner.pack(side="left")
    tk.Label(inner, text=message, bg=SURF, fg=TXT, font=F(10), wraplength=320).pack()

    win.update_idletasks()
    pw = parent.winfo_x() + parent.winfo_width()  - win.winfo_width()  - 16
    ph = parent.winfo_y() + parent.winfo_height() - win.winfo_height() - 16
    win.geometry(f"+{pw}+{ph}")
    win.after(2500, win.destroy)


def popup(parent, title, message, type_="info"):
    """Modal alert dialog — blocks until dismissed."""
    icons   = {"info": "ℹ", "success": "✓", "error": "✗", "warning": "⚠"}
    colours = {"info": ACC, "success": OK,  "error": ERR, "warning": WARN}
    icon  = icons.get(type_, "ℹ")
    color = colours.get(type_, ACC)

    win = tk.Toplevel(parent)
    win.title(title)
    win.configure(bg=BG)
    win.geometry("420x190")
    win.resizable(False, False)
    win.grab_set()

    win.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width()  - 420) // 2
    y = parent.winfo_y() + (parent.winfo_height() - 190) // 2
    win.geometry(f"+{x}+{y}")

    tk.Frame(win, bg=color, height=3).pack(fill="x")
    body = tk.Frame(win, bg=BG, padx=24, pady=18)
    body.pack(fill="both", expand=True)

    row = tk.Frame(body, bg=BG)
    row.pack(fill="x")
    tk.Label(row, text=icon,  bg=BG, fg=color, font=F(18)).pack(side="left", padx=(0, 10))
    tk.Label(row, text=title, bg=BG, fg=TXT,   font=F(12, True)).pack(side="left")

    tk.Label(body, text=message, bg=BG, fg=MUT, font=F(10),
             wraplength=370, justify="left").pack(anchor="w", pady=(8, 16))

    Btn(body, "  OK  ", cmd=win.destroy).pack(anchor="e")
    win.wait_window()


def render_pdf_page(doc, page_num, zoom=1.5):
    """
    Render a fitz page to a tkinter PhotoImage.
    Requires: PyMuPDF (fitz), Pillow
    """
    import io
    from PIL import Image, ImageTk
    pix = doc[page_num].get_pixmap(matrix=__import__("fitz").Matrix(zoom, zoom))
    img = Image.open(io.BytesIO(pix.tobytes("ppm")))
    return ImageTk.PhotoImage(img)
