"""Drive the HIGHWAY.EXE static replay with Playwright and record the demo footage.

Needs the static UI on :4173 (`vite preview ui --port 4173`, the `tower-static` launch config)
and video/out/durations.json from tts.py. Writes video/out/raw.webm and video/out/timeline.json.
"""
import json
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

HERE = Path(__file__).parent
OUT = HERE / "out"
URL = "http://localhost:4173"
PAD = 0.45      # silence after each narration clip
TAIL = 1.2      # hold on the end card
W, H = 1920, 1080

END_CARD = """
<h1>HIGHWAY<b>.EXE</b></h1>
<div class="row">
  <div class="st g"><b>15/15</b><span>EVENTS PASS AUDIT</span></div>
  <div class="st"><b>879</b><span>TOOL CALLS</span></div>
  <div class="st g"><b>0</b><span>FAILED</span></div>
  <div class="st m"><b>61.6s</b><span>ON A LAPTOP</span></div>
</div>
<p>the model reads. code decides. every action carries its own proof.</p>
<div class="url">highway-exe.netlify.app</div>
"""

HOOK_CARD = """
<h2>ONE LATE CHIP SHIPMENT</h2>
<div class="row">
  <div class="st m"><b>8</b><span>BUILDS BLOCKED</span></div>
  <div class="st"><b>67</b><span>ORDERS SLIPPING</span></div>
  <div class="st"><b>29</b><span>DEALERS WAITING</span></div>
</div>
<p>Wacky Wheels Co. runs just-in-time. Who fixes it?</p>
"""


def select(pg: Page, ev: str) -> None:
    pg.locator("button.tx-item").filter(has=pg.locator(".id", has_text=ev)).first.dispatch_event("click")


def tab(pg: Page, name: str) -> None:
    pg.get_by_role("tab", name=name).dispatch_event("click")


def js(pg: Page, code: str) -> None:
    pg.evaluate(code)


# Each scene is a list of (fraction of scene length, action).
def scenes(cap: dict[str, str]):
    return {
        "hook": [
            (0.0, lambda pg: js(pg, f"V.card({json.dumps(HOOK_CARD)})")),
            (0.97, lambda pg: js(pg, "V.uncard()")),
        ],
        "problem": [
            (0.0, lambda pg: pg.keyboard.press("Enter")),
            (0.03, lambda pg: js(pg, f"V.caption({json.dumps(cap['problem'])}, '01 // THE PROBLEM')")),
            (0.12, lambda pg: js(pg, "V.spotlight('INCOMING TRANSMISSIONS'); V.zoom('INCOMING TRANSMISSIONS', 1.7, -120)")),
        ],
        "read": [
            (0.0, lambda pg: (js(pg, "V.clear()"), select(pg, "E-01"))),
            (0.02, lambda pg: js(pg, f"V.caption({json.dumps(cap['read'])}, '02 // READ')")),
            (0.05, lambda pg: js(pg, "V.spotlight('ICE'); V.zoom('ICE', 2.1)")),
            (0.45, lambda pg: js(pg, "V.unzoom(); V.spotlight('CREW'); V.zoom('CREW', 1.5, -90)")),
        ],
        "ground": [
            (0.0, lambda pg: (js(pg, "V.clear()"), tab(pg, "NETRUN"))),
            (0.02, lambda pg: js(pg, f"V.caption({json.dumps(cap['ground'])}, '03 // GROUND')")),
            (0.06, lambda pg: js(pg, "V.spotlight('NETRUN'); V.zoom('NETRUN', 1.45, 40)")),
        ],
        "prove": [
            (0.0, lambda pg: (js(pg, "V.clear()"), pg.get_by_role("button", name=">>| SKIP").dispatch_event("click"),
                              select(pg, "E-11"), tab(pg, "SLOT GRID"))),
            (0.02, lambda pg: js(pg, f"V.caption({json.dumps(cap['prove'])}, '04 // PROVE')")),
            (0.06, lambda pg: js(pg, "V.spotlight('SLOT GRID'); V.zoom('SLOT GRID', 1.4, 40)")),
            (0.5, lambda pg: js(pg, "V.unzoom(); V.spotlight('ICE'); V.zoom('ICE', 2.1)")),
        ],
        "escalate": [
            (0.0, lambda pg: (js(pg, "V.clear()"), select(pg, "E-02"), tab(pg, "CASE FILE"))),
            (0.02, lambda pg: js(pg, f"V.caption({json.dumps(cap['escalate'])}, '05 // FAIL CLOSED')")),
            (0.05, lambda pg: js(pg, "V.spotlight('THE HIGHWAY')")),
            (0.4, lambda pg: js(pg, "V.spotlight('HUMAN-IN-THE-LOOP'); V.zoom('HUMAN-IN-THE-LOOP', 1.9, 60)")),
        ],
        "results": [
            (0.0, lambda pg: (js(pg, "V.clear()"), select(pg, "E-01"), tab(pg, "CASE FILE"))),
            (0.02, lambda pg: js(pg, f"V.caption({json.dumps(cap['results'])}, '06 // RESULTS')")),
            (0.04, lambda pg: js(pg, "V.spotlight('CASE FILE'); V.zoom('CASE FILE', 1.35, 0)")),
            (0.42, lambda pg: js(pg, f"V.hideCaption(); V.clear(); V.card({json.dumps(END_CARD)})")),
        ],
    }


def main() -> None:
    durs = {d["id"]: d["seconds"] for d in json.loads((OUT / "durations.json").read_text())}
    script = json.loads((HERE / "script.json").read_text(encoding="utf-8"))
    cap = {s["id"]: s["caption"] for s in script["scenes"]}
    plan = scenes(cap)
    overlay = (HERE / "overlay.js").read_text(encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": W, "height": H}, device_scale_factor=1,
                                  record_video_dir=str(OUT / "rec"), record_video_size={"width": W, "height": H})
        t_video = time.monotonic()
        pg = ctx.new_page()
        pg.goto(URL)
        pg.wait_for_load_state("networkidle")
        pg.evaluate("document.fonts.ready")
        pg.add_script_tag(content=overlay)
        pg.wait_for_timeout(1500)  # let the boot log finish typing
        for _ in range(3):  # three flashes in case the screencast drops one; build.py syncs on the last
            pg.evaluate("V.sync(true)")
            pg.wait_for_timeout(500)
            pg.evaluate("V.sync(false)")  # scene time 0 = first frame after the last green flash
            pg.wait_for_timeout(500)
        pg.wait_for_timeout(500)

        timeline, t0 = [], time.monotonic()  # 1 s after the last flash ended
        start = 0.0
        for sc in script["scenes"]:
            sid = sc["id"]
            length = durs[sid] + PAD + (TAIL if sid == "results" else 0)
            timeline.append({"id": sid, "start": round(start, 3), "seconds": round(length, 3)})
            for frac, act in plan[sid]:
                wait = t0 + start + frac * length - time.monotonic()
                if wait > 0:
                    time.sleep(wait)
                act(pg)
            start += length
        wait = t0 + start - time.monotonic()
        if wait > 0:
            time.sleep(wait)

        offset = t0 - t_video
        video = pg.video
        ctx.close()
        browser.close()
        raw = OUT / "raw.webm"
        raw.unlink(missing_ok=True)
        Path(video.path()).rename(raw)

    (OUT / "timeline.json").write_text(json.dumps({"video_offset": round(offset, 3), "total": round(start, 3),
                                                   "scenes": timeline}, indent=2))
    print(f"recorded {raw} offset={offset:.2f}s total={start:.1f}s")


if __name__ == "__main__":
    main()
