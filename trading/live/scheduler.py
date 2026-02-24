"""
Strategy scheduler — runs strategies at defined intervals.
Uses APScheduler (lightweight, no external deps beyond pip).
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("scheduler")

SCHEDULE_FILE = Path("trading/workspace/schedules.json")


def load_schedules() -> list:
    """Load saved schedules from disk."""
    if SCHEDULE_FILE.exists():
        with open(SCHEDULE_FILE) as f:
            return json.load(f)
    return []


def save_schedule(schedule: Dict[str, Any]):
    """Add a schedule to the saved list."""
    schedules = load_schedules()
    schedules.append(schedule)
    SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(schedules, f, indent=2)


def remove_schedule(strategy_name: str):
    """Remove a schedule by strategy name."""
    schedules = load_schedules()
    schedules = [s for s in schedules if s.get("strategy_name") != strategy_name]
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(schedules, f, indent=2)


def create_cron_entry(
    strategy_name: str,
    strategy_file: str,
    symbol: str,
    exchange: str,
    interval_hours: int = 4,
    amount: float = 0.01,
    testnet: bool = True,
) -> Dict[str, Any]:
    """
    Create a schedule entry.
    This generates a crontab-compatible entry or systemd timer config.
    """
    schedule = {
        "strategy_name": strategy_name,
        "strategy_file": strategy_file,
        "symbol": symbol,
        "exchange": exchange,
        "interval_hours": interval_hours,
        "amount": amount,
        "testnet": testnet,
        "cron_expression": f"0 */{interval_hours} * * *",
    }
    save_schedule(schedule)
    return schedule


def generate_crontab_line(schedule: Dict) -> str:
    """Generate a crontab line for a scheduled strategy."""
    cron = schedule.get("cron_expression", "0 */4 * * *")
    strategy_file = schedule["strategy_file"]
    symbol = schedule["symbol"]
    exchange = schedule["exchange"]
    amount = schedule["amount"]
    testnet_flag = "--testnet" if schedule.get("testnet", True) else ""

    working_dir = os.getcwd()
    cmd = (
        f"{cron} cd {working_dir} && "
        f"python -m trading.live.run_scheduled "
        f"--strategy {strategy_file} "
        f"--symbol {symbol} "
        f"--exchange {exchange} "
        f"--amount {amount} "
        f"{testnet_flag} "
        f">> trading/logs/cron.log 2>&1"
    )
    return cmd


def generate_systemd_timer(schedule: Dict) -> str:
    """Generate a systemd timer unit for a scheduled strategy."""
    name = schedule["strategy_name"]
    hours = schedule.get("interval_hours", 4)

    service = f"""[Unit]
Description=TradingClaw strategy: {name}

[Service]
Type=oneshot
WorkingDirectory={os.getcwd()}
ExecStart=/usr/bin/python -m trading.live.run_scheduled \\
    --strategy {schedule['strategy_file']} \\
    --symbol {schedule['symbol']} \\
    --exchange {schedule['exchange']} \\
    --amount {schedule['amount']} \\
    {'--testnet' if schedule.get('testnet', True) else ''}
Environment=PATH=/usr/local/bin:/usr/bin

[Install]
WantedBy=multi-user.target
"""

    timer = f"""[Unit]
Description=Run {name} every {hours}h

[Timer]
OnCalendar=*-*-* 00/{hours}:00:00
Persistent=true

[Install]
WantedBy=timers.target
"""
    return f"# {name}.service\n{service}\n# {name}.timer\n{timer}"
