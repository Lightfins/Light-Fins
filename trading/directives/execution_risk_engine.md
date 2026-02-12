# Directive: Execution & Risk Engine

## Goal
Protect capital through position sizing, stop placement, drawdown containment, and kill switches. No trade is taken without risk engine approval.

## Execution Scripts

| Script | Purpose |
|--------|---------|
| `execution/risk_engine.py` | Position sizing, SL/TP, drawdown, correlation, kill switch |
| `execution/backtest_engine.py` | Historical validation of strategies |

## Risk Parameters (from config.py)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Risk per trade | 1% | Industry standard for prop firms |
| Max risk cap | 2% | Hard ceiling, never exceeded |
| SL multiplier | 1.5x ATR | Gives room without overexposure |
| TP multiplier | 3.0x ATR | Targets 2:1 RR minimum |
| Max drawdown | 15% | Kill switch trigger |
| Max daily loss | 3% | Stop trading for the day |
| Max open positions | 5 | Prevents overtrading |
| Max correlated positions | 3 | Prevents hidden concentration |
| Kelly fraction | 0.25 | Quarter-Kelly for safety margin |

## Position Sizing Logic (in order)
1. Calculate fixed fractional size: `capital * risk% / distance_to_SL`
2. Calculate Kelly size: `kelly_f * capital / distance_to_SL` (where kelly_f uses quarter-Kelly)
3. Take the **smaller** of the two
4. Cap at max position % of account (5%)
5. Floor at minimum lot size (0.01)
6. Deduct commission + slippage from effective risk

## Kill Switch Conditions
Any of these triggers halts ALL trading:
- Drawdown >= 15% from peak
- Daily loss >= 3% of capital
- Max open positions reached (5)

Kill switch resets at next daily session start (UTC midnight), UNLESS drawdown is still above threshold.

## Correlation Check
Before opening any trade:
1. Look up correlation group (e.g., "USD short" group: EURUSD long, GBPUSD long, AUDUSD long)
2. Count existing positions in same group
3. If count >= 3 → BLOCK the trade

## Backtest Validation
Before deploying any strategy live:
1. Run `BacktestEngine.run(df, strategy_fn, name)` on at least 1000 bars
2. Require: win_rate > 0.40, profit_factor > 1.3, max_drawdown < 20%
3. If fails → strategy does not go live

## Edge Cases
- ATR can compress to near-zero in dead markets → floor SL distance at 0.1% of price
- Slippage is modeled as fixed (1 pip) — in real deployment, use volatility-based model
- Commission is entry + exit (round-trip)
- Risk of ruin calculation is an approximation — use Monte Carlo for definitive answer
