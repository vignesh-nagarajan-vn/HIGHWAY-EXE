"""Backend for the HIGHWAY.EXE control-tower UI.

    python -m tower.api            # serves the API and, if built, the UI on http://127.0.0.1:8765

GET  /api/world             plants, models, dealers, suppliers, calendar, baseline schedule, ontology stats
GET  /api/runs              recorded runs (anything under runs/ with traces)
GET  /api/run/{name}        run summary + every trace + audit (REPLAY mode)
POST /api/live              start a live run against the enterprise server (LIVE mode)
GET  /api/live/stream       server-sent events: one trace per event as the tower finishes it
"""
from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..config import ROOT, RUNS_DIR, settings
from ..data import world
from ..ground import calendar as cal
from ..kg import kg
from ..kg.ontology import CLASSES, RELATIONS

app = FastAPI(title="HIGHWAY.EXE")
UI_DIST = ROOT / "ui" / "dist"


@app.get("/api/world")
def get_world() -> dict:
    w = world()
    days = [cal.date_of(i).isoformat() for i in range(0, cal.last_index() + 1)]
    schedule = [{"po": po, "plant": r["plant_id"], "date": r["build_date"], "model": r["model"],
                 "cos": len(w.cos_by_po.get(po, []))}
                for po, r in sorted(w.production_orders.items()) if r["build_date"] >= days[0]]
    return {
        "today": cal.today().isoformat(), "days": days,
        "plants": [{"id": p, "name": w.plants[p]["name"], "city": w.plants[p]["city"], "slots": w.slots(p),
                    "models": sorted(w.plant_models[p])} for p in w.plant_order],
        "dealers": [{"id": d, "name": r["name"], "city": r["city"], "region": r["region"],
                     "loaners": w.loaners.get(d, 0)} for d, r in sorted(w.dealers.items())],
        "suppliers": [{"id": s, "name": r["name"], "city": r["city"]} for s, r in sorted(w.suppliers.items())],
        "models": sorted(w.models), "schedule": schedule, "kg": kg().stats(),
        "ontology": {"classes": CLASSES, "relations": {k: list(v) for k, v in RELATIONS.items()}},
        "settings": {"reader": settings().ollama_model, "validator": settings().anthropic_model},
    }


def _run_dirs() -> list[Path]:
    return sorted((p for p in RUNS_DIR.glob("*") if (p / "traces").is_dir()), key=lambda p: p.stat().st_mtime,
                  reverse=True)


@app.get("/api/runs")
def get_runs() -> list[dict]:
    out = []
    for p in _run_dirs():
        s = p / "run_summary.json"
        out.append({"name": p.name, "summary": json.loads(s.read_text(encoding="utf-8")) if s.exists() else None,
                    "events": len(list((p / "traces").glob("E-*.json")))})
    return out


@app.get("/api/run/{name}")
def get_run(name: str) -> dict:
    p = RUNS_DIR / name
    if not (p / "traces").is_dir() or p.resolve().parent != RUNS_DIR.resolve():
        raise HTTPException(404, "no such run")
    traces = [json.loads(t.read_text(encoding="utf-8")) for t in sorted((p / "traces").glob("E-*.json"))]
    read = lambda f: json.loads((p / f).read_text(encoding="utf-8")) if (p / f).exists() else None
    return {"name": name, "summary": read("run_summary.json"), "audit": read("audit.json"), "traces": traces}


class LiveRequest(BaseModel):
    out: str = "live"
    server: str | None = None


_live: dict = {"thread": None, "traces": [], "done": False, "error": None}


@app.post("/api/live")
def start_live(req: LiveRequest) -> dict:
    if _live["thread"] and _live["thread"].is_alive():
        raise HTTPException(409, "a live run is already in progress")
    from ..run import run

    _live.update(traces=[], done=False, error=None)
    out = RUNS_DIR / req.out

    def work():
        try:
            out.mkdir(parents=True, exist_ok=True)
            run(req.server or settings().enterprise_url, out, on_event=_live["traces"].append)
        except BaseException as e:   # SystemExit when the server is down
            _live["error"] = str(e)
        finally:
            _live["done"] = True

    _live["thread"] = threading.Thread(target=work, daemon=True)
    _live["thread"].start()
    return {"started": True, "out": str(out)}


@app.get("/api/live/stream")
async def live_stream() -> StreamingResponse:
    async def gen():
        sent = 0
        while True:
            while sent < len(_live["traces"]):
                yield f"event: trace\ndata: {json.dumps(_live['traces'][sent], default=str)}\n\n"
                sent += 1
            if _live["done"]:
                yield f"event: done\ndata: {json.dumps({'error': _live['error']})}\n\n"
                return
            await asyncio.sleep(0.4)
    return StreamingResponse(gen(), media_type="text/event-stream")


if UI_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=UI_DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = UI_DIST / path
        return FileResponse(f if path and f.is_file() else UI_DIST / "index.html")
