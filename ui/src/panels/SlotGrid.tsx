/* SLOT GRID: 6 plants x 20 working days x 5 build slots. Disrupted days get hazard stripes,
   vacated slots glitch red, and each move lands as a lit tile with an arc from where it came
   from (cyan = same-plant reschedule, magenta = cross-plant transfer). Hover a tile for its reason. */
import { useMemo } from "react";
import type { Trace, World } from "../types";

const CW = 44, CH = 34, LW = 74, HH = 34;

export function SlotGrid({ world, trace, show }: { world: World; trace?: Trace; show: boolean }) {
  const days = world.days;
  const plants = world.plants.map((p) => p.id);
  const col = (d: string) => days.indexOf(d);
  const row = (p: string) => plants.indexOf(p);

  const { cells, moves, blocks } = useMemo(() => {
    const cells = new Map<string, { po: string; model: string; state: "base" | "out" | "in-r" | "in-t"; why?: string }[]>();
    const key = (p: string, d: string) => `${p}|${d}`;
    for (const r of world.schedule) {
      const k = key(r.plant, r.date);
      if (!cells.has(k)) cells.set(k, []);
      cells.get(k)!.push({ po: r.po, model: r.model, state: "base" });
    }
    const moves = show && trace ? trace.slot_decisions.filter((d) => d.to_date) : [];
    for (const m of moves) {
      const src = cells.get(key(m.from_plant, m.from_date));
      const s = src?.find((x) => x.po === m.production_order_id);
      if (s) { s.state = "out"; s.why = m.reason; }
      const k = key(m.to_plant!, m.to_date!);
      if (!cells.has(k)) cells.set(k, []);
      cells.get(k)!.push({ po: m.production_order_id, model: m.model, state: m.mode === "transfer" ? "in-t" : "in-r", why: m.reason });
    }
    const blocks: { plant: string; lo: number; hi: number; label: string }[] = [];
    if (show && trace) {
      for (const inc of trace.incidents) {
        const i = inc.incident;
        if (i.kind === "quality_hold") continue;
        const end = i.kind === "plant_outage" ? i.end : days[Math.max(0, col(i.resume_on!) - 1)];
        const lo = Math.max(0, col(i.start) >= 0 ? col(i.start) : 0);
        const hi = col(end) >= 0 ? col(end) : days.length - 1;
        blocks.push({ plant: i.plant, lo, hi, label: i.kind === "plant_outage" ? "DARK" : `${i.part} SHORT` });
      }
    }
    return { cells, moves, blocks };
  }, [world, trace, show]);

  const cx = (c: number) => LW + c * CW;
  const cy = (r: number) => HH + r * CH;
  const W = LW + days.length * CW, H = HH + plants.length * CH;

  return (
    <div style={{ overflow: "auto", height: "100%" }}>
      <div style={{ position: "relative", width: W, height: H + 40 }}>
        {days.map((d, c) => (
          <div key={d} className="px" style={{ position: "absolute", left: cx(c), top: 2, width: CW, fontSize: 7, textAlign: "center",
                                                color: c === 0 ? "var(--amber)" : "var(--dim)" }}>
            {d.slice(5)}<br />{"MTWTF"[c % 5]}
          </div>
        ))}
        {plants.map((p, r) => (
          <div key={p} className="px" style={{ position: "absolute", left: 4, top: cy(r) + 10, fontSize: 9, color: "var(--cyan)" }}>{p}</div>
        ))}
        {blocks.map((b, i) => (
          <div key={i} title={b.label} style={{
            position: "absolute", left: cx(b.lo), top: cy(row(b.plant)), width: (b.hi - b.lo + 1) * CW, height: CH,
            background: "repeating-linear-gradient(45deg, rgba(249,200,14,0.28) 0 6px, transparent 6px 12px)",
            boxShadow: "inset 0 0 0 2px var(--amber)" }}>
            <span className="px" style={{ fontSize: 6, color: "var(--amber)", position: "absolute", top: -9, left: 2 }}>{b.label}</span>
          </div>
        ))}
        {plants.map((p, r) => days.map((d, c) => {
          const list = cells.get(`${p}|${d}`) ?? [];
          return (
            <div key={`${p}${d}`} style={{ position: "absolute", left: cx(c) + 2, top: cy(r) + 4, width: CW - 4, height: CH - 8,
                                            display: "flex", gap: 2, padding: 2, background: "#0d0430", boxShadow: "inset 0 0 0 1px #24145a" }}>
              {Array.from({ length: 5 }).map((_, s) => {
                const t = list[s];
                const bg = !t ? "transparent" : t.state === "base" ? "#3d2a85" : t.state === "out" ? "transparent"
                  : t.state === "in-r" ? "var(--cyan)" : "var(--magenta)";
                return (
                  <i key={s} title={t ? `${t.po} ${t.model}${t.why ? "\n" + t.why : ""}` : "free slot"} style={{
                    flex: 1, display: "block", background: bg,
                    boxShadow: !t ? "inset 0 0 0 1px #2b1a66" : t.state === "out" ? "inset 0 0 0 2px var(--red)"
                      : t.state.startsWith("in") ? `0 0 6px ${t.state === "in-r" ? "var(--cyan)" : "var(--magenta)"}` : "none" }} />
                );
              })}
            </div>
          );
        }))}
        <svg width={W} height={H} style={{ position: "absolute", left: 0, top: 0, pointerEvents: "none" }}>
          {moves.map((m, i) => {
            const x1 = cx(col(m.from_date)) + CW / 2, y1 = cy(row(m.from_plant)) + CH / 2;
            const x2 = cx(col(m.to_date!)) + CW / 2, y2 = cy(row(m.to_plant!)) + CH / 2;
            const mx = (x1 + x2) / 2, my = Math.min(y1, y2) - 26 - (i % 4) * 6;
            const color = m.mode === "transfer" ? "#ff2a6d" : "#05d9e8";
            return <path key={i} d={`M${x1},${y1} Q${mx},${my} ${x2},${y2}`} fill="none" stroke={color} strokeWidth={2}
                         strokeDasharray="6 4" style={{ animation: "dash 1.2s linear infinite" }} />;
          })}
        </svg>
        <div className="dim" style={{ position: "absolute", top: H + 8, left: 4, fontSize: 16 }}>
          <span className="neon-c">■</span> rescheduled same plant &nbsp; <span className="neon-m">■</span> transferred &nbsp;
          <span style={{ color: "var(--red)" }}>□</span> vacated &nbsp; <span className="amber">▨</span> disrupted &nbsp;
          {trace && show && !trace.slot_decisions.length && <span className="amber">this event moves no production orders</span>}
        </div>
      </div>
      <style>{"@keyframes dash { to { stroke-dashoffset: -20 } }"}</style>
    </div>
  );
}
