import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { useReplay } from "./replay";
import type { Run, Trace, World } from "./types";
import { Boot } from "./panels/Boot";
import { Hud } from "./panels/Hud";
import { Transmissions } from "./panels/Transmissions";
import { Win } from "./panels/Win";

export function App() {
  const [world, setWorld] = useState<World | null>(null);
  const [runs, setRuns] = useState<string[]>([]);
  const [run, setRun] = useState<Run | null>(null);
  const [booted, setBooted] = useState(false);
  const [selected, setSelected] = useState(0);
  const [follow, setFollow] = useState(true);
  const [mode, setMode] = useState<"REPLAY" | "LIVE">("REPLAY");
  const [liveBusy, setLiveBusy] = useState(false);
  const [reduced, setReduced] = useState(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [sound, setSound] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.world().then(setWorld).catch((e) => setErr(String(e)));
    api.runs().then((rs) => {
      const names = rs.map((r) => r.name);
      setRuns(names);
      const pick = names.includes("final") ? "final" : names[0];
      if (pick) api.run(pick).then(setRun);
    }).catch((e) => setErr(String(e)));
  }, []);

  const traces: Trace[] = run?.traces ?? [];
  const R = useReplay(traces);

  useEffect(() => { if (booted && traces.length) R.restart(); }, [booted, run?.name]);
  useEffect(() => { if (follow && R.active >= 0) setSelected(R.active); }, [R.active, follow]);

  const revealed = useMemo(() => traces.flatMap((t, i) => (t.apply?.calls ?? []).slice(0, R.views[i]?.calls ?? 0)),
                           [traces, R.views]);
  const tokens = traces.reduce((s, t, i) => s + (R.views[i]?.status !== "queued" ? t.metrics.tokens_in + t.metrics.tokens_out : 0), 0);

  const startLive = async () => {
    setLiveBusy(true);
    setMode("LIVE");
    const live: Run = { name: "live", summary: null, audit: null, traces: [] };
    setRun(live);
    await api.startLive("live");
    api.liveStream((t) => setRun((r) => (r ? { ...r, traces: [...r.traces, t] } : r)), () => {
      setLiveBusy(false);
      api.run("live").then(setRun).catch(() => undefined);
    });
  };

  if (!booted) return <div className="crt"><Boot world={world} onStart={() => setBooted(true)} />{err && <div className="boot">{err}</div>}</div>;
  if (!world) return null;
  const sel = traces[selected];

  return (
    <div className={`crt ${reduced ? "reduced" : ""}`}>
      <div className="app">
        <Hud world={world} run={run} runs={runs} mode={mode} playing={R.playing} speed={R.speed} reduced={reduced}
             sound={sound} liveBusy={liveBusy} revealedCalls={revealed.length}
             failedSoFar={revealed.filter((c) => !c.ok).length} tokensSoFar={tokens}
             onRun={(n) => { setMode("REPLAY"); api.run(n).then(setRun); }}
             onPlay={() => R.setPlaying(!R.playing)} onRestart={() => { setFollow(true); R.restart(); }}
             onSkip={R.finishAll} onSpeed={R.setSpeed} onReduced={() => setReduced(!reduced)}
             onSound={() => setSound(!sound)} onLive={startLive} />
        <Win title="THE HIGHWAY" tag="EVENT LANE"><div className="dim">highway lane loading...</div></Win>
        <div className="mid">
          <Transmissions traces={traces} views={R.views} selected={selected} active={R.active}
                         onSelect={(i) => { setFollow(false); setSelected(i); }} />
          <Win title="NETRUN" tag={sel?.event.event_id}><div className="dim">graph view</div></Win>
          <div className="col"><Win title="CREW"><div className="dim">agents</div></Win></div>
        </div>
        <div className="bottom">
          <Win title="PACKET LOG"><div className="term">{revealed.length} calls</div></Win>
          <Win title="HUMAN-IN-THE-LOOP"><div className="dim">inbox</div></Win>
        </div>
      </div>
    </div>
  );
}
