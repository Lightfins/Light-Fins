# Directive: Monitor Strategy Performance

## Goal
Track live and backtest performance, detect degradation, suggest improvements.

## When to Use
- After deploying a strategy live
- When user asks "how is my strategy doing?"
- Periodically (daily) to check all active strategies

## Steps

### 1. Check Active Schedules
Load `trading/workspace/schedules.json` to see what's running.

### 2. Review Trade Logs
Parse `trading/logs/trade_history.jsonl`:
- Count trades in last 24h, 7d, 30d
- Calculate P&L from filled orders
- Check for failed orders

### 3. Compare to Backtest
Load the original backtest results from `trading/workspace/backtest_*.json`.
Compare live performance to backtest expectations:
- Is live win rate within 10% of backtest?
- Is live drawdown within 1.5x of backtest max DD?
- Are trade frequencies similar?

### 4. Detect Problems
Flag these issues:
- Live performance 30%+ worse than backtest → possible overfitting
- No trades in expected window → signal generation issue
- All recent trades are losses → market regime change
- Max drawdown exceeded → consider pausing

### 5. Suggest Improvements
Based on analysis:
- If drawdown too high → suggest tighter stops or smaller position size
- If win rate dropped → re-optimize with recent data
- If too few trades → loosen entry conditions
- If regime changed → suggest different indicator set

## Output
- Performance summary (table format)
- Comparison: backtest vs live
- Red flags (if any)
- Suggested actions

## Tools
- `trading/engine/backtest.py` — for re-running backtests with updated data
- `trading/prompts/claude_integration.py:analyze_backtest_results()` — for AI analysis
- Streamlit dashboard — for visual monitoring
