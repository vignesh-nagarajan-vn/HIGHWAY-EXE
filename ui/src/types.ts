export interface Plant { id: string; name: string; city: string; slots: number; models: string[] }
export interface Dealer { id: string; name: string; city: string; region: string; loaners: number }
export interface SchedRow { po: string; plant: string; date: string; model: string; cos: number }

export interface World {
  today: string;
  days: string[];
  plants: Plant[];
  dealers: Dealer[];
  suppliers: { id: string; name: string; city: string }[];
  models: string[];
  schedule: SchedRow[];
  kg: { nodes: number; edges: number; by_class: Record<string, number>; by_relation: Record<string, number> };
  ontology: { classes: Record<string, string>; relations: Record<string, [string, string, string]> };
  settings: { reader: string; validator: string };
}

export interface Hop { cls: string; rel: string; count: number; ids: string[]; note: string }
export interface Incident {
  kind: "supplier_delay" | "plant_outage" | "quality_hold";
  plant: string; part?: string; supplier?: string; shipment_id?: string; lot_ids: string[];
  start: string; end: string; resume_on?: string; support: string[]; evidence: string;
}
export interface TraceIncident {
  no: number; incident: Incident; graph_path: string; traceroute: string[]; hops: Hop[];
  impact: Record<string, string[]>;
}
export interface SlotDecision {
  production_order_id: string; model: string; from_plant: string; from_date: string;
  to_plant: string | null; to_date: string | null; mode: "reschedule" | "transfer" | "unplaceable";
  reason: string; incident_no: number;
}
export interface PacketT {
  seq: number; agent: string; tool: string; args: Record<string, any>; rule: string; why: string;
  incident: number | null; path: string; proof: Record<string, string>;
}
export interface Call {
  event_id: string; tool: string; args: Record<string, any>; agent: string; seq: number | null;
  ok: boolean; result: any; error: string | null; ms: number; write: boolean;
}
export interface Reading {
  category: string; incidents: any[]; rationale: string; reader: string; model: string | null;
  tokens_in: number; tokens_out: number; latency_ms: number; error: string | null;
}
export interface IceResult { rule: string; ok: boolean; detail: string; level: "pass" | "warn" | "error" }
export interface Trace {
  event: { event_id: string; received_at: string; source: string; text: string };
  stamp: string; summary: string; reason: string;
  verdict: { category: "operational" | "noise" | "unconfirmed"; agreement: string; readers: string[];
             missing_intel: string[]; unresolved: any[] };
  readings: Reading[];
  incidents: TraceIncident[];
  slot_decisions: SlotDecision[];
  loaner_report: Record<string, { pool: number; entitled: string[]; granted: string[]; waitlisted: string[] }>;
  packets: PacketT[];
  verification: { ok: boolean; ice: IceResult[]; crosscheck: any[]; twin: { ok: boolean; errors: any[]; calls: number } } | null;
  apply: { applied: number; failed: number; blocked: boolean; reads: number; calls: Call[] } | null;
  radio: { agent: string; text: string; kind: string }[];
  metrics: { llm_calls: number; validator_called: boolean; tokens_in: number; tokens_out: number;
             reader_model: string; total_ms: number; [k: string]: any };
}
export interface RunSummary {
  events: number; reader_model: string; validator_model: string; validator_calls: number; llm_calls: number;
  tokens_in: number; tokens_out: number; tool_calls: number; write_calls: number; failed_calls: number;
  transport: string; seconds: number;
}
export interface Run { name: string; summary: RunSummary | null; audit: any; traces: Trace[] }
