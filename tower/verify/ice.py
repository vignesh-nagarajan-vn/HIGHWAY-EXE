"""ICE - the policy firewall. One executable check per handbook rule, run on the whole plan
before the twin and before any real call. A failing check blocks the event."""
from __future__ import annotations

from collections import Counter, defaultdict

from ..data import world
from ..policy.rules import AGENT_TOOLS, LOANER_TIERS, TIER_RANK
from ..vendor import WRITE_TOOLS


def _res(rule: str, ok: bool, detail: str, level: str = "error") -> dict:
    return {"rule": rule, "ok": ok, "detail": detail, "level": "pass" if ok else level}


def check(plan) -> list[dict]:
    w = world()
    v = plan.verdict
    P = plan.packets
    out: list[dict] = []
    bad_scope = [f"{p.agent}:{p.tool}" for p in P if p.tool not in AGENT_TOOLS.get(p.agent, set())]
    out.append(_res("SCOPE", not bad_scope, "every tool call made by the agent that owns it"
                    if not bad_scope else f"out-of-scope calls: {bad_scope[:3]}"))
    writes = [p for p in P if p.tool in WRITE_TOOLS]
    if v.category == "noise":
        out.append(_res("R7", not P, "noise: zero calls" if not P else f"{len(P)} calls on noise"))
        return out
    if v.category == "unconfirmed":
        esc = [p for p in P if p.tool == "escalate"]
        ok = not writes and len(esc) == 1
        out.append(_res("R8", ok, "unconfirmed: exactly one escalate, zero writes" if ok
                        else f"{len(writes)} writes / {len(esc)} escalations on an unconfirmed report"))
        return out

    supply = [wo for wo in plan.orders if wo.incident.kind != "quality_hold"]
    quality = [wo for wo in plan.orders if wo.incident.kind == "quality_hold"]

    # R1/R2/R3: exactly the affected orders move, each once, to a legal slot
    affected = {po for wo in supply for po in wo.impact.production_orders}
    moves = [p for p in P if p.tool in ("mes.reschedule", "mes.transfer")]
    moved = Counter(p.args["production_order_id"] for p in moves)
    stuck = {d.production_order_id for d in plan.slot_decisions if d.mode == "unplaceable"}
    extra = set(moved) - affected
    missing = affected - set(moved) - stuck
    dup = [po for po, n in moved.items() if n > 1]
    out.append(_res("R1/R2", not extra and not missing,
                    f"{len(moved)} of {len(affected)} affected orders moved, none unaffected" if not extra and not missing
                    else f"unaffected moved: {sorted(extra)[:3]}, affected not moved: {sorted(missing)[:3]}"))
    illegal = []
    resume = {}
    for wo in supply:
        for po in wo.impact.production_orders:
            resume.setdefault(po, wo.incident.resume_on)
    for d in plan.slot_decisions:
        if d.mode == "reschedule" and d.to_date < resume[d.production_order_id]:
            illegal.append(f"{d.production_order_id} before restart")
        if d.mode == "transfer" and d.model not in w.plant_models[d.to_plant]:
            illegal.append(f"{d.production_order_id} to a plant that cannot build {d.model}")
    out.append(_res("R3", not illegal and not dup, "every move is on/after restart or a legal transfer"
                    if not illegal and not dup else f"{(illegal + dup)[:3]}"))

    # R4: one notice per dealer, exactly its affected customer orders
    want = defaultdict(set)
    for wo in supply:
        for co in wo.impact.customer_orders:
            want[w.customer_orders[co]["dealer_id"]].add(co)
    notes = [p for p in P if p.tool == "dealer.notify"]
    per = Counter(p.args["dealer_id"] for p in notes)
    got = {p.args["dealer_id"]: set(p.args["customer_order_ids"]) for p in notes}
    ok4 = all(n == 1 for n in per.values()) and got == dict(want)
    out.append(_res("R4", ok4, f"{len(notes)} notices for {len(want)} dealers, exact order lists" if ok4
                    else "dealer notices do not match affected customer orders"))

    # R5: loaners only to entitled customers, by priority, within pool
    loans = [p.args["customer_order_id"] for p in P if p.tool == "crm.assign_loaner"]
    tier = lambda co: w.customers[w.customer_orders[co]["customer_id"]]["tier"]
    bad = [c for c in loans if c not in {c for s in want.values() for c in s} or tier(c) not in LOANER_TIERS]
    prio_ok = True
    for dealer, r in plan.loaner_report.items():
        key = lambda c: (TIER_RANK[tier(c)], w.customer_orders[c]["promised_date"], c)
        ranked = sorted(r["entitled"], key=key)
        k = len(r["granted"])
        if r["granted"] != ranked[:k] or k > r["pool"] or (r["waitlisted"] and k < r["pool"]):
            prio_ok = False
    out.append(_res("R5", not bad and prio_ok, f"{len(loans)} loaners, priority and pools respected"
                    if not bad and prio_ok else f"loaner violations: {bad[:3]} priority_ok={prio_ok}"))

    # R6: quality hold sets match the lot sweep exactly
    if quality:
        held = {p.args["lot_id"] for p in P if p.tool == "quality.hold_lot"}
        lots = {l for wo in quality for l in wo.incident.lot_ids}
        stops = {v for p in P if p.tool == "dealer.stop_sale" for v in p.args["vins"]}
        stock = {v for wo in quality for v in wo.impact.vehicles_in_stock}
        told = {p.args["customer_id"] for p in P if p.tool == "crm.notify_customer"}
        owners = {c for wo in quality for c in wo.impact.owners}
        ok6 = held == lots and stops == stock and told == owners
        out.append(_res("R6", ok6, f"hold {len(held)} lot, stop {len(stops)} vehicles, contact {len(told)} owners"
                        if ok6 else "quality actions do not match the lot sweep"))

    # R9: at least three kinds of action per real incident
    weak = []
    for wo in plan.orders:
        kinds = {p.tool for p in writes if p.incident == wo.incident_no}
        if len(kinds) < 3:
            weak.append(f"#{wo.incident_no}: {sorted(kinds)}")
    out.append(_res("R9", not weak, "each incident uses 3+ kinds of action" if not weak
                    else f"fewer than 3 action kinds (no eligible customers?): {weak}", level="warn"))

    # R10: nothing duplicated
    sig = Counter((p.tool, repr(sorted(p.args.items()))) for p in writes)
    dups = [k for k, n in sig.items() if n > 1]
    out.append(_res("R10", not dups, "no duplicate or extra writes" if not dups else f"duplicates: {dups[:2]}"))
    return out


def blocking(results: list[dict]) -> list[dict]:
    return [r for r in results if not r["ok"] and r["level"] == "error"]
