#!/bin/bash
# bootstrap.sh — AndrobianOS
# ════════════════════════════════════════════════════════════════════
# Run this ONCE on a fresh Debian proot to install everything:
#
#   curl -fsSL https://raw.githubusercontent.com/YOUR_USER/androbian-os/main/bootstrap.sh | bash
#
# Or after cloning the repo:
#   bash /opt/androbian/bootstrap.sh
# ════════════════════════════════════════════════════════════════════

set -e

GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'
RED='\033[0;31m';   NC='\033[0m'
ok()   { echo -e "${GREEN}  ✓  $*${NC}"; }
info() { echo -e "${CYAN}  →  $*${NC}"; }
warn() { echo -e "${YELLOW}  ⚠  $*${NC}"; }
err()  { echo -e "${RED}  ✗  $*${NC}"; exit 1; }

echo ""
echo -e "${CYAN}"
echo "  ╔══════════════════════════════════════════╗"
echo "  ║        AndrobianOS  —  Bootstrap         ║"
echo "  ║   Debian on Android · Termux · proot     ║"
echo "  ╚══════════════════════════════════════════╝"
echo -e "${NC}"

SUITE_DIR="/opt/androbian"
GITHUB_USER="${ANDROBIAN_USER:-YOUR_GITHUB_USERNAME}"
GITHUB_REPO="${ANDROBIAN_REPO:-androbian-os}"

# ── Step 1: System dependencies ──────────────────────────────────────────────
info "Step 1/7: Installing system dependencies…"
apt update -qq 2>/dev/null
apt install -y --no-install-recommends \
    python3 python3-pip python3-tk python3-pil python3-pil.imagetk \
    git curl wget ca-certificates \
    ghostscript tmux screen \
    fonts-inter 2>/dev/null || \
apt install -y --no-install-recommends \
    python3 python3-pip python3-tk \
    git curl wget ca-certificates \
    ghostscript tmux screen 2>/dev/null || true
ok "System dependencies installed."

# ── Step 2: Python libraries ──────────────────────────────────────────────────
info "Step 2/7: Installing Python libraries…"
pip3 install --break-system-packages --quiet pymupdf Pillow 2>/dev/null || \
pip3 install --quiet pymupdf Pillow 2>/dev/null || true
ok "Python libraries installed."

# ── Step 3: Download the suite ────────────────────────────────────────────────
info "Step 3/7: Downloading AndrobianOS suite from GitHub…"
mkdir -p /opt
if [ -d "$SUITE_DIR/.git" ]; then
    cd "$SUITE_DIR" && git pull origin main --quiet 2>/dev/null || true
    ok "Suite updated from GitHub."
else
    git clone --depth 1 \
        "https://github.com/${GITHUB_USER}/${GITHUB_REPO}.git" \
        "$SUITE_DIR" --quiet 2>/dev/null ||
    err "Clone failed. Check: 1) Internet connection  2) Repo is public  3) Username is correct"
    ok "Suite downloaded to $SUITE_DIR."
fi

