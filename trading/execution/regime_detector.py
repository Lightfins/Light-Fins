"""
Regime Detection Engine
-----------------------
Classifies market state into regimes:
  - Trending Up / Trending Down / Ranging
  - High Volatility / Low Volatility
  - Momentum / Mean-Reversion favorable

Uses ADX, Bollinger Band width, ATR percentile, and directional movement.
Regime shifts are the #1 strategy killer — this module exists to prevent that.

Inputs:  OHLCV DataFrame
Outputs: DataFrame with regime labels + regime summary
"""

import numpy as np
import pandas as pd
from config import (
    ADX_PERIOD, ADX_TREND_THRESHOLD, VOLATILITY_LOOKBACK,
    REGIME_SMOOTHING, BBANDS_PERIOD, BBANDS_STD, ATR_PERIOD
)


def compute_adx(df: pd.DataFrame, period: int = ADX_PERIOD) -> pd.DataFrame:
    """Compute Average Directional Index (ADX) with +DI and -DI."""
    df = df.copy()
    high = df["high"]
    low = df["low"]
    close = df["close"]

    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    tr = pd.DataFrame({
        "hl": high - low,
        "hc": (high - close.shift(1)).abs(),
        "lc": (low - close.shift(1)).abs()
    }).max(axis=1)

    atr = tr.ewm(span=period, min_periods=period).mean()
    plus_di = 100 * plus_dm.ewm(span=period, min_periods=period).mean() / atr
    minus_di = 100 * minus_dm.ewm(span=period, min_periods=period).mean() / atr

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(span=period, min_periods=period).mean()

    df["adx"] = adx
    df["plus_di"] = plus_di
    df["minus_di"] = minus_di

    return df


def compute_bollinger_width(df: pd.DataFrame, period: int = BBANDS_PERIOD, std: float = BBANDS_STD) -> pd.DataFrame:
    """Bollinger Band width as a volatility regime indicator."""
    df = df.copy()
    ma = df["close"].rolling(period).mean()
    sd = df["close"].rolling(period).std()
    upper = ma + std * sd
    lower = ma - std * sd

    df["bb_upper"] = upper
    df["bb_lower"] = lower
    df["bb_mid"] = ma
    df["bb_width"] = (upper - lower) / ma * 100  # width as % of price

    return df


def compute_atr_regime(df: pd.DataFrame, period: int = ATR_PERIOD, lookback: int = VOLATILITY_LOOKBACK) -> pd.DataFrame:
    """ATR percentile rank over lookback — measures volatility regime."""
    df = df.copy()
    tr = pd.DataFrame({
        "hl": df["high"] - df["low"],
        "hc": (df["high"] - df["close"].shift(1)).abs(),
        "lc": (df["low"] - df["close"].shift(1)).abs()
    }).max(axis=1)

    atr = tr.rolling(period).mean()
    df["atr"] = atr

    # Percentile rank of current ATR vs recent history
    df["atr_percentile"] = atr.rolling(lookback * 5).apply(
        lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100 if len(x) > 1 else 50,
        raw=False
    )

    return df


def classify_regime(df: pd.DataFrame) -> pd.DataFrame:
    """
    Classify each bar into a regime:
    - trend_regime: "trending_up", "trending_down", "ranging"
    - vol_regime: "high_vol", "low_vol", "normal_vol"
    - strategy_fit: "momentum", "mean_reversion", "neutral"
    """
    df = df.copy()

    # Trend regime (ADX-based)
    df["trend_regime"] = "ranging"
    trending = df["adx"] >= ADX_TREND_THRESHOLD
    bullish = df["plus_di"] > df["minus_di"]
    df.loc[trending & bullish, "trend_regime"] = "trending_up"
    df.loc[trending & ~bullish, "trend_regime"] = "trending_down"

    # Volatility regime (ATR percentile-based)
    df["vol_regime"] = "normal_vol"
    df.loc[df["atr_percentile"] >= 75, "vol_regime"] = "high_vol"
    df.loc[df["atr_percentile"] <= 25, "vol_regime"] = "low_vol"

    # Strategy fit
    df["strategy_fit"] = "neutral"
    # Trending + normal/high vol = momentum plays
    df.loc[
        (df["trend_regime"].isin(["trending_up", "trending_down"])) &
        (df["vol_regime"].isin(["normal_vol", "high_vol"])),
        "strategy_fit"
    ] = "momentum"
    # Ranging + low/normal vol = mean-reversion plays
    df.loc[
        (df["trend_regime"] == "ranging") &
        (df["vol_regime"].isin(["low_vol", "normal_vol"])),
        "strategy_fit"
    ] = "mean_reversion"

    return df


