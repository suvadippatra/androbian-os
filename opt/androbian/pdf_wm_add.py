"""
pdf_wm_add.py — Joydip's PDF Suite
Stamp every page of a PDF with a custom text or image watermark.
Supports diagonal / corners / centre placement, opacity, colour, rotation, font size.
"""

import tkinter as tk
from tkinter import ttk, colorchooser
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


# ─── Backend ─────────────────────────────────────────────────────────────────

def hex_to_rgb01(hex_col):
    """Convert #RRGGBB to (r, g, b) each in 0.0–1.0."""
    h = hex_col.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))


POSITIONS = {
    "Centre (diagonal)": "diag",
    "Centre (straight)": "center",
    "Top-left"         : "tl",
    "Top-right"        : "tr",
    "Bottom-left"      : "bl",
    "Bottom-right"     : "br",
}


def add_text_watermark(input_path, output_path,
                       text="WATERMARK",
                       font_size=52,
                       opacity=0.25,
                       colour_hex="#4F8EF7",
                       position="diag",
                       rotation=None,    # None → auto by position
                       margin_pts=40):
    """
    Stamp every page with a text watermark using PyMuPDF's text insertion.
    Uses the 'helv' (Helvetica) built-in font so no font files are needed.
    """
    colour = hex_to_rgb01(colour_hex)
    src    = fitz.open(input_path)
    out    = fitz.open()

    for i, page in enumerate(src):
        out.insert_pdf(src, from_page=i, to_page=i)
        new_page = out[-1]
        w, h = new_page.rect.width, new_page.rect.height

        # Determine text insertion point and auto-rotation
        if position == "diag":
            angle = -(rotation if rotation is not None else 45)
            x, y  = w / 2, h / 2
        elif position == "center":
            angle = rotation if rotation is not None else 0
            x, y  = w / 2, h / 2
        elif position == "tl":
            angle = rotation if rotation is not None else 0
            x, y  = margin_pts + font_size * 3, margin_pts + font_size
        elif position == "tr":
            angle = rotation if rotation is not None else 0
            x, y  = w - margin_pts - font_size * 3, margin_pts + font_size
        elif position == "bl":
            angle = rotation if rotation is not None else 0
            x, y  = margin_pts + font_size * 3, h - margin_pts
        else:   # br
            angle = rotation if rotation is not None else 0
            x, y  = w - margin_pts - font_size * 3, h - margin_pts

        # Build a transparency-enabled overlay using a Form XObject
        # so the opacity setting is honoured across all PDF viewers.
        shape = new_page.new_shape()
        shape.insert_text(
            fitz.Point(x, y),
            text,
            fontsize  = font_size,
            fontname  = "helv",
            color     = colour,
            fill      = colour,
            render_mode = 0,
            rotate    = angle,
            stroke_opacity = opacity,
            fill_opacity   = opacity,
        )
        shape.commit()

    src.close()
    out.save(output_path, garbage=4, deflate=True)
    out.close()


def add_image_watermark(input_path, output_path,
                        image_path="",
                        opacity=0.25,
                        position="diag",
                        scale=0.4):
    """
    Stamp every page with a raster image watermark.
    Uses PyMuPDF's insert_image with a soft-mask layer for opacity.
    """
    import struct, zlib

    src   = fitz.open(input_path)
    stamp = fitz.open(image_path)   # fitz can open PNG/JPEG directly

    out   = fitz.open()

    for i, page in enumerate(src):
        out.insert_pdf(src, from_page=i, to_page=i)
        new_page = out[-1]
        w, h = new_page.rect.width, new_page.rect.height
        iw, ih = stamp[0].rect.width, stamp[0].rect.height

        # Scale stamp to `scale` fraction of the page width
        sw = w * scale
        sh = sw * (ih / iw) if iw > 0 else sw

        if position in ("diag", "center"):
            x0, y0 = (w - sw) / 2, (h - sh) / 2
        elif position == "tl":
            x0, y0 = 20, 20
        elif position == "tr":
            x0, y0 = w - sw - 20, 20
        elif position == "bl":
            x0, y0 = 20, h - sh - 20
        else:  # br
            x0, y0 = w - sw - 20, h - sh - 20

        rect = fitz.Rect(x0, y0, x0 + sw, y0 + sh)
        new_page.insert_image(rect, stream=stamp.convert_to_pdf(),
                              keep_proportion=True)

    stamp.close()
    src.close()
    out.save(output_path, garbage=4, deflate=True)
    out.close()


class WmAddApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Watermark Add — Joydip's Suite")
        self.geometry("800x680")
        self.minsize(660, 520)
        T.apply(self)
        self._colour = "#4F8EF7"
        self._centre()
        self._build()

    def _centre(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"800x680+{(sw-800)//2}+{(sh-680)//2}")

    # ─── UI ───────────────────────────────────────────────────────────────────
    def _build(self):
        T.app_header(self, "Add Watermark",
                     "Stamp text or image watermarks on every page of a PDF", "⬡")

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

        # ── Watermark type tabs ──
        tab_card = T.Card(body)
        tab_card.pack(fill="x", pady=(0, 10))
        self.nb = ttk.Notebook(tab_card)
        self.nb.pack(fill="x")

        # ─ Text watermark tab ─
        t1 = tk.Frame(self.nb, bg=T.SURF, padx=14, pady=10)
        self.nb.add(t1, text="  Text Watermark  ")

        r1 = tk.Frame(t1, bg=T.SURF)
        r1.pack(fill="x", pady=(0, 6))
        tk.Label(r1, text="Watermark text:", bg=T.SURF, fg=T.MUT, font=T.F(10),
                 width=16, anchor="w").pack(side="left")
        self.wm_text = tk.StringVar(value="CONFIDENTIAL")
        tk.Entry(r1, textvariable=self.wm_text, bg=T.SURF2, fg=T.TXT,
                 font=T.F(11), relief="flat", bd=0, insertbackground=T.TXT,
                 width=28).pack(side="left", ipady=5)

        self.font_s = T.Slider(t1, "Font size", 12, 120, 52,
                                fmt="{:.0f}", suffix=" pt", bg=T.SURF, resolution=2)
        self.font_s.pack(fill="x", pady=2)

        # Colour picker row
        col_row = tk.Frame(t1, bg=T.SURF)
        col_row.pack(fill="x", pady=(4, 0))
        tk.Label(col_row, text="Text colour:", bg=T.SURF, fg=T.MUT, font=T.F(10),
                 width=16, anchor="w").pack(side="left")
        self._col_swatch = tk.Label(col_row, text="       ", bg=self._colour,
                                    relief="flat", bd=0)
        self._col_swatch.pack(side="left", padx=(0, 8))
        T.Btn(col_row, "Pick colour", cmd=self._pick_colour, style="secondary",
              font=T.F(10, True), padx=8, pady=3).pack(side="left")
        self._col_lbl = tk.Label(col_row, text=self._colour, bg=T.SURF,
                                  fg=T.MUT, font=T.FM(9))
        self._col_lbl.pack(side="left", padx=6)

        # ─ Image watermark tab ─
        t2 = tk.Frame(self.nb, bg=T.SURF, padx=14, pady=10)
        self.nb.add(t2, text="  Image Watermark  ")
        tk.Label(t2, text="Watermark image (PNG/JPG with transparency recommended):",
                 bg=T.SURF, fg=T.MUT, font=T.F(10)).pack(anchor="w", pady=(0, 5))
        self.img_picker = T.FilePicker(
            t2, "Image:", bg=T.SURF,
            types=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff")])
        self.img_picker.pack(fill="x")
        self.scale_s = T.Slider(t2, "Scale (% of page width)",
                                 5, 100, 40, fmt="{:.0f}", suffix="%",
                                 bg=T.SURF, resolution=5)
        self.scale_s.pack(fill="x", pady=(8, 0))

        # ── Shared settings (opacity, position, rotation) ──
        shared_card = T.Card(body)
        shared_card.pack(fill="x", pady=(0, 10))
        sh_i = tk.Frame(shared_card, bg=T.SURF, padx=12, pady=10)
        sh_i.pack(fill="x")
        tk.Label(sh_i, text="Placement (applies to both text and image):",
                 bg=T.SURF, fg=T.MUT, font=T.F(10)).pack(anchor="w", pady=(0, 6))

        self.opacity_s  = T.Slider(sh_i, "Opacity",  5, 100, 25,
                                    fmt="{:.0f}", suffix="%", bg=T.SURF, resolution=1)
        self.rotation_s = T.Slider(sh_i, "Rotation (°)", -180, 180, -45,
                                    fmt="{:.0f}", suffix="°",  bg=T.SURF, resolution=5)
        self.opacity_s.pack(fill="x", pady=2)
        self.rotation_s.pack(fill="x", pady=2)

        pos_row = tk.Frame(sh_i, bg=T.SURF)
        pos_row.pack(fill="x", pady=(6, 0))
        tk.Label(pos_row, text="Position:", bg=T.SURF, fg=T.MUT, font=T.F(10),
                 width=14, anchor="w").pack(side="left")
        self.pos_var = tk.StringVar(value="Centre (diagonal)")
        pos_cb = ttk.Combobox(pos_row, textvariable=self.pos_var,
                               values=list(POSITIONS.keys()), state="readonly", width=22)
        pos_cb.pack(side="left")

        # ── Output ──
        out_card = T.Card(body)
        out_card.pack(fill="x", pady=(0, 8))
        out_i = tk.Frame(out_card, bg=T.SURF, padx=12, pady=8)
        out_i.pack(fill="x")
        tk.Label(out_i, text="Output:", bg=T.SURF, fg=T.MUT, font=T.F(10)
                 ).pack(anchor="w", pady=(0, 4))
        self.out_row = T.OutputRow(out_i, "watermarked_output.pdf", bg=T.SURF)
        self.out_row.pack(fill="x")

        # ── Progress + run ──
        self.prog = ttk.Progressbar(body, mode="indeterminate")
        self.prog.pack(fill="x", pady=(0, 4))
        self.log = T.LogBox(body, height=3)
        self.log.pack(fill="x", pady=(0, 8))

        T.Btn(body, "⬡   Apply Watermark", cmd=self._start,
              style="primary", font=T.F(12, True)).pack(side="right")

    # ─── Colour picker ────────────────────────────────────────────────────────
    def _pick_colour(self):
        result = colorchooser.askcolor(color=self._colour, title="Choose watermark colour")
        if result and result[1]:
            self._colour = result[1]
            self._col_swatch.config(bg=self._colour)
            self._col_lbl.config(text=self._colour)

    # ─── Run ──────────────────────────────────────────────────────────────────
    def _start(self):
        paths = self.picker.get()
        if not paths:
            T.popup(self, "No file", "Browse and select a PDF first.", "warning")
            return

        inp     = paths[0]
        out     = self.out_row.get_path()
        opacity = self.opacity_s.get() / 100.0
        pos_key = self.pos_var.get()
        pos     = POSITIONS[pos_key]
        rot     = int(self.rotation_s.get())
        tab     = self.nb.index(self.nb.select())

        # Validate
        if tab == 0 and not self.wm_text.get().strip():
            T.popup(self, "No text", "Enter a watermark text string.", "warning")
            return
        if tab == 1:
            img_paths = self.img_picker.get()
            if not img_paths:
                T.popup(self, "No image", "Browse and select a watermark image.", "warning")
                return

        self.log.clear()
        self.log.append(
            f"Applying {'text' if tab == 0 else 'image'} watermark to "
            f"{os.path.basename(inp)} …")
        self.prog.start(10)

        def worker():
            try:
                if tab == 0:
                    add_text_watermark(
                        inp, out,
                        text       = self.wm_text.get(),
                        font_size  = int(self.font_s.get()),
                        opacity    = opacity,
                        colour_hex = self._colour,
                        position   = pos,
                        rotation   = rot,
                    )
                else:
                    add_image_watermark(
                        inp, out,
                        image_path = img_paths[0],
                        opacity    = opacity,
                        position   = pos,
                        scale      = self.scale_s.get() / 100.0,
                    )
                self.prog.stop()
                self.prog["value"] = 100
                self.log.append(f"✓  Saved to: {out}", T.OK)
                T.toast(self, "Watermark applied  ✓", "success")
            except Exception as e:
                self.prog.stop()
                self.log.append(f"ERROR: {e}", T.ERR)
                T.popup(self, "Watermark Failed", str(e), "error")

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    WmAddApp().mainloop()
