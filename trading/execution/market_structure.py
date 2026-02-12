"""
Market Structure Detection Engine
---------------------------------
Detects: Swing Highs/Lows, Higher Highs/Lower Lows, Break of Structure,
Liquidity Sweeps, and overall market bias.

Inputs:  OHLCV DataFrame (columns: open, high, low, close, volume, timestamp)
Outputs: Annotated DataFrame with structure labels + summary dict
"""

import numpy as np
import pandas as pd
from typing import Optional
from config import SWING_LOOKBACK, BOS_MIN_BARS, LIQUIDITY_SWEEP_TOLERANCE


def detect_swing_points(df: pd.DataFrame, lookback: int = SWING_LOOKBACK) -> pd.DataFrame:
    """
    Identify swing highs and swing lows using a rolling window.
    A swing high is a bar whose high is the highest in [i-lookback, i+lookback].
    A swing low is a bar whose low is the lowest in [i-lookback, i+lookback].
    """
    df = df.copy()
    df["swing_high"] = False
    df["swing_low"] = False
    df["swing_high_price"] = np.nan
    df["swing_low_price"] = np.nan

    highs = df["high"].values
    lows = df["low"].values

    for i in range(lookback, len(df) - lookback):
        window_high = highs[i - lookback: i + lookback + 1]
        window_low = lows[i - lookback: i + lookback + 1]

        if highs[i] == window_high.max():
            df.iloc[i, df.columns.get_loc("swing_high")] = True
            df.iloc[i, df.columns.get_loc("swing_high_price")] = highs[i]

        if lows[i] == window_low.min():
            df.iloc[i, df.columns.get_loc("swing_low")] = True
            df.iloc[i, df.columns.get_loc("swing_low_price")] = lows[i]

    return df


def classify_structure(df: pd.DataFrame) -> pd.DataFrame:
    """
    Label swing points as HH (Higher High), HL (Higher Low),
    LH (Lower High), LL (Lower Low).
    """
    df = df.copy()
    df["structure_label"] = ""

    swing_highs = df[df["swing_high"]].copy()
    swing_lows = df[df["swing_low"]].copy()

    # Classify highs
    prev_high = None
    for idx in swing_highs.index:
        price = df.loc[idx, "swing_high_price"]
        if prev_high is not None:
            df.loc[idx, "structure_label"] = "HH" if price > prev_high else "LH"
        prev_high = price

    # Classify lows
    prev_low = None
    for idx in swing_lows.index:
        price = df.loc[idx, "swing_low_price"]
        if prev_low is not None:
            label = df.loc[idx, "structure_label"]
            low_label = "HL" if price > prev_low else "LL"
            df.loc[idx, "structure_label"] = (
                f"{label}/{low_label}" if label else low_label
            )
        prev_low = price

    return df


def detect_break_of_structure(df: pd.DataFrame, min_bars: int = BOS_MIN_BARS) -> pd.DataFrame:
    """
    Detect Break of Structure (BOS):
    - Bullish BOS: price closes above the last swing high
    - Bearish BOS: price closes below the last swing low
    """
    df = df.copy()
    df["bos"] = ""
    df["bos_level"] = np.nan

    last_swing_high = None
    last_swing_high_idx = None
    last_swing_low = None
    last_swing_low_idx = None

    for i in range(len(df)):
        if df.iloc[i]["swing_high"]:
            last_swing_high = df.iloc[i]["swing_high_price"]
            last_swing_high_idx = i

        if df.iloc[i]["swing_low"]:
            last_swing_low = df.iloc[i]["swing_low_price"]
            last_swing_low_idx = i

        # Bullish BOS
        if (last_swing_high is not None and last_swing_high_idx is not None
                and i - last_swing_high_idx >= min_bars
                and df.iloc[i]["close"] > last_swing_high):
            df.iloc[i, df.columns.get_loc("bos")] = "bullish"
            df.iloc[i, df.columns.get_loc("bos_level")] = last_swing_high
            last_swing_high = df.iloc[i]["high"]
            last_swing_high_idx = i

        # Bearish BOS
        if (last_swing_low is not None and last_swing_low_idx is not None
                and i - last_swing_low_idx >= min_bars
                and df.iloc[i]["close"] < last_swing_low):
            df.iloc[i, df.columns.get_loc("bos")] = "bearish"
            df.iloc[i, df.columns.get_loc("bos_level")] = last_swing_low
            last_swing_low = df.iloc[i]["low"]
            last_swing_low_idx = i

    return df


