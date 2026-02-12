"""
Trade Journal Engine
--------------------
SQLite-backed journal that records every trade with full context.
Provides analytics: equity curve, heatmaps, strategy rankings,
error classification, session breakdowns, risk metrics.

This is the MEMORY of the system. Without it, the bot learns nothing.

Inputs:  Trade records, query parameters
Outputs: Analytics dicts, CSV/JSON exports
"""

import json
import sqlite3
import csv
import io
import os
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
from config import DB_PATH, DATA_DIR, HEATMAP_BUCKETS


def get_connection():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_journal():
    """Create journal tables if they don't exist."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS trades (
            id TEXT PRIMARY KEY,
            timestamp_open TEXT NOT NULL,
            timestamp_close TEXT,
            pair TEXT NOT NULL,
            direction TEXT NOT NULL,  -- long / short
            strategy TEXT NOT NULL,
            setup_type TEXT,
            market_regime TEXT,
            session TEXT,
            entry_price REAL NOT NULL,
            exit_price REAL,
            stop_loss REAL,
            take_profit REAL,
            position_size REAL,
            risk_amount REAL,
            gross_pnl REAL DEFAULT 0,
            net_pnl REAL DEFAULT 0,
            r_multiple REAL DEFAULT 0,
            confidence_score REAL,
            confidence_tier TEXT,
            entry_reason TEXT,
            exit_reason TEXT,
            mistake_class TEXT,   -- none, early_exit, late_entry, wrong_direction, oversize, fomo, revenge
            notes TEXT,
            status TEXT DEFAULT 'open'  -- open / closed / cancelled
        );

        CREATE TABLE IF NOT EXISTS daily_summary (
            date TEXT PRIMARY KEY,
            trades_taken INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            gross_pnl REAL DEFAULT 0,
            net_pnl REAL DEFAULT 0,
            max_drawdown_pct REAL DEFAULT 0,
            best_trade_r REAL DEFAULT 0,
            worst_trade_r REAL DEFAULT 0,
            avg_r REAL DEFAULT 0,
            capital_eod REAL DEFAULT 0,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS strategy_scores (
            strategy TEXT PRIMARY KEY,
            total_trades INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            win_rate REAL DEFAULT 0,
            avg_r REAL DEFAULT 0,
            expectancy REAL DEFAULT 0,
            max_consecutive_loss INTEGER DEFAULT 0,
            last_updated TEXT,
            enabled INTEGER DEFAULT 1
        );

        CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp_open);
        CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy);
        CREATE INDEX IF NOT EXISTS idx_trades_pair ON trades(pair);
        CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
    """)
    conn.commit()
    conn.close()


def log_trade_open(trade: dict) -> str:
    """Record a new trade entry."""
    conn = get_connection()
    trade_id = trade.get("id", f"T{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}")
    conn.execute("""
        INSERT INTO trades (id, timestamp_open, pair, direction, strategy, setup_type,
                           market_regime, session, entry_price, stop_loss, take_profit,
                           position_size, risk_amount, confidence_score, confidence_tier,
                           entry_reason, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
    """, (
        trade_id, trade.get("timestamp", datetime.utcnow().isoformat()),
        trade["pair"], trade["direction"], trade["strategy"],
        trade.get("setup_type", ""), trade.get("market_regime", ""),
        trade.get("session", ""), trade["entry_price"],
        trade.get("stop_loss"), trade.get("take_profit"),
        trade.get("position_size"), trade.get("risk_amount"),
        trade.get("confidence_score"), trade.get("confidence_tier"),
        trade.get("entry_reason", ""),
    ))
    conn.commit()
    conn.close()
    return trade_id


