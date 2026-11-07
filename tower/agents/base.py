"""Shared bits for the agents: a work order (what DISPATCH hands a specialist) and a
radio log, the agent's running commentary that shows up in the trace and the UI."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ..ground import calendar as cal
from ..ground.judge import ResolvedIncident
from ..kg.paths import Impact


@dataclass
class WorkOrder:
    incident_no: int
    incident: ResolvedIncident
    impact: Impact | None = None


@dataclass
class Radio:
    lines: list[dict] = field(default_factory=list)

    def say(self, agent: str, text: str, kind: str = "info") -> None:
        self.lines.append({"agent": agent, "text": text, "kind": kind})


def idx_ceil(d: str) -> int:
    """Working-day index of d, or of the next working day if d is a weekend."""
    x = date.fromisoformat(d)
    while not cal.is_workday(x):
        x = cal.next_workday(x)
    return cal.idx_of(x)
