# Directive: Adaptive Learning System

## Goal
Build a self-improving feedback loop. The system logs every trade, detects failure patterns, adjusts strategy weights, and auto-disables broken strategies.

## Execution Scripts

| Script | Purpose |
|--------|---------|
| `execution/journal_engine.py` | SQLite trade journal, analytics, export |
| `execution/strategy_ranker.py` | Strategy evaluation, auto-disable, error clusters |
| `execution/monte_carlo.py` | Forward-looking risk simulation |

## Trade Logging (Every Trade, No Exceptions)

### Required Fields
- Timestamp (open and close)
- Pair, direction, strategy name
- Setup type (breakout, pullback, sweep reversal, etc.)
- Market regime at entry
- Session at entry
- Entry/exit prices, SL, TP
- Position size, risk amount
- Gross P&L, net P&L, R-multiple
- Confidence score and tier
- Entry reason (text)
- Exit reason (stop_loss, take_profit, strategy_exit, end_of_data)
- Mistake classification

### Mistake Classification Options
- `none` — trade executed correctly
- `early_exit` — exited before TP was hit
- `late_entry` — entered after optimal entry point
- `wrong_direction` — bias was incorrect
- `oversize` — position too large for conditions
- `fomo` — entered without proper setup
- `revenge` — traded to recover recent loss

## Strategy Scoring System
Run `evaluate_strategies()` after every 10 closed trades:

| Metric | How Calculated |
|--------|----------------|
| Win rate | wins / total |
| Avg R | mean of R-multiples |
| Expectancy | (win_rate * avg_win_R) - (loss_rate * avg_loss_R) |
| Max consecutive losses | longest losing streak |

### Auto-Disable Rules
- If expectancy < -2.0 AND total_trades >= 20 → **DISABLE** strategy
- If expectancy < 0 AND total_trades >= 20 → **REDUCE SIZE** (0.5x modifier)
- If win_rate < 0.35 AND total_trades >= 20 → **REVIEW** (flag for human)

### Size Modifier
- Expectancy > 0.5 → 1.2x size (reward winners)
- Expectancy 0 to 0.5 → 1.0x (standard)
- Expectancy -2 to 0 → 0.5x (reduce losers)
- Expectancy < -2 → 0.0x (disabled)

## Error Cluster Detection
Run `detect_error_clusters()` weekly:
- Group mistakes by (strategy, mistake_type)
- If same mistake appears >= 3 times in 30 days → generate rule modification suggestion
- Suggestions map to concrete fixes (see strategy_ranker.py)

## Monte Carlo Integration
Run `stress_test_scenarios()` monthly (or after 50 new trades):
- Normal conditions
- Reduced win rate (-20% of winners)
- Amplified losses (1.5x loss size)
- Black swan injection (5% of trades become -5R)
- If ruin_probability > 10% in ANY scenario → alert + review all strategies

## Self-Annealing Loop
1. Error detected in trade journal
2. Error cluster identified
3. Rule modification suggested
4. Strategy weight adjusted or strategy disabled
5. System re-evaluated with Monte Carlo
6. If improved → update directive with new thresholds
7. If not improved → revert and try alternative fix

## Edge Cases
- New strategies start with `eval_status = "insufficient_data"` until 20 trades
- Don't auto-disable strategies that are working in a regime they weren't designed for (check regime_fit)
- Manual override: human can force-enable any strategy via journal database
