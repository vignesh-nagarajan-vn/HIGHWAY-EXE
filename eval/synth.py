"""Synthetic messy events with known ground truth, sampled from the knowledge graph.

Ground truth comes from the tables (a real shipment, a real lot, a real plant and window), and
the text is rendered with nicknames, relative dates, digests, rumors and noise. With
--paraphrase, Claude Haiku rewrites each message in a different voice (facts preserved), so the
readers are tested on wording no template produced.

    python -m eval.synth --n 120 --out eval/out/synth.json [--paraphrase]
"""
from __future__ import annotations

import argparse
import json
import random
from datetime import date, timedelta
from pathlib import Path

from tower.data import world
from tower.ground import calendar as cal

WD = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def phrase(d: date, rng: random.Random, allow_relative: bool = True) -> str:
    t = cal.today()
    week = (cal.monday_of(d) - cal.monday_of(t)).days // 7
    opts = [d.isoformat(), f"{WD[d.weekday()]} {MON[d.month - 1]} {d.day}", f"{MON[d.month - 1]} {d.day}"]
    if allow_relative and week == 1:
        opts += [f"next {WD[d.weekday()]}"] * 2
    if allow_relative and week == -1:
        opts += [f"last {WD[d.weekday()]}"] * 2
    return rng.choice(opts)


def names(kind: str, eid: str, rng: random.Random) -> str:
    w = world()
    al = [r["alias"] for r in w.aliases if r["entity_type"] == kind and r["entity_id"] == eid]
    if kind == "plant":
        al += [eid, w.plants[eid]["name"]]
    if kind == "part":
        al += [w.parts[eid]["name"]]
    if kind == "supplier":
        al += [w.suppliers[eid]["name"]]
    return rng.choice(al)


def delay(rng: random.Random) -> tuple[str, dict]:
    w = world()
    sh = rng.choice([s for s in w.shipments.values() if "2027-03-08" <= s["eta_date"] <= "2027-03-29"])
    eta = date.fromisoformat(sh["eta_date"])
    new = eta
    for _ in range(rng.randint(1, 4)):
        new = cal.next_workday(new)
    sup, part, plant = (names("supplier", sh["supplier_id"], rng), names("part", sh["part_id"], rng),
                        names("plant", sh["plant_id"], rng))
    o, n = phrase(eta, rng), phrase(new, rng)
    tpl = rng.choice([
        f"Heads up from {sup}: the {part} run for {plant} can't make it {o}. Carrier says {n} now.",
        f"{plant} line is waiting on {part} from {sup}. Original drop was {o}, new ETA is {n}.",
        f"Subject: shipment {sh['shipment_id']} late\n{sup} reports the {part} load for {plant} due {o} "
        f"will now arrive {n} (port congestion).",
        f"FYI {sup} says the {part} delivery to {plant} slips from {o} to {n}.",
    ])
    truth = {"kind": "supplier_delay", "plant": sh["plant_id"], "shipment_id": sh["shipment_id"], "lot_ids": [],
             "start": sh["eta_date"], "end": new.isoformat()}
    return tpl, truth


def outage(rng: random.Random) -> tuple[str, dict]:
    w = world()
    p = rng.choice(list(w.plants))
    s = cal.date_of(rng.randint(1, 16))
    e = s
    for _ in range(rng.randint(0, 3)):
        e = cal.next_workday(e)
    plant = names("plant", p, rng)
    a, b = phrase(s, rng), phrase(e, rng)
    tpl = rng.choice([
        f"{plant} update: a power failure. We're dark from {a} through {b}; the line restarts the following working day.",
        f"Plant operations alert: {plant} lost production to a flood. Production is stopped from {a} through {b} inclusive.",
        f"{plant} has a software outage on the line, no builds {a} to {b}.",
    ])
    truth = {"kind": "plant_outage", "plant": p, "shipment_id": None, "lot_ids": [], "start": s.isoformat(),
             "end": e.isoformat()}
    return tpl, truth


