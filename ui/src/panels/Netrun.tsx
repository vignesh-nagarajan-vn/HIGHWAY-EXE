/* NETRUN: the incident's graph path drawn as a cyberspace route. A light trail runs hop by hop
   along the typed edges while the traceroute prints beside it. Noise and rumors get NO ROUTE. */
import cytoscape from "cytoscape";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Trace, TraceIncident } from "../types";

const CLS_COLOR: Record<string, string> = {
  Supplier: "#f9c80e", Shipment: "#ff8a1f", Part: "#b967ff", Plant: "#05d9e8", Model: "#8b84bf",
  ProductionOrder: "#39ff14", CustomerOrder: "#ff2a6d", Dealer: "#05d9e8", Customer: "#f4f1ff",
  Lot: "#ff3b3b", Vehicle: "#f9c80e", WorkDay: "#8b84bf",
};

function elements(inc: TraceIncident) {
  const nodes: cytoscape.ElementDefinition[] = [];
  const edges: cytoscape.ElementDefinition[] = [];
  let prev: string[] = [];
  inc.hops.forEach((h, i) => {
    const show = h.ids.slice(0, h.count > 5 ? 4 : 5);
    const cur: string[] = [];
    show.forEach((id, j) => {
      const nid = `${i}:${id}`;
      nodes.push({ data: { id: nid, label: `${h.cls}\n${id}`, cls: h.cls, hop: i },
                   position: { x: i * 150, y: (j - (Math.min(show.length + (h.count > 5 ? 1 : 0), 5) - 1) / 2) * 62 } });
      cur.push(nid);
    });
    if (h.count > 5) {
      const nid = `${i}:more`;
      nodes.push({ data: { id: nid, label: `+${h.count - show.length}\n${h.cls}`, cls: h.cls, hop: i, more: 1 },
                   position: { x: i * 150, y: (show.length - (show.length) / 2) * 62 } });
      cur.push(nid);
    }
    if (prev.length) {
      cur.forEach((c) => edges.push({ data: { id: `${prev[0]}->${c}`, source: prev[0], target: c, label: h.rel, hop: i } }));
    }
    prev = cur;
  });
  return [...nodes, ...edges];
}

