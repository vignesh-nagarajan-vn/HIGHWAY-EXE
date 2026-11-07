"""READER-B: a deterministic grammar reader, the second opinion next to the SLM.

It knows nothing about the 15 judged events: it segments the message (digests, numbered items),
spots incident cues, picks up entities with the resolver's lexicon and date phrases with the
date grammar, and emits the same EventReading schema as the LLM readers.
"""
from __future__ import annotations

import re
import time

from ..ground.dates import find_mentions
from ..ground.resolver import scan
from .schemas import EventReading, IncidentReading

HEDGES = [r"\brumou?rs?\b", r"\bunconfirmed\b", r"\bnot confirmed\b", r"\bnothing confirmed\b",
          r"\bno details\b", r"\bmay be\b", r"\bmight\b", r"\bpossibl[ey]\b", r"\bsomeone\b.*\bmentioned\b",
          r"\bheard\b", r"\bsometime soon\b", r"\bcan'?t confirm\b", r"\bunverified\b", r"\bnot sure\b"]
CUES = {
    "quality_hold": [r"\bquality\b", r"\bdefect", r"\bfaulty\b", r"\bcontaminat", r"\bsuspect\b", r"\brecall\b",
                     r"\bon hold\b", r"\bnon-?conform"],
    "plant_outage": [r"\boutage\b", r"\bdark\b", r"\bpower failure\b", r"\blost production\b",
                     r"\bproduction is stopped\b", r"\bshut ?down\b", r"\bno builds\b", r"\bcannot build\b",
                     r"\bline (?:is )?down\b", r"\bfire\b", r"\bflood"],
    "supplier_delay": [r"\bdelay", r"\blate\b", r"\bcan'?t make it\b", r"\bcannot make it\b", r"\bnew eta\b",
                       r"\bwill now arrive\b", r"\bwaiting on\b", r"\bslips?\b", r"\bpushed\b",
                       r"\bnow arrive", r"\bcarrier says\b", r"\bwas due\b"],
}
NEW_DATE_CUE = re.compile(r"(now|new eta|will (?:now )?arrive|pushed to|slips? to)\W+(?:\w+\W+){0,3}$", re.I)
SEGMENT_SPLIT = re.compile(r"(?:^|\s)\(?\d{1,2}\)\s+|\n\s*[-*•]\s+")


def _has(patterns, text) -> bool:
    return any(re.search(p, text, re.I) for p in patterns)


def segments(text: str) -> list[str]:
    parts = [p.strip() for p in SEGMENT_SPLIT.split(text) if p and p.strip()]
    return parts or [text]


def _kind(seg: str) -> str | None:
    if _has(CUES["quality_hold"], seg) and re.search(r"\b(built|lot|vehicles?)\b", seg, re.I):
        return "quality_hold"
    if _has(CUES["plant_outage"], seg):
        return "plant_outage"
    if _has(CUES["supplier_delay"], seg):
        return "supplier_delay"
    return None


def _first(cands) -> str | None:
    ids = sorted({c.entity_id for c in cands})
    return ids[0] if len(ids) == 1 else None


def _incident(kind: str, seg: str) -> IncidentReading:
    ents = scan(seg)
    dates = find_mentions(seg)
    d_from = d_to = None
    if len(dates) >= 2:
        d_from, d_to = dates[0].text, dates[1].text
    elif len(dates) == 1:
        before = seg[:dates[0].start]
        if kind == "supplier_delay" and NEW_DATE_CUE.search(before):
            d_to = dates[0].text
        elif kind == "plant_outage":
            d_from = d_to = dates[0].text
        else:
            d_from = dates[0].text
    return IncidentReading(
        kind=kind,
        supplier=_first(ents["supplier"]),
        part=_first(ents["part"]),
        plant=_first(ents["plant"]),
        shipment_id=_first(ents["shipment"]),
        lot_id=_first(ents["lot"]),
        date_from=d_from,
        date_to=d_to,
        evidence=seg,
    )


def read(event: dict) -> EventReading:
    t0 = time.perf_counter()
    text = event["text"]
    hedged = _has(HEDGES, text)
    incidents = [_incident(k, s) for s in segments(text) if (k := _kind(s))]
    if hedged:
        cat, why = "unconfirmed", "hedging language (rumor / may / not confirmed)"
        incidents = []
    elif incidents:
        cat, why = "operational", f"{len(incidents)} incident cue(s): " + ", ".join(i.kind for i in incidents)
    else:
        cat, why = "noise", "no supply, outage or quality cue"
    return EventReading(category=cat, incidents=incidents, rationale=why, reader="grammar",
                        model="rules", latency_ms=int((time.perf_counter() - t0) * 1000))
