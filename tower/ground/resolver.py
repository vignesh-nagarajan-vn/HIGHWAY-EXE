"""Resolve human names ("the Texas plant", "Volt", "360 cameras", "CAM-360") to entity ids.

Order of evidence: explicit ids > aliases.csv / table names (exact) > containment > fuzzy.
Ties are returned as several candidates; the judge treats them as ambiguous.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from rapidfuzz import fuzz

from ..data import world

STATE_NAMES = {"TX": "texas", "KY": "kentucky", "MS": "mississippi", "IN": "indiana",
               "AL": "alabama", "NC": "north carolina"}
ID_PATTERNS = {
    "plant": re.compile(r"\bP_[A-Z]{2}\b"),
    "supplier": re.compile(r"\bSUP-\d{2}\b"),
    "shipment": re.compile(r"\bSH-\d{4}\b"),
    "lot": re.compile(r"\bLOT-\d{4}\b"),
}


@dataclass(frozen=True)
class Candidate:
    entity_id: str
    score: float
    how: str           # id | alias | name | contains | fuzzy
    term: str = ""


def norm(s: str) -> str:
    s = s.lower().replace("’", "'").replace("_", " ")
    s = re.sub(r"[^a-z0-9\- ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


@lru_cache(maxsize=1)
def lexicon() -> dict[str, list[tuple[str, str, str]]]:
    """cls -> [(normalised term, entity_id, source)] longest first."""
    w = world()
    lex: dict[str, set[tuple[str, str, str]]] = {"plant": set(), "part": set(), "supplier": set()}
    for r in w.aliases:
        lex[r["entity_type"]].add((norm(r["alias"]), r["entity_id"], "alias"))
    for pid, r in w.plants.items():
        city = r["city"].split(",")[0]
        state = r["city"].split(",")[-1].strip()
        lex["plant"] |= {(norm(r["name"]), pid, "name"), (norm(city), pid, "name"),
                         (norm(f"{city} plant"), pid, "name"),
                         (norm(STATE_NAMES.get(state, state)), pid, "name"),
                         (norm(f"{STATE_NAMES.get(state, state)} plant"), pid, "name")}
    for pid, r in w.parts.items():
        lex["part"] |= {(norm(r["name"]), pid, "name"), (norm(pid), pid, "id")}
    for sid, r in w.suppliers.items():
        lex["supplier"] |= {(norm(r["name"]), sid, "name"), (norm(r["name"].split()[0]), sid, "name")}
    return {k: sorted(v, key=lambda t: -len(t[0])) for k, v in lex.items()}


def _term_re(term: str) -> re.Pattern:
    tail = "" if term.endswith("s") else "(?:e?s)?"
    return re.compile(rf"(?<![a-z0-9]){re.escape(term)}{tail}(?![a-z0-9])")


@lru_cache(maxsize=4096)
def _compiled(term: str) -> re.Pattern:
    return _term_re(term)


def resolve(mention: str | None, cls: str) -> list[Candidate]:
    """Candidates for one mention, best first. Empty list = unknown."""
    if not mention or not mention.strip():
        return []
    raw = mention.strip()
    if cls in ID_PATTERNS and (m := ID_PATTERNS[cls].search(raw.upper())):
        return [Candidate(m.group(0), 1.0, "id", raw)]
    n = norm(raw)
    lex = lexicon().get(cls, [])
    exact = {(eid, src) for term, eid, src in lex if term == n or term == n.rstrip("s")}
    if exact:
        return _dedupe([Candidate(e, 0.99, s, raw) for e, s in exact])
    contains = [(term, eid) for term, eid, _ in lex if _compiled(term).search(n)]
    if contains:
        best = len(contains[0][0])
        top = {eid for term, eid in contains if len(term) == best}
        return _dedupe([Candidate(e, 0.9, "contains", raw) for e in top])
    scored = sorted(((fuzz.token_set_ratio(n, term), eid) for term, eid, _ in lex), reverse=True)
    if scored and scored[0][0] >= 85:
        top = {eid for s, eid in scored if s >= scored[0][0] - 2}
        return _dedupe([Candidate(e, scored[0][0] / 100, "fuzzy", raw) for e in top])
    return []


def _dedupe(cands: list[Candidate]) -> list[Candidate]:
    seen, out = set(), []
    for c in sorted(cands, key=lambda c: (-c.score, c.entity_id)):
        if c.entity_id not in seen:
            seen.add(c.entity_id)
            out.append(c)
    return out


def scan(text: str) -> dict[str, list[Candidate]]:
    """Find every entity mentioned anywhere in a free-text message (longest term wins)."""
    found: dict[str, list[Candidate]] = {"plant": [], "part": [], "supplier": [], "shipment": [], "lot": []}
    for cls in ("plant", "supplier", "shipment", "lot"):
        for m in ID_PATTERNS[cls].finditer(text):
            found[cls].append(Candidate(m.group(0), 1.0, "id", m.group(0)))
    n = norm(text)
    taken: list[tuple[int, int]] = []
    all_terms = sorted(((t, e, s, c) for c, lst in lexicon().items() for t, e, s in lst), key=lambda x: -len(x[0]))
    for term, eid, src, cls in all_terms:
        for m in _compiled(term).finditer(n):
            a, b = m.span()
            if any(not (b <= x or a >= y) for x, y in taken):
                continue
            taken.append((a, b))
            found[cls].append(Candidate(eid, 0.95, src, term))
    for cls in found:
        found[cls] = _dedupe(found[cls])
    return found


def unique(cands: list[Candidate]) -> str | None:
    return cands[0].entity_id if len(cands) == 1 else None
