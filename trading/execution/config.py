"""
Trading system configuration.
All tunable parameters live here — no magic numbers in execution code.
"""

import os
from pathlib import Path

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "journal.db"
TMP_DIR = BASE_DIR / ".tmp"

# --- Trading Sessions (UTC) ---
SESSIONS = {
    "asia":   {"start": "00:00", "end": "08:00", "label": "Asia"},
    "london": {"start": "07:00", "end": "16:00", "label": "London"},
    "ny":     {"start": "12:00", "end": "21:00", "label": "New York"},
}
SESSION_OVERLAP = {
    "london_ny": {"start": "12:00", "end": "16:00", "label": "London/NY Overlap"},
}

# --- Market Structure ---
SWING_LOOKBACK = 5          # bars each side for swing detection
BOS_MIN_BARS = 3            # minimum bars between swing points for valid BOS
LIQUIDITY_SWEEP_TOLERANCE = 0.0002  # price tolerance for sweep detection (0.02%)

# --- Regime Detection ---
ADX_PERIOD = 14
ADX_TREND_THRESHOLD = 25    # above = trending, below = ranging
VOLATILITY_LOOKBACK = 20    # bars for volatility regime
REGIME_SMOOTHING = 3        # EMA smoothing for regime signals

# --- Momentum / Mean-Reversion ---
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BBANDS_PERIOD = 20
BBANDS_STD = 2.0

# --- Volume ---
VOLUME_MA_PERIOD = 20
VOLUME_SPIKE_THRESHOLD = 1.5  # multiplier above MA to flag spike

# --- Risk Management ---
DEFAULT_RISK_PCT = 1.0       # risk 1% of account per trade
MAX_RISK_PCT = 2.0           # hard cap
ATR_PERIOD = 14
ATR_SL_MULTIPLIER = 1.5     # stop loss = ATR * multiplier
ATR_TP_MULTIPLIER = 3.0     # take profit = ATR * multiplier (default 2:1 RR)
MAX_DRAWDOWN_PCT = 15.0     # kill switch at 15% drawdown
MAX_DAILY_LOSS_PCT = 3.0    # stop trading after 3% daily loss
MAX_CORRELATED_POSITIONS = 3 # max positions in correlated pairs
MAX_OPEN_POSITIONS = 5

# --- Position Sizing ---
KELLY_FRACTION = 0.25       # quarter-Kelly for safety
MIN_POSITION_SIZE = 0.01    # minimum lot size
MAX_POSITION_PCT = 5.0      # max 5% of account in single position

# --- Strategy Scoring ---
CONFIDENCE_LOW = 40
CONFIDENCE_MEDIUM = 65
CONFIDENCE_HIGH = 80
MIN_CONFIDENCE_TO_TRADE = 50
STRATEGY_DISABLE_THRESHOLD = -2.0  # disable strategy if expectancy drops below
STRATEGY_EVAL_MIN_TRADES = 20      # minimum trades before auto-disable kicks in
STRATEGY_LOOKBACK_TRADES = 50      # rolling window for strategy evaluation

# --- Monte Carlo ---
MC_SIMULATIONS = 10000
MC_TRADE_COUNT = 252        # ~1 year of daily trades
MC_CONFIDENCE_LEVELS = [0.05, 0.25, 0.50, 0.75, 0.95]

# --- Journal ---
JOURNAL_EXPORT_FORMATS = ["json", "csv"]
HEATMAP_BUCKETS = {
    "hour": 24,
    "day_of_week": 7,
    "session": 3,
}

# --- Backtest ---
DEFAULT_INITIAL_CAPITAL = 10000.0
DEFAULT_COMMISSION = 0.0002  # 2 pips equivalent
SLIPPAGE_MODEL = "fixed"     # "fixed" or "volatility"
FIXED_SLIPPAGE = 0.0001     # 1 pip

# --- Multi-Timeframe ---
HTF_TIMEFRAMES = ["4H", "D"]  # higher timeframe confirmation
HTF_BIAS_PENALTY = 30         # score penalty for trading against HTF bias
HTF_NEUTRAL_PENALTY = 10      # penalty when HTF is neutral (no clear direction)

# --- News Filter ---
NEWS_BLACKOUT_MINUTES = 30    # no trading ±30 min around high-impact events
NEWS_CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
NEWS_HIGH_IMPACT_ONLY = True  # only filter red (high-impact) events
NEWS_CACHE_HOURS = 4          # re-fetch calendar every 4 hours

# --- Risk State Persistence ---
RISK_STATE_PATH = DATA_DIR / "risk_state.json"
RISK_STATE_SAVE_INTERVAL = 10  # save state every N seconds
