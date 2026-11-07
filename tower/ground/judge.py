"""GRAPH JUDGE: turns verbatim readings into grounded incidents, using the knowledge graph as
the referee.

For every incident it enumerates candidate entities and candidate dates and keeps only the
combinations the data supports (a shipment with that ETA exists, the new ETA is later, a lot
with that build window exists, dates are working days...). If exactly one best combination
survives, the incident is actionable; otherwise it is unresolved and lists the missing intel.
It then compares the readers: identical grounded results = agreement.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from itertools import product

from ..data import world
from ..intake.schemas import EventReading, IncidentReading
from . import calendar as cal
from .dates import DateCandidate, resolve as resolve_date
from .resolver import resolve as resolve_entity


@dataclass
class ResolvedIncident:
    kind: str
    actionable: bool
    plant: str | None = None
    part: str | None = None
    supplier: str | None = None
    shipment_id: str | None = None
    lot_ids: list[str] = field(default_factory=list)
    start: str | None = None        # delay: original ETA | outage: first dark day | quality: first build day
    end: str | None = None          # delay: new ETA      | outage: last dark day  | quality: last build day
    resume_on: str | None = None    # first day the plant can build again (delay/outage)
    support: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    evidence: str = ""

    def key(self) -> tuple:
        return (self.kind, self.plant, self.shipment_id, tuple(self.lot_ids), self.start, self.end)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Verdict:
    category: str                       # operational | noise | unconfirmed
    incidents: list[ResolvedIncident]   # actionable, in plan order
    unresolved: list[ResolvedIncident]
    agreement: str                      # unanimous | majority | split | single
    readers: list[str]
    reason: str
    missing_intel: list[str] = field(default_factory=list)
    per_reader: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


def _ids(mention: str | None, cls: str) -> list[str]:
    return [c.entity_id for c in resolve_entity(mention, cls)] if mention else []


def _dates(expr: str | None, memo: dict[str, date]) -> list[DateCandidate]:
    if not expr:
        return []
    key = expr.strip().lower()
    if key in memo:   # phrase already pinned by the graph elsewhere in this message
        return [DateCandidate(memo[key], "same phrase grounded elsewhere in this message")]
    return resolve_date(expr)


def _pick(combos: list[tuple[int, tuple]]) -> tuple | None:
    """Unique best combination by primacy score, else None (ambiguous)."""
    if not combos:
        return None
    best = max(s for s, _ in combos)
    top = {c for s, c in combos if s == best}
    return next(iter(top)) if len(top) == 1 else None


def judge_delay(r: IncidentReading, memo: dict) -> ResolvedIncident:
    w = world()
    out = ResolvedIncident("supplier_delay", False, evidence=r.evidence)
    plants, parts, sups = _ids(r.plant, "plant"), _ids(r.part, "part"), _ids(r.supplier, "supplier")
    shipments = list(w.shipments.values())
    if r.shipment_id:
        sid = _ids(r.shipment_id, "shipment")
        shipments = [w.shipments[s] for s in sid if s in w.shipments]
        if not shipments:
            out.missing.append(f"shipment {r.shipment_id} is not in the inbound schedule")
            return out
    if r.part and not parts:
        out.missing.append(f"part '{r.part}' does not match any part")
    if r.plant and not plants:
        out.missing.append(f"plant '{r.plant}' does not match any plant")
    origs, news = _dates(r.date_from, memo), _dates(r.date_to, memo)
    if not origs:
        out.missing.append("original arrival date")
    if not news:
        out.missing.append("new arrival date")
    if not (r.shipment_id or (parts and plants)):
        out.missing.append("which part and which plant")
    if out.missing:
        return out
    combos = []
    for sh in shipments:
        if parts and sh["part_id"] not in parts:
            continue
        if plants and sh["plant_id"] not in plants:
            continue
        if sups and sh["supplier_id"] not in sups:
            continue
        for o, n in product(origs, news):
            if o.value.isoformat() != sh["eta_date"] or n.value <= o.value or not cal.is_workday(n.value):
                continue
            combos.append((int(o.primary) + int(n.primary), (sh["shipment_id"], o, n)))
    pick = _pick(combos)
    if pick is None:
        if not combos:
            out.missing.append("no inbound shipment matches that supplier, part, plant and original date")
            if sups and parts and plants:
                real = {s["supplier_id"] for s in w.shipments.values() if s["part_id"] in parts and s["plant_id"] in plants}
                if real and not set(sups) & real:
                    out.missing.append(f"supplier named does not ship that part to that plant (actual: {sorted(real)})")
        else:
            out.missing.append("several shipments or dates fit the message")
        return out
    sid, o, n = pick
    sh = w.shipments[sid]
    out.actionable = True
    out.plant, out.part, out.supplier, out.shipment_id = sh["plant_id"], sh["part_id"], sh["supplier_id"], sid
    out.start, out.end, out.resume_on = sh["eta_date"], n.value.isoformat(), n.value.isoformat()
    out.support = [f"shipment {sid}: {sh['supplier_id']} -> {sh['part_id']} -> {sh['plant_id']}, ETA {sh['eta_date']}",
                   f"'{r.date_from}' = {o.value} ({o.rule}) matches the shipment ETA",
                   f"'{r.date_to}' = {n.value} ({n.rule}) is later than the original ETA"]
    memo[(r.date_from or "").strip().lower()] = o.value
    memo[(r.date_to or "").strip().lower()] = n.value
    return out


def judge_outage(r: IncidentReading, memo: dict) -> ResolvedIncident:
    out = ResolvedIncident("plant_outage", False, evidence=r.evidence)
    plants = sorted(set(_ids(r.plant, "plant")))
    if len(plants) != 1:
        out.missing.append("which plant" if not plants else f"plant is ambiguous: {plants}")
    starts, ends = _dates(r.date_from, memo), _dates(r.date_to or r.date_from, memo)
    if not starts:
        out.missing.append("first day of the outage")
    if not ends:
        out.missing.append("last day of the outage")
    if out.missing:
        return out
    combos = []
    for s, e in product(starts, ends):
        if s.value > e.value or (e.value - s.value).days > 31:
            continue
        if e.value < cal.today():
            continue
        combos.append((int(s.primary) + int(e.primary), (s, e)))
    pick = _pick(combos)
    if pick is None:
        out.missing.append("the outage dates do not form a single valid range")
        return out
    s, e = pick
    out.actionable = True
    out.plant, out.start, out.end = plants[0], s.value.isoformat(), e.value.isoformat()
    out.resume_on = cal.next_workday(e.value).isoformat()
    out.support = [f"plant {plants[0]} from '{r.plant}'",
                   f"'{r.date_from}' = {s.value} ({s.rule})", f"'{r.date_to}' = {e.value} ({e.rule})",
                   f"restart on the next working day {out.resume_on}"]
    return out


def judge_quality(r: IncidentReading, memo: dict) -> ResolvedIncident:
    w = world()
    out = ResolvedIncident("quality_hold", False, evidence=r.evidence)
    plants, parts, sups = _ids(r.plant, "plant"), _ids(r.part, "part"), _ids(r.supplier, "supplier")
    starts, ends = _dates(r.date_from, memo), _dates(r.date_to or r.date_from, memo)
    if r.lot_id:
        lot_ids = _ids(r.lot_id, "lot")
        if not lot_ids or lot_ids[0] not in w.lots:
            out.missing.append(f"lot {r.lot_id} is not in the lot register")
            return out
        lot = w.lots[lot_ids[0]]
        conflicts = []
        if parts and lot["part_id"] not in parts:
            conflicts.append("part")
        if plants and lot["plant_id"] not in plants:
            conflicts.append("plant")
        if sups and lot["supplier_id"] not in sups:
            conflicts.append("supplier")
        if starts and lot["first_build_date"] not in {c.value.isoformat() for c in starts}:
            conflicts.append("first build date")
        if ends and lot["last_build_date"] not in {c.value.isoformat() for c in ends}:
            conflicts.append("last build date")
        if conflicts:
            out.missing.append(f"lot {lot['lot_id']} contradicts the message on: {', '.join(conflicts)}")
            return out
        chosen = [lot]
        out.support = [f"lot {lot['lot_id']} named explicitly; part, plant, supplier and window agree"]
    else:
        if not (parts and plants):
            out.missing.append("which part and which plant")
        if not starts or not ends:
            out.missing.append("the suspect build window")
        if out.missing:
            return out
        pool = [l for l in w.lots.values() if l["part_id"] in parts and l["plant_id"] in plants
                and (not sups or l["supplier_id"] in sups)]
        combos = []
        for s, e in product(starts, ends):
            lo, hi = s.value.isoformat(), e.value.isoformat()
            covered = sorted((l for l in pool if lo <= l["first_build_date"] and l["last_build_date"] <= hi),
                             key=lambda l: l["first_build_date"])
            # the stated window must be exactly the union of whole lots
            if covered and covered[0]["first_build_date"] == lo and covered[-1]["last_build_date"] == hi:
                combos.append((int(s.primary) + int(e.primary), tuple(l["lot_id"] for l in covered)))
        pick = _pick(combos)
        if pick is None:
            out.missing.append("no lot (or set of whole lots) matches that build window" if not combos
                               else "several lots fit the message")
            return out
        chosen = [w.lots[l] for l in pick]
        out.support = [f"lot {l['lot_id']}: {l['supplier_id']} {l['part_id']} at {l['plant_id']}, "
                       f"built {l['first_build_date']}..{l['last_build_date']} = stated window" for l in chosen]
        memo[(r.date_from or "").strip().lower()] = date.fromisoformat(chosen[0]["first_build_date"])
        memo[(r.date_to or "").strip().lower()] = date.fromisoformat(chosen[-1]["last_build_date"])
    out.actionable = True
    out.lot_ids = [l["lot_id"] for l in chosen]
    out.plant, out.part, out.supplier = chosen[0]["plant_id"], chosen[0]["part_id"], chosen[0]["supplier_id"]
    out.start, out.end = chosen[0]["first_build_date"], chosen[-1]["last_build_date"]
    return out


JUDGES = {"supplier_delay": judge_delay, "plant_outage": judge_outage, "quality_hold": judge_quality}


def ground_reading(reading: EventReading) -> tuple[str, list[ResolvedIncident]]:
    """Ground one reader's output. Graph-anchored kinds go first so their dates can pin the
    same phrases inside the rest of the message (e.g. 'next Friday' in a digest)."""
    if reading.category != "operational" or not reading.incidents:
        return reading.category if reading.category != "operational" else "noise", []
    memo: dict[str, date] = {}
    order = sorted(range(len(reading.incidents)),
                   key=lambda i: reading.incidents[i].kind == "plant_outage")
    resolved: dict[int, ResolvedIncident] = {}
    for i in order:
        inc = reading.incidents[i]
        resolved[i] = JUDGES[inc.kind](inc, memo)
    return "operational", [resolved[i] for i in range(len(reading.incidents))]


def signature(category: str, incs: list[ResolvedIncident]) -> tuple:
    return (category, tuple(sorted(i.key() for i in incs if i.actionable)),
            sum(not i.actionable for i in incs))


def judge(readings: list[EventReading]) -> tuple[Verdict | None, dict]:
    """Ground every usable reading and look for agreement. Returns (verdict or None, details).
    None means the readers disagree and a validator reading is needed."""
    usable = [r for r in readings if not r.error]
    grounded = {r.reader: ground_reading(r) for r in usable}
    sigs = {name: signature(cat, incs) for name, (cat, incs) in grounded.items()}
    details = {name: {"category": cat, "incidents": [i.to_dict() for i in incs], "signature": repr(sigs[name])}
               for name, (cat, incs) in grounded.items()}
    if not sigs:
        return None, details
    counts: dict[tuple, list[str]] = {}
    for name, s in sigs.items():
        counts.setdefault(s, []).append(name)
    best_sig, voters = max(counts.items(), key=lambda kv: len(kv[1]))
    if len(sigs) == 1:
        return None, details           # one voice is not enough
    if len(voters) == len(sigs):
        agreement = "unanimous"
    elif len(voters) >= 2 and len(voters) > len(sigs) / 2:
        agreement = "majority"
    else:
        return None, details
    cat, incs = grounded[voters[0]]
    return _verdict(cat, incs, agreement, voters, details), details


def _verdict(cat: str, incs: list[ResolvedIncident], agreement: str, voters: list[str], details: dict) -> Verdict:
    actionable = [i for i in incs if i.actionable]
    unresolved = [i for i in incs if not i.actionable]
    missing = [m for i in unresolved for m in i.missing]
    if cat == "noise":
        reason = "not about plant operations, shipments or part quality"
    elif cat == "unconfirmed":
        reason = "possibly about our operations but unconfirmed or not specific"
        missing = missing or ["a confirmed source", "which part / plant / supplier", "the dates affected"]
    elif not actionable:
        cat, reason = "unconfirmed", "reads like an incident but cannot be grounded in the company data"
    else:
        reason = f"{len(actionable)} grounded incident(s)" + (f", {len(unresolved)} unresolved" if unresolved else "")
    order = {"supplier_delay": 0, "plant_outage": 0, "quality_hold": 1}
    actionable.sort(key=lambda i: (order[i.kind], i.start or ""))
    return Verdict(cat, actionable, unresolved, agreement, voters, reason, missing, details)


def split_verdict(details: dict) -> Verdict:
    return Verdict("unconfirmed", [], [], "split", list(details), "the readers could not agree on what happened",
                   ["a clear restatement of the incident (readers disagree)"], details)
