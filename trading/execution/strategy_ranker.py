"""
Strategy Ranking & Auto-Disable System
---------------------------------------
Tracks performance of each strategy, ranks by expectancy,
and auto-disables strategies that fall below threshold.

This is the IMMUNE SYSTEM. Bad strategies get quarantined.

Inputs:  Journal data
Outputs: Strategy rankings, enable/disable decisions
"""

import json
from datetime import datetime
from config import (
    STRATEGY_DISABLE_THRESHOLD, STRATEGY_EVAL_MIN_TRADES,
    STRATEGY_LOOKBACK_TRADES
)
from journal_engine import get_connection, update_strategy_scores


STRATEGY_REGISTRY = {
    "momentum_bos": {
        "description": "Momentum entry on Break of Structure",
        "regime_fit": "momentum",
        "min_confidence": 60,
    },
    "liquidity_sweep_reversal": {
        "description": "Reversal after liquidity sweep",
        "regime_fit": "mean_reversion",
        "min_confidence": 65,
    },
    "session_open_breakout": {
        "description": "Breakout on London/NY session open",
        "regime_fit": "momentum",
        "min_confidence": 55,
    },
    "range_mean_reversion": {
        "description": "Mean reversion at range boundaries",
        "regime_fit": "mean_reversion",
        "min_confidence": 60,
    },
    "trend_pullback": {
        "description": "Entry on pullback in established trend",
        "regime_fit": "momentum",
        "min_confidence": 55,
    },
}


def evaluate_strategies() -> list[dict]:
    """
    Evaluate all strategies, rank by expectancy, flag underperformers.
    Returns sorted list of strategy evaluations.
    """
    update_strategy_scores()

    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM strategy_scores ORDER BY expectancy DESC
    """).fetchall()
    conn.close()

    evaluations = []
    for row in rows:
        strat = dict(row)
        total = strat["total_trades"]

        # Determine status
        if total < STRATEGY_EVAL_MIN_TRADES:
            strat["eval_status"] = "insufficient_data"
            strat["action"] = "monitor"
        elif strat["expectancy"] < STRATEGY_DISABLE_THRESHOLD:
            strat["eval_status"] = "failing"
            strat["action"] = "disable"
        elif strat["expectancy"] < 0:
            strat["eval_status"] = "underperforming"
            strat["action"] = "reduce_size"
        elif strat["win_rate"] < 0.35:
            strat["eval_status"] = "low_win_rate"
            strat["action"] = "review"
        else:
            strat["eval_status"] = "healthy"
            strat["action"] = "continue"

        # Confidence adjustment suggestion
        if strat["expectancy"] > 0.5:
            strat["size_modifier"] = 1.2  # scale up
        elif strat["expectancy"] > 0:
            strat["size_modifier"] = 1.0
        elif strat["expectancy"] > STRATEGY_DISABLE_THRESHOLD:
            strat["size_modifier"] = 0.5  # scale down
        else:
            strat["size_modifier"] = 0.0  # disabled

        # Add registry info
        reg = STRATEGY_REGISTRY.get(strat["strategy"], {})
        strat["description"] = reg.get("description", "Unknown strategy")
        strat["regime_fit"] = reg.get("regime_fit", "unknown")

        evaluations.append(strat)

    return evaluations


def auto_disable_strategies() -> list[dict]:
    """
    Disable strategies that have fallen below threshold.
    Returns list of actions taken.
    """
    evaluations = evaluate_strategies()
    actions = []

    conn = get_connection()
    for strat in evaluations:
        if strat["action"] == "disable" and strat.get("enabled", 1) == 1:
            conn.execute("""
                UPDATE strategy_scores SET enabled = 0 WHERE strategy = ?
            """, (strat["strategy"],))
            actions.append({
                "strategy": strat["strategy"],
                "action": "DISABLED",
                "reason": f"Expectancy {strat['expectancy']} below threshold {STRATEGY_DISABLE_THRESHOLD}",
                "trades": strat["total_trades"],
                "timestamp": datetime.utcnow().isoformat(),
            })

    conn.commit()
    conn.close()
    return actions


def get_strategy_recommendation(regime: str, session: str) -> list[dict]:
    """
    Recommend which strategies to use based on current regime and session.
    Returns ranked list of suitable strategies.
    """
    evaluations = evaluate_strategies()
    suitable = []

    for strat in evaluations:
        if not strat.get("enabled", 1):
            continue
        if strat["action"] == "disable":
            continue

        # Regime fit
        if strat["regime_fit"] == regime or strat["regime_fit"] == "unknown":
            score = strat["expectancy"] * 100 + strat["win_rate"] * 50
            suitable.append({
                "strategy": strat["strategy"],
                "description": strat["description"],
                "score": round(score, 2),
                "win_rate": strat["win_rate"],
                "expectancy": strat["expectancy"],
                "size_modifier": strat["size_modifier"],
                "total_trades": strat["total_trades"],
            })

    suitable.sort(key=lambda x: x["score"], reverse=True)
    return suitable


def detect_error_clusters() -> list[dict]:
    """
    Detect repeated failure patterns that suggest rule modifications.
    Looks for: same mistake type > 3 times in last 20 trades per strategy.
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT strategy, mistake_class, COUNT(*) as count
        FROM trades
        WHERE status = 'closed'
            AND mistake_class IS NOT NULL
            AND mistake_class != 'none'
            AND timestamp_close >= datetime('now', '-30 days')
        GROUP BY strategy, mistake_class
        HAVING count >= 3
        ORDER BY count DESC
    """).fetchall()
    conn.close()

    clusters = []
    for row in rows:
        suggestion = _suggest_fix(row["strategy"], row["mistake_class"], row["count"])
        clusters.append({
            "strategy": row["strategy"],
            "mistake": row["mistake_class"],
            "occurrences": row["count"],
            "suggestion": suggestion,
        })

    return clusters


def _suggest_fix(strategy: str, mistake: str, count: int) -> str:
    """Generate rule modification suggestion based on error pattern."""
    fixes = {
        "early_exit": "Widen take-profit or use trailing stop instead of fixed TP",
        "late_entry": "Add limit order at pullback level instead of market entry",
        "wrong_direction": "Increase minimum confidence threshold for this strategy",
        "oversize": "Reduce position size modifier; enforce Kelly fraction cap",
        "fomo": "Add cooldown timer between trades; require minimum setup time",
        "revenge": "Implement mandatory pause after 2 consecutive losses",
    }
    base = fixes.get(mistake, f"Review and address recurring '{mistake}' pattern")
    return f"{base} ({count} occurrences in 30 days)"


if __name__ == "__main__":
    print("Strategy Registry:")
    for name, info in STRATEGY_REGISTRY.items():
        print(f"  {name}: {info['description']} (fits: {info['regime_fit']})")

    evals = evaluate_strategies()
    print(f"\nEvaluations: {len(evals)} strategies")
    for e in evals:
        print(f"  {e['strategy']}: {e['eval_status']} -> {e['action']}")
