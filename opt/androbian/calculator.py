"""
calculator.py — Joydip's PDF Suite
A scientific calculator with graphing capability.
Supports standard arithmetic, trigonometry, logarithms, constants,
expression evaluation, and function plotting via matplotlib/canvas fallback.
"""

import tkinter as tk
from tkinter import ttk
import math, sys, os, cmath
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import theme as T

# ─── Safe expression evaluator ────────────────────────────────────────────────
SAFE_NAMES = {
    k: v for k, v in math.__dict__.items()
    if not k.startswith("_")
}
SAFE_NAMES.update({
    "pi": math.pi, "e": math.e, "tau": math.tau,
    "inf": math.inf, "nan": math.nan,
    "abs": abs, "round": round, "int": int, "float": float,
    "log": math.log, "log2": math.log2, "log10": math.log10,
    "ln": math.log,         # convenient alias
    "exp": math.exp,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "atan2": math.atan2,
    "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
    "sqrt": math.sqrt, "cbrt": lambda x: x**(1/3),
    "pow": pow,
    "factorial": math.factorial,
    "comb": math.comb, "perm": math.perm,
    "gcd": math.gcd,
    "degrees": math.degrees, "radians": math.radians,
    "floor": math.floor, "ceil": math.ceil, "trunc": math.trunc,
    "mod": lambda a, b: a % b,
    "__builtins__": {},
}

def safe_eval(expr):
    expr = expr.replace("^", "**").replace("×", "*").replace("÷", "/")
    return eval(compile(expr, "<string>", "eval"), SAFE_NAMES)


# ─── Graph engine (uses matplotlib if available, canvas fallback otherwise) ───
try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.pyplot as plt
    import numpy as np
    MPL = True
except ImportError:
    MPL = False


class CalcApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Scientific Calculator — Joydip's Suite")
        self.geometry("860x620")
        self.minsize(700, 500)
        T.apply(self)
        self._centre()
        self._history = []
        self._hist_idx = -1
        self._build()

    def _centre(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"860x620+{(sw-860)//2}+{(sh-620)//2}")

    # ─── UI construction ──────────────────────────────────────────────────────
    def _build(self):
        T.app_header(self, "Scientific Calculator",
                     "Full expression evaluator with graphing support", "∑")

        body = tk.Frame(self, bg=T.BG, padx=20, pady=14)
        body.pack(fill="both", expand=True)

        nb = ttk.Notebook(body)
        nb.pack(fill="both", expand=True)

        # ── Tab 1: Calculator ──
        calc_tab = tk.Frame(nb, bg=T.BG)
        nb.add(calc_tab, text="  Calculator  ")
        self._build_calc(calc_tab)

        # ── Tab 2: Grapher ──
        graph_tab = tk.Frame(nb, bg=T.BG)
        nb.add(graph_tab, text="  Grapher  ")
        self._build_graph(graph_tab)

        # ── Tab 3: History ──
        hist_tab = tk.Frame(nb, bg=T.BG)
        nb.add(hist_tab, text="  History  ")
        self._build_history(hist_tab)

    # ─── Calculator tab ───────────────────────────────────────────────────────
    def _build_calc(self, parent):
        # Display
        disp_card = T.Card(parent)
        disp_card.pack(fill="x", padx=0, pady=(12, 8))
        d_i = tk.Frame(disp_card, bg=T.SURF, padx=12, pady=8)
        d_i.pack(fill="x")
        self._expr_var = tk.StringVar()
        self._result_var = tk.StringVar(value="0")
        tk.Entry(d_i, textvariable=self._expr_var, bg=T.SURF2, fg=T.MUT,
                 font=T.F(13), relief="flat", bd=0, insertbackground=T.TXT,
                 ).pack(fill="x", ipady=5)
        tk.Label(d_i, textvariable=self._result_var, bg=T.SURF, fg=T.TXT,
                 font=T.F(20, True), anchor="e").pack(fill="x", pady=(4, 0))

        # Keyboard binding
        self.bind("<Return>",    lambda e: self._calc())
        self.bind("<BackSpace>", lambda e: self._backspace())
        self.bind("<Escape>",    lambda e: self._clear())

        # ── Button grid ──
        btn_frame = tk.Frame(parent, bg=T.BG)
        btn_frame.pack(fill="both", expand=True, pady=(0, 6))

        # Button layout: (label, insert_text, is_op)
        ROWS = [
            [("sin(",  "sin(",  False), ("cos(",  "cos(",  False), ("tan(",  "tan(",  False),
             ("log(",  "log(",  False), ("ln(",   "ln(",   False),  ("√",    "sqrt(", False)],

            [("π",  "pi",   False), ("e",  "e",    False), ("x²", "**2",  False),
             ("xⁿ", "**",   False), ("|x|","abs(", False), ("n!", "factorial(", False)],

            [("7", "7", False), ("8", "8", False), ("9", "9", False),
             ("÷", "/",  True),  ("(", "(", False), (")", ")", False)],

            [("4", "4", False), ("5", "5", False), ("6", "6", False),
             ("×", "*",  True),  ("%", "%", False), ("^", "**",False)],

            [("1", "1", False), ("2", "2", False), ("3", "3", False),
             ("−", "-",  True),  (".", ".", False), ("←", None, "back")],

            [("0", "0", False), ("00", "00", False), ("C", None, "clear"),
             ("+", "+",  True), ("ANS", None, "ans"), ("=", None, "eq")],
        ]

        for r, row in enumerate(ROWS):
            rf = tk.Frame(btn_frame, bg=T.BG)
            rf.pack(fill="x", expand=True, padx=0, pady=1)
            for c, (label, ins, special) in enumerate(row):
                if special == "eq":
                    st, cmd = "primary", self._calc
                elif special == "clear":
                    st, cmd = "danger", self._clear
                elif special == "back":
                    st, cmd = "secondary", self._backspace
                elif special == "ans":
                    st, cmd = "secondary", self._insert_ans
                elif special:  # True = operator
                    st, cmd = "warn", lambda t=ins: self._insert(t)
                else:
                    st, cmd = "secondary", lambda t=ins: self._insert(t)
                T.Btn(rf, label, cmd=cmd, style=st,
                      font=T.F(11, label in ("=",)),
                      ).pack(side="left", fill="x", expand=True, padx=1)

    def _insert(self, text):
        cur = self._expr_var.get()
        self._expr_var.set(cur + text)
        self._live_eval()

    def _backspace(self):
        cur = self._expr_var.get()
        self._expr_var.set(cur[:-1])
        self._live_eval()

    def _clear(self):
        self._expr_var.set("")
        self._result_var.set("0")

    def _insert_ans(self):
        if self._history:
            self._insert(str(self._history[-1][1]))

    def _live_eval(self):
        """Show rolling evaluation result without adding to history."""
        expr = self._expr_var.get().strip()
        if not expr:
            self._result_var.set("0")
            return
        try:
            result = safe_eval(expr)
            self._result_var.set(self._fmt(result))
        except Exception:
            self._result_var.set("…")

    def _calc(self):
        expr = self._expr_var.get().strip()
        if not expr:
            return
        try:
            result = safe_eval(expr)
            fmted  = self._fmt(result)
            self._result_var.set(fmted)
            self._history.append((expr, result))
            self._hist_var.set("\n".join(
                f"{e}  =  {self._fmt(r)}" for e, r in reversed(self._history[-30:])))
        except Exception as ex:
            self._result_var.set(f"Error: {ex}")

    def _fmt(self, v):
        if isinstance(v, float):
            if v == int(v) and abs(v) < 1e15:
                return str(int(v))
            return f"{v:.10g}"
        return str(v)

    # ─── Grapher tab ──────────────────────────────────────────────────────────
    def _build_graph(self, parent):
        top = tk.Frame(parent, bg=T.BG, padx=12, pady=10)
        top.pack(fill="x")

        fn_row = tk.Frame(top, bg=T.BG)
        fn_row.pack(fill="x", pady=(0, 6))
        tk.Label(fn_row, text="f(x) =", bg=T.BG, fg=T.MUT, font=T.F(12),
                 width=7, anchor="e").pack(side="left")
        self._fn_var = tk.StringVar(value="sin(x)")
        tk.Entry(fn_row, textvariable=self._fn_var, bg=T.SURF2, fg=T.TXT,
                 font=T.F(12), relief="flat", bd=0, insertbackground=T.TXT
                 ).pack(side="left", fill="x", expand=True, ipady=5, padx=(6, 8))
        T.Btn(fn_row, "Plot", cmd=self._plot, style="primary",
              font=T.F(11, True), padx=12, pady=5).pack(side="right")

        range_row = tk.Frame(top, bg=T.BG)
        range_row.pack(fill="x", pady=(0, 6))
        for lbl, var, default in [
            ("x min:", "_xmin", "-10"), ("x max:", "_xmax", "10"),
            ("y min:", "_ymin", "auto"), ("y max:", "_ymax", "auto"),
        ]:
            tk.Label(range_row, text=lbl, bg=T.BG, fg=T.MUT, font=T.F(10)).pack(side="left")
            v = tk.StringVar(value=default)
            setattr(self, var, v)
            tk.Entry(range_row, textvariable=v, bg=T.SURF2, fg=T.TXT,
                     font=T.F(10), relief="flat", bd=0, width=7,
                     insertbackground=T.TXT).pack(side="left", ipady=4, padx=(2, 12))

        if MPL:
            fig, self._ax = plt.subplots(facecolor=T.BG, figsize=(6, 4))
            self._ax.set_facecolor(T.SURF2)
            self._ax.tick_params(colors=T.MUT, labelsize=8)
            for spine in self._ax.spines.values():
                spine.set_color(T.BDR)
            self._ax.grid(True, color=T.BDR, linewidth=0.5, linestyle="--")
            self._mpl_canvas = FigureCanvasTkAgg(fig, parent)
            self._mpl_canvas.get_tk_widget().pack(fill="both", expand=True, padx=12, pady=4)
        else:
            self._canvas = tk.Canvas(parent, bg=T.SURF2, highlightthickness=0)
            self._canvas.pack(fill="both", expand=True, padx=12, pady=4)
            tk.Label(parent,
                     text="Install matplotlib and numpy for graphing: "
                          "pip install matplotlib numpy",
                     bg=T.BG, fg=T.MUT, font=T.F(9)).pack()

    def _plot(self):
        if not MPL:
            T.popup(self, "matplotlib not installed",
                    "Run: pip install matplotlib numpy --break-system-packages",
                    "warning")
            return
        fn   = self._fn_var.get().strip()
        xmin = float(self._xmin.get() or -10)
        xmax = float(self._xmax.get() or 10)

        x = np.linspace(xmin, xmax, 800)
        local_ns = dict(SAFE_NAMES)
        local_ns.update({
            "sin": np.sin, "cos": np.cos, "tan": np.tan,
            "log": np.log, "log10": np.log10, "log2": np.log2,
            "exp": np.exp, "sqrt": np.sqrt, "abs": np.abs,
            "x": x,
        })
        try:
            y = eval(compile(fn.replace("^","**"), "<f>", "eval"), local_ns)
            self._ax.clear()
            self._ax.set_facecolor(T.SURF2)
            self._ax.grid(True, color=T.BDR, linewidth=0.5, linestyle="--")
            self._ax.plot(x, y, color=T.ACC, linewidth=1.8, label=f"f(x) = {fn}")
            self._ax.axhline(0, color=T.BDR, linewidth=0.8)
            self._ax.axvline(0, color=T.BDR, linewidth=0.8)
            self._ax.legend(facecolor=T.SURF, edgecolor=T.BDR,
                            labelcolor=T.TXT, fontsize=9)
            ymin_s = self._ymin.get()
            ymax_s = self._ymax.get()
            if ymin_s.lower() != "auto" and ymax_s.lower() != "auto":
                self._ax.set_ylim(float(ymin_s), float(ymax_s))
            self._ax.set_xlim(xmin, xmax)
            self._mpl_canvas.draw()
        except Exception as e:
            T.popup(self, "Plot Error", str(e), "error")

    # ─── History tab ─────────────────────────────────────────────────────────
    def _build_history(self, parent):
        top = tk.Frame(parent, bg=T.BG, padx=12, pady=10)
        top.pack(fill="x")
        T.Btn(top, "Clear History", cmd=self._clear_hist,
              style="danger", font=T.F(10, True)).pack(anchor="e")
        T.Divider(parent).pack(fill="x")
        self._hist_var = tk.StringVar(value="No calculations yet.")
        self._hist_log = T.LogBox(parent, height=20)
        self._hist_log.pack(fill="both", expand=True, padx=12, pady=10)

    def _clear_hist(self):
        self._history.clear()
        self._hist_log.clear()


if __name__ == "__main__":
    CalcApp().mainloop()