def log_trade_close(trade_id: str, close_data: dict):
    """Record trade exit."""
    conn = get_connection()
    conn.execute("""
        UPDATE trades SET
            timestamp_close = ?,
            exit_price = ?,
            gross_pnl = ?,
            net_pnl = ?,
            r_multiple = ?,
            exit_reason = ?,
            mistake_class = ?,
            notes = ?,
            status = 'closed'
        WHERE id = ?
    """, (
        close_data.get("timestamp", datetime.utcnow().isoformat()),
        close_data["exit_price"],
        close_data.get("gross_pnl", 0),
        close_data.get("net_pnl", 0),
        close_data.get("r_multiple", 0),
        close_data.get("exit_reason", ""),
        close_data.get("mistake_class", "none"),
        close_data.get("notes", ""),
        trade_id,
    ))
    conn.commit()
    conn.close()


def get_equity_curve(days: int = 90) -> list[dict]:
    """Return daily equity curve data."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT date, capital_eod, net_pnl, max_drawdown_pct
        FROM daily_summary
        WHERE date >= date('now', ?)
        ORDER BY date
    """, (f"-{days} days",)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_strategy_rankings() -> list[dict]:
    """Get all strategies ranked by expectancy."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM strategy_scores ORDER BY expectancy DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_strategy_scores():
    """Recalculate strategy scores from trade data."""
    conn = get_connection()
    strategies = conn.execute("""
        SELECT DISTINCT strategy FROM trades WHERE status = 'closed'
    """).fetchall()

    for row in strategies:
        strat = row["strategy"]
        trades = conn.execute("""
            SELECT net_pnl, r_multiple FROM trades
            WHERE strategy = ? AND status = 'closed'
            ORDER BY timestamp_close DESC
        """, (strat,)).fetchall()

        total = len(trades)
        if total == 0:
            continue

        wins = sum(1 for t in trades if t["net_pnl"] > 0)
        losses = total - wins
        win_rate = wins / total if total > 0 else 0
        avg_r = sum(t["r_multiple"] for t in trades) / total

        # Expectancy = (win_rate * avg_win_r) - (loss_rate * avg_loss_r)
        win_rs = [t["r_multiple"] for t in trades if t["r_multiple"] > 0]
        loss_rs = [abs(t["r_multiple"]) for t in trades if t["r_multiple"] <= 0]
        avg_win_r = sum(win_rs) / len(win_rs) if win_rs else 0
        avg_loss_r = sum(loss_rs) / len(loss_rs) if loss_rs else 0
        expectancy = (win_rate * avg_win_r) - ((1 - win_rate) * avg_loss_r)

        # Max consecutive losses
        max_consec = 0
        current = 0
        for t in trades:
            if t["net_pnl"] <= 0:
                current += 1
                max_consec = max(max_consec, current)
            else:
                current = 0

        conn.execute("""
            INSERT OR REPLACE INTO strategy_scores
            (strategy, total_trades, wins, losses, win_rate, avg_r, expectancy,
             max_consecutive_loss, last_updated, enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            strat, total, wins, losses, round(win_rate, 4), round(avg_r, 2),
            round(expectancy, 4), max_consec, datetime.utcnow().isoformat(),
            1  # auto-disable logic is in strategy_ranker.py
        ))

    conn.commit()
    conn.close()


