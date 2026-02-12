"""
Live Market Data Feed & Briefing Engine
-----------------------------------------
Your "secretary": fetches real OHLCV data, runs the full analysis pipeline
(market structure, regime, session, volume), and produces a structured
briefing for every pair on the watchlist.

No API keys required. Uses yfinance (Yahoo Finance) for free data.

Inputs:  Watchlist from config
Outputs: Per-pair analysis + overall market brief
"""

import json
import os
import time
import traceback
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

from config import (
    WATCHLIST, WATCHLIST_LABELS, FEED_INTERVAL, FEED_LOOKBACK_DAYS,
    FEED_CACHE_SECONDS, BRIEFING_CACHE_PATH, DATA_DIR,
    RSI_PERIOD, RSI_OVERBOUGHT, RSI_OVERSOLD,
    VOLUME_MA_PERIOD, VOLUME_SPIKE_THRESHOLD,
)

# Global cache
_cache = {"timestamp": 0, "data": None}


def fetch_ohlcv(symbol: str, interval: str = FEED_INTERVAL,
                days: int = FEED_LOOKBACK_DAYS) -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV candles from Yahoo Finance.
    Returns DataFrame with columns: timestamp, open, high, low, close, volume.
    """
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        period = f"{days}d"
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            return None

        df = df.reset_index()
        # Normalize column names
        col_map = {}
        for c in df.columns:
            cl = c.lower()
            if cl in ("date", "datetime"):
                col_map[c] = "timestamp"
            elif cl == "open":
                col_map[c] = "open"
            elif cl == "high":
                col_map[c] = "high"
            elif cl == "low":
                col_map[c] = "low"
            elif cl == "close":
                col_map[c] = "close"
            elif cl == "volume":
                col_map[c] = "volume"
        df = df.rename(columns=col_map)

        required = ["open", "high", "low", "close", "volume"]
        if not all(c in df.columns for c in required):
            return None

        if "timestamp" not in df.columns:
            df["timestamp"] = df.index

        # Ensure timestamp is timezone-naive for consistency
        if hasattr(df["timestamp"].dtype, "tz") and df["timestamp"].dtype.tz is not None:
            df["timestamp"] = df["timestamp"].dt.tz_localize(None)

        return df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
    except Exception as e:
        print(f"[FEED] Error fetching {symbol}: {e}")
        return None


def compute_rsi(series: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    """Compute RSI from a price series."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(span=period, min_periods=period).mean()
    avg_loss = loss.ewm(span=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def analyze_single_pair(symbol: str) -> Optional[dict]:
    """
    Run the full analysis pipeline on one pair:
    1. Fetch OHLCV
    2. Market structure (swing, BOS, sweeps)
    3. Regime detection (trend/range, vol)
    4. Session analysis
    5. Momentum (RSI)
    6. Volume analysis
    7. Produce structured brief
    """
    df = fetch_ohlcv(symbol)
    if df is None or len(df) < 50:
        return None

    label = WATCHLIST_LABELS.get(symbol, symbol)
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last

    # --- Price action ---
    price = float(last["close"])
    change = float(last["close"] - prev["close"])
    change_pct = (change / prev["close"] * 100) if prev["close"] != 0 else 0
    day_range = float(last["high"] - last["low"])

    # --- Market Structure ---
    from market_structure import analyze_market_structure
    try:
        ms_df, bias = analyze_market_structure(df)
    except Exception:
        ms_df = df
        bias = {"bias": "neutral", "strength_pct": 0, "bos_bullish": 0, "bos_bearish": 0,
                "sweeps_bullish": 0, "sweeps_bearish": 0, "hh_count": 0, "ll_count": 0}

    # --- Regime ---
    from regime_detector import analyze_regime
    try:
        reg_df, regime = analyze_regime(df)
    except Exception:
        regime = {"current": {"trend": "unknown", "volatility": "unknown",
                              "strategy_fit": "unknown", "adx": 0},
                  "stability": "unknown", "regime_shifts_100bars": 0}

    # --- Session ---
    from session_analyzer import analyze_sessions
    try:
        sess_df, sess_stats = analyze_sessions(df)
    except Exception:
        sess_stats = {}

    # --- RSI ---
    rsi_series = compute_rsi(df["close"])
    rsi = float(rsi_series.iloc[-1]) if not rsi_series.empty and not np.isnan(rsi_series.iloc[-1]) else 50.0

    # --- Volume ---
    vol_ma = df["volume"].rolling(VOLUME_MA_PERIOD).mean()
    current_vol = float(last["volume"])
    avg_vol = float(vol_ma.iloc[-1]) if not vol_ma.empty and not np.isnan(vol_ma.iloc[-1]) else 1
    vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0

    # --- ATR ---
    tr = pd.DataFrame({
        "hl": df["high"] - df["low"],
        "hc": (df["high"] - df["close"].shift(1)).abs(),
        "lc": (df["low"] - df["close"].shift(1)).abs()
    }).max(axis=1)
    atr = float(tr.rolling(14).mean().iloc[-1]) if len(tr) >= 14 else float(tr.mean())

    # --- Build the brief ---
    current_regime = regime.get("current", {})
    trend = current_regime.get("trend", "unknown")
    vol_regime = current_regime.get("volatility", "unknown")
    adx = current_regime.get("adx", 0)
    strategy_fit = current_regime.get("strategy_fit", "unknown")

    # Determine outlook sentence
    outlook = _build_outlook(label, bias, trend, rsi, vol_ratio, adx)

    # RSI condition
    if rsi > RSI_OVERBOUGHT:
        rsi_condition = "overbought"
    elif rsi < RSI_OVERSOLD:
        rsi_condition = "oversold"
    elif rsi > 60:
        rsi_condition = "bullish"
    elif rsi < 40:
        rsi_condition = "bearish"
    else:
        rsi_condition = "neutral"

    return {
        "symbol": symbol,
        "label": label,
        "price": round(price, 5),
        "change": round(change, 5),
        "change_pct": round(change_pct, 2),
        "day_range": round(day_range, 5),
        "atr": round(atr, 5),
        "bias": bias.get("bias", "neutral"),
        "bias_strength": bias.get("strength_pct", 0),
        "trend": trend,
        "vol_regime": vol_regime,
        "adx": round(adx, 1),
        "strategy_fit": strategy_fit,
        "stability": regime.get("stability", "unknown"),
        "regime_shifts": regime.get("regime_shifts_100bars", 0),
        "rsi": round(rsi, 1),
        "rsi_condition": rsi_condition,
        "volume_ratio": round(vol_ratio, 2),
        "volume_spike": vol_ratio >= VOLUME_SPIKE_THRESHOLD,
        "bos_bullish": bias.get("bos_bullish", 0),
        "bos_bearish": bias.get("bos_bearish", 0),
        "sweeps_bullish": bias.get("sweeps_bullish", 0),
        "sweeps_bearish": bias.get("sweeps_bearish", 0),
        "hh_count": bias.get("hh_count", 0),
        "ll_count": bias.get("ll_count", 0),
        "outlook": outlook,
    }


def _build_outlook(label, bias, trend, rsi, vol_ratio, adx) -> str:
    """Generate a one-line secretary-style market read."""
    direction = bias.get("bias", "neutral")
    strength = bias.get("strength_pct", 0)

    parts = []

    # Direction
    if direction == "bullish" and strength > 60:
        parts.append(f"{label} showing strong bullish structure")
    elif direction == "bullish":
        parts.append(f"{label} leaning bullish")
    elif direction == "bearish" and strength > 60:
        parts.append(f"{label} showing strong bearish structure")
    elif direction == "bearish":
        parts.append(f"{label} leaning bearish")
    else:
        parts.append(f"{label} is neutral / choppy")

    # Trend
    if trend == "trending_up":
        parts.append("in an uptrend")
    elif trend == "trending_down":
        parts.append("in a downtrend")
    elif trend == "ranging":
        parts.append("stuck in a range")

    # RSI warning
    if rsi > RSI_OVERBOUGHT:
        parts.append("-- OVERBOUGHT, watch for pullback")
    elif rsi < RSI_OVERSOLD:
        parts.append("-- OVERSOLD, watch for bounce")

    # Volume
    if vol_ratio >= VOLUME_SPIKE_THRESHOLD:
        parts.append("with volume confirmation")

    # ADX
    if adx < 15:
        parts.append("(dead market, avoid)")
    elif adx > 40:
        parts.append("(strong momentum)")

    return ". ".join(parts) + "."


def generate_market_briefing() -> dict:
    """
    Run full analysis on all watchlist pairs.
    Returns structured briefing with per-pair analysis + summary.
    """
    # Check cache
    if _cache["data"] and (time.time() - _cache["timestamp"]) < FEED_CACHE_SECONDS:
        return _cache["data"]

    now = datetime.utcnow()
    pairs = []
    bullish_count = 0
    bearish_count = 0
    trending_count = 0
    ranging_count = 0
    errors = []

    for symbol in WATCHLIST:
        try:
            analysis = analyze_single_pair(symbol)
            if analysis:
                pairs.append(analysis)
                if analysis["bias"] == "bullish":
                    bullish_count += 1
                elif analysis["bias"] == "bearish":
                    bearish_count += 1
                if analysis["trend"] in ("trending_up", "trending_down"):
                    trending_count += 1
                elif analysis["trend"] == "ranging":
                    ranging_count += 1
            else:
                errors.append(f"{symbol}: no data")
        except Exception as e:
            errors.append(f"{symbol}: {str(e)[:60]}")

    # Session context
    hour = now.hour
    if 0 <= hour < 8:
        session = "Asia"
        session_note = "Low volatility expected. Mean-reversion setups favored."
    elif 7 <= hour < 12:
        session = "London"
        session_note = "Peak liquidity. Breakouts and momentum plays are live."
    elif 12 <= hour < 16:
        session = "London/NY Overlap"
        session_note = "Maximum liquidity. Highest probability window."
    elif 16 <= hour < 21:
        session = "New York"
        session_note = "Good liquidity. Watch for late-day reversals."
    else:
        session = "Off-Hours"
        session_note = "Low liquidity. Spreads widen. Avoid new entries."

    # Sort by absolute change for "movers" section
    movers = sorted(pairs, key=lambda p: abs(p["change_pct"]), reverse=True)

    # Overall market sentiment
    total = len(pairs)
    if total > 0:
        bull_pct = bullish_count / total * 100
        bear_pct = bearish_count / total * 100
    else:
        bull_pct = bear_pct = 0

    if bull_pct > 60:
        market_mood = "RISK-ON"
        mood_detail = "Majority of pairs showing bullish structure. Look for long setups."
    elif bear_pct > 60:
        market_mood = "RISK-OFF"
        mood_detail = "Majority of pairs showing bearish structure. Look for short setups or stay flat."
    else:
        market_mood = "MIXED"
        mood_detail = "No clear directional consensus. Be selective, reduce size."

    briefing = {
        "timestamp": now.isoformat(),
        "session": session,
        "session_note": session_note,
        "market_mood": market_mood,
        "mood_detail": mood_detail,
        "summary": {
            "total_pairs": total,
            "bullish": bullish_count,
            "bearish": bearish_count,
            "neutral": total - bullish_count - bearish_count,
            "trending": trending_count,
            "ranging": ranging_count,
            "bull_pct": round(bull_pct, 0),
            "bear_pct": round(bear_pct, 0),
        },
        "top_movers": [
            {"label": m["label"], "change_pct": m["change_pct"],
             "bias": m["bias"], "outlook": m["outlook"]}
            for m in movers[:5]
        ],
        "pairs": pairs,
        "errors": errors,
    }

    # Update cache
    _cache["timestamp"] = time.time()
    _cache["data"] = briefing

    # Persist to disk
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(str(BRIEFING_CACHE_PATH), "w") as f:
            json.dump(briefing, f, indent=2, default=str)
    except IOError:
        pass

    return briefing


def get_pair_analysis(symbol: str) -> Optional[dict]:
    """Get analysis for a single pair (uses cached briefing if fresh)."""
    briefing = generate_market_briefing()
    for pair in briefing.get("pairs", []):
        if pair["symbol"] == symbol or pair["label"] == symbol:
            return pair
    # Not in cache, try direct fetch
    return analyze_single_pair(symbol)


if __name__ == "__main__":
    print("Fetching market briefing...\n")
    brief = generate_market_briefing()
    print(f"Session: {brief['session']}")
    print(f"Market Mood: {brief['market_mood']} — {brief['mood_detail']}")
    print(f"Bullish: {brief['summary']['bullish']} | Bearish: {brief['summary']['bearish']} | Neutral: {brief['summary']['neutral']}")
    print(f"\nTop Movers:")
    for m in brief["top_movers"]:
        arrow = "^" if m["change_pct"] > 0 else "v"
        print(f"  {m['label']}: {m['change_pct']:+.2f}% {arrow}  [{m['bias']}]")
    print(f"\nDetailed Analysis:")
    for p in brief["pairs"]:
        print(f"\n  {p['label']} @ {p['price']}")
        print(f"    {p['outlook']}")
        print(f"    Bias: {p['bias']} ({p['bias_strength']}%) | Trend: {p['trend']} | ADX: {p['adx']}")
        print(f"    RSI: {p['rsi']} ({p['rsi_condition']}) | Vol: {p['volume_ratio']}x {'SPIKE' if p['volume_spike'] else ''}")
    if brief["errors"]:
        print(f"\n  Errors: {brief['errors']}")
