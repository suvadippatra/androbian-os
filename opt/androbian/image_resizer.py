"""
image_resizer.py — Joydip's PDF Suite
Resize a photo to meet exam form upload criteria.
The user specifies maximum file size (KB), pixel dimensions, and aspect-ratio constraints.
The app finds the best quality/size balance automatically.
"""

import tkinter as tk
from tkinter import ttk, filedialog
import os, io, threading, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import theme as T

try:
    from PIL import Image, ImageTk
    PIL_OK = True
except ImportError:
    PIL_OK = False
    import subprocess
    subprocess.run(["pip", "install", "Pillow", "--break-system-packages"],
                   capture_output=True)


PRESETS = {
    "NEET / JEE Photo (200×230 px, <100 KB)"      : dict(w=200, h=230, max_kb=100,  fmt="JPEG"),
    "NEET / JEE Signature (140×60 px, <50 KB)"     : dict(w=140, h=60,  max_kb=50,   fmt="JPEG"),
    "SSC / UPSC Photo (3.5×4.5 cm @100dpi)"        : dict(w=138, h=177, max_kb=150,  fmt="JPEG"),
    "Passport Photo (35×45 mm @300dpi)"             : dict(w=413, h=531, max_kb=200,  fmt="JPEG"),
    "Custom …"                                      : None,
}


def auto_compress(img, target_w, target_h, max_kb, fmt="JPEG"):
    """
    Resize the image to target_w × target_h, then binary-search for the
    highest JPEG quality that keeps the file under max_kb kilobytes.
    Returns the final bytes buffer and the quality used.
    """
    resized = img.convert("RGB").resize((target_w, target_h), Image.LANCZOS)
    if fmt.upper() in ("PNG",):
        buf = io.BytesIO()
        resized.save(buf, format="PNG", optimize=True)
        return buf, None   # PNG quality not adjustable

    lo, hi, best_q, best_buf = 1, 95, 75, None
    while lo <= hi:
        mid = (lo + hi) // 2
        buf = io.BytesIO()
        resized.save(buf, format="JPEG", quality=mid, optimize=True)
        kb  = buf.tell() / 1024.0
        if kb <= max_kb:
            best_q, best_buf = mid, buf
            lo = mid + 1
        else:
            hi = mid - 1

    if best_buf is None:
        # Even quality=1 is too large — just save at quality=1
        best_buf = io.BytesIO()
        resized.save(best_buf, format="JPEG", quality=1, optimize=True)
        best_q = 1

    return best_buf, best_q


class ImageResizerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Exam Photo Resizer — Joydip's Suite")
        self.geometry("720x560")
        T.apply(self)
        self._centre()
        self._src_img = None
        self._photo   = None
        self._build()

    def _centre(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"720x560+{(sw-720)//2}+{(sh-560)//2}")

    def _build(self):
        T.app_header(self, "Exam Photo Resizer",
                     "Resize any photo to meet exam form upload criteria automatically", "⊡")
        body = tk.Frame(self, bg=T.BG, padx=20, pady=14)
        body.pack(fill="both", expand=True)

        mid = tk.Frame(body, bg=T.BG)
        mid.pack(fill="both", expand=True, pady=(0, 10))
        left  = tk.Frame(mid, bg=T.BG)
        right = T.Card(mid, width=200)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        # Source
        src_card = T.Card(left)
        src_card.pack(fill="x", pady=(0, 10))
        s_i = tk.Frame(src_card, bg=T.SURF, padx=12, pady=10)
        s_i.pack(fill="x")
        tk.Label(s_i, text="Source image:", bg=T.SURF, fg=T.MUT, font=T.F(10)
                 ).pack(anchor="w", pady=(0, 5))
        self.picker = T.FilePicker(
            s_i, bg=T.SURF,
            types=[("Images", "*.jpg *.jpeg *.png *.bmp *.tiff *.webp")])
        self.picker.pack(fill="x")
        T.Btn(s_i, "Load Image", cmd=self._load, style="secondary",
              font=T.F(10, True), padx=9, pady=4).pack(anchor="e", pady=(5, 0))
        self.src_info = tk.Label(s_i, text="", bg=T.SURF, fg=T.MUT, font=T.F(9))
        self.src_info.pack(anchor="w")

        # Preset
        preset_card = T.Card(left)
        preset_card.pack(fill="x", pady=(0, 10))
        p_i = tk.Frame(preset_card, bg=T.SURF, padx=12, pady=10)
        p_i.pack(fill="x")
        tk.Label(p_i, text="Exam preset:", bg=T.SURF, fg=T.MUT, font=T.F(10)
                 ).pack(anchor="w", pady=(0, 5))
        self._preset = tk.StringVar(value=list(PRESETS.keys())[0])
        cb = ttk.Combobox(p_i, textvariable=self._preset,
                          values=list(PRESETS.keys()), state="readonly", width=44)
        cb.pack(anchor="w")
        cb.bind("<<ComboboxSelected>>", self._on_preset)

        # Custom fields (shown only for "Custom …")
        self.custom_card = tk.Frame(p_i, bg=T.SURF)
        for lbl, var_name, default in [
            ("Width (px):",  "_cw",  "400"),
            ("Height (px):", "_ch",  "400"),
            ("Max size (KB):", "_ck", "200"),
        ]:
            row = tk.Frame(self.custom_card, bg=T.SURF)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=lbl, bg=T.SURF, fg=T.MUT, font=T.F(10),
                     width=16, anchor="w").pack(side="left")
            v = tk.StringVar(value=default)
            setattr(self, var_name, v)
            tk.Entry(row, textvariable=v, bg=T.SURF2, fg=T.TXT,
                     font=T.F(10), relief="flat", bd=0, width=10
                     ).pack(side="left", ipady=4)

        self._fmt_var = tk.StringVar(value="JPEG")
        fmt_row = tk.Frame(self.custom_card, bg=T.SURF)
        fmt_row.pack(fill="x", pady=2)
        tk.Label(fmt_row, text="Output format:", bg=T.SURF, fg=T.MUT,
                 font=T.F(10), width=16, anchor="w").pack(side="left")
        for f in ("JPEG", "PNG"):
            tk.Radiobutton(fmt_row, text=f, variable=self._fmt_var, value=f,
                           bg=T.SURF, fg=T.TXT, selectcolor=T.SURF2,
                           activebackground=T.SURF, font=T.F(10)
                           ).pack(side="left", padx=4)

        # Output
        out_card = T.Card(left)
        out_card.pack(fill="x", pady=(0, 8))
        out_i = tk.Frame(out_card, bg=T.SURF, padx=12, pady=8)
        out_i.pack(fill="x")
        tk.Label(out_i, text="Save as:", bg=T.SURF, fg=T.MUT, font=T.F(10)
                 ).pack(anchor="w", pady=(0, 4))
        self.out_row = T.OutputRow(out_i, "resized_photo.jpg", bg=T.SURF)
        self.out_row.pack(fill="x")

        # Preview panel
        tk.Label(right, text="Preview", bg=T.SURF, fg=T.MUT, font=T.F(10)).pack(pady=(8, 2))
        T.Divider(right).pack(fill="x")
        self.canvas = tk.Canvas(right, bg=T.SURF2, highlightthickness=0,
                                width=180, height=220)
        self.canvas.pack(pady=6, padx=6)
        self.prev_info = tk.Label(right, text="", bg=T.SURF, fg=T.MUT, font=T.F(9),
                                  wraplength=180, justify="center")
        self.prev_info.pack(padx=6)

        # Run
        self.log = T.LogBox(body, height=3)
        self.log.pack(fill="x", pady=(0, 8))
        T.Btn(body, "⊡   Resize Image", cmd=self._start,
              style="primary", font=T.F(12, True)).pack(side="right")

    def _on_preset(self, _=None):
        if self._preset.get() == "Custom …":
            self.custom_card.pack(fill="x", pady=(6, 0))
        else:
            self.custom_card.pack_forget()

    def _load(self):
        paths = self.picker.get()
        if not paths or not PIL_OK:
            return
        try:
            self._src_img = Image.open(paths[0])
            w, h = self._src_img.size
            kb = os.path.getsize(paths[0]) / 1024
            self.src_info.config(
                text=f"{w}×{h} px  |  {kb:.1f} KB  |  {self._src_img.format}", fg=T.OK)
            self._show_preview(self._src_img)
        except Exception as e:
            T.popup(self, "Load Error", str(e), "error")

    def _show_preview(self, img):
        if not PIL_OK:
            return
        thumb = img.copy()
        thumb.thumbnail((180, 220), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(thumb)
        self.canvas.delete("all")
        x = 180 // 2
        y = 220 // 2
        self.canvas.create_image(x, y, image=self._photo)
        self.prev_info.config(text=f"{img.size[0]}×{img.size[1]} px")

    def _get_params(self):
        key = self._preset.get()
        if key == "Custom …":
            return (int(self._cw.get()), int(self._ch.get()),
                    int(self._ck.get()), self._fmt_var.get())
        p = PRESETS[key]
        return p["w"], p["h"], p["max_kb"], p["fmt"]

    def _start(self):
        if self._src_img is None:
            T.popup(self, "No image", "Load an image first.", "warning")
            return
        try:
            tw, th, max_kb, fmt = self._get_params()
        except ValueError as e:
            T.popup(self, "Parameter error", str(e), "error")
            return

        out = self.out_row.get_path()
        if fmt.upper() == "JPEG" and not out.lower().endswith((".jpg", ".jpeg")):
            out = os.path.splitext(out)[0] + ".jpg"
        elif fmt.upper() == "PNG" and not out.lower().endswith(".png"):
            out = os.path.splitext(out)[0] + ".png"

        self.log.clear()
        img = self._src_img

        def worker():
            try:
                buf, quality = auto_compress(img, tw, th, max_kb, fmt)
                with open(out, "wb") as f:
                    f.write(buf.getvalue())
                final_kb = os.path.getsize(out) / 1024
                q_str = f"  JPEG quality: {quality}" if quality else ""
                self.log.append(
                    f"✓  Saved  {tw}×{th} px  |  {final_kb:.1f} KB{q_str}", T.OK)
                self.log.append(f"   Path: {out}", T.OK)
                # Show compressed preview
                result_img = Image.open(out)
                self._show_preview(result_img)
                T.toast(self, f"Resized to {final_kb:.1f} KB  ✓", "success")
            except Exception as e:
                self.log.append(f"ERROR: {e}", T.ERR)

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    ImageResizerApp().mainloop()
