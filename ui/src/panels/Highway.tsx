/* THE HIGHWAY: every incoming event drives in as a pixel vehicle. Delays are cargo trucks,
   outages ride on a power-down factory rig, quality holds are hazard-striped cars, compound
   digests are road trains, rumors are ghost cars that pull into the HUMAN lane, and noise is an
   ad blimp that drifts past without stopping. Vehicles park under the tower checkpoint while
   the agents work, then exit stamped. */
import { useEffect, useRef } from "react";
import type { EventView } from "../replay";
import type { Trace } from "../types";
import { BLIMP, FACTORY_RIG, GHOST_CAR, HAZARD_CAR, TRAILER, TRUCK, drawSprite, rng, spriteSize } from "../engine/sprites";
import { Win } from "./Win";

type Kind = "delay" | "outage" | "quality" | "compound" | "rumor" | "noise";
interface Car { ev: number; kind: Kind; x: number; y: number; vx: number; label: string; parked: number; done: boolean }

function kindOf(t: Trace): Kind {
  if (t.verdict.category === "noise") return "noise";
  if (t.verdict.category === "unconfirmed") return "rumor";
  if (t.incidents.length > 1) return "compound";
  const k = t.incidents[0]?.incident.kind;
  return k === "plant_outage" ? "outage" : k === "quality_hold" ? "quality" : "delay";
}

const S = 3; // pixel scale

