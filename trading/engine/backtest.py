"""
Backtesting engine using vectorbt + pandas_ta.
Supports TradingView CSV imports, multi-asset testing, and professional stats.
"""

import os
import json
import datetime
import numpy as np
import pandas as pd
import pandas_ta as ta
import vectorbt as vbt
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

WORKSPACE = Path(os.getenv("TRADING_WORKSPACE", "trading/workspace"))
DATA_DIR = Path(os.getenv("TRADING_DATA_DIR", "trading/data"))


def load_tradingview_csv(filepath: str) -> pd.DataFrame:
    """Load a TradingView-exported CSV (time, open, high, low, close, volume)."""
    df = pd.read_csv(filepath)

    # Normalize column names
    col_map = {}
    for col in df.columns:
        lower = col.strip().lower()
        if lower in ("time", "date", "datetime", "timestamp"):
            col_map[col] = "datetime"
        elif lower == "open":
            col_map[col] = "open"
        elif lower == "high":
            col_map[col] = "high"
        elif lower == "low":
            col_map[col] = "low"
        elif lower == "close":
            col_map[col] = "close"
        elif lower in ("volume", "vol"):
            col_map[col] = "volume"

    df = df.rename(columns=col_map)

    if "datetime" not in df.columns:
        raise ValueError(f"No datetime column found in {filepath}. Columns: {list(df.columns)}")

    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime").sort_index()

    for col in ["open", "high", "low", "close"]:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if "volume" not in df.columns:
        df["volume"] = 0

    df = df.dropna(subset=["open", "high", "low", "close"])
    return df


def load_multi_asset(filepaths: List[str]) -> Dict[str, pd.DataFrame]:
    """Load multiple CSV files for multi-asset backtesting."""
    assets = {}
    for fp in filepaths:
        name = Path(fp).stem.upper()
        assets[name] = load_tradingview_csv(fp)
    return assets


