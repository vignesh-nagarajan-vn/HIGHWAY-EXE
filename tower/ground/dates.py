"""Deterministic date grammar.

Readers copy date phrases verbatim ("next Friday", "Thursday Feb 25", "2027-03-15"); this
module turns each phrase into one or more candidate dates. Ambiguous phrases return several
candidates (primary reading first) and the graph judge keeps the one the data supports.

Convention (validated against the data, see tests): relative to Monday 2027-03-08,
"next <weekday>" is that weekday in the following calendar week and "last <weekday>" is
that weekday in the previous calendar week.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

from . import calendar as cal

WEEKDAYS = {
    "monday": 0, "mon": 0, "tuesday": 1, "tue": 1, "tues": 1, "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thur": 3, "thurs": 3, "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5, "sunday": 6, "sun": 6,
}
MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3, "april": 4, "apr": 4,
    "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7, "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9, "october": 10, "oct": 10, "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}
_WD = r"(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tues?|wed|thu(?:rs?)?|fri|sat|sun)"
# "may" is excluded as a bare month word to avoid matching the verb; "May 3" still needs a day number.
_MON = r"(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sept?|oct|nov|dec)"

ISO_RE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
MONTH_DAY_RE = re.compile(
    rf"\b(?:(?P<wd>{_WD})\.?,?\s+)?(?P<mon>{_MON})\.?\s+(?P<day>\d{{1,2}})(?:st|nd|rd|th)?\b(?:,?\s+(?P<year>20\d{{2}}))?",
    re.I)
SLASH_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})(?:/(20\d{2}))?\b")
REL_WD_RE = re.compile(rf"\b(?:(?P<mod>next|last|this|coming|past|previous)\s+)?(?P<wd>{_WD})\b\.?", re.I)
WORD_RE = re.compile(r"\b(today|tomorrow|yesterday)\b", re.I)


@dataclass(frozen=True)
class DateCandidate:
    value: date
    rule: str          # human-readable rule that produced it
    primary: bool = True


@dataclass(frozen=True)
class DateMention:
    text: str
    start: int
    end: int


def find_mentions(text: str) -> list[DateMention]:
    """All date phrases in order of appearance, longest match wins, no overlaps."""
    spans: list[tuple[int, int]] = []
    found: list[DateMention] = []

    def add(m):
        s, e = m.span()
        if any(not (e <= a or s >= b) for a, b in spans):
            return
        spans.append((s, e))
        found.append(DateMention(m.group(0).strip().rstrip(","), s, e))

    for rx in (ISO_RE, MONTH_DAY_RE, SLASH_RE, REL_WD_RE, WORD_RE):
        for m in rx.finditer(text):
            if rx is MONTH_DAY_RE and m.group("mon").lower() == "may" and not m.group("day"):
                continue
            add(m)
    return sorted(found, key=lambda d: d.start)


def resolve(expr: str, today: date | None = None) -> list[DateCandidate]:
    """Candidate dates for one phrase, primary reading first. Empty if not a date."""
    t = today or cal.today()
    s = expr.strip().lower().rstrip(".,")
    if not s:
        return []
    if m := ISO_RE.search(s):
        return [DateCandidate(date(int(m[1]), int(m[2]), int(m[3])), "ISO date")]
    if m := MONTH_DAY_RE.search(s):
        year = int(m.group("year")) if m.group("year") else t.year
        try:
            d = date(year, MONTHS[m.group("mon").lower().rstrip(".")], int(m.group("day")))
        except ValueError:
            return []
        rule = "calendar date"
        if m.group("wd") and WEEKDAYS[m.group("wd").lower()] != d.weekday():
            rule += " (weekday in text disagrees)"
        return [DateCandidate(d, rule)]
    if m := SLASH_RE.search(s):
        year = int(m[3]) if m[3] else t.year
        try:
            return [DateCandidate(date(year, int(m[1]), int(m[2])), "M/D date")]
        except ValueError:
            return []
    if m := WORD_RE.search(s):
        w = m[1].lower()
        delta = {"today": 0, "tomorrow": 1, "yesterday": -1}[w]
        return [DateCandidate(t + timedelta(days=delta), w)]
    if m := REL_WD_RE.search(s):
        wd = WEEKDAYS[m.group("wd").lower()]
        mod = (m.group("mod") or "").lower()
        this_week = cal.monday_of(t) + timedelta(days=wd)
        upcoming = t + timedelta(days=(wd - t.weekday()) % 7 or 7)
        recent = t - timedelta(days=(t.weekday() - wd) % 7 or 7)
        if mod == "next":
            out = [DateCandidate(this_week + timedelta(days=7), "next = weekday of the following week"),
                   DateCandidate(upcoming, "next = the upcoming weekday", primary=False)]
        elif mod in ("last", "past", "previous"):
            out = [DateCandidate(this_week - timedelta(days=7), "last = weekday of the previous week"),
                   DateCandidate(recent, "last = the most recent weekday", primary=False)]
        elif mod in ("this", "coming"):
            first = this_week if this_week >= t else upcoming
            out = [DateCandidate(first, f"{mod} = weekday of the current week"),
                   DateCandidate(upcoming, f"{mod} = the upcoming weekday", primary=False)]
        else:
            out = [DateCandidate(upcoming, "bare weekday = upcoming"),
                   DateCandidate(recent, "bare weekday = most recent", primary=False)]
        seen, uniq = set(), []
        for c in out:
            if c.value not in seen:
                seen.add(c.value)
                uniq.append(c)
        return uniq
    return []


def resolve_one(expr: str) -> date | None:
    c = resolve(expr)
    return c[0].value if c else None
