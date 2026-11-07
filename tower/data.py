"""Typed, read-only view of the company tables (the 'World').

Loaded once and shared by the knowledge graph, the planners and the verifiers.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path

from .config import DATA_DIR, EVENTS_PATH


def _read(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@dataclass
class World:
    plants: dict[str, dict]
    plant_order: list[str]
    plant_models: dict[str, set[str]]
    models: dict[str, dict]
    parts: dict[str, dict]
    bom: dict[str, set[str]]              # model -> parts
    suppliers: dict[str, dict]
    shipments: dict[str, dict]
    lots: dict[str, dict]
    production_orders: dict[str, dict]
    customer_orders: dict[str, dict]
    customers: dict[str, dict]
    dealers: dict[str, dict]
    vehicles: dict[str, dict]
    loaners: dict[str, int]
    aliases: list[dict]
    calendar: list[dict]
    # derived indexes
    cos_by_po: dict[str, list[str]] = field(default_factory=dict)
    vins_by_po: dict[str, list[str]] = field(default_factory=dict)
    pos_by_plant: dict[str, list[str]] = field(default_factory=dict)

    def models_using(self, part_id: str) -> set[str]:
        return {m for m, parts in self.bom.items() if part_id in parts}

    def slots(self, plant_id: str) -> int:
        return int(self.plants[plant_id]["slots_per_day"])


def load_world(data_dir: Path = DATA_DIR) -> World:
    rd = lambda n: _read(data_dir / n)
    plants_rows = rd("plants.csv")
    plants = {r["plant_id"]: r for r in plants_rows}
    plant_models: dict[str, set[str]] = defaultdict(set)
    for r in rd("plant_models.csv"):
        plant_models[r["plant_id"]].add(r["model"])
    bom: dict[str, set[str]] = defaultdict(set)
    for r in rd("bom.csv"):
        bom[r["model"]].add(r["part_id"])
    pos = {r["production_order_id"]: {**r, "units": int(r["units"])} for r in rd("production_orders.csv")}
    cos = {r["customer_order_id"]: r for r in rd("customer_orders.csv")}
    vehicles = {r["vin"]: r for r in rd("finished_vehicles.csv")}
    w = World(
        plants=plants,
        plant_order=[r["plant_id"] for r in plants_rows],
        plant_models=dict(plant_models),
        models={r["model"]: r for r in rd("models.csv")},
        parts={r["part_id"]: r for r in rd("parts.csv")},
        bom=dict(bom),
        suppliers={r["supplier_id"]: r for r in rd("suppliers.csv")},
        shipments={r["shipment_id"]: r for r in rd("inbound_shipments.csv")},
        lots={r["lot_id"]: r for r in rd("part_lots.csv")},
        production_orders=pos,
        customer_orders=cos,
        customers={r["customer_id"]: r for r in rd("customers.csv")},
        dealers={r["dealer_id"]: r for r in rd("dealers.csv")},
        vehicles=vehicles,
        loaners={r["dealer_id"]: int(r["loaners_available"]) for r in rd("loaners.csv")},
        aliases=rd("aliases.csv"),
        calendar=rd("calendar.csv"),
    )
    cos_by_po: dict[str, list[str]] = defaultdict(list)
    for co_id, r in cos.items():
        cos_by_po[r["production_order_id"]].append(co_id)
    vins_by_po: dict[str, list[str]] = defaultdict(list)
    for vin, r in vehicles.items():
        vins_by_po[r["production_order_id"]].append(vin)
    pos_by_plant: dict[str, list[str]] = defaultdict(list)
    for po_id, r in pos.items():
        pos_by_plant[r["plant_id"]].append(po_id)
    w.cos_by_po = {k: sorted(v) for k, v in cos_by_po.items()}
    w.vins_by_po = {k: sorted(v) for k, v in vins_by_po.items()}
    w.pos_by_plant = {k: sorted(v) for k, v in pos_by_plant.items()}
    return w


@lru_cache(maxsize=1)
def world() -> World:
    return load_world()


def load_events(path: Path = EVENTS_PATH) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def iso(d: date) -> str:
    return d.isoformat()
