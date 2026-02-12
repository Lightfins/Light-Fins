"""
Probabilistic Trade Scoring Engine
-----------------------------------
Scores each potential trade on a 0-100 confidence scale.
Aggregates signals from: market structure, regime, session, volume, momentum.

This is the GATE — no trade enters without a score.
Low-confidence trades get filtered. High-confidence trades get sized up.

Inputs:  Signal dict from various analyzers
Outputs: Score (0-100), confidence tier, component breakdown
"""

import numpy as np
from config import (
    CONFIDENCE_LOW, CONFIDENCE_MEDIUM, CONFIDENCE_HIGH,
    MIN_CONFIDENCE_TO_TRADE, VOLUME_SPIKE_THRESHOLD,
    RSI_OVERBOUGHT, RSI_OVERSOLD,
    HTF_BIAS_PENALTY, HTF_NEUTRAL_PENALTY,
    NEWS_BLACKOUT_MINUTES
)


# Weight allocation for scoring components (must sum to 100)
SCORE_WEIGHTS = {
    "htf_alignment": 15,      # higher timeframe bias confirmation (FIX #1)
    "market_structure": 20,   # HH/HL/BOS alignment
    "regime_alignment": 15,   # strategy fits current regime
    "session_quality": 10,    # trading in good session
    "volume_confirmation": 10, # volume confirms the move
    "momentum_alignment": 10, # RSI/MACD support
    "risk_reward": 10,        # R:R ratio quality
    "news_filter": 10,        # economic calendar filter (FIX #3)
}


def score_htf_alignment(signals: dict) -> float:
    """
    Score based on higher-timeframe bias confirmation (0-100).
    FIX #1: The #1 reason for false signals is trading against the HTF trend.
    A 1H bullish BOS means nothing if the Daily is bearish.
    """
    score = 50.0

    htf_bias = signals.get("htf_bias", "unknown")  # bullish / bearish / neutral / unknown
    trade_direction = signals.get("trade_direction", "long")
    htf_bos = signals.get("htf_bos", "")  # bullish / bearish from HTF

    if htf_bias == "unknown":
        # No HTF data available — mild penalty, not a kill
        return 40.0

    # Direction alignment with HTF bias
    if htf_bias == "bullish" and trade_direction == "long":
        score += 30
    elif htf_bias == "bearish" and trade_direction == "short":
        score += 30
    elif htf_bias == "neutral":
        score -= HTF_NEUTRAL_PENALTY
    else:
        # Trading AGAINST higher timeframe = major penalty
        score -= HTF_BIAS_PENALTY

    # HTF BOS confirmation (extra strong signal)
    if htf_bos == "bullish" and trade_direction == "long":
        score += 20
    elif htf_bos == "bearish" and trade_direction == "short":
        score += 20
    elif htf_bos and htf_bos != "":
        score -= 15  # HTF BOS in opposite direction

    return np.clip(score, 0, 100)


def score_news_filter(signals: dict) -> float:
    """
    Score based on economic calendar proximity (0-100).
    FIX #3: High-impact news events create unmodelable volatility.
    No amount of technical analysis survives NFP/FOMC/CPI surprises.
    """
    news_minutes = signals.get("minutes_to_news", None)
    news_impact = signals.get("news_impact", "none")  # high / medium / low / none

    # No news data available — neutral score
    if news_minutes is None and news_impact == "none":
        return 70.0

    # Inside blackout zone for high-impact events
    if news_impact == "high" and news_minutes is not None:
        if abs(news_minutes) <= NEWS_BLACKOUT_MINUTES:
            return 0.0  # ABSOLUTE KILL — no trading near red events
        elif abs(news_minutes) <= NEWS_BLACKOUT_MINUTES * 2:
            return 25.0  # danger zone
        else:
            return 80.0  # far enough away

    # Medium impact events — warning but not kill
    if news_impact == "medium" and news_minutes is not None:
        if abs(news_minutes) <= 15:
            return 30.0
        else:
            return 70.0

    return 75.0  # no news or low impact


