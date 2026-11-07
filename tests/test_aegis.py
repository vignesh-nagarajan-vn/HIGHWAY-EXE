from tower.agents import aegis
from tower.agents.base import Radio, WorkOrder
from tower.data import world
from tower.ground.judge import ResolvedIncident
from tower.kg import kg


def test_quality_hold_packets():
    inc = ResolvedIncident("quality_hold", True, plant="P_TX", part="HARN-B", supplier="SUP-07",
                           lot_ids=["LOT-0017"], start="2027-02-22", end="2027-02-24")
    wo = WorkOrder(1, inc)
    aegis.assess(kg(), wo)
    packets, owners = aegis.plan(kg(), wo, Radio())
    tools = [p.tool for p in packets]
    assert tools[0] == "quality.hold_lot" and tools.count("quality.hold_lot") == 1
    stops = [p for p in packets if p.tool == "dealer.stop_sale"]
    vins = [v for p in stops for v in p.args["vins"]]
    assert len(vins) == 86 and len(owners) == 94
    w = world()
    for p in stops:
        for v in p.args["vins"]:
            r = w.vehicles[v]
            assert r["status"] == "in_stock" and r["dealer_id"] == p.args["dealer_id"]
            assert r["plant_id"] == "P_TX" and "2027-02-22" <= r["build_date"] <= "2027-02-24"
            assert r["model"] in {"SUMMIT", "RANGER"}          # models whose BOM has HARN-B
