# Directive: Deploy a Strategy Live

## Goal
Take a backtested strategy and deploy it to execute trades automatically on a schedule.

## Inputs
- Strategy name or file path
- Exchange (default: Hyperliquid testnet)
- Symbol (e.g., BTC/USDT)
- Trade amount
- Interval (e.g., every 4 hours)
- Testnet vs mainnet

## Safety Checklist (MANDATORY before any deployment)
1. Strategy has been backtested on 3+ assets
2. Max drawdown < 25%
3. Sharpe ratio > 0.5
4. At least 30 trades in backtest
5. User has explicitly confirmed they want to deploy
6. Read-only mode test completed first

## Steps

### 1. Validate Strategy
Load the strategy from `trading/workspace/strategies/`.
Check it meets the safety checklist above.

### 2. Start in Read-Only Mode
```python
from trading.live.executor import ReadOnlyMode
ReadOnlyMode.activate()
```
Run one cycle to verify signals are generated correctly without executing.

### 3. Set Up Exchange Connection
Ensure the correct API keys are in `trading/.env`:
- Hyperliquid: `HYPERLIQUID_SECRET_KEY`
- CCXT exchanges: `{EXCHANGE}_API_KEY` and `{EXCHANGE}_SECRET`

### 4. Create Schedule
```python
from trading.live.scheduler import create_cron_entry
schedule = create_cron_entry(
    strategy_name="my_strategy",
    strategy_file="trading/workspace/strategies/my_strategy.json",
    symbol="BTC/USDT",
    exchange="hyperliquid",
    interval_hours=4,
    amount=0.01,
    testnet=True,
)
```

### 5. Install Cron Job
Generate the crontab line:
```python
from trading.live.scheduler import generate_crontab_line
cron_line = generate_crontab_line(schedule)
# User manually adds this to crontab -e
```

### 6. Monitor
- Check `trading/logs/live_trades.log` for execution logs
- Check `trading/logs/trade_history.jsonl` for trade records
- Dashboard shows live P&L at http://localhost:8501

## Kill Switch
If anything goes wrong:
```python
from trading.live.executor import KillSwitch
KillSwitch.activate()
```
Or create the file manually: `touch trading/workspace/.kill_switch`

## Output
- Crontab entry or systemd timer config
- Confirmation of read-only test results
- Link to monitoring dashboard

## Edge Cases
- If exchange connection fails, do not retry indefinitely — log and alert
- If API key is missing, activate read-only mode automatically
- Always use testnet first — never go mainnet without explicit user confirmation
- If kill switch file exists, refuse to execute any trades

## Learnings
- Always start on testnet. Always.
- Hyperliquid testnet has different rate limits than mainnet
