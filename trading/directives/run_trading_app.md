# Directive: Running the Trading App

## Prerequisites
- Python 3.10+
- pip install -r requirements.txt

## Quick Start
```bash
cd trading
pip install -r requirements.txt
python server.py
```
Then open `http://localhost:8085` in your browser.

## Architecture
```
Layer 1 (Directives)     directives/*.md          Instructions
Layer 2 (Orchestration)  server.py                FastAPI routing
Layer 3 (Execution)      execution/*.py           Deterministic logic
Frontend                 frontend/                Cockpit UI
```

## Server Configuration
- Default port: 8085
- Static files served from: `frontend/`
- API base path: `/api/`
- Journal database: `data/journal.db` (SQLite, auto-created)

## API Reference

### Status & Risk
- `GET /api/status` — System status, risk exposure, kill switch state
- `GET /api/sessions` — Current trading session info

### Journal & Analytics
- `GET /api/journal?days=30&limit=100` — Recent trades
- `GET /api/journal/export?fmt=json&days=90` — Export (json or csv)
- `GET /api/equity?days=90` — Equity curve
- `GET /api/metrics?days=30` — Sharpe, Sortino, max DD
- `GET /api/errors` — Error heatmap
- `GET /api/strategies` — Strategy rankings

### Trading Operations
- `POST /api/trade/open` — Log new trade entry
- `POST /api/trade/close` — Log trade exit
- `POST /api/score` — Score a potential trade (0-100)

### Simulation
- `GET /api/montecarlo?n_sims=5000&n_trades=252` — Monte Carlo sim
- `POST /api/backtest` — Run backtest with demo data

## Troubleshooting
- If journal.db doesn't exist, it's auto-created on first import of journal_engine.py
- If port 8085 is busy, change it in server.py __main__ block
- Frontend polls every 5 seconds — reduce POLL_INTERVAL in dashboard.js if needed
