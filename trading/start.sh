#!/usr/bin/env bash
# TradingClaw — One-click start script
# Usage: ./trading/start.sh [docker|local]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}"
echo "╔══════════════════════════════════════╗"
echo "║         TradingClaw Agent            ║"
echo "║   Local AI Trading System            ║"
echo "╚══════════════════════════════════════╝"
echo -e "${NC}"

# Check for .env
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}No .env found. Creating from template...${NC}"
    cp .env.example .env
    echo -e "${RED}IMPORTANT: Edit trading/.env and add your ANTHROPIC_API_KEY${NC}"
    echo "Get your key: https://console.anthropic.com/settings/keys"
    echo ""
fi

# Create workspace dirs
mkdir -p workspace/strategies workspace/pinescript data logs data/sample

MODE="${1:-local}"

if [ "$MODE" = "docker" ]; then
    echo -e "${GREEN}Starting with Docker...${NC}"

    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Docker not found. Install Docker or use: ./start.sh local${NC}"
        exit 1
    fi

    docker compose up --build -d
    echo ""
    echo -e "${GREEN}TradingClaw is running!${NC}"
    echo -e "Dashboard: ${YELLOW}http://localhost:8501${NC}"
    echo ""
    echo "Commands:"
    echo "  docker compose logs -f    # View logs"
    echo "  docker compose down       # Stop"
    echo "  docker compose restart    # Restart"

elif [ "$MODE" = "local" ]; then
    echo -e "${GREEN}Starting locally...${NC}"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Python 3 not found.${NC}"
        exit 1
    fi

    # Install deps if needed
    if ! python3 -c "import streamlit" 2>/dev/null; then
        echo -e "${YELLOW}Installing dependencies...${NC}"
        pip install -r requirements.txt
    fi

    # Load .env
    if [ -f ".env" ]; then
        set -a
        source .env
        set +a
    fi

    # Start read-only mode by default for safety
    if [ "$START_READ_ONLY" = "true" ]; then
        echo -e "${YELLOW}Starting in READ-ONLY mode (safe mode)${NC}"
        touch workspace/.read_only
    fi

    export PYTHONPATH="$(dirname "$SCRIPT_DIR")"

    echo ""
    echo -e "${GREEN}Starting Streamlit dashboard...${NC}"
    echo -e "Dashboard: ${YELLOW}http://localhost:${STREAMLIT_PORT:-8501}${NC}"
    echo ""

    streamlit run dashboard/app.py \
        --server.port "${STREAMLIT_PORT:-8501}" \
        --server.address localhost \
        --server.headless true

else
    echo "Usage: ./start.sh [docker|local]"
    echo "  docker  — Run in Docker container (recommended)"
    echo "  local   — Run directly on your machine"
fi
