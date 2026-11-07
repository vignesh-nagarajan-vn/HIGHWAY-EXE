"""Freeze the UI's read-only API into static JSON for a hosted replay (Vercel).

    python -m tower.api.export_static            # exports runs/final
    python -m tower.api.export_static final dev  # or any recorded runs

Writes ui/public/data/{world.json, runs.json, run/<name>.json}. The UI reads these files when it is
built with `npm run build:static`; LIVE mode stays local because it needs Ollama and the enterprise server.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from ..config import ROOT, RUNS_DIR
from .server import get_run, get_world

OUT = ROOT / "ui" / "public" / "data"


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, separators=(",", ":"), default=str), encoding="utf-8")
    print(f"{path.relative_to(ROOT)}  {path.stat().st_size / 1024:,.0f} KB")


def main(names: list[str]) -> None:
    _write(OUT / "world.json", get_world())
    runs = []
    for name in names:
        run = get_run(name)
        _write(OUT / "run" / f"{name}.json", run)
        runs.append({"name": name, "summary": run["summary"], "events": len(run["traces"])})
    _write(OUT / "runs.json", runs)


if __name__ == "__main__":
    names = sys.argv[1:] or ["final"]
    missing = [n for n in names if not (RUNS_DIR / n / "traces").is_dir()]
    if missing:
        sys.exit(f"no recorded run: {', '.join(missing)}")
    main(names)
