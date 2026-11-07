"""Run the control tower over the event feed.

    python vendor/hack_the_highway_package/enterprise_server.py --data vendor/hack_the_highway_package/data \
        --out runs/final --port 8000
    python -m tower.run --out runs/final

Writes traces/E-XX.json, case_files.md and run_summary.json next to the server's action_log.jsonl.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .agents.dispatch import plan_event
from .config import settings
from .exec.apply import Executor, apply
from .intake.llm import ollama_available, warmup
from .kg import kg
from .trace.writer import build_trace, case_files_md, facts, template_summary, write_summary, write_trace
from .verify import ice, verify


def run(server: str, out: Path, transport: str = "mcp", model: str | None = None, use_validator: bool = True,
        only: set[str] | None = None, on_event=None, llm_summary: bool = False) -> dict:
    model = model or settings().ollama_model
    ex = Executor(server, transport)
    if not ex.http.alive():
        raise SystemExit(f"enterprise server not reachable at {server}")
    t0 = time.perf_counter()
    g = kg()
    if not ollama_available(model):
        print(f"warning: Ollama model {model} not available - READER-A will fail closed", file=sys.stderr)
    else:
        warmup(model)
    events = ex.http.events()
    traces = []
    for e in events:
        if only and e["event_id"] not in only:
            continue
        ts = time.perf_counter()
        first_call = len(ex.calls)
        plan = plan_event(e, slm_model=model, use_validator=use_validator, read_pool=ex.pool_reader(e["event_id"]))
        tp = time.perf_counter()
        if plan.packets:
            ver = verify(plan)
        else:
            ver = {"ok": True, "ice": ice.check(plan), "crosscheck": [], "twin": {"ok": True, "errors": [], "calls": 0}}
        tv = time.perf_counter()
        if plan.packets:
            res = apply(plan, ver, ex, plan.radio)
        else:
            res = {"applied": 0, "failed": 0, "blocked": False, "reads": 0, "calls": []}
        res["calls"] = ex.calls[first_call:]          # include the live reads made while planning
        res["reads"] = sum(1 for c in res["calls"] if c["tool"] in ("mes.get_schedule", "crm.loaner_availability"))
        ta = time.perf_counter()
        f = facts(plan, res)
        if llm_summary:
            summary, smeta = write_summary(f, model)
        else:   # audit summaries are generated from the facts, so every number is exact
            summary, smeta = template_summary(f), {"model": "template"}
        trace = build_trace(plan, ver, res, summary, smeta, {
            "plan_ms": int((tp - ts) * 1000), "verify_ms": int((tv - tp) * 1000), "apply_ms": int((ta - tv) * 1000),
            "total_ms": int((time.perf_counter() - ts) * 1000)})
        write_trace(out, trace)
        traces.append(trace)
        print(f"{e['event_id']:<5} {trace['stamp']:<26} writes={res['applied']:<4} failed={res['failed']} "
              f"readers={plan.verdict.agreement:<9} {trace['metrics']['total_ms']} ms", flush=True)
        if on_event:
            on_event(trace)
    ex.close()
    (out / "case_files.md").write_text(case_files_md(traces), encoding="utf-8")
    calls = [c for t in traces for c in (t["apply"] or {}).get("calls", [])]
    summary = {
        "events": len(traces), "reader_model": model, "validator_model": settings().anthropic_model,
        "validator_calls": sum(t["metrics"]["validator_called"] for t in traces),
        "llm_calls": sum(t["metrics"]["llm_calls"] for t in traces),
        "tokens_in": sum(t["metrics"]["tokens_in"] for t in traces),
        "tokens_out": sum(t["metrics"]["tokens_out"] for t in traces),
        "tool_calls": len(calls),
        "write_calls": sum(c["write"] for c in calls), "failed_calls": sum(not c["ok"] for c in calls),
        "transport": transport, "graph": g.stats(), "seconds": round(time.perf_counter() - t0, 1),
        "stamps": {t["event"]["event_id"]: t["stamp"] for t in traces},
    }
    (out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description="HIGHWAY.EXE control tower")
    ap.add_argument("--server", default=settings().enterprise_url)
    ap.add_argument("--out", default="runs/dev")
    ap.add_argument("--transport", choices=["mcp", "http"], default="mcp")
    ap.add_argument("--model", default=None, help="Ollama model for READER-A (default from OLLAMA_MODEL)")
    ap.add_argument("--no-validator", action="store_true")
    ap.add_argument("--events", default="", help="comma-separated subset, e.g. E-01,E-12")
    ap.add_argument("--llm-summary", action="store_true",
                    help="let the SLM phrase case-file summaries (numbers are checked against the facts)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    s = run(a.server, out, a.transport, a.model, not a.no_validator,
            {x.strip() for x in a.events.split(",") if x.strip()} or None, llm_summary=a.llm_summary)
    print(json.dumps({k: v for k, v in s.items() if k not in ("graph", "stamps")}, indent=2))


if __name__ == "__main__":
    main()
