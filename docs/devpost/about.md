## Inspiration

Wacky Wheels Co. gets a steady stream of operations messages: a supplier shipment is late, a plant loses power, a batch of airbags might be bad. Each one ripples out to production orders, customers, dealers and loaner cars. Get it wrong and a customer gets the wrong date, or a recalled car gets sold.

Hundreds of teams got the same prompt, and the obvious build is "let an LLM read the message and call the tools." We didn't trust that. A model that invents an order id or misreads "next Friday" will do the wrong thing with total confidence. So we flipped it: **the model only reads, code decides, and every tool call has to prove itself before it runs.**

For the look, we went with our favorite game styles: the neon of cyberpunk and the pixel art and text boxes of Undertale. A control tower is basically a wall of screens with things moving across them, so we built it like a retro operating system you'd find in one of those games. Every event drives in as a car, and the agents show up as a pixel crew reporting what they're doing.

## What it does

HIGHWAY.EXE is a control tower. For each event it:

1. **Reads the message twice.** A small local model (`qwen3:4b`) and a hand-written grammar each pull out what happened, where and when. The model never outputs an id or an action.
2. **Checks the reading against the data.** Both readings are matched to a knowledge graph, and anything that doesn't fit real records is dropped. If the readers disagree, Claude Haiku breaks the tie. If it can't, a human decides.
3. **Plans the fix.** DISPATCH coordinates. FORGE reschedules orders, AEGIS holds bad lots and stops sales, RELAY handles dealers, loaners and owners. Each agent can only call its own tools.
4. **Proves the plan three ways.** ICE checks the 10 handbook rules, TWIN dry-runs the plan on a copy of the enterprise system, and CROSSCHECK recomputes every affected record in SQL. All three must pass before anything is written.
5. **Applies it and explains it.** Tool calls go out through an MCP server. Every event gets a full trace and a one-page case file.

In the UI you can watch the graph path, the plant schedule, the proof checks and the human review inbox update live.

## How we built it

- **Backend:** Python. NetworkX for the knowledge graph, DuckDB for the SQL crosscheck, RapidFuzz for fuzzy name matching, Pydantic for the reader schema, FastAPI for the UI's API, and an MCP server wrapping the organisers' enterprise endpoint.
- **Models:** Qwen3 4B through Ollama, running locally on an RTX 5060. Claude Haiku as a tiebreaker only.
- **Frontend:** React, TypeScript and Vite, with Cytoscape for the graph view. The hosted version is a static replay of the final run on Netlify.
- **Evaluation:** a replay auditor that runs our action log against a fresh copy of the enterprise system, plus a benchmark of 60 messy synthetic messages for the readers.

## Results

- 15 of 15 events pass the replay audit: 879 tool calls, 0 failed.
- Rumors and noise produce 0 tool calls. Unconfirmed reports produce exactly one escalation.
- The whole run takes 61.6 seconds on a laptop, with 15 model calls and 0 Haiku calls.
- On the 60-message benchmark, the grammar reader scored 100% and `qwen3:4b` scored 98.3%. Every time the model was wrong, the grammar reader disagreed, so no mistake slipped through silently.

## Challenges

- **"Next Friday."** Relative dates are ambiguous. "Next Friday" could be two different days. Instead of guessing, we generate both and let the graph keep the one that matches a real shipment or lot.
- **Two problems in one message.** Some messages report a plant outage and a late shipment together. Both get planned against one shared ledger, so a dealer gets one notice covering both instead of two conflicting ones.
- **Knowing when to stop.** It's tempting to always act. We made the tower fail closed: if the readers disagree, a field is missing, or the wording is hedged, it escalates instead of guessing.
- **Deploying on campus.** The Texas A&M network blocks every `*.vercel.app` site, so we moved the hosted demo to Netlify partway through.

## What we learned

A 4B model running on a laptop is plenty for reading messages, as long as it never has to make a decision. Putting a deterministic second reader next to it was the biggest win: it doesn't make the model smarter, it just makes the model's mistakes visible. And the data can settle a surprising number of ambiguous phrases if you check the reading against it.

## What's next

- Re-plan around a rejected action instead of escalating it.
- Let an operator approve a clarified incident from the review inbox and run a second, audited pass.
- Build a paraphrase-heavy test set to stress the grammar reader harder.
