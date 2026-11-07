/* CASE FILE: the audit-ready dossier for one event: stamp, summary, why, readers, graph paths,
   action counts, loaner ranking and slot moves, with exports. */
import { download } from "../api";
import type { Trace } from "../types";

function md(t: Trace): string {
  const acts: Record<string, number> = {};
  t.packets.forEach((p) => (acts[p.tool] = (acts[p.tool] ?? 0) + 1));
  return [
    `# ${t.event.event_id} - ${t.stamp}`, "", `> ${t.event.text}`, "", `**Summary.** ${t.summary}`, "",
    `**Why.** ${t.reason} (readers ${t.verdict.agreement}: ${t.verdict.readers.join(", ")})`, "",
    ...t.incidents.flatMap((i) => [`**Graph path #${i.no}.** \`${i.graph_path}\``, "", "```", ...i.traceroute, "```", ""]),
    `**Actions.** ${Object.entries(acts).map(([k, v]) => `${k} x${v}`).join(", ") || "none"}`, "",
  ].join("\n");
}

export function CaseFile({ trace, runName }: { trace?: Trace; runName: string }) {
  if (!trace) return <div className="dim">select an event</div>;
  const t = trace;
  const ok = t.stamp.startsWith("RESOLVED");
  const acts: Record<string, number> = {};
  t.packets.forEach((p) => (acts[p.tool] = (acts[p.tool] ?? 0) + 1));
  const loaners = Object.entries(t.loaner_report);
  return (
    <div style={{ position: "relative", padding: "6px 8px", fontSize: 18 }}>
      <div className="px" style={{
        position: "absolute", right: 18, top: 14, transform: "rotate(-8deg)", fontSize: 13, padding: "8px 10px",
        color: ok ? "var(--acid)" : t.stamp.startsWith("NO") ? "var(--dim)" : "var(--amber)",
        boxShadow: `inset 0 0 0 3px ${ok ? "var(--acid)" : t.stamp.startsWith("NO") ? "var(--dim)" : "var(--amber)"}` }}>
        {t.stamp}
      </div>
      <div className="px neon-c" style={{ fontSize: 11 }}>CASE FILE {t.event.event_id}</div>
      <div className="dim">{t.event.source} // received {t.event.received_at.replace("T", " ")}</div>
      <blockquote style={{ margin: "10px 0", padding: "6px 10px", background: "#0d0430", boxShadow: "inset 3px 0 0 var(--magenta)", maxWidth: "70%" }}>
        {t.event.text}
      </blockquote>
      <div><span className="neon-c px" style={{ fontSize: 8 }}>SUMMARY </span>{t.summary}</div>
      <div style={{ marginTop: 6 }}><span className="neon-c px" style={{ fontSize: 8 }}>WHY </span>{t.reason}</div>

      <div className="px dim" style={{ fontSize: 8, margin: "12px 0 4px" }}>READERS</div>
      <table style={{ borderCollapse: "collapse", fontSize: 17 }}>
        <tbody>
          {t.readings.map((r) => (
            <tr key={r.reader}>
              <td style={{ paddingRight: 14 }} className="amber">{r.reader.toUpperCase()}</td>
              <td style={{ paddingRight: 14 }}>{r.model}</td>
              <td style={{ paddingRight: 14 }}>{r.category}</td>
              <td style={{ paddingRight: 14 }}>{r.incidents.length} incident(s)</td>
              <td style={{ paddingRight: 14 }} className="dim">{r.latency_ms} ms</td>
              <td className="dim">{r.tokens_in + r.tokens_out} tok</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="dim" style={{ fontSize: 16 }}>verdict: {t.verdict.category} ({t.verdict.agreement})</div>

      {t.incidents.map((i) => (
        <div key={i.no}>
          <div className="px dim" style={{ fontSize: 8, margin: "12px 0 4px" }}>GRAPH PATH #{i.no}</div>
          <code style={{ color: "var(--acid)", fontSize: 16, wordBreak: "break-word" }}>{i.graph_path}</code>
        </div>
      ))}

      <div className="px dim" style={{ fontSize: 8, margin: "12px 0 4px" }}>ACTIONS</div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        {Object.keys(acts).length === 0 && <span className="chip">NONE</span>}
        {Object.entries(acts).map(([k, v]) => <span key={k} className="chip cyan">{k} x{v}</span>)}
      </div>

      {t.slot_decisions.length > 0 && (<>
        <div className="px dim" style={{ fontSize: 8, margin: "12px 0 4px" }}>SLOT REASONING</div>
        {t.slot_decisions.map((d) => (
          <div key={d.production_order_id} style={{ fontSize: 16 }}>
            <span className={d.mode === "transfer" ? "neon-m" : "neon-c"}>{d.mode.toUpperCase().padEnd(10)}</span>{" "}
            {d.production_order_id} {d.model} {d.from_plant} {d.from_date} {"->"} {d.to_plant} {d.to_date} <span className="dim">// {d.reason}</span>
          </div>
        ))}
      </>)}

      {loaners.length > 0 && (<>
        <div className="px dim" style={{ fontSize: 8, margin: "12px 0 4px" }}>LOANER RANKING (PLATINUM &gt; GOLD &gt; PROMISED DATE &gt; ORDER ID)</div>
        {loaners.map(([d, r]) => (
          <div key={d} style={{ fontSize: 16 }}>
            {d} pool {r.pool}: <span className="neon-a">{r.granted.join(" ")}</span>
            {r.waitlisted.length > 0 && <span className="amber"> // waitlist {r.waitlisted.join(" ")}</span>}
          </div>
        ))}
      </>)}

      <div style={{ display: "flex", gap: 6, marginTop: 14 }}>
        <button className="pbtn" onClick={() => download(`${t.event.event_id}_trace.json`, JSON.stringify(t, null, 1))}>EXPORT TRACE</button>
        <button className="pbtn" onClick={() => download(`${t.event.event_id}_case.md`, md(t), "text/markdown")}>EXPORT CASE .MD</button>
        <a className="pbtn" href={`/api/run/${runName}`} target="_blank" rel="noreferrer" style={{ textDecoration: "none" }}>RUN JSON</a>
      </div>
    </div>
  );
}
