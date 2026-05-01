"""
pdf_booklet.py — Joydip's PDF Suite
Re-order PDF pages for saddle-stitch booklet printing.
Supports multi-sheet signatures, configurable canvas sizes,
a physical cutoff zone (the "bleed trim" area), gap and margin controls.

How booklet ordering works (simple explanation):
  For a 4-page document printed on 1 sheet (2 sides, 2 pages per side):
    Sheet 1 front : page 4 | page 1
    Sheet 1 back  : page 2 | page 3
  The algorithm pads the source to the nearest multiple of (4 × sig_sheets),
  then interleaves outer-to-inner for each signature group.
"""

import tkinter as tk
from tkinter import ttk
import os, threading, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import theme as T

try:
    import fitz
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "pymupdf", "--break-system-packages"],
                   capture_output=True)
    import fitz

MM = 2.8346   # 1 mm in PDF points

CANVAS_SIZES = {
    "A4  (210×297 mm)"  : (210.0, 297.0),
    "A3  (297×420 mm)"  : (297.0, 420.0),
    "Legal (216×356 mm)": (216.0, 356.0),
    "Custom …"          : None,
}


# ─── Booklet algorithm ────────────────────────────────────────────────────────

def compute_booklet_order(n_pages, sig_sheets=1):
    """
    Return a list of (left_page_0based, right_page_0based) tuples for each
    physical half-sheet (spread), in print order. None means a blank page.

    sig_sheets: how many physical sheets per signature group (1–4).
    Pages are padded so that n_pages is a multiple of 4 × sig_sheets.
    """
    pages_per_sig = 4 * sig_sheets
    # Pad to nearest multiple
    padded = math.ceil(n_pages / pages_per_sig) * pages_per_sig
    order = list(range(n_pages)) + [None] * (padded - n_pages)

    spreads = []
    for sig_start in range(0, padded, pages_per_sig):
        sig = order[sig_start: sig_start + pages_per_sig]
        # For each sheet in the signature, outer pages fold around inner ones
        for sheet in range(sig_sheets):
            lo = sheet
            hi = pages_per_sig - 1 - sheet
            # Front side: right = sig[lo], left = sig[hi]  (when folded, lo is right)
            spreads.append((sig[hi], sig[lo]))    # front
            # Back side:  left = sig[lo+1], right = sig[hi-1]
            spreads.append((sig[lo + 1], sig[hi - 1]))  # back

    return spreads


def impose_booklet(input_path, output_path,
                   canvas_w_mm=210.0, canvas_h_mm=297.0,
                   cutoff_mm=10.0,
                   sig_sheets=1,
                   gap_mm=4.0, margin_mm=6.0):
    """
    Read input_path and produce a ready-to-print booklet PDF.
    Each output page is canvas_w × canvas_h, split into two cells,
    with the physical cutoff zone trimmed from the edges.
    """
    src = fitz.open(input_path)
    n   = len(src)
    spreads = compute_booklet_order(n, sig_sheets)

    # Effective canvas after cutoff on every side
    eff_w = (canvas_w_mm - 2 * cutoff_mm) * MM   # total width for two cells
    eff_h = (canvas_h_mm - 2 * cutoff_mm) * MM
    full_w = canvas_w_mm * MM
    full_h = canvas_h_mm * MM

    # Each cell occupies half the effective width minus half the gap
    cell_w = (eff_w - gap_mm * MM) / 2.0
    cell_h = eff_h - 2 * margin_mm * MM

    # Offsets from page origin (0,0)
    x_off = cutoff_mm * MM          # left edge of left cell
    y_off = cutoff_mm * MM + margin_mm * MM

    out = fitz.open()

    for left_idx, right_idx in spreads:
        page = out.new_page(width=full_w, height=full_h)

        # Left cell
        left_rect  = fitz.Rect(x_off,
                                y_off,
                                x_off + cell_w,
                                y_off + cell_h)
        # Right cell (gap between them)
        right_rect = fitz.Rect(x_off + cell_w + gap_mm * MM,
                                y_off,
                                x_off + cell_w * 2 + gap_mm * MM,
                                y_off + cell_h)

        if left_idx is not None and left_idx < n:
            page.show_pdf_page(left_rect, src, left_idx)
        if right_idx is not None and right_idx < n:
            page.show_pdf_page(right_rect, src, right_idx)

    out.save(output_path, garbage=4, deflate=True)
    src.close()
    out.close()


class BookletApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF Booklet — Joydip's Suite")
        self.geometry("780x640")
        self.minsize(640, 480)
        T.apply(self)
        self._centre()
        self._build()

    def _centre(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"780x640+{(sw-780)//2}+{(sh-640)//2}")

    # ─── UI ───────────────────────────────────────────────────────────────────
    def _build(self):
        T.app_header(self, "PDF Booklet Imposition",
                     "Re-order pages for saddle-stitch booklet printing", "⊟")

        body = tk.Frame(self, bg=T.BG, padx=20, pady=14)
        body.pack(fill="both", expand=True)

        # ── Source file ──
        src_card = T.Card(body)
        src_card.pack(fill="x", pady=(0, 10))
        src_i = tk.Frame(src_card, bg=T.SURF, padx=12, pady=10)
        src_i.pack(fill="x")
        tk.Label(src_i, text="Source PDF:", bg=T.SURF, fg=T.MUT, font=T.F(10)
                 ).pack(anchor="w", pady=(0, 5))
        self.picker = T.FilePicker(src_i, bg=T.SURF)
        self.picker.pack(fill="x")
        self.src_info = tk.Label(src_i, text="", bg=T.SURF, fg=T.MUT, font=T.F(9))
        self.src_info.pack(anchor="w", pady=(3, 0))
        T.Btn(src_i, "Load & Preview Order", cmd=self._preview,
              style="secondary", font=T.F(10, True), padx=9, pady=4
              ).pack(anchor="e", pady=(5, 0))

        # ── Canvas & cutoff ──
        canvas_card = T.Card(body)
        canvas_card.pack(fill="x", pady=(0, 10))
        cv_i = tk.Frame(canvas_card, bg=T.SURF, padx=12, pady=10)
        cv_i.pack(fill="x")

        row_top = tk.Frame(cv_i, bg=T.SURF)
        row_top.pack(fill="x", pady=(0, 6))
        tk.Label(row_top, text="Canvas size:", bg=T.SURF, fg=T.MUT, font=T.F(10),
                 width=14, anchor="w").pack(side="left")
        self.canvas_var = tk.StringVar(value="A4  (210×297 mm)")
        cb = ttk.Combobox(row_top, textvariable=self.canvas_var,
                          values=list(CANVAS_SIZES.keys()), state="readonly", width=22)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", self._on_canvas_change)

        # Custom mm row
        self.custom_row = tk.Frame(cv_i, bg=T.SURF)
        tk.Label(self.custom_row, text="W (mm):", bg=T.SURF, fg=T.MUT, font=T.F(9)
                 ).pack(side="left")
        self._cw = tk.StringVar(value="210")
        tk.Entry(self.custom_row, textvariable=self._cw, bg=T.SURF2, fg=T.TXT,
                 font=T.F(10), relief="flat", bd=0, width=6
                 ).pack(side="left", ipady=4, padx=(2, 8))
        tk.Label(self.custom_row, text="H (mm):", bg=T.SURF, fg=T.MUT, font=T.F(9)
                 ).pack(side="left")
        self._ch = tk.StringVar(value="297")
        tk.Entry(self.custom_row, textvariable=self._ch, bg=T.SURF2, fg=T.TXT,
                 font=T.F(10), relief="flat", bd=0, width=6
                 ).pack(side="left", ipady=4)

        # Cutoff
        co_row = tk.Frame(cv_i, bg=T.SURF)
        co_row.pack(fill="x", pady=(4, 0))
        self.cutoff_s = T.Slider(co_row, "Cutoff zone (each side)",
                                  0, 30, 10, fmt="{:.0f}", suffix=" mm",
                                  bg=T.SURF, resolution=1)
        self.cutoff_s.pack(fill="x")
        tk.Label(cv_i,
                 text="The cutoff zone trims the physical edge of each canvas side "
                      "(default 10 mm → effective A4 canvas is 190×277 mm).",
                 bg=T.SURF, fg=T.DIM, font=T.F(9), wraplength=640
                 ).pack(anchor="w", pady=(3, 0))

        # ── Signature & spacing ──
        sig_card = T.Card(body)
        sig_card.pack(fill="x", pady=(0, 10))
        sig_i = tk.Frame(sig_card, bg=T.SURF, padx=12, pady=10)
        sig_i.pack(fill="x")

        sig_row = tk.Frame(sig_i, bg=T.SURF)
        sig_row.pack(fill="x", pady=(0, 6))
        tk.Label(sig_row, text="Sheets per signature:", bg=T.SURF, fg=T.MUT,
                 font=T.F(10), width=22, anchor="w").pack(side="left")
        self._sig = tk.IntVar(value=1)
        for v in (1, 2, 3, 4):
            tk.Radiobutton(sig_row, text=str(v), variable=self._sig, value=v,
                           bg=T.SURF, fg=T.TXT, selectcolor=T.SURF2,
                           activebackground=T.SURF, font=T.F(10)
                           ).pack(side="left", padx=8)

        self.gap_s    = T.Slider(sig_i, "Gap between pages (mm)",  0, 20, 4,
                                  fmt="{:.0f}", suffix=" mm", bg=T.SURF, resolution=1)
        self.margin_s = T.Slider(sig_i, "Top/bottom margin (mm)",  0, 30, 6,
                                  fmt="{:.0f}", suffix=" mm", bg=T.SURF, resolution=1)
        self.gap_s.pack(fill="x", pady=2)
        self.margin_s.pack(fill="x", pady=2)

        # ── Spread preview list ──
        prev_card = T.Card(body)
        prev_card.pack(fill="x", pady=(0, 10))
        prev_i = tk.Frame(prev_card, bg=T.SURF, padx=12, pady=8)
        prev_i.pack(fill="x")
        tk.Label(prev_i, text="Spread order preview (front then back of each sheet):",
                 bg=T.SURF, fg=T.MUT, font=T.F(10)).pack(anchor="w", pady=(0, 4))
        sb = tk.Scrollbar(prev_i, bg=T.BDR, relief="flat", bd=0)
        self.prev_lb = tk.Listbox(
            prev_i, bg=T.SURF2, fg=T.TXT, font=T.FM(9),
            selectbackground=T.ADIM, relief="flat", bd=0,
            yscrollcommand=sb.set, height=4, activestyle="none")
        sb.config(command=self.prev_lb.yview)
        sb.pack(side="right", fill="y")
        self.prev_lb.pack(fill="x")

        # ── Output ──
        out_card = T.Card(body)
        out_card.pack(fill="x", pady=(0, 8))
        out_i = tk.Frame(out_card, bg=T.SURF, padx=12, pady=8)
        out_i.pack(fill="x")
        tk.Label(out_i, text="Output:", bg=T.SURF, fg=T.MUT, font=T.F(10)
                 ).pack(anchor="w", pady=(0, 4))
        self.out_row = T.OutputRow(out_i, "booklet_output.pdf", bg=T.SURF)
        self.out_row.pack(fill="x")

        # ── Progress + run ──
        self.prog = ttk.Progressbar(body, mode="indeterminate")
        self.prog.pack(fill="x", pady=(0, 4))
        self.log = T.LogBox(body, height=3)
        self.log.pack(fill="x", pady=(0, 8))

        T.Btn(body, "⊟   Create Booklet PDF", cmd=self._start,
              style="primary", font=T.F(12, True)).pack(side="right")

    def _on_canvas_change(self, _=None):
        if self.canvas_var.get() == "Custom …":
            self.custom_row.pack(fill="x", pady=4)
        else:
            self.custom_row.pack_forget()

    def _get_canvas(self):
        key = self.canvas_var.get()
        if key == "Custom …":
            try:
                return float(self._cw.get()), float(self._ch.get())
            except ValueError:
                raise ValueError("Invalid custom canvas dimensions.")
        return CANVAS_SIZES[key]

    # ─── Preview ──────────────────────────────────────────────────────────────
    def _preview(self):
        paths = self.picker.get()
        if not paths:
            T.popup(self, "No file", "Browse and select a PDF first.", "warning")
            return
        try:
            doc = fitz.open(paths[0])
            n = len(doc)
            doc.close()
            self.src_info.config(
                text=f"Loaded: {os.path.basename(paths[0])}  |  {n} pages", fg=T.OK)
        except Exception as e:
            T.popup(self, "Load Error", str(e), "error")
            return

        sig = self._sig.get()
        spreads = compute_booklet_order(n, sig)
        self.prev_lb.delete(0, "end")
        for i, (l, r) in enumerate(spreads):
            side  = "Front" if i % 2 == 0 else "Back "
            sheet = i // 2 + 1
            l_lbl = f"p{l+1}" if l is not None else "blank"
            r_lbl = f"p{r+1}" if r is not None else "blank"
            self.prev_lb.insert(
                "end", f"  Sheet {sheet:02d} {side}:  Left={l_lbl:>6}  |  Right={r_lbl}")
        padded = len(spreads) * 2
        self.log.clear()
        self.log.append(
            f"{n} source pages → {len(spreads)} spreads "
            f"({len(spreads)//2} physical sheet(s)).  "
            f"{padded - n} blank padding page(s) added.", T.OK)

    # ─── Impose ───────────────────────────────────────────────────────────────
    def _start(self):
        paths = self.picker.get()
        if not paths:
            T.popup(self, "No file", "Browse and select a PDF first.", "warning")
            return
        try:
            cw, ch = self._get_canvas()
        except ValueError as e:
            T.popup(self, "Canvas Error", str(e), "error")
            return

        inp    = paths[0]
        out    = self.out_row.get_path()
        cutoff = self.cutoff_s.get()
        sig    = self._sig.get()
        gap    = self.gap_s.get()
        margin = self.margin_s.get()

        self.log.clear()
        self.log.append(f"Imposing booklet — canvas {cw:.0f}×{ch:.0f} mm, "
                         f"cutoff {cutoff:.0f} mm, sig {sig} sheet(s) …")
        self.prog.start(10)

        def worker():
            try:
                impose_booklet(inp, out, cw, ch, cutoff, sig, gap, margin)
                self.prog.stop()
                self.prog["value"] = 100
                self.log.append(f"✓  Saved to: {out}", T.OK)
                T.toast(self, "Booklet PDF created  ✓", "success")
            except Exception as e:
                self.prog.stop()
                self.log.append(f"ERROR: {e}", T.ERR)
                T.popup(self, "Booklet Failed", str(e), "error")

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    BookletApp().mainloop()
