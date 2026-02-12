"""
Session-Based Behavior Analyzer
--------------------------------
Segments market data by trading session (Asia, London, NY),
measures per-session volatility, volume, and directional bias.
Detects session-based edge: which sessions are profitable, which are traps.

Inputs:  OHLCV DataFrame with UTC timestamps
Outputs: Session-annotated DataFrame + session performance metrics
"""

import numpy as np
import pandas as pd
from datetime import time
from config import SESSIONS, SESSION_OVERLAP, ATR_PERIOD


def label_sessions(df: pd.DataFrame) -> pd.DataFrame:
    """Tag each bar with its trading session(s)."""
    df = df.copy()
    df["session"] = "off_hours"

    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    hours = df["timestamp"].dt.hour
    minutes = df["timestamp"].dt.minute
    time_decimal = hours + minutes / 60.0

    for session_key, session_info in SESSIONS.items():
        start_h, start_m = map(int, session_info["start"].split(":"))
        end_h, end_m = map(int, session_info["end"].split(":"))
        start_dec = start_h + start_m / 60.0
        end_dec = end_h + end_m / 60.0

        mask = (time_decimal >= start_dec) & (time_decimal < end_dec)
        df.loc[mask, "session"] = session_key

    # Mark overlaps (London/NY overlap takes priority labeling)
    for overlap_key, overlap_info in SESSION_OVERLAP.items():
        start_h, start_m = map(int, overlap_info["start"].split(":"))
        end_h, end_m = map(int, overlap_info["end"].split(":"))
        start_dec = start_h + start_m / 60.0
        end_dec = end_h + end_m / 60.0

        mask = (time_decimal >= start_dec) & (time_decimal < end_dec)
        df.loc[mask, "session_overlap"] = overlap_key

    if "session_overlap" not in df.columns:
        df["session_overlap"] = ""

    return df


def compute_session_volatility(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-bar true range and session-level ATR."""
    df = df.copy()
    df["true_range"] = np.maximum(
        df["high"] - df["low"],
        np.maximum(
            np.abs(df["high"] - df["close"].shift(1)),
            np.abs(df["low"] - df["close"].shift(1))
        )
    )
    df["tr_pct"] = df["true_range"] / df["close"] * 100
    return df


def session_statistics(df: pd.DataFrame) -> dict:
    """
    Compute per-session statistics:
    - Average range (volatility)
    - Average volume
    - Directional bias (% of bars that closed up)
    - Best/worst session by various metrics
    """
    stats = {}
    for session in ["asia", "london", "ny"]:
        session_data = df[df["session"] == session]
        if len(session_data) == 0:
            continue

        close_up = (session_data["close"] > session_data["open"]).mean() * 100
        avg_range = session_data["true_range"].mean()
        avg_range_pct = session_data["tr_pct"].mean()
        avg_volume = session_data["volume"].mean()
        max_range = session_data["true_range"].max()

        # Session open-to-close movement
        if len(session_data) > 1:
            session_groups = session_data.groupby(session_data["timestamp"].dt.date)
            daily_moves = []
            for date, group in session_groups:
                if len(group) >= 2:
                    move = (group.iloc[-1]["close"] - group.iloc[0]["open"]) / group.iloc[0]["open"] * 100
                    daily_moves.append(move)
            avg_move = np.mean(daily_moves) if daily_moves else 0
            move_std = np.std(daily_moves) if daily_moves else 0
        else:
            avg_move = 0
            move_std = 0

        stats[session] = {
            "label": SESSIONS[session]["label"],
            "bar_count": len(session_data),
            "avg_range": round(float(avg_range), 6),
            "avg_range_pct": round(float(avg_range_pct), 4),
            "max_range": round(float(max_range), 6),
            "avg_volume": round(float(avg_volume), 0),
            "bullish_pct": round(float(close_up), 1),
            "avg_daily_move_pct": round(float(avg_move), 4),
            "daily_move_std": round(float(move_std), 4),
        }

    # Rank sessions
    if stats:
        most_volatile = max(stats, key=lambda s: stats[s]["avg_range_pct"])
        least_volatile = min(stats, key=lambda s: stats[s]["avg_range_pct"])
        most_directional = max(stats, key=lambda s: abs(stats[s]["avg_daily_move_pct"]))

        stats["_rankings"] = {
            "most_volatile": most_volatile,
            "least_volatile": least_volatile,
            "most_directional": most_directional,
        }

    return stats


def detect_session_transitions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mark session open/close transitions. These are high-probability
    zones for fakeouts, stop hunts, and volatility spikes.
    """
    df = df.copy()
    df["session_transition"] = ""

    prev_session = None
    for i in range(len(df)):
        current_session = df.iloc[i]["session"]
        if prev_session is not None and current_session != prev_session:
            df.iloc[i, df.columns.get_loc("session_transition")] = f"{prev_session}_to_{current_session}"
        prev_session = current_session

    return df


def analyze_sessions(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Full session analysis pipeline.
    Returns (annotated_df, session_stats_dict).
    """
    df = label_sessions(df)
    df = compute_session_volatility(df)
    df = detect_session_transitions(df)
    stats = session_statistics(df)
    return df, stats


if __name__ == "__main__":
    np.random.seed(42)
    n = 500
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
    result, stats = analyze_sessions(df)
    for session, s in stats.items():
        if session.startswith("_"):
            continue
        print(f"\n{s['label']}:")
        for k, v in s.items():
            if k != "label":
                print(f"  {k}: {v}")
    if "_rankings" in stats:
        print(f"\nRankings: {stats['_rankings']}")
