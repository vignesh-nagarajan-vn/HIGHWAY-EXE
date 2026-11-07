import { STATIC } from "../api";
import type { Run, World } from "../types";

interface Props {
  world: World; run: Run | null; runs: string[]; mode: "REPLAY" | "LIVE";
  playing: boolean; speed: number; reduced: boolean; sound: boolean; liveBusy: boolean;
  revealedCalls: number; failedSoFar: number; tokensSoFar: number;
  onRun: (name: string) => void; onPlay: () => void; onRestart: () => void; onSkip: () => void;
  onSpeed: (s: number) => void; onReduced: () => void; onSound: () => void; onLive: () => void;
}

export function Hud(p: Props) {
  const s = p.run?.summary;
  return (
    <header className="hud">
      <div>
        <div className="logo">HIGHWAY<b>.EXE</b></div>
        <div className="sub">WACKY WHEELS CO. // CONTROL TOWER</div>
      </div>
      <div className="stat"><span className="k">SIM CLOCK</span><span className="v">{p.world.today} MON</span></div>
      <div className="stat"><span className="k">READER-A</span><span className="v">{(s?.reader_model ?? p.world.settings.reader).toUpperCase()}</span></div>
      <div className="stat"><span className="k">TOKENS</span><span className="v">{p.tokensSoFar.toLocaleString()}</span></div>
      <div className="stat"><span className="k">VALIDATOR CALLS</span><span className="v">{s ? String(s.validator_calls).padStart(2, "0") : "--"}</span></div>
      <div className="stat"><span className="k">TOOL CALLS</span><span className="v">{String(p.revealedCalls).padStart(3, "0")}</span></div>
      <div className="stat"><span className="k">FAILED CALLS</span>
        <span className={`v ${p.failedSoFar === 0 ? "zero" : ""}`}>{String(p.failedSoFar).padStart(3, "0")}</span></div>
      <div className="grow" />
      <label className="stat">
        <span className="k">RUN</span>
        <select className="pbtn" value={p.run?.name ?? ""} onChange={(e) => p.onRun(e.target.value)} aria-label="Recorded run">
          {p.runs.map((r) => <option key={r} value={r}>{r.toUpperCase()}</option>)}
        </select>
      </label>
      <span className={`chip ${p.mode === "LIVE" ? "mag" : "cyan"}`}>{p.mode}</span>
      <button className="pbtn" onClick={p.onPlay} aria-label={p.playing ? "Pause" : "Play"}>{p.playing ? "|| PAUSE" : "> PLAY"}</button>
      <button className="pbtn" onClick={p.onRestart}>{"<< RESTART"}</button>
      <button className="pbtn" onClick={p.onSkip}>{">>| SKIP"}</button>
      {[1, 2, 4].map((x) => (
        <button key={x} className={`pbtn ${p.speed === x ? "on" : ""}`} onClick={() => p.onSpeed(x)}>{x}X</button>
      ))}
      <button className={`pbtn ${p.liveBusy ? "on" : ""}`} onClick={p.onLive} disabled={p.liveBusy || STATIC}
              title={STATIC ? "Hosted replay: LIVE mode runs locally (python -m tower.api)" : "Run the tower live against the enterprise server on :8000"}>
        {p.liveBusy ? "LIVE..." : STATIC ? "LIVE: LOCAL" : "RUN LIVE"}
      </button>
      <button className={`pbtn ${p.reduced ? "on" : ""}`} onClick={p.onReduced} title="Reduce motion">FX {p.reduced ? "OFF" : "ON"}</button>
      <button className={`pbtn ${p.sound ? "on" : ""}`} onClick={p.onSound} title="8-bit sound">SND {p.sound ? "ON" : "OFF"}</button>
    </header>
  );
}
