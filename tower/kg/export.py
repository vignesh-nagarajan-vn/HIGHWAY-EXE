"""Export the ontology (Turtle + Mermaid) and the instance graph (JSON lines).

python -m tower.kg.export docs/ontology
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .build import KnowledgeGraph, kg
from .ontology import CLASSES, NAMESPACE, RELATIONS


def ontology_ttl() -> str:
    out = [f"@prefix hx: <{NAMESPACE}> .", "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
           "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .", ""]
    for cls, desc in CLASSES.items():
        out.append(f'hx:{cls} a owl:Class ; rdfs:comment "{desc}" .')
    out.append("")
    for rel, (dom, rng, desc) in RELATIONS.items():
        rng_s = "owl:Thing" if rng == "*" else f"hx:{rng}"
        out.append(f'hx:{rel} a owl:ObjectProperty ; rdfs:domain hx:{dom} ; rdfs:range {rng_s} ; rdfs:comment "{desc}" .')
    return "\n".join(out) + "\n"


def ontology_mermaid(g: KnowledgeGraph) -> str:
    counts = g.stats()["by_class"]
    lines = ["flowchart LR"]
    for cls in CLASSES:
        lines.append(f'  {cls}["{cls}<br/>{counts.get(cls, 0):,}"]')
    for rel, (dom, rng, _) in RELATIONS.items():
        if rng != "*":
            lines.append(f"  {dom} -- {rel} --> {rng}")
    return "\n".join(lines) + "\n"


def export(out_dir: Path) -> dict:
    g = kg()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "ontology.ttl").write_text(ontology_ttl(), encoding="utf-8")
    (out_dir / "ontology.mmd").write_text(ontology_mermaid(g), encoding="utf-8")
    with open(out_dir / "graph_nodes.jsonl", "w", encoding="utf-8") as f:
        for n, d in g.g.nodes(data=True):
            f.write(json.dumps({"id": n, **d}) + "\n")
    with open(out_dir / "graph_edges.jsonl", "w", encoding="utf-8") as f:
        for u, v, k in g.g.edges(keys=True):
            f.write(json.dumps({"source": u, "relation": k, "target": v}) + "\n")
    stats = g.stats()
    (out_dir / "graph_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


if __name__ == "__main__":
    s = export(Path(sys.argv[1] if len(sys.argv) > 1 else "docs/ontology"))
    print(f"exported {s['nodes']} nodes / {s['edges']} edges")
