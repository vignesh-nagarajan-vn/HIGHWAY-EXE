import { useEffect, useState } from "react";
import type { World } from "../types";

/** CRT power-on + BIOS-style self test, then PRESS START. */
export function Boot({ world, onStart }: { world: World | null; onStart: () => void }) {
  const lines = world
    ? [
        "WACKY WHEELS CO. // CONTROL TOWER BIOS v2.077",
        "(c) TAMU DATATHON 2026 - HACK THE HIGHWAY",
        "",
        `MEMORY TEST .......................... 640K OK`,
        `CALENDAR ............................. TODAY ${world.today} (MON)`,
        `PLANTS ............................... ${world.plants.length} ONLINE  ${world.plants.map((p) => p.id).join(" ")}`,
        `DEALERS .............................. ${world.dealers.length} LINKED`,
        `ONTOLOGY ............................. ${world.kg.nodes.toLocaleString()} NODES / ${world.kg.edges.toLocaleString()} EDGES`,
        `CLASSES .............................. ${Object.keys(world.kg.by_class).length}  RELATIONS ${Object.keys(world.kg.by_relation).length}`,
        `READER-A ............................. ${world.settings.reader.toUpperCase()} (LOCAL GPU)`,
        `READER-B ............................. GRAMMAR v1 (DETERMINISTIC)`,
        `VALIDATOR ............................ ${world.settings.validator.toUpperCase()} (ON DISAGREEMENT ONLY)`,
        `ICE FIREWALL ......................... R1-R10 ARMED`,
        `DIGITAL TWIN ......................... SYNCED`,
        `SQL CROSSCHECK ....................... DUCKDB READY`,
        `MCP BUS .............................. 10 TOOLS MOUNTED`,
      ]
    : ["WACKY WHEELS CO. // CONTROL TOWER BIOS v2.077", "", "CONTACTING TOWER BACKEND ..."];
  const [n, setN] = useState(0);
  const [out, setOut] = useState(false);
  useEffect(() => {
    if (n >= lines.length) return;
    const t = setTimeout(() => setN((x) => x + 1), lines[n] === "" ? 120 : 90);
    return () => clearTimeout(t);
  }, [n, lines.length]);
  const go = () => {
    if (!world) return;
    setOut(true);
    setTimeout(onStart, 430);
  };
  useEffect(() => {
    const k = (e: KeyboardEvent) => { if (e.key === "Enter" || e.key === " ") go(); };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  });
  return (
    <div className={`boot ${out ? "out" : ""}`} onClick={go} role="button" tabIndex={0} aria-label="Press start">
      {lines.slice(0, n).map((l, i) => <div key={i}>{l || " "}</div>)}
      {n >= lines.length && world && (
        <>
          <div className="ascii">HIGHWAY<b>.EXE</b></div>
          <div className="dim">every action carries its own proof</div>
          <div className="start blink">PRESS START</div>
        </>
      )}
    </div>
  );
}
