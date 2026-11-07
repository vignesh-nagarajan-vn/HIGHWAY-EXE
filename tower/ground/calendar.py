"""Working-day calendar (Monday-Friday) anchored on the handbook's 'today' (day index 0)."""
from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache

from ..data import world


@lru_cache(maxsize=1)
def _cal() -> tuple[date, int, int]:
    rows = world().calendar
    today = next(date.fromisoformat(r["date"]) for r in rows if int(r["day_index"]) == 0)
    idx = [int(r["day_index"]) for r in rows]
    return today, min(idx), max(idx)


def today() -> date:
    return _cal()[0]


def last_index() -> int:
    return _cal()[2]


def is_workday(d: date) -> bool:
    return d.weekday() < 5


def idx_of(d: date) -> int:
    """Working-day index relative to today (weekdays only)."""
    days = (d - today()).days
    if days % 7 > 4:
        raise ValueError(f"{d} is a weekend")
    return 5 * (days // 7) + days % 7


def date_of(i: int) -> date:
    return today() + timedelta(days=7 * (i // 5) + i % 5)


def next_workday(d: date) -> date:
    d = d + timedelta(days=1)
    while not is_workday(d):
        d += timedelta(days=1)
    return d


def in_planning_window(d: date) -> bool:
    return is_workday(d) and 0 <= idx_of(d) <= last_index()


def window_end() -> date:
    return date_of(last_index())


def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())
