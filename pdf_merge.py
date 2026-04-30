"""
pdf_merge.py — Joydip's PDF Suite
Merge multiple PDF files in any custom order you choose.
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


class MergeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF Merge — Joydip's Suite")
        self.geometry("760x580")
        self.minsize(620, 460)
        T.apply(self)
        self._centre()
        self.files = []       # list of absolute file paths
        self._build()

    def _centre(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"760x580+{(sw-760)//2}+{(sh-580)//2}")

    # ─── UI construction ──────────────────────────────────────────────────────
    def _build(self):
        T.app_header(self, "PDF Merge", "Combine multiple PDFs in your chosen order", "⊕")

        body = tk.Frame(self, bg=T.BG, padx=20, pady=14)
        body.pack(fill="both", expand=True)

        # ── File list card ──
        list_card = T.Card(body)
        list_card.pack(fill="both", expand=True, pady=(0, 10))

        top_bar = tk.Frame(list_card, bg=T.SURF, padx=12, pady=9)
        top_bar.pack(fill="x")
        tk.Label(top_bar, text="Files to merge — use ↑ ↓ to reorder:",
                 bg=T.SURF, fg=T.MUT, font=T.F(10)).pack(side="left")

        btns = tk.Frame(top_bar, bg=T.SURF)
        btns.pack(side="right")
        for txt, cmd in [("+ Add", self._add_files),
                         ("✕ Remove", self._remove_sel),
                         ("↑", lambda: self._move(-1)),
                         ("↓", lambda: self._move(1)),
                         ("Clear All", self._clear_all)]:
            st = "danger" if txt == "✕ Remove" else "secondary"
            T.Btn(btns, txt, cmd=cmd, style=st, font=T.F(10, True),
                  padx=9, pady=4).pack(side="left", padx=2)

        # ── Listbox with scrollbar ──
        lb_wrap = tk.Frame(list_card, bg=T.SURF, padx=12, pady=6)
        lb_wrap.pack(fill="both", expand=True)

        sb = tk.Scrollbar(lb_wrap, bg=T.BDR, troughcolor=T.BG,
                          relief="flat", bd=0)
        self.lb = tk.Listbox(
            lb_wrap, bg=T.SURF2, fg=T.TXT, font=T.F(10),
            selectbackground=T.ADIM, selectforeground=T.TXT,
            relief="flat", bd=0, activestyle="none",
            yscrollcommand=sb.set, height=9
        )
        sb.config(command=self.lb.yview)
        sb.pack(side="right", fill="y")
        self.lb.pack(fill="both", expand=True)

        # ── Status strip at bottom of card ──
        self.info_var = tk.StringVar(value="No files added.  Click '+ Add' to begin.")
        tk.Label(list_card, textvariable=self.info_var,
                 bg=T.SURF, fg=T.MUT, font=T.F(9), pady=5).pack()

        # ── Total page count label ──
        self.pages_var = tk.StringVar(value="")
        tk.Label(body, textvariable=self.pages_var,
                 bg=T.BG, fg=T.MUT, font=T.F(9)).pack(anchor="w", pady=(0, 6))

        # ── Output row ──
        out_card = T.Card(body)
        out_card.pack(fill="x", pady=(0, 10))
        out_inner = tk.Frame(out_card, bg=T.SURF, padx=12, pady=10)
        out_inner.pack(fill="x")
        tk.Label(out_inner, text="Output file:", bg=T.SURF, fg=T.MUT,
                 font=T.F(10)).pack(anchor="w", pady=(0, 5))
        self.out_row = T.OutputRow(out_inner, "merged_output.pdf", bg=T.SURF)
        self.out_row.pack(fill="x")

        # ── Progress + log ──
        self.prog = ttk.Progressbar(body, mode="determinate")
        self.prog.pack(fill="x", pady=(0, 4))
        self.log = T.LogBox(body, height=3)
        self.log.pack(fill="x", pady=(0, 8))

        # ── Merge button ──
        T.Btn(body, "⊕   Merge PDFs", cmd=self._start_merge,
              style="primary", font=T.F(12, True)).pack(side="right")

    # ─── File management ──────────────────────────────────────────────────────
    def _add_files(self):
        from tkinter import filedialog
        fs = filedialog.askopenfilenames(
            title="Select PDF files",
            filetypes=[("PDF files", "*.pdf")])
        for f in fs:
            if f not in self.files:
                self.files.append(f)
        self._refresh()

    def _remove_sel(self):
        sel = self.lb.curselection()
        if not sel:
            return
        idx = sel[0]
        self.files.pop(idx)
        self._refresh()

    def _move(self, direction):
        sel = self.lb.curselection()
        if not sel:
            return
        idx = sel[0]
        new_idx = idx + direction
        if 0 <= new_idx < len(self.files):
            self.files[idx], self.files[new_idx] = self.files[new_idx], self.files[idx]
            self._refresh()
            self.lb.selection_set(new_idx)

    def _clear_all(self):
        self.files.clear()
        self._refresh()

    def _refresh(self):
        """Redraw the listbox and recalculate total pages."""
        self.lb.delete(0, "end")
        total_pages = 0
        for i, path in enumerate(self.files):
            try:
                doc = fitz.open(path)
                n = len(doc)
                doc.close()
                total_pages += n
                label = f"  {i+1:02d}.  {os.path.basename(path)}   ({n} pages)"
            except Exception:
                label = f"  {i+1:02d}.  {os.path.basename(path)}   (unreadable)"
            self.lb.insert("end", label)

        n = len(self.files)
        if n == 0:
            self.info_var.set("No files added.  Click '+ Add' to begin.")
            self.pages_var.set("")
        else:
            self.info_var.set(f"{n} file(s) queued.  Select a row and use ↑ ↓ to reorder.")
            self.pages_var.set(f"Total pages after merge: {total_pages}")

    # ─── Merge logic ──────────────────────────────────────────────────────────
    def _start_merge(self):
        if len(self.files) < 2:
            T.popup(self, "Not enough files",
                    "Please add at least 2 PDF files to merge.", "warning")
            return
        out = self.out_row.get_path()
        self.prog["value"] = 0
        self.log.clear()
        self.log.append("Starting merge operation …")

        def worker():
            try:
                result = fitz.open()
                total = len(self.files)
                for i, path in enumerate(self.files):
                    doc = fitz.open(path)
                    result.insert_pdf(doc)
                    doc.close()
                    progress = int((i + 1) / total * 90)
                    self.prog["value"] = progress
                    self.log.append(f"  ✓  Added: {os.path.basename(path)}", T.OK)

                self.log.append("Saving and optimising …")
                result.save(out, garbage=4, deflate=True)
                result.close()
                self.prog["value"] = 100
                self.log.append(f"Done!  Saved → {out}", T.OK)
                T.toast(self, f"Merged {total} files  ✓", "success")
            except Exception as e:
                self.log.append(f"ERROR: {e}", T.ERR)
                T.popup(self, "Merge Failed", str(e), "error")

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    MergeApp().mainloop()
