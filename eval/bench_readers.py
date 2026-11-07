"""Reader benchmark: which reader (and which small model) grounds events correctly?

Each reader's output goes through the same graph judge, and the grounded result is compared
with the ground truth (category + kind, plant, shipment/lot, window for every incident).

    python -m eval.bench_readers --synth eval/out/synth.json --models qwen3:4b,llama3.2:3b --limit 60
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from tower.data import load_events
from tower.ground.judge import ground_reading
from tower.intake import grammar_reader, haiku_validator, slm_reader


def key(i: dict) -> tuple:
    return (i["kind"], i["plant"], i.get("shipment_id"), tuple(i.get("lot_ids") or []), i["start"], i["end"])


def grounded_truth(reading) -> dict:
    cat, incs = ground_reading(reading)
    acts = [i for i in incs if i.actionable]
    if cat == "operational" and not acts:
        cat = "unconfirmed"
    return {"category": cat, "incidents": sorted(key(i.to_dict()) for i in acts)}


def score(events: list[dict], read) -> dict:
    ok, lat, tin, tout, errors, misses = 0, [], 0, 0, 0, []
    for e in events:
        r = read(e)
        if r.error:
            errors += 1
        lat.append(r.latency_ms)
        tin += r.tokens_in
        tout += r.tokens_out
        got = grounded_truth(r)
        want = {"category": e["truth"]["category"], "incidents": sorted(key(i) for i in e["truth"]["incidents"])}
        if got == want:
            ok += 1
        else:
            misses.append({"event": e["event_id"], "text": e["text"][:160], "want": want, "got": got})
    n = len(events)
    return {"n": n, "accuracy": round(ok / n, 4) if n else 0, "errors": errors,
            "p50_ms": int(statistics.median(lat)) if lat else 0, "tokens_in": tin, "tokens_out": tout,
            "misses": misses[:10]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--synth", default="eval/out/synth.json")
    ap.add_argument("--models", default="qwen3:4b,llama3.2:3b,qwen2.5:7b-instruct")
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--haiku", action="store_true", help="also score the Haiku validator as a reader")
    ap.add_argument("--out", default="eval/out/bench.json")
    a = ap.parse_args()
    events = json.loads(Path(a.synth).read_text(encoding="utf-8"))[: a.limit]
    results = {"grammar": score(events, grammar_reader.read)}
    print(f"grammar      acc={results['grammar']['accuracy']:.3f}")
    for m in [x for x in a.models.split(",") if x]:
        results[m] = score(events, lambda e, m=m: slm_reader.read(e, m))
        r = results[m]
        print(f"{m:<20} acc={r['accuracy']:.3f} p50={r['p50_ms']}ms tokens={r['tokens_in']}+{r['tokens_out']} "
              f"errors={r['errors']}", flush=True)
    if a.haiku and haiku_validator.available():
        results["haiku"] = score(events, haiku_validator.read)
        print(f"haiku        acc={results['haiku']['accuracy']:.3f}")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
