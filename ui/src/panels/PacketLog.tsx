import { useEffect, useMemo, useRef, useState } from "react";
import type { Call, PacketT, Trace } from "../types";
import { Win } from "./Win";

function brief(c: Call): string {
  const a = c.args;
  switch (c.tool) {
    case "mes.reschedule": return `${a.production_order_id} -> ${a.new_date}`;
    case "mes.transfer": return `${a.production_order_id} -> ${a.to_plant_id} ${a.new_date}`;
    case "mes.get_schedule": return `${a.plant_id} ${a.date} (free ${c.result?.free_slots ?? "?"})`;
    case "dealer.notify": return `${a.dealer_id} [${a.customer_order_ids.length} orders]`;
    case "dealer.stop_sale": return `${a.dealer_id} [${a.vins.length} VINs]`;
    case "crm.loaner_availability": return `${a.dealer_id} (pool ${c.result?.available ?? "?"})`;
    case "crm.assign_loaner": return `${a.customer_order_id}`;
    case "crm.notify_customer": return `${a.customer_id}`;
    case "quality.hold_lot": return `${a.lot_id}`;
    case "escalate": return `"${String(a.reason).slice(0, 70)}..."`;
    default: return JSON.stringify(a).slice(0, 60);
  }
}

export function PacketLog({ traces, revealedPerEvent, onSelect }: {
  traces: Trace[]; revealedPerEvent: number[]; onSelect: (i: number) => void;
}) {
  const [open, setOpen] = useState<string | null>(null);
  const end = useRef<HTMLDivElement>(null);
  const rows = useMemo(() => {
    const out: { ev: number; c: Call; p?: PacketT; key: string }[] = [];
    traces.forEach((t, ev) => {
      const bySeq = new Map(t.packets.map((p) => [p.seq, p]));
      (t.apply?.calls ?? []).slice(0, revealedPerEvent[ev] ?? 0).forEach((c, i) =>
        out.push({ ev, c, p: c.seq != null ? bySeq.get(c.seq) : undefined, key: `${t.event.event_id}:${i}` }));
    });
    return out.slice(-400);
  }, [traces, revealedPerEvent]);
  const total = revealedPerEvent.reduce((a, b) => a + b, 0);
  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [total]);

  return (
    <Win title="PACKET LOG" tag="MCP BUS -> ENTERPRISE" right={<span className="dim" style={{ fontSize: 16 }}>{total} calls</span>}>
      <div className="term">
        {rows.length === 0 && <div className="dim">$ waiting for the first packet_</div>}
        {rows.map(({ ev, c, p, key }) => {
          const cls = c.tool === "escalate" ? "esc" : !c.write ? "rd" : c.ok ? "ok" : "bad";
          return (
            <div key={key}>
              <div className={`ln ${cls}`} onClick={() => { setOpen(open === key ? null : key); onSelect(ev); }}>
                {`${c.event_id} ${c.seq != null ? "#" + String(c.seq).padStart(3, "0") : "    "} ${(c.agent || "-").padEnd(8)} ${c.tool.padEnd(23)} ${brief(c).padEnd(40)} ${(p?.rule ?? (c.write ? "" : "READ")).padEnd(5)} ${c.ok ? "OK" : "ERR " + c.error}`}
              </div>
              {open === key && (
                <div style={{ margin: "2px 0 6px 18px", padding: "4px 8px", background: "#0d0430", boxShadow: "inset 2px 0 0 var(--cyan)", whiteSpace: "pre-wrap" }}>
                  {p ? (<>
                    <div><span className="neon-c">WHY</span> {p.why}</div>
                    <div><span className="neon-c">RULE</span> {p.rule}</div>
                    {p.path && <div><span className="neon-c">PATH</span> {p.path}</div>}
                    <div><span className="neon-c">PROOF</span> ice={p.proof.ice ?? "-"} twin={p.proof.twin ?? "-"} crosscheck={p.proof.crosscheck ?? "-"} applied={p.proof.applied ?? "-"}</div>
                  </>) : <div className="dim">free read made to confirm the plan against the live system ({c.ms} ms)</div>}
                </div>
              )}
            </div>
          );
        })}
        <div ref={end} />
      </div>
    </Win>
  );
}
