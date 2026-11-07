"""APPLY - execute verified packets through the MCP enterprise server.

A sync facade over an MCP client session (in-process transport) so the planners can make live
reads during planning and the executor can apply packets in order. Only a plan that passed
ICE, TWIN and CROSSCHECK reaches the write tools; anything else becomes a single escalation.
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from typing import Any

from mcp import Client

from ..agents.base import Radio
from ..policy.ledger import Packet
from ..vendor import WRITE_TOOLS
from .client import EnterpriseHTTP
from .mcp_enterprise import build_server, tool_name


class Executor:
    """Calls enterprise tools via MCP (default) or plain HTTP, and logs every call."""

    def __init__(self, base_url: str | None = None, transport: str = "mcp"):
        self.http = EnterpriseHTTP(base_url)
        self.transport = transport
        self.calls: list[dict] = []
        if transport == "mcp":
            logging.getLogger("httpx").setLevel(logging.WARNING)
            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
            self._thread.start()
            self._ready = threading.Event()
            self._queue: asyncio.Queue | None = None
            self._worker = asyncio.run_coroutine_threadsafe(self._serve(), self._loop)
            if not self._ready.wait(timeout=30):
                raise RuntimeError("MCP client did not start")

    async def _serve(self) -> None:
        """One task owns the MCP session for its whole life (anyio cancel scopes require it)."""
        self._queue = asyncio.Queue()
        async with Client(build_server(self.http)) as client:
            self._client = client
            self._ready.set()
            while True:
                job = await self._queue.get()
                if job is None:
                    return
                make, fut = job
                try:
                    fut.set_result(await make(client))
                except Exception as e:   # surfaced to the caller thread
                    fut.set_exception(e)

    def _submit(self, make) -> Any:
        cf =asyncio.run_coroutine_threadsafe(self._enqueue(make), self._loop)
        return cf.result(timeout=120)

    async def _enqueue(self, make) -> Any:
        fut = self._loop.create_future()
        await self._queue.put((make, fut))
        return await fut

    def close(self) -> None:
        if self.transport == "mcp":
            asyncio.run_coroutine_threadsafe(self._queue.put(None), self._loop).result(timeout=10)
            self._worker.result(timeout=30)
            self._loop.call_soon_threadsafe(self._loop.stop)

    def mcp_tools(self) -> list[str]:
        if self.transport != "mcp":
            return []
        res = self._submit(lambda c: c.list_tools())
        return sorted(t.name for t in res.tools)

    def call(self, event_id: str, tool: str, args: dict, agent: str = "", seq: int | None = None) -> dict:
        t0 = time.perf_counter()
        if self.transport == "mcp":
            res = self._submit(lambda c: c.call_tool(tool_name(tool), {"event_id": event_id, "args": args}))
            out = res.structured_content if getattr(res, "structured_content", None) else None
            if out is None:
                text = next((c.text for c in res.content if getattr(c, "type", "") == "text"), "{}")
                try:
                    out = json.loads(text)
                except ValueError:
                    out = {"ok": False, "error": text}
            if "result" in out and isinstance(out["result"], dict) and "ok" in out["result"] and len(out) == 1:
                out = out["result"]
        else:
            out = self.http.act(event_id, tool, args)
        rec = {"event_id": event_id, "tool": tool, "args": args, "agent": agent, "seq": seq,
               "ok": bool(out.get("ok")), "result": out.get("result"), "error": out.get("error"),
               "ms": int((time.perf_counter() - t0) * 1000), "write": tool in WRITE_TOOLS}
        self.calls.append(rec)
        return rec

    def pool_reader(self, event_id: str):
        def read(dealer: str) -> int | None:
            r = self.call(event_id, "crm.loaner_availability", {"dealer_id": dealer}, agent="RELAY")
            return r["result"]["available"] if r["ok"] else None
        return read


def apply(plan, verification: dict, ex: Executor, radio: Radio) -> dict:
    eid = plan.event["event_id"]
    if not verification["ok"]:
        problems = ([f"{r['rule']}: {r['detail']}" for r in verification["ice"] if not r["ok"] and r["level"] == "error"]
                    + [f"twin: {e['error']}" for e in verification["twin"]["errors"]]
                    + [f"crosscheck #{c['incident']} disagrees" for c in verification["crosscheck"] if not c["agree"]])
        radio.say("DISPATCH", "verification gate failed -> nothing applied, escalating", "warn")
        rec = ex.call(eid, "escalate", {"reason": f"[{eid}] plan blocked by the tower's own checks: "
                                                  f"{'; '.join(problems)[:600]}"}, agent="DISPATCH")
        return {"applied": 0, "failed": 0, "blocked": True, "reads": 0, "calls": [rec]}

    start = len(ex.calls)
    # live confirmation of target days before moving anything (free reads)
    targets = sorted({(p.args.get("to_plant_id") or plan_plant(plan, p), p.args["new_date"])
                      for p in plan.packets if p.tool in ("mes.reschedule", "mes.transfer")})
    short = []
    for plant, day in targets:
        r = ex.call(eid, "mes.get_schedule", {"plant_id": plant, "date": day}, agent="FORGE")
        need = sum(1 for p in plan.packets if p.tool in ("mes.reschedule", "mes.transfer")
                   and (p.args.get("to_plant_id") or plan_plant(plan, p)) == plant and p.args["new_date"] == day)
        if r["ok"] and r["result"]["free_slots"] < need:
            short.append(f"{plant} {day}")
    if short:
        radio.say("FORGE", f"live schedule disagrees with the plan on {short} - moves on those days may fail", "warn")
    elif targets:
        radio.say("FORGE", f"live schedule confirms free slots on {len(targets)} target day(s)")

    failed = []
    for p in plan.packets:
        rec = ex.call(eid, p.tool, p.args, agent=p.agent, seq=p.seq)
        p.proof["applied"] = "ok" if rec["ok"] else f"error: {rec['error']}"
        if not rec["ok"]:
            failed.append((p, rec["error"]))
    if failed:
        radio.say("DISPATCH", f"{len(failed)} call(s) failed on the live system -> escalating", "warn")
        ex.call(eid, "escalate", {"reason": f"[{eid}] {len(failed)} planned call(s) were rejected by the live system: "
                                            + "; ".join(f"{p.tool} {p.args.get('production_order_id', '')}: {e}"
                                                        for p, e in failed)[:600]}, agent="DISPATCH")
    calls = ex.calls[start:]
    applied = sum(1 for c in calls if c["write"] and c["ok"])
    radio.say("DISPATCH", f"applied {applied} write call(s), {len(failed)} failed, "
                          f"{sum(1 for c in calls if not c['write'])} read/escalate call(s)")
    return {"applied": applied, "failed": len(failed), "blocked": False,
            "reads": sum(1 for c in calls if c["tool"] in ("mes.get_schedule", "crm.loaner_availability")),
            "calls": calls}


def plan_plant(plan, p: Packet) -> str:
    po = p.args["production_order_id"]
    return next(d.from_plant for d in plan.slot_decisions if d.production_order_id == po)