def score_market_structure(signals: dict) -> float:
    """Score based on market structure alignment (0-100)."""
    score = 50.0  # neutral baseline

    bias = signals.get("market_bias", "neutral")
    trade_direction = signals.get("trade_direction", "long")
    bos = signals.get("bos", "")
    sweep = signals.get("liquidity_sweep", "")
    structure_label = signals.get("structure_label", "")

    # Direction alignment with bias
    if bias == "bullish" and trade_direction == "long":
        score += 20
    elif bias == "bearish" and trade_direction == "short":
        score += 20
    elif bias == "neutral":
        score += 0
    else:
        score -= 25  # trading against bias

    # BOS confirmation
    if bos == "bullish" and trade_direction == "long":
        score += 15
    elif bos == "bearish" and trade_direction == "short":
        score += 15
    elif bos:
        score -= 10

    # Liquidity sweep (powerful reversal signal)
    if sweep == "bullish_sweep" and trade_direction == "long":
        score += 15
    elif sweep == "bearish_sweep" and trade_direction == "short":
        score += 15

    # Structure continuation
    if "HH" in structure_label and trade_direction == "long":
        score += 5
    elif "LL" in structure_label and trade_direction == "short":
        score += 5

    return np.clip(score, 0, 100)


def score_regime_alignment(signals: dict) -> float:
    """Score based on regime-strategy fit (0-100)."""
    score = 50.0

    strategy_type = signals.get("strategy_type", "momentum")  # momentum or mean_reversion
    regime_fit = signals.get("regime_fit", "neutral")
    regime_stability = signals.get("regime_stability", "moderate")
    trend_regime = signals.get("trend_regime", "ranging")

    # Perfect fit
    if strategy_type == regime_fit:
        score += 30
    elif regime_fit == "neutral":
        score += 0
    else:
        score -= 30  # momentum strategy in mean-reversion regime = danger

    # Stability bonus/penalty
    if regime_stability == "stable":
        score += 15
    elif regime_stability == "unstable":
        score -= 20  # regime shifting = unreliable signals

    # Trending bonus for momentum
    if strategy_type == "momentum":
        if trend_regime in ["trending_up", "trending_down"]:
            score += 10

    return np.clip(score, 0, 100)


def score_session_quality(signals: dict) -> float:
    """Score based on session timing (0-100)."""
    score = 50.0

    session = signals.get("session", "off_hours")
    session_overlap = signals.get("session_overlap", "")
    is_transition = signals.get("is_session_transition", False)

    # Session quality
    if session == "london":
        score += 25  # highest liquidity, cleanest moves
    elif session == "ny":
        score += 20
    elif session == "asia":
        score += 5   # low volatility, range-bound
    else:
        score -= 20  # off-hours = low liquidity traps

    # Overlap bonus
    if session_overlap == "london_ny":
        score += 15  # peak liquidity

    # Transition penalty
    if is_transition:
        score -= 15  # session opens are noisy

    return np.clip(score, 0, 100)


def score_volume_confirmation(signals: dict) -> float:
    """Score based on volume confirmation (0-100)."""
    score = 50.0

    volume_ratio = signals.get("volume_ratio", 1.0)  # current vol / avg vol
    volume_trend = signals.get("volume_trend", "flat")  # increasing / decreasing / flat

    if volume_ratio >= VOLUME_SPIKE_THRESHOLD:
        score += 25  # strong volume confirms move
    elif volume_ratio >= 1.0:
        score += 10
    else:
        score -= 15  # low volume = weak conviction

    # Volume trend
    if volume_trend == "increasing":
        score += 15
    elif volume_trend == "decreasing":
        score -= 10

    return np.clip(score, 0, 100)


