import type { EventView } from "../replay";
import type { Trace } from "../types";
import { Win } from "./Win";

const ORDER = ["SCOPE", "R1/R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10"];

export function Ice({ trace, view }: { trace?: Trace; view?: EventView }) {
  const lit = !!view?.gate;
  const v = trace?.verification;
  const byRule = new Map((v?.ice ?? []).map((r) => [r.rule, r]));
  const cross = v?.crosscheck ?? [];
  const agree = trace?.verdict.agreement;
  const chip = (label: string, state: "pass" | "warn" | "fail" | "", title: string) => (
    <span key={label} className={`chip ${lit ? state : ""}`} title={title} style={{ minWidth: 58, textAlign: "center" }}>{label}</span>
  );
  return (
    <Win title="ICE" tag="POLICY FIREWALL" hot={lit && !!v?.ok} alarm={lit && v != null && !v.ok}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
        {ORDER.map((r) => {
          const x = byRule.get(r);
          return chip(r, x ? (x.ok ? "pass" : x.level === "warn" ? "warn" : "fail") : "", x?.detail ?? "not applicable to this event");
        })}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginTop: 8 }}>
        {chip(`READERS ${agree === "unanimous" ? "2/2" : agree === "majority" ? "2/3" : agree === "split" ? "SPLIT" : "--"}`,
              agree === "unanimous" || agree === "majority" ? "pass" : agree ? "warn" : "",
              trace ? trace.readings.map((r) => `${r.reader}: ${r.category}`).join(" | ") : "")}
        {chip(`VALIDATOR ${trace?.metrics.validator_called ? "CALLED" : "IDLE"}`, trace?.metrics.validator_called ? "warn" : "pass",
              "Claude Haiku is only called when the readers disagree")}
        {chip("TWIN", v ? (v.twin.ok ? "pass" : "fail") : "", v ? `${v.twin.calls} calls dry-run, ${v.twin.errors.length} errors` : "")}
        {chip("XCHECK", cross.length ? (cross.every((c) => c.agree) ? "pass" : "fail") : "",
              cross.map((c) => `#${c.incident}: ${c.agree ? "graph == SQL" : "DISAGREE"}`).join(" | ") || "no impact to cross-check")}
      </div>
      {lit && v && (
        <div style={{ marginTop: 8, fontSize: 16 }} className={v.ok ? "neon-a" : "neon-m"}>
          {v.ok ? "> all gates green: packets cleared for the live system" : "> gate failure: nothing applied, escalated"}
        </div>
      )}
    </Win>
  );
}
