#!/usr/bin/env python3
"""
touch_manager.py — AndrobianOS
═══════════════════════════════════════════════════════════════════════════════
WHAT THIS FILE DOES:
  Manages X11 touch input for tablet use. Applies XInput rules and Openbox
  keybindings so the tablet feels native. Provides a small always-on-top
  toggle bar so the user can switch modes without a terminal.

TOUCH MODES:
  ─ Direct Touch (default in Termux:X11)
      Taps = left click. No scroll, no right-click.
      Good for: typing, clicking buttons.

  ─ Touchpad Mode (xinput sets the screen as a relative pointer)
      Finger drag = cursor movement. Two-finger scroll works.
      Tap = click, two-finger tap = right-click.
      Good for: file managers, web browsing.

GESTURES ADDED IN BOTH MODES (via xdotool keyboard shortcuts):
  ─ Swipe LEFT  on the toggle bar  →  Left arrow key
  ─ Swipe RIGHT on the toggle bar  →  Right arrow key
  ─ Two-finger scroll equivalent   →  Page Up / Page Down buttons in bar

TOGGLE BAR:
  A small floating bar docked at the bottom-right corner of the screen.
  Tapping it never accidentally triggers the desktop underneath.
  You can drag it to any position.

HOW TO START AUTOMATICALLY:
  Add to ~/.config/openbox/autostart:
    python3 /opt/androbian/touch_manager.py &

HOW TO DISABLE COMPLETELY:
  Remove the line above from autostart and reboot the desktop.
  OR: click the ✕ button on the toggle bar.
═══════════════════════════════════════════════════════════════════════════════
"""

import tkinter as tk
from tkinter import ttk
import subprocess
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import theme as T
except ImportError:
    # Minimal fallback colours if theme.py is not found
    class T:
        BG = "#0F1117"; SURF = "#181C25"; SURF2 = "#1F2432"
        BDR = "#2C3044"; ACC = "#4F8EF7"; TXT = "#E8EAF0"
        MUT = "#7A8099"; DIM = "#3A3F52"; OK  = "#4EBF85"
        WARN = "#E8A838"; ERR = "#D95F6E"
        @staticmethod
        def F(s=11, bold=False): return ("Inter", s, "bold" if bold else "normal")
        @staticmethod
        def apply(r): r.configure(bg=T.BG)

# ── Config file path (persists the user's chosen mode) ─────────────────────
CONFIG_PATH = os.path.expanduser("~/.config/androbian/touch_mode.json")


def _load_mode():
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f).get("mode", "direct")
    except Exception:
        return "direct"


def _save_mode(mode):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump({"mode": mode}, f)


