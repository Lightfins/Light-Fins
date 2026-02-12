#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════
#  TRADING COMMAND CENTER — One-Click Launcher
#  Double-click this file or run: ./launch.sh
# ═══════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT=8085
VENV_DIR="$SCRIPT_DIR/.venv"

echo ""
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║       TRADING COMMAND CENTER v1.1            ║"
echo "  ║       Launching...                           ║"
echo "  ╚══════════════════════════════════════════════╝"
echo ""

# --- Create venv if needed ---
if [ ! -d "$VENV_DIR" ]; then
    echo "[SETUP] Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# --- Activate venv ---
source "$VENV_DIR/bin/activate"

# --- Install dependencies ---
echo "[SETUP] Checking dependencies..."
pip install -q -r "$SCRIPT_DIR/requirements.txt" 2>/dev/null

# --- Create data directory ---
mkdir -p "$SCRIPT_DIR/data"

# --- Kill any existing instance ---
if lsof -ti:$PORT >/dev/null 2>&1; then
    echo "[WARN] Port $PORT in use — stopping previous instance..."
    kill $(lsof -ti:$PORT) 2>/dev/null || true
    sleep 1
fi

# --- Launch server ---
echo "[BOOT] Starting server on port $PORT..."
echo ""

cd "$SCRIPT_DIR"
python server.py &
SERVER_PID=$!

# --- Wait for server to be ready ---
echo "[BOOT] Waiting for server..."
for i in $(seq 1 15); do
    if curl -s "http://localhost:$PORT/api/status" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

# --- Open browser ---
URL="http://localhost:$PORT"
echo ""
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║  SYSTEM ONLINE                               ║"
echo "  ║  Cockpit: $URL                    ║"
echo "  ║  Press Ctrl+C to shut down                   ║"
echo "  ╚══════════════════════════════════════════════╝"
echo ""

# Open in default browser
if command -v xdg-open &>/dev/null; then
    xdg-open "$URL" 2>/dev/null &
elif command -v open &>/dev/null; then
    open "$URL" 2>/dev/null &
elif command -v start &>/dev/null; then
    start "$URL" 2>/dev/null &
fi

# --- Keep running until Ctrl+C ---
trap "echo ''; echo '[SHUTDOWN] Saving state and stopping...'; kill $SERVER_PID 2>/dev/null; exit 0" INT TERM
wait $SERVER_PID
