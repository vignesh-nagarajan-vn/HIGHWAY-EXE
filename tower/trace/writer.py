"""Per-event trace (the evidence file the judges ask for) and the case-file summary."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from ..intake.llm import LLMUnavailable, ollama_chat, parse_json
from ..intake.prompts import SUMMARY_SYSTEM
from ..kg.paths import path_string, traceroute


def stamp(plan, apply_res: dict | None) -> str:
    c = plan.verdict.category
    if c == "noise":
        return "NO ACTION - NOISE"
    if c == "unconfirmed":
        return "ESCALATED - UNCONFIRMED"
    if apply_res and (apply_res.get("blocked") or apply_res.get("failed")):
        return "ESCALATED - CHECK FAILED"
    if plan.verdict.unresolved:
        return "RESOLVED + ESCALATED"
    return "RESOLVED"


def facts(plan, apply_res: dict | None) -> dict:
    v = plan.verdict
    f = {"event": plan.event["event_id"], "source": plan.event.get("source"), "category": v.category,
         "reason": v.reason, "missing_intel": v.missing_intel,
         "actions": dict(Counter(p.tool for p in plan.packets))}
    incs = []
    for wo in plan.orders:
        i, imp = wo.incident, wo.impact
        d = {"kind": i.kind, "plant": i.plant, "window": [i.start, i.end]}
        if i.kind == "quality_hold":
            d.update(lots=i.lot_ids, part=i.part, vehicles_in_stock=len(imp.vehicles_in_stock),
                     vehicles_sold=len(imp.vehicles_sold), owners=len(imp.owners))
        else:
            moves = [s for s in plan.slot_decisions if s.incident_no == wo.incident_no]
            d.update(part=i.part, shipment=i.shipment_id, restart=i.resume_on,
                     production_orders=len(imp.production_orders), customer_orders=len(imp.customer_orders),
                     dealers=len(imp.dealers), rescheduled=sum(s.mode == "reschedule" for s in moves),
                     transferred=sum(s.mode == "transfer" for s in moves))
        incs.append(d)
    f["incidents"] = incs
    if plan.loaner_report:
        f["loaners_granted"] = sum(len(r["granted"]) for r in plan.loaner_report.values())
        f["loaners_waitlisted"] = sum(len(r["waitlisted"]) for r in plan.loaner_report.values())
    return f


def template_summary(f: dict) -> str:
    if f["category"] == "noise":
        return f"Judged noise: {f['reason']}. The tower took no action and called no tools."
    if f["category"] == "unconfirmed":
        return (f"Unconfirmed report: {f['reason']}. The tower escalated it to a human and changed nothing. "
                f"Missing: {', '.join(f['missing_intel'][:3])}.")
    parts = []
    for i in f["incidents"]:
        if i["kind"] == "quality_hold":
            parts.append(f"Quality hold on {', '.join(i['lots'])} ({i['part']} installed at {i['plant']}, built "
                         f"{i['window'][0]} to {i['window'][1]}): lot held, {i['vehicles_in_stock']} unsold vehicles "
                         f"stopped from sale, {i['owners']} owners of sold vehicles contacted.")
        elif i["kind"] == "supplier_delay":
            parts.append(f"Late {i['part']} shipment {i['shipment']} to {i['plant']} (ETA {i['window'][0]} -> "
                         f"{i['window'][1]}): {i['production_orders']} production orders blocked, "
                         f"{i['rescheduled']} rescheduled and {i['transferred']} transferred; "
                         f"{i['customer_orders']} customer orders at {i['dealers']} dealers affected.")
        else:
            parts.append(f"{i['plant']} dark {i['window'][0]} to {i['window'][1]} (restart {i['restart']}): "
                         f"{i['production_orders']} production orders blocked, {i['rescheduled']} rescheduled and "
                         f"{i['transferred']} transferred; {i['customer_orders']} customer orders at "
                         f"{i['dealers']} dealers affected.")
    if "loaners_granted" in f:
        parts.append(f"The tower sent one notice per affected dealer and assigned {f['loaners_granted']} loaners"
                     + (f" ({f['loaners_waitlisted']} entitled customers waitlisted, pools empty)."
                        if f.get("loaners_waitlisted") else "."))
    return " ".join(parts)


def write_summary(f: dict, model: str | None) -> tuple[str, dict]:
    schema = {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]}
    try:
        r = ollama_chat(SUMMARY_SYSTEM, "FACTS: " + json.dumps(f), schema=schema, model=model,
                        num_predict=220, timeout=120)
        try:
            text = str(parse_json(r.text).get("summary", "")).strip()
        except ValueError:
            text = ""
        # guardrail: a summary must be short and must not invent numbers absent from the facts
        nums = set(re.findall(r"\d+", text))
        known = set(re.findall(r"\d+", json.dumps(f)))
        if text and len(text) < 700 and nums <= known:
            return text, {"model": r.model, "tokens_in": r.tokens_in, "tokens_out": r.tokens_out,
                          "latency_ms": r.latency_ms}
    except LLMUnavailable:
        pass
    return template_summary(f), {"model": "template"}


def build_trace(plan, verification: dict | None, apply_res: dict | None, summary: str, summary_meta: dict,
                timings: dict) -> dict:
    v = plan.verdict
    incidents = []
    for wo in plan.orders:
        imp = wo.impact
        incidents.append({
            "no": wo.incident_no, "incident": wo.incident.to_dict(),
            "graph_path": path_string(imp), "traceroute": traceroute(imp),
            "hops": [{"cls": h.cls, "rel": h.rel, "count": len(h.ids), "ids": h.ids[:40], "note": h.note}
                     for h in imp.hops],
            "impact": {k: getattr(imp, k) for k in ("production_orders", "customer_orders", "dealers",
                                                     "vehicles_in_stock", "vehicles_sold", "owners", "models")},
        })
    tokens_in = sum(r.tokens_in for r in plan.readings) + summary_meta.get("tokens_in", 0)
    tokens_out = sum(r.tokens_out for r in plan.readings) + summary_meta.get("tokens_out", 0)
    return {
        "event": plan.event,
        "stamp": stamp(plan, apply_res),
        "summary": summary,
        "reason": v.reason,
        "verdict": {"category": v.category, "agreement": v.agreement, "readers": v.readers,
                    "missing_intel": v.missing_intel,
                    "unresolved": [i.to_dict() for i in v.unresolved]},
        "readings": [r.model_dump() for r in plan.readings],
        "grounding": v.per_reader,
        "incidents": incidents,
        "slot_decisions": [d.to_dict() for d in plan.slot_decisions],
        "loaner_report": plan.loaner_report,
        "packets": [p.to_dict() for p in plan.packets],
        "verification": verification,
        "apply": apply_res,
        "radio": plan.radio.lines,
        "metrics": {"llm_calls": sum(1 for r in plan.readings if r.reader in ("slm", "haiku"))
                    + (1 if summary_meta.get("model") not in (None, "template") else 0),
                    "validator_called": plan.validator_called, "tokens_in": tokens_in, "tokens_out": tokens_out,
                    "reader_model": next((r.model for r in plan.readings if r.reader == "slm"), None),
                    "summary_model": summary_meta.get("model"), **timings},
    }


def write_trace(out_dir: Path, trace: dict) -> Path:
    d = out_dir / "traces"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{trace['event']['event_id']}.json"
    p.write_text(json.dumps(trace, indent=1, default=str), encoding="utf-8")
    return p


def case_files_md(traces: list[dict]) -> str:
    out = ["# HIGHWAY.EXE case files", ""]
    for t in traces:
        e = t["event"]
        out += [f"## {e['event_id']} - {t['stamp']}", "", f"> {e['text']}", "", f"**Summary.** {t['summary']}", "",
                f"**Why.** {t['reason']} (readers: {t['verdict']['agreement']}, {', '.join(t['verdict']['readers'])})", ""]
        if t["verdict"]["missing_intel"]:
            out += [f"**Missing intel.** {'; '.join(t['verdict']['missing_intel'])}", ""]
        for inc in t["incidents"]:
            out += [f"**Graph path #{inc['no']}.** `{inc['graph_path']}`", "", "```", *inc["traceroute"], "```", ""]
        acts = Counter(p["tool"] for p in t["packets"])
        if acts:
            out += ["**Actions.** " + ", ".join(f"{k} x{v}" for k, v in sorted(acts.items())), ""]
        else:
            out += ["**Actions.** none", ""]
    return "\n".join(out)
