"""
pdf_split.py — Joydip's PDF Suite
Split a PDF by custom page ranges, every-N-pages, or individual extractions.
"""

import tkinter as tk
from tkinter import ttk
import os, threading, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import theme as T

try:
    import fitz
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "pymupdf", "--break-system-packages"],
                   capture_output=True)
    import fitz


# ─── Page-range parser ────────────────────────────────────────────────────────
def parse_ranges(text, n_pages):
    """
    Convert a string like "1-5, 8, 10-12" into a list of 0-based page index lists.
    Each comma-separated token becomes its own output document.
    Raises ValueError with a descriptive message on invalid syntax.
    """
    segments = []
    for token in text.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            parts = token.split("-", 1)
            try:
                a, b = int(parts[0]), int(parts[1])
            except ValueError:
                raise ValueError(f"Invalid range token: '{token}'")
            if a < 1 or b < a or b > n_pages:
                raise ValueError(
                    f"Range {token} is out of bounds (document has {n_pages} pages).")
            segments.append(list(range(a - 1, b)))  # convert to 0-based
        else:
            try:
                p = int(token)
            except ValueError:
                raise ValueError(f"Invalid page number: '{token}'")
            if p < 1 or p > n_pages:
                raise ValueError(
                    f"Page {p} is out of bounds (document has {n_pages} pages).")
            segments.append([p - 1])
    if not segments:
        raise ValueError("No valid page ranges entered.")
    return segments


def every_n_pages(n_pages, n):
    """Split into chunks of n pages each."""
    return [list(range(i, min(i + n, n_pages))) for i in range(0, n_pages, n)]


class SplitApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF Split — Joydip's Suite")
        self.geometry("800x640")
        self.minsize(640, 480)
        T.apply(self)
        self._centre()
        self._src_doc = None   # fitz.Document or None
        self._segments = []    # list of page-index lists
        self._build()

    def _centre(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"800x640+{(sw-800)//2}+{(sh-640)//2}")

    # ─── UI ───────────────────────────────────────────────────────────────────
    def _build(self):
        T.app_header(self, "PDF Split",
                     "Split one PDF into multiple documents by page ranges or intervals", "✂")

        body = tk.Frame(self, bg=T.BG, padx=20, pady=14)
        body.pack(fill="both", expand=True)

        # ── Source file ──
        src_card = T.Card(body)
        src_card.pack(fill="x", pady=(0, 10))
        src_inner = tk.Frame(src_card, bg=T.SURF, padx=12, pady=10)
        src_inner.pack(fill="x")
        tk.Label(src_inner, text="Source PDF:", bg=T.SURF, fg=T.MUT,
                 font=T.F(10)).pack(anchor="w", pady=(0, 5))
        self.src_picker = T.FilePicker(src_inner, "File:", bg=T.SURF)
        self.src_picker.pack(fill="x")
        T.Btn(src_inner, "Load File", cmd=self._load_src, style="secondary",
              font=T.F(10, True), padx=9, pady=4).pack(anchor="e", pady=(6, 0))
        self.src_info = tk.Label(src_inner, text="", bg=T.SURF, fg=T.MUT, font=T.F(9))
        self.src_info.pack(anchor="w")

        # ── Mode tabs ──
        tab_card = T.Card(body)
        tab_card.pack(fill="x", pady=(0, 10))
        self.nb = ttk.Notebook(tab_card)
        self.nb.pack(fill="x", padx=0, pady=0)

        # Tab 1: custom ranges
        t1 = tk.Frame(self.nb, bg=T.SURF, padx=14, pady=10)
        self.nb.add(t1, text="  Custom Ranges  ")
        tk.Label(t1, text='Page ranges (e.g. "1-5, 8, 10-12")  — each token → separate PDF:',
                 bg=T.SURF, fg=T.MUT, font=T.F(10)).pack(anchor="w")
        self.range_var = tk.StringVar()
        tk.Entry(t1, textvariable=self.range_var, bg=T.SURF2, fg=T.TXT,
                 font=T.F(11), relief="flat", bd=0, insertbackground=T.TXT
                 ).pack(fill="x", ipady=6, pady=(5, 0))

        # Tab 2: every N pages
        t2 = tk.Frame(self.nb, bg=T.SURF, padx=14, pady=10)
        self.nb.add(t2, text="  Every N Pages  ")
        tk.Label(t2, text="Split the document into equal chunks of N pages each:",
                 bg=T.SURF, fg=T.MUT, font=T.F(10)).pack(anchor="w")
        self.n_slider = T.Slider(t2, "Pages per chunk", 1, 50, 10, bg=T.SURF)
        self.n_slider.pack(fill="x", pady=(8, 0))

        # Tab 3: extract single pages
        t3 = tk.Frame(self.nb, bg=T.SURF, padx=14, pady=10)
        self.nb.add(t3, text="  Extract Pages  ")
        tk.Label(t3, text='Extract individual pages as separate PDFs (e.g. "3, 7, 12"):',
                 bg=T.SURF, fg=T.MUT, font=T.F(10)).pack(anchor="w")
        self.extract_var = tk.StringVar()
        tk.Entry(t3, textvariable=self.extract_var, bg=T.SURF2, fg=T.TXT,
                 font=T.F(11), relief="flat", bd=0, insertbackground=T.TXT
                 ).pack(fill="x", ipady=6, pady=(5, 0))

        # ── Preview of splits ──
        prev_card = T.Card(body)
        prev_card.pack(fill="x", pady=(0, 10))
        prev_inner = tk.Frame(prev_card, bg=T.SURF, padx=12, pady=8)
        prev_inner.pack(fill="x")
        top = tk.Frame(prev_inner, bg=T.SURF)
        top.pack(fill="x")
        tk.Label(top, text="Preview of output documents:", bg=T.SURF, fg=T.MUT,
                 font=T.F(10)).pack(side="left")
        T.Btn(top, "Preview", cmd=self._preview, style="secondary",
              font=T.F(10, True), padx=9, pady=3).pack(side="right")

        sb = tk.Scrollbar(prev_inner, bg=T.BDR, relief="flat", bd=0)
        self.prev_lb = tk.Listbox(
            prev_inner, bg=T.SURF2, fg=T.TXT, font=T.FM(9),
            selectbackground=T.ADIM, relief="flat", bd=0,
            yscrollcommand=sb.set, height=5, activestyle="none"
        )
        sb.config(command=self.prev_lb.yview)
        sb.pack(side="right", fill="y")
        self.prev_lb.pack(fill="x", pady=(4, 0))

        # ── Output directory ──
        out_card = T.Card(body)
        out_card.pack(fill="x", pady=(0, 8))
        out_inner = tk.Frame(out_card, bg=T.SURF, padx=12, pady=8)
        out_inner.pack(fill="x")
        tk.Label(out_inner, text="Save output files to:", bg=T.SURF, fg=T.MUT,
                 font=T.F(10)).pack(anchor="w", pady=(0, 4))
        dir_row = tk.Frame(out_inner, bg=T.SURF)
        dir_row.pack(fill="x")
        self._out_dir = tk.StringVar(value=os.path.expanduser("~/Desktop"))
        tk.Entry(dir_row, textvariable=self._out_dir, bg=T.SURF2, fg=T.TXT,
                 font=T.F(10), relief="flat", bd=0, state="readonly",
                 ).pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 8))
        T.Btn(dir_row, "📁", cmd=self._pick_dir, style="secondary",
              padx=8, pady=4).pack(side="right")

        # ── Progress, log, run button ──
        self.prog = ttk.Progressbar(body, mode="determinate")
        self.prog.pack(fill="x", pady=(0, 4))
        self.log = T.LogBox(body, height=3)
        self.log.pack(fill="x", pady=(0, 8))

        T.Btn(body, "✂   Split PDF", cmd=self._start_split,
              style="primary", font=T.F(12, True)).pack(side="right")

    # ─── Source file loading ──────────────────────────────────────────────────
    def _load_src(self):
        paths = self.src_picker.get()
        if not paths:
            T.popup(self, "No file selected", "Click Browse first to pick a PDF.", "warning")
            return
        path = paths[0]
        try:
            if self._src_doc:
                self._src_doc.close()
            self._src_doc = fitz.open(path)
            n = len(self._src_doc)
            size_mb = os.path.getsize(path) / 1048576
            self.src_info.config(
                text=f"Loaded: {os.path.basename(path)}  |  {n} pages  |  {size_mb:.1f} MB",
                fg=T.OK)
            # Auto-suggest a sane default name prefix
            stem = os.path.splitext(os.path.basename(path))[0]
            self._stem = stem
        except Exception as e:
            T.popup(self, "Load Error", str(e), "error")

    def _pick_dir(self):
        from tkinter import filedialog
        d = filedialog.askdirectory(initialdir=self._out_dir.get())
        if d:
            self._out_dir.set(d)

    # ─── Preview computation ──────────────────────────────────────────────────
    def _compute_segments(self):
        if not self._src_doc:
            raise ValueError("Load a PDF file first.")
        n = len(self._src_doc)
        tab = self.nb.index(self.nb.select())
        if tab == 0:
            return parse_ranges(self.range_var.get(), n)
        elif tab == 1:
            chunk = max(1, int(self.n_slider.get()))
            return every_n_pages(n, chunk)
        else:
            return parse_ranges(self.extract_var.get(), n)

    def _preview(self):
        try:
            segs = self._compute_segments()
            self._segments = segs
            self.prev_lb.delete(0, "end")
            n = len(self._src_doc)
            for i, pages in enumerate(segs):
                p_from = pages[0] + 1
                p_to   = pages[-1] + 1
                count  = len(pages)
                range_str = f"p{p_from}" if count == 1 else f"p{p_from}–p{p_to}"
                label = (f"  Doc {i+1:02d}:  {range_str}  "
                         f"({count} page{'s' if count>1 else ''})  →  "
                         f"{getattr(self,'_stem','output')}_{i+1:02d}_{range_str}.pdf")
                self.prev_lb.insert("end", label)
            self.log.clear()
            self.log.append(f"Preview computed: {len(segs)} output document(s).", T.OK)
        except ValueError as e:
            T.popup(self, "Range Error", str(e), "error")
        except Exception as e:
            T.popup(self, "Error", str(e), "error")

    # ─── Split logic ──────────────────────────────────────────────────────────
    def _start_split(self):
        try:
            segs = self._compute_segments()
            self._segments = segs
        except (ValueError, Exception) as e:
            T.popup(self, "Error", str(e), "error")
            return

        out_dir = self._out_dir.get()
        stem    = getattr(self, "_stem", "output")
        doc     = self._src_doc
        self.prog["value"] = 0
        self.log.clear()
        self.log.append(f"Splitting into {len(segs)} document(s) …")

        def worker():
            try:
                total = len(segs)
                for i, pages in enumerate(segs):
                    p_from = pages[0] + 1
                    p_to   = pages[-1] + 1
                    count  = len(pages)
                    range_str = (f"p{p_from}" if count == 1
                                 else f"p{p_from}-p{p_to}")
                    fname = f"{stem}_{i+1:02d}_{range_str}.pdf"
                    out_path = os.path.join(out_dir, fname)

                    out_doc = fitz.open()
                    out_doc.insert_pdf(doc, from_page=pages[0], to_page=pages[-1])
                    out_doc.save(out_path, garbage=4, deflate=True)
                    out_doc.close()

                    self.prog["value"] = int((i + 1) / total * 100)
                    self.log.append(f"  ✓  Saved: {fname}", T.OK)

                self.log.append(f"\nAll {total} file(s) saved to {out_dir}", T.OK)
                T.toast(self, f"Split complete — {total} file(s) saved  ✓", "success")
            except Exception as e:
                self.log.append(f"ERROR: {e}", T.ERR)
                T.popup(self, "Split Failed", str(e), "error")

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    SplitApp().mainloop()
