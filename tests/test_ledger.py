from tower.data import world
from tower.policy.ledger import Block, Ledger
from tower.policy.rules import AGENT_TOOLS, RULES


def test_ledger_mirrors_future_schedule():
    led = Ledger(world())
    assert len(led.loc) == 360                     # 6 plants x 20 days x 3 orders
    assert led.free("P_TX", 0) == 2


def test_blocks_and_moves():
    led = Ledger(world())
    led.blocks.append(Block("P_TX", 9, 11, None, "outage"))
    po = next(p for p, (pl, i) in led.loc.items() if pl == "P_TX" and i == 9)
    assert not led.feasible(po, "P_TX", 10)        # inside the outage
    assert led.feasible(po, "P_TX", 11)
    led.move(po, "P_TX", 11)
    assert led.free("P_TX", 11) == 1 and led.free("P_TX", 9) == 3


def test_rules_and_scopes_complete():
    assert set(RULES) == {f"R{i}" for i in range(1, 11)}
    tools = set().union(*AGENT_TOOLS.values())
    from tower.vendor import TOOLS
    assert tools == set(TOOLS)                     # every enterprise tool has exactly one owner
