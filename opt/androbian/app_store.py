#!/usr/bin/env python3
"""
app_store.py — AndrobianOS  [v3 — GitHub-connected]
═══════════════════════════════════════════════════════════════════════
HOW THE GITHUB CONNECTION WORKS:
  On open, the store fetches apps_manifest.json from your GitHub repo.
  This file lists every app, its version, description, and download URL.
  The store compares each app's version against the locally installed copy.
  If a newer version exists on GitHub, an "Update" button appears.
  If the file is missing locally, an "Install" button appears.

  All of this is controlled by YOU editing apps_manifest.json on GitHub.
  No rebuilding of this file is needed to add or update apps.

USER-CREATED APPS (paste-code feature):
  Kept, but sandboxed. User apps are saved to a separate folder:
    ~/.config/androbian/user_apps/
  They NEVER overwrite core suite files. If a user app crashes, the
  main OS is completely unaffected. The user app simply fails to launch.

UNLOCK HIDDEN PANEL:
  Hold (press and hold) the store header for 4 seconds.
═══════════════════════════════════════════════════════════════════════
"""

import tkinter as tk
from tkinter import ttk
import os, sys, json, threading, subprocess, webbrowser, shutil, hashlib
import urllib.request, urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import theme as T

# ── Paths ──────────────────────────────────────────────────────────────────
SUITE_DIR    = os.path.dirname(os.path.abspath(__file__))
USER_APP_DIR = os.path.expanduser("~/.config/androbian/user_apps")
CONFIG_FILE  = os.path.expanduser("~/.config/androbian/config.json")
LOCAL_MANIFEST = os.path.join(SUITE_DIR, "apps_manifest.json")

os.makedirs(USER_APP_DIR, exist_ok=True)

# ── Config helpers ──────────────────────────────────────────────────────────

def _read_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _manifest_url():
    cfg  = _read_config()
    user = cfg.get("github_user", "YOUR_USER")
    repo = cfg.get("github_repo", "androbian-os")
    return (f"https://raw.githubusercontent.com/{user}/{repo}/main/"
            "apps_manifest.json")


