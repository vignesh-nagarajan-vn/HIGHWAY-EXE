import type { Run, Trace, World } from "./types";

async function j<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init);
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json() as Promise<T>;
}

/** Hosted replay (`vite build --mode static`): read JSON frozen by `python -m tower.api.export_static`. */
export const STATIC = import.meta.env.MODE === "static";

export const runUrl = (name: string) =>
  STATIC ? `/data/run/${encodeURIComponent(name)}.json` : `/api/run/${encodeURIComponent(name)}`;

export const api = {
  world: () => j<World>(STATIC ? "/data/world.json" : "/api/world"),
  runs: () => j<{ name: string; events: number; summary: any }[]>(STATIC ? "/data/runs.json" : "/api/runs"),
  run: (name: string) => j<Run>(runUrl(name)),
  startLive: (out: string) =>
    STATIC ? Promise.reject(new Error("LIVE mode runs locally: python -m tower.api with Ollama and the enterprise server"))
    : j<{ started: boolean }>("/api/live", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ out }),
    }),
  liveStream: (onTrace: (t: Trace) => void, onDone: (err: string | null) => void) => {
    const es = new EventSource("/api/live/stream");
    es.addEventListener("trace", (e) => onTrace(JSON.parse((e as MessageEvent).data)));
    es.addEventListener("done", (e) => {
      onDone(JSON.parse((e as MessageEvent).data).error);
      es.close();
    });
    return () => es.close();
  },
};

export function download(name: string, text: string, type = "application/json") {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
