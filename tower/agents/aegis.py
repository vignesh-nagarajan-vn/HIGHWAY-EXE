"""AEGIS - Quality.

Resolves the defective lot(s), sweeps the vehicles built from them, splits unsold from sold,
holds the lot and stops sale dealer by dealer. Owner contacts go to RELAY as a work order.
"""
from __future__ import annotations

from collections import defaultdict

from ..kg.build import KnowledgeGraph
from ..kg.paths import Impact, lot_impact, path_string
from ..policy.ledger import Packet
from .base import Radio, WorkOrder

NAME = "AEGIS"


def assess(kg: KnowledgeGraph, wo: WorkOrder) -> list[Impact]:
    imps = [lot_impact(kg, lot) for lot in wo.incident.lot_ids]
    wo.impact = imps[0]
    if len(imps) > 1:      # several whole lots: merge into one impact for the downstream steps
        m = wo.impact
        for extra in imps[1:]:
            m.production_orders = sorted(set(m.production_orders) | set(extra.production_orders))
            m.vehicles_in_stock = sorted(set(m.vehicles_in_stock) | set(extra.vehicles_in_stock))
            m.vehicles_sold = sorted(set(m.vehicles_sold) | set(extra.vehicles_sold))
            m.dealers = sorted(set(m.dealers) | set(extra.dealers))
            m.owners = sorted(set(m.owners) | set(extra.owners))
    return imps


def plan(kg: KnowledgeGraph, wo: WorkOrder, radio: Radio) -> tuple[list[Packet], list[str]]:
    w = kg.w
    imp = wo.impact
    path = path_string(imp)
    inc = wo.incident
    packets = [Packet(NAME, "quality.hold_lot", {"lot_id": lot}, "R6",
                      f"{lot}: {inc.supplier} {inc.part} installed at {inc.plant}, built {inc.start}..{inc.end}",
                      wo.incident_no, path) for lot in inc.lot_ids]
    by_dealer: dict[str, list[str]] = defaultdict(list)
    for vin in imp.vehicles_in_stock:
        by_dealer[w.vehicles[vin]["dealer_id"]].append(vin)
    for dealer in sorted(by_dealer):
        vins = sorted(by_dealer[dealer])
        packets.append(Packet(NAME, "dealer.stop_sale", {"dealer_id": dealer, "vins": vins}, "R6",
                              f"{len(vins)} unsold affected vehicle(s) in stock at {dealer}", wo.incident_no, path))
    radio.say(NAME, f"lot {', '.join(inc.lot_ids)}: {len(imp.production_orders)} production orders, "
                    f"{len(imp.vehicles_in_stock) + len(imp.vehicles_sold)} vehicles "
                    f"({len(imp.vehicles_in_stock)} in stock at {len(by_dealer)} dealers, {len(imp.vehicles_sold)} sold)")
    radio.say(NAME, f"handing {len(imp.owners)} owner contacts to RELAY")
    return packets, imp.owners