export function Highway({ traces, views, selected, onSelect, speed, reduced }: {
  traces: Trace[]; views: EventView[]; selected: number; onSelect: (i: number) => void; speed: number; reduced: boolean;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const cars = useRef<Map<number, Car>>(new Map());
  const props = useRef({ traces, views, selected, speed, reduced });
  props.current = { traces, views, selected, speed, reduced };

  useEffect(() => { cars.current.clear(); }, [traces]);

  useEffect(() => {
    const cv = canvas.current!;
    const ctx = cv.getContext("2d")!;
    let raf = 0;
    let t = 0;
    const R = rng(77);
    const stars = Array.from({ length: 70 }, () => ({ x: R(), y: R() * 0.45, b: R() }));
    const far = Array.from({ length: 60 }, () => ({ w: 14 + Math.floor(R() * 26), h: 30 + Math.floor(R() * 40) }));
    const near = Array.from({ length: 40 }, () => ({ w: 22 + Math.floor(R() * 34), h: 40 + Math.floor(R() * 52), sign: R() < 0.22 }));
    const signs = ["WACKY", "NEON", "24/7", "JIT", "EXE", "VOLT", "TOWER"];

    const frame = () => {
      const { traces, views, selected, speed, reduced } = props.current;
      const W = cv.clientWidth, H = cv.clientHeight;
      if (cv.width !== W || cv.height !== H) { cv.width = W; cv.height = H; }
      ctx.imageSmoothingEnabled = false;
      t += reduced ? 0 : 1;
      const road = H - 64, human = H - 22, check = Math.round(W * 0.34);

      // sky
      const g = ctx.createLinearGradient(0, 0, 0, road);
      g.addColorStop(0, "#090120"); g.addColorStop(1, "#2a0b4f");
      ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
      for (const s of stars) {
        ctx.fillStyle = (Math.floor(t / 20 + s.b * 10) % 7 === 0) ? "#ffffff" : "#6a5fb0";
        ctx.fillRect(Math.floor(s.x * W), Math.floor(s.y * H), 2, 2);
      }
      ctx.fillStyle = "#ff2a6d"; ctx.fillRect(W - 90, 18, 26, 26);   // pixel moon
      ctx.fillStyle = "#090120"; ctx.fillRect(W - 82, 14, 26, 26);

      // skylines (parallax)
      let x = -((t * 0.15) % 600);
      for (let i = 0; x < W; i = (i + 1) % far.length) {
        const b = far[i]; ctx.fillStyle = "#1a0b45"; ctx.fillRect(Math.floor(x), road - b.h - 18, b.w, b.h + 18); x += b.w + 2;
      }
      x = -((t * 0.4) % 900);
      for (let i = 0; x < W; i = (i + 1) % near.length) {
        const b = near[i];
        const top = road - b.h;
        ctx.fillStyle = "#12063a"; ctx.fillRect(Math.floor(x), top, b.w, b.h);
        for (let wy = top + 6; wy < road - 6; wy += 8)
          for (let wx = 4; wx < b.w - 4; wx += 7)
            if ((wx * 7 + wy * 13 + i) % 5 === 0) { ctx.fillStyle = (wx + wy + i) % 3 ? "#f9c80e" : "#05d9e8"; ctx.fillRect(Math.floor(x) + wx, wy, 3, 3); }
        if (b.sign) {
          ctx.font = "8px 'Press Start 2P'"; ctx.fillStyle = (Math.floor(t / 30) + i) % 9 === 0 ? "#40102a" : "#ff2a6d";
          ctx.fillText(signs[i % signs.length], Math.floor(x) + 3, top - 4);
        }
        x += b.w + 6;
      }

      // road + lanes
      ctx.fillStyle = "#0c0322"; ctx.fillRect(0, road - 6, W, H - road + 6);
      ctx.fillStyle = "#05d9e8"; ctx.fillRect(0, road - 6, W, 2);
      ctx.fillStyle = "#3d2a85"; ctx.fillRect(0, human - 16, W, 2);
      ctx.fillStyle = "#f9c80e";
      for (let dx = -((t * 2) % 40); dx < W; dx += 40) ctx.fillRect(Math.floor(dx), road + 18, 18, 3);
      ctx.font = "7px 'Press Start 2P'"; ctx.fillStyle = "#b967ff";
      ctx.fillText("HUMAN REVIEW LANE  >>  escalate()", 8, human + 14);

      // tower checkpoint gantry
      ctx.fillStyle = "#3d2a85";
      ctx.fillRect(check - 34, road - 70, 6, 76); ctx.fillRect(check + 46, road - 70, 6, 76); ctx.fillRect(check - 34, road - 74, 86, 8);
      ctx.font = "7px 'Press Start 2P'"; ctx.fillStyle = "#05d9e8"; ctx.fillText("TOWER CHECKPOINT", check - 34, road - 78);
      const busy = views.some((v) => v.status === "active" && v.phase !== "arrive");
      if (busy) {
        const by = road - 66 + ((t * 2) % 64);
        ctx.fillStyle = "rgba(57,255,20,0.35)"; ctx.fillRect(check - 28, by, 74, 3);
        ctx.fillStyle = "rgba(5,217,232,0.08)"; ctx.fillRect(check - 28, road - 66, 74, 70);
      }

      // vehicles
      const humanBay = 18;
      let rumorsParked = 0;
      traces.forEach((tr, i) => {
        const v = views[i];
        if (!v || v.status === "queued") { cars.current.delete(i); return; }
        const kind = kindOf(tr);
        let c = cars.current.get(i);
        if (!c) {
          c = { ev: i, kind, x: W + 40, y: kind === "noise" ? 26 + (i % 3) * 14 : road - 2, vx: 0,
                label: tr.event.event_id, parked: 0, done: false };
          cars.current.set(i, c);
        }
        const sp = (reduced ? 50 : 4) * speed;
        let target: number;
        let ty = c.y;
        if (kind === "noise") target = -160;
        else if (kind === "rumor" && (v.gate || v.status === "done")) { target = humanBay + rumorsParked * 70; ty = human - 6; rumorsParked++; }
        else if (v.status === "done") target = -200;
        else target = check - 10;
        const dx = target - c.x;
        c.x += Math.sign(dx) * Math.min(Math.abs(dx), sp);
        c.y += Math.sign(ty - c.y) * Math.min(Math.abs(ty - c.y), 2 * speed);
        const sprite = kind === "delay" || kind === "compound" ? TRUCK : kind === "outage" ? FACTORY_RIG
          : kind === "quality" ? HAZARD_CAR : kind === "rumor" ? GHOST_CAR : BLIMP;
        const { h } = spriteSize(sprite, S);
        const bob = v.status === "active" && Math.abs(dx) < 1 && !reduced ? (Math.floor(t / 8) % 2) : 0;
        const y = c.y - h + bob;
        drawSprite(ctx, sprite, c.x, y, S, kind === "rumor" ? 0.7 : 1, true);
        if (kind === "compound") {
          const tw = spriteSize(TRUCK, S).w;
          drawSprite(ctx, TRAILER, c.x + tw + 2, y + (spriteSize(TRUCK, S).h - spriteSize(TRAILER, S).h), S);
          drawSprite(ctx, TRAILER, c.x + tw + 2 + spriteSize(TRAILER, S).w + 2, y + (spriteSize(TRUCK, S).h - spriteSize(TRAILER, S).h), S);
        }
        ctx.font = "8px 'Press Start 2P'";
        ctx.fillStyle = i === selected ? "#f9c80e" : "#e9e6ff";
        ctx.fillText(c.label, c.x, y - 6);
        if (v.stamped && kind !== "noise") {
          ctx.fillStyle = tr.stamp.startsWith("RESOLVED") ? "#39ff14" : "#f9c80e";
          ctx.fillText(tr.stamp.startsWith("RESOLVED") ? "OK" : "!", c.x + 52, y - 6);
        }
        if (i === selected) { ctx.strokeStyle = "#f9c80e"; ctx.setLineDash([4, 3]); ctx.strokeRect(c.x - 4, y - 16, spriteSize(sprite, S).w + 8, h + 20); ctx.setLineDash([]); }
      });
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, []);

  const click = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    const px = e.clientX - r.left, py = e.clientY - r.top;
    let best = -1, bestD = 1e9;
    cars.current.forEach((c) => {
      const d = Math.abs(px - (c.x + 36)) + Math.abs(py - (c.y - 18)) * 1.5;
      if (d < bestD) { bestD = d; best = c.ev; }
    });
    if (best >= 0 && bestD < 90) onSelect(best);
  };

  return (
    <Win title="THE HIGHWAY" tag="EVENT LANE" hot={views.some((v) => v.status === "active")}>
      <canvas ref={canvas} onClick={click} style={{ width: "100%", height: "100%", display: "block", cursor: "pointer" }}
              aria-label="Highway: each event is a vehicle; click one to open its case" />
    </Win>
  );
}
