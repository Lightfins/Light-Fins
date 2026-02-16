"""
Entry point for cron/systemd scheduled strategy execution.
Usage: python -m trading.live.run_scheduled --strategy path.json --symbol BTC/USDT --exchange hyperliquid --amount 0.01 [--testnet]
"""

import argparse
import json
import logging
from trading.engine.backtest import load_tradingview_csv, apply_indicators, generate_signals
from trading.engine.data_fetcher import fetch_ohlcv
from trading.live.executor import LiveExecutor, KillSwitch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("run_scheduled")


def main():
    parser = argparse.ArgumentParser(description="Run a scheduled trading strategy")
    parser.add_argument("--strategy", required=True, help="Path to strategy JSON file")
    parser.add_argument("--symbol", required=True, help="Trading symbol e.g. BTC/USDT")
    parser.add_argument("--exchange", default="hyperliquid", help="Exchange ID")
    parser.add_argument("--amount", type=float, default=0.01, help="Trade amount")
    parser.add_argument("--testnet", action="store_true", help="Use testnet")
    args = parser.parse_args()

    if KillSwitch.is_active():
        logger.warning("Kill switch active. Exiting.")
        return

    # Load strategy
    with open(args.strategy) as f:
        strategy = json.load(f)

    # Fetch latest data
    timeframe = strategy.get("timeframe", "4h")
    logger.info(f"Fetching {args.symbol} {timeframe} data...")
    df = fetch_ohlcv(args.symbol, timeframe, limit=200)

    # Apply indicators and generate signals
    df = apply_indicators(df, strategy)
    entries, exits = generate_signals(df, strategy)

    last_entry = bool(entries.iloc[-1]) if len(entries) > 0 else False
    last_exit = bool(exits.iloc[-1]) if len(exits) > 0 else False

    logger.info(f"Signal check: entry={last_entry}, exit={last_exit}")

    if not last_entry and not last_exit:
        logger.info("No signal. Done.")
        return

    # Execute
    executor = LiveExecutor(args.exchange, testnet=args.testnet)

    if last_entry:
        result = executor.place_order(args.symbol, "buy", args.amount)
        logger.info(f"BUY result: {result}")
    elif last_exit:
        result = executor.place_order(args.symbol, "sell", args.amount)
        logger.info(f"SELL result: {result}")


if __name__ == "__main__":
    main()
