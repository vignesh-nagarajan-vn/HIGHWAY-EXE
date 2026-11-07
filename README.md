<p align="center"><img src="ui/public/favicon.svg" width="80" alt="HIGHWAY.EXE logo, a pixel car"></p>

# HIGHWAY.EXE

**A multi-agent control tower for Wacky Wheels Co. where every action carries its own proof.**

- Live Deployment: [highway-exe.vercel.app](https://highway-exe.vercel.app/) (replay of the final run; LIVE mode runs locally)
- Event: TAMU Datathon 2026 · Hitachi Solutions "Hack the Highway"
- Design card: [docs/design_card.md](docs/design_card.md)

A local small model reads each operations message. Deterministic code grounds it in a 17k-node knowledge graph, plans the corrective actions by the policy handbook, and proves each tool call three ways before it touches the enterprise server. The control tower UI is a pixel-cyberpunk retro OS where every event drives in as a vehicle.

- **Final run:** 15/15 events pass the replay audit, 879 tool calls, 0 failed, 15 LLM calls (`qwen3:4b`), 0 validator calls, 61.6 s.
- **Models:** Qwen3 4B (`qwen3:4b`) via Ollama as the reader; Claude Haiku 5.5 (`claude-haiku-5-5`) as validator, only on reader disagreement.
- **Run it:** see [Quick start](#quick-start), then open http://localhost:5173 and press start.

## Demo

| Boot sequence | NETRUN traceroute (E-01) |
|:-:|:-:|
| <img src="docs/screenshots/1-boot.jpg" width="400" alt="BIOS-style boot log listing the ontology size, both readers, the validator and the armed ICE rules"> | <img src="docs/screenshots/2-netrun.jpg" width="400" alt="E-01 delay path from supplier to shipment, part, plant, orders, dealers and customers, with the traceroute printout beside it"> |
| **SLOT GRID (E-11)** | **CASE FILE (E-11)** |
| <img src="docs/screenshots/3-slot-grid.jpg" width="400" alt="Jackson plant dark for three days, with six orders moved later at the same plant and three arcing to other plants"> | <img src="docs/screenshots/4-case-file.jpg" width="400" alt="E-11 case file stamped RESOLVED, with the generated summary and both readers agreeing"> |

<img src="docs/screenshots/desktop.jpg" width="820" alt="The full control tower mid-replay: E-04 on the highway, the E-02 ghost car in the human review lane, dealer notices in the packet log and an escalation ticket in the inbox">

## How it works

1. **Two readers.** `qwen3:4b` on the laptop GPU and a deterministic grammar reader each read the event. Names and date phrases are copied verbatim; the model never outputs ids, dates or actions.
2. **Graph judge.** Both readings are grounded in the knowledge graph. Only combinations the data supports survive. If the readers disagree, Claude Haiku casts a third vote; if nothing settles, the tower escalates with a missing-intel checklist.
3. **Agents.** DISPATCH coordinates. FORGE plans reschedules and transfers, AEGIS runs quality holds, RELAY sends dealer notices, loaners and owner contacts. Each agent can only call its own tools.
4. **Proof gates.** ICE checks handbook rules R1 to R10, TWIN dry-runs the plan on the organisers' own enterprise model, CROSSCHECK recomputes every affected set in DuckDB SQL. Only then does APPLY call the tools, through an MCP server.
5. **Explain.** Each event gets a trace (readings, graph path, traceroute, slot reasoning, loaner ranking, proofs, every call) and a case file.

Details: [docs/design_card.md](docs/design_card.md).

## Quick start

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
ollama pull qwen3:4b
```

Copy `.env.example` to `.env` and add `ANTHROPIC_API_KEY` if you want the validator.

Start a fresh enterprise server, then run the tower:

```bash
python vendor/hack_the_highway_package/enterprise_server.py --data vendor/hack_the_highway_package/data --out runs/demo --port 8000
```

```bash
python -m tower.run --out runs/demo
```

```bash
python -m eval.replay_audit runs/demo
```

Control tower UI (replays any recorded run, or runs live against the server):

```bash
python -m tower.api
```

```bash
cd ui && npm install && npm run dev
```

Open http://localhost:5173, press start. `npm run build` lets `python -m tower.api` serve the UI on :8765 by itself.

Hosted replay: `python -m tower.api.export_static` freezes the read-only API into `ui/public/data/`, and Vercel builds it with `npm run build:static` (see [vercel.json](vercel.json)).

## Submission artifacts

| What | Where |
|---|---|
| Action log | [runs/final/action_log.jsonl](runs/final/action_log.jsonl) |
| Trace per event | [runs/final/traces/](runs/final/traces) |
| Case files (summary + reason per event) | [runs/final/case_files.md](runs/final/case_files.md) |
| Replay audit | [runs/final/audit.json](runs/final/audit.json) |
| Ontology and graph export | [docs/ontology/](docs/ontology) (Turtle, Mermaid, JSONL) |
| Design card | [docs/design_card.md](docs/design_card.md) |
| Reader benchmark | [docs/reader_benchmark.json](docs/reader_benchmark.json) |

## Layout

```
tower/kg        ontology, graph build, impact traversals, exports
tower/ground    calendar, date grammar, entity resolver, graph judge
tower/intake    SLM reader, grammar reader, Haiku validator, prompts
tower/agents    dispatch, forge, aegis, relay
tower/policy    rule registry, shared ledger
tower/verify    ICE firewall, digital twin, SQL crosscheck
tower/exec      MCP server over the enterprise API, executor
tower/trace     traces and case files
tower/api       backend for the UI
ui/             React + Vite control tower
eval/           replay auditor, synthetic events, reader benchmark
tests/          pytest suite
vendor/         organisers' starter package, unmodified
```
