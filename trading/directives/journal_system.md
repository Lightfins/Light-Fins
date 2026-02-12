# Directive: Transparent Journal System

## Goal
Provide a brutally honest, human-readable, exportable journal dashboard visible inside the trading cockpit app.

## Dashboard Components

### 1. Daily Summary
- Trades taken, wins, losses
- Gross P&L, net P&L
- Best/worst trade (R-multiple)
- Capital end-of-day
- Generated via `update_daily_summary()` at UTC midnight

### 2. Weekly Performance Breakdown
- Aggregated from daily summaries
- Week-over-week comparison
- Trend direction (improving / declining / flat)

### 3. Error Heatmap
- Generated via `get_error_heatmap()`
- Dimensions: hour of day, day of week, session
- Shows WHERE and WHEN mistakes concentrate
- Visual: cockpit UI renders as color-coded grid

### 4. Strategy Performance Ranking
- Generated via `evaluate_strategies()`
- Sorted by expectancy (descending)
- Shows: strategy name, win rate, expectancy, status, size modifier
- Color-coded: green = healthy, amber = review, red = failing/disabled

### 5. Equity Curve
- Generated via `get_equity_curve(days=90)`
- Rendered on HTML5 canvas (charts.js)
- Shows: daily capital, P&L overlay, drawdown fill
- Green line = above start, red line = below start

### 6. Max Drawdown Tracker
- Real-time: `risk_engine.drawdown_pct`
- Historical: from daily_summary.max_drawdown_pct
- Visual: gauge bar in risk panel (green/amber/red thresholds)

### 7. Risk-Adjusted Return Metrics
- Sharpe Ratio (annualized): `avg_daily_return / std * sqrt(252)`
- Sortino Ratio: uses downside deviation only
- Generated via `get_performance_metrics(days=30)`

### 8. Session-Based Performance
- Which sessions are profitable vs. losing
- From `session_analyzer.py` stats
- Informs session trading rules

### 9. Psychological Pattern Tracker
- Tracks mistake_class distribution over time
- Flags: FOMO streaks, revenge trading clusters
- From `detect_error_clusters()` in strategy_ranker.py

## Export Formats
- JSON: `export_trades("json", days=90)`
- CSV: `export_trades("csv", days=90)`
- Available via API: `GET /api/journal/export?fmt=json&days=90`

## Honesty Rules
- Never hide losing streaks
- Never smooth equity curve
- Show raw R-multiples, not just P&L
- Mistake classification is mandatory on every trade
- "none" is valid only when trade followed all rules
- Error heatmap must be visible on the main dashboard (not buried)

## Update Frequency
- Real-time: risk status, open positions, confidence meter
- Every 5 seconds: equity curve, journal, alerts (via dashboard.js polling)
- Daily: daily summary computation
- Weekly: error cluster analysis
- Monthly: Monte Carlo stress test

## API Endpoints

| Endpoint | Data |
|----------|------|
| GET /api/status | System status, risk, kill switch |
| GET /api/journal | Trade history |
| GET /api/journal/export | Export (JSON/CSV) |
| GET /api/equity | Equity curve |
| GET /api/strategies | Strategy rankings + error clusters |
| GET /api/errors | Error heatmap |
| GET /api/metrics | Sharpe, Sortino, drawdown, win rate |
| GET /api/montecarlo | Monte Carlo simulation results |
