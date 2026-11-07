import { useEffect, useRef, useState } from "react";
import { PORTRAITS, drawSprite } from "../engine/sprites";
import type { EventView } from "../replay";
import type { Trace } from "../types";
import { Win } from "./Win";

const ROLES: Record<string, string> = {
  DISPATCH: "COORDINATOR", FORGE: "SUPPLY CHAIN", AEGIS: "QUALITY", RELAY: "DEALERS + CARE",
};
const COLOR: Record<string, string> = { DISPATCH: "var(--cyan)", FORGE: "var(--amber)", AEGIS: "var(--magenta)", RELAY: "var(--acid)" };

function Portrait({ name, lit }: { name: string; lit: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const c = ref.current!;
    const ctx = c.getContext("2d")!;
    ctx.clearRect(0, 0, 48, 48);
    drawSprite(ctx, PORTRAITS[name], 0, 0, 3, lit ? 1 : 0.55);
  }, [name, lit]);
  return <canvas ref={ref} width={48} height={48}
                 style={{ background: "#0a0320", boxShadow: lit ? `0 0 0 2px ${COLOR[name]}, 0 0 14px ${COLOR[name]}` : "0 0 0 2px #2b1a66" }} />;
}

function Typed({ text, reduced }: { text: string; reduced: boolean }) {
  const [n, setN] = useState(reduced ? text.length : 0);
  useEffect(() => { setN(reduced ? text.length : 0); }, [text, reduced]);
  useEffect(() => {
    if (n >= text.length) return;
    const t = setTimeout(() => setN((x) => Math.min(text.length, x + 3)), 16);
    return () => clearTimeout(t);
  }, [n, text]);
  return <>{text.slice(0, n)}{n < text.length && <span className="blink">_</span>}</>;
}

export function Crew({ trace, view, reduced }: { trace?: Trace; view?: EventView; reduced: boolean }) {
  const lines = trace ? trace.radio.slice(0, view?.status === "done" ? trace.radio.length : view?.radio ?? 0) : [];
  const last = lines[lines.length - 1];
  return (
    <Win title="CREW" tag="1 COORDINATOR + 3 SPECIALISTS" hot={!!last && view?.status === "active"}>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {Object.keys(ROLES).map((name) => {
          const mine = lines.filter((l) => l.agent === name);
          const said = mine[mine.length - 1];
          const speaking = last?.agent === name && view?.status === "active";
          return (
            <div key={name} style={{ display: "grid", gridTemplateColumns: "48px 1fr", gap: 8, alignItems: "start" }}>
              <Portrait name={name} lit={speaking || !!said} />
              <div>
                <div className="px" style={{ fontSize: 8, color: COLOR[name] }}>{name} <span className="dim">// {ROLES[name]}</span></div>
                <div style={{ background: "#0d0430", padding: "4px 6px", marginTop: 3, minHeight: 34, fontSize: 17,
                              boxShadow: speaking ? `inset 0 0 0 1px ${COLOR[name]}` : "inset 0 0 0 1px #2b1a66",
                              color: said?.kind === "warn" ? "var(--amber)" : "var(--text)" }}>
                  {said ? (speaking ? <Typed text={said.text} reduced={reduced} /> : said.text) : <span className="dim">standing by</span>}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </Win>
  );
}
