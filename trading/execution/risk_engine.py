"""
Risk & Execution Engine
-----------------------
Handles: position sizing, stop-loss placement, take-profit targets,
drawdown containment, risk-of-ruin calculation, correlation checks.

This is the DEFENSE LAYER. Strategy finds trades. Risk engine decides
whether you survive long enough to collect.

Inputs:  Account state, trade parameters, ATR data
Outputs: Position size, SL/TP levels, risk metrics, kill-switch triggers
"""

import numpy as np
import pandas as pd
import json
import os
from typing import Optional
from config import (
    DEFAULT_RISK_PCT, MAX_RISK_PCT, ATR_PERIOD, ATR_SL_MULTIPLIER,
    ATR_TP_MULTIPLIER, MAX_DRAWDOWN_PCT, MAX_DAILY_LOSS_PCT,
    MAX_CORRELATED_POSITIONS, MAX_OPEN_POSITIONS,
    KELLY_FRACTION, MIN_POSITION_SIZE, MAX_POSITION_PCT,
    DEFAULT_COMMISSION, FIXED_SLIPPAGE, RISK_STATE_PATH, DATA_DIR
)


class RiskEngine:
    """Stateful risk manager that tracks account exposure and enforces limits."""

    def __init__(self, initial_capital: float, risk_pct: float = DEFAULT_RISK_PCT):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.risk_pct = min(risk_pct, MAX_RISK_PCT)
        self.peak_capital = initial_capital
        self.open_positions = []
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.killed = False
        self.kill_reason = ""

    @property
    def drawdown_pct(self) -> float:
        if self.peak_capital <= 0:
            return 0.0
        return (self.peak_capital - self.capital) / self.peak_capital * 100

    @property
    def total_exposure(self) -> float:
        return sum(p.get("position_value", 0) for p in self.open_positions)

    @property
    def exposure_pct(self) -> float:
        if self.capital <= 0:
            return 0.0
        return self.total_exposure / self.capital * 100

    def check_kill_switch(self) -> dict:
        """Check if any hard limits are breached."""
        reasons = []

        if self.drawdown_pct >= MAX_DRAWDOWN_PCT:
            reasons.append(f"Max drawdown breached: {self.drawdown_pct:.1f}% >= {MAX_DRAWDOWN_PCT}%")

        if abs(self.daily_pnl / max(self.capital, 1)) * 100 >= MAX_DAILY_LOSS_PCT and self.daily_pnl < 0:
            reasons.append(f"Daily loss limit: {self.daily_pnl:.2f}")

        if len(self.open_positions) >= MAX_OPEN_POSITIONS:
            reasons.append(f"Max open positions: {len(self.open_positions)}")

        if reasons:
            self.killed = True
            self.kill_reason = "; ".join(reasons)

        return {
            "killed": self.killed,
            "reasons": reasons,
            "drawdown_pct": round(self.drawdown_pct, 2),
            "daily_pnl": round(self.daily_pnl, 2),
            "open_positions": len(self.open_positions),
        }

    def compute_stop_loss(self, entry_price: float, atr: float,
                          direction: str, multiplier: float = ATR_SL_MULTIPLIER) -> float:
        """ATR-based stop loss placement."""
        distance = atr * multiplier
        if direction == "long":
            return round(entry_price - distance, 5)
        else:
            return round(entry_price + distance, 5)

    def compute_take_profit(self, entry_price: float, stop_loss: float,
                            direction: str, rr_ratio: float = None) -> float:
        """Take profit based on R-multiple of stop distance."""
        if rr_ratio is None:
            rr_ratio = ATR_TP_MULTIPLIER / ATR_SL_MULTIPLIER
        risk = abs(entry_price - stop_loss)
        reward = risk * rr_ratio
        if direction == "long":
            return round(entry_price + reward, 5)
        else:
            return round(entry_price - reward, 5)

    def compute_position_size(self, entry_price: float, stop_loss: float,
                              win_rate: Optional[float] = None,
                              avg_win_loss_ratio: Optional[float] = None) -> dict:
        """
        Position sizing with multiple methods:
        1. Fixed fractional (default)
        2. Kelly criterion (if win_rate provided)
        3. Volatility-adjusted (scales down in high vol)
        """
        risk_amount = self.capital * (self.risk_pct / 100)
        risk_per_unit = abs(entry_price - stop_loss)

        if risk_per_unit <= 0:
            return {"size": 0, "method": "error", "reason": "Invalid SL distance"}

        # Fixed fractional
        fixed_size = risk_amount / risk_per_unit

        # Kelly criterion
        kelly_size = fixed_size  # default fallback
        if win_rate is not None and avg_win_loss_ratio is not None and avg_win_loss_ratio > 0:
            kelly_f = (win_rate * avg_win_loss_ratio - (1 - win_rate)) / avg_win_loss_ratio
            kelly_f = max(0, kelly_f * KELLY_FRACTION)  # fractional Kelly
            kelly_risk = self.capital * kelly_f
            kelly_size = kelly_risk / risk_per_unit

        # Use the more conservative
        size = min(fixed_size, kelly_size)

        # Cap at max position %
        max_value = self.capital * (MAX_POSITION_PCT / 100)
        max_size = max_value / entry_price
        size = min(size, max_size)

        # Floor
        size = max(size, MIN_POSITION_SIZE)

        # Account for commission and slippage
        effective_risk = risk_per_unit + DEFAULT_COMMISSION + FIXED_SLIPPAGE
        adjusted_size = risk_amount / effective_risk
        size = min(size, adjusted_size)
        size = max(size, MIN_POSITION_SIZE)

        position_value = size * entry_price

        return {
            "size": round(size, 4),
            "position_value": round(position_value, 2),
            "risk_amount": round(risk_amount, 2),
            "risk_per_unit": round(risk_per_unit, 5),
            "effective_risk": round(effective_risk, 5),
            "method": "kelly" if kelly_size < fixed_size else "fixed_fractional",
            "position_pct": round(position_value / self.capital * 100, 2),
        }

    def check_correlation(self, pair: str, direction: str) -> dict:
        """
        Check for correlated exposure.
        Prevents: going long EURUSD and long GBPUSD simultaneously (both USD shorts).
        """
        # Simple correlation groups (can be extended)
        correlation_groups = {
            "usd_short": ["EURUSD_long", "GBPUSD_long", "AUDUSD_long"],
            "usd_long": ["EURUSD_short", "GBPUSD_short", "AUDUSD_short"],
            "jpy_short": ["USDJPY_long", "EURJPY_long", "GBPJPY_long"],
            "jpy_long": ["USDJPY_short", "EURJPY_short", "GBPJPY_short"],
        }

        trade_key = f"{pair}_{direction}"
        correlated = []

        for group, members in correlation_groups.items():
            if trade_key in members:
                for pos in self.open_positions:
                    pos_key = f"{pos['pair']}_{pos['direction']}"
                    if pos_key in members and pos_key != trade_key:
                        correlated.append(pos_key)

        blocked = len(correlated) >= MAX_CORRELATED_POSITIONS

        return {
            "blocked": blocked,
            "correlated_positions": correlated,
            "count": len(correlated),
            "limit": MAX_CORRELATED_POSITIONS,
        }

    def register_trade(self, trade: dict):
        """Register a new open position."""
        self.open_positions.append(trade)
        self.daily_trades += 1

    def close_trade(self, trade_id: str, exit_price: float) -> dict:
        """Close a position and update P&L."""
        trade = None
        for i, pos in enumerate(self.open_positions):
            if pos.get("id") == trade_id:
                trade = self.open_positions.pop(i)
                break

        if trade is None:
            return {"error": f"Trade {trade_id} not found"}

        entry = trade["entry_price"]
        size = trade["size"]
        direction = trade["direction"]

        if direction == "long":
            pnl = (exit_price - entry) * size
        else:
            pnl = (entry - exit_price) * size

        # Deduct costs
        cost = (DEFAULT_COMMISSION + FIXED_SLIPPAGE) * size
        net_pnl = pnl - cost

        self.capital += net_pnl
        self.daily_pnl += net_pnl
        if self.capital > self.peak_capital:
            self.peak_capital = self.capital

        r_multiple = net_pnl / trade.get("risk_amount", 1) if trade.get("risk_amount") else 0

        return {
            "trade_id": trade_id,
            "gross_pnl": round(pnl, 2),
            "costs": round(cost, 4),
            "net_pnl": round(net_pnl, 2),
            "r_multiple": round(r_multiple, 2),
            "capital_after": round(self.capital, 2),
            "drawdown_pct": round(self.drawdown_pct, 2),
        }

    def reset_daily(self):
        """Reset daily counters (call at session start)."""
        self.daily_pnl = 0.0
        self.daily_trades = 0
        if not self.killed or self.drawdown_pct < MAX_DRAWDOWN_PCT:
            self.killed = False
            self.kill_reason = ""

    def compute_risk_of_ruin(self, win_rate: float, avg_win: float, avg_loss: float,
                             ruin_level_pct: float = 50.0) -> float:
        """
        Estimate probability of hitting ruin level using simplified formula.
        ruin_level_pct: what % loss counts as ruin (default 50%).
        """
        if avg_loss == 0 or win_rate >= 1.0:
            return 0.0
        if win_rate <= 0:
            return 1.0

        edge = win_rate * avg_win - (1 - win_rate) * avg_loss
        if edge <= 0:
            return 1.0  # negative expectancy = certain ruin eventually

        # Risk of ruin approximation (simplified)
        a = avg_win / avg_loss if avg_loss > 0 else 1
        q = 1 - win_rate
        p = win_rate

        if a == 0:
            return 1.0

        ratio = q / (p * a) if (p * a) > 0 else 1
        n_units = (ruin_level_pct / 100) * self.capital / (avg_loss if avg_loss > 0 else 1)

        ror = min(1.0, ratio ** n_units) if ratio < 1 else 1.0
        return round(ror, 4)

    def save_state(self):
        """
        Persist risk engine state to disk.
        FIX #2: Server restart no longer wipes position tracking or kill switch.
        """
        os.makedirs(DATA_DIR, exist_ok=True)
        state = {
            "capital": self.capital,
            "initial_capital": self.initial_capital,
            "peak_capital": self.peak_capital,
            "risk_pct": self.risk_pct,
            "open_positions": self.open_positions,
            "daily_pnl": self.daily_pnl,
            "daily_trades": self.daily_trades,
            "killed": self.killed,
            "kill_reason": self.kill_reason,
        }
        tmp_path = str(RISK_STATE_PATH) + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, str(RISK_STATE_PATH))

    def restore_state(self) -> bool:
        """
        Restore risk engine state from disk on startup.
        Returns True if state was restored, False if starting fresh.
        """
        if not os.path.exists(RISK_STATE_PATH):
            return False
        try:
            with open(RISK_STATE_PATH, "r") as f:
                state = json.load(f)
            self.capital = state["capital"]
            self.initial_capital = state["initial_capital"]
            self.peak_capital = state["peak_capital"]
            self.risk_pct = state.get("risk_pct", self.risk_pct)
            self.open_positions = state.get("open_positions", [])
            self.daily_pnl = state.get("daily_pnl", 0.0)
            self.daily_trades = state.get("daily_trades", 0)
            self.killed = state.get("killed", False)
            self.kill_reason = state.get("kill_reason", "")
            return True
        except (json.JSONDecodeError, KeyError, IOError):
            return False

    def get_status(self) -> dict:
        """Full risk engine status snapshot."""
        return {
            "capital": round(self.capital, 2),
            "initial_capital": round(self.initial_capital, 2),
            "pnl": round(self.capital - self.initial_capital, 2),
            "pnl_pct": round((self.capital - self.initial_capital) / self.initial_capital * 100, 2),
            "peak_capital": round(self.peak_capital, 2),
            "drawdown_pct": round(self.drawdown_pct, 2),
            "daily_pnl": round(self.daily_pnl, 2),
            "daily_trades": self.daily_trades,
            "open_positions": len(self.open_positions),
            "total_exposure": round(self.total_exposure, 2),
            "exposure_pct": round(self.exposure_pct, 2),
            "killed": self.killed,
            "kill_reason": self.kill_reason,
        }


if __name__ == "__main__":
    engine = RiskEngine(initial_capital=10000, risk_pct=1.0)

    sl = engine.compute_stop_loss(1.1000, 0.0020, "long")
    tp = engine.compute_take_profit(1.1000, sl, "long", rr_ratio=2.5)
    sizing = engine.compute_position_size(1.1000, sl, win_rate=0.55, avg_win_loss_ratio=2.0)

    print(f"Entry: 1.1000  SL: {sl}  TP: {tp}")
    print(f"Position: {sizing}")
    print(f"Risk of Ruin: {engine.compute_risk_of_ruin(0.55, 200, 100)}")
    print(f"Status: {engine.get_status()}")
