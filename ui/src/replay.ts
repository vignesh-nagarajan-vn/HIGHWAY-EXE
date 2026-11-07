/* The replay engine: turns recorded traces into a timeline of steps (a vehicle arrives, the readers
   report, each agent speaks, the ICE gates light up, packets stream out, the case is stamped) and
   plays it back at a chosen speed. LIVE mode appends traces as the backend finishes them. */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Trace } from "./types";

export type Phase = "arrive" | "read" | "radio" | "gate" | "apply" | "stamp";
export interface Step { ev: number; phase: Phase; ms: number; radio?: number; calls?: number }

const BASE: Record<Phase, number> = { arrive: 1500, read: 900, radio: 420, gate: 900, apply: 160, stamp: 900 };

export function buildSteps(traces: Trace[]): Step[] {
  const steps: Step[] = [];
  traces.forEach((t, ev) => {
    steps.push({ ev, phase: "arrive", ms: BASE.arrive });
    steps.push({ ev, phase: "read", ms: BASE.read });
    t.radio.forEach((_, i) => steps.push({ ev, phase: "radio", ms: BASE.radio, radio: i + 1 }));
    steps.push({ ev, phase: "gate", ms: BASE.gate });
    const calls = t.apply?.calls.length ?? 0;
    const chunk = Math.max(1, Math.ceil(calls / 14));
    for (let c = chunk; c < calls + chunk; c += chunk) {
      steps.push({ ev, phase: "apply", ms: BASE.apply, calls: Math.min(c, calls) });
    }
    steps.push({ ev, phase: "stamp", ms: BASE.stamp });
  });
  return steps;
}

export interface EventView {
  status: "queued" | "active" | "done";
  phase: Phase | null;
  radio: number;   // radio lines revealed
  calls: number;   // tool calls revealed
  gate: boolean;   // ICE panel lit
  stamped: boolean;
}

export function useReplay(traces: Trace[]) {
  const steps = useMemo(() => buildSteps(traces), [traces]);
  const [pos, setPos] = useState(0);           // index of the next step to play
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    if (!playing || pos >= steps.length) {
      if (pos >= steps.length) setPlaying(false);
      return;
    }
    timer.current = window.setTimeout(() => setPos((p) => p + 1), steps[pos].ms / speed);
    return () => { if (timer.current) window.clearTimeout(timer.current); };
  }, [playing, pos, steps, speed]);

  const views: EventView[] = useMemo(() => {
    const v: EventView[] = traces.map(() => ({ status: "queued", phase: null, radio: 0, calls: 0, gate: false, stamped: false }));
    for (let i = 0; i < pos && i < steps.length; i++) {
      const s = steps[i];
      const e = v[s.ev];
      e.status = "active";
      e.phase = s.phase;
      if (s.radio) e.radio = s.radio;
      if (s.phase === "gate") e.gate = true;
      if (s.calls) e.calls = s.calls;
      if (s.phase === "stamp") { e.stamped = true; e.status = "done"; }
    }
    return v;
  }, [pos, steps, traces]);

  const active = pos > 0 && pos <= steps.length ? steps[Math.min(pos, steps.length) - 1].ev : -1;

  const finishAll = useCallback(() => { setPos(steps.length); setPlaying(false); }, [steps.length]);
  const restart = useCallback(() => { setPos(0); setPlaying(true); }, []);
  const jumpTo = useCallback((ev: number) => {
    const end = steps.findIndex((s) => s.ev === ev && s.phase === "stamp");
    if (end >= 0) setPos(end + 1);
  }, [steps]);

  return { steps, pos, playing, setPlaying, speed, setSpeed, views, active, finishAll, restart, jumpTo,
           done: pos >= steps.length && steps.length > 0 };
}