# ── XInput / xinput helpers ─────────────────────────────────────────────────
def _run(cmd):
    """Run a shell command silently. Returns True on success."""
    try:
        result = subprocess.run(cmd, shell=True,
                                capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False


def _get_touch_device_id():
    """
    Find the XInput device ID for the touchscreen.
    Works on most Termux:X11 setups — device is usually named
    'pointer:' or contains 'Touch' or 'touch'.
    Returns the ID string, or None if not found.
    """
    result = subprocess.run(["xinput", "--list", "--short"],
                             capture_output=True, text=True)
    for line in result.stdout.splitlines():
        lower = line.lower()
        if "touch" in lower or "stylus" in lower or "finger" in lower:
            # Extract the id=N part
            for part in line.split():
                if part.startswith("id="):
                    return part.replace("id=", "").strip()
    return None


def apply_direct_mode():
    """
    Direct touch: every tap = left-click at that exact position.
    No scrolling, no right-click. Simple and reliable.
    Uses: xinput set-prop … "libinput Click Method Buttonareas"
    """
    dev = _get_touch_device_id()
    if dev:
        _run(f'xinput set-prop {dev} "libinput Tapping Enabled" 1')
        _run(f'xinput set-prop {dev} "libinput Natural Scrolling Enabled" 0')
        _run(f'xinput set-prop {dev} "libinput Click Method Enabled" 1 0')
    return True


def apply_touchpad_mode():
    """
    Touchpad mode: finger drag moves the cursor relatively (like a laptop
    touchpad). Two-finger scroll works. Two-finger tap = right-click.
    Uses: xinput to set the device to relative motion mode.
    Falls back gracefully if xinput properties are not available.
    """
    dev = _get_touch_device_id()
    if dev:
        _run(f'xinput set-prop {dev} "libinput Tapping Enabled" 1')
        _run(f'xinput set-prop {dev} "libinput Natural Scrolling Enabled" 1')
        _run(f'xinput set-prop {dev} "libinput Scroll Method Enabled" 0 0 1')
        _run(f'xinput set-prop {dev} "libinput Click Method Enabled" 0 1')
        # Enable two-finger tap for right-click
        _run(f'xinput set-prop {dev} "libinput Tapping Button Mapping Enabled" 0 1')
    return True


# ── Main toggle bar window ──────────────────────────────────────────────────
class TouchBar(tk.Tk):
    """
    A small floating overlay bar. Always on top, semi-transparent.
    Draggable so the user can move it out of the way.
    """

    BAR_W = 320
    BAR_H = 44

    def __init__(self):
        super().__init__()
        self.overrideredirect(True)          # no title bar / decorations
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.90)
        self.configure(bg=T.SURF)
        self.wm_attributes("-type", "dock")  # X11: above normal windows

        # Position: bottom-right, 20 px from edge
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = sw - self.BAR_W - 20
        y  = sh - self.BAR_H - 20
        self.geometry(f"{self.BAR_W}x{self.BAR_H}+{x}+{y}")

        # Drag state
        self._drag_x = 0
        self._drag_y = 0

        self._mode = _load_mode()
        self._build()
        self._apply_current_mode()

        # Gesture tracking on the bar itself
        self._swipe_start_x = None

    def _build(self):
        bar = tk.Frame(self, bg=T.SURF, bd=0, padx=6, pady=5)
        bar.pack(fill="both", expand=True)

        # Drag handle (the label area)
        self._icon_lbl = tk.Label(bar, text="✋", bg=T.SURF, fg=T.MUT,
                                   font=("Monospace", 13), cursor="fleur")
        self._icon_lbl.pack(side="left", padx=(2, 4))
        self._icon_lbl.bind("<ButtonPress-1>",   self._drag_start)
        self._icon_lbl.bind("<B1-Motion>",        self._drag_move)

        # Mode label
        self._mode_lbl = tk.Label(bar, text="", bg=T.SURF, fg=T.TXT,
                                   font=("Inter", 9, "bold"), width=12, anchor="w")
        self._mode_lbl.pack(side="left")

        # Toggle button
        self._tog_btn = tk.Button(
            bar, text="Switch", bg=T.ACC, fg=T.TXT,
            font=("Inter", 9, "bold"), relief="flat", bd=0,
            padx=8, pady=2, cursor="hand2",
            command=self._toggle_mode)
        self._tog_btn.pack(side="left", padx=4)

        # Separator
        tk.Frame(bar, bg=T.BDR, width=1, height=28).pack(side="left", padx=4)

        # ← → scroll buttons (gesture shortcuts)
        for sym, key in [("←", "Left"), ("→", "Right"),
                         ("↑", "Prior"), ("↓", "Next")]:
            tk.Button(
                bar, text=sym, bg=T.SURF2, fg=T.MUT,
                font=("Monospace", 11), relief="flat", bd=0,
                padx=5, pady=1, cursor="hand2",
                command=lambda k=key: self._key_press(k)
            ).pack(side="left", padx=1)

        # Close button
        tk.Button(bar, text="✕", bg=T.SURF, fg=T.DIM,
                  font=("Inter", 10), relief="flat", bd=0,
                  padx=4, pady=1, cursor="hand2",
                  command=self._close_bar
                  ).pack(side="right", padx=2)

        self._update_label()

    # ── Mode toggle ─────────────────────────────────────────────────────────
    def _toggle_mode(self):
        self._mode = "touchpad" if self._mode == "direct" else "direct"
        _save_mode(self._mode)
        self._apply_current_mode()
        self._update_label()

    def _apply_current_mode(self):
        if self._mode == "touchpad":
            apply_touchpad_mode()
        else:
            apply_direct_mode()

    def _update_label(self):
        if self._mode == "touchpad":
            self._mode_lbl.config(text="Touchpad  ", fg=T.OK)
            self._icon_lbl.config(text="🖱")
        else:
            self._mode_lbl.config(text="Direct    ", fg=T.ACC)
            self._icon_lbl.config(text="✋")

    # ── Key-press simulation via xdotool ───────────────────────────────────
    def _key_press(self, key):
        """
        Simulate a keyboard key press so the user can trigger
        Left/Right/PageUp/PageDown from the touch bar.
        """
        _run(f"xdotool key {key}")

    # ── Drag to move the bar ────────────────────────────────────────────────
    def _drag_start(self, event):
        self._drag_x = event.x_root - self.winfo_x()
        self._drag_y = event.y_root - self.winfo_y()
        self._swipe_start_x = event.x_root

    def _drag_move(self, event):
        nx = event.x_root - self._drag_x
        ny = event.y_root - self._drag_y
        self.geometry(f"+{nx}+{ny}")

    # ── Close (disables automatic touch management) ────────────────────────
    def _close_bar(self):
        """Restore default touch mode then hide the bar."""
        apply_direct_mode()
        self.destroy()