def apply_indicators(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
    """Apply technical indicators from a strategy config to the dataframe."""
    indicators = config.get("indicators", [])

    for ind in indicators:
        name = ind["name"].upper()
        params = ind.get("params", {})

        if name == "RSI":
            length = params.get("length", 14)
            df[f"rsi_{length}"] = ta.rsi(df["close"], length=length)

        elif name == "EMA":
            length = params.get("length", 20)
            df[f"ema_{length}"] = ta.ema(df["close"], length=length)

        elif name == "SMA":
            length = params.get("length", 20)
            df[f"sma_{length}"] = ta.sma(df["close"], length=length)

        elif name == "MACD":
            fast = params.get("fast", 12)
            slow = params.get("slow", 26)
            signal = params.get("signal", 9)
            macd = ta.macd(df["close"], fast=fast, slow=slow, signal=signal)
            if macd is not None:
                df = pd.concat([df, macd], axis=1)

        elif name == "BBANDS":
            length = params.get("length", 20)
            std = params.get("std", 2.0)
            bb = ta.bbands(df["close"], length=length, std=std)
            if bb is not None:
                df = pd.concat([df, bb], axis=1)

        elif name == "ATR":
            length = params.get("length", 14)
            df[f"atr_{length}"] = ta.atr(df["high"], df["low"], df["close"], length=length)

        elif name == "STOCH":
            k = params.get("k", 14)
            d = params.get("d", 3)
            smooth_k = params.get("smooth_k", 3)
            stoch = ta.stoch(df["high"], df["low"], df["close"], k=k, d=d, smooth_k=smooth_k)
            if stoch is not None:
                df = pd.concat([df, stoch], axis=1)

        elif name == "ADX":
            length = params.get("length", 14)
            adx = ta.adx(df["high"], df["low"], df["close"], length=length)
            if adx is not None:
                df = pd.concat([df, adx], axis=1)

        elif name == "VWAP":
            df["vwap"] = ta.vwap(df["high"], df["low"], df["close"], df["volume"])

        elif name == "SUPERTREND":
            length = params.get("length", 7)
            multiplier = params.get("multiplier", 3.0)
            st = ta.supertrend(df["high"], df["low"], df["close"],
                               length=length, multiplier=multiplier)
            if st is not None:
                df = pd.concat([df, st], axis=1)

    return df


def generate_signals(df: pd.DataFrame, config: Dict[str, Any]) -> Tuple[pd.Series, pd.Series]:
    """
    Generate entry/exit signals from strategy config.
    Returns (entries, exits) as boolean Series.
    """
    rules = config.get("rules", {})
    entry_rules = rules.get("entry", [])
    exit_rules = rules.get("exit", [])

    entries = pd.Series(True, index=df.index)
    for rule in entry_rules:
        condition = _evaluate_condition(df, rule)
        entries = entries & condition

    exits = pd.Series(True, index=df.index)
    for rule in exit_rules:
        condition = _evaluate_condition(df, rule)
        exits = exits & condition

    # Clean: no entry where exit, forward fill to prevent overlapping
    entries = entries & ~exits
    entries = entries.fillna(False)
    exits = exits.fillna(False)

    return entries, exits


def _evaluate_condition(df: pd.DataFrame, rule: Dict) -> pd.Series:
    """Evaluate a single condition rule against the dataframe."""
    op = rule.get("operator", "crosses_above")
    left = _resolve_operand(df, rule.get("left"))
    right = _resolve_operand(df, rule.get("right"))

    if left is None or right is None:
        return pd.Series(False, index=df.index)

    if op == "crosses_above":
        return (left > right) & (left.shift(1) <= right.shift(1))
    elif op == "crosses_below":
        return (left < right) & (left.shift(1) >= right.shift(1))
    elif op == "greater_than":
        return left > right
    elif op == "less_than":
        return left < right
    elif op == "equals":
        return left == right
    else:
        return pd.Series(False, index=df.index)


def _resolve_operand(df: pd.DataFrame, operand) -> Optional[pd.Series]:
    """Resolve an operand — either a column name or a numeric constant."""
    if operand is None:
        return None
    if isinstance(operand, (int, float)):
        return pd.Series(operand, index=df.index)
    if isinstance(operand, str):
        if operand in df.columns:
            return df[operand]
        # Try to parse as number
        try:
            val = float(operand)
            return pd.Series(val, index=df.index)
        except ValueError:
            pass
    return None


def run_backtest(
    df: pd.DataFrame,
    entries: pd.Series,
    exits: pd.Series,
    init_cash: float = 10000.0,
    fees: float = 0.001,
    slippage: float = 0.001,
    direction: str = "long",
) -> vbt.Portfolio:
    """Run a vectorbt backtest and return the portfolio object."""
    pf = vbt.Portfolio.from_signals(
        close=df["close"],
        entries=entries,
        exits=exits,
        init_cash=init_cash,
        fees=fees,
        slippage=slippage,
        direction=direction,
        freq="1h",  # will be overridden by actual index freq
    )
    return pf


def extract_stats(pf: vbt.Portfolio, asset_name: str = "unknown") -> Dict[str, Any]:
    """Extract professional-grade statistics from a portfolio."""
    stats = pf.stats()
    total_return = pf.total_return()
    trades = pf.trades.records_readable if hasattr(pf.trades, "records_readable") else pd.DataFrame()
    num_trades = len(trades) if not isinstance(trades, type(None)) else 0

    # Safely extract values
    def safe_get(s, key, default=0.0):
        try:
            return float(s[key]) if key in s.index else default
        except (KeyError, TypeError, ValueError):
            return default

    result = {
        "asset": asset_name,
        "net_profit_pct": round(total_return * 100, 2),
        "max_drawdown_pct": round(safe_get(stats, "Max Drawdown [%]"), 2),
        "win_rate_pct": round(safe_get(stats, "Win Rate [%]"), 2),
        "profit_factor": round(safe_get(stats, "Profit Factor"), 2),
        "sharpe_ratio": round(safe_get(stats, "Sharpe Ratio"), 3),
        "sortino_ratio": round(safe_get(stats, "Sortino Ratio"), 3),
        "total_trades": num_trades,
        "total_return": round(total_return, 4),
        "start_value": round(safe_get(stats, "Start Value"), 2),
        "end_value": round(safe_get(stats, "End Value"), 2),
        "max_drawdown_duration": str(stats.get("Max Drawdown Duration", "N/A")),
        "avg_winning_trade_pct": round(safe_get(stats, "Avg Winning Trade [%]"), 2),
        "avg_losing_trade_pct": round(safe_get(stats, "Avg Losing Trade [%]"), 2),
        "best_trade_pct": round(safe_get(stats, "Best Trade [%]"), 2),
        "worst_trade_pct": round(safe_get(stats, "Worst Trade [%]"), 2),
    }
    return result


def save_equity_curve(pf: vbt.Portfolio, filepath: str):
    """Save equity curve data to CSV."""
    equity = pf.value()
    equity.to_csv(filepath)
    return filepath


def run_strategy(
    strategy_config: Dict[str, Any],
    data_files: List[str],
    init_cash: float = 10000.0,
    fees: float = 0.001,
) -> Dict[str, Any]:
    """
    Full pipeline: load data -> apply indicators -> generate signals -> backtest -> stats.
    Runs across multiple assets for multi-asset validation.
    """
    results = []
    portfolios = {}

    for filepath in data_files:
        asset_name = Path(filepath).stem.upper()
        df = load_tradingview_csv(filepath)
        df = apply_indicators(df, strategy_config)
        entries, exits = generate_signals(df, strategy_config)

        pf = run_backtest(df, entries, exits, init_cash=init_cash, fees=fees)
        stats = extract_stats(pf, asset_name)
        results.append(stats)
        portfolios[asset_name] = pf

    # Compute aggregate score
    avg_return = np.mean([r["net_profit_pct"] for r in results])
    avg_dd = np.mean([r["max_drawdown_pct"] for r in results])
    avg_sharpe = np.mean([r["sharpe_ratio"] for r in results])
    avg_win_rate = np.mean([r["win_rate_pct"] for r in results])

    summary = {
        "strategy_name": strategy_config.get("name", "unnamed"),
        "timeframe": strategy_config.get("timeframe", "unknown"),
        "assets_tested": len(data_files),
        "avg_net_profit_pct": round(avg_return, 2),
        "avg_max_drawdown_pct": round(avg_dd, 2),
        "avg_sharpe_ratio": round(avg_sharpe, 3),
        "avg_win_rate_pct": round(avg_win_rate, 2),
        "per_asset_results": results,
        "timestamp": datetime.datetime.now().isoformat(),
    }

    return summary


def compare_variants(
    variants: List[Dict[str, Any]],
    data_files: List[str],
    init_cash: float = 10000.0,
) -> List[Dict[str, Any]]:
    """
    Run multiple strategy variants and rank them.
    Returns list sorted by composite score (return/dd ratio + sharpe).
    """
    all_results = []

    for i, variant in enumerate(variants):
        variant_name = variant.get("name", f"variant_{i+1}")
        variant["name"] = variant_name
        result = run_strategy(variant, data_files, init_cash=init_cash)

        # Composite score: penalize drawdown, reward sharpe and returns
        dd = max(abs(result["avg_max_drawdown_pct"]), 0.01)
        score = (result["avg_net_profit_pct"] / dd) + result["avg_sharpe_ratio"]
        result["composite_score"] = round(score, 3)
        all_results.append(result)

    all_results.sort(key=lambda x: x["composite_score"], reverse=True)
    return all_results


def save_results(results: Dict[str, Any], name: str = None):
    """Save backtest results to workspace as JSON."""
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    if name is None:
        name = results.get("strategy_name", "result")
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = WORKSPACE / f"backtest_{name}_{ts}.json"
    with open(filepath, "w") as f:
        json.dump(results, f, indent=2, default=str)
    return str(filepath)
