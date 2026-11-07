"""Impact traversals over the knowledge graph.

Each query walks typed edges forward from the incident's anchor node and records every
hop, so the result is both the affected set and the graph path that proves it.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .build import KnowledgeGraph
from .ontology import node_id as N, split_id


@dataclass
class Hop:
    cls: str
    rel: str            # relation used to reach this hop ("" for the anchor)
    ids: list[str]
    note: str = ""


@dataclass
class Impact:
    kind: str                      # supplier_delay | plant_outage | quality_hold
    anchor: str                    # node id of the incident anchor
    plant: str
    window: tuple[str, str]        # affected build window (inclusive, ISO)
    resume_on: str | None = None   # first day the plant may build again (delay/outage)
    production_orders: list[str] = field(default_factory=list)
    customer_orders: list[str] = field(default_factory=list)
    dealers: list[str] = field(default_factory=list)
    customers: list[str] = field(default_factory=list)
    vehicles_in_stock: list[str] = field(default_factory=list)
    vehicles_sold: list[str] = field(default_factory=list)
    owners: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    part: str | None = None
    hops: list[Hop] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _keys(ids) -> list[str]:
    return sorted({split_id(i)[1] for i in ids})


def _today(kg: KnowledgeGraph) -> str:
    return next(d["date"] for d in kg.w.calendar if int(d["day_index"]) == 0)


def _orders_downstream(kg: KnowledgeGraph, imp: Impact, po_nodes: list[str]) -> None:
    """ProductionOrder -> CustomerOrder -> Dealer / Customer."""
    co_nodes = sorted({c for p in po_nodes for c in kg.out(p, "PROMISED_TO")})
    dealer_nodes = {d for c in co_nodes for d in kg.out(c, "VIA_DEALER")}
    cust_nodes = {c2 for c in co_nodes for c2 in kg.out(c, "FOR_CUSTOMER")}
    imp.production_orders = _keys(po_nodes)
    imp.customer_orders = _keys(co_nodes)
    imp.dealers = _keys(dealer_nodes)
    imp.customers = _keys(cust_nodes)
    imp.hops += [
        Hop("ProductionOrder", "BUILT_AS", imp.production_orders),
        Hop("CustomerOrder", "PROMISED_TO", imp.customer_orders),
        Hop("Dealer", "VIA_DEALER", imp.dealers, "notify"),
        Hop("Customer", "FOR_CUSTOMER", imp.customers, "loaner check"),
    ]


def delay_impact(kg: KnowledgeGraph, shipment_id: str, new_eta: str) -> Impact:
    """Rule 1: builds needing the part at the receiving plant, from the original ETA up to
    (not including) the new ETA."""
    sh = N("Shipment", shipment_id)
    part = kg.out(sh, "CARRIES")[0]
    plant = kg.out(sh, "DELIVERS_TO")[0]
    supplier = kg.inn(sh, "SENDS")[0]
    orig = kg.attrs(sh)["eta"]
    start = max(orig, _today(kg))
    models = sorted(kg.out(part, "IN_BOM_OF"))
    built_here = set(kg.out(plant, "BUILDS"))
    models_here = [m for m in models if m in built_here]
    po_nodes = sorted(
        p for m in models_here for p in kg.out(m, "BUILT_AS")
        if kg.attrs(p)["plant"] == split_id(plant)[1] and start <= kg.attrs(p)["date"] < new_eta
    )
    imp = Impact("supplier_delay", sh, split_id(plant)[1], (orig, new_eta), resume_on=new_eta,
                 part=split_id(part)[1], models=_keys(models_here))
    imp.hops = [
        Hop("Supplier", "", _keys([supplier])),
        Hop("Shipment", "SENDS", [shipment_id], f"ETA {orig} -> {new_eta}"),
        Hop("Part", "CARRIES", [split_id(part)[1]]),
        Hop("Plant", "DELIVERS_TO", [split_id(plant)[1]]),
        Hop("Model", "IN_BOM_OF", imp.models, "BOM filter at receiving plant"),
    ]
    _orders_downstream(kg, imp, po_nodes)
    return imp


def outage_impact(kg: KnowledgeGraph, plant_id: str, start: str, end: str, resume_on: str | None) -> Impact:
    """Rule 2: every production order of the plant inside the outage (inclusive)."""
    plant = N("Plant", plant_id)
    lo = max(start, _today(kg))
    po_nodes = sorted(p for p in kg.out(plant, "RUNS") if lo <= kg.attrs(p)["date"] <= end)
    imp = Impact("plant_outage", plant, plant_id, (start, end), resume_on=resume_on)
    imp.hops = [Hop("Plant", "", [plant_id], f"dark {start} .. {end}")]
    _orders_downstream(kg, imp, po_nodes)
    return imp


def lot_impact(kg: KnowledgeGraph, lot_id: str) -> Impact:
    """Rule 6: vehicles built at the lot's plant on the lot's build dates, from production
    orders of models that use the part; split into unsold (stop sale) and sold (owners)."""
    lot = N("Lot", lot_id)
    a = kg.attrs(lot)
    part = kg.out(lot, "LOT_OF")[0]
    plant = kg.out(lot, "INSTALLED_AT")[0]
    supplier = kg.inn(lot, "MADE")[0]
    plant_id = split_id(plant)[1]
    first, last = a["first_build"], a["last_build"]
    models = sorted(m for m in kg.out(part, "IN_BOM_OF") if m in set(kg.out(plant, "BUILDS")))
    po_nodes = sorted(
        p for m in models for p in kg.out(m, "BUILT_AS")
        if kg.attrs(p)["plant"] == plant_id and first <= kg.attrs(p)["date"] <= last
    )
    vehicles = [v for p in po_nodes for v in kg.out(p, "PRODUCED") if first <= kg.attrs(v)["date"] <= last]
    in_stock = [v for v in vehicles if kg.attrs(v)["status"] == "in_stock"]
    sold = [v for v in vehicles if kg.attrs(v)["status"] == "sold"]
    dealers = {d for v in in_stock for d in kg.out(v, "AT_DEALER")}
    owners = {c for v in sold for c in kg.out(v, "OWNED_BY")}
    imp = Impact("quality_hold", lot, plant_id, (first, last), part=split_id(part)[1], models=_keys(models))
    imp.production_orders = _keys(po_nodes)
    imp.vehicles_in_stock = _keys(in_stock)
    imp.vehicles_sold = _keys(sold)
    imp.dealers = _keys(dealers)
    imp.owners = _keys(owners)
    imp.hops = [
        Hop("Supplier", "", _keys([supplier])),
        Hop("Lot", "MADE", [lot_id], f"built {first} .. {last}"),
        Hop("Part", "LOT_OF", [split_id(part)[1]]),
        Hop("Model", "IN_BOM_OF", imp.models),
        Hop("ProductionOrder", "BUILT_AS", imp.production_orders, f"at {plant_id} in window"),
        Hop("Vehicle", "PRODUCED", imp.vehicles_in_stock + imp.vehicles_sold,
            f"{len(imp.vehicles_in_stock)} in stock / {len(imp.vehicles_sold)} sold"),
        Hop("Dealer", "AT_DEALER", imp.dealers, "stop sale"),
        Hop("Customer", "OWNED_BY", imp.owners, "contact owners"),
    ]
    return imp


def traceroute(imp: Impact) -> list[str]:
    """Render the graph path like a network traceroute: one line per hop with fan-out."""
    lines = [f"traceroute to {imp.kind.upper()} via {imp.anchor}, {len(imp.hops)} hops max"]
    for i, h in enumerate(imp.hops, 1):
        head = h.ids[0] if len(h.ids) == 1 else f"{len(h.ids)}x"
        sample = "" if len(h.ids) <= 1 else " [" + ", ".join(h.ids[:3]) + (", ..." if len(h.ids) > 3 else "") + "]"
        via = f"-{h.rel}->" if h.rel else "anchor"
        note = f"  ({h.note})" if h.note else ""
        lines.append(f"{i:>2}  {via:<16} {h.cls}:{head}{sample}{note}")
    return lines


def path_string(imp: Impact) -> str:
    """Compact one-line path, e.g. Shipment:SH-0182 -CARRIES-> Part:CAM-360 -> ..."""
    parts = []
    for h in imp.hops:
        label = f"{h.cls}:{h.ids[0]}" if len(h.ids) == 1 else f"{len(h.ids)}x{h.cls}"
        parts.append(label if not h.rel else f"-{h.rel}-> {label}")
    return " ".join(parts)