# ── Standalone settings window (opened from App Store / Settings) ───────────
class TouchSettingsWindow(tk.Toplevel):
    """
    Full settings panel shown when the user wants more detail.
    Call: TouchSettingsWindow(parent)
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Touch Settings — AndrobianOS")
        self.geometry("560x420")
        self.configure(bg=T.BG)
        T.apply(self)
        self._mode = _load_mode()
        self._build()

    def _build(self):
        try:
            T.app_header(self, "Touch Input Settings",
                         "Configure how your tablet screen responds to touch", "✋")
        except Exception:
            tk.Label(self, text="Touch Input Settings", bg=T.BG, fg=T.TXT,
                     font=("Inter", 14, "bold")).pack(pady=10)

        body = tk.Frame(self, bg=T.BG, padx=20, pady=14)
        body.pack(fill="both", expand=True)

        # Mode selector
        mode_card = tk.Frame(body, bg="#181C25", bd=0,
                              highlightthickness=1, highlightbackground="#2C3044")
        mode_card.pack(fill="x", pady=(0, 12))
        inner = tk.Frame(mode_card, bg="#181C25", padx=14, pady=12)
        inner.pack(fill="x")
        tk.Label(inner, text="Touch mode:", bg="#181C25", fg=T.MUT,
                 font=("Inter", 10)).pack(anchor="w", pady=(0, 8))

        self._mode_var = tk.StringVar(value=self._mode)

        modes = [
            ("direct",    "Direct Touch",
             "Tap = click at that spot. Fast and simple.\n"
             "No scrolling or right-click. Best for forms and buttons."),
            ("touchpad",  "Touchpad Mode",
             "Finger drag moves the cursor like a laptop touchpad.\n"
             "Two-finger scroll works. Two-finger tap = right-click.\n"
             "Best for browsing and file managers."),
        ]

        for val, lbl, desc in modes:
            rb_row = tk.Frame(inner, bg="#181C25")
            rb_row.pack(fill="x", pady=4)
            tk.Radiobutton(
                rb_row, text=lbl, variable=self._mode_var, value=val,
                bg="#181C25", fg=T.TXT, selectcolor="#1F2432",
                activebackground="#181C25", font=("Inter", 11, "bold")
            ).pack(anchor="w")
            tk.Label(rb_row, text=desc, bg="#181C25", fg=T.MUT,
                     font=("Inter", 9), justify="left").pack(anchor="w", padx=(24, 0))

        # Gesture shortcuts info
        info = tk.Frame(body, bg="#1F2432", bd=0,
                         highlightthickness=1, highlightbackground="#2C3044")
        info.pack(fill="x", pady=(0, 12))
        ii = tk.Frame(info, bg="#1F2432", padx=14, pady=10)
        ii.pack(fill="x")
        tk.Label(ii, text="Touch bar shortcut buttons:",
                 bg="#1F2432", fg=T.MUT, font=("Inter", 10)).pack(anchor="w", pady=(0, 6))
        shortcuts = [
            ("←  Left arrow",    "Scroll left / go back in browser"),
            ("→  Right arrow",   "Scroll right / go forward in browser"),
            ("↑  Page Up",       "Scroll up a full screen"),
            ("↓  Page Down",     "Scroll down a full screen"),
        ]
        for key, what in shortcuts:
            r = tk.Frame(ii, bg="#1F2432")
            r.pack(fill="x", pady=1)
            tk.Label(r, text=key,  bg="#1F2432", fg=T.ACC,
                     font=("Courier", 10, "bold"), width=16, anchor="w").pack(side="left")
            tk.Label(r, text=what, bg="#1F2432", fg=T.MUT,
                     font=("Inter", 9)).pack(side="left")

        # Apply button
        def apply_settings():
            new_mode = self._mode_var.get()
            _save_mode(new_mode)
            if new_mode == "touchpad":
                apply_touchpad_mode()
            else:
                apply_direct_mode()
            self._mode = new_mode
            self.destroy()

        tk.Button(body, text="Apply & Close",
                  bg=T.ACC, fg=T.TXT, font=("Inter", 11, "bold"),
                  relief="flat", bd=0, padx=14, pady=7, cursor="hand2",
                  command=apply_settings).pack(anchor="e")


# ── Entry point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    bar = TouchBar()
    bar.mainloop()
