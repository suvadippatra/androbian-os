#!/usr/bin/env python3
"""
splash.py  —  AndrobianOS  [v4 — HTML-powered animation via pywebview]
═══════════════════════════════════════════════════════════════════════════════
WHAT CHANGED FROM v3
  The animation is now driven entirely by splash.html (CSS keyframes + JS
  timeline).  Python handles only three jobs:
    1. Read splash.html, inject CONFIG values, and hand it to pywebview.
    2. Launch the desktop process in a background thread.
    3. Tell the browser to fade out (via JS) and then close the window.

DEPENDENCIES
  pip install pywebview
  • On Linux also install the GTK/WebKit back-end:
      sudo apt install python3-gi gir1.2-webkit2-4.1

HOW TO CUSTOMISE
  Only edit the values in the CONFIG block below.
  The HTML file drives the visuals — edit splash.html for colour / layout.
═══════════════════════════════════════════════════════════════════════════════
"""

import webview          # pip install pywebview
import threading
import subprocess
import time
import os

# ═══════════════════════════════════════════════════════════════════════════════
# ▼  CONFIG — change any of these values to customise  ▼
# ═══════════════════════════════════════════════════════════════════════════════

BRAND_NAME      = "AndrobianOS"                 # main heading in the HTML
SUB_TEXT        = "debian for android"          # small text below brand
LOADING_TEXT    = "loading joydip's profile"    # bottom status line

# Seconds to wait after Popen before we consider the desktop "ready"
DESKTOP_SETTLE  = 2.5

# Command that starts the desktop / launcher in the background
DESKTOP_COMMAND = ["python3", "/opt/androbian/launcher.py"]

# Path to the companion HTML file (must be in the same directory as this script)
HTML_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "splash.html")

# ▲  END CONFIG  ▲
# ═══════════════════════════════════════════════════════════════════════════════


# ── JS snippet injected when the desktop is ready ──────────────────────────────
#
#   1. Adds a 1-second CSS opacity fade to <body>.
#   2. After the fade completes, calls back into Python via the JS-API bridge
#      to destroy the window (window.pywebview.api.close_window()).
#
_FADEOUT_JS = """
(function () {
    document.body.style.transition = 'opacity 1s ease';
    document.body.style.opacity    = '0';
    setTimeout(function () {
        window.pywebview.api.close_window();
    }, 1050);
})();
"""


class _JsApi:
    """
    Thin Python object exposed to JavaScript as  window.pywebview.api.
    Only one method is needed: close_window(), called from _FADEOUT_JS
    after the CSS fade has finished.
    """

    def __init__(self, splash: "AndrobianSplash"):
        self._splash = splash

    def close_window(self):
        """Destroy the pywebview window from the JS side."""
        if self._splash.window:
            self._splash.window.destroy()


class AndrobianSplash:
    """
    Manages the splash lifecycle:
      • Prepares the HTML (injects config strings).
      • Creates a fullscreen borderless pywebview window.
      • Launches the desktop in a daemon thread.
      • Triggers a JS-driven CSS fade-out once the desktop is ready,
        then closes itself.
    """

    def __init__(self):
        self.window: webview.Window | None = None
        self._js_api = _JsApi(self)

    # ── HTML preparation ────────────────────────────────────────────────────
    def _prepare_html(self) -> str:
        """
        Load splash.html and replace the three user-visible strings with
        the CONFIG values so a single HTML file works for any branding.
        """
        with open(HTML_FILE, "r", encoding="utf-8") as fh:
            html = fh.read()

        # These replacements match the exact strings hardcoded in splash.html.
        # Update these if you rename things in the HTML.
        html = html.replace("AndrobianOS",              BRAND_NAME)
        html = html.replace("debian for Android",       SUB_TEXT)
        html = html.replace("loading joydip's profile", LOADING_TEXT)

        return html

    # ── Background desktop launch ───────────────────────────────────────────
    def _bg_launch(self):
        """
        Start the desktop process, wait for it to settle, then trigger the
        fade-out via JavaScript.  Mirrors the v3 _bg_launch() exactly.
        """
        try:
            subprocess.Popen(
                DESKTOP_COMMAND,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(DESKTOP_SETTLE)
        except Exception:
            # If the launcher cannot be found / fails, still close cleanly
            time.sleep(4.0)

        self._trigger_fadeout()

    # ── Fade-out bridge ─────────────────────────────────────────────────────
    def _trigger_fadeout(self):
        """
        Evaluate the JS fade-out snippet inside the live page.
        The JS will call back into _JsApi.close_window() after 1 second.
        """
        if self.window:
            self.window.evaluate_js(_FADEOUT_JS)

    # ── Entry point ─────────────────────────────────────────────────────────
    def run(self):
        html = self._prepare_html()

        self.window = webview.create_window(
            title            = "",          # no title bar
            html             = html,        # pass HTML as a string, not a file path
            fullscreen       = True,
            frameless        = True,        # borderless — matches overrideredirect(True)
            background_color = "#000000",   # prevents white flash on load
            js_api           = self._js_api,
        )

        # Desktop launch runs in a daemon thread so the animation is unblocked
        threading.Thread(target=self._bg_launch, daemon=True).start()

        # webview.start() blocks until the last window is destroyed
        webview.start()


# ── Run ─────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    AndrobianSplash().run()
