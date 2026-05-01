"""
pdf_to_image.py — Joydip's PDF Suite
Extract any page from a PDF as a high-quality image (PNG or JPEG).
Supports DPI selection, page range, and batch export.
"""

import tkinter as tk
from tkinter import ttk, filedialog
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

try:
    from PIL import Image, ImageTk
    PIL_OK = True
except ImportError:
    PIL_OK = False


class Pdf2ImgApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF → Image — Joydip's Suite")
        self.geometry("740x580")
        T.apply(self)
        self._centre()
        self._doc = None
        self._photo = None
        self._build()

    def _centre(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"740x580+{(sw-740)//2}+{(sh-580)//2}")

    def _build(self):
        T.app_header(self, "PDF → Image",
                     "Extract PDF pages as PNG or JPEG images at any resolution", "◫")
        body = tk.Frame(self, bg=T.BG, padx=20, pady=14)
        body.pack(fill="both", expand=True)

        # Source
        src_card = T.Card(body)
        src_card.pack(fill="x", pady=(0, 10))
        src_i = tk.Frame(src_card, bg=T.SURF, padx=12, pady=10)
        src_i.pack(fill="x")
        tk.Label(src_i, text="Source PDF:", bg=T.SURF, fg=T.MUT, font=T.F(10)
                 ).pack(anchor="w", pady=(0, 5))
        self.picker = T.FilePicker(src_i, bg=T.SURF)
        self.picker.pack(fill="x")
        T.Btn(src_i, "Load PDF", cmd=self._load, style="secondary",
              font=T.F(10, True), padx=9, pady=4).pack(anchor="e", pady=(5, 0))
        self.src_info = tk.Label(src_i, text="", bg=T.SURF, fg=T.MUT, font=T.F(9))
        self.src_info.pack(anchor="w")

        # Two-column: controls + mini preview
        mid = tk.Frame(body, bg=T.BG)
        mid.pack(fill="both", expand=True, pady=(0, 10))

        left = tk.Frame(mid, bg=T.BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        right = T.Card(mid, width=220)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        # Controls
        ctrl_card = T.Card(left)
        ctrl_card.pack(fill="x", pady=(0, 10))
        c_i = tk.Frame(ctrl_card, bg=T.SURF, padx=12, pady=10)
        c_i.pack(fill="x")

        dpi_row = tk.Frame(c_i, bg=T.SURF)
        dpi_row.pack(fill="x", pady=(0, 6))
        tk.Label(dpi_row, text="Resolution (DPI):", bg=T.SURF, fg=T.MUT,
                 font=T.F(10), width=18, anchor="w").pack(side="left")
        self._dpi = tk.StringVar(value="150")
        for dpi in ("72", "96", "150", "200", "300", "600"):
            tk.Radiobutton(dpi_row, text=dpi, variable=self._dpi, value=dpi,
                           bg=T.SURF, fg=T.TXT, selectcolor=T.SURF2,
                           activebackground=T.SURF, font=T.F(10)
                           ).pack(side="left", padx=4)

        fmt_row = tk.Frame(c_i, bg=T.SURF)
        fmt_row.pack(fill="x", pady=(0, 6))
        tk.Label(fmt_row, text="Format:", bg=T.SURF, fg=T.MUT,
                 font=T.F(10), width=18, anchor="w").pack(side="left")
        self._fmt = tk.StringVar(value="PNG")
        for fmt in ("PNG", "JPEG"):
            tk.Radiobutton(fmt_row, text=fmt, variable=self._fmt, value=fmt,
                           bg=T.SURF, fg=T.TXT, selectcolor=T.SURF2,
                           activebackground=T.SURF, font=T.F(10)
                           ).pack(side="left", padx=4)

        range_row = tk.Frame(c_i, bg=T.SURF)
        range_row.pack(fill="x", pady=(0, 6))
        tk.Label(range_row, text='Pages (e.g. "1-5, 8"):',
                 bg=T.SURF, fg=T.MUT, font=T.F(10), width=18, anchor="w"
                 ).pack(side="left")
        self._pages_var = tk.StringVar(value="all")
        tk.Entry(range_row, textvariable=self._pages_var, bg=T.SURF2, fg=T.TXT,
                 font=T.F(10), relief="flat", bd=0, insertbackground=T.TXT,
                 width=20).pack(side="left", ipady=4)

        # Output directory
        out_row = tk.Frame(c_i, bg=T.SURF)
        out_row.pack(fill="x", pady=(4, 0))
        tk.Label(out_row, text="Save images to:", bg=T.SURF, fg=T.MUT,
                 font=T.F(10), width=18, anchor="w").pack(side="left")
        self._out_dir = tk.StringVar(value=os.path.expanduser("~/Desktop"))
        tk.Entry(out_row, textvariable=self._out_dir, bg=T.SURF2, fg=T.TXT,
                 font=T.F(10), relief="flat", bd=0, state="readonly",
                 width=24).pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 6))
        T.Btn(out_row, "📁", cmd=self._pick_dir, style="secondary",
              padx=6, pady=3).pack(side="right")

        # Preview controls
        tk.Label(right, text="Page Preview", bg=T.SURF, fg=T.MUT,
                 font=T.F(10)).pack(pady=(8, 2))
        T.Divider(right).pack(fill="x")
        self.canvas = tk.Canvas(right, bg=T.SURF2, highlightthickness=0,
                                width=200, height=270)
        self.canvas.pack(pady=6, padx=6)

        pg_row = tk.Frame(right, bg=T.SURF)
        pg_row.pack()
        T.Btn(pg_row, "◀", cmd=lambda: self._nav(-1), style="secondary",
              padx=6, pady=2).pack(side="left")
        self._pg_var = tk.StringVar(value="—")
        tk.Label(pg_row, textvariable=self._pg_var, bg=T.SURF, fg=T.TXT,
                 font=T.F(10), width=6, anchor="center").pack(side="left")
        T.Btn(pg_row, "▶", cmd=lambda: self._nav(1), style="secondary",
              padx=6, pady=2).pack(side="left")
        self._cur_pg = 0

        # Progress + run
        self.prog = ttk.Progressbar(body, mode="determinate")
        self.prog.pack(fill="x", pady=(0, 4))
        self.log = T.LogBox(body, height=3)
        self.log.pack(fill="x", pady=(0, 8))
        T.Btn(body, "◫   Extract Images", cmd=self._start,
              style="primary", font=T.F(12, True)).pack(side="right")

    def _load(self):
        paths = self.picker.get()
        if not paths:
            return
        try:
            if self._doc:
                self._doc.close()
            self._doc = fitz.open(paths[0])
            n = len(self._doc)
            self.src_info.config(text=f"{n} pages", fg=T.OK)
            self._cur_pg = 0
            self._show_preview(0)
        except Exception as e:
            T.popup(self, "Load Error", str(e), "error")

    def _pick_dir(self):
        d = filedialog.askdirectory(initialdir=self._out_dir.get())
        if d:
            self._out_dir.set(d)

    def _nav(self, d):
        if not self._doc:
            return
        self._cur_pg = max(0, min(len(self._doc) - 1, self._cur_pg + d))
        self._show_preview(self._cur_pg)

    def _show_preview(self, pg):
        if not self._doc or not PIL_OK:
            return
        try:
            import io
            from PIL import Image, ImageTk
            pix = self._doc[pg].get_pixmap(matrix=fitz.Matrix(1.0, 1.0))
            img = Image.open(io.BytesIO(pix.tobytes("ppm")))
            img.thumbnail((200, 270), Image.LANCZOS)
            self._photo = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self.canvas.create_image(100, 135, image=self._photo)
            self._pg_var.set(f"{pg+1}/{len(self._doc)}")
        except Exception:
            pass

    def _parse_pages(self, n):
        """Return list of 0-based page indices from the pages entry."""
        raw = self._pages_var.get().strip()
        if raw.lower() == "all":
            return list(range(n))
        pages = []
        for token in raw.split(","):
            token = token.strip()
            if "-" in token:
                a, b = token.split("-", 1)
                pages.extend(range(int(a)-1, int(b)))
            else:
                pages.append(int(token)-1)
        return sorted(set(p for p in pages if 0 <= p < n))

    def _start(self):
        if not self._doc:
            T.popup(self, "No file", "Load a PDF first.", "warning")
            return
        dpi     = int(self._dpi.get())
        fmt     = self._fmt.get().lower()
        out_dir = self._out_dir.get()
        stem    = os.path.splitext(os.path.basename(self.picker.get()[0]))[0]
        try:
            pages = self._parse_pages(len(self._doc))
        except Exception as e:
            T.popup(self, "Page range error", str(e), "error")
            return

        self.log.clear()
        self.log.append(f"Extracting {len(pages)} page(s) at {dpi} DPI as {fmt.upper()} …")
        self.prog["value"] = 0
        doc = self._doc

        def worker():
            try:
                mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
                for i, pg in enumerate(pages):
                    pix  = doc[pg].get_pixmap(matrix=mat)
                    name = f"{stem}_page{pg+1:04d}.{fmt}"
                    path = os.path.join(out_dir, name)
                    if fmt == "png":
                        pix.save(path)
                    else:
                        pix.pil_save(path, format="JPEG", quality=90)
                    self.prog["value"] = int((i+1)/len(pages)*100)
                    self.log.append(f"  ✓  {name}", T.OK)
                self.log.append(f"\nDone — {len(pages)} image(s) saved to {out_dir}", T.OK)
                T.toast(self, "Images extracted  ✓", "success")
            except Exception as e:
                self.log.append(f"ERROR: {e}", T.ERR)

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    Pdf2ImgApp().mainloop()
