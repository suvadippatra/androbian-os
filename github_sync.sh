#!/bin/bash
# github_sync.sh — AndrobianOS
# ════════════════════════════════════════════════════════════════════
# Backup your entire suite to GitHub, or restore it on a new device.
#
# USAGE:
#   bash /opt/androbian/github_sync.sh push    ← backup to GitHub
#   bash /opt/androbian/github_sync.sh pull    ← restore from GitHub
#
# FIRST-TIME SETUP:
#   Edit the three variables below: GITHUB_USER, GITHUB_REPO, GITHUB_TOKEN
#   See the GitHub Setup Guide document for step-by-step instructions.
# ════════════════════════════════════════════════════════════════════

GITHUB_USER="YOUR_GITHUB_USERNAME"
GITHUB_REPO="androbian-os"
GITHUB_TOKEN="YOUR_PERSONAL_ACCESS_TOKEN"

SUITE_DIR="/opt/androbian"
REPO_URL="https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/${GITHUB_USER}/${GITHUB_REPO}.git"
MODE="${1:-push}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'
RED='\033[0;31m';   NC='\033[0m'
ok()   { echo -e "${GREEN}  ✓  $*${NC}"; }
info() { echo -e "${CYAN}  →  $*${NC}"; }
warn() { echo -e "${YELLOW}  ⚠  $*${NC}"; }
err()  { echo -e "${RED}  ✗  $*${NC}"; exit 1; }

# ── Also update the config.json with current credentials ──────────────────
_update_config() {
    mkdir -p "$HOME/.config/androbian"
    cat > "$HOME/.config/androbian/config.json" << EOF
{
  "github_user":  "${GITHUB_USER}",
  "github_repo":  "${GITHUB_REPO}",
  "github_token": "${GITHUB_TOKEN}",
  "suite_dir":    "${SUITE_DIR}"
}
EOF
}

# ── PUSH ──────────────────────────────────────────────────────────────────
do_push() {
    echo ""
    echo -e "${CYAN}  ══════════════════════════════════════════"
    echo "     AndrobianOS  →  Backing up to GitHub"
    echo -e "  ══════════════════════════════════════════${NC}"
    echo ""

    [ "$GITHUB_USER" = "YOUR_GITHUB_USERNAME" ] && \
        err "Edit github_sync.sh and set your GITHUB_USER, GITHUB_TOKEN first."

    _update_config

    cd "$SUITE_DIR" || err "Suite not found at $SUITE_DIR"

    if [ ! -d ".git" ]; then
        git init
        git remote add origin "$REPO_URL"
        ok "Git repository initialised."
    else
        git remote set-url origin "$REPO_URL"
    fi

    # .gitignore
    cat > .gitignore << 'EOF'
__pycache__/
*.pyc
*.pyo
.DS_Store
*.swp
*.tmp
EOF

    # README
    cat > README.md << READMEEOF
# AndrobianOS

A customised Debian Linux desktop running inside Termux proot on Android.
Built by Joydip, Bankura, West Bengal.

## One-command install on any Android device

\`\`\`bash
# Step 1 — in Termux:
pkg install proot-distro git -y && proot-distro install debian
proot-distro login debian

# Step 2 — inside Debian:
curl -fsSL https://raw.githubusercontent.com/${GITHUB_USER}/${GITHUB_REPO}/main/bootstrap.sh | bash
\`\`\`

After that, type **joy** in Termux to start the desktop.

## What's included
- Boot animation (AndrobianOS cinematic intro)
- 11 Python GUI apps: PDF tools, watermark handling, calculator, exam photo resizer
- Custom App Store (fetches this repo's manifest)
- Settings: themes (macOS/Windows), wallpaper, compositor
- Touch manager: Direct Touch / Touchpad mode toggle
- Community feedback system

*Last backup: $(date '+%Y-%m-%d %H:%M')*
READMEEOF

    git add -A
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    git commit -m "AndrobianOS backup: ${TIMESTAMP}" 2>/dev/null || warn "Nothing new to commit."

    git push -u origin main 2>/dev/null || \
    git push -u origin master 2>/dev/null || {
        warn "Trying force push (first time)…"
        git branch -M main
        git push --force -u origin main || \
            err "Push failed. Check your token and repo name."
    }

    echo ""
    ok "Backup complete!"
    echo ""
    echo "  Your repo: https://github.com/${GITHUB_USER}/${GITHUB_REPO}"
    echo ""
    echo "  One-command install URL:"
    echo "  curl -fsSL https://raw.githubusercontent.com/${GITHUB_USER}/${GITHUB_REPO}/main/bootstrap.sh | bash"
    echo ""
}

# ── PULL ──────────────────────────────────────────────────────────────────
do_pull() {
    echo ""
    echo -e "${CYAN}  ══════════════════════════════════════════"
    echo "     AndrobianOS  ←  Restoring from GitHub"
    echo -e "  ══════════════════════════════════════════${NC}"

    [ "$GITHUB_USER" = "YOUR_GITHUB_USERNAME" ] && \
        err "Edit github_sync.sh and set your GITHUB_USER, GITHUB_TOKEN first."

    _update_config

    if [ -d "$SUITE_DIR/.git" ]; then
        cd "$SUITE_DIR"
        git remote set-url origin "$REPO_URL"
        git pull origin main 2>/dev/null || git pull origin master
        ok "Suite updated from GitHub."
    else
        mkdir -p /opt
        git clone "$REPO_URL" "$SUITE_DIR" || err "Clone failed."
        ok "Suite cloned to $SUITE_DIR."
    fi

    bash "$SUITE_DIR/bootstrap.sh" || true
}

case "$MODE" in
    push) do_push ;;
    pull) do_pull ;;
    *)    echo "Usage: bash github_sync.sh [push|pull]" ;;
esac
