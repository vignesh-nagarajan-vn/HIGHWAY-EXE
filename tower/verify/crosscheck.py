"""CROSSCHECK - N-version impact analysis.

The same handbook rules written a second time, independently, as SQL over the raw CSVs in
DuckDB. The graph traversal and the SQL must return identical affected sets before anything
is applied; a disagreement means one of the two derivations is wrong and blocks the event.
"""
from __future__ import annotations

from functools import lru_cache

import duckdb

from ..config import DATA_DIR
from ..kg.paths import Impact

TABLES = ["production_orders", "customer_orders", "finished_vehicles", "bom", "inbound_shipments",
          "part_lots", "plant_models", "calendar"]


@lru_cache(maxsize=1)
def _con() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    for t in TABLES:
        path = (DATA_DIR / f"{t}.csv").as_posix()
        con.execute(f"CREATE TABLE {t} AS SELECT * FROM read_csv('{path}', all_varchar=true, header=true)")
    return con


def _today() -> str:
    return _con().execute("SELECT date FROM calendar WHERE day_index = '0'").fetchone()[0]


def _orders_tail(po_sql: str, params: list) -> dict:
    con = _con()
    pos = [r[0] for r in con.execute(f"SELECT DISTINCT production_order_id FROM ({po_sql}) ORDER BY 1", params).fetchall()]
    cos = con.execute(f"""SELECT customer_order_id, dealer_id, customer_id FROM customer_orders
                          WHERE production_order_id IN (SELECT production_order_id FROM ({po_sql}))""", params).fetchall()
    return {"production_orders": pos, "customer_orders": sorted(c[0] for c in cos),
            "dealers": sorted({c[1] for c in cos}), "customers": sorted({c[2] for c in cos})}


def delay_sets(shipment_id: str, new_eta: str) -> dict:
    sql = """SELECT p.production_order_id FROM inbound_shipments s
             JOIN production_orders p ON p.plant_id = s.plant_id
             JOIN bom b ON b.model = p.model AND b.part_id = s.part_id
             WHERE s.shipment_id = ? AND p.build_date >= greatest(s.eta_date, ?) AND p.build_date < ?"""
    return _orders_tail(sql, [shipment_id, _today(), new_eta])


def outage_sets(plant_id: str, start: str, end: str) -> dict:
    sql = """SELECT production_order_id FROM production_orders
             WHERE plant_id = ? AND build_date >= greatest(?, ?) AND build_date <= ?"""
    return _orders_tail(sql, [plant_id, start, _today(), end])


def lot_sets(lot_ids: list[str]) -> dict:
    con = _con()
    marks = ",".join("?" for _ in lot_ids)
    rows = con.execute(f"""
        SELECT DISTINCT v.vin, v.status, v.dealer_id, v.customer_id, v.production_order_id
        FROM part_lots l
        JOIN bom b ON b.part_id = l.part_id
        JOIN production_orders p ON p.plant_id = l.plant_id AND p.model = b.model
             AND p.build_date BETWEEN l.first_build_date AND l.last_build_date
        JOIN finished_vehicles v ON v.production_order_id = p.production_order_id
             AND v.build_date BETWEEN l.first_build_date AND l.last_build_date
        WHERE l.lot_id IN ({marks})""", lot_ids).fetchall()
    stock = [r for r in rows if r[1] == "in_stock"]
    sold = [r for r in rows if r[1] == "sold"]
    return {"production_orders": sorted({r[4] for r in rows}),
            "vehicles_in_stock": sorted(r[0] for r in stock), "vehicles_sold": sorted(r[0] for r in sold),
            "dealers": sorted({r[2] for r in stock}), "owners": sorted({r[3] for r in sold if r[3]})}


def compare(imp: Impact, kind: str, **kw) -> dict:
    """Run the SQL twin of an impact and diff every set."""
    if kind == "supplier_delay":
        sql = delay_sets(kw["shipment_id"], kw["new_eta"])
    elif kind == "plant_outage":
        sql = outage_sets(kw["plant_id"], kw["start"], kw["end"])
    else:
        sql = lot_sets(kw["lot_ids"])
    diffs = {}
    for key, want in sql.items():
        got = getattr(imp, key)
        if sorted(got) != sorted(want):
            diffs[key] = {"graph_only": sorted(set(got) - set(want))[:5], "sql_only": sorted(set(want) - set(got))[:5]}
    return {"agree": not diffs, "sizes": {k: len(v) for k, v in sql.items()}, "diffs": diffs}
