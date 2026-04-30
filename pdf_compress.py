"""
pdf_compress.py — Joydip's PDF Suite
Compress a PDF using PyMuPDF's garbage-collection and deflate options.
For aggressive compression, Ghostscript is used if installed.
"""

import tkinter as tk
from tkinter import ttk
import os, threading, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import theme as T

try:
    import fitz
except ImportError:
    subprocess.run(["pip", "install", "pymupdf", "--break-system-packages"],
                   capture_output=True)
    import fitz

GS_SETTINGS = {
    "Screen  (72 dpi — smallest)": "/screen",
    "Ebook   (150 dpi — balanced)": "/ebook",
    "Printer (300 dpi — high quality)": "/printer",
    "Prepress (330 dpi — maximum quality)": "/prepress",
}

def compress_pymupdf(inp, out, log_cb):
    """Fast in-process compression using PyMuPDF garbage + deflate."""
    doc = fitz.open(inp)
    doc.save(out, garbage=4, deflate=True, deflate_images=True, deflate_fonts=True)
    doc.close()
    before = os.path.getsize(inp)
    after  = os.path.getsize(out)
    log_cb(f"Original : {before/1048576:.2f} MB")
    log_cb(f"Compressed: {after/1048576:.2f} MB")
    log_cb(f"Reduction : {(1 - after/before)*100:.1f}%")

def compress_ghostscript(inp, out, setting, log_cb):
    """Aggressive lossy compression via Ghostscript (if installed)."""
    gs_cmd = [
        "gs", "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS={setting}",
        "-dNOPAUSE", "-dQUIET", "-dBATCH",
        f"-sOutputFile={out}", inp
    ]
    try:
        result = subprocess.run(gs_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            log_cb(f"Ghostscript error: {result.stderr[:200]}", T.ERR)
            return False
        before = os.path.getsize(inp)
        after  = os.path.getsize(out)
        log_cb(f"Original  : {before/1048576:.2f} MB")
        log_cb(f"Compressed: {after/1048576:.2f} MB")
        log_cb(f"Reduction : {(1 - after/before)*100:.1f}%")
        return True
    except FileNotFoundError:
        log_cb("Ghostscript not found. Install with: sudo apt install ghostscript", T.WARN)
        return False

class CompressApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF Compress — Joydip's Suite")
        self.geometry("700x460")
        T.apply(self)
        self._centre()
        self._build()

    def _centre(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"700x460+{(sw-700)//2}+{(sh-460)//2}")

    def _build(self):
        T.app_header(self, "PDF Compress", "Reduce PDF file size efficiently", "⊘")
        body = tk.Frame(self, bg=T.BG, padx=20, pady=14)
        body.pack(fill="both", expand=True)

        src_card = T.Card(body)
        src_card.pack(fill="x", pady=(0, 10))
        src_i = tk.Frame(src_card, bg=T.SURF, padx=12, pady=10)
        src_i.pack(fill="x")
        tk.Label(src_i, text="Source PDF:", bg=T.SURF, fg=T.MUT, font=T.F(10)
                 ).pack(anchor="w", pady=(0, 5))
        self.picker = T.FilePicker(src_i, bg=T.SURF)
        self.picker.pack(fill="x")

        mode_card = T.Card(body)
        mode_card.pack(fill="x", pady=(0, 10))
        m_i = tk.Frame(mode_card, bg=T.SURF, padx=12, pady=10)
        m_i.pack(fill="x")
        tk.Label(m_i, text="Compression mode:", bg=T.SURF, fg=T.MUT, font=T.F(10)
                 ).pack(anchor="w", pady=(0, 5))
        self._mode = tk.StringVar(value="fast")
        tk.Radiobutton(m_i, text="Fast (lossless, PyMuPDF only — no Ghostscript needed)",
                       variable=self._mode, value="fast",
                       bg=T.SURF, fg=T.TXT, selectcolor=T.SURF2,
                       activebackground=T.SURF, font=T.F(10)).pack(anchor="w")
        tk.Radiobutton(m_i, text="Aggressive (lossy, requires Ghostscript installed):",
                       variable=self._mode, value="gs",
                       bg=T.SURF, fg=T.TXT, selectcolor=T.SURF2,
                       activebackground=T.SURF, font=T.F(10)).pack(anchor="w", pady=(4, 0))
        self.gs_var = tk.StringVar(value="Ebook   (150 dpi — balanced)")
        ttk.Combobox(m_i, textvariable=self.gs_var,
                     values=list(GS_SETTINGS.keys()), state="readonly",
                     width=40).pack(anchor="w", padx=(24, 0), pady=(2, 0))

        out_card = T.Card(body)
        out_card.pack(fill="x", pady=(0, 8))
        out_i = tk.Frame(out_card, bg=T.SURF, padx=12, pady=8)
        out_i.pack(fill="x")
        tk.Label(out_i, text="Output:", bg=T.SURF, fg=T.MUT, font=T.F(10)
                 ).pack(anchor="w", pady=(0, 4))
        self.out_row = T.OutputRow(out_i, "compressed_output.pdf", bg=T.SURF)
        self.out_row.pack(fill="x")

        self.prog = ttk.Progressbar(body, mode="indeterminate")
        self.prog.pack(fill="x", pady=(0, 4))
        self.log = T.LogBox(body, height=4)
        self.log.pack(fill="x", pady=(0, 8))
        T.Btn(body, "⊘   Compress PDF", cmd=self._start,
              style="primary", font=T.F(12, True)).pack(side="right")

    def _start(self):
        paths = self.picker.get()
        if not paths:
            T.popup(self, "No file", "Select a PDF first.", "warning")
            return
        inp  = paths[0]
        out  = self.out_row.get_path()
        mode = self._mode.get()
        self.log.clear()
        self.prog.start(10)

        def worker():
            try:
                if mode == "fast":
                    compress_pymupdf(inp, out,
                                     lambda m, c=T.TXT: self.log.append(m, c))
                else:
                    setting = GS_SETTINGS[self.gs_var.get()]
                    compress_ghostscript(inp, out, setting,
                                         lambda m, c=T.TXT: self.log.append(m, c))
                self.prog.stop()
                self.log.append(f"✓  Saved to: {out}", T.OK)
                T.toast(self, "Compression done  ✓", "success")
            except Exception as e:
                self.prog.stop()
                self.log.append(f"ERROR: {e}", T.ERR)

        threading.Thread(target=worker, daemon=True).start()

if __name__ == "__main__":
    CompressApp().mainloop()
