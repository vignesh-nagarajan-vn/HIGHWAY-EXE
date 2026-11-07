"""Shared state for planning one event: slots, disruptions and loaner pools.

All specialists of an event plan against the same Ledger, so a compound message (an outage plus
a delay) never hands the same slot or the same loaner to two orders.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from ..data import World
from ..ground import calendar as cal


@dataclass
class Block:
    """A disruption: the plant cannot build `models` (None = anything) on days [lo, hi)."""
    plant: str
    lo: int
    hi: int
    models: frozenset[str] | None
    label: str


@dataclass
class Packet:
    """One planned tool call, carrying the proof that justifies it."""
    agent: str
    tool: str
    args: dict
    rule: str
    why: str
    incident: int | None = None
    path: str = ""
    seq: int = 0
    proof: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"seq": self.seq, "agent": self.agent, "tool": self.tool, "args": self.args, "rule": self.rule,
                "why": self.why, "incident": self.incident, "path": self.path, "proof": self.proof}


class Ledger:
    def __init__(self, w: World):
        self.w = w
        self.loc: dict[str, tuple[str, int]] = {}
        self.slots: dict[tuple[str, int], set[str]] = defaultdict(set)
        for po, r in w.production_orders.items():
            i = cal.idx_of(date.fromisoformat(r["build_date"]))
            if i >= 0:
                self.loc[po] = (r["plant_id"], i)
                self.slots[(r["plant_id"], i)].add(po)
        self.original = dict(self.loc)
        self.blocks: list[Block] = []
        self.loaners: dict[str, int] = dict(w.loaners)
        self.loaners_live: set[str] = set()   # dealers whose pool came from a live read
        self.loaned: set[str] = set()

    # --- capacity ---------------------------------------------------------
    def free(self, plant: str, idx: int) -> int:
        return self.w.slots(plant) - len(self.slots[(plant, idx)])

    def blocked(self, plant: str, idx: int, model: str) -> Block | None:
        for b in self.blocks:
            if b.plant == plant and b.lo <= idx < b.hi and (b.models is None or model in b.models):
                return b
        return None

    def feasible(self, po: str, plant: str, idx: int) -> bool:
        model = self.w.production_orders[po]["model"]
        return (0 <= idx <= cal.last_index() and model in self.w.plant_models[plant]
                and self.free(plant, idx) > 0 and self.blocked(plant, idx, model) is None
                and (plant, idx) != self.loc.get(po))

    def move(self, po: str, plant: str, idx: int) -> None:
        cur = self.loc[po]
        self.slots[cur].discard(po)
        self.slots[(plant, idx)].add(po)
        self.loc[po] = (plant, idx)

    # --- loaners ----------------------------------------------------------
    def take_loaner(self, co: str, dealer: str) -> bool:
        if co in self.loaned or self.loaners.get(dealer, 0) <= 0:
            return False
        self.loaners[dealer] -= 1
        self.loaned.add(co)
        return True
