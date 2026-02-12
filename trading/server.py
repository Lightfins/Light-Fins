"""
Trading System Orchestration Server
------------------------------------
Layer 2: Routes requests between the cockpit UI and execution scripts.
Serves the frontend, provides API endpoints for all trading operations.

Endpoints:
  GET  /                     -> Cockpit UI
  GET  /api/status           -> System status
  GET  /api/journal          -> Trade journal data
  GET  /api/journal/export   -> Export trades (JSON/CSV)
  GET  /api/equity           -> Equity curve
  GET  /api/strategies       -> Strategy rankings
  GET  /api/errors           -> Error heatmap
  GET  /api/metrics          -> Performance metrics (Sharpe, Sortino, etc.)
  GET  /api/regime           -> Current regime analysis
  GET  /api/sessions         -> Session statistics
  GET  /api/montecarlo       -> Monte Carlo simulation
  POST /api/score            -> Score a potential trade
  POST /api/trade/open       -> Log trade open
  POST /api/trade/close      -> Log trade close
  POST /api/backtest         -> Run backtest
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path

# Add execution to path
sys.path.insert(0, str(Path(__file__).parent / "execution"))

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import uvicorn

from config import DEFAULT_INITIAL_CAPITAL
from risk_engine import RiskEngine
from journal_engine import (
    init_journal, log_trade_open, log_trade_close,
    get_equity_curve, get_strategy_rankings, update_strategy_scores,
    get_error_heatmap, get_performance_metrics, export_trades,
    update_daily_summary
)
from strategy_ranker import evaluate_strategies, auto_disable_strategies, detect_error_clusters
from trade_scorer import compute_trade_score
from monte_carlo import run_monte_carlo, stress_test_scenarios

app = FastAPI(title="Trading Command Center", version="1.0.0")

# Global risk engine instance
risk_engine = RiskEngine(initial_capital=DEFAULT_INITIAL_CAPITAL)

# Serve frontend
frontend_dir = Path(__file__).parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_cockpit():
    index_path = frontend_dir / "index.html"
    return FileResponse(str(index_path))


@app.get("/api/status")
async def get_status():
    """Full system status snapshot."""
    risk_status = risk_engine.get_status()
    kill_check = risk_engine.check_kill_switch()
    strategies = evaluate_strategies()

    active_strategies = sum(1 for s in strategies if s.get("enabled", 1) and s["action"] != "disable")
    failing_strategies = sum(1 for s in strategies if s["action"] == "disable")

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "risk": risk_status,
        "kill_switch": kill_check,
        "strategies": {
            "active": active_strategies,
            "failing": failing_strategies,
            "total": len(strategies),
        },
        "system": "operational" if not kill_check["killed"] else "KILLED",
    }


@app.get("/api/journal")
async def get_journal(days: int = 30, limit: int = 100):
    """Get recent trade journal entries."""
    trades_json = export_trades("json", days)
    trades = json.loads(trades_json)
    return {
        "trades": trades[:limit],
        "total": len(trades),
        "period_days": days,
    }


@app.get("/api/journal/export")
async def export_journal(fmt: str = "json", days: int = 90):
    """Export trade history."""
    data = export_trades(fmt, days)
    if fmt == "csv":
        return JSONResponse(content={"format": "csv", "data": data})
    return json.loads(data)


@app.get("/api/equity")
async def get_equity(days: int = 90):
    """Get equity curve data."""
    curve = get_equity_curve(days)
    return {"equity_curve": curve, "period_days": days}


@app.get("/api/strategies")
async def get_strategies():
    """Get strategy rankings and evaluations."""
    evaluations = evaluate_strategies()
    error_clusters = detect_error_clusters()
    return {
        "strategies": evaluations,
        "error_clusters": error_clusters,
    }


@app.get("/api/errors")
async def get_errors():
    """Get error heatmap data."""
    return get_error_heatmap()


@app.get("/api/metrics")
async def get_metrics(days: int = 30):
    """Get performance metrics."""
    return get_performance_metrics(days)


@app.get("/api/regime")
async def get_regime():
    """Get current market regime analysis (requires market data)."""
    # In production, this would pull live data.
    # For now, return structure for the UI to consume.
    return {
        "current": {
            "trend": "unknown",
            "volatility": "unknown",
            "strategy_fit": "unknown",
            "adx": 0,
        },
        "note": "Connect market data feed to enable live regime detection",
    }


@app.get("/api/sessions")
async def get_sessions():
    """Get session statistics."""
    now = datetime.utcnow()
    hour = now.hour
    if 0 <= hour < 8:
        current = "asia"
    elif 7 <= hour < 16:
        current = "london"
    elif 12 <= hour < 21:
        current = "ny"
    else:
        current = "off_hours"

    overlap = ""
    if 12 <= hour < 16:
        overlap = "london_ny"

    return {
        "current_session": current,
        "overlap": overlap,
        "utc_hour": hour,
        "timestamp": now.isoformat(),
    }


@app.get("/api/montecarlo")
async def run_mc(n_sims: int = 5000, n_trades: int = 252):
    """Run Monte Carlo simulation from historical trades."""
    trades_json = export_trades("json", 365)
    trades = json.loads(trades_json)

    if len(trades) < 5:
        # Generate demo data for display
        rng = np.random.default_rng(42)
        demo_returns = [200 if rng.random() > 0.45 else -100 for _ in range(50)]
        result = run_monte_carlo(demo_returns, DEFAULT_INITIAL_CAPITAL, min(n_sims, 5000), n_trades)
        result["note"] = "Using demo data — not enough historical trades yet"
        return result

    returns = [t.get("net_pnl", 0) for t in trades if t.get("net_pnl") is not None]
    return run_monte_carlo(returns, risk_engine.capital, min(n_sims, 10000), n_trades)


@app.post("/api/score")
async def score_trade(request: Request):
    """Score a potential trade setup."""
    signals = await request.json()
    result = compute_trade_score(signals)
    return result


@app.post("/api/trade/open")
async def open_trade(request: Request):
    """Log a new trade entry."""
    trade = await request.json()
    trade_id = log_trade_open(trade)

    # Register with risk engine
    risk_engine.register_trade({
        "id": trade_id,
        "pair": trade["pair"],
        "direction": trade["direction"],
        "entry_price": trade["entry_price"],
        "size": trade.get("position_size", 0),
        "risk_amount": trade.get("risk_amount", 0),
        "position_value": trade.get("position_size", 0) * trade["entry_price"],
    })

    return {"trade_id": trade_id, "status": "opened"}


@app.post("/api/trade/close")
async def close_trade(request: Request):
    """Log trade exit."""
    data = await request.json()
    trade_id = data["trade_id"]

    # Close in risk engine
    risk_result = risk_engine.close_trade(trade_id, data["exit_price"])

    # Log to journal
    close_data = {
        "exit_price": data["exit_price"],
        "gross_pnl": risk_result.get("gross_pnl", 0),
        "net_pnl": risk_result.get("net_pnl", 0),
        "r_multiple": risk_result.get("r_multiple", 0),
        "exit_reason": data.get("exit_reason", ""),
        "mistake_class": data.get("mistake_class", "none"),
        "notes": data.get("notes", ""),
    }
    log_trade_close(trade_id, close_data)

    return {
        "trade_id": trade_id,
        "result": risk_result,
        "risk_status": risk_engine.get_status(),
    }


@app.post("/api/backtest")
async def run_backtest_endpoint(request: Request):
    """Run a backtest with demo data (in production, accepts uploaded data)."""
    from backtest_engine import BacktestEngine, momentum_bos_strategy

    # Generate synthetic data for demo
    rng = np.random.default_rng(42)
    n = 1000
    prices = 1.1000 + np.cumsum(rng.standard_normal(n) * 0.001)
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="1h"),
        "open": prices,
        "high": prices + np.abs(rng.standard_normal(n) * 0.0005),
        "low": prices - np.abs(rng.standard_normal(n) * 0.0005),
        "close": prices + rng.standard_normal(n) * 0.0003,
        "volume": rng.integers(100, 10000, n),
    })

    engine = BacktestEngine()
    results = engine.run(df, momentum_bos_strategy, "momentum_bos")
    return results


# Initialize journal on startup
init_journal()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8085)
