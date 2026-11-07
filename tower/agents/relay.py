"""RELAY - Dealer Network & Customer Care.

Turns affected customer orders into exactly one notice per dealer, allocates loaners by the
handbook's priority against the live pool, and contacts owners on AEGIS's behalf.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Callable

from ..data import World
from ..policy.ledger import Ledger, Packet
from ..policy.rules import LOANER_TIERS, TIER_RANK
from .base import Radio, WorkOrder

NAME = "RELAY"


def _labels(orders: list[WorkOrder]) -> str:
    out = []
    for wo in orders:
        i = wo.incident
        if i.kind == "supplier_delay":
            out.append(f"late {i.part} shipment to {i.plant} (now {i.end})")
        else:
            out.append(f"{i.plant} outage {i.start}..{i.end}")
    return "; ".join(out)


def plan_delays(w: World, ledger: Ledger, orders: list[WorkOrder], radio: Radio,
                read_pool: Callable[[str], int | None] | None = None) -> tuple[list[Packet], dict]:
    """Rules 4 and 5 over the union of all incidents in the event (shared pools)."""
    co_incident: dict[str, int] = {}
    co_path: dict[int, str] = {}
    for wo in orders:
        for co in wo.impact.customer_orders:
            co_incident.setdefault(co, wo.incident_no)
        from ..kg.paths import path_string
        co_path[wo.incident_no] = path_string(wo.impact)
    by_dealer: dict[str, list[str]] = defaultdict(list)
    for co in sorted(co_incident):
        by_dealer[w.customer_orders[co]["dealer_id"]].append(co)
    packets: list[Packet] = []
    reason = _labels(orders)
    for dealer in sorted(by_dealer):
        cos = by_dealer[dealer]
        incs = sorted({co_incident[c] for c in cos})
        packets.append(Packet(NAME, "dealer.notify", {
            "dealer_id": dealer, "customer_order_ids": cos,
            "message": f"Wacky Wheels control tower: {len(cos)} of your customer orders are delayed by {reason}. "
                       f"Production has been re-planned; affected orders: {', '.join(cos)}."},
            "R4", f"{dealer} has {len(cos)} affected customer order(s); one notice listing exactly those",
            incs[0], co_path[incs[0]]))
    radio.say(NAME, f"{len(co_incident)} affected customer orders across {len(by_dealer)} dealers -> "
                    f"{len(by_dealer)} dealer notices (one each)")

    report: dict[str, dict] = {}
    granted = 0
    for dealer in sorted(by_dealer):
        entitled = [c for c in by_dealer[dealer]
                    if w.customers[w.customer_orders[c]["customer_id"]]["tier"] in LOANER_TIERS]
        if not entitled:
            continue
        entitled.sort(key=lambda c: (TIER_RANK[w.customers[w.customer_orders[c]["customer_id"]]["tier"]],
                                     w.customer_orders[c]["promised_date"], c))
        if read_pool is not None and dealer not in ledger.loaners_live:
            live = read_pool(dealer)
            if live is not None:
                ledger.loaners[dealer] = live
                ledger.loaners_live.add(dealer)
        pool = ledger.loaners.get(dealer, 0)
        got, wait = [], []
        for co in entitled:
            if ledger.take_loaner(co, dealer):
                got.append(co)
                tier = w.customers[w.customer_orders[co]["customer_id"]]["tier"]
                packets.append(Packet(NAME, "crm.assign_loaner", {"customer_order_id": co}, "R5",
                                      f"{co}: {tier} customer, promised {w.customer_orders[co]['promised_date']}, "
                                      f"{dealer} pool {pool} -> rank {len(got)}",
                                      co_incident[co], co_path[co_incident[co]]))
            else:
                wait.append(co)
        granted += len(got)
        report[dealer] = {"pool": pool, "entitled": entitled, "granted": got, "waitlisted": wait}
    short = sum(len(r["waitlisted"]) for r in report.values())
    radio.say(NAME, f"loaners: {granted} granted to Platinum/Gold customers across {len(report)} dealers"
                    + (f", {short} entitled customers waitlisted (pool empty)" if short else ""))
    return packets, report


def plan_owner_contacts(w: World, owners: list[str], why: str, incident_no: int, path: str,
                        radio: Radio) -> list[Packet]:
    packets = [Packet(NAME, "crm.notify_customer", {
        "customer_id": cid,
        "message": f"Safety notice from Wacky Wheels: your vehicle may contain a part under quality hold ({why}). "
                   f"Please contact your dealer to schedule an inspection at no cost."},
        "R6", f"owner of a sold affected vehicle ({why})", incident_no, path) for cid in sorted(set(owners))]
    radio.say(NAME, f"contacting {len(packets)} owners of sold vehicles for AEGIS")
    return packets
