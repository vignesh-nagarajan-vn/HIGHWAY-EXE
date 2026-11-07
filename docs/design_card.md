# HIGHWAY.EXE design card

**One line:** the LLM only reads; code decides; every tool call carries a proof (graph path, handbook rule, twin dry-run, SQL crosscheck) before it reaches the enterprise server.

## Architecture

```
event -> READER-A qwen3:4b (Ollama, local GPU, JSON schema)  \
      -> READER-B deterministic grammar                        > GRAPH JUDGE (grounds both in the KG)
         readers disagree -> VALIDATOR claude-haiku-5-5        /  unresolved or unconfirmed -> escalate
DISPATCH (coordinator) -> work orders -> FORGE | AEGIS | RELAY (one shared Ledger per event)
proof packets -> ICE (rules R1-R10) -> TWIN (vendor Enterprise, in-process) -> CROSSCHECK (DuckDB SQL)
             -> APPLY through an MCP server wrapping POST /act -> trace + case file per event
```

| Agent | Role | Tools it may call |
|---|---|---|
| DISPATCH | coordinator: reading, triage, compound splits, escalation | `escalate` |
| FORGE | supply chain planner: delay and outage impact, slot plan | `mes.*` |
| AEGIS | quality: lot resolution, vehicle sweep, stop sale | `quality.hold_lot`, `dealer.stop_sale` |
| RELAY | dealer network and customer care: notices, loaners, owners | `dealer.notify`, `crm.*` |

Knowledge graph: networkx MultiDiGraph, 14 classes, 21 typed relations, 17,120 nodes, 27,795 edges. Edges point from cause to consequence, so every impact query is a forward walk and every citation reads left to right (`docs/ontology/`).

## LLM versus code

| LLM (1 call per event) | Code (everything that changes the world) |
|---|---|
| category, incident split, names and date phrases copied verbatim | alias and fuzzy resolution, date grammar, KG grounding |
| | affected sets, slot planning, loaner ranking, lot sweep |
| | messages (templates), summaries (generated from facts) |

The model never outputs an id, a date or an action. Case-file summaries come from the facts, so every number is exact.

## Guardrails

- **Two readers + graph judge.** A reading counts only if it grounds to real records (shipment ETA, later new ETA, whole-lot windows). "next Friday" yields 3/12 and 3/19; the graph keeps the one that fits.
- **Fail closed.** Disagreement goes to Haiku for a majority vote; no majority, a missing slot or hedged wording goes to `escalate` with a missing-intel checklist.
- **Least privilege.** Each agent can only call its own tools (ICE `SCOPE` check).
- **ICE / TWIN / CROSSCHECK** must all pass before the first write. A failed gate applies nothing and escalates.
- **Failed calls.** Transport errors retry with backoff; tool errors never retry blindly and end in an escalation.

## Evaluation

| Check | Result |
|---|---|
| Replay audit of `runs/final/action_log.jsonl` on a fresh vendor world | 15/15 events pass, 879 calls, **0 failed** |
| SQL crosscheck (independent implementation) | agrees on all 12 grounded incidents |
| Noise / rumors | 0 calls on E-05/06/07, exactly one `escalate` on E-02/E-13 |
| Reader benchmark, 60 synthetic messy events | grammar 100%, qwen3:4b 98.3%, qwen2.5:7b 98.3%, llama3.2:3b 93.3% |
| Silent reader errors (SLM wrong and grammar agrees) | 0: every SLM miss was a disagreement, so it is caught |
| Cost of the final run | 15 LLM calls, 14,935 tokens, 0 Haiku calls, 61.6 s on a laptop RTX 5060 |

**Models cited:** Qwen3 4B (`qwen3:4b`, Ollama, local) as READER-A; Claude Haiku 5.5 (`claude-haiku-5-5`) as the validator and synthetic paraphraser, called only on disagreement.

## Judgment calls

- Relative dates: "next X" is X of the following week, "last X" of the previous week. The data confirms it (lot LOT-0130 and shipment SH-0190 match exactly).
- Rule 3 transfers go to the earliest free day at any other plant that builds the model, ties broken by `plants.csv` order (`TRANSFER_FROM` switch).
- Compound events plan both incidents against one ledger; each dealer gets one notice covering both; loaner priority runs once over the union.

## What we would improve

- Re-plan around a live rejection instead of escalating it.
- Paraphrase-heavy synthetic set (Haiku) to stress the grammar reader, which is strong on templates by construction.
- Offer operator actions on escalation tickets (approve a clarified incident), writing a second, audited pass.