def score_momentum_alignment(signals: dict) -> float:
    """Score based on momentum indicators (0-100)."""
    score = 50.0

    rsi = signals.get("rsi", 50)
    macd_signal = signals.get("macd_signal", "neutral")  # bullish / bearish / neutral
    trade_direction = signals.get("trade_direction", "long")

    # RSI alignment
    if trade_direction == "long":
        if rsi < RSI_OVERSOLD:
            score += 20  # oversold bounce opportunity
        elif rsi < 50:
            score += 10  # below midline, room to run
        elif rsi > RSI_OVERBOUGHT:
            score -= 20  # overbought, risky long
    else:  # short
        if rsi > RSI_OVERBOUGHT:
            score += 20
        elif rsi > 50:
            score += 10
        elif rsi < RSI_OVERSOLD:
            score -= 20

    # MACD alignment
    if macd_signal == "bullish" and trade_direction == "long":
        score += 15
    elif macd_signal == "bearish" and trade_direction == "short":
        score += 15
    elif macd_signal != "neutral":
        score -= 10

    return np.clip(score, 0, 100)


def score_risk_reward(signals: dict) -> float:
    """Score based on risk-reward ratio (0-100)."""
    rr_ratio = signals.get("risk_reward_ratio", 1.0)

    if rr_ratio >= 4.0:
        return 95
    elif rr_ratio >= 3.0:
        return 85
    elif rr_ratio >= 2.5:
        return 75
    elif rr_ratio >= 2.0:
        return 65
    elif rr_ratio >= 1.5:
        return 50
    elif rr_ratio >= 1.0:
        return 30
    else:
        return 10  # sub 1:1 RR is almost never worth it


def compute_trade_score(signals: dict) -> dict:
    """
    Compute weighted composite score from all components.
    Returns full breakdown + final verdict.
    """
    components = {
        "htf_alignment": score_htf_alignment(signals),
        "market_structure": score_market_structure(signals),
        "regime_alignment": score_regime_alignment(signals),
        "session_quality": score_session_quality(signals),
        "volume_confirmation": score_volume_confirmation(signals),
        "momentum_alignment": score_momentum_alignment(signals),
        "risk_reward": score_risk_reward(signals),
        "news_filter": score_news_filter(signals),
    }

    # Weighted composite
    total = sum(
        components[k] * SCORE_WEIGHTS[k] / 100
        for k in components
    )
    total = round(np.clip(total, 0, 100), 1)

    # Confidence tier
    if total >= CONFIDENCE_HIGH:
        tier = "HIGH"
    elif total >= CONFIDENCE_MEDIUM:
        tier = "MEDIUM"
    elif total >= CONFIDENCE_LOW:
        tier = "LOW"
    else:
        tier = "NO_TRADE"

    # Kill signals — any single component below 20 is a red flag
    red_flags = [k for k, v in components.items() if v < 20]

    tradeable = total >= MIN_CONFIDENCE_TO_TRADE and len(red_flags) == 0

    return {
        "score": total,
        "tier": tier,
        "tradeable": tradeable,
        "components": {k: round(v, 1) for k, v in components.items()},
        "weights": SCORE_WEIGHTS,
        "red_flags": red_flags,
        "verdict": (
            f"TRADE ({tier} confidence)" if tradeable
            else f"NO TRADE — score {total}, flags: {red_flags}"
        ),
    }


if __name__ == "__main__":
    # Example: strong bullish setup
    signals = {
        "trade_direction": "long",
        "market_bias": "bullish",
        "bos": "bullish",
        "liquidity_sweep": "bullish_sweep",
        "structure_label": "HH",
        "strategy_type": "momentum",
        "regime_fit": "momentum",
        "regime_stability": "stable",
        "trend_regime": "trending_up",
        "session": "london",
        "session_overlap": "london_ny",
        "is_session_transition": False,
        "volume_ratio": 1.8,
        "volume_trend": "increasing",
        "rsi": 45,
        "macd_signal": "bullish",
        "risk_reward_ratio": 3.0,
    }
    result = compute_trade_score(signals)
    print(f"\nTrade Score: {result['score']}/100 ({result['tier']})")
    print(f"Tradeable: {result['tradeable']}")
    print(f"Verdict: {result['verdict']}")
    print("\nComponent Breakdown:")
    for comp, score in result["components"].items():
        print(f"  {comp}: {score}/100 (weight: {SCORE_WEIGHTS[comp]}%)")
    if result["red_flags"]:
        print(f"\nRED FLAGS: {result['red_flags']}")
