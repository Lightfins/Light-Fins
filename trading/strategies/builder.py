"""
Strategy builder — creates, edits, and generates variants of trading strategies.
Strategies are JSON configs that the backtest engine consumes.
"""

import json
import copy
import itertools
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


STRATEGIES_DIR = Path("trading/workspace/strategies")


def create_strategy(
    name: str,
    timeframe: str,
    indicators: List[Dict],
    entry_rules: List[Dict],
    exit_rules: List[Dict],
    direction: str = "long",
    description: str = "",
) -> Dict[str, Any]:
    """Create a strategy config dict."""
    strategy = {
        "name": name,
        "timeframe": timeframe,
        "direction": direction,
        "description": description,
        "indicators": indicators,
        "rules": {
            "entry": entry_rules,
            "exit": exit_rules,
        },
        "created_at": datetime.datetime.now().isoformat(),
        "version": 1,
    }
    return strategy


def save_strategy(strategy: Dict[str, Any], directory: str = None) -> str:
    """Save a strategy config to disk."""
    save_dir = Path(directory) if directory else STRATEGIES_DIR
    save_dir.mkdir(parents=True, exist_ok=True)

    name = strategy.get("name", "unnamed")
    filepath = save_dir / f"{name}.json"
    with open(filepath, "w") as f:
        json.dump(strategy, f, indent=2)
    return str(filepath)


def load_strategy(filepath: str) -> Dict[str, Any]:
    """Load a strategy config from disk."""
    with open(filepath) as f:
        return json.load(f)


def generate_variants(
    base_strategy: Dict[str, Any],
    param_grid: Dict[str, List],
    max_variants: int = 20,
) -> List[Dict[str, Any]]:
    """
    Generate strategy variants by sweeping indicator parameters.

    param_grid format:
    {
        "rsi_length": [10, 14, 21],
        "ema_length": [9, 20, 50],
        "rsi_overbought": [70, 75, 80],
    }

    Maps param names to indicator params via naming convention:
    - "{indicator_name}_{param_name}" e.g. "rsi_length", "ema_length"
    """
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    combos = list(itertools.product(*values))

    if len(combos) > max_variants:
        # Sample evenly from the grid
        step = len(combos) // max_variants
        combos = combos[::step][:max_variants]

    variants = []
    for i, combo in enumerate(combos):
        variant = copy.deepcopy(base_strategy)
        param_set = dict(zip(keys, combo))

        # Apply params to matching indicators
        for indicator in variant["indicators"]:
            ind_name = indicator["name"].lower()
            for param_key, param_val in param_set.items():
                parts = param_key.split("_", 1)
                if len(parts) == 2 and parts[0].lower() == ind_name:
                    indicator.setdefault("params", {})[parts[1]] = param_val

        # Apply params to rules (for threshold values)
        for rule_type in ["entry", "exit"]:
            for rule in variant["rules"].get(rule_type, []):
                for param_key, param_val in param_set.items():
                    if rule.get("right") == f"${{{param_key}}}":
                        rule["right"] = param_val
                    if rule.get("left") == f"${{{param_key}}}":
                        rule["left"] = param_val

        variant["name"] = f"{base_strategy['name']}_v{i+1}"
        variant["params"] = param_set
        variants.append(variant)

    return variants


# Pre-built strategy templates

def template_rsi_ema(
    rsi_length: int = 14,
    ema_fast: int = 9,
    ema_slow: int = 21,
    rsi_oversold: int = 30,
    rsi_overbought: int = 70,
    timeframe: str = "4h",
) -> Dict[str, Any]:
    """RSI + EMA crossover strategy template."""
    return create_strategy(
        name=f"rsi_ema_{timeframe}",
        timeframe=timeframe,
        indicators=[
            {"name": "RSI", "params": {"length": rsi_length}},
            {"name": "EMA", "params": {"length": ema_fast}},
            {"name": "EMA", "params": {"length": ema_slow}},
        ],
        entry_rules=[
            {"left": f"ema_{ema_fast}", "operator": "crosses_above", "right": f"ema_{ema_slow}"},
            {"left": f"rsi_{rsi_length}", "operator": "less_than", "right": rsi_overbought},
        ],
        exit_rules=[
            {"left": f"ema_{ema_fast}", "operator": "crosses_below", "right": f"ema_{ema_slow}"},
        ],
        description=f"RSI({rsi_length}) filter + EMA({ema_fast}/{ema_slow}) crossover on {timeframe}",
    )


def template_macd_bb(
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    bb_length: int = 20,
    bb_std: float = 2.0,
    timeframe: str = "4h",
) -> Dict[str, Any]:
    """MACD + Bollinger Bands strategy template."""
    return create_strategy(
        name=f"macd_bb_{timeframe}",
        timeframe=timeframe,
        indicators=[
            {"name": "MACD", "params": {"fast": macd_fast, "slow": macd_slow, "signal": macd_signal}},
            {"name": "BBANDS", "params": {"length": bb_length, "std": bb_std}},
        ],
        entry_rules=[
            {"left": "MACDh_12_26_9", "operator": "crosses_above", "right": 0},
            {"left": "close", "operator": "less_than", "right": f"BBU_{bb_length}_{bb_std}"},
        ],
        exit_rules=[
            {"left": "MACDh_12_26_9", "operator": "crosses_below", "right": 0},
        ],
        description=f"MACD({macd_fast}/{macd_slow}/{macd_signal}) + BBands({bb_length}, {bb_std}) on {timeframe}",
    )


def template_supertrend_adx(
    st_length: int = 10,
    st_multiplier: float = 3.0,
    adx_length: int = 14,
    adx_threshold: int = 25,
    timeframe: str = "4h",
) -> Dict[str, Any]:
    """Supertrend + ADX filter strategy template."""
    return create_strategy(
        name=f"supertrend_adx_{timeframe}",
        timeframe=timeframe,
        indicators=[
            {"name": "SUPERTREND", "params": {"length": st_length, "multiplier": st_multiplier}},
            {"name": "ADX", "params": {"length": adx_length}},
        ],
        entry_rules=[
            {"left": f"SUPERTd_{st_length}_{st_multiplier}", "operator": "equals", "right": 1},
            {"left": f"ADX_{adx_length}", "operator": "greater_than", "right": adx_threshold},
        ],
        exit_rules=[
            {"left": f"SUPERTd_{st_length}_{st_multiplier}", "operator": "equals", "right": -1},
        ],
        description=f"Supertrend({st_length}, {st_multiplier}) + ADX({adx_length}) > {adx_threshold} on {timeframe}",
    )
