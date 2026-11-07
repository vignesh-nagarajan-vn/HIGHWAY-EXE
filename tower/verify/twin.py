"""TWIN - digital-twin dry run.

Replays the whole plan on a fresh in-process copy of the organisers' own enterprise model
(vendor/enterprise.py, unmodified) before any real call is made. Any ToolError here means the
real server would reject the call too, so the plan is fixed or escalated instead of executed.
"""
from __future__ import annotations

import itertools
from functools import lru_cache

from ..config import DATA_DIR
from ..policy.ledger import Packet
from ..vendor import Enterprise, ToolError

_runs = itertools.count(1)


@lru_cache(maxsize=1)
def _world() -> Enterprise:
    return Enterprise(str(DATA_DIR))


def dry_run(event_id: str, packets: list[Packet]) -> dict:
    ent = _world()
    key = f"{event_id}#twin{next(_runs)}"       # every dry run gets its own fresh world copy
    errors = []
    for p in packets:
        try:
            ent.call(key, p.tool, p.args)
            p.proof["twin"] = "ok"
        except ToolError as e:
            p.proof["twin"] = f"error: {e}"
            errors.append({"seq": p.seq, "tool": p.tool, "error": str(e)})
    s = ent.state(key)
    return {"ok": not errors, "errors": errors, "calls": len(packets),
            "final": {"moved": sum(1 for po, loc in s["loc"].items()
                                   if loc != (ent.orders[po]["plant_id"], ent.orders[po]["idx"])),
                      "held": sorted(s["held"]), "stopped": len(s["stopped"]),
                      "notified_dealers": len(s["notified"]), "loaned": len(s["loaned"]),
                      "customers": len(s["customers"]), "escalated": s["escalated"]}}
