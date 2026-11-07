"""FORGE - Supply Chain Planner.

Finds the production orders a delay or an outage blocks (graph traversal) and plans their
capacity-aware moves: earliest free slot at the same plant on or after the disruption ends,
otherwise a transfer to the earliest free day at another plant that builds the model.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from ..config import settings
from ..ground import calendar as cal
from ..kg.build import KnowledgeGraph
from ..kg.paths import delay_impact, outage_impact, path_string
from ..policy.ledger import Block, Ledger, Packet
from .base import Radio, WorkOrder, idx_ceil

NAME = "FORGE"


@dataclass
class SlotDecision:
    production_order_id: str
    model: str
    from_plant: str
    from_date: str
    to_plant: str | None
    to_date: str | None
    mode: str            # reschedule | transfer | unplaceable
    reason: str
    incident_no: int

    def to_dict(self) -> dict:
        return asdict(self)


def assess(kg: KnowledgeGraph, wo: WorkOrder) -> None:
    inc = wo.incident
    if inc.kind == "supplier_delay":
        wo.impact = delay_impact(kg, inc.shipment_id, inc.end)
    else:
        wo.impact = outage_impact(kg, inc.plant, inc.start, inc.end, inc.resume_on)


def block_for(wo: WorkOrder) -> Block:
    inc, imp = wo.incident, wo.impact
    lo = max(idx_ceil(inc.start), 0)
    hi = idx_ceil(inc.resume_on)
    models = frozenset(imp.models) if inc.kind == "supplier_delay" else None
    label = (f"{inc.part} short at {inc.plant}" if inc.kind == "supplier_delay" else f"{inc.plant} dark")
    return Block(inc.plant, lo, hi, models, label)


def plan(kg: KnowledgeGraph, ledger: Ledger, orders: list[WorkOrder], radio: Radio) -> tuple[list[Packet], list[SlotDecision]]:
    w = kg.w
    transfer_from = settings().transfer_from
    for wo in orders:
        ledger.blocks.append(block_for(wo))
    packets: list[Packet] = []
    decisions: list[SlotDecision] = []
    done: set[str] = set()
    for wo in orders:
        imp = wo.impact
        resume = idx_ceil(wo.incident.resume_on)
        radio.say(NAME, f"incident #{wo.incident_no}: {len(imp.production_orders)} production orders blocked at "
                        f"{imp.plant}; plant can build again on {wo.incident.resume_on}")
        todo = sorted((p for p in imp.production_orders if p not in done),
                      key=lambda p: (ledger.original[p][1], p))
        for po in todo:
            done.add(po)
            model = w.production_orders[po]["model"]
            home, cur = ledger.loc[po]
            target = None
            for i in range(max(resume, 0), cal.last_index() + 1):
                if ledger.feasible(po, home, i):
                    target, mode = (home, i), "reschedule"
                    why = f"earliest free slot at {home} on/after restart ({ledger.free(home, i)} free)"
                    break
            if target is None:
                start = 0 if transfer_from == "today" else max(resume, 0)
                for i in range(start, cal.last_index() + 1):
                    for plant in w.plant_order:
                        if plant != home and ledger.feasible(po, plant, i):
                            target, mode = (plant, i), "transfer"
                            why = (f"{home} has no free slot after restart through {cal.window_end()}; "
                                   f"earliest free {model} slot elsewhere is {plant}")
                            break
                    if target:
                        break
            from_date = cal.date_of(cur).isoformat()
            if target is None:
                decisions.append(SlotDecision(po, model, home, from_date, None, None, "unplaceable",
                                              "no feasible slot anywhere in the planning window", wo.incident_no))
                radio.say(NAME, f"{po} cannot be placed anywhere in the window - escalating", "warn")
                continue
            plant, i = target
            new_date = cal.date_of(i).isoformat()
            ledger.move(po, plant, i)
            decisions.append(SlotDecision(po, model, home, from_date, plant, new_date, mode, why, wo.incident_no))
            if mode == "reschedule":
                packets.append(Packet(NAME, "mes.reschedule", {"production_order_id": po, "new_date": new_date},
                                      "R3", f"{po} ({model}) {from_date} -> {new_date}: {why}",
                                      wo.incident_no, path_string(imp)))
            else:
                packets.append(Packet(NAME, "mes.transfer",
                                      {"production_order_id": po, "to_plant_id": plant, "new_date": new_date},
                                      "R3", f"{po} ({model}) {home} {from_date} -> {plant} {new_date}: {why}",
                                      wo.incident_no, path_string(imp)))
        moved = [d for d in decisions if d.incident_no == wo.incident_no]
        radio.say(NAME, f"incident #{wo.incident_no}: {sum(d.mode == 'reschedule' for d in moved)} rescheduled, "
                        f"{sum(d.mode == 'transfer' for d in moved)} transferred, "
                        f"{sum(d.mode == 'unplaceable' for d in moved)} unplaceable")
    return packets, decisions
