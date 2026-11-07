from tower.agents.base import Radio
from tower.agents.dispatch import EventPlan
from tower.ground.judge import Verdict
from tower.policy.ledger import Packet
from tower.verify import ice, twin


def bare_plan(category, packets):
    v = Verdict(category, [], [], "unanimous", ["slm", "grammar"], "test")
    return EventPlan({"event_id": "T"}, [], v, packets=packets, radio=Radio())


def test_ice_blocks_writes_on_noise_and_rumors():
    write = Packet("RELAY", "crm.notify_customer", {"customer_id": "C0001", "message": "hi"}, "R6", "x")
    assert ice.blocking(ice.check(bare_plan("noise", [write])))
    esc = Packet("DISPATCH", "escalate", {"reason": "rumor"}, "R8", "x")
    assert not ice.blocking(ice.check(bare_plan("unconfirmed", [esc])))
    assert ice.blocking(ice.check(bare_plan("unconfirmed", [esc, write])))


def test_ice_blocks_out_of_scope_tools():
    rogue = Packet("FORGE", "escalate", {"reason": "x"}, "R8", "x")
    assert any(r["rule"] == "SCOPE" for r in ice.blocking(ice.check(bare_plan("unconfirmed", [rogue]))))


def test_twin_catches_infeasible_calls():
    bad = Packet("FORGE", "mes.reschedule", {"production_order_id": "PO-0001", "new_date": "2027-03-10"}, "R3", "x")
    r = twin.dry_run("T", [bad])        # PO-0001 was built in the past
    assert not r["ok"] and "already built" in r["errors"][0]["error"]
