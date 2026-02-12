"""
Economic Calendar News Filter
------------------------------
FIX #3: Fetches forex economic calendar and determines if it's safe to trade.
High-impact events (NFP, FOMC, CPI) create unmodelable volatility.
This module provides a no-trade blackout zone around those events.

Inputs:  Current UTC timestamp, optional currency pair
Outputs: Next event info, minutes until event, impact level, trade-safe boolean
"""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from config import (
    NEWS_BLACKOUT_MINUTES, NEWS_CALENDAR_URL,
    NEWS_HIGH_IMPACT_ONLY, NEWS_CACHE_HOURS, DATA_DIR
)

CACHE_PATH = DATA_DIR / "news_cache.json"

# Fallback calendar: major recurring events (UTC times, approximate)
# Used when API is unavailable
RECURRING_EVENTS = [
    {"title": "US Non-Farm Payrolls", "impact": "high", "currency": "USD",
     "day_of_week": 4, "week_of_month": 0, "hour": 13, "minute": 30},
    {"title": "FOMC Rate Decision", "impact": "high", "currency": "USD",
     "recurrence": "6_weekly", "hour": 19, "minute": 0},
    {"title": "US CPI", "impact": "high", "currency": "USD",
     "day_of_week": 2, "week_of_month": 1, "hour": 13, "minute": 30},
    {"title": "ECB Rate Decision", "impact": "high", "currency": "EUR",
     "recurrence": "6_weekly", "hour": 13, "minute": 15},
    {"title": "UK CPI", "impact": "high", "currency": "GBP",
     "day_of_week": 2, "week_of_month": 2, "hour": 7, "minute": 0},
]


def _load_cache() -> Optional[list]:
    """Load cached calendar if still fresh."""
    if not os.path.exists(CACHE_PATH):
        return None
    try:
        with open(CACHE_PATH, "r") as f:
            data = json.load(f)
        cached_at = data.get("cached_at", 0)
        if time.time() - cached_at > NEWS_CACHE_HOURS * 3600:
            return None  # stale
        return data.get("events", [])
    except (json.JSONDecodeError, IOError):
        return None


def _save_cache(events: list):
    """Cache calendar to disk."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(str(CACHE_PATH), "w") as f:
        json.dump({"cached_at": time.time(), "events": events}, f)


def fetch_calendar() -> list:
    """
    Fetch economic calendar. Try API first, fallback to cache, then to hardcoded.
    Returns list of event dicts: [{title, datetime_utc, impact, currency}]
    """
    # Try cache first
    cached = _load_cache()
    if cached:
        return cached

    # Try API fetch
    events = _fetch_from_api()
    if events:
        _save_cache(events)
        return events

    # Fallback: generate from recurring events
    events = _generate_from_recurring()
    return events


def _fetch_from_api() -> Optional[list]:
    """Fetch from ForexFactory-style API. Non-blocking, tolerant of failure."""
    try:
        import urllib.request
        req = urllib.request.Request(
            NEWS_CALENDAR_URL,
            headers={"User-Agent": "TradingCommandCenter/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = json.loads(resp.read().decode())

        events = []
        for item in raw:
            impact = (item.get("impact") or "").lower()
            if NEWS_HIGH_IMPACT_ONLY and impact != "high":
                continue
            title = item.get("title", "Unknown Event")
            date_str = item.get("date", "")
            currency = item.get("country", "")
            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                events.append({
                    "title": title,
                    "datetime_utc": dt.strftime("%Y-%m-%dT%H:%M:%S"),
                    "impact": impact,
                    "currency": currency,
                })
            except (ValueError, AttributeError):
                continue
        return events if events else None
    except Exception:
        return None


def _generate_from_recurring() -> list:
    """Generate approximate event times from hardcoded recurring events."""
    now = datetime.utcnow()
    events = []

    for evt in RECURRING_EVENTS:
        # Find next occurrence this week or next week
        for day_offset in range(14):
            candidate = now.replace(
                hour=evt["hour"], minute=evt["minute"], second=0, microsecond=0
            ) + timedelta(days=day_offset)

            if candidate < now - timedelta(hours=1):
                continue

            if "day_of_week" in evt and candidate.weekday() != evt["day_of_week"]:
                continue

            events.append({
                "title": evt["title"],
                "datetime_utc": candidate.strftime("%Y-%m-%dT%H:%M:%S"),
                "impact": evt["impact"],
                "currency": evt["currency"],
                "source": "recurring_estimate",
            })
            break

    return events


def check_news_proximity(pair: str = "", now: Optional[datetime] = None) -> dict:
    """
    Check proximity to next high-impact news event.
    Returns: {safe_to_trade, minutes_to_event, next_event, impact}
    """
    if now is None:
        now = datetime.utcnow()

    events = fetch_calendar()
    if not events:
        return {
            "safe_to_trade": True,
            "minutes_to_event": None,
            "next_event": None,
            "impact": "none",
            "note": "No calendar data available",
        }

    # Filter by currency if pair provided
    relevant = events
    if pair:
        currencies = set()
        # Extract currencies from pair (e.g., "EURUSD" -> EUR, USD)
        if len(pair) >= 6:
            currencies.add(pair[:3].upper())
            currencies.add(pair[3:6].upper())
        if currencies:
            relevant = [e for e in events if e.get("currency", "").upper() in currencies]
            if not relevant:
                relevant = events  # fallback to all events if no match

    # Find nearest event
    nearest = None
    nearest_minutes = float("inf")

    for evt in relevant:
        try:
            evt_time = datetime.strptime(evt["datetime_utc"], "%Y-%m-%dT%H:%M:%S")
            delta_minutes = (evt_time - now).total_seconds() / 60
            if abs(delta_minutes) < abs(nearest_minutes):
                nearest_minutes = delta_minutes
                nearest = evt
        except (ValueError, KeyError):
            continue

    if nearest is None:
        return {
            "safe_to_trade": True,
            "minutes_to_event": None,
            "next_event": None,
            "impact": "none",
        }

    impact = nearest.get("impact", "low")
    is_blackout = impact == "high" and abs(nearest_minutes) <= NEWS_BLACKOUT_MINUTES
    is_caution = impact == "high" and abs(nearest_minutes) <= NEWS_BLACKOUT_MINUTES * 2

    return {
        "safe_to_trade": not is_blackout,
        "caution": is_caution,
        "minutes_to_event": round(nearest_minutes, 1),
        "next_event": nearest.get("title", "Unknown"),
        "event_time": nearest.get("datetime_utc", ""),
        "impact": impact,
        "currency": nearest.get("currency", ""),
    }


if __name__ == "__main__":
    result = check_news_proximity("EURUSD")
    print(f"Safe to trade: {result['safe_to_trade']}")
    if result["next_event"]:
        print(f"Next event: {result['next_event']} ({result['impact']})")
        print(f"Minutes away: {result['minutes_to_event']}")