def update_daily_summary(date: str, capital: float):
    """Compute and store daily summary from closed trades."""
    conn = get_connection()
    trades = conn.execute("""
        SELECT * FROM trades
        WHERE date(timestamp_close) = ? AND status = 'closed'
    """, (date,)).fetchall()

    total = len(trades)
    wins = sum(1 for t in trades if t["net_pnl"] > 0)
    losses = total - wins
    gross_pnl = sum(t["gross_pnl"] for t in trades)
    net_pnl = sum(t["net_pnl"] for t in trades)
    r_multiples = [t["r_multiple"] for t in trades]
    best_r = max(r_multiples) if r_multiples else 0
    worst_r = min(r_multiples) if r_multiples else 0
    avg_r = sum(r_multiples) / len(r_multiples) if r_multiples else 0

    conn.execute("""
        INSERT OR REPLACE INTO daily_summary
        (date, trades_taken, wins, losses, gross_pnl, net_pnl,
         best_trade_r, worst_trade_r, avg_r, capital_eod)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (date, total, wins, losses, round(gross_pnl, 2), round(net_pnl, 2),
          round(best_r, 2), round(worst_r, 2), round(avg_r, 2), round(capital, 2)))
    conn.commit()
    conn.close()


def get_error_heatmap() -> dict:
    """
    Build error heatmap: what mistakes happen when?
    Buckets: hour of day, day of week, session.
    """
    conn = get_connection()
    trades = conn.execute("""
        SELECT timestamp_open, session, mistake_class, r_multiple
        FROM trades WHERE status = 'closed' AND mistake_class != 'none'
        AND mistake_class IS NOT NULL
    """).fetchall()
    conn.close()

    heatmap = {
        "by_hour": {},
        "by_day": {},
        "by_session": {},
        "by_type": {},
    }

    for t in trades:
        ts = datetime.fromisoformat(t["timestamp_open"])
        hour = ts.hour
        day = ts.strftime("%A")
        session = t["session"]
        mistake = t["mistake_class"]

        heatmap["by_hour"][hour] = heatmap["by_hour"].get(hour, 0) + 1
        heatmap["by_day"][day] = heatmap["by_day"].get(day, 0) + 1
        heatmap["by_session"][session] = heatmap["by_session"].get(session, 0) + 1
        heatmap["by_type"][mistake] = heatmap["by_type"].get(mistake, 0) + 1

    return heatmap


def get_performance_metrics(days: int = 30) -> dict:
    """Compute Sharpe, Sortino, max drawdown, win rate, expectancy."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT net_pnl, r_multiple, capital_eod FROM daily_summary
        WHERE date >= date('now', ?)
        ORDER BY date
    """, (f"-{days} days",)).fetchall()
    conn.close()

    if not rows:
        return {"error": "No data available"}

    daily_returns = [r["net_pnl"] for r in rows]
    capitals = [r["capital_eod"] for r in rows]

    avg_return = sum(daily_returns) / len(daily_returns) if daily_returns else 0
    std_return = (sum((r - avg_return) ** 2 for r in daily_returns) / max(len(daily_returns) - 1, 1)) ** 0.5

    # Sharpe (annualized, assuming 252 trading days)
    sharpe = (avg_return / std_return * (252 ** 0.5)) if std_return > 0 else 0

    # Sortino (downside deviation only)
    downside = [r for r in daily_returns if r < 0]
    downside_std = (sum(r ** 2 for r in downside) / max(len(downside), 1)) ** 0.5
    sortino = (avg_return / downside_std * (252 ** 0.5)) if downside_std > 0 else 0

    # Max drawdown
    peak = capitals[0] if capitals else 0
    max_dd = 0
    for c in capitals:
        if c > peak:
            peak = c
        dd = (peak - c) / peak * 100 if peak > 0 else 0
        max_dd = max(max_dd, dd)

    return {
        "period_days": days,
        "total_pnl": round(sum(daily_returns), 2),
        "avg_daily_pnl": round(avg_return, 2),
        "daily_std": round(std_return, 2),
        "sharpe_ratio": round(sharpe, 2),
        "sortino_ratio": round(sortino, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "total_days": len(rows),
        "profitable_days": sum(1 for r in daily_returns if r > 0),
        "losing_days": sum(1 for r in daily_returns if r < 0),
    }


def export_trades(fmt: str = "json", days: int = 90) -> str:
    """Export trade history as JSON or CSV string."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM trades
        WHERE date(timestamp_open) >= date('now', ?)
        ORDER BY timestamp_open DESC
    """, (f"-{days} days",)).fetchall()
    conn.close()

    trades = [dict(r) for r in rows]

    if fmt == "json":
        return json.dumps(trades, indent=2)
    elif fmt == "csv":
        if not trades:
            return ""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=trades[0].keys())
        writer.writeheader()
        writer.writerows(trades)
        return output.getvalue()
    else:
        return json.dumps(trades, indent=2)


# Initialize on import
init_journal()