export function Netrun({ trace, reduced, live }: { trace?: Trace; reduced: boolean; live: boolean }) {
  const host = useRef<HTMLDivElement>(null);
  const [incNo, setIncNo] = useState(0);
  const [lit, setLit] = useState(0);
  const inc = trace?.incidents[incNo];
  const els = useMemo(() => (inc ? elements(inc) : []), [inc]);

  useEffect(() => { setIncNo(0); }, [trace?.event.event_id]);
  useEffect(() => { setLit(reduced ? 99 : 0); }, [inc, reduced]);
  useEffect(() => {
    if (!inc || lit > inc.hops.length) return;
    const t = setTimeout(() => setLit((x) => x + 1), 380);
    return () => clearTimeout(t);
  }, [lit, inc]);

  const cy = useRef<cytoscape.Core | null>(null);
  useEffect(() => {
    if (!host.current || !inc) return;
    cy.current?.destroy();
    cy.current = cytoscape({
      container: host.current, elements: els, layout: { name: "preset" }, userZoomingEnabled: true,
      boxSelectionEnabled: false, autoungrabify: true,
      style: [
        { selector: "node", style: {
            shape: "round-rectangle", width: 112, height: 40, "background-color": "#120636",
            "border-width": 2, "border-color": "#2b1a66", label: "data(label)", color: "#6a63a0",
            "font-family": "VT323, monospace", "font-size": 15, "text-wrap": "wrap", "text-valign": "center",
            "text-halign": "center" } },
        { selector: "node[more]", style: { "border-style": "dashed" } },
        { selector: "node.lit", style: {
            "border-color": (n: cytoscape.NodeSingular) => CLS_COLOR[n.data("cls")] ?? "#05d9e8",
            color: "#f4f1ff", "background-color": "#1b0d4a",
            "underlay-color": (n: cytoscape.NodeSingular) => CLS_COLOR[n.data("cls")] ?? "#05d9e8",
            "underlay-padding": 5, "underlay-opacity": 0.22 } as any },
        { selector: "edge", style: {
            width: 2, "line-color": "#2b1a66", "curve-style": "bezier", "target-arrow-shape": "triangle",
            "target-arrow-color": "#2b1a66", label: "data(label)", "font-size": 10, color: "#4a4380",
            "font-family": "Press Start 2P, monospace", "text-rotation": "autorotate",
            "text-background-color": "#0b0221", "text-background-opacity": 1, "text-background-padding": "2px" } },
        { selector: "edge.lit", style: { "line-color": "#ff2a6d", "target-arrow-color": "#ff2a6d", color: "#ff2a6d", width: 3 } },
      ],
    });
    cy.current.fit(undefined, 24);
    const ro = new ResizeObserver(() => { cy.current?.resize(); cy.current?.fit(undefined, 24); });
    ro.observe(host.current);
    return () => { ro.disconnect(); cy.current?.destroy(); cy.current = null; };
  }, [els]);

  useEffect(() => {
    const c = cy.current;
    if (!c) return;
    c.batch(() => {
      c.nodes().forEach((n) => { n.toggleClass("lit", n.data("hop") < lit); });
      c.edges().forEach((e) => { e.toggleClass("lit", e.data("hop") < lit); });
    });
  }, [lit, els]);

  if (!trace) return <div className="dim">no event selected</div>;
  if (!trace.incidents.length) {
    const rumor = trace.verdict.category === "unconfirmed";
    return (
      <div style={{ display: "grid", placeItems: "center", height: "100%", textAlign: "center", gap: 10 }}>
        <div>
          <div className="px glitch neon-m" data-text="NO ROUTE TO OPERATIONS" style={{ fontSize: 16 }}>NO ROUTE TO OPERATIONS</div>
          <p style={{ maxWidth: 560, margin: "14px auto" }}>
            {rumor ? "The report could not be grounded in the company graph: " : "Not about plant operations: "}
            <span className="amber">{trace.reason}</span>
          </p>
          {rumor && (
            <div style={{ textAlign: "left", display: "inline-block" }}>
              <div className="px dim" style={{ fontSize: 8, marginBottom: 6 }}>MISSING INTEL</div>
              {trace.verdict.missing_intel.map((m) => <div key={m}>[ ] {m}</div>)}
            </div>
          )}
          <div className="dim" style={{ marginTop: 12 }}>{rumor ? "-> routed to HUMAN REVIEW LANE via escalate()" : "-> zero tool calls"}</div>
        </div>
      </div>
    );
  }
  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) 300px", gap: 8, height: "100%" }}>
      <div style={{ position: "relative", minHeight: 260, background: "repeating-linear-gradient(0deg,#0b0221 0 23px,#160a3e 23px 24px),repeating-linear-gradient(90deg,transparent 0 23px,#160a3e 23px 24px)" }}>
        <div ref={host} style={{ position: "absolute", inset: 0 }} />
        {trace.incidents.length > 1 && (
          <div style={{ position: "absolute", top: 6, left: 6, display: "flex", gap: 4 }}>
            {trace.incidents.map((x, i) => (
              <button key={i} className={`pbtn ${i === incNo ? "on" : ""}`} onClick={() => setIncNo(i)}>
                PATH #{x.no} {x.incident.kind.split("_")[1].toUpperCase()}
              </button>
            ))}
          </div>
        )}
        <button className="pbtn" style={{ position: "absolute", bottom: 6, right: 6 }} onClick={() => setLit(0)}>RE-TRACE</button>
      </div>
      <div className="term" style={{ overflow: "auto", fontSize: 16, background: "#07021a", padding: 6 }}>
        <div className="neon-a">$ {inc!.traceroute[0]}</div>
        {inc!.traceroute.slice(1, lit + 1).map((l, i) => <div key={i} style={{ whiteSpace: "pre-wrap" }}>{l}</div>)}
        {lit <= inc!.hops.length && <span className="blink">_</span>}
        <div className="px dim" style={{ fontSize: 8, margin: "10px 0 4px" }}>GROUNDING (GRAPH JUDGE)</div>
        {inc!.incident.support.map((s, i) => <div key={i} className="dim">+ {s}</div>)}
        <div className="px dim" style={{ fontSize: 8, margin: "10px 0 4px" }}>EVIDENCE</div>
        <div className="amber">"{inc!.incident.evidence}"</div>
      </div>
    </div>
  );
}
