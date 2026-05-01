#!/usr/bin/env python3
"""
launcher.py — AndrobianOS
The central hub dashboard. All apps launched from here.
"""
import tkinter as tk
from tkinter import ttk
import os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import theme as T

APPS_DIR = os.path.dirname(os.path.abspath(__file__))

SECTIONS = [
    {
        "title": "PDF Tools",
        "colour": T.ACC,
        "apps": [
            dict(name="PDF Merge",        icon="⊕", file="pdf_merge.py",     desc="Combine multiple PDFs"),
            dict(name="PDF Split",        icon="✂", file="pdf_split.py",     desc="Split by ranges or pages"),
            dict(name="PDF N-up",         icon="⊞", file="pdf_nup.py",       desc="Multi-page per sheet"),
            dict(name="PDF Booklet",      icon="⊟", file="pdf_booklet.py",   desc="Booklet imposition"),
            dict(name="Rearrange Pages",  icon="⇅", file="pdf_rearrange.py", desc="Reorder / delete pages"),
            dict(name="PDF Compress",     icon="⊘", file="pdf_compress.py",  desc="Reduce file size"),
            dict(name="PDF → Image",      icon="◫", file="pdf_to_image.py",  desc="Extract pages as images"),
        ],
    },
    {
        "title": "Watermark",
        "colour": T.WARN,
        "apps": [
            dict(name="Remove Watermark", icon="◌", file="pdf_wm_remove.py", desc="Strip watermark layers"),
            dict(name="Add Watermark",    icon="⬡", file="pdf_wm_add.py",    desc="Stamp on every page"),
        ],
    },
    {
        "title": "Utilities",
        "colour": T.OK,
        "apps": [
            dict(name="Exam Photo Resizer", icon="⊡", file="image_resizer.py", desc="Resize for NEET/JEE/SSC"),
            dict(name="Calculator",         icon="∑", file="calculator.py",    desc="Scientific + graphing"),
        ],
    },
    {
        "title": "System",
        "colour": "#B06EF7",
        "apps": [
            dict(name="App Store",    icon="⊛", file="app_store.py",    desc="Install and manage apps"),
            dict(name="Settings",     icon="⚙", file="settings.py",     desc="Theme, wallpaper, display"),
            dict(name="Touch Manager",icon="✋", file="touch_manager.py",desc="Touch mode + gestures"),
            dict(name="Community",    icon="💬", file="community.py",    desc="Feedback & suggestions"),
        ],
    },
]


class LauncherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AndrobianOS")
        self.geometry("900x580")
        self.minsize(680, 440)
        T.apply(self)
        self._centre()
        self._build()

    def _centre(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"900x580+{(sw-900)//2}+{(sh-580)//2}")

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=T.SURF)
        hdr.pack(fill="x")
        tk.Frame(hdr, bg=T.ACC, width=4).pack(side="left", fill="y")
        hi = tk.Frame(hdr, bg=T.SURF, padx=18, pady=14)
        hi.pack(side="left", fill="both", expand=True)
        tk.Label(hi, text="AndrobianOS",
                 bg=T.SURF, fg=T.TXT, font=T.F(17, True)).pack(anchor="w")
        tk.Label(hi, text="Debian on Android — POCO PAD 5G · Bankura",
                 bg=T.SURF, fg=T.MUT, font=T.F(10)).pack(anchor="w")
        tk.Label(hdr, text="v1.0", bg=T.SURF, fg=T.DIM,
                 font=T.F(9)).pack(side="right", padx=12)
        T.Divider(self).pack(fill="x")

        # Scrollable body
        canvas = tk.Canvas(self, bg=T.BG, highlightthickness=0)
        sb = tk.Scrollbar(self, orient="vertical", command=canvas.yview,
                          bg=T.BDR, relief="flat", bd=0)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        body = tk.Frame(canvas, bg=T.BG, padx=22, pady=16)
        win  = canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win, width=e.width))
        body.bind("<Configure>",
                  lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        for ev in ("<MouseWheel>",):
            canvas.bind_all(ev,
                lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        canvas.bind_all("<Button-4>",
                        lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>",
                        lambda e: canvas.yview_scroll(1, "units"))

        for section in SECTIONS:
            self._render_section(body, section)

    def _render_section(self, parent, section):
        sf = tk.Frame(parent, bg=T.BG)
        sf.pack(fill="x", pady=(0, 14))

        hdr = tk.Frame(sf, bg=T.BG)
        hdr.pack(fill="x", pady=(0, 8))
        tk.Frame(hdr, bg=section["colour"], width=3, height=20
                 ).pack(side="left", fill="y", padx=(0, 8))
        tk.Label(hdr, text=section["title"], bg=T.BG,
                 fg=section["colour"], font=T.F(11, True)).pack(side="left")

        tiles = tk.Frame(sf, bg=T.BG)
        tiles.pack(fill="x", padx=10)

        for i, app in enumerate(section["apps"]):
            tile = self._make_tile(tiles, app, section["colour"])
            tile.grid(row=i//4, column=i%4, padx=5, pady=5, sticky="nsew")

        for c in range(4):
            tiles.columnconfigure(c, weight=1)

    def _make_tile(self, parent, app, accent):
        tile = tk.Frame(parent, bg=T.SURF, bd=0,
                        highlightthickness=1, highlightbackground=T.BDR,
                        cursor="hand2")
        tile.configure(width=185, height=96)
        tile.pack_propagate(False)

        inner = tk.Frame(tile, bg=T.SURF, padx=12, pady=10)
        inner.pack(fill="both", expand=True)

        icon_l = tk.Label(inner, text=app["icon"], bg=T.SURF,
                          fg=accent, font=T.F(18), anchor="w")
        icon_l.pack(anchor="w")
        name_l = tk.Label(inner, text=app["name"], bg=T.SURF,
                          fg=T.TXT, font=T.F(10, True), anchor="w")
        name_l.pack(anchor="w")
        desc_l = tk.Label(inner, text=app["desc"], bg=T.SURF,
                          fg=T.MUT, font=T.F(8), anchor="w",
                          wraplength=160, justify="left")
        desc_l.pack(anchor="w")

        all_w = [tile, inner, icon_l, name_l, desc_l]

        def on_enter(e, ws=all_w):
            for w in ws:
                w.configure(bg=T.SURF2)
            tile.configure(highlightbackground=accent)

        def on_leave(e, ws=all_w):
            for w in ws:
                w.configure(bg=T.SURF)
            tile.configure(highlightbackground=T.BDR)

        for w in all_w:
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", lambda e, a=app: self._launch(a))

        return tile

    def _launch(self, app):
        fpath = os.path.join(APPS_DIR, app["file"])
        if not os.path.isfile(fpath):
            T.popup(self, "File not found",
                    f"Cannot find: {fpath}\n\nInstall it from the App Store.", "error")
            return
        subprocess.Popen([sys.executable, fpath])


if __name__ == "__main__":
    LauncherApp().mainloop()
