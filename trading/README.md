# TradingClaw — Local AI Trading Agent

Autonomous crypto trading agent powered by Claude, running 100% locally.

## Quick Start

```bash
# 1. Configure your API key
cp trading/.env.example trading/.env
# Edit trading/.env → add your ANTHROPIC_API_KEY

# 2. Start (pick one)
./trading/start.sh local    # Run directly
./trading/start.sh docker   # Run in Docker (recommended)

# 3. Open dashboard
# http://localhost:8501
```

## Architecture

```
trading/
├── engine/           # Backtesting (vectorbt + pandas_ta)
│   ├── backtest.py   # Core backtester — signals, stats, multi-asset
│   └── data_fetcher.py # Free OHLCV data via ccxt
├── strategies/       # Strategy builder + templates
│   └── builder.py    # Create, edit, variant generation
├── pinescript/       # Pine Script v5 generator
│   └── generator.py  # Strategy config → TradingView code
├── live/             # Live trading execution
│   ├── executor.py   # Hyperliquid + CCXT, kill switch, safety
│   ├── scheduler.py  # Cron/systemd scheduling
│   └── run_scheduled.py # Cron entry point
├── dashboard/        # Streamlit web UI
│   └── app.py        # Chat, strategies, backtests, logs
├── prompts/          # Claude integration
│   ├── system_prompt.py    # Agent system prompts
│   └── claude_integration.py # API calls, model routing
├── data/             # OHLCV CSV files (TradingView format)
├── workspace/        # Results, saved strategies, Pine Scripts
├── logs/             # Trade logs, system logs
├── .env.example      # Environment template
├── requirements.txt  # Python dependencies
├── Dockerfile        # Docker image
├── docker-compose.yml
└── start.sh          # One-click launcher
```

## How to Create a New Strategy

### Option 1: Chat (recommended)
Open the dashboard and type:
> "Create a 4h BTC strategy with RSI + EMA, test 8 variants, backtest on BTC+ETH+SOL, give me the best one + Pine Script"

### Option 2: Python
```python
from trading.strategies.builder import template_rsi_ema, generate_variants
from trading.engine.backtest import compare_variants
from trading.pinescript.generator import save_pine_script

# Create base strategy
base = template_rsi_ema(timeframe="4h")

# Generate 8 variants
variants = generate_variants(base, {
    "rsi_length": [10, 14, 21],
    "ema_length": [9, 20, 50],
}, max_variants=8)

# Backtest across 3 assets
data_files = ["trading/data/BTCUSDT_4h.csv", "trading/data/ETHUSDT_4h.csv", "trading/data/SOLUSDT_4h.csv"]
results = compare_variants(variants, data_files)

# Generate Pine Script for the winner
best = results[0]  # sorted by composite score
save_pine_script(best)
```

### Option 3: From TradingView data
1. Export CSV from TradingView (time, open, high, low, close, volume)
2. Put it in `trading/data/`
3. Run backtest via dashboard or Python

## How to Deploy Live

### Phase 1: Testnet (safe)
```python
from trading.live.executor import LiveExecutor, ReadOnlyMode

# Start in read-only to verify
ReadOnlyMode.activate()
executor = LiveExecutor("hyperliquid", testnet=True)
executor.place_order("BTC/USDT", "buy", 0.001)
# → Will simulate, not execute

# When ready for testnet
ReadOnlyMode.deactivate()
executor.place_order("BTC/USDT", "buy", 0.001)
# → Executes on Hyperliquid testnet
```

### Phase 2: Schedule it
```python
from trading.live.scheduler import create_cron_entry, generate_crontab_line

schedule = create_cron_entry(
    strategy_name="rsi_ema_4h",
    strategy_file="trading/workspace/strategies/rsi_ema_4h.json",
    symbol="BTC/USDT",
    exchange="hyperliquid",
    interval_hours=4,
    amount=0.01,
    testnet=True,
)

# Add to crontab
print(generate_crontab_line(schedule))
# Copy output into: crontab -e
```

### Emergency: Kill Switch
```bash
# Instant halt — all trades blocked
touch trading/workspace/.kill_switch

# Or via Python
from trading.live.executor import KillSwitch
KillSwitch.activate()
```

## How to Monitor

### Dashboard
http://localhost:8501 → Live Trading tab shows:
- Kill switch / read-only status
- Active schedules
- Trade history
- P&L

### Logs
```bash
# Live trade log
tail -f trading/logs/live_trades.log

# Trade history (JSON lines)
cat trading/logs/trade_history.jsonl

# Cron execution log
tail -f trading/logs/cron.log
```

## Model Cost Management

TradingClaw routes tasks to the cheapest adequate Claude model:

| Task | Model | ~Cost |
|------|-------|-------|
| Strategy design | Opus 4 | Higher — used rarely |
| Analysis & chat | Sonnet 4.5 | Medium — default for most tasks |
| Validation | Haiku 4.5 | Lowest — quick checks |

With Claude Pro, you get included API usage. The agent minimizes calls:
- Backtesting is 100% local (no API calls)
- Pine Script generation is 100% local
- Data fetching is free (public exchange APIs)
- Only chat/analysis uses Claude API

## Data Sources (all free)
- **ccxt**: Public OHLCV from Binance, Bybit, OKX, etc. No API key needed.
- **TradingView CSV**: Export and drop into `trading/data/`

## Safety Features
- Kill switch (instant trade halt)
- Read-only mode (simulate without executing)
- Testnet first (never mainnet without explicit confirmation)
- Full logging of every action
- Docker isolation (recommended)
- API keys in .env only (never hardcoded)
- Confirmation required before any live trade
