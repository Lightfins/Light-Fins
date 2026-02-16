# Directive: Create a New Trading Strategy

## Goal
Turn a natural language trading idea into a tested, validated strategy with Pine Script output.

## Inputs
- User's trading idea (e.g., "4h BTC RSI + EMA strategy")
- Timeframe (1m, 5m, 15m, 1h, 4h, 1d)
- Assets to test on (default: BTC, ETH, SOL)
- Number of variants to generate (default: 8)

## Steps

### 1. Parse the Request
Extract from the user's message:
- Which indicators to use
- What timeframe
- Long only, short only, or both
- Any specific parameter preferences

### 2. Create Base Strategy
Use `trading/strategies/builder.py`:
- Pick the closest template (rsi_ema, macd_bb, supertrend_adx) or build custom
- Set reasonable default parameters

### 3. Generate Variants
Use `builder.generate_variants()` with a parameter grid:
- For RSI: length [10, 14, 21], overbought [70, 75, 80], oversold [20, 25, 30]
- For EMA: fast [9, 12, 20], slow [21, 26, 50]
- For MACD: fast [8, 12], slow [21, 26], signal [7, 9]
- Cap at max_variants=20

### 4. Ensure Data Exists
Check `trading/data/` for CSV files matching the requested assets.
If missing, use `trading/engine/data_fetcher.py` to fetch from Binance (free, no API key).

### 5. Run Multi-Asset Backtest
Use `trading/engine/backtest.py`:
```python
from trading.engine.backtest import compare_variants
results = compare_variants(variants, data_files)
```

### 6. Present Results
Show a table with columns:
| Variant | Net Profit % | Max DD % | Win Rate | Sharpe | Sortino | Trades | Score |

Highlight the best performer.

### 7. Generate Pine Script
For the best variant:
```python
from trading.pinescript.generator import save_pine_script
filepath = save_pine_script(best_strategy)
```

### 8. Save Everything
- Strategy config → `trading/workspace/strategies/`
- Backtest results → `trading/workspace/`
- Pine Script → `trading/workspace/pinescript/`

## Output
- Strategy JSON config
- Backtest results table (all variants, all assets)
- Pine Script v5 code
- Recommendation with reasoning

## Edge Cases
- If no data files exist, fetch them first (free via ccxt)
- If all variants are unprofitable, say so honestly and suggest alternative indicators
- If too few trades (<20), the results are unreliable — note this
- If the timeframe doesn't match the data granularity, warn the user

## Learnings
- (Add learnings as they come in — API limits, common errors, etc.)
