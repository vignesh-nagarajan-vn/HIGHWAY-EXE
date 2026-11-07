"""Build the knowledge graph (networkx MultiDiGraph) from the company tables."""
from __future__ import annotations

from collections import Counter
from functools import lru_cache

import networkx as nx

from ..data import World, world
from .ontology import RELATIONS, node_id as N


class KnowledgeGraph:
    """Thin wrapper over a MultiDiGraph with typed helpers."""

    def __init__(self, g: nx.MultiDiGraph, w: World):
        self.g = g
        self.w = w

    # --- typed navigation -------------------------------------------------
    def out(self, nid: str, rel: str) -> list[str]:
        return [v for _, v, k in self.g.out_edges(nid, keys=True) if k == rel]

    def inn(self, nid: str, rel: str) -> list[str]:
        return [u for u, _, k in self.g.in_edges(nid, keys=True) if k == rel]

    def attrs(self, nid: str) -> dict:
        return self.g.nodes[nid]

    def has(self, nid: str) -> bool:
        return nid in self.g

    def stats(self) -> dict:
        nodes = Counter(d["type"] for _, d in self.g.nodes(data=True))
        edges = Counter(k for _, _, k in self.g.edges(keys=True))
        return {"nodes": self.g.number_of_nodes(), "edges": self.g.number_of_edges(),
                "by_class": dict(sorted(nodes.items())), "by_relation": dict(sorted(edges.items()))}


def build_graph(w: World) -> KnowledgeGraph:
    g = nx.MultiDiGraph()

    def node(cls: str, key: str, **attrs):
        g.add_node(N(cls, key), type=cls, key=key, **attrs)

    def edge(u: str, rel: str, v: str):
        assert rel in RELATIONS, rel
        g.add_edge(u, v, key=rel)

    for d in w.calendar:
        node("WorkDay", d["date"], index=int(d["day_index"]), weekday=d["weekday"])
    for sid, r in w.suppliers.items():
        node("Supplier", sid, name=r["name"], city=r["city"])
    for pid, r in w.parts.items():
        node("Part", pid, name=r["name"], category=r["category"])
    for m, r in w.models.items():
        node("Model", m, segment=r["segment"])
    for p, r in w.plants.items():
        node("Plant", p, name=r["name"], city=r["city"], slots_per_day=int(r["slots_per_day"]))
        for m in sorted(w.plant_models.get(p, ())):
            edge(N("Plant", p), "BUILDS", N("Model", m))
    for m, parts in w.bom.items():
        for pid in sorted(parts):
            edge(N("Part", pid), "IN_BOM_OF", N("Model", m))
    for did, r in w.dealers.items():
        node("Dealer", did, name=r["name"], city=r["city"], region=r["region"])
        node("LoanerPool", did, available=w.loaners.get(did, 0))
        edge(N("Dealer", did), "HAS_POOL", N("LoanerPool", did))
    for cid, r in w.customers.items():
        node("Customer", cid, name=r["name"], tier=r["tier"])

    supplies = set()
    for sh, r in w.shipments.items():
        node("Shipment", sh, eta=r["eta_date"], covers_days=int(r["covers_days"]))
        edge(N("Supplier", r["supplier_id"]), "SENDS", N("Shipment", sh))
        edge(N("Shipment", sh), "CARRIES", N("Part", r["part_id"]))
        edge(N("Shipment", sh), "DELIVERS_TO", N("Plant", r["plant_id"]))
        if N("WorkDay", r["eta_date"]) in g:
            edge(N("Shipment", sh), "ARRIVES_ON", N("WorkDay", r["eta_date"]))
        supplies.add((r["supplier_id"], r["part_id"]))
    for lot, r in w.lots.items():
        node("Lot", lot, first_build=r["first_build_date"], last_build=r["last_build_date"])
        edge(N("Supplier", r["supplier_id"]), "MADE", N("Lot", lot))
        edge(N("Lot", lot), "LOT_OF", N("Part", r["part_id"]))
        edge(N("Lot", lot), "INSTALLED_AT", N("Plant", r["plant_id"]))
        supplies.add((r["supplier_id"], r["part_id"]))
    for s, p in sorted(supplies):
        edge(N("Supplier", s), "SUPPLIES", N("Part", p))

    for po, r in w.production_orders.items():
        node("ProductionOrder", po, plant=r["plant_id"], date=r["build_date"], model=r["model"], units=r["units"])
        edge(N("Plant", r["plant_id"]), "RUNS", N("ProductionOrder", po))
        edge(N("Model", r["model"]), "BUILT_AS", N("ProductionOrder", po))
        edge(N("ProductionOrder", po), "SCHEDULED_ON", N("WorkDay", r["build_date"]))
    for co, r in w.customer_orders.items():
        node("CustomerOrder", co, promised=r["promised_date"], model=r["model"])
        edge(N("ProductionOrder", r["production_order_id"]), "PROMISED_TO", N("CustomerOrder", co))
        edge(N("CustomerOrder", co), "VIA_DEALER", N("Dealer", r["dealer_id"]))
        edge(N("CustomerOrder", co), "FOR_CUSTOMER", N("Customer", r["customer_id"]))
    for vin, r in w.vehicles.items():
        node("Vehicle", vin, status=r["status"], date=r["build_date"], model=r["model"], plant=r["plant_id"])
        edge(N("ProductionOrder", r["production_order_id"]), "PRODUCED", N("Vehicle", vin))
        edge(N("Vehicle", vin), "AT_DEALER", N("Dealer", r["dealer_id"]))
        if r["status"] == "sold" and r["customer_id"]:
            edge(N("Vehicle", vin), "OWNED_BY", N("Customer", r["customer_id"]))

    cls_of = {"plant": "Plant", "part": "Part", "supplier": "Supplier"}
    for r in w.aliases:
        a = N("Alias", r["alias"].lower())
        g.add_node(a, type="Alias", key=r["alias"].lower(), text=r["alias"])
        edge(a, "ALIAS_OF", N(cls_of[r["entity_type"]], r["entity_id"]))
    return KnowledgeGraph(g, w)


@lru_cache(maxsize=1)
def kg() -> KnowledgeGraph:
    return build_graph(world())
