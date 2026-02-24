"""
TradingClaw CLI — quick commands without the dashboard.
Usage:
    python -m trading.cli fetch BTC/USDT 4h
    python -m trading.cli backtest trading/strategies/templates/rsi_ema_4h.json
    python -m trading.cli variants trading/strategies/templates/rsi_ema_4h.json
    python -m trading.cli pine trading/strategies/templates/rsi_ema_4h.json
    python -m trading.cli chat "Create a MACD strategy for ETH on 1h"
"""

import sys
import json
import glob
from pathlib import Path


def cmd_fetch(args):
    """Fetch OHLCV data."""
    from trading.engine.data_fetcher import fetch_and_save

    symbol = args[0] if args else "BTC/USDT"
    timeframe = args[1] if len(args) > 1 else "4h"
    limit = int(args[2]) if len(args) > 2 else 1000

    print(f"Fetching {symbol} {timeframe} ({limit} candles)...")
    filepath = fetch_and_save(symbol, timeframe, limit=limit)
    print(f"Saved to {filepath}")


def cmd_backtest(args):
    """Run a backtest."""
    from trading.engine.backtest import run_strategy, save_results

    if not args:
        print("Usage: python -m trading.cli backtest <strategy.json> [data_dir]")
        return

    with open(args[0]) as f:
        strategy = json.load(f)

    data_dir = args[1] if len(args) > 1 else "trading/data"
    data_files = sorted(glob.glob(f"{data_dir}/*.csv"))

    if not data_files:
        print(f"No CSV files in {data_dir}. Run: python -m trading.cli fetch BTC/USDT 4h")
        return

    print(f"Running {strategy['name']} on {len(data_files)} assets...")
    results = run_strategy(strategy, data_files)
    filepath = save_results(results)

    print(f"\n{'='*60}")
    print(f"Strategy: {results['strategy_name']}")
    print(f"Assets tested: {results['assets_tested']}")
    print(f"Avg Net Profit: {results['avg_net_profit_pct']:.2f}%")
    print(f"Avg Max DD: {results['avg_max_drawdown_pct']:.2f}%")
    print(f"Avg Sharpe: {results['avg_sharpe_ratio']:.3f}")
    print(f"Avg Win Rate: {results['avg_win_rate_pct']:.1f}%")
    print(f"{'='*60}")

    for r in results["per_asset_results"]:
        print(f"  {r['asset']:12s} | Ret: {r['net_profit_pct']:7.2f}% | DD: {r['max_drawdown_pct']:6.2f}% | "
              f"Sharpe: {r['sharpe_ratio']:6.3f} | WR: {r['win_rate_pct']:5.1f}% | Trades: {r['total_trades']}")

    print(f"\nResults saved to {filepath}")


def cmd_variants(args):
    """Generate and test variants."""
    from trading.engine.backtest import compare_variants, save_results
    from trading.strategies.builder import generate_variants

    if not args:
        print("Usage: python -m trading.cli variants <strategy.json> [data_dir]")
        return

    with open(args[0]) as f:
        base = json.load(f)

    data_dir = args[1] if len(args) > 1 else "trading/data"
    data_files = sorted(glob.glob(f"{data_dir}/*.csv"))

    if not data_files:
        print(f"No CSV files in {data_dir}.")
        return

    # Auto-generate param grid from indicators
    param_grid = _auto_param_grid(base)
    if not param_grid:
        print("Could not auto-generate parameter grid. Define manually.")
        return

    variants = generate_variants(base, param_grid, max_variants=8)
    print(f"Testing {len(variants)} variants on {len(data_files)} assets...\n")

    results = compare_variants(variants, data_files)

    print(f"{'Rank':<5} {'Name':<25} {'Return%':>8} {'MaxDD%':>8} {'Sharpe':>8} {'WinRate':>8} {'Score':>8}")
    print("-" * 75)
    for i, r in enumerate(results):
        print(f"{i+1:<5} {r['strategy_name']:<25} {r['avg_net_profit_pct']:>7.2f}% "
              f"{r['avg_max_drawdown_pct']:>7.2f}% {r['avg_sharpe_ratio']:>8.3f} "
              f"{r['avg_win_rate_pct']:>7.1f}% {r['composite_score']:>8.3f}")

    if results:
        best = results[0]
        filepath = save_results(best, name=best["strategy_name"])
        print(f"\nBest variant: {best['strategy_name']} (score: {best['composite_score']:.3f})")
        print(f"Saved to {filepath}")


def cmd_pine(args):
    """Generate Pine Script."""
    from trading.pinescript.generator import generate_pine_script, save_pine_script

    if not args:
        print("Usage: python -m trading.cli pine <strategy.json>")
        return

    with open(args[0]) as f:
        strategy = json.load(f)

    script = generate_pine_script(strategy)
    filepath = save_pine_script(strategy)

    print(script)
    print(f"\nSaved to {filepath}")


def cmd_chat(args):
    """Chat with Claude trading agent."""
    from trading.prompts.claude_integration import chat

    if not args:
        print("Usage: python -m trading.cli chat \"your message here\"")
        return

    message = " ".join(args)
    print(f"You: {message}\n")
    response, _ = chat(message)
    print(f"TradingClaw:\n{response}")


def _auto_param_grid(strategy):
    """Auto-generate a parameter grid from strategy indicators."""
    grid = {}
    for ind in strategy.get("indicators", []):
        name = ind["name"].lower()
        params = ind.get("params", {})
        if name == "rsi":
            base = params.get("length", 14)
            grid["rsi_length"] = [max(5, base - 4), base, base + 7]
        elif name == "ema":
            base = params.get("length", 20)
            grid[f"ema_length"] = [max(3, base - 3), base, base + 10]
        elif name == "sma":
            base = params.get("length", 20)
            grid[f"sma_length"] = [max(5, base - 5), base, base + 10]
        elif name == "macd":
            grid["macd_fast"] = [8, 12]
            grid["macd_slow"] = [21, 26]
    return grid


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "fetch": cmd_fetch,
        "backtest": cmd_backtest,
        "variants": cmd_variants,
        "pine": cmd_pine,
        "chat": cmd_chat,
    }

    if command in commands:
        commands[command](args)
    else:
        print(f"Unknown command: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()
