from tower.agents import forge, relay
from tower.agents.base import Radio, WorkOrder
from tower.data import world
from tower.ground.judge import ResolvedIncident
from tower.kg import kg
from tower.policy.ledger import Ledger
from tower.policy.rules import TIER_RANK


def setup(incidents):
    led, radio = Ledger(world()), Radio()
    orders = [WorkOrder(i, inc) for i, inc in enumerate(incidents, 1)]
    for wo in orders:
        forge.assess(kg(), wo)
    return led, radio, orders


def test_one_notice_per_dealer_with_exact_orders():
    led, radio, orders = setup([ResolvedIncident("plant_outage", True, plant="P_KY", start="2027-03-16",
                                                 end="2027-03-18", resume_on="2027-03-19")])
    packets, _ = relay.plan_delays(world(), led, orders, radio)
    notes = [p for p in packets if p.tool == "dealer.notify"]
    assert len(notes) == len({p.args["dealer_id"] for p in notes}) == 32
    listed = sorted(c for p in notes for c in p.args["customer_order_ids"])
    assert listed == sorted(orders[0].impact.customer_orders)
    for p in notes:
        assert all(world().customer_orders[c]["dealer_id"] == p.args["dealer_id"] for c in p.args["customer_order_ids"])


def test_loaners_follow_priority_and_pool():
    w = world()
    led, radio, orders = setup([ResolvedIncident("plant_outage", True, plant="P_MS", start="2027-03-26",
                                                 end="2027-03-30", resume_on="2027-03-31")])
    packets, report = relay.plan_delays(w, led, orders, radio, read_pool=lambda d: 1)   # force scarcity
    for dealer, r in report.items():
        assert len(r["granted"]) == min(1, len(r["entitled"]))
        key = lambda c: (TIER_RANK[w.customers[w.customer_orders[c]["customer_id"]]["tier"]],
                         w.customer_orders[c]["promised_date"], c)
        assert r["granted"] == sorted(r["entitled"], key=key)[:1]
    loaned = {p.args["customer_order_id"] for p in packets if p.tool == "crm.assign_loaner"}
    assert all(w.customers[w.customer_orders[c]["customer_id"]]["tier"] != "Standard" for c in loaned)
