"""
settings.py — Joydip's Linux Suite
Desktop settings panel:
  • Wallpaper — pick any image file, apply instantly
  • Theme — macOS Dark / macOS Light / Windows Classic (minimal storage)
  • Time & Date — sync with Android time or set manually
  • Display — font size, icon size, compositor toggle
"""

import tkinter as tk
from tkinter import ttk, filedialog, colorchooser
import os, sys, subprocess, threading, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import theme as T

APPS_DIR   = os.path.dirname(os.path.abspath(__file__))
THEME_FILE = os.path.join(APPS_DIR, "theme.py")

# ─── Built-in colour themes (light on storage — just hex values) ──────────────
# Each theme overrides the 10 colour tokens in theme.py
THEMES = {
    "macOS Dark (default)": {
        "BG":   "#0F1117", "SURF":  "#181C25", "SURF2": "#1F2432",
        "BDR":  "#2C3044", "ACC":   "#4F8EF7", "TXT":   "#E8EAF0",
        "MUT":  "#7A8099", "DIM":   "#3A3F52", "OK":    "#4EBF85",
        "WARN": "#E8A838", "ERR":   "#D95F6E",
    },
    "macOS Light": {
        "BG":   "#F5F5F7", "SURF":  "#FFFFFF", "SURF2": "#EBEBED",
        "BDR":  "#D0D0D5", "ACC":   "#007AFF", "TXT":   "#1D1D1F",
        "MUT":  "#6E6E73", "DIM":   "#C7C7CC", "OK":    "#30B16C",
        "WARN": "#F5A623", "ERR":   "#D32F2F",
    },
    "Windows 11 Dark": {
        "BG":   "#202020", "SURF":  "#2D2D2D", "SURF2": "#383838",
        "BDR":  "#484848", "ACC":   "#0078D4", "TXT":   "#FFFFFF",
        "MUT":  "#AAAAAA", "DIM":   "#555555", "OK":    "#13A10E",
        "WARN": "#FFA500", "ERR":   "#E81123",
    },
    "Windows 11 Light": {
        "BG":   "#F3F3F3", "SURF":  "#FFFFFF", "SURF2": "#EBEBEB",
        "BDR":  "#D0D0D0", "ACC":   "#0078D4", "TXT":   "#1A1A1A",
        "MUT":  "#767676", "DIM":   "#C8C8C8", "OK":    "#107C10",
        "WARN": "#FF8C00", "ERR":   "#E81123",
    },
    "AMOLED Black": {
        "BG":   "#000000", "SURF":  "#0A0A0A", "SURF2": "#111111",
        "BDR":  "#1A1A1A", "ACC":   "#00B4FF", "TXT":   "#FFFFFF",
        "MUT":  "#666666", "DIM":   "#222222", "OK":    "#00CC66",
        "WARN": "#FFAA00", "ERR":   "#FF4444",
    },
}


class SettingsApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Settings — Joydip's Suite")
        self.geometry("760x580")
        self.minsize(640, 460)
        T.apply(self)
        self._centre()
        self._build()

    def _centre(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"760x580+{(sw-760)//2}+{(sh-580)//2}")

    def _build(self):
        T.app_header(self, "Settings", "Wallpaper · Theme · Time & Date · Display", "⚙")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        tabs = [
            ("  🖼  Wallpaper  ",  self._build_wallpaper),
            ("  🎨  Theme  ",      self._build_theme),
            ("  🕐  Time & Date  ", self._build_time),
            ("  🔤  Display  ",    self._build_display),
        ]
        for name, builder in tabs:
            t = tk.Frame(nb, bg=T.BG)
            nb.add(t, text=name)
            builder(t)

        T.Divider(self).pack(fill="x")
        self.status = tk.Label(self, text="", bg=T.BG, fg=T.MUT, font=T.F(9))
        self.status.pack(anchor="w", padx=18, pady=6)

    # ── Wallpaper ─────────────────────────────────────────────────────────────
    def _build_wallpaper(self, parent):
        body = tk.Frame(parent, bg=T.BG, padx=20, pady=14)
        body.pack(fill="both", expand=True)

        info_card = T.Card(body)
        info_card.pack(fill="x", pady=(0, 10))
        ii = tk.Frame(info_card, bg=T.SURF, padx=14, pady=10)
        ii.pack(fill="x")
        tk.Label(ii,
                 text="Select any image file (PNG, JPG, BMP) to use as the desktop wallpaper.\n"
                      "Uses 'feh' if installed, falls back to 'nitrogen' or 'xsetroot'.",
                 bg=T.SURF, fg=T.MUT, font=T.F(10),
                 justify="left").pack(anchor="w")

        pick_row = tk.Frame(body, bg=T.BG)
        pick_row.pack(fill="x", pady=(0, 10))
        self._wp_path = tk.StringVar(value="No wallpaper selected")
        tk.Entry(pick_row, textvariable=self._wp_path,
                 bg=T.SURF2, fg=T.MUT, font=T.F(10),
                 relief="flat", bd=0, state="readonly"
                 ).pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 10))
        T.Btn(pick_row, "Browse Image",
              cmd=self._pick_wallpaper, style="secondary",
              font=T.F(10, True)).pack(side="right")

        # Mode
        mode_card = T.Card(body)
        mode_card.pack(fill="x", pady=(0, 10))
        mi = tk.Frame(mode_card, bg=T.SURF, padx=14, pady=10)
        mi.pack(fill="x")
        tk.Label(mi, text="Scaling mode:", bg=T.SURF, fg=T.MUT, font=T.F(10)
                 ).pack(anchor="w", pady=(0, 6))
        self._wp_mode = tk.StringVar(value="--bg-fill")
        for label, val in [
            ("Fill (crop to fit)",  "--bg-fill"),
            ("Scale (stretch)",     "--bg-scale"),
            ("Center (no stretch)", "--bg-center"),
            ("Tile (repeat)",       "--bg-tile"),
        ]:
            tk.Radiobutton(mi, text=label, variable=self._wp_mode, value=val,
                           bg=T.SURF, fg=T.TXT, selectcolor=T.SURF2,
                           activebackground=T.SURF, font=T.F(10)
                           ).pack(anchor="w")

        T.Btn(body, "Apply Wallpaper",
              cmd=self._apply_wallpaper, style="primary",
              font=T.F(11, True)).pack(anchor="w", pady=(6, 0))

        # Also show a note about saving wallpaper across reboots
        T.Divider(body).pack(fill="x", pady=10)
        tk.Label(body,
                 text="To make the wallpaper persist after reboot, add the apply command\n"
                      "to  ~/.config/openbox/autostart  (the Edit button adds it automatically).",
                 bg=T.BG, fg=T.DIM, font=T.F(9), justify="left").pack(anchor="w")
        T.Btn(body, "Add to Autostart",
              cmd=self._save_wp_autostart, style="secondary",
              font=T.F(9, True), padx=8, pady=3).pack(anchor="w", pady=(4, 0))

    def _pick_wallpaper(self):
        f = filedialog.askopenfilename(
            title="Select wallpaper image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.tiff *.webp"),
                       ("All files", "*.*")])
        if f:
            self._wp_path.set(f)

    def _apply_wallpaper(self):
        path = self._wp_path.get()
        if not os.path.isfile(path):
            T.popup(self, "No file", "Select an image file first.", "warning")
            return
        mode = self._wp_mode.get()
        # Try feh first, then nitrogen, then xsetroot
        for cmd in [
            ["feh", mode, path],
            ["nitrogen", "--set-auto", path],
            ["xsetroot", "-bitmap", path],
        ]:
            try:
                subprocess.Popen(cmd)
                self.status.config(text=f"✓  Wallpaper applied using: {cmd[0]}", fg=T.OK)
                return
            except FileNotFoundError:
                continue
        T.popup(self, "No wallpaper tool",
                "Install feh first:\n  apt install feh\nor:\n  apt install nitrogen",
                "warning")

    def _save_wp_autostart(self):
        path = self._wp_path.get()
        if not os.path.isfile(path):
            T.popup(self, "No file", "Select and apply a wallpaper first.", "warning")
            return
        mode    = self._wp_mode.get()
        line    = f"feh {mode} '{path}' &\n"
        autostart = os.path.expanduser("~/.config/openbox/autostart")
        os.makedirs(os.path.dirname(autostart), exist_ok=True)
        # Avoid duplicate entries
        existing = open(autostart).read() if os.path.exists(autostart) else ""
        if "feh" in existing:
            # Replace existing feh line
            lines = [l for l in existing.splitlines() if "feh" not in l]
            lines.append(line.strip())
            with open(autostart, "w") as f:
                f.write("\n".join(lines) + "\n")
        else:
            with open(autostart, "a") as f:
                f.write(line)
        self.status.config(text="✓  Wallpaper command added to autostart.", fg=T.OK)

    # ── Theme ─────────────────────────────────────────────────────────────────
    def _build_theme(self, parent):
        body = tk.Frame(parent, bg=T.BG, padx=20, pady=14)
        body.pack(fill="both", expand=True)

        tk.Label(body,
                 text="Selecting a theme rewrites the colour tokens in theme.py.\n"
                      "All apps use the new colours on their next launch.",
                 bg=T.BG, fg=T.MUT, font=T.F(10)).pack(anchor="w", pady=(0, 10))

        # Theme cards
        self._theme_var = tk.StringVar(value="macOS Dark (default)")
        for name, colours in THEMES.items():
            card = T.Card(body)
            card.pack(fill="x", pady=3)
            row = tk.Frame(card, bg=T.SURF, padx=14, pady=8)
            row.pack(fill="x")

            tk.Radiobutton(row, text=name, variable=self._theme_var, value=name,
                           bg=T.SURF, fg=T.TXT, selectcolor=T.SURF2,
                           activebackground=T.SURF, font=T.F(11, True)
                           ).pack(side="left")

            # Show a colour swatch row
            swatches = tk.Frame(row, bg=T.SURF)
            swatches.pack(side="left", padx=16)
            for key in ("BG", "SURF", "ACC", "TXT", "OK"):
                col = colours[key]
                tk.Frame(swatches, bg=col, width=22, height=22,
                         bd=1, relief="solid").pack(side="left", padx=1)

        T.Divider(body).pack(fill="x", pady=10)
        T.Btn(body, "🎨  Apply Theme",
              cmd=self._apply_theme, style="primary",
              font=T.F(11, True)).pack(anchor="w")

        tk.Label(body,
                 text="Tip: After applying a theme, restart the apps you have open.",
                 bg=T.BG, fg=T.DIM, font=T.F(9)).pack(anchor="w", pady=(6, 0))

    def _apply_theme(self):
        name    = self._theme_var.get()
        colours = THEMES[name]
        if not os.path.isfile(THEME_FILE):
            T.popup(self, "Not found", f"theme.py not found at:\n{THEME_FILE}", "error")
            return

        with open(THEME_FILE, "r") as f:
            code = f.read()

        # Replace each colour token line
        import re
        for token, value in colours.items():
            code = re.sub(
                rf'^({token}\s*=\s*")[^"]*(")',
                rf'\g<1>{value}\g<2>',
                code, flags=re.MULTILINE
            )

        with open(THEME_FILE, "w") as f:
            f.write(code)

        self.status.config(text=f"✓  Theme '{name}' applied. Restart apps to see changes.", fg=T.OK)
        T.toast(self, f"Theme '{name}' saved  ✓", "success")

    # ── Time & Date ───────────────────────────────────────────────────────────
    def _build_time(self, parent):
        body = tk.Frame(parent, bg=T.BG, padx=20, pady=14)
        body.pack(fill="both", expand=True)

        # Current time display
        time_card = T.Card(body)
        time_card.pack(fill="x", pady=(0, 10))
        ti = tk.Frame(time_card, bg=T.SURF, padx=14, pady=12)
        ti.pack(fill="x")
        tk.Label(ti, text="Current system time:", bg=T.SURF, fg=T.MUT, font=T.F(10)
                 ).pack(anchor="w")
        self._cur_time_lbl = tk.Label(ti, text="", bg=T.SURF, fg=T.ACC,
                                       font=T.F(14, True))
        self._cur_time_lbl.pack(anchor="w", pady=(4, 0))
        self._update_clock()

        # Sync with Android hardware clock
        sync_card = T.Card(body)
        sync_card.pack(fill="x", pady=(0, 10))
        si = tk.Frame(sync_card, bg=T.SURF, padx=14, pady=12)
        si.pack(fill="x")
        tk.Label(si, text="Sync with Android time:",
                 bg=T.SURF, fg=T.MUT, font=T.F(10)).pack(anchor="w", pady=(0, 6))
        tk.Label(si,
                 text="This reads the Android hardware clock (which is always accurate)\n"
                      "and sets the Linux system clock to match it.",
                 bg=T.SURF, fg=T.DIM, font=T.F(9), justify="left").pack(anchor="w", pady=(0, 8))
        T.Btn(si, "⟳  Sync with Android Clock",
              cmd=self._sync_android_time,
              style="primary", font=T.F(10, True)).pack(anchor="w")

        # Manual time set
        man_card = T.Card(body)
        man_card.pack(fill="x", pady=(0, 10))
        mi = tk.Frame(man_card, bg=T.SURF, padx=14, pady=12)
        mi.pack(fill="x")
        tk.Label(mi, text="Set manually:", bg=T.SURF, fg=T.MUT, font=T.F(10)
                 ).pack(anchor="w", pady=(0, 6))

        dt_row = tk.Frame(mi, bg=T.SURF)
        dt_row.pack(fill="x")
        self._man_vars = {}
        now = datetime.datetime.now()
        for lbl, key, dflt, w in [
            ("Year:",   "year",  str(now.year),   6),
            ("Month:",  "month", f"{now.month:02d}", 4),
            ("Day:",    "day",   f"{now.day:02d}",   4),
            ("Hour:",   "hour",  f"{now.hour:02d}",  4),
            ("Minute:", "min",   f"{now.minute:02d}", 4),
            ("Second:", "sec",   f"{now.second:02d}", 4),
        ]:
            col = tk.Frame(dt_row, bg=T.SURF)
            col.pack(side="left", padx=(0, 10))
            tk.Label(col, text=lbl, bg=T.SURF, fg=T.MUT, font=T.F(9)).pack(anchor="w")
            v = tk.StringVar(value=dflt)
            tk.Entry(col, textvariable=v, bg=T.SURF2, fg=T.TXT, font=T.F(10),
                     relief="flat", bd=0, width=w,
                     insertbackground=T.TXT).pack(ipady=4)
            self._man_vars[key] = v

        T.Btn(mi, "Set Time", cmd=self._set_manual_time,
              style="secondary", font=T.F(10, True), padx=9, pady=4
              ).pack(anchor="w", pady=(8, 0))

        # Timezone
        tz_card = T.Card(body)
        tz_card.pack(fill="x")
        tzi = tk.Frame(tz_card, bg=T.SURF, padx=14, pady=10)
        tzi.pack(fill="x")
        tk.Label(tzi, text="Timezone:", bg=T.SURF, fg=T.MUT, font=T.F(10)
                 ).pack(anchor="w", pady=(0, 4))
        tz_row = tk.Frame(tzi, bg=T.SURF)
        tz_row.pack(fill="x")
        self._tz_var = tk.StringVar(value="Asia/Kolkata")
        common_tzs = ["Asia/Kolkata", "Asia/Kolkata", "UTC", "Asia/Dhaka",
                      "America/New_York", "Europe/London", "Asia/Singapore"]
        ttk.Combobox(tz_row, textvariable=self._tz_var,
                     values=common_tzs, width=24).pack(side="left")
        T.Btn(tz_row, "Apply Timezone",
              cmd=self._apply_tz, style="secondary",
              font=T.F(9, True), padx=8, pady=3).pack(side="left", padx=8)

    def _update_clock(self):
        now = datetime.datetime.now()
        self._cur_time_lbl.config(
            text=now.strftime("%A, %d %B %Y  —  %H:%M:%S"))
        self.after(1000, self._update_clock)

    def _sync_android_time(self):
        """
        Inside Termux/proot, 'hwclock --hctosys' reads the hardware clock.
        Alternative: parse 'date' from Android via termux-api.
        """
        try:
            result = subprocess.run(
                ["hwclock", "--hctosys"],
                capture_output=True, text=True)
            if result.returncode == 0:
                self.status.config(text="✓  Synced with hardware clock.", fg=T.OK)
            else:
                # Try setting from Android via termux-api
                ts = subprocess.run(
                    ["termux-battery-status"],  # any termux-api call
                    capture_output=True, text=True)
                # fallback: use NTP
                subprocess.Popen(["ntpdate", "-u", "pool.ntp.org"])
                self.status.config(text="→  Using NTP sync (hwclock unavailable in proot).", fg=T.WARN)
        except FileNotFoundError:
            subprocess.Popen(["chronyd", "-q"])
            self.status.config(
                text="→  Note: Hardware clock sync not available inside proot.\n"
                     "   Linux inherits Android's time automatically — no manual sync needed.",
                fg=T.WARN)

    def _set_manual_time(self):
        try:
            y  = self._man_vars["year"].get()
            mo = self._man_vars["month"].get()
            d  = self._man_vars["day"].get()
            h  = self._man_vars["hour"].get()
            mi = self._man_vars["min"].get()
            s  = self._man_vars["sec"].get()
            # Format: MMDDhhmm[[CC]YY][.ss]
            result = subprocess.run(
                ["date", f"{mo}{d}{h}{mi}{y}.{s}"],
                capture_output=True, text=True)
            if result.returncode == 0:
                self.status.config(text=f"✓  Time set to {y}-{mo}-{d} {h}:{mi}:{s}", fg=T.OK)
            else:
                self.status.config(text=f"✗  {result.stderr.strip()}", fg=T.ERR)
        except Exception as e:
            self.status.config(text=f"Error: {e}", fg=T.ERR)

    def _apply_tz(self):
        tz = self._tz_var.get()
        try:
            r = subprocess.run(["timedatectl", "set-timezone", tz],
                               capture_output=True, text=True)
            if r.returncode == 0:
                self.status.config(text=f"✓  Timezone set to {tz}", fg=T.OK)
            else:
                # Manual fallback
                os.makedirs("/etc", exist_ok=True)
                zone_file = f"/usr/share/zoneinfo/{tz}"
                if os.path.isfile(zone_file):
                    subprocess.run(["ln", "-sf", zone_file, "/etc/localtime"])
                    self.status.config(text=f"✓  Timezone linked: {tz}", fg=T.OK)
                else:
                    self.status.config(text=f"✗  Zone file not found: {zone_file}", fg=T.ERR)
        except Exception as e:
            self.status.config(text=f"Error: {e}", fg=T.ERR)

    # ── Display ───────────────────────────────────────────────────────────────
    def _build_display(self, parent):
        body = tk.Frame(parent, bg=T.BG, padx=20, pady=14)
        body.pack(fill="both", expand=True)

        # Compositor (picom) toggle
        comp_card = T.Card(body)
        comp_card.pack(fill="x", pady=(0, 10))
        ci = tk.Frame(comp_card, bg=T.SURF, padx=14, pady=12)
        ci.pack(fill="x")
        tk.Label(ci, text="Compositor (picom) — rounded corners + transparency:",
                 bg=T.SURF, fg=T.MUT, font=T.F(10)).pack(anchor="w", pady=(0, 8))
        btn_row = tk.Frame(ci, bg=T.SURF)
        btn_row.pack(anchor="w")
        T.Btn(btn_row, "Start Compositor",
              cmd=lambda: subprocess.Popen(
                  ["picom", "--config", "/etc/picom.conf"]) or
                  self.status.config(text="✓  Compositor started.", fg=T.OK),
              style="success", font=T.F(10, True)).pack(side="left", padx=(0, 8))
        T.Btn(btn_row, "Stop Compositor",
              cmd=lambda: subprocess.run(["pkill", "picom"]) or
                  self.status.config(text="Compositor stopped.", fg=T.WARN),
              style="secondary", font=T.F(10, True)).pack(side="left")

        # Corner radius
        cr_card = T.Card(body)
        cr_card.pack(fill="x", pady=(0, 10))
        cri = tk.Frame(cr_card, bg=T.SURF, padx=14, pady=12)
        cri.pack(fill="x")
        tk.Label(cri, text="Window corner radius (requires compositor):",
                 bg=T.SURF, fg=T.MUT, font=T.F(10)).pack(anchor="w", pady=(0, 6))
        self._corner_s = T.Slider(cri, "Corner radius", 0, 24, 10,
                                   fmt="{:.0f}", suffix=" px", bg=T.SURF, resolution=1)
        self._corner_s.pack(fill="x")
        T.Btn(cri, "Apply Corner Radius",
              cmd=self._apply_corner_radius,
              style="secondary", font=T.F(9, True), padx=8, pady=3
              ).pack(anchor="w", pady=(6, 0))

        # Panel opacity
        op_card = T.Card(body)
        op_card.pack(fill="x", pady=(0, 10))
        oi = tk.Frame(op_card, bg=T.SURF, padx=14, pady=12)
        oi.pack(fill="x")
        tk.Label(oi, text="Inactive window opacity:", bg=T.SURF, fg=T.MUT, font=T.F(10)
                 ).pack(anchor="w", pady=(0, 6))
        self._opacity_s = T.Slider(oi, "Opacity", 50, 100, 96,
                                    fmt="{:.0f}", suffix="%", bg=T.SURF, resolution=1)
        self._opacity_s.pack(fill="x")
        T.Btn(oi, "Apply Opacity",
              cmd=self._apply_opacity,
              style="secondary", font=T.F(9, True), padx=8, pady=3
              ).pack(anchor="w", pady=(6, 0))

    def _apply_corner_radius(self):
        r    = int(self._corner_s.get())
        conf = "/etc/picom.conf"
        if not os.path.isfile(conf):
            T.popup(self, "Not found",
                    f"picom.conf not found at {conf}\n"
                    "Copy it there: sudo cp /opt/joydip_suite/picom.conf /etc/picom.conf",
                    "warning")
            return
        import re
        with open(conf) as f:
            text = f.read()
        text = re.sub(r"corner-radius\s*=\s*\d+", f"corner-radius = {r}", text)
        with open(conf, "w") as f:
            f.write(text)
        # Restart picom
        subprocess.run(["pkill", "picom"])
        import time; time.sleep(0.3)
        subprocess.Popen(["picom", "--config", conf])
        self.status.config(text=f"✓  Corner radius set to {r}px and compositor restarted.", fg=T.OK)

    def _apply_opacity(self):
        op   = self._opacity_s.get() / 100.0
        conf = "/etc/picom.conf"
        if not os.path.isfile(conf):
            T.popup(self, "Not found", f"picom.conf not found at {conf}", "warning")
            return
        import re
        with open(conf) as f:
            text = f.read()
        text = re.sub(r"inactive-opacity\s*=\s*[\d.]+",
                      f"inactive-opacity = {op:.2f}", text)
        with open(conf, "w") as f:
            f.write(text)
        subprocess.run(["pkill", "picom"])
        import time; time.sleep(0.3)
        subprocess.Popen(["picom", "--config", conf])
        self.status.config(text=f"✓  Opacity set to {int(op*100)}%.", fg=T.OK)


if __name__ == "__main__":
    SettingsApp().mainloop()
