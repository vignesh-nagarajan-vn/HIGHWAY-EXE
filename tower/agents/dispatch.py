"""DISPATCH - the coordinator.

Runs the two readers, asks the graph judge for a verdict (calling the Haiku validator only on
disagreement), decides noise / escalate / act, splits compound messages into work orders for
FORGE, AEGIS and RELAY, and returns one ordered plan of proof-carrying packets.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..data import world
from ..ground.judge import Verdict, judge, split_verdict
from ..intake import grammar_reader, haiku_validator, slm_reader
from ..intake.schemas import EventReading
from ..kg import kg
from ..policy.ledger import Ledger, Packet
from . import aegis, forge, relay
from .base import Radio, WorkOrder

NAME = "DISPATCH"


@dataclass
class EventPlan:
    event: dict
    readings: list[EventReading]
    verdict: Verdict
    orders: list[WorkOrder] = field(default_factory=list)
    packets: list[Packet] = field(default_factory=list)
    slot_decisions: list = field(default_factory=list)
    loaner_report: dict = field(default_factory=dict)
    radio: Radio = field(default_factory=Radio)
    validator_called: bool = False

    @property
    def writes(self) -> list[Packet]:
        from ..vendor import WRITE_TOOLS
        return [p for p in self.packets if p.tool in WRITE_TOOLS]


def read_event(event: dict, radio: Radio, slm_model: str | None = None,
               use_validator: bool = True) -> tuple[list[EventReading], Verdict, bool]:
    a = slm_reader.read(event, slm_model)
    b = grammar_reader.read(event)
    readings = [a, b]
    radio.say(NAME, f"READER-A ({a.model}) says {a.category.upper()} with {len(a.incidents)} incident(s)"
                    + (f" [error: {a.error}]" if a.error else "") + f" in {a.latency_ms} ms")
    radio.say(NAME, f"READER-B (grammar) says {b.category.upper()} with {len(b.incidents)} incident(s)")
    verdict, details = judge(readings)
    called = False
    if verdict is None and use_validator:
        radio.say(NAME, "readers disagree after grounding -> calling VALIDATOR (Claude Haiku)", "warn")
        c = haiku_validator.read(event)
        readings.append(c)
        called = True
        radio.say(NAME, f"VALIDATOR ({c.model}) says {c.category.upper()} with {len(c.incidents)} incident(s)"
                        + (f" [error: {c.error}]" if c.error else ""))
        verdict, details = judge(readings)
    if verdict is None:
        verdict = split_verdict(details)
        radio.say(NAME, "no majority reading -> escalate to a human", "warn")
    else:
        radio.say(NAME, f"GRAPH JUDGE: {verdict.category.upper()} ({verdict.agreement}: "
                        f"{', '.join(verdict.readers)}) - {verdict.reason}")
    return readings, verdict, called


def escalation_text(event: dict, verdict: Verdict) -> str:
    missing = "; ".join(dict.fromkeys(verdict.missing_intel)) or "n/a"
    return (f"[{event['event_id']} via {event.get('source', '?')}] Not actionable: {verdict.reason}. "
            f"Missing intel: {missing}. No operational change made. Please confirm with the supplier or "
            f"plant operations and re-submit with part, plant and dates.")


def plan_event(event: dict, slm_model: str | None = None, use_validator: bool = True,
               read_pool: Callable[[str], int | None] | None = None) -> EventPlan:
    radio = Radio()
    radio.say(NAME, f"incoming {event.get('source', 'message')} {event['event_id']}")
    readings, verdict, called = read_event(event, radio, slm_model, use_validator)
    plan = EventPlan(event, readings, verdict, radio=radio, validator_called=called)

    if verdict.category == "noise":
        radio.say(NAME, "NOISE: not about our operations -> no action (R7)")
        return plan
    if verdict.category == "unconfirmed":
        plan.packets.append(Packet(NAME, "escalate", {"reason": escalation_text(event, verdict)}, "R8",
                                   "unconfirmed or unspecific report: hand to a human, change nothing"))
        radio.say(NAME, "UNCONFIRMED: escalating to a human, no operational change (R8)", "warn")
        return plan

    g, w = kg(), world()
    ledger = Ledger(w)
    plan.orders = [WorkOrder(i, inc) for i, inc in enumerate(verdict.incidents, 1)]
    supply = [wo for wo in plan.orders if wo.incident.kind in ("supplier_delay", "plant_outage")]
    quality = [wo for wo in plan.orders if wo.incident.kind == "quality_hold"]
    for wo in plan.orders:
        who = "FORGE" if wo in supply else "AEGIS"
        radio.say(NAME, f"work order #{wo.incident_no} -> {who}: {wo.incident.kind} at {wo.incident.plant}")

    if supply:
        for wo in supply:
            forge.assess(g, wo)
        moves, decisions = forge.plan(g, ledger, supply, radio)
        plan.packets += moves
        plan.slot_decisions = decisions
        notices, report = relay.plan_delays(w, ledger, supply, radio, read_pool)
        plan.packets += notices
        plan.loaner_report = report
        stuck = [d for d in decisions if d.mode == "unplaceable"]
        if stuck:
            plan.packets.append(Packet(NAME, "escalate", {"reason": (
                f"[{event['event_id']}] {len(stuck)} production order(s) have no feasible slot in the planning "
                f"window: {', '.join(d.production_order_id for d in stuck)}. Needs a planner decision.")},
                "R8", "capacity exhausted for some affected orders"))
    for wo in quality:
        aegis.assess(g, wo)
        q_packets, owners = aegis.plan(g, wo, radio)
        plan.packets += q_packets
        why = f"{wo.incident.part} lot {', '.join(wo.incident.lot_ids)}"
        plan.packets += relay.plan_owner_contacts(w, owners, why, wo.incident_no, q_packets[0].path, radio)
    if verdict.unresolved:
        plan.packets.append(Packet(NAME, "escalate", {"reason": (
            f"[{event['event_id']}] part of this message could not be grounded: "
            f"{'; '.join(m for i in verdict.unresolved for m in i.missing)}. The grounded incidents were handled.")},
            "R8", "unresolved incident inside an otherwise actionable message"))
    for n, p in enumerate(plan.packets, 1):
        p.seq = n
    kinds = sorted({p.tool for p in plan.writes})
    radio.say(NAME, f"plan ready: {len(plan.packets)} packets, action kinds: {', '.join(kinds)}")
    return plan