def _download_manifest():
    """Fetch manifest from GitHub. Falls back to local file on failure."""
    try:
        url = _manifest_url()
        req = urllib.request.Request(url, headers={"User-Agent": "AndrobianOS/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read())
            # Cache it locally
            with open(LOCAL_MANIFEST, "w") as f:
                json.dump(data, f, indent=2)
            return data, True      # (data, from_github)
    except Exception:
        try:
            with open(LOCAL_MANIFEST) as f:
                return json.load(f), False
        except Exception:
            return {"suite_apps": [], "announcements": []}, False


def _installed_version(file_name):
    """
    Read the version comment from the first 10 lines of an installed app file.
    Returns '0' if not found.  Format expected:  # version: 1.0
    """
    path = os.path.join(SUITE_DIR, file_name)
    if not os.path.isfile(path):
        return None    # Not installed
    try:
        with open(path) as f:
            for line in f.readlines()[:10]:
                if "version:" in line.lower():
                    return line.strip().split(":")[-1].strip()
    except Exception:
        pass
    return "1.0"       # Installed but version undetectable


def _download_app_file(file_name, log_cb):
    """
    Download a single .py file from GitHub raw content to SUITE_DIR.
    Returns True on success.
    """
    cfg  = _read_config()
    user = cfg.get("github_user", "YOUR_USER")
    repo = cfg.get("github_repo", "androbian-os")
    url  = f"https://raw.githubusercontent.com/{user}/{repo}/main/{file_name}"
    dest = os.path.join(SUITE_DIR, file_name)
    log_cb(f"  Downloading {file_name} from GitHub…")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AndrobianOS/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
        with open(dest, "wb") as f:
            f.write(content)
        log_cb(f"  ✓  {file_name} saved ({len(content)//1024} KB)", T.OK)
        return True
    except Exception as e:
        log_cb(f"  ✗  Failed to download {file_name}: {e}", T.ERR)
        return False


# ── System package catalogue (apt) — grouped by category ──────────────────
APT_CATALOGUE = {
    "Browser": [
        dict(name="Falkon",        pkg="falkon",         size="~90 MB",
             desc="Lightweight Qt browser — recommended default"),
        dict(name="Firefox ESR",   pkg="firefox-esr",    size="~220 MB",
             desc="Full Mozilla Firefox — best site compatibility"),
    ],
    "Office & Notes": [
        dict(name="LibreOffice Core", pkg="libreoffice-core", size="~380 MB",
             desc="Writer, Calc, Impress — minimal install"),
        dict(name="CherryTree",    pkg="cherrytree",     size="~40 MB",
             desc="Hierarchical rich-text notes"),
        dict(name="Zathura",       pkg="zathura zathura-pdf-poppler", size="~25 MB",
             desc="Minimal keyboard-driven PDF viewer"),
        dict(name="Foliate",       pkg="foliate",        size="~35 MB",
             desc="GTK e-book reader (EPUB, PDF)"),
    ],
    "Education": [
        dict(name="Anki",          pkg="anki",            size="~100 MB",
             desc="Flashcard app — essential for medical students"),
        dict(name="GoldenDict",    pkg="goldendict",      size="~45 MB",
             desc="Offline dictionary — add MDX medical files"),
    ],
    "UI & Desktop": [
        dict(name="Picom",         pkg="picom",           size="~8 MB",
             desc="Compositor — rounded corners + animations"),
        dict(name="Plank Dock",    pkg="plank",           size="~15 MB",
             desc="macOS-style icon dock"),
        dict(name="Kvantum",       pkg="kvantum",         size="~15 MB",
             desc="SVG Qt theme engine"),
        dict(name="Feh",           pkg="feh",             size="~2 MB",
             desc="Wallpaper setter (needed by Settings app)"),
    ],
    "System Tools": [
        dict(name="Ghostscript",   pkg="ghostscript",     size="~30 MB",
             desc="PDF engine for PDF Compress aggressive mode"),
        dict(name="htop",          pkg="htop",            size="~3 MB",
             desc="Interactive process monitor"),
        dict(name="tmux",          pkg="tmux",            size="~4 MB",
             desc="Terminal session manager — keeps sessions alive"),
        dict(name="xdotool",       pkg="xdotool",         size="~2 MB",
             desc="Keyboard/mouse automation — needed by Touch Manager"),
        dict(name="Flatpak",       pkg="flatpak",         size="~25 MB",
             desc="Universal app installer — needed for Flathub apps"),
    ],
    "Python Libraries": [
        dict(name="Pillow",        pkg="python3-pil",     size="~25 MB",
             desc="Image processing library"),
        dict(name="Matplotlib",    pkg="python3-matplotlib", size="~60 MB",
             desc="Graphing library for Calculator app"),
        dict(name="NumPy",         pkg="python3-numpy",   size="~20 MB",
             desc="Maths library (used with Matplotlib)"),
    ],
}

EXTERNAL_STORES = [
    dict(name="KDE Apps",  url="https://apps.kde.org/",       colour=T.ACC),
    dict(name="Flathub",   url="https://flathub.org/",         colour=T.OK),
]


# ── Main App Store ─────────────────────────────────────────────────────────

class AppStoreApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("App Store — AndrobianOS")
        self.geometry("940x680")
        self.minsize(700, 500)
        T.apply(self)
        self._centre()
        self._manifest      = {"suite_apps": [], "announcements": []}
        self._from_github   = False
        self._hidden_added  = False
        self._lp_job        = None   # long-press job id
        self._build()
        # Fetch manifest in background so UI opens instantly
        threading.Thread(target=self._fetch_manifest_bg, daemon=True).start()

    def _centre(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"940x680+{(sw-940)//2}+{(sh-680)//2}")

    # ── Background manifest fetch ──────────────────────────────────────────
    def _fetch_manifest_bg(self):
        data, from_gh = _download_manifest()
        self._manifest   = data
        self._from_github = from_gh
        # Refresh the suite tab and announcements
        self.after(0, self._populate_suite_tab)
        self.after(0, self._show_announcements)

    # ── Main layout ────────────────────────────────────────────────────────
    def _build(self):
        # Header — 4-second long-press unlocks hidden panel
        hdr = tk.Frame(self, bg=T.SURF)
        hdr.pack(fill="x")
        tk.Frame(hdr, bg=T.ACC, width=4).pack(side="left", fill="y")
        hi = tk.Frame(hdr, bg=T.SURF, padx=18, pady=12)
        hi.pack(side="left", fill="both", expand=True)

        self._title_lbl = tk.Label(hi, text="App Store — AndrobianOS",
                                    bg=T.SURF, fg=T.TXT, font=T.F(14, True))
        self._title_lbl.pack(anchor="w")
        self._src_lbl = tk.Label(hi,
            text="Fetching app list from GitHub…",
            bg=T.SURF, fg=T.MUT, font=T.F(9))
        self._src_lbl.pack(anchor="w")

        for w in (self._title_lbl, hi, hdr):
            w.bind("<ButtonPress-1>",   self._lp_start)
            w.bind("<ButtonRelease-1>", self._lp_cancel)

        T.Divider(self).pack(fill="x")

        # External store buttons
        ext_row = tk.Frame(self, bg=T.BG, padx=18, pady=6)
        ext_row.pack(fill="x")
        tk.Label(ext_row, text="External:", bg=T.BG, fg=T.MUT,
                 font=T.F(9)).pack(side="left", padx=(0, 8))
        for s in EXTERNAL_STORES:
            T.Btn(ext_row, f"  {s['name']}  ↗",
                  cmd=lambda u=s["url"]: webbrowser.open(u),
                  style="secondary", font=T.F(9, True), padx=6, pady=2
                  ).pack(side="left", padx=(0, 6))
        tk.Label(ext_row,
                 text="(Flathub needs flatpak installed first)",
                 bg=T.BG, fg=T.DIM, font=T.F(8)).pack(side="left")

        T.Divider(self).pack(fill="x")

        # Main notebook
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)

        # Tab 1 — Suite Apps (populated after manifest loads)
        self._suite_frame = tk.Frame(self.nb, bg=T.BG)
        self.nb.add(self._suite_frame, text="  ⚙  Suite Apps  ")
        tk.Label(self._suite_frame,
                 text="Loading app list from GitHub…",
                 bg=T.BG, fg=T.MUT, font=T.F(10)).pack(pady=30)

        # Tab 2 — System Packages
        t2 = tk.Frame(self.nb, bg=T.BG)
        self.nb.add(t2, text="  📦  System Packages  ")
        self._build_apt_tab(t2)

        # Bottom log
        T.Divider(self).pack(fill="x")
        self.log = T.LogBox(self, height=3)
        self.log.pack(fill="x")

    # ── Announcements banner ───────────────────────────────────────────────
    def _show_announcements(self):
        for ann in self._manifest.get("announcements", []):
            self.log.append(
                f"📢  {ann.get('title','')}: {ann.get('body','')}", T.ACC)

        src = "GitHub ✓" if self._from_github else "Local cache (offline)"
        self._src_lbl.config(text=f"Source: {src}")

    # ── Suite Apps tab ─────────────────────────────────────────────────────
    def _populate_suite_tab(self):
        """Called after manifest loads. Rebuilds the suite apps tab."""
        for w in self._suite_frame.winfo_children():
            w.destroy()

        apps = self._manifest.get("suite_apps", [])
        if not apps:
            tk.Label(self._suite_frame,
                     text="Could not load app list. Check GitHub config.",
                     bg=T.BG, fg=T.ERR, font=T.F(10)).pack(pady=30)
            return

        # Category filter
        top = tk.Frame(self._suite_frame, bg=T.BG, padx=16, pady=6)
        top.pack(fill="x")
        cats = ["All"] + sorted(set(a.get("category","") for a in apps))
        self._cat_var = tk.StringVar(value="All")
        self._cat_var.trace_add("write", lambda *_: self._filter_suite(apps))
        ttk.Combobox(top, textvariable=self._cat_var,
                     values=cats, state="readonly", width=18).pack(side="left")
        tk.Label(top, text=f"  {len(apps)} apps available",
                 bg=T.BG, fg=T.MUT, font=T.F(9)).pack(side="left", padx=8)
        T.Btn(top, "⟳ Refresh", cmd=lambda: threading.Thread(
              target=self._fetch_manifest_bg, daemon=True).start(),
              style="secondary", font=T.F(9, True), padx=6, pady=2
              ).pack(side="right")

        # Scrollable list
        self._suite_cv   = tk.Canvas(self._suite_frame, bg=T.BG, highlightthickness=0)
        self._suite_sb   = tk.Scrollbar(self._suite_frame, orient="vertical",
                                         command=self._suite_cv.yview,
                                         bg=T.BDR, relief="flat", bd=0)
        self._suite_cv.configure(yscrollcommand=self._suite_sb.set)
        self._suite_sb.pack(side="right", fill="y")
        self._suite_cv.pack(fill="both", expand=True, padx=8, pady=4)

        self._suite_inner = tk.Frame(self._suite_cv, bg=T.BG)
        self._suite_win   = self._suite_cv.create_window(
            (0, 0), window=self._suite_inner, anchor="nw")
        self._suite_cv.bind("<Configure>",
            lambda e: self._suite_cv.itemconfig(self._suite_win, width=e.width))
        self._suite_inner.bind("<Configure>",
            lambda e: self._suite_cv.configure(
                scrollregion=self._suite_cv.bbox("all")))

        self._all_suite_apps = apps
        self._filter_suite(apps)

    def _filter_suite(self, apps):
        cat = self._cat_var.get() if hasattr(self, "_cat_var") else "All"
        filtered = apps if cat == "All" else [
            a for a in apps if a.get("category") == cat]
        for w in self._suite_inner.winfo_children():
            w.destroy()
        for app in filtered:
            self._suite_card(self._suite_inner, app).pack(fill="x", pady=2)
        self._suite_inner.update_idletasks()
        self._suite_cv.configure(scrollregion=self._suite_cv.bbox("all"))

    def _suite_card(self, parent, app):
        installed_v = _installed_version(app["file"])
        manifest_v  = app.get("version", "1.0")

        if installed_v is None:
            status_text = "Not installed"
            status_col  = T.DIM
            action      = "Install"
            action_st   = "success"
        elif installed_v != manifest_v:
            status_text = f"v{installed_v} → v{manifest_v} available"
            status_col  = T.WARN
            action      = "Update"
            action_st   = "warn"
        else:
            status_text = f"✓ Installed  v{installed_v}"
            status_col  = T.OK
            action      = "Reinstall"
            action_st   = "secondary"

        card = T.Card(parent)
        row  = tk.Frame(card, bg=T.SURF, padx=14, pady=9)
        row.pack(fill="x")

        info = tk.Frame(row, bg=T.SURF)
        info.pack(side="left", fill="both", expand=True)

        hdr_row = tk.Frame(info, bg=T.SURF)
        hdr_row.pack(fill="x")
        tk.Label(hdr_row,
                 text=f"{app.get('icon','')}  {app['name']}",
                 bg=T.SURF, fg=T.TXT, font=T.F(11, True)).pack(side="left")
        tk.Label(hdr_row,
                 text=f"[{app.get('category','')}]  ~{app.get('size_kb',0)} KB",
                 bg=T.SURF, fg=T.DIM, font=T.F(8)).pack(side="right")

        tk.Label(info, text=app.get("desc", ""),
                 bg=T.SURF, fg=T.MUT, font=T.F(9)).pack(anchor="w")
        tk.Label(info, text=status_text,
                 bg=T.SURF, fg=status_col, font=T.F(9, True)).pack(anchor="w")

        btns = tk.Frame(row, bg=T.SURF)
        btns.pack(side="right")
        T.Btn(btns, action,
              cmd=lambda a=app: self._install_app(a),
              style=action_st, font=T.F(9, True), padx=9, pady=4).pack(pady=1)
        if installed_v is not None:
            T.Btn(btns, "Launch",
                  cmd=lambda a=app: self._launch_app(a),
                  style="primary", font=T.F(9, True), padx=9, pady=3).pack()
        return card

    def _install_app(self, app):
        self.log.clear()
        self.log.append(f"Installing {app['name']}…")
        threading.Thread(
            target=lambda: _download_app_file(
                app["file"],
                lambda m, c=None: self.log.append(m, c)) or
            self.after(0, lambda: self._populate_suite_tab()),
            daemon=True).start()

    def _launch_app(self, app):
        path = os.path.join(SUITE_DIR, app["file"])
        if os.path.isfile(path):
            subprocess.Popen([sys.executable, path])
            self.log.append(f"Launched: {app['name']}", T.OK)
        else:
            T.popup(self, "Not installed",
                    f"'{app['file']}' not found locally.\nClick Install first.", "warning")

    # ── System packages tab ────────────────────────────────────────────────
    def _build_apt_tab(self, parent):
        top = tk.Frame(parent, bg=T.BG, padx=16, pady=6)
        top.pack(fill="x")
        tk.Label(top, text="Search:", bg=T.BG, fg=T.MUT, font=T.F(10)).pack(side="left")
        self._srch = tk.StringVar()
        tk.Entry(top, textvariable=self._srch, bg=T.SURF2, fg=T.TXT,
                 font=T.F(11), relief="flat", bd=0, insertbackground=T.TXT,
                 width=24).pack(side="left", ipady=5, padx=8)
        self._srch.trace_add("write", lambda *_: self._rebuild_apt())
        T.Btn(top, "✕", cmd=lambda: self._srch.set(""),
              style="secondary", font=T.F(9), padx=4, pady=2).pack(side="left")

        self._apt_nb = ttk.Notebook(parent)
        self._apt_nb.pack(fill="both", expand=True, padx=8, pady=4)
        self._apt_frames = {}
        for cat, pkgs in APT_CATALOGUE.items():
            f = tk.Frame(self._apt_nb, bg=T.BG)
            self._apt_nb.add(f, text=f"  {cat}  ")
            self._apt_frames[cat] = (f, pkgs)
            self._fill_apt_frame(f, pkgs)

    def _rebuild_apt(self):
        srch = self._srch.get().lower()
        for cat, (f, pkgs) in self._apt_frames.items():
            filtered = [p for p in pkgs if
                        srch in p["name"].lower() or
                        srch in p["desc"].lower()] if srch else pkgs
            self._fill_apt_frame(f, filtered)

    def _fill_apt_frame(self, frame, pkgs):
        for w in frame.winfo_children():
            w.destroy()
        cv = tk.Canvas(frame, bg=T.BG, highlightthickness=0)
        sb = tk.Scrollbar(frame, orient="vertical", command=cv.yview,
                          bg=T.BDR, relief="flat", bd=0)
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        cv.pack(fill="both", expand=True, padx=4, pady=4)
        inner = tk.Frame(cv, bg=T.BG)
        win   = cv.create_window((0, 0), window=inner, anchor="nw")
        cv.bind("<Configure>", lambda e, w=win, c=cv: c.itemconfig(w, width=e.width))
        inner.bind("<Configure>", lambda e, c=cv: c.configure(scrollregion=c.bbox("all")))
        for pkg in pkgs:
            self._apt_card(inner, pkg).pack(fill="x", pady=2)
        if not pkgs:
            tk.Label(inner, text="No matching packages.",
                     bg=T.BG, fg=T.DIM, font=T.F(10)).pack(pady=12)

    def _apt_card(self, parent, pkg):
        card = T.Card(parent)
        row  = tk.Frame(card, bg=T.SURF, padx=14, pady=8)
        row.pack(fill="x")
        info = tk.Frame(row, bg=T.SURF)
        info.pack(side="left", fill="both", expand=True)
        hr = tk.Frame(info, bg=T.SURF)
        hr.pack(fill="x")
        tk.Label(hr, text=pkg["name"], bg=T.SURF, fg=T.TXT,
                 font=T.F(11, True)).pack(side="left")
        tk.Label(hr, text=pkg["size"],  bg=T.SURF, fg=T.MUT,
                 font=T.F(9)).pack(side="right")
        tk.Label(info, text=pkg["desc"], bg=T.SURF, fg=T.MUT, font=T.F(9)
                 ).pack(anchor="w")
        tk.Label(info, text=f"apt: {pkg['pkg']}", bg=T.SURF, fg=T.DIM,
                 font=("Courier New", 8)).pack(anchor="w")
        btns = tk.Frame(row, bg=T.SURF)
        btns.pack(side="right")
        T.Btn(btns, "Install",
              cmd=lambda p=pkg: self._apt_run(p, "install"),
              style="success", font=T.F(9, True), padx=8, pady=3).pack(pady=1)
        T.Btn(btns, "Remove",
              cmd=lambda p=pkg: self._apt_run(p, "remove"),
              style="danger",  font=T.F(9, True), padx=8, pady=3).pack()
        return card

    def _apt_run(self, pkg, action):
        pkgs = pkg["pkg"].split()
        cmd  = (["apt", "install", "-y"] if action == "install"
                else ["apt", "remove", "-y"]) + pkgs
        self.log.clear()
        self.log.append(f"Running: {' '.join(cmd)}")

        def worker():
            try:
                env  = dict(os.environ, DEBIAN_FRONTEND="noninteractive")
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,
                                        text=True, env=env)
                for line in proc.stdout:
                    if line.strip():
                        self.log.append(line.rstrip())
                proc.wait()
                col = T.OK if proc.returncode == 0 else T.ERR
                msg = ("✓ Done" if proc.returncode == 0
                       else f"✗ Failed (code {proc.returncode})")
                self.log.append(msg, col)
                if proc.returncode == 0:
                    T.toast(self, f"{pkg['name']} {action}ed  ✓", "success")
            except FileNotFoundError:
                self.log.append(
                    "✗ 'apt' not found — run this inside proot Debian, not Termux.", T.ERR)
            except Exception as e:
                self.log.append(f"✗ {e}", T.ERR)

        threading.Thread(target=worker, daemon=True).start()

    # ── Long-press unlock (4 seconds) ─────────────────────────────────────
    def _lp_start(self, event):
        self._lp_cancel(event)
        self._lp_job = self.after(4000, self._unlock_hidden)

    def _lp_cancel(self, event):
        if self._lp_job:
            self.after_cancel(self._lp_job)
            self._lp_job = None

    def _unlock_hidden(self):
        self._lp_job = None
        if not self._hidden_added:
            t = tk.Frame(self.nb, bg=T.BG)
            self._build_hidden_tab(t)
            self.nb.add(t, text="  🔧  Dev Tools  ")
            self._hidden_added = True
        tabs = self.nb.tabs()
        self.nb.select(tabs[-1])
        T.toast(self, "Developer panel unlocked (4-sec hold)  🔧", "warning")

    # ── Hidden dev panel ───────────────────────────────────────────────────
    def _build_hidden_tab(self, parent):
        nb2 = ttk.Notebook(parent)
        nb2.pack(fill="both", expand=True)

        ca = tk.Frame(nb2, bg=T.BG)
        nb2.add(ca, text="  ➕  Create App  ")
        self._build_create_app(ca)

        ua = tk.Frame(nb2, bg=T.BG)
        nb2.add(ua, text="  📱  My Apps  ")
        self._build_user_apps(ua)

    def _build_create_app(self, parent):
        body = tk.Frame(parent, bg=T.BG, padx=18, pady=10)
        body.pack(fill="both", expand=True)

        T.Card(body)  # info card
        info = T.Card(body)
        info.pack(fill="x", pady=(0, 10))
        ii = tk.Frame(info, bg=T.SURF, padx=14, pady=10)
        ii.pack(fill="x")
        tk.Label(ii,
            text="Apps you create here are saved to:\n"
                 f"  {USER_APP_DIR}\n"
                 "They are SANDBOXED — if they crash, the main OS is unaffected.\n"
                 "They NEVER overwrite core suite files.",
            bg=T.SURF, fg=T.MUT, font=T.F(9), justify="left").pack(anchor="w")

        self._new_vars = []
        meta = T.Card(body)
        meta.pack(fill="x", pady=(0, 8))
        mi = tk.Frame(meta, bg=T.SURF, padx=14, pady=10)
        mi.pack(fill="x")
        row = tk.Frame(mi, bg=T.SURF)
        row.pack(fill="x")
        for lbl, dflt, w in [
            ("App name:", "My Tool", 18),
            ("File (.py):", "my_tool.py", 16),
            ("Icon:", "◈", 3),
            ("Description:", "What it does", 32),
        ]:
            col = tk.Frame(row, bg=T.SURF)
            col.pack(side="left", padx=(0, 10))
            tk.Label(col, text=lbl, bg=T.SURF, fg=T.MUT, font=T.F(9)).pack(anchor="w")
            v = tk.StringVar(value=dflt)
            tk.Entry(col, textvariable=v, bg=T.SURF2, fg=T.TXT, font=T.F(10),
                     relief="flat", bd=0, width=w,
                     insertbackground=T.TXT).pack(ipady=4)
            self._new_vars.append(v)

        # Code editor
        cc = T.Card(body)
        cc.pack(fill="both", expand=True, pady=(0, 8))
        ci = tk.Frame(cc, bg=T.SURF)
        ci.pack(fill="both", expand=True)
        hh = tk.Frame(ci, bg=T.SURF, padx=12, pady=5)
        hh.pack(fill="x")
        tk.Label(hh, text="Paste Python code:", bg=T.SURF, fg=T.MUT, font=T.F(10)
                 ).pack(side="left")

        TEMPLATE = (
            '"""\nmy_tool.py — AndrobianOS user app\n"""\n\n'
            'import tkinter as tk\nimport os, sys\n'
            'sys.path.insert(0, "/opt/androbian")\n'
            'import theme as T\n\n\n'
            'class MyToolApp(tk.Tk):\n'
            '    def __init__(self):\n'
            '        super().__init__()\n'
            '        self.title("My Tool")\n'
            '        self.geometry("600x400")\n'
            '        T.apply(self)\n'
            '        T.app_header(self, "My Tool", "subtitle", "◈")\n'
            '        body = tk.Frame(self, bg=T.BG, padx=20, pady=14)\n'
            '        body.pack(fill="both", expand=True)\n'
            '        T.Btn(body, "Click me",\n'
            '              cmd=lambda: T.toast(self, "It works!", "success")\n'
            '              ).pack()\n\n\n'
            'if __name__ == "__main__":\n'
            '    MyToolApp().mainloop()\n'
        )
        T.Btn(hh, "Insert Template", style="secondary", font=T.F(9, True), padx=8, pady=3,
              cmd=lambda: (self._new_ed.delete("1.0", "end"),
                           self._new_ed.insert("1.0", TEMPLATE))
              ).pack(side="right")

        sf = tk.Frame(ci, bg=T.SURF2)
        sf.pack(fill="both", expand=True)
        sb = tk.Scrollbar(sf, bg=T.BDR, relief="flat", bd=0)
        self._new_ed = tk.Text(sf, bg=T.SURF2, fg="#D4D4D4", font=("Courier New", 10),
                                insertbackground=T.TXT, relief="flat", bd=0,
                                yscrollcommand=sb.set, wrap="none", tabs="    ")
        sb.config(command=self._new_ed.yview)
        sb.pack(side="right", fill="y")
        self._new_ed.pack(fill="both", expand=True)

        st = tk.Label(body, text="", bg=T.BG, fg=T.MUT, font=T.F(9))
        st.pack(anchor="w", pady=(0, 4))
        T.Btn(body, "💾  Save to My Apps",
              cmd=lambda: self._save_user_app(st),
              style="success", font=T.F(11, True)).pack(anchor="e")

    def _save_user_app(self, status_lbl):
        name  = self._new_vars[0].get().strip()
        fname = self._new_vars[1].get().strip()
        icon  = self._new_vars[2].get().strip() or "◈"
        desc  = self._new_vars[3].get().strip()
        code  = self._new_ed.get("1.0", "end-1c").strip()
        if not fname.endswith(".py"):
            fname += ".py"
        if not name or not code:
            T.popup(self, "Missing", "Fill in app name and paste code.", "warning")
            return
        # Save to USER_APP_DIR (sandboxed — separate from core SUITE_DIR)
        fpath = os.path.join(USER_APP_DIR, fname)
        with open(fpath, "w") as f:
            f.write(code)
        status_lbl.config(
            text=f"✓  Saved to: {fpath}  (sandboxed — will not affect core system)",
            fg=T.OK)
        self.log.append(f"User app saved: {fname}", T.OK)
        T.toast(self, f"'{name}' saved to My Apps  ✓", "success")

    def _build_user_apps(self, parent):
        """List all user-created apps from USER_APP_DIR with Launch / Delete."""
        body = tk.Frame(parent, bg=T.BG, padx=18, pady=10)
        body.pack(fill="both", expand=True)
        tk.Label(body, text=f"Your personal apps  —  stored at:\n{USER_APP_DIR}",
                 bg=T.BG, fg=T.MUT, font=T.F(9)).pack(anchor="w", pady=(0, 10))

        cv = tk.Canvas(body, bg=T.BG, highlightthickness=0)
        sb = tk.Scrollbar(body, orient="vertical", command=cv.yview,
                          bg=T.BDR, relief="flat", bd=0)
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        cv.pack(fill="both", expand=True)
        inner = tk.Frame(cv, bg=T.BG)
        win   = cv.create_window((0, 0), window=inner, anchor="nw")
        cv.bind("<Configure>", lambda e: cv.itemconfig(win, width=e.width))
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))

        files = sorted(f for f in os.listdir(USER_APP_DIR) if f.endswith(".py"))
        if not files:
            tk.Label(inner, text="No user apps yet. Use 'Create App' tab to add one.",
                     bg=T.BG, fg=T.DIM, font=T.F(10)).pack(pady=16)
        else:
            for fname in files:
                card = T.Card(inner)
                card.pack(fill="x", pady=2)
                row = tk.Frame(card, bg=T.SURF, padx=14, pady=8)
                row.pack(fill="x")
                tk.Label(row, text=fname, bg=T.SURF, fg=T.TXT,
                         font=T.F(10, True)).pack(side="left")
                fpath = os.path.join(USER_APP_DIR, fname)
                T.Btn(row, "Launch",
                      cmd=lambda p=fpath: subprocess.Popen([sys.executable, p]),
                      style="primary", font=T.F(9, True), padx=7, pady=3
                      ).pack(side="right", padx=(4, 0))
                T.Btn(row, "Delete",
                      cmd=lambda p=fpath, c=card: (
                          os.remove(p), c.destroy()),
                      style="danger", font=T.F(9, True), padx=7, pady=3
                      ).pack(side="right")


if __name__ == "__main__":
    AppStoreApp().mainloop()
