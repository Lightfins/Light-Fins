"""
Free data fetcher for crypto OHLCV data using ccxt.
No paid APIs — uses public exchange endpoints.
"""

import os
import time
import pandas as pd
from pathlib import Path
from typing import Optional

DATA_DIR = Path(os.getenv("TRADING_DATA_DIR", "trading/data"))


def fetch_ohlcv(
    symbol: str = "BTC/USDT",
    timeframe: str = "4h",
    exchange_id: str = "binance",
    limit: int = 1000,
    since: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetch OHLCV data from a public exchange via ccxt.
    No API key needed for public market data.
    """
    import ccxt

    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class({"enableRateLimit": True})

    since_ts = None
    if since:
        since_ts = exchange.parse8601(since + "T00:00:00Z")

    all_ohlcv = []
    fetched = 0
    current_since = since_ts

    while fetched < limit:
        batch_limit = min(1000, limit - fetched)
        ohlcv = exchange.fetch_ohlcv(
            symbol, timeframe, since=current_since, limit=batch_limit
        )
        if not ohlcv:
            break

        all_ohlcv.extend(ohlcv)
        fetched += len(ohlcv)
        current_since = ohlcv[-1][0] + 1  # next millisecond after last candle
        time.sleep(exchange.rateLimit / 1000)

        if len(ohlcv) < batch_limit:
            break

    df = pd.DataFrame(all_ohlcv, columns=["datetime", "open", "high", "low", "close", "volume"])
    df["datetime"] = pd.to_datetime(df["datetime"], unit="ms")
    df = df.set_index("datetime").sort_index()
    df = df[~df.index.duplicated(keep="first")]

    return df


def fetch_and_save(
    symbol: str = "BTC/USDT",
    timeframe: str = "4h",
    exchange_id: str = "binance",
    limit: int = 1000,
    since: Optional[str] = None,
) -> str:
    """Fetch OHLCV and save to CSV in data directory."""
    df = fetch_ohlcv(symbol, timeframe, exchange_id, limit, since)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    clean_symbol = symbol.replace("/", "").upper()
    filename = f"{clean_symbol}_{timeframe}_{exchange_id}.csv"
    filepath = DATA_DIR / filename
    df.to_csv(filepath)

    return str(filepath)


def fetch_multi_asset(
    symbols: list = None,
    timeframe: str = "4h",
    exchange_id: str = "binance",
    limit: int = 1000,
) -> dict:
    """Fetch data for multiple symbols. Returns dict of {symbol: filepath}."""
    if symbols is None:
        symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

    results = {}
    for symbol in symbols:
        filepath = fetch_and_save(symbol, timeframe, exchange_id, limit)
        results[symbol] = filepath

    return results
