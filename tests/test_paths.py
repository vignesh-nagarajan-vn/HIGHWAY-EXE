"""Graph traversal sanity checks. Expected sizes come from the planning-time analysis and live
only in tests (the runtime never sees them)."""
from tower.kg import kg
from tower.kg.paths import delay_impact, lot_impact, outage_impact, path_string, traceroute


def test_delay_impact_follows_bom_at_receiving_plant():
    imp = delay_impact(kg(), "SH-0182", "2027-03-18")
    assert imp.plant == "P_IN" and imp.part == "CAM-360"
    assert imp.models == ["VOYAGER"]            # SUMMIT uses CAM-360 but is not built at P_IN
    assert len(imp.production_orders) == 3
    assert len(imp.customer_orders) == 26 and len(imp.dealers) == 14
    assert all("2027-03-15" <= kg().attrs(f"ProductionOrder:{p}")["date"] < "2027-03-18" for p in imp.production_orders)


def test_outage_impact_inclusive_window():
    imp = outage_impact(kg(), "P_MS", "2027-03-26", "2027-03-30", "2027-03-31")
    assert len(imp.production_orders) == 9
    assert len(imp.customer_orders) == 79


def test_lot_impact_splits_sold_and_unsold():
    imp = lot_impact(kg(), "LOT-0130")
    assert imp.plant == "P_MS" and imp.window == ("2027-02-25", "2027-03-01")
    assert len(imp.vehicles_in_stock) == 110 and len(imp.vehicles_sold) == 150
    assert len(imp.owners) == 150


def test_traceroute_renders_every_hop():
    imp = delay_impact(kg(), "SH-0182", "2027-03-18")
    lines = traceroute(imp)
    assert lines[0].startswith("traceroute to SUPPLIER_DELAY")
    assert len(lines) == len(imp.hops) + 1
    assert "Shipment:SH-0182" in path_string(imp)
