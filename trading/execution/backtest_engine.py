"""
Backtesting Framework
---------------------
Runs strategies against historical data with realistic execution modeling.
Includes: slippage, commission, drawdown tracking, trade logging.

NOT a production backtester (no tick data, no order book simulation).
Purpose: validate strategy logic before live deployment.

Inputs:  OHLCV DataFrame, strategy function, risk parameters
Outputs: Backtest results with full trade log and equity curve
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Callable, Optional
from config import (
    DEFAULT_INITIAL_CAPITAL, DEFAULT_COMMISSION, FIXED_SLIPPAGE,
    DEFAULT_RISK_PCT, ATR_PERIOD
)


class BacktestEngine:
    """Event-driven backtester with trade-by-trade simulation."""

    def __init__(
        self,
        initial_capital: float = DEFAULT_INITIAL_CAPITAL,
        commission: float = DEFAULT_COMMISSION,
        slippage: float = FIXED_SLIPPAGE,
        risk_pct: float = DEFAULT_RISK_PCT,
    ):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.risk_pct = risk_pct
        self.peak_capital = initial_capital
        self.trades = []
        self.equity_curve = []
        self.open_trade = None

    def run(
        self,
        df: pd.DataFrame,
        strategy_fn: Callable,
        strategy_name: str = "unnamed",
    ) -> dict:
        """
        Run backtest.

        strategy_fn(row, prev_rows, state) -> dict or None
            Returns: {
                "action": "buy" | "sell" | "close" | None,
                "stop_loss": float,
                "take_profit": float,
                "setup_type": str,
                "entry_reason": str,
            }
        """
        self.capital = self.initial_capital
        self.peak_capital = self.initial_capital
        self.trades = []
        self.equity_curve = []
        self.open_trade = None

        state = {"bars_since_entry": 0}

        for i in range(ATR_PERIOD + 1, len(df)):
            row = df.iloc[i]
            prev = df.iloc[max(0, i - 50):i]

            # Check open trade SL/TP
            if self.open_trade:
                self._check_exit(row)
                state["bars_since_entry"] += 1

            # Get strategy signal
            signal = strategy_fn(row, prev, state)

            if signal and signal.get("action") in ("buy", "sell") and not self.open_trade:
                self._open_trade(row, signal, strategy_name)
                state["bars_since_entry"] = 0
            elif signal and signal.get("action") == "close" and self.open_trade:
                self._close_trade(row["close"], "strategy_exit", row)

            # Record equity
            unrealized = 0
            if self.open_trade:
                if self.open_trade["direction"] == "long":
                    unrealized = (row["close"] - self.open_trade["entry_price"]) * self.open_trade["size"]
                else:
                    unrealized = (self.open_trade["entry_price"] - row["close"]) * self.open_trade["size"]

            equity = self.capital + unrealized
            self.equity_curve.append({
                "timestamp": str(row.get("timestamp", i)),
                "equity": round(equity, 2),
                "capital": round(self.capital, 2),
                "unrealized": round(unrealized, 2),
            })

        # Close any remaining position
        if self.open_trade:
            last_row = df.iloc[-1]
            self._close_trade(last_row["close"], "end_of_data", last_row)

        return self._compile_results(strategy_name, len(df))

    def _open_trade(self, row, signal, strategy_name):
        direction = "long" if signal["action"] == "buy" else "short"
        entry_price = row["close"]

        # Apply slippage
        if direction == "long":
            entry_price += self.slippage
        else:
            entry_price -= self.slippage

        sl = signal.get("stop_loss", 0)
        tp = signal.get("take_profit", 0)

        risk_distance = abs(entry_price - sl) if sl else entry_price * 0.01
        risk_amount = self.capital * (self.risk_pct / 100)
        size = risk_amount / risk_distance if risk_distance > 0 else 0

        self.open_trade = {
            "entry_price": entry_price,
            "stop_loss": sl,
            "take_profit": tp,
            "direction": direction,
            "size": size,
            "risk_amount": risk_amount,
            "strategy": strategy_name,
            "setup_type": signal.get("setup_type", ""),
            "entry_reason": signal.get("entry_reason", ""),
            "entry_time": str(row.get("timestamp", "")),
        }

    def _check_exit(self, row):
        trade = self.open_trade
        if not trade:
            return

        if trade["direction"] == "long":
            # Stop loss
            if trade["stop_loss"] and row["low"] <= trade["stop_loss"]:
                self._close_trade(trade["stop_loss"] - self.slippage, "stop_loss", row)
                return
            # Take profit
            if trade["take_profit"] and row["high"] >= trade["take_profit"]:
                self._close_trade(trade["take_profit"] - self.slippage, "take_profit", row)
                return
        else:
            if trade["stop_loss"] and row["high"] >= trade["stop_loss"]:
                self._close_trade(trade["stop_loss"] + self.slippage, "stop_loss", row)
                return
            if trade["take_profit"] and row["low"] <= trade["take_profit"]:
                self._close_trade(trade["take_profit"] + self.slippage, "take_profit", row)
                return

    def _close_trade(self, exit_price: float, reason: str, row):
        trade = self.open_trade
        if not trade:
            return

        size = trade["size"]
        if trade["direction"] == "long":
            gross_pnl = (exit_price - trade["entry_price"]) * size
        else:
            gross_pnl = (trade["entry_price"] - exit_price) * size

        cost = self.commission * size * 2  # entry + exit
        net_pnl = gross_pnl - cost
        r_multiple = net_pnl / trade["risk_amount"] if trade["risk_amount"] else 0

        self.capital += net_pnl
        if self.capital > self.peak_capital:
            self.peak_capital = self.capital

        self.trades.append({
            "entry_price": round(trade["entry_price"], 5),
            "exit_price": round(exit_price, 5),
            "direction": trade["direction"],
            "size": round(size, 4),
            "gross_pnl": round(gross_pnl, 2),
            "net_pnl": round(net_pnl, 2),
            "r_multiple": round(r_multiple, 2),
            "exit_reason": reason,
            "strategy": trade["strategy"],
            "setup_type": trade["setup_type"],
            "entry_time": trade["entry_time"],
            "exit_time": str(row.get("timestamp", "")),
        })

        self.open_trade = None

    def _compile_results(self, strategy_name: str, total_bars: int) -> dict:
        if not self.trades:
            return {
                "strategy": strategy_name,
                "total_trades": 0,
                "error": "No trades generated",
            }

        pnls = [t["net_pnl"] for t in self.trades]
        r_multiples = [t["r_multiple"] for t in self.trades]
        wins = [t for t in self.trades if t["net_pnl"] > 0]
        losses = [t for t in self.trades if t["net_pnl"] <= 0]

        win_rate = len(wins) / len(self.trades) if self.trades else 0
        avg_win = np.mean([t["net_pnl"] for t in wins]) if wins else 0
        avg_loss = np.mean([abs(t["net_pnl"]) for t in losses]) if losses else 0
        profit_factor = sum(t["net_pnl"] for t in wins) / max(sum(abs(t["net_pnl"]) for t in losses), 0.01)

        # Expectancy
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

        # Max drawdown from equity curve
        equities = [e["equity"] for e in self.equity_curve]
        peak = equities[0]
        max_dd = 0
        max_dd_pct = 0
        for eq in equities:
            if eq > peak:
                peak = eq
            dd = peak - eq
            dd_pct = dd / peak * 100 if peak > 0 else 0
            max_dd = max(max_dd, dd)
            max_dd_pct = max(max_dd_pct, dd_pct)

        # Max consecutive losses
        max_consec_loss = 0
        consec = 0
        for t in self.trades:
            if t["net_pnl"] <= 0:
                consec += 1
                max_consec_loss = max(max_consec_loss, consec)
            else:
                consec = 0

        # Sharpe (from trade returns)
        if len(pnls) > 1:
            sharpe = np.mean(pnls) / np.std(pnls) * np.sqrt(252) if np.std(pnls) > 0 else 0
        else:
            sharpe = 0

        return {
            "strategy": strategy_name,
            "total_bars": total_bars,
            "total_trades": len(self.trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(win_rate, 4),
            "avg_win": round(float(avg_win), 2),
            "avg_loss": round(float(avg_loss), 2),
            "profit_factor": round(float(profit_factor), 2),
            "expectancy": round(float(expectancy), 2),
            "total_pnl": round(sum(pnls), 2),
            "total_return_pct": round((self.capital - self.initial_capital) / self.initial_capital * 100, 2),
            "max_drawdown": round(max_dd, 2),
            "max_drawdown_pct": round(max_dd_pct, 2),
            "max_consecutive_losses": max_consec_loss,
            "avg_r_multiple": round(float(np.mean(r_multiples)), 2),
            "sharpe_ratio": round(float(sharpe), 2),
            "final_capital": round(self.capital, 2),
            "trade_log": self.trades,
            "equity_curve": self.equity_curve[::max(1, len(self.equity_curve) // 200)],  # downsample
        }


# --- Example Strategy Functions ---

def momentum_bos_strategy(row, prev, state) -> Optional[dict]:
    """Simple momentum strategy: buy on higher high, sell on lower low."""
    if len(prev) < 20:
        return None

    recent_high = prev["high"].rolling(10).max().iloc[-1]
    recent_low = prev["low"].rolling(10).min().iloc[-1]
    atr = (prev["high"] - prev["low"]).rolling(14).mean().iloc[-1]

    if row["close"] > recent_high:
        return {
            "action": "buy",
            "stop_loss": row["close"] - atr * 1.5,
            "take_profit": row["close"] + atr * 3.0,
            "setup_type": "breakout_high",
            "entry_reason": "Close above recent high",
        }
    elif row["close"] < recent_low:
        return {
            "action": "sell",
            "stop_loss": row["close"] + atr * 1.5,
            "take_profit": row["close"] - atr * 3.0,
            "setup_type": "breakout_low",
            "entry_reason": "Close below recent low",
        }
    return None


if __name__ == "__main__":
    np.random.seed(42)
    n = 1000
    # Trending then ranging then trending market
    t1 = np.cumsum(np.random.randn(333) * 0.001 + 0.0002)
    t2 = np.cumsum(np.random.randn(334) * 0.0005)
    t3 = np.cumsum(np.random.randn(333) * 0.001 - 0.0002)
    prices = 1.1000 + np.concatenate([t1, t2 + t1[-1], t3 + t1[-1] + t2[-1]])

    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="1h"),
        "open": prices,
        "high": prices + np.abs(np.random.randn(n) * 0.0005),
        "low": prices - np.abs(np.random.randn(n) * 0.0005),
        "close": prices + np.random.randn(n) * 0.0003,
        "volume": np.random.randint(100, 10000, n),
    })

    engine = BacktestEngine()
    results = engine.run(df, momentum_bos_strategy, "momentum_bos")

    print(f"Strategy: {results['strategy']}")
    print(f"Total Trades: {results['total_trades']}")
    print(f"Win Rate: {results['win_rate'] * 100:.1f}%")
    print(f"Profit Factor: {results['profit_factor']}")
    print(f"Expectancy: ${results['expectancy']}")
    print(f"Total P&L: ${results['total_pnl']}")
    print(f"Max Drawdown: {results['max_drawdown_pct']:.1f}%")
    print(f"Sharpe Ratio: {results['sharpe_ratio']}")
