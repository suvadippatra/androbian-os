"""
pdf_rearrange.py — Joydip's PDF Suite
Drag-and-drop style page reordering via an interactive numbered list.
The user can also delete pages or duplicate them before saving.
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


class RearrangeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Rearrange Pages — Joydip's Suite")
        self.geometry("740x560")
        T.apply(self)
        self._centre()
        self._doc_path = None
        self._order = []     # list of 0-based original page indices (current display order)
        self._build()

    def _centre(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"740x560+{(sw-740)//2}+{(sh-560)//2}")

    def _build(self):
        T.app_header(self, "Rearrange PDF Pages",
                     "Reorder, delete, or duplicate pages — then save", "⇅")
        body = tk.Frame(self, bg=T.BG, padx=20, pady=14)
        body.pack(fill="both", expand=True)

        # Source file load
        src_card = T.Card(body)
        src_card.pack(fill="x", pady=(0, 10))
        src_i = tk.Frame(src_card, bg=T.SURF, padx=12, pady=10)
        src_i.pack(fill="x")
        tk.Label(src_i, text="Source PDF:", bg=T.SURF, fg=T.MUT, font=T.F(10)
                 ).pack(anchor="w", pady=(0, 5))
        self.picker = T.FilePicker(src_i, bg=T.SURF)
        self.picker.pack(fill="x")
        T.Btn(src_i, "Load Pages", cmd=self._load, style="secondary",
              font=T.F(10, True), padx=9, pady=4).pack(anchor="e", pady=(5, 0))
        self.src_info = tk.Label(src_i, text="", bg=T.SURF, fg=T.MUT, font=T.F(9))
        self.src_info.pack(anchor="w")

        # Page list + controls
        list_card = T.Card(body)
        list_card.pack(fill="both", expand=True, pady=(0, 10))
        top_bar = tk.Frame(list_card, bg=T.SURF, padx=12, pady=8)
        top_bar.pack(fill="x")
        tk.Label(top_bar, text="Page order  (select a row, then use buttons):",
                 bg=T.SURF, fg=T.MUT, font=T.F(10)).pack(side="left")
        btn_f = tk.Frame(top_bar, bg=T.SURF)
        btn_f.pack(side="right")
        for label, cmd, st in [
            ("↑ Up",       lambda: self._shift(-1), "secondary"),
            ("↓ Down",     lambda: self._shift(1),  "secondary"),
            ("Duplicate",  self._dup,               "secondary"),
            ("✕ Delete",   self._delete,             "danger"),
            ("Reset",      self._reset,              "secondary"),
        ]:
            T.Btn(btn_f, label, cmd=cmd, style=st,
                  font=T.F(9, True), padx=7, pady=3).pack(side="left", padx=2)

        lb_wrap = tk.Frame(list_card, bg=T.SURF, padx=12, pady=4)
        lb_wrap.pack(fill="both", expand=True)
        sb = tk.Scrollbar(lb_wrap, bg=T.BDR, relief="flat", bd=0)
        self.lb = tk.Listbox(lb_wrap, bg=T.SURF2, fg=T.TXT, font=T.FM(10),
                             selectbackground=T.ADIM, relief="flat", bd=0,
                             yscrollcommand=sb.set, activestyle="none")
        sb.config(command=self.lb.yview)
        sb.pack(side="right", fill="y")
        self.lb.pack(fill="both", expand=True)
        self.count_var = tk.StringVar(value="")
        tk.Label(list_card, textvariable=self.count_var,
                 bg=T.SURF, fg=T.MUT, font=T.F(9), pady=4).pack()

        # Output + run
        out_card = T.Card(body)
        out_card.pack(fill="x", pady=(0, 8))
        out_i = tk.Frame(out_card, bg=T.SURF, padx=12, pady=8)
        out_i.pack(fill="x")
        tk.Label(out_i, text="Output:", bg=T.SURF, fg=T.MUT, font=T.F(10)
                 ).pack(anchor="w", pady=(0, 4))
        self.out_row = T.OutputRow(out_i, "rearranged.pdf", bg=T.SURF)
        self.out_row.pack(fill="x")

        self.prog = ttk.Progressbar(body, mode="determinate")
        self.prog.pack(fill="x", pady=(0, 4))
        self.log = T.LogBox(body, height=2)
        self.log.pack(fill="x", pady=(0, 8))
        T.Btn(body, "⇅   Save Rearranged PDF", cmd=self._save,
              style="primary", font=T.F(12, True)).pack(side="right")

    def _load(self):
        paths = self.picker.get()
        if not paths:
            T.popup(self, "No file", "Select a PDF first.", "warning")
            return
        try:
            doc = fitz.open(paths[0])
            self._doc_path = paths[0]
            self._order = list(range(len(doc)))
            self._orig_n = len(doc)
            self.src_info.config(
                text=f"Loaded: {os.path.basename(paths[0])}  |  {len(doc)} pages",
                fg=T.OK)
            doc.close()
            self._refresh()
        except Exception as e:
            T.popup(self, "Load Error", str(e), "error")

    def _refresh(self):
        self.lb.delete(0, "end")
        for i, orig in enumerate(self._order):
            label = f"  Position {i+1:03d}  ←  Original page {orig+1:03d}"
            self.lb.insert("end", label)
        self.count_var.set(f"{len(self._order)} page(s) in current order")

    def _shift(self, d):
        sel = self.lb.curselection()
        if not sel:
            return
        i = sel[0]
        j = i + d
        if 0 <= j < len(self._order):
            self._order[i], self._order[j] = self._order[j], self._order[i]
            self._refresh()
            self.lb.selection_set(j)

    def _dup(self):
        sel = self.lb.curselection()
        if not sel:
            return
        i = sel[0]
        self._order.insert(i + 1, self._order[i])
        self._refresh()

    def _delete(self):
        sel = self.lb.curselection()
        if not sel:
            return
        self._order.pop(sel[0])
        self._refresh()

    def _reset(self):
        if hasattr(self, "_orig_n"):
            self._order = list(range(self._orig_n))
            self._refresh()

    def _save(self):
        if not self._doc_path or not self._order:
            T.popup(self, "Nothing to save", "Load a PDF and adjust the order first.",
                    "warning")
            return
        out = self.out_row.get_path()
        self.log.clear()
        self.prog["value"] = 0
        order = list(self._order)

        def worker():
            try:
                src = fitz.open(self._doc_path)
                out_doc = fitz.open()
                for i, pg in enumerate(order):
                    out_doc.insert_pdf(src, from_page=pg, to_page=pg)
                    self.prog["value"] = int((i + 1) / len(order) * 100)
                out_doc.save(out, garbage=4, deflate=True)
                src.close()
                out_doc.close()
                self.log.append(f"✓  Saved {len(order)} pages → {out}", T.OK)
                T.toast(self, "Pages saved  ✓", "success")
            except Exception as e:
                self.log.append(f"ERROR: {e}", T.ERR)

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    RearrangeApp().mainloop()
