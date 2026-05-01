#!/bin/bash
# create_desktop_entries.sh — AndrobianOS
# Creates .desktop files so all apps appear in the LXQt application menu.
# Run once after installation: bash /opt/androbian/create_desktop_entries.sh

SUITE_DIR="/opt/androbian"
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"
PYTHON="$(which python3)"

mk() {
    local NAME="$1" FILE="$2" COMMENT="$3" CAT="$4"
    cat > "$DESKTOP_DIR/androbian_${FILE%.py}.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$NAME
Comment=$COMMENT
Exec=$PYTHON $SUITE_DIR/$FILE
Icon=utilities-terminal
Categories=$CAT
Terminal=false
StartupNotify=false
EOF
}

echo "Creating .desktop entries for AndrobianOS…"
mk "AndrobianOS Launcher"    "launcher.py"      "Open all tools"                    "Utility;"
mk "PDF Merge"               "pdf_merge.py"     "Merge multiple PDFs"               "Utility;"
mk "PDF Split"               "pdf_split.py"     "Split PDF by page ranges"          "Utility;"
mk "PDF N-up"                "pdf_nup.py"       "Multi-page sheet layout"           "Utility;"
mk "Watermark Remover"       "pdf_wm_remove.py" "Remove watermarks from PDFs"       "Utility;"
mk "PDF Booklet"             "pdf_booklet.py"   "Booklet page imposition"           "Utility;"
mk "Add Watermark"           "pdf_wm_add.py"    "Stamp watermarks on PDFs"          "Utility;"
mk "PDF Compress"            "pdf_compress.py"  "Reduce PDF file size"              "Utility;"
mk "Rearrange Pages"         "pdf_rearrange.py" "Reorder PDF pages"                 "Utility;"
mk "PDF to Image"            "pdf_to_image.py"  "Extract PDF pages as images"       "Utility;"
mk "Exam Photo Resizer"      "image_resizer.py" "Resize photos for exam forms"      "Utility;"
mk "Scientific Calculator"   "calculator.py"    "Calculator with graphing"          "Utility;Education;"
mk "App Store"               "app_store.py"     "Install and manage apps"           "System;PackageManager;"
mk "Settings"                "settings.py"      "Theme, wallpaper, display"         "System;Settings;"
mk "Touch Manager"           "touch_manager.py" "Touch mode toggle"                 "System;"
mk "Community Feedback"      "community.py"     "Suggestions and bug reports"       "System;"

command -v update-desktop-database &>/dev/null && \
    update-desktop-database "$DESKTOP_DIR"

echo "  ✓  Done. All apps now appear in the LXQt menu."
