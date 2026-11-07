import type { ReactNode } from "react";

/** A retro-OS pixel window with a title bar. */
export function Win(props: { title: string; tag?: string; hot?: boolean; alarm?: boolean; right?: ReactNode;
                            children: ReactNode; className?: string; bodyClass?: string }) {
  return (
    <section className={`win ${props.hot ? "hot" : ""} ${props.alarm ? "alarm" : ""} ${props.className ?? ""}`}
             aria-label={props.title}>
      <div className="titlebar">
        <span>{props.title}</span>
        {props.tag && <span className="tag">{props.tag}</span>}
        <span className="spacer" />
        {props.right}
        <span className="btns" aria-hidden><i /><i /><i /></span>
      </div>
      <div className={`body ${props.bodyClass ?? ""}`}>{props.children}</div>
    </section>
  );
}

export const KIND_LABEL: Record<string, string> = {
  supplier_delay: "DELAY", plant_outage: "OUTAGE", quality_hold: "QUALITY",
};

export function eventBadge(t: { verdict: { category: string }; incidents: { incident: { kind: string } }[] }) {
  if (t.verdict.category === "noise") return { label: "NOISE", cls: "" };
  if (t.verdict.category === "unconfirmed") return { label: "RUMOR", cls: "warn" };
  if (t.incidents.length > 1) return { label: "COMPOUND", cls: "mag" };
  const k = t.incidents[0]?.incident.kind;
  return { label: KIND_LABEL[k] ?? "OPS", cls: k === "quality_hold" ? "fail" : "cyan" };
}