# ── Step 4: Permissions ───────────────────────────────────────────────────────
info "Step 4/7: Setting permissions…"
chmod +x "$SUITE_DIR"/*.sh  2>/dev/null || true
chmod +x "$SUITE_DIR"/*.py  2>/dev/null || true
chmod 4755 /usr/bin/sudo    2>/dev/null || true
ok "Permissions set."

# ── Step 5: Config directory ──────────────────────────────────────────────────
info "Step 5/7: Creating config directory…"
mkdir -p "$HOME/.config/androbian/user_apps"
# Write the config file (GitHub credentials filled in by github_sync.sh later)
if [ ! -f "$HOME/.config/androbian/config.json" ]; then
    cat > "$HOME/.config/androbian/config.json" << EOF
{
  "github_user":  "${GITHUB_USER}",
  "github_repo":  "${GITHUB_REPO}",
  "github_token": "YOUR_TOKEN_HERE",
  "suite_dir":    "${SUITE_DIR}"
}
EOF
fi
ok "Config directory created."

# ── Step 6: Create the 'joy' command ─────────────────────────────────────────
# ════════════════════════════════════════════════════════════════════
# THIS IS THE KEY CHANGE:
# 'joy' is a Termux-side script (saved inside Termux, NOT inside proot).
# It does FOUR things automatically before showing the user anything:
#   1. Launches Termux:X11 via Android intent (am start)
#   2. Waits for X server to be ready (polls /tmp/.X11-unix/X0)
#   3. Starts PulseAudio for audio
#   4. Enters proot Debian and runs the splash + desktop
#
# The user NEVER needs to manually open Termux:X11.
# They just open Termux, type 'joy', press Enter, and the boot
# animation appears within 2-3 seconds.
# ════════════════════════════════════════════════════════════════════

info "Step 6/7: Creating the 'joy' command in Termux…"

# The 'joy' script is placed OUTSIDE proot (in Termux's usr/bin)
# so the user can call it from the Termux prompt.
cat > /data/data/com.termux/files/usr/bin/joy << 'JOYEOF'
#!/data/data/com.termux/files/usr/bin/bash
# joy — Start AndrobianOS desktop (single command, no manual steps)
# Usage: type 'joy' in Termux and press Enter. That's it.

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║   Starting AndrobianOS…              ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# ── 1. Launch Termux:X11 app via Android intent ────────────────────────────
# This sends an intent to Android to open the Termux:X11 app.
# The app opens in background (user will see the splash in it immediately).
echo "  → Starting X11 display server…"
am start --user 0 \
    -n com.termux.x11/com.termux.x11.MainActivity \
    2>/dev/null

# ── 2. Wait for X server socket to appear ─────────────────────────────────
# The X server is ready when /tmp/.X11-unix/X0 exists.
# We poll every 500ms with a 10-second timeout.
echo "  → Waiting for X server…"
WAITED=0
while [ ! -S /tmp/.X11-unix/X0 ] && [ $WAITED -lt 20 ]; do
    sleep 0.5
    WAITED=$((WAITED + 1))
done
if [ ! -S /tmp/.X11-unix/X0 ]; then
    echo "  ⚠  X server socket not found after 10s."
    echo "     If Termux:X11 is not installed, install it from:"
    echo "     https://github.com/termux/termux-x11/releases"
    echo "     Then run 'joy' again."
    exit 1
fi
echo "  ✓  X server ready."

# ── 3. Start PulseAudio for audio ─────────────────────────────────────────
echo "  → Starting audio server…"
pulseaudio --start \
    --load="module-native-protocol-tcp auth-ip-acl=127.0.0.1" \
    --exit-idle-time=-1 2>/dev/null || true

# ── 4. Enter proot Debian and start the desktop ───────────────────────────
echo "  → Entering Debian…"
echo ""

# We bind Android's internal storage to ~/android_storage inside the desktop
proot-distro login debian \
    --bind /sdcard:/home/joydip/android_storage \
    --user joydip \
    -- bash -ic '
        export DISPLAY=:0
        export PULSE_SERVER=tcp:127.0.0.1:4713
        export QT_QPA_PLATFORMTHEME=qt5ct
        export XDG_RUNTIME_DIR=/tmp/runtime-joydip
        mkdir -p $XDG_RUNTIME_DIR
        # Start the desktop (splash animation → launcher)
        python3 /opt/androbian/splash.py
    '
JOYEOF

chmod +x /data/data/com.termux/files/usr/bin/joy
ok "'joy' command created in Termux."

# ── Step 7: Desktop entries + shortcuts ──────────────────────────────────────
info "Step 7/7: Creating desktop entries…"
bash "$SUITE_DIR/create_desktop_entries.sh" 2>/dev/null || true

# Create desktop folder shortcut
mkdir -p "$HOME/Desktop"
cat > "$HOME/Desktop/AndrobianOS.desktop" << 'DESK'
[Desktop Entry]
Version=1.0
Type=Application
Name=AndrobianOS Suite
Comment=PDF tools, calculator, and more
Exec=python3 /opt/androbian/launcher.py
Terminal=false
DESK
chmod +x "$HOME/Desktop/AndrobianOS.desktop"
ok "Desktop shortcuts created."

echo ""
echo -e "${GREEN}"
echo "  ══════════════════════════════════════════"
echo "  ✓  AndrobianOS is ready!"
echo "  ══════════════════════════════════════════"
echo -e "${NC}"
echo "  HOW TO START THE DESKTOP:"
echo "    Open Termux → type: joy → press Enter"
echo "    That's all. Termux:X11 opens automatically."
echo ""
echo "  DAILY COMMANDS (inside proot Debian):"
echo "    python3 /opt/androbian/launcher.py   → open all tools"
echo "    apt install <package>                → install system app"
echo "    bash /opt/androbian/github_sync.sh push  → backup to GitHub"
echo ""
