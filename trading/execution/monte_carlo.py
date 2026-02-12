"""
Monte Carlo Risk Stress Testing
--------------------------------
Simulates thousands of possible equity curves from historical trade data.
Answers: "What's the REALISTIC range of outcomes?"

Prevents overconfidence from a single backtest equity curve.
A backtest is ONE path. Monte Carlo shows the DISTRIBUTION of paths.

Inputs:  Historical R-multiples or trade returns
Outputs: Percentile equity curves, risk metrics, ruin probability
"""

import numpy as np
from typing import Optional
from config import MC_SIMULATIONS, MC_TRADE_COUNT, MC_CONFIDENCE_LEVELS


def run_monte_carlo(
    trade_returns: list[float],
    initial_capital: float = 10000.0,
    n_simulations: int = MC_SIMULATIONS,
    n_trades: int = MC_TRADE_COUNT,
    risk_per_trade: float = 100.0,
) -> dict:
    """
    Run Monte Carlo simulation by resampling historical trade returns.

    Args:
        trade_returns: List of historical P&L per trade (or R-multiples * risk)
        initial_capital: Starting capital
        n_simulations: Number of simulation paths
        n_trades: Trades per simulation path
        risk_per_trade: Dollar risk per trade (for R-multiple conversion)

    Returns:
        Simulation results with percentile curves and risk metrics
    """
    if not trade_returns or len(trade_returns) < 5:
        return {"error": "Insufficient trade data (need at least 5 trades)"}

    returns = np.array(trade_returns, dtype=float)

    # Resample trades randomly for each simulation
    rng = np.random.default_rng(42)
    sampled_indices = rng.choice(len(returns), size=(n_simulations, n_trades), replace=True)
    sampled_returns = returns[sampled_indices]

    # Build equity curves
    equity_curves = np.zeros((n_simulations, n_trades + 1))
    equity_curves[:, 0] = initial_capital

    for t in range(n_trades):
        equity_curves[:, t + 1] = equity_curves[:, t] + sampled_returns[:, t]

    # Final equity values
    final_equities = equity_curves[:, -1]

    # Drawdown calculation per simulation
    max_drawdowns = np.zeros(n_simulations)
    for i in range(n_simulations):
        curve = equity_curves[i]
        peak = np.maximum.accumulate(curve)
        drawdown = (peak - curve) / np.where(peak > 0, peak, 1) * 100
        max_drawdowns[i] = drawdown.max()

    # Percentile curves
    percentile_curves = {}
    for level in MC_CONFIDENCE_LEVELS:
        pct_label = f"p{int(level * 100)}"
        percentile_curves[pct_label] = np.percentile(equity_curves, level * 100, axis=0).tolist()

    # Risk metrics
    ruin_threshold = initial_capital * 0.5  # 50% loss = ruin
    ruin_count = np.sum(np.any(equity_curves <= ruin_threshold, axis=1))
    ruin_probability = ruin_count / n_simulations

    profitable_count = np.sum(final_equities > initial_capital)
    profit_probability = profitable_count / n_simulations

    return {
        "simulations": n_simulations,
        "trades_per_sim": n_trades,
        "initial_capital": initial_capital,
        "input_trades": len(trade_returns),
        "final_equity": {
            "mean": round(float(np.mean(final_equities)), 2),
            "median": round(float(np.median(final_equities)), 2),
            "std": round(float(np.std(final_equities)), 2),
            "min": round(float(np.min(final_equities)), 2),
            "max": round(float(np.max(final_equities)), 2),
            "p5": round(float(np.percentile(final_equities, 5)), 2),
            "p25": round(float(np.percentile(final_equities, 25)), 2),
            "p75": round(float(np.percentile(final_equities, 75)), 2),
            "p95": round(float(np.percentile(final_equities, 95)), 2),
        },
        "drawdown": {
            "mean_max_dd_pct": round(float(np.mean(max_drawdowns)), 2),
            "median_max_dd_pct": round(float(np.median(max_drawdowns)), 2),
            "worst_max_dd_pct": round(float(np.max(max_drawdowns)), 2),
            "p95_max_dd_pct": round(float(np.percentile(max_drawdowns, 95)), 2),
        },
        "risk": {
            "ruin_probability": round(float(ruin_probability), 4),
            "profit_probability": round(float(profit_probability), 4),
            "expected_return_pct": round(float((np.mean(final_equities) - initial_capital) / initial_capital * 100), 2),
        },
        "percentile_curves": {
            k: [round(v, 2) for v in vals[::max(1, len(vals) // 50)]]  # downsample for display
            for k, vals in percentile_curves.items()
        },
    }


def stress_test_scenarios(
    trade_returns: list[float],
    initial_capital: float = 10000.0,
) -> dict:
    """
    Run Monte Carlo under different stress scenarios:
    1. Normal (as-is)
    2. Reduced win rate (remove 20% of winners)
    3. Increased losses (amplify losses by 50%)
    4. Clustered losses (group losing trades together)
    5. Black swan (inject 5% of trades as -5R losses)
    """
    if not trade_returns or len(trade_returns) < 5:
        return {"error": "Insufficient data"}

    returns = np.array(trade_returns, dtype=float)
    results = {}

    # 1. Normal
    results["normal"] = run_monte_carlo(trade_returns, initial_capital, n_simulations=2000)

    # 2. Reduced win rate
    winners = returns[returns > 0]
    losers = returns[returns <= 0]
    n_remove = max(1, int(len(winners) * 0.2))
    degraded = np.concatenate([winners[n_remove:], losers]).tolist()
    results["reduced_win_rate"] = run_monte_carlo(degraded, initial_capital, n_simulations=2000)

    # 3. Amplified losses
    amplified = returns.copy()
    amplified[amplified < 0] *= 1.5
    results["amplified_losses"] = run_monte_carlo(amplified.tolist(), initial_capital, n_simulations=2000)

    # 4. Black swan injection
    rng = np.random.default_rng(99)
    avg_loss = np.mean(np.abs(returns[returns < 0])) if np.any(returns < 0) else 100
    black_swans = np.full(max(1, int(len(returns) * 0.05)), -5 * avg_loss)
    with_swans = np.concatenate([returns, black_swans]).tolist()
    results["black_swan"] = run_monte_carlo(with_swans, initial_capital, n_simulations=2000)

    # Summary comparison
    results["comparison"] = {
        scenario: {
            "final_median": results[scenario]["final_equity"]["median"],
            "ruin_prob": results[scenario]["risk"]["ruin_probability"],
            "p95_drawdown": results[scenario]["drawdown"]["p95_max_dd_pct"],
        }
        for scenario in ["normal", "reduced_win_rate", "amplified_losses", "black_swan"]
    }

    return results


if __name__ == "__main__":
    import json

    # Simulate a strategy with 55% win rate, 2:1 RR
    rng = np.random.default_rng(42)
    n_trades = 100
    wins = rng.choice([True, False], size=n_trades, p=[0.55, 0.45])
    trade_pnl = [200 if w else -100 for w in wins]

    result = run_monte_carlo(trade_pnl, initial_capital=10000, n_simulations=5000, n_trades=252)
    print("=== Monte Carlo Results ===")
    print(f"Final Equity (median): ${result['final_equity']['median']}")
    print(f"Final Equity (5th percentile): ${result['final_equity']['p5']}")
    print(f"Ruin Probability: {result['risk']['ruin_probability'] * 100:.1f}%")
    print(f"Expected Return: {result['risk']['expected_return_pct']:.1f}%")
    print(f"P95 Max Drawdown: {result['drawdown']['p95_max_dd_pct']:.1f}%")

    print("\n=== Stress Tests ===")
    stress = stress_test_scenarios(trade_pnl)
    print(json.dumps(stress["comparison"], indent=2))