def detect_liquidity_sweeps(df: pd.DataFrame, tolerance: float = LIQUIDITY_SWEEP_TOLERANCE) -> pd.DataFrame:
    """
    Detect liquidity sweeps: price spikes beyond a swing level then reverses.
    - Bullish sweep: wick below swing low, close above it (stop hunt below)
    - Bearish sweep: wick above swing high, close below it (stop hunt above)
    """
    df = df.copy()
    df["liquidity_sweep"] = ""
    df["sweep_level"] = np.nan

    swing_high_levels = []
    swing_low_levels = []

    for i in range(len(df)):
        if df.iloc[i]["swing_high"]:
            swing_high_levels.append(df.iloc[i]["swing_high_price"])
        if df.iloc[i]["swing_low"]:
            swing_low_levels.append(df.iloc[i]["swing_low_price"])

        low = df.iloc[i]["low"]
        high = df.iloc[i]["high"]
        close = df.iloc[i]["close"]

        # Check for bearish sweep (above swing high, close back below)
        for level in reversed(swing_high_levels[-10:]):
            if high > level * (1 + tolerance) and close < level:
                df.iloc[i, df.columns.get_loc("liquidity_sweep")] = "bearish_sweep"
                df.iloc[i, df.columns.get_loc("sweep_level")] = level
                break

        # Check for bullish sweep (below swing low, close back above)
        for level in reversed(swing_low_levels[-10:]):
            if low < level * (1 - tolerance) and close > level:
                df.iloc[i, df.columns.get_loc("liquidity_sweep")] = "bullish_sweep"
                df.iloc[i, df.columns.get_loc("sweep_level")] = level
                break

    return df


def compute_market_bias(df: pd.DataFrame) -> dict:
    """
    Determine overall market bias from structure labels.
    Returns bias dict: {bias, strength, hh_count, ll_count, bos_bullish, bos_bearish}
    """
    recent = df.tail(50)

    hh_count = recent["structure_label"].str.contains("HH", na=False).sum()
    hl_count = recent["structure_label"].str.contains("HL", na=False).sum()
    lh_count = recent["structure_label"].str.contains("LH", na=False).sum()
    ll_count = recent["structure_label"].str.contains("LL", na=False).sum()
    bos_bull = (recent["bos"] == "bullish").sum()
    bos_bear = (recent["bos"] == "bearish").sum()
    sweeps_bull = (recent["liquidity_sweep"] == "bullish_sweep").sum()
    sweeps_bear = (recent["liquidity_sweep"] == "bearish_sweep").sum()

    bull_score = hh_count * 2 + hl_count + bos_bull * 3 + sweeps_bull * 2
    bear_score = ll_count * 2 + lh_count + bos_bear * 3 + sweeps_bear * 2

    total = bull_score + bear_score
    if total == 0:
        bias = "neutral"
        strength = 0.0
    elif bull_score > bear_score:
        bias = "bullish"
        strength = round(bull_score / total * 100, 1)
    else:
        bias = "bearish"
        strength = round(bear_score / total * 100, 1)

    return {
        "bias": bias,
        "strength_pct": strength,
        "hh_count": int(hh_count),
        "hl_count": int(hl_count),
        "lh_count": int(lh_count),
        "ll_count": int(ll_count),
        "bos_bullish": int(bos_bull),
        "bos_bearish": int(bos_bear),
        "sweeps_bullish": int(sweeps_bull),
        "sweeps_bearish": int(sweeps_bear),
    }


def analyze_market_structure(df: pd.DataFrame, lookback: int = SWING_LOOKBACK) -> tuple[pd.DataFrame, dict]:
    """
    Full pipeline: swing detection -> classification -> BOS -> liquidity sweeps -> bias.
    Returns (annotated_df, bias_summary).
    """
    df = detect_swing_points(df, lookback)
    df = classify_structure(df)
    df = detect_break_of_structure(df)
    df = detect_liquidity_sweeps(df)
    bias = compute_market_bias(df)
    return df, bias


if __name__ == "__main__":
    # Quick smoke test with synthetic data
    np.random.seed(42)
    n = 200
    prices = 1.1000 + np.cumsum(np.random.randn(n) * 0.001)
    data = {
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="1h"),
        "open": prices,
        "high": prices + np.abs(np.random.randn(n) * 0.0005),
        "low": prices - np.abs(np.random.randn(n) * 0.0005),
        "close": prices + np.random.randn(n) * 0.0003,
        "volume": np.random.randint(100, 10000, n),
    }
    df = pd.DataFrame(data)
    result, bias = analyze_market_structure(df)
    print(f"Bias: {bias}")
    print(f"Swing Highs: {result['swing_high'].sum()}")
    print(f"Swing Lows: {result['swing_low'].sum()}")
    print(f"BOS events: {(result['bos'] != '').sum()}")
    print(f"Liquidity sweeps: {(result['liquidity_sweep'] != '').sum()}")
