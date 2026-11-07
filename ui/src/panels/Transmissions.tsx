import type { EventView } from "../replay";
import type { Trace } from "../types";
import { Win, eventBadge } from "./Win";

export function Transmissions({ traces, views, selected, active, onSelect }: {
  traces: Trace[]; views: EventView[]; selected: number; active: number; onSelect: (i: number) => void;
}) {
  return (
    <Win title="INCOMING TRANSMISSIONS" tag={`${views.filter((v) => v.status !== "queued").length}/${traces.length}`}>
      <div className="tx">
        {traces.map((t, i) => {
          const v = views[i];
          const b = eventBadge(t);
          return (
            <button key={t.event.event_id} onClick={() => onSelect(i)}
                    className={`tx-item ${v.status} ${i === selected ? "sel" : ""} ${i === active && v.status === "active" ? "active" : ""}`}>
              <span className="id">{t.event.event_id}</span>
              <span className="src">{t.event.source} {t.event.received_at.slice(11, 16)}</span>
              <span className="txt">{v.status === "queued" ? "[encrypted] " + "░".repeat(24) : t.event.text}</span>
              <span className="badge">
                {v.status !== "queued" && v.phase !== "arrive" && <span className={`chip ${b.cls}`}>{b.label}</span>}{" "}
                {v.stamped && <span className={`chip ${t.stamp.startsWith("RESOLVED") ? "pass" : t.stamp.startsWith("ESC") ? "warn" : ""}`}>{t.stamp}</span>}
              </span>
            </button>
          );
        })}
      </div>
    </Win>
  );
}
