"""
pdf_wm_remove.py — Joydip's PDF Suite
Watermark removal using four independently-toggled strategies,
derived directly from the comprehensive_watermark_remover notebook.
"""

import tkinter as tk
from tkinter import ttk
import os, threading, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import theme as T

try:
    import fitz
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "pymupdf", "--break-system-packages"],
                   capture_output=True)
    import fitz


# ─── Backend: four-strategy watermark remover ────────────────────────────────
# Logic derived directly from the uploaded Watermark_removal_.ipynb notebook.

def detect_watermark(input_path, grey_lo=0.60, grey_hi=0.99):
    """
    Non-destructive scan: count how many structural objects *would* be modified
    by each strategy. Returns a dict report used by the detection panel.
    """
    report = {
        "annotations":  0,
        "vector_streams": 0,
        "large_images":   0,
        "total_objects":  0,
    }
    try:
        doc = fitz.open(input_path)
        report["total_objects"] = doc.xref_length()

        # Count annotations
        for page in doc:
            report["annotations"] += len(list(page.annots()))

        # Count modifiable streams (grey colour operators)
        lo = f"{grey_lo:.2f}".encode()
        hi = f"{grey_hi:.2f}".encode()
        # Build a simple numeric range at the last digit level
        lo_d = str(int(grey_lo * 10))[-1].encode()
        hi_d = str(int(grey_hi * 10))[-1].encode()
        bound = rb'(?:0?\.[' + lo_d + rb'-' + hi_d + rb'][0-9]*)'
        rgb_pat  = re.compile(bound + rb'\s+' + bound + rb'\s+' + bound + rb'\s+(rg|RG)\b')
        gray_pat = re.compile(bound + rb'\s+(g|G)\b')

        for xref in range(1, doc.xref_length()):
            if doc.xref_is_stream(xref):
                try:
                    b = doc.xref_stream(xref)
                    if b and (rgb_pat.search(b) or gray_pat.search(b)):
                        report["vector_streams"] += 1
                except Exception:
                    continue

        # Count large images
        for page in doc:
            for img in page.get_images(full=True):
                if img[2] > 400 and img[3] > 400:
                    report["large_images"] += 1

        doc.close()
    except Exception:
        pass
    return report


