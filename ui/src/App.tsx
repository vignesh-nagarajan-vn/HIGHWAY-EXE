import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import { blip } from "./engine/audio";
import { useReplay } from "./replay";
import type { Run, Trace, World } from "./types";
import { Boot } from "./panels/Boot";
import { CaseFile } from "./panels/CaseFile";
import { Crew } from "./panels/Crew";
import { Highway } from "./panels/Highway";
import { Hud } from "./panels/Hud";
import { Ice } from "./panels/Ice";
import { Inbox } from "./panels/Inbox";
import { Netrun } from "./panels/Netrun";
import { PacketLog } from "./panels/PacketLog";
import { SlotGrid } from "./panels/SlotGrid";
import { Transmissions } from "./panels/Transmissions";
import { Win } from "./panels/Win";

type Tab = "NETRUN" | "SLOT GRID" | "CASE FILE";

export function App() {
  const [world, setWorld] = useState<World | null>(null);
  const [runs, setRuns] = useState<string[]>([]);
  const [run, setRun] = useState<Run | null>(null);
  const [booted, setBooted] = useState(false);
  const [selected, setSelected] = useState(0);
  const [follow, setFollow] = useState(true);
  const [tab, setTab] = useState<Tab>("NETRUN");
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

  useEffect(() => { if (booted && traces.length && mode === "REPLAY") R.restart(); }, [booted, run?.name]);
  useEffect(() => { if (mode === "LIVE") R.setPlaying(true); }, [traces.length, mode]);
  useEffect(() => { if (follow && R.active >= 0) setSelected(R.active); }, [R.active, follow]);

  const perEvent = useMemo(() => traces.map((_, i) => R.views[i]?.calls ?? 0), [traces, R.views]);
  const revealed = useMemo(() => traces.flatMap((t, i) => (t.apply?.calls ?? []).slice(0, perEvent[i])), [traces, perEvent]);
  const tokens = traces.reduce((s, t, i) => s + (R.views[i]?.status !== "queued" ? t.metrics.tokens_in + t.metrics.tokens_out : 0), 0);

  // 8-bit sound cues
  const prev = useRef({ calls: 0, stamped: 0, active: -1 });
  useEffect(() => {
    const stamped = R.views.filter((v) => v.stamped).length;
    if (revealed.length > prev.current.calls) blip("packet", sound);
    if (stamped > prev.current.stamped) blip(traces[R.active]?.verdict.category === "unconfirmed" ? "alert" : "stamp", sound);
    if (R.active !== prev.current.active && R.active >= 0) blip("arrive", sound);
    prev.current = { calls: revealed.length, stamped, active: R.active };
  }, [revealed.length, R.views, R.active, sound]);

  const startLive = async () => {
    setLiveBusy(true);
    setMode("LIVE");
    setFollow(true);
    setRun({ name: "live", summary: null, audit: null, traces: [] });
    try {
      await api.startLive("live");
    } catch (e) {
      setErr(String(e)); setLiveBusy(false); return;
    }
    api.liveStream((t) => setRun((r) => (r ? { ...r, traces: [...r.traces, t] } : r)), (e) => {
      setLiveBusy(false);
      if (e) setErr(e);
      api.run("live").then(setRun).catch(() => undefined);
      api.runs().then((rs) => setRuns(rs.map((r) => r.name)));
    });
  };

  if (!booted) return <div className="crt"><Boot world={world} onStart={() => setBooted(true)} />{err && <div className="boot">{err}</div>}</div>;
  if (!world) return null;
  const sel = traces[selected];
  const selView = R.views[selected];
  const pick = (i: number) => { setFollow(false); setSelected(i); };

  return (
    <div className={`crt ${reduced ? "reduced" : ""}`}>
      <div className="app">
        <Hud world={world} run={run} runs={runs} mode={mode} playing={R.playing} speed={R.speed} reduced={reduced}
             sound={sound} liveBusy={liveBusy} revealedCalls={revealed.length}
             failedSoFar={revealed.filter((c) => !c.ok).length} tokensSoFar={tokens}
             onRun={(n) => { setMode("REPLAY"); setFollow(true); api.run(n).then(setRun); }}
             onPlay={() => R.setPlaying(!R.playing)} onRestart={() => { setFollow(true); R.restart(); }}
             onSkip={R.finishAll} onSpeed={R.setSpeed} onReduced={() => setReduced(!reduced)}
             onSound={() => setSound(!sound)} onLive={startLive} />
        <Highway traces={traces} views={R.views} selected={selected} speed={R.speed} reduced={reduced} onSelect={pick} />
        <div className="mid">
          <Transmissions traces={traces} views={R.views} selected={selected} active={R.active} onSelect={pick} />
          <section className="win" style={{ minHeight: 0 }}>
            <div className="titlebar">
              <span>{tab}</span><span className="tag">{sel?.event.event_id ?? ""}</span><span className="spacer" />
              {!follow && <button className="pbtn" onClick={() => setFollow(true)}>FOLLOW LIVE</button>}
              <span className="btns" aria-hidden><i /><i /><i /></span>
            </div>
            <div className="tabs" role="tablist">
              {(["NETRUN", "SLOT GRID", "CASE FILE"] as Tab[]).map((t) => (
                <button key={t} role="tab" aria-selected={tab === t} className={`pbtn ${tab === t ? "on" : ""}`} onClick={() => setTab(t)}>{t}</button>
              ))}
            </div>
            <div className="body">
              {!sel || selView?.status === "queued" ? <div className="dim">awaiting transmission...</div>
                : tab === "NETRUN" ? <Netrun trace={sel} reduced={reduced} live={mode === "LIVE"} />
                : tab === "SLOT GRID" ? <SlotGrid world={world} trace={sel} show={!!selView?.gate} />
                : <CaseFile trace={sel} runName={run?.name ?? ""} />}
            </div>
          </section>
          <div className="col">
            <Crew trace={sel} view={selView} reduced={reduced} />
            <Ice trace={sel} view={selView} />
          </div>
        </div>
        <div className="bottom">
          <PacketLog traces={traces} revealedPerEvent={perEvent} onSelect={pick} />
          <Inbox traces={traces} revealedPerEvent={perEvent} onSelect={pick} />
        </div>
      </div>
      {err && booted && <div className="chip fail" style={{ position: "fixed", bottom: 12, left: 12, zIndex: 999 }} onClick={() => setErr(null)}>{err}</div>}
    </div>
  );
}