def detect_regime_shifts(df: pd.DataFrame, smoothing: int = REGIME_SMOOTHING) -> pd.DataFrame:
    """
    Detect when the regime changes — these transitions are danger zones.
    Many strategies break at regime boundaries.
    """
    df = df.copy()
    df["regime_shift"] = False
    df["regime_shift_type"] = ""

    prev_trend = None
    prev_vol = None

    for i in range(len(df)):
        curr_trend = df.iloc[i]["trend_regime"]
        curr_vol = df.iloc[i]["vol_regime"]

        if prev_trend is not None:
            if curr_trend != prev_trend:
                df.iloc[i, df.columns.get_loc("regime_shift")] = True
                df.iloc[i, df.columns.get_loc("regime_shift_type")] = f"trend:{prev_trend}->{curr_trend}"
            elif curr_vol != prev_vol:
                df.iloc[i, df.columns.get_loc("regime_shift")] = True
                df.iloc[i, df.columns.get_loc("regime_shift_type")] = f"vol:{prev_vol}->{curr_vol}"

        prev_trend = curr_trend
        prev_vol = curr_vol

    return df


def regime_summary(df: pd.DataFrame) -> dict:
    """Summarize regime distribution and shift frequency."""
    recent = df.tail(100)
    total = len(recent)

    trend_dist = recent["trend_regime"].value_counts(normalize=True).to_dict()
    vol_dist = recent["vol_regime"].value_counts(normalize=True).to_dict()
    fit_dist = recent["strategy_fit"].value_counts(normalize=True).to_dict()
    shift_count = recent["regime_shift"].sum()

    current_trend = recent.iloc[-1]["trend_regime"] if len(recent) > 0 else "unknown"
    current_vol = recent.iloc[-1]["vol_regime"] if len(recent) > 0 else "unknown"
    current_fit = recent.iloc[-1]["strategy_fit"] if len(recent) > 0 else "unknown"
    current_adx = float(recent.iloc[-1]["adx"]) if len(recent) > 0 else 0

    return {
        "current": {
            "trend": current_trend,
            "volatility": current_vol,
            "strategy_fit": current_fit,
            "adx": round(current_adx, 2),
        },
        "distribution_100bars": {
            "trend": {k: round(v * 100, 1) for k, v in trend_dist.items()},
            "volatility": {k: round(v * 100, 1) for k, v in vol_dist.items()},
            "strategy_fit": {k: round(v * 100, 1) for k, v in fit_dist.items()},
        },
        "regime_shifts_100bars": int(shift_count),
        "stability": "stable" if shift_count < 5 else "unstable" if shift_count > 15 else "moderate",
    }


def analyze_regime(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Full regime analysis pipeline."""
    df = compute_adx(df)
    df = compute_bollinger_width(df)
    df = compute_atr_regime(df)
    df = classify_regime(df)
    df = detect_regime_shifts(df)
    summary = regime_summary(df)
    return df, summary


if __name__ == "__main__":
    np.random.seed(42)
    n = 500
    # Simulate trending then ranging market
    trend = np.cumsum(np.random.randn(250) * 0.001 + 0.0003)
    ranging = np.cumsum(np.random.randn(250) * 0.0005)
    prices = 1.1000 + np.concatenate([trend, ranging + trend[-1]])

    data = {
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="1h"),
        "open": prices,
        "high": prices + np.abs(np.random.randn(n) * 0.0005),
        "low": prices - np.abs(np.random.randn(n) * 0.0005),
        "close": prices + np.random.randn(n) * 0.0003,
        "volume": np.random.randint(100, 10000, n),
    }
    df = pd.DataFrame(data)
    result, summary = analyze_regime(df)
    import json
    print(json.dumps(summary, indent=2))
