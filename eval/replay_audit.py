"""Replay auditor: replays an action_log.jsonl on a fresh copy of the organisers' world (the way
the judges score it) and checks the final state against the handbook, recomputing every
expected set with the independent SQL implementation.

    python -m eval.replay_audit runs/final
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from tower.config import DATA_DIR
from tower.data import world
from tower.policy.rules import LOANER_TIERS, TIER_RANK
from tower.vendor import WRITE_TOOLS, Enterprise, ToolError
from tower.verify import crosscheck

# planning-time sanity numbers (from the read-only data analysis); used only here, never at runtime
SANITY = {"E-11": {"moved": 9, "transfers": 3}, "E-09": {"moved": 6, "transfers": 2},
          "E-12": {"moved": 3}, "E-04": {"moved": 9}, "E-08": {"moved": 6}, "E-10": {"moved": 3},
          "E-01": {"moved": 14}}


def expected_sets(trace: dict) -> dict:
    """Recompute what the final state must look like from the grounded incidents, via SQL."""
    exp = {"pos": set(), "cos": set(), "lots": set(), "stock": set(), "owners": set()}
    for inc in trace["incidents"]:
        i = inc["incident"]
        if i["kind"] == "supplier_delay":
            s = crosscheck.delay_sets(i["shipment_id"], i["end"])
        elif i["kind"] == "plant_outage":
            s = crosscheck.outage_sets(i["plant"], i["start"], i["end"])
        else:
            s = crosscheck.lot_sets(i["lot_ids"])
            exp["lots"] |= set(i["lot_ids"])
            exp["stock"] |= set(s["vehicles_in_stock"])
            exp["owners"] |= set(s["owners"])
            continue
        exp["pos"] |= set(s["production_orders"])
        exp["cos"] |= set(s["customer_orders"])
    return exp


def audit(run_dir: Path) -> dict:
    w = world()
    log = [json.loads(l) for l in (run_dir / "action_log.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    traces = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (run_dir / "traces").glob("E-*.json")}
    ent = Enterprise(str(DATA_DIR))
    by_event = defaultdict(list)
    for rec in log:
        by_event[rec["event_id"]].append(rec)
    rows, problems = [], []
    for eid in sorted(set(by_event) | set(traces)):
        recs = by_event.get(eid, [])
        replay_err = []
        for r in recs:
            try:
                ent.call(eid, r["tool"], r["args"])
            except ToolError as e:
                replay_err.append(str(e))
        s = ent.state(eid)
        t = traces.get(eid)
        cat = t["verdict"]["category"] if t else "?"
        writes = [r for r in recs if r["tool"] in WRITE_TOOLS]
        esc = [r for r in recs if r["tool"] == "escalate"]
        moved = {po for po, loc in s["loc"].items() if loc != (ent.orders[po]["plant_id"], ent.orders[po]["idx"])}
        transfers = {po for po in moved if s["loc"][po][0] != ent.orders[po]["plant_id"]}
        checks = {"no_failed_calls": not any(not r["ok"] for r in recs) and not replay_err}
        if cat == "noise":
            checks["noise_untouched"] = not recs
        elif cat == "unconfirmed":
            checks["rumor_escalated_only"] = not writes and len(esc) == 1
        elif t:
            exp = expected_sets(t)
            notified = {c for d, cs in s["notified"].items() for c in cs}
            want_by_dealer = defaultdict(set)
            for c in exp["cos"]:
                want_by_dealer[w.customer_orders[c]["dealer_id"]].add(c)
            notes = Counter(r["args"]["dealer_id"] for r in writes if r["tool"] == "dealer.notify")
            checks["moved_exactly_affected"] = moved == exp["pos"]
            checks["dealers_told_exact_orders"] = notified == exp["cos"] and dict(s["notified"]) == dict(want_by_dealer)
            checks["one_notice_per_dealer"] = all(n == 1 for n in notes.values())
            tier = lambda c: w.customers[w.customer_orders[c]["customer_id"]]["tier"]
            loan_ok = all(c in exp["cos"] and tier(c) in LOANER_TIERS for c in s["loaned"])
            for dealer in want_by_dealer:
                ent_list = sorted((c for c in want_by_dealer[dealer] if tier(c) in LOANER_TIERS),
                                  key=lambda c: (TIER_RANK[tier(c)], w.customer_orders[c]["promised_date"], c))
                k = min(len(ent_list), w.loaners.get(dealer, 0))
                if set(ent_list[:k]) != {c for c in s["loaned"] if w.customer_orders[c]["dealer_id"] == dealer}:
                    loan_ok = False
            checks["loaners_by_priority_and_pool"] = loan_ok
            checks["lots_held"] = s["held"] == exp["lots"]
            checks["unsold_stopped"] = s["stopped"] == exp["stock"]
            checks["owners_contacted"] = s["customers"] == exp["owners"]
            kinds = {r["tool"] for r in writes}
            checks["three_action_kinds"] = len(kinds) >= 3
            for key, val in SANITY.get(eid, {}).items():
                got = len(moved) if key == "moved" else len(transfers)
                checks[f"sanity_{key}={val}"] = got == val
        bad = [k for k, v in checks.items() if not v]
        problems += [f"{eid}: {k}" for k in bad]
        rows.append({"event": eid, "category": cat, "calls": len(recs), "writes": len(writes),
                     "moved": len(moved), "transfers": len(transfers), "notified_dealers": len(s["notified"]),
                     "loaners": len(s["loaned"]), "held": sorted(s["held"]), "stopped": len(s["stopped"]),
                     "owners": len(s["customers"]), "escalated": s["escalated"], "checks": checks, "pass": not bad})
    report = {"events": len(rows), "passed": sum(r["pass"] for r in rows), "calls": len(log),
              "failed_calls": sum(not r["ok"] for r in log), "problems": problems, "rows": rows}
    (run_dir / "audit.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report


def main() -> None:
    run_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "runs/final")
    r = audit(run_dir)
    print(f"{'event':<6}{'category':<13}{'calls':>6}{'writes':>7}{'moved':>6}{'xfer':>5}{'dealers':>8}"
          f"{'loaners':>8}{'stopped':>8}{'owners':>7}  result")
    for x in r["rows"]:
        print(f"{x['event']:<6}{x['category']:<13}{x['calls']:>6}{x['writes']:>7}{x['moved']:>6}{x['transfers']:>5}"
              f"{x['notified_dealers']:>8}{x['loaners']:>8}{x['stopped']:>8}{x['owners']:>7}  "
              f"{'PASS' if x['pass'] else 'FAIL ' + ','.join(k for k, v in x['checks'].items() if not v)}")
    print(f"\n{r['passed']}/{r['events']} events pass | {r['calls']} calls | {r['failed_calls']} failed")
    sys.exit(0 if not r["problems"] else 1)


if __name__ == "__main__":
    main()
