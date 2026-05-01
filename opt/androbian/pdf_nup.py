"""
pdf_nup.py — Joydip's PDF Suite
Arrange multiple source pages onto each output sheet (N-up imposition).
Supports 1×1 through 4×4 layouts, custom spacing, A4/A3/Letter/custom sizes.
"""

import tkinter as tk
from tkinter import ttk
import os, threading, io, sys
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

# Standard page sizes in points (1 pt = 1/72 inch; 1mm ≈ 2.8346 pt)
PAGE_SIZES = {
    "A4  (210×297 mm)":  (595.28,  841.89),
    "A3  (297×420 mm)":  (841.89, 1190.55),
    "A5  (148×210 mm)":  (419.53,  595.28),
    "Letter (216×279 mm)": (612.0,  792.0),
    "Legal  (216×356 mm)": (612.0, 1008.0),
    "Custom …":          None,
}
MM = 2.8346   # points per mm


# ─── Core imposition algorithm ────────────────────────────────────────────────
def impose_nup(input_path, output_path, rows, cols,
               page_size_pts=(595.28, 841.89),
               spacing_mm=4.0, margin_mm=8.0):
    """
    Lay out 'rows × cols' source pages per output sheet.
    Handles partial last sheets gracefully (empty cells stay blank).
    """
    sp = spacing_mm * MM
    mg = margin_mm  * MM
    ow, oh = page_size_pts

    cell_w = (ow - 2 * mg - (cols - 1) * sp) / cols
    cell_h = (oh - 2 * mg - (rows - 1) * sp) / rows

    src = fitz.open(input_path)
    out = fitz.open()
    n   = len(src)
    per = rows * cols

    for sheet_idx in range(-(-n // per)):   # ceiling division
        out_page = out.new_page(width=ow, height=oh)
        for cell in range(per):
            src_idx = sheet_idx * per + cell
            if src_idx >= n:
                break
            r = cell // cols
            c = cell  % cols
            x0 = mg + c * (cell_w + sp)
            y0 = mg + r * (cell_h + sp)
            rect = fitz.Rect(x0, y0, x0 + cell_w, y0 + cell_h)
            out_page.show_pdf_page(rect, src, src_idx)

    out.save(output_path, garbage=4, deflate=True)
    src.close()
    out.close()


class NupApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF N-up — Joydip's Suite")
        self.geometry("820x680")
        self.minsize(660, 520)
        T.apply(self)
        self._centre()
        self._preview_job = None
        self._build()

    def _centre(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"820x680+{(sw-820)//2}+{(sh-680)//2}")

    # ─── UI ───────────────────────────────────────────────────────────────────
    def _build(self):
        T.app_header(self, "PDF N-up",
                     "Arrange multiple pages per sheet — rows × columns", "⊞")

        # Two-column layout: controls left, preview right
        main = tk.Frame(self, bg=T.BG, padx=20, pady=14)
        main.pack(fill="both", expand=True)

        left  = tk.Frame(main, bg=T.BG)
        right = tk.Frame(main, bg=T.BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        right.pack(side="right", fill="both")

        # ── Source file ──
        src_card = T.Card(left)
        src_card.pack(fill="x", pady=(0, 10))
        src_i = tk.Frame(src_card, bg=T.SURF, padx=12, pady=10)
        src_i.pack(fill="x")
        tk.Label(src_i, text="Source PDF:", bg=T.SURF, fg=T.MUT, font=T.F(10)
                 ).pack(anchor="w", pady=(0, 5))
        self.picker = T.FilePicker(src_i, bg=T.SURF)
        self.picker.pack(fill="x")
        self.src_info = tk.Label(src_i, text="", bg=T.SURF, fg=T.MUT, font=T.F(9))
        self.src_info.pack(anchor="w", pady=(3, 0))

        # ── Layout controls ──
        ctrl_card = T.Card(left)
        ctrl_card.pack(fill="x", pady=(0, 10))
        ctrl_i = tk.Frame(ctrl_card, bg=T.SURF, padx=12, pady=10)
        ctrl_i.pack(fill="x")

        tk.Label(ctrl_i, text="Layout:", bg=T.SURF, fg=T.MUT, font=T.F(10)
                 ).pack(anchor="w", pady=(0, 4))
        self.rows_s = T.Slider(ctrl_i, "Rows",    1, 4, 2, bg=T.SURF, resolution=1)
        self.cols_s = T.Slider(ctrl_i, "Columns", 1, 4, 2, bg=T.SURF, resolution=1)
        self.rows_s.pack(fill="x", pady=2)
        self.cols_s.pack(fill="x", pady=2)

        T.Divider(ctrl_i).pack(fill="x", pady=8)
        tk.Label(ctrl_i, text="Spacing:", bg=T.SURF, fg=T.MUT, font=T.F(10)
                 ).pack(anchor="w", pady=(0, 4))
        self.sp_s  = T.Slider(ctrl_i, "Between pages (mm)", 0, 30, 4,
                               fmt="{:.0f}", suffix=" mm", bg=T.SURF, resolution=1)
        self.mg_s  = T.Slider(ctrl_i, "Page margin  (mm)",  0, 30, 8,
                               fmt="{:.0f}", suffix=" mm", bg=T.SURF, resolution=1)
        self.sp_s.pack(fill="x", pady=2)
        self.mg_s.pack(fill="x", pady=2)

        T.Divider(ctrl_i).pack(fill="x", pady=8)
        tk.Label(ctrl_i, text="Output page size:", bg=T.SURF, fg=T.MUT,
                 font=T.F(10)).pack(anchor="w", pady=(0, 4))
        self.size_var = tk.StringVar(value="A4  (210×297 mm)")
        cb = ttk.Combobox(ctrl_i, textvariable=self.size_var,
                          values=list(PAGE_SIZES.keys()), state="readonly")
        cb.pack(fill="x", pady=(0, 4))
        cb.bind("<<ComboboxSelected>>", self._on_size_change)

        # Custom size row (hidden unless "Custom …" selected)
        self.custom_row = tk.Frame(ctrl_i, bg=T.SURF)
        tk.Label(self.custom_row, text="W mm:", bg=T.SURF, fg=T.MUT, font=T.F(9)
                 ).pack(side="left")
        self._cw = tk.StringVar(value="210")
        tk.Entry(self.custom_row, textvariable=self._cw, bg=T.SURF2, fg=T.TXT,
                 font=T.F(10), relief="flat", bd=0, width=6).pack(side="left", ipady=4)
        tk.Label(self.custom_row, text=" H mm:", bg=T.SURF, fg=T.MUT, font=T.F(9)
                 ).pack(side="left")
        self._ch = tk.StringVar(value="297")
        tk.Entry(self.custom_row, textvariable=self._ch, bg=T.SURF2, fg=T.TXT,
                 font=T.F(10), relief="flat", bd=0, width=6).pack(side="left", ipady=4)

        # ── Output ──
        out_card = T.Card(left)
        out_card.pack(fill="x", pady=(0, 10))
        out_i = tk.Frame(out_card, bg=T.SURF, padx=12, pady=8)
        out_i.pack(fill="x")
        tk.Label(out_i, text="Output:", bg=T.SURF, fg=T.MUT, font=T.F(10)
                 ).pack(anchor="w", pady=(0, 4))
        self.out_row = T.OutputRow(out_i, "nup_output.pdf", bg=T.SURF)
        self.out_row.pack(fill="x")

        # ── Progress + log ──
        self.prog = ttk.Progressbar(left, mode="indeterminate")
        self.prog.pack(fill="x", pady=(0, 4))
        self.log = T.LogBox(left, height=3)
        self.log.pack(fill="x", pady=(0, 8))

        # Action buttons
        btn_row = tk.Frame(left, bg=T.BG)
        btn_row.pack(fill="x")
        T.Btn(btn_row, "Preview Page", cmd=self._show_preview,
              style="secondary", font=T.F(10, True)).pack(side="left")
        T.Btn(btn_row, "⊞   Create N-up PDF", cmd=self._start,
              style="primary", font=T.F(12, True)).pack(side="right")

        # ── Preview panel (right) ──
        prev_card = T.Card(right, width=260)
        prev_card.pack(fill="both", expand=True)
        prev_card.pack_propagate(False)
        tk.Label(prev_card, text="Preview", bg=T.SURF, fg=T.MUT,
                 font=T.F(10)).pack(pady=(8, 4))
        T.Divider(prev_card).pack(fill="x")
        self.canvas = tk.Canvas(prev_card, bg=T.SURF2, highlightthickness=0,
                                width=240, height=320)
        self.canvas.pack(pady=10, padx=10)
        self.prev_lbl = tk.Label(prev_card, text="Load a PDF and click\n'Preview Page'",
                                 bg=T.SURF, fg=T.DIM, font=T.F(9), justify="center")
        self.prev_lbl.pack()

        # Slider change callbacks for live preview info
        for s in (self.rows_s, self.cols_s, self.sp_s, self.mg_s):
            s.var.trace_add("write", lambda *_: self._update_info())

    def _on_size_change(self, event=None):
        if self.size_var.get() == "Custom …":
            self.custom_row.pack(fill="x", pady=4)
        else:
            self.custom_row.pack_forget()

    def _get_page_size(self):
        key = self.size_var.get()
        if key == "Custom …":
            try:
                w = float(self._cw.get()) * MM
                h = float(self._ch.get()) * MM
                return (w, h)
            except ValueError:
                raise ValueError("Invalid custom page dimensions.")
        return PAGE_SIZES[key]

    def _update_info(self):
        r = int(self.rows_s.get())
        c = int(self.cols_s.get())
        self.log.clear()
        self.log.append(f"Layout: {r}×{c} = {r*c} source pages per output sheet.")

    # ─── Preview ──────────────────────────────────────────────────────────────
    def _show_preview(self):
        if not PIL_OK:
            self.prev_lbl.config(text="Pillow not installed.\nRun: pip install Pillow")
            return
        paths = self.picker.get()
        if not paths:
            T.popup(self, "No file", "Browse and select a PDF first.", "warning")
            return
        try:
            src = fitz.open(paths[0])
            n = len(src)
            self.src_info.config(text=f"{n} pages", fg=T.OK)
            # Render page 0 at modest zoom for the canvas
            pix  = src[0].get_pixmap(matrix=fitz.Matrix(1.2, 1.2))
            img  = Image.open(io.BytesIO(pix.tobytes("ppm")))
            # Scale to fit canvas 240×320
            img.thumbnail((240, 320), Image.LANCZOS)
            self._photo = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self.canvas.create_image(120, 160, image=self._photo)
            self.prev_lbl.config(
                text=f"Showing page 1 of {n}.\nEach output sheet will hold "
                     f"{int(self.rows_s.get())}×{int(self.cols_s.get())} pages.")
            src.close()
        except Exception as e:
            self.prev_lbl.config(text=f"Preview error:\n{e}")

    # ─── Imposition ───────────────────────────────────────────────────────────
    def _start(self):
        paths = self.picker.get()
        if not paths:
            T.popup(self, "No file", "Browse and select a PDF first.", "warning")
            return
        try:
            page_size = self._get_page_size()
        except ValueError as e:
            T.popup(self, "Size Error", str(e), "error")
            return

        rows   = int(self.rows_s.get())
        cols   = int(self.cols_s.get())
        sp_mm  = self.sp_s.get()
        mg_mm  = self.mg_s.get()
        inp    = paths[0]
        out    = self.out_row.get_path()

        self.log.clear()
        self.log.append(
            f"Imposing {rows}×{cols} N-up on {os.path.basename(inp)} …")
        self.prog.start(10)

        def worker():
            try:
                impose_nup(inp, out, rows, cols, page_size, sp_mm, mg_mm)
                self.prog.stop()
                self.prog["value"] = 100
                src = fitz.open(inp)
                n_src = len(src)
                src.close()
                out_doc = fitz.open(out)
                n_out = len(out_doc)
                out_doc.close()
                self.log.append(
                    f"✓  Done!  {n_src} source pages → {n_out} output sheets.", T.OK)
                self.log.append(f"   Saved to: {out}", T.OK)
                T.toast(self, "N-up PDF created  ✓", "success")
            except Exception as e:
                self.prog.stop()
                self.log.append(f"ERROR: {e}", T.ERR)
                T.popup(self, "N-up Failed", str(e), "error")

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    NupApp().mainloop()
