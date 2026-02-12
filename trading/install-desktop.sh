#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════
#  Creates a desktop shortcut for Trading Command Center
#  Run once: ./install-desktop.sh
# ═══════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_DIR="$HOME/Desktop"
APPS_DIR="$HOME/.local/share/applications"
ICON_SRC="$SCRIPT_DIR/frontend/logo.svg"
ICON_DIR="$HOME/.local/share/icons"
LAUNCHER="$SCRIPT_DIR/launch.sh"

echo "[INSTALL] Setting up desktop launcher..."

# Ensure directories exist
mkdir -p "$DESKTOP_DIR" "$APPS_DIR" "$ICON_DIR"

# Copy icon
cp "$ICON_SRC" "$ICON_DIR/trading-command-center.svg"

# Create .desktop file
DESKTOP_FILE="$DESKTOP_DIR/TradingCommandCenter.desktop"
cat > "$DESKTOP_FILE" << DESKTOP_EOF
[Desktop Entry]
Version=1.1
Type=Application
Name=Trading Command Center
Comment=Launch the Trading Command Center cockpit
Exec=bash $LAUNCHER
Icon=$ICON_DIR/trading-command-center.svg
Terminal=true
Categories=Finance;Development;
StartupNotify=true
DESKTOP_EOF

chmod +x "$DESKTOP_FILE"

# Also install to applications menu
cp "$DESKTOP_FILE" "$APPS_DIR/trading-command-center.desktop"

echo "[INSTALL] Desktop shortcut created!"
echo ""
echo "  You should now see 'Trading Command Center' on your desktop."
echo "  Double-click it to launch."
echo ""
echo "  If the icon doesn't appear immediately, try:"
echo "    - Right-click the desktop file > Properties > Allow executing"
echo "    - Or run:  gio set '$DESKTOP_FILE' metadata::trusted true"
echo ""
