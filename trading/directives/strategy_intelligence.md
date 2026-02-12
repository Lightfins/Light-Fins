# Directive: Strategic Intelligence System

## Goal
Provide the trading agent with market-reading capabilities that detect structure, regime, session behavior, and confluence — then score every potential trade before entry.

## Inputs
- OHLCV data (1H minimum, multi-timeframe preferred)
- Current UTC timestamp (for session detection)

## Execution Scripts

| Script | Purpose |
|--------|---------|
| `execution/market_structure.py` | Swing detection, HH/HL/LH/LL, BOS, liquidity sweeps |
| `execution/session_analyzer.py` | Session labeling, per-session volatility/volume stats |
| `execution/regime_detector.py` | ADX-based trend/range classification, vol regime, strategy fit |
| `execution/trade_scorer.py` | 0-100 confidence scoring with component breakdown |

## Pipeline (in order)
1. **Market Structure** → `analyze_market_structure(df)` → annotated df + bias dict
2. **Session Analysis** → `analyze_sessions(df)` → session labels + stats
3. **Regime Detection** → `analyze_regime(df)` → regime labels + summary
4. **Trade Scoring** → `compute_trade_score(signals)` → score + verdict

## Decision Rules

### Entry Gate
- Score >= 50 AND zero red flags → TRADE
- Score < 50 OR any red flag → NO TRADE
- Score >= 80 → HIGH confidence, scale up position
- Score 65-79 → MEDIUM confidence, standard position
- Score 50-64 → LOW confidence, reduce position

### Regime Override
- If regime = "unstable" (>15 shifts in 100 bars) → reduce all confidence by 15 points
- If regime just shifted → skip next 3 bars minimum
- If strategy_fit != current regime → NO TRADE regardless of score

### Session Rules
- Prefer London and NY sessions
- London/NY overlap = highest priority
- Asia session = mean-reversion only (low volatility)
- Off-hours = NO TRADE

## Edge Cases & Learnings
- Liquidity sweeps are strongest when they coincide with BOS
- Back-to-back BOS signals are often whipsaws — require minimum 3 bars between
- ADX trending threshold (25) is a guideline, not gospel — in low-vol pairs, 20 may be better
- Volume spikes without price movement = absorption, not confirmation

## Output
Signal dict ready for `trade_scorer.py`, containing all required fields from each analyzer.
