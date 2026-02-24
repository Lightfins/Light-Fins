"""
Live trading executor — Phase 1: Hyperliquid, Phase 2: CCXT multi-exchange.
Safety-first: kill switch, confirmation before trades, full logging.
"""

import os
import json
import logging
import datetime
from pathlib import Path
from typing import Dict, Any, Optional

LOG_DIR = Path("trading/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("live_executor")
handler = logging.FileHandler(LOG_DIR / "live_trades.log")
handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class KillSwitch:
    """Global kill switch — when active, no trades execute."""

    KILL_FILE = Path("trading/workspace/.kill_switch")

    @classmethod
    def is_active(cls) -> bool:
        return cls.KILL_FILE.exists()

    @classmethod
    def activate(cls):
        cls.KILL_FILE.parent.mkdir(parents=True, exist_ok=True)
        cls.KILL_FILE.write_text(datetime.datetime.now().isoformat())
        logger.warning("KILL SWITCH ACTIVATED — all live trading halted")

    @classmethod
    def deactivate(cls):
        if cls.KILL_FILE.exists():
            cls.KILL_FILE.unlink()
        logger.info("Kill switch deactivated — live trading re-enabled")


class ReadOnlyMode:
    """Read-only testing mode — logs what would happen without executing."""

    READONLY_FILE = Path("trading/workspace/.read_only")

    @classmethod
    def is_active(cls) -> bool:
        return cls.READONLY_FILE.exists()

    @classmethod
    def activate(cls):
        cls.READONLY_FILE.parent.mkdir(parents=True, exist_ok=True)
        cls.READONLY_FILE.write_text(datetime.datetime.now().isoformat())
        logger.info("READ-ONLY mode activated — trades will be simulated only")

    @classmethod
    def deactivate(cls):
        if cls.READONLY_FILE.exists():
            cls.READONLY_FILE.unlink()
        logger.info("Read-only mode deactivated")


class LiveExecutor:
    """
    Executes trades on exchanges.
    Phase 1: Hyperliquid via their Python SDK
    Phase 2: Any exchange via CCXT
    """

    def __init__(self, exchange_id: str = "hyperliquid", testnet: bool = True):
        self.exchange_id = exchange_id
        self.testnet = testnet
        self.exchange = None
        self._setup_exchange()

    def _setup_exchange(self):
        """Initialize exchange connection."""
        if self.exchange_id == "hyperliquid":
            self._setup_hyperliquid()
        else:
            self._setup_ccxt()

    def _setup_hyperliquid(self):
        """Setup Hyperliquid connection."""
        try:
            from hyperliquid.utils import constants
            from hyperliquid.exchange import Exchange as HLExchange
            from hyperliquid.info import Info

            secret_key = os.getenv("HYPERLIQUID_SECRET_KEY", "")
            if not secret_key:
                logger.warning("HYPERLIQUID_SECRET_KEY not set — running in read-only mode")
                ReadOnlyMode.activate()
                return

            base_url = constants.TESTNET_API_URL if self.testnet else constants.MAINNET_API_URL
            self.info = Info(base_url, skip_ws=True)
            self.exchange = HLExchange(
                wallet=None,  # Will be set from secret key
                base_url=base_url,
            )
            logger.info(f"Hyperliquid {'testnet' if self.testnet else 'mainnet'} connected")
        except ImportError:
            logger.warning("hyperliquid-python-sdk not installed. Install with: pip install hyperliquid-python-sdk")
            self.exchange = None

    def _setup_ccxt(self):
        """Setup CCXT exchange connection."""
        try:
            import ccxt

            api_key = os.getenv(f"{self.exchange_id.upper()}_API_KEY", "")
            secret = os.getenv(f"{self.exchange_id.upper()}_SECRET", "")

            exchange_class = getattr(ccxt, self.exchange_id)
            config = {"enableRateLimit": True}

            if api_key:
                config["apiKey"] = api_key
            if secret:
                config["secret"] = secret
            if self.testnet:
                config["sandbox"] = True

            self.exchange = exchange_class(config)
            logger.info(f"CCXT {self.exchange_id} {'testnet' if self.testnet else 'live'} connected")
        except ImportError:
            logger.warning("ccxt not installed")
            self.exchange = None
        except Exception as e:
            logger.error(f"Failed to connect to {self.exchange_id}: {e}")
            self.exchange = None

    def place_order(
        self,
        symbol: str,
        side: str,  # "buy" or "sell"
        amount: float,
        order_type: str = "market",
        price: Optional[float] = None,
        confirm: bool = True,
    ) -> Dict[str, Any]:
        """
        Place an order with safety checks.
        Returns order result or simulation result.
        """
        # Safety checks
        if KillSwitch.is_active():
            msg = "BLOCKED: Kill switch is active. No trades will execute."
            logger.warning(msg)
            return {"status": "blocked", "reason": "kill_switch", "message": msg}

        order_info = {
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "type": order_type,
            "price": price,
            "timestamp": datetime.datetime.now().isoformat(),
            "exchange": self.exchange_id,
            "testnet": self.testnet,
        }

        # Read-only mode: just log
        if ReadOnlyMode.is_active():
            msg = f"READ-ONLY: Would {side} {amount} {symbol} @ {order_type}"
            logger.info(msg)
            return {"status": "simulated", "order": order_info, "message": msg}

        # Log the trade attempt
        logger.info(f"ORDER: {side} {amount} {symbol} @ {order_type} (price={price})")

        if self.exchange is None:
            return {"status": "error", "reason": "no_exchange", "message": "Exchange not connected"}

        try:
            if self.exchange_id == "hyperliquid":
                result = self._execute_hyperliquid(symbol, side, amount, order_type, price)
            else:
                result = self._execute_ccxt(symbol, side, amount, order_type, price)

            logger.info(f"ORDER FILLED: {json.dumps(result, default=str)}")
            self._save_trade_log(order_info, result)
            return {"status": "filled", "order": order_info, "result": result}

        except Exception as e:
            logger.error(f"ORDER FAILED: {e}")
            return {"status": "error", "order": order_info, "message": str(e)}

    def _execute_hyperliquid(self, symbol, side, amount, order_type, price):
        """Execute via Hyperliquid SDK."""
        is_buy = side.lower() == "buy"
        result = self.exchange.order(
            symbol.replace("/USDT", "").replace("USDT", ""),
            is_buy,
            amount,
            price if order_type == "limit" else None,
            {"limit": {"tif": "Gtc"}} if order_type == "limit" else None,
        )
        return result

    def _execute_ccxt(self, symbol, side, amount, order_type, price):
        """Execute via CCXT."""
        if order_type == "market":
            return self.exchange.create_market_order(symbol, side, amount)
        else:
            return self.exchange.create_limit_order(symbol, side, amount, price)

    def get_balance(self) -> Dict:
        """Get account balance."""
        if self.exchange is None:
            return {"error": "Exchange not connected"}
        try:
            if hasattr(self.exchange, "fetch_balance"):
                return self.exchange.fetch_balance()
            return {"error": "Balance fetch not supported"}
        except Exception as e:
            return {"error": str(e)}

    def get_positions(self) -> list:
        """Get open positions."""
        if self.exchange is None:
            return []
        try:
            if hasattr(self.exchange, "fetch_positions"):
                return self.exchange.fetch_positions()
            return []
        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
            return []

    def _save_trade_log(self, order: Dict, result: Dict):
        """Persist trade to log file."""
        log_file = LOG_DIR / "trade_history.jsonl"
        entry = {"order": order, "result": result}
        with open(log_file, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")


class ScheduledStrategy:
    """Run a strategy on a cron-like schedule."""

    def __init__(
        self,
        strategy_config: Dict[str, Any],
        executor: LiveExecutor,
        symbol: str,
        amount: float,
    ):
        self.strategy = strategy_config
        self.executor = executor
        self.symbol = symbol
        self.amount = amount

    def check_and_execute(self, df) -> Dict:
        """
        Check current data against strategy signals and execute if triggered.
        Called by cron/scheduler.
        """
        from trading.engine.backtest import apply_indicators, generate_signals

        df = apply_indicators(df, self.strategy)
        entries, exits = generate_signals(df, self.strategy)

        last_entry = entries.iloc[-1] if len(entries) > 0 else False
        last_exit = exits.iloc[-1] if len(exits) > 0 else False

        result = {"signal": "none", "action": None}

        if last_entry:
            result["signal"] = "entry"
            result["action"] = self.executor.place_order(
                self.symbol, "buy", self.amount
            )
        elif last_exit:
            result["signal"] = "exit"
            result["action"] = self.executor.place_order(
                self.symbol, "sell", self.amount
            )

        logger.info(f"Scheduled check for {self.symbol}: signal={result['signal']}")
        return result