def remove_watermarks(input_path, output_path,
                      do_annotations=True,
                      do_text=False,    target_text="",
                      do_images=False,  img_threshold=400,
                      do_vectors=True,
                      grey_lo=0.60,     grey_hi=0.99,
                      progress_cb=None):
    """
    Execute the selected removal strategies and save the cleaned PDF.
    progress_cb(pct, message) is called during processing when provided.
    """
    def _cb(pct, msg):
        if progress_cb:
            progress_cb(pct, msg)

    doc = fitz.open(input_path)
    mods = 0

    # ── Strategy 1: annotation stripping ──
    if do_annotations:
        _cb(10, "Strategy 1: Stripping annotation layers …")
        removed = 0
        for page in doc:
            annots = list(page.annots())
            for annot in annots:
                page.delete_annot(annot)
                removed += 1
        mods += removed
        _cb(25, f"  → Removed {removed} annotation(s).")

    # ── Strategy 2: text redaction ──
    if do_text and target_text:
        _cb(30, f"Strategy 2: Redacting text  '{target_text}' …")
        redacted = 0
        for page in doc:
            hits = page.search_for(target_text)
            for rect in hits:
                page.add_redact_annot(rect, fill=(1, 1, 1))
            if hits:
                page.apply_redactions()
                redacted += len(hits)
        mods += redacted
        _cb(45, f"  → Redacted {redacted} text instance(s).")

    # ── Strategy 3: large image neutralisation ──
    if do_images:
        _cb(50, f"Strategy 3: Neutralising large raster images (threshold {img_threshold}px) …")
        neutralised = 0
        for page in doc:
            for img in page.get_images(full=True):
                xref, w, h = img[0], img[2], img[3]
                if w > img_threshold and h > img_threshold:
                    try:
                        doc.xref_set_key(xref, "Width",  "1")
                        doc.xref_set_key(xref, "Height", "1")
                        neutralised += 1
                    except Exception:
                        pass
        mods += neutralised
        _cb(65, f"  → Neutralised {neutralised} large image(s).")

    # ── Strategy 4: global vector grey-colour sweep ──
    # Direct port of neutralize_global_vector_watermark / obliterate_remaining_watermark
    # from the uploaded notebook.
    if do_vectors:
        _cb(70, f"Strategy 4: Sweeping vector streams for grey {grey_lo:.2f}–{grey_hi:.2f} …")

        lo_d = str(int(grey_lo * 10))[-1].encode()
        hi_d = str(min(9, int(grey_hi * 10)))[-1].encode()
        bound = rb'(?:0?\.[' + lo_d + rb'-' + hi_d + rb'][0-9]*)'
        rgb_pat  = re.compile(bound + rb'\s+' + bound + rb'\s+' + bound + rb'\s+(rg|RG)\b')
        gray_pat = re.compile(bound + rb'\s+(g|G)\b')

        swept = 0
        total_xrefs = doc.xref_length()
        for xref in range(1, total_xrefs):
            if doc.xref_is_stream(xref):
                try:
                    raw = doc.xref_stream(xref)
                    if not raw:
                        continue
                    new = rgb_pat.sub(rb'1.0 1.0 1.0 \1', raw)
                    new = gray_pat.sub(rb'1.0 \1',         new)
                    if new != raw:
                        doc.update_stream(xref, new)
                        swept += 1
                except Exception:
                    continue
        mods += swept
        _cb(92, f"  → Swept {swept} stream(s) across {total_xrefs} objects.")

    # ── Save ──
    _cb(95, "Compiling and saving cleaned document …")
    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    _cb(100, f"✓  Done — {mods} structural modification(s) made.")
    return mods


class WmRemoveApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Watermark Remover — Joydip's Suite")
        self.geometry("800x680")
        self.minsize(660, 520)
        T.apply(self)
        self._centre()
        self._build()

    def _centre(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"800x680+{(sw-800)//2}+{(sh-680)//2}")

    # ─── UI ───────────────────────────────────────────────────────────────────
    def _build(self):
        T.app_header(self, "Watermark Remover",
                     "Auto-detect and remove watermarks using up to 4 strategies", "◌")

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

        # ── Strategy toggles ──
        strat_card = T.Card(body)
        strat_card.pack(fill="x", pady=(0, 10))
        strat_i = tk.Frame(strat_card, bg=T.SURF, padx=12, pady=10)
        strat_i.pack(fill="x")
        tk.Label(strat_i, text="Removal strategies — enable what applies to your file:",
                 bg=T.SURF, fg=T.MUT, font=T.F(10)).pack(anchor="w", pady=(0, 6))

        self._do_ann  = tk.BooleanVar(value=True)
        self._do_vec  = tk.BooleanVar(value=True)
        self._do_img  = tk.BooleanVar(value=False)
        self._do_txt  = tk.BooleanVar(value=False)

        row1 = tk.Frame(strat_i, bg=T.SURF)
        row1.pack(fill="x", pady=2)
        tk.Checkbutton(row1, text="Strip annotation layers  (surface stamps, highlights)",
                       variable=self._do_ann, bg=T.SURF, fg=T.TXT,
                       selectcolor=T.SURF2, activebackground=T.SURF,
                       font=T.F(10)).pack(side="left")

        row2 = tk.Frame(strat_i, bg=T.SURF)
        row2.pack(fill="x", pady=2)
        tk.Checkbutton(row2, text="Sweep vector colour streams  (grey geometric overlays)",
                       variable=self._do_vec, bg=T.SURF, fg=T.TXT,
                       selectcolor=T.SURF2, activebackground=T.SURF,
                       font=T.F(10)).pack(side="left")

        row3 = tk.Frame(strat_i, bg=T.SURF)
        row3.pack(fill="x", pady=2)
        cb_img = tk.Checkbutton(row3, text="Neutralise large background images  (threshold:",
                                variable=self._do_img, bg=T.SURF, fg=T.TXT,
                                selectcolor=T.SURF2, activebackground=T.SURF,
                                font=T.F(10))
        cb_img.pack(side="left")
        self._img_thr = tk.StringVar(value="400")
        tk.Entry(row3, textvariable=self._img_thr, bg=T.SURF2, fg=T.TXT,
                 font=T.F(10), relief="flat", bd=0, width=5).pack(side="left", ipady=3)
        tk.Label(row3, text="px)", bg=T.SURF, fg=T.MUT, font=T.F(10)).pack(side="left")

        row4 = tk.Frame(strat_i, bg=T.SURF)
        row4.pack(fill="x", pady=2)
        cb_txt = tk.Checkbutton(row4, text="Redact text string:",
                                variable=self._do_txt, bg=T.SURF, fg=T.TXT,
                                selectcolor=T.SURF2, activebackground=T.SURF,
                                font=T.F(10))
        cb_txt.pack(side="left")
        self._txt_val = tk.StringVar()
        tk.Entry(row4, textvariable=self._txt_val, bg=T.SURF2, fg=T.TXT,
                 font=T.F(10), relief="flat", bd=0, width=20,
                 insertbackground=T.TXT).pack(side="left", ipady=3, padx=(6, 0))

        # ── Grey accuracy slider (affects strategy 4) ──
        grey_card = T.Card(body)
        grey_card.pack(fill="x", pady=(0, 10))
        grey_i = tk.Frame(grey_card, bg=T.SURF, padx=12, pady=10)
        grey_i.pack(fill="x")
        tk.Label(grey_i,
                 text="Vector sweep accuracy — grey range to target "
                      "(lower range = more selective, higher range = more aggressive):",
                 bg=T.SURF, fg=T.MUT, font=T.F(10), wraplength=660, justify="left"
                 ).pack(anchor="w", pady=(0, 6))
        self.grey_lo_s = T.Slider(grey_i, "Lower bound (0.60 = selective)",
                                  0, 100, 60, fmt="{:.0f}", suffix="%", bg=T.SURF,
                                  resolution=1)
        self.grey_hi_s = T.Slider(grey_i, "Upper bound (0.99 = aggressive)",
                                  0, 100, 99, fmt="{:.0f}", suffix="%", bg=T.SURF,
                                  resolution=1)
        self.grey_lo_s.pack(fill="x", pady=2)
        self.grey_hi_s.pack(fill="x", pady=2)
        tk.Label(grey_i,
                 text="Tip: For typical grey vector watermarks start at 84%–86%  "
                      "(the exact range from GATE PDFs). Wider = removes more, "
                      "but may also lighten real content.",
                 bg=T.SURF, fg=T.DIM, font=T.F(9), wraplength=660, justify="left"
                 ).pack(anchor="w", pady=(4, 0))

        # ── Detection report ──
        det_card = T.Card(body)
        det_card.pack(fill="x", pady=(0, 10))
        det_i = tk.Frame(det_card, bg=T.SURF, padx=12, pady=8)
        det_i.pack(fill="x")
        top = tk.Frame(det_i, bg=T.SURF)
        top.pack(fill="x")
        tk.Label(top, text="Detection report (scan before removing):",
                 bg=T.SURF, fg=T.MUT, font=T.F(10)).pack(side="left")
        T.Btn(top, "Scan File", cmd=self._scan, style="secondary",
              font=T.F(10, True), padx=9, pady=3).pack(side="right")
        self.det_log = T.LogBox(det_i, height=4)
        self.det_log.pack(fill="x", pady=(6, 0))

        # ── Output ──
        out_card = T.Card(body)
        out_card.pack(fill="x", pady=(0, 8))
        out_i = tk.Frame(out_card, bg=T.SURF, padx=12, pady=8)
        out_i.pack(fill="x")
        tk.Label(out_i, text="Output:", bg=T.SURF, fg=T.MUT, font=T.F(10)
                 ).pack(anchor="w", pady=(0, 4))
        self.out_row = T.OutputRow(out_i, "cleaned_output.pdf", bg=T.SURF)
        self.out_row.pack(fill="x")

        # ── Progress + run ──
        self.prog = ttk.Progressbar(body, mode="determinate")
        self.prog.pack(fill="x", pady=(0, 4))
        self.log = T.LogBox(body, height=3)
        self.log.pack(fill="x", pady=(0, 8))

        T.Btn(body, "◌   Remove Watermarks", cmd=self._start,
              style="primary", font=T.F(12, True)).pack(side="right")

    # ─── Scan ─────────────────────────────────────────────────────────────────
    def _scan(self):
        paths = self.picker.get()
        if not paths:
            T.popup(self, "No file", "Browse and select a PDF first.", "warning")
            return
        p = paths[0]
        lo = self.grey_lo_s.get() / 100.0
        hi = self.grey_hi_s.get() / 100.0
        self.det_log.clear()
        self.det_log.append(f"Scanning: {os.path.basename(p)} …")
        try:
            doc_f = fitz.open(p)
            n_pages = len(doc_f)
            size_mb = os.path.getsize(p) / 1048576
            doc_f.close()
            self.src_info.config(
                text=f"{n_pages} pages  |  {size_mb:.1f} MB", fg=T.OK)
        except Exception as e:
            T.popup(self, "Load error", str(e), "error")
            return

        def worker():
            r = detect_watermark(p, lo, hi)
            self.det_log.append(
                f"  Total PDF objects   : {r['total_objects']}")
            self.det_log.append(
                f"  Annotations found   : {r['annotations']}"
                + ("  ← likely watermark" if r['annotations'] > 0 else ""), T.OK if r['annotations'] > 0 else None)
            self.det_log.append(
                f"  Grey vector streams : {r['vector_streams']}"
                + ("  ← likely watermark" if r['vector_streams'] > 0 else ""), T.OK if r['vector_streams'] > 0 else None)
            self.det_log.append(
                f"  Large images (>{int(400)}px): {r['large_images']}")
            if r['annotations'] == 0 and r['vector_streams'] == 0 and r['large_images'] == 0:
                self.det_log.append(
                    "  → No detectable watermark layers found.\n"
                    "     (Scanned/printed page watermarks cannot be removed "
                    "programmatically.)", T.WARN)
            else:
                self.det_log.append(
                    "  → Watermark layers detected. Ready to remove.", T.OK)

        threading.Thread(target=worker, daemon=True).start()

    # ─── Remove ───────────────────────────────────────────────────────────────
    def _start(self):
        paths = self.picker.get()
        if not paths:
            T.popup(self, "No file", "Browse and select a PDF first.", "warning")
            return
        inp = paths[0]
        out = self.out_row.get_path()
        lo  = self.grey_lo_s.get() / 100.0
        hi  = self.grey_hi_s.get() / 100.0

        self.prog["value"] = 0
        self.log.clear()
        self.log.append("Starting watermark removal …")

        def cb(pct, msg):
            self.prog["value"] = pct
            self.log.append(msg)

        def worker():
            try:
                mods = remove_watermarks(
                    inp, out,
                    do_annotations = self._do_ann.get(),
                    do_text        = self._do_txt.get(),
                    target_text    = self._txt_val.get(),
                    do_images      = self._do_img.get(),
                    img_threshold  = int(self._img_thr.get() or "400"),
                    do_vectors     = self._do_vec.get(),
                    grey_lo        = lo,
                    grey_hi        = hi,
                    progress_cb    = cb,
                )
                self.log.append(f"Saved to: {out}", T.OK)
                T.toast(self, f"Watermark removal done — {mods} modification(s)  ✓",
                        "success")
            except Exception as e:
                self.log.append(f"ERROR: {e}", T.ERR)
                T.popup(self, "Removal Failed", str(e), "error")

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    WmRemoveApp().mainloop()