def quality(rng: random.Random) -> tuple[str, dict]:
    w = world()
    lot = rng.choice(list(w.lots.values()))
    a, b = date.fromisoformat(lot["first_build_date"]), date.fromisoformat(lot["last_build_date"])
    sup, part, plant = (names("supplier", lot["supplier_id"], rng), names("part", lot["part_id"], rng),
                        names("plant", lot["plant_id"], rng))
    fa, fb = phrase(a, rng), phrase(b, rng)
    tpl = rng.choice([
        f"Quality alert: {sup} says the {part} sent to {plant} had a faulty weld. Anything built {fa} through {fb} is suspect.",
        f"QUALITY BULLETIN: Lot {lot['lot_id']} ({lot['part_id']}, supplier {lot['supplier_id']}) installed at "
        f"{lot['plant_id']} on vehicles built {a.isoformat()} to {b.isoformat()} has a defect. Hold the lot.",
        f"{sup} flagged contamination in {part} shipped to {plant}; vehicles built {fa} to {fb} are suspect.",
    ])
    truth = {"kind": "quality_hold", "plant": lot["plant_id"], "shipment_id": None, "lot_ids": [lot["lot_id"]],
             "start": lot["first_build_date"], "end": lot["last_build_date"]}
    return tpl, truth


NOISE = ["Dealer {c} asks where to find the new brochure PDF.",
         "Reminder: the spring price list goes out to dealers on Friday.",
         "Weather service: heavy snow expected in {c} this weekend.",
         "The cafeteria at headquarters is closed for renovation next week.",
         "Marketing wants photos of the new {m} for the auto show."]
RUMOR = ["Rumor from a supplier rep: something may be off with a {cat} part coming up. No dates, no details.",
         "Someone on the floor mentioned a possible shortage of something {cat} sometime soon. Not confirmed.",
         "Heard {cat} supplies might get tight, nobody has confirmed anything."]


def sample(rng: random.Random, i: int) -> dict:
    w = world()
    r = rng.random()
    if r < 0.25:
        text, truth = delay(rng); cat, incs = "operational", [truth]
    elif r < 0.45:
        text, truth = outage(rng); cat, incs = "operational", [truth]
    elif r < 0.65:
        text, truth = quality(rng); cat, incs = "operational", [truth]
    elif r < 0.75:
        (t1, a), (t2, b) = delay(rng), outage(rng)
        text, cat, incs = f"Morning digest, two items. (1) {t2} (2) {t1}", "operational", [b, a]
    elif r < 0.88:
        city = rng.choice(list(w.dealers.values()))["city"]
        text = rng.choice(NOISE).format(c=city, m=rng.choice(list(w.models)).title()); cat, incs = "noise", []
    else:
        text = rng.choice(RUMOR).format(cat=rng.choice(["electronic", "seating", "tire", "wiring"]))
        cat, incs = "unconfirmed", []
    return {"event_id": f"S-{i:03d}", "source": "synthetic", "text": text, "truth": {"category": cat, "incidents": incs}}


def paraphrase(events: list[dict]) -> list[dict]:
    """Ask Haiku to rewrite each message in a new human voice, keeping every fact."""
    import anthropic
    from tower.config import settings
    client = anthropic.Anthropic(api_key=settings().anthropic_key)
    out = []
    for e in events:
        r = client.messages.create(
            model=settings().anthropic_model, max_tokens=400, output_config={"effort": "low"},
            system="Rewrite the operations message in a different, natural human voice (chat, email or alert). "
                   "Keep EVERY name, id and date phrase exactly as written. Do not add facts. Reply with the message only.",
            messages=[{"role": "user", "content": e["text"]}])
        text = next((b.text for b in r.content if b.type == "text"), e["text"]).strip()
        out.append({**e, "text": text, "template_text": e["text"]})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--seed", type=int, default=2027)
    ap.add_argument("--out", default="eval/out/synth.json")
    ap.add_argument("--paraphrase", action="store_true")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    events = [sample(rng, i) for i in range(1, a.n + 1)]
    if a.paraphrase:
        events = paraphrase(events)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(events, indent=1), encoding="utf-8")
    print(f"wrote {len(events)} synthetic events to {a.out}")


if __name__ == "__main__":
    main()
