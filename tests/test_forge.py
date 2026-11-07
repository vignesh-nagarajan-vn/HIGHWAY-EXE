from tower.agents import forge
from tower.agents.base import Radio, WorkOrder
from tower.data import world
from tower.ground.judge import ResolvedIncident
from tower.kg import kg
from tower.policy.ledger import Ledger
from tower.vendor import Enterprise
from tower.config import DATA_DIR


def outage(plant, start, end, resume):
    return ResolvedIncident("plant_outage", True, plant=plant, start=start, end=end, resume_on=resume)


def run(incidents):
    led, radio = Ledger(world()), Radio()
    orders = [WorkOrder(i, inc) for i, inc in enumerate(incidents, 1)]
    for wo in orders:
        forge.assess(kg(), wo)
    return forge.plan(kg(), led, orders, radio), orders


def test_forced_transfers_when_plant_is_full():
    # Jackson dark 3/26-3/30: 9 orders, only 6 free slots 3/31-4/2 -> 3 transfers
    (packets, decisions), _ = run([outage("P_MS", "2027-03-26", "2027-03-30", "2027-03-31")])
    modes = [d.mode for d in decisions]
    assert modes.count("reschedule") == 6 and modes.count("transfer") == 3
    for d in decisions:
        if d.mode == "reschedule":
            assert d.to_plant == "P_MS" and d.to_date >= "2027-03-31"
        else:
            assert d.to_plant != "P_MS" and d.model in world().plant_models[d.to_plant]


def test_reschedule_is_earliest_and_ordered():
    (packets, decisions), _ = run([outage("P_KY", "2027-03-16", "2027-03-18", "2027-03-19")])
    dates = [d.to_date for d in decisions]
    assert dates == sorted(dates)
    assert dates[:2] == ["2027-03-19", "2027-03-19"]
    assert all(d.mode == "reschedule" for d in decisions)


def test_plan_replays_cleanly_on_the_vendor_world():
    (packets, _), _ = run([outage("P_MS", "2027-03-26", "2027-03-30", "2027-03-31")])
    ent = Enterprise(str(DATA_DIR))
    for p in packets:
        ent.call("T", p.tool, p.args)          # raises ToolError on any infeasible move
