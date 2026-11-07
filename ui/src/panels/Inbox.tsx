import type { Trace } from "../types";
import { Win } from "./Win";

export function Inbox({ traces, revealedPerEvent, onSelect }: {
  traces: Trace[]; revealedPerEvent: number[]; onSelect: (i: number) => void;
}) {
  const cards = traces.flatMap((t, ev) =>
    (t.apply?.calls ?? []).slice(0, revealedPerEvent[ev] ?? 0)
      .filter((c) => c.tool === "escalate")
      .map((c, i) => ({ ev, t, reason: String(c.args.reason), key: `${t.event.event_id}:${i}` })));
  return (
    <Win title="HUMAN-IN-THE-LOOP" tag={`${cards.length} TICKET${cards.length === 1 ? "" : "S"}`} alarm={cards.length > 0}>
      {cards.length === 0 && <div className="dim">no escalations yet. the tower only calls a human when a report is unconfirmed or cannot be grounded.</div>}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {cards.map(({ ev, t, reason, key }) => (
          <button key={key} onClick={() => onSelect(ev)} style={{
            textAlign: "left", border: 0, cursor: "pointer", background: "#1a0b3a", padding: "6px 8px",
            boxShadow: "inset 0 0 0 2px var(--amber)" }}>
            <div className="px amber" style={{ fontSize: 9 }}>TICKET {t.event.event_id} // {t.event.source.toUpperCase()}</div>
            <div style={{ fontSize: 17, margin: "4px 0" }}>"{t.event.text}"</div>
            <div className="dim" style={{ fontSize: 16 }}>{reason}</div>
            {t.verdict.missing_intel.length > 0 && (
              <div style={{ marginTop: 4 }}>
                {t.verdict.missing_intel.map((m) => <div key={m} style={{ fontSize: 16 }}><span className="amber">[ ]</span> {m}</div>)}
              </div>
            )}
          </button>
        ))}
      </div>
    </Win>
  );
}
