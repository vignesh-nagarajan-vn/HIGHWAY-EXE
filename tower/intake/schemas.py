"""What a reader produces: a structured reading of one event, with names and date phrases
copied verbatim. Readers never compute dates or ids; the ground layer does that."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Kind = Literal["supplier_delay", "plant_outage", "quality_hold"]
Category = Literal["operational", "noise", "unconfirmed"]


class IncidentReading(BaseModel):
    kind: Kind
    supplier: str | None = Field(None, description="supplier name exactly as written, or null")
    part: str | None = Field(None, description="part name or id exactly as written, or null")
    plant: str | None = Field(None, description="plant name or id exactly as written, or null")
    shipment_id: str | None = Field(None, description="shipment id like SH-0123 if written, else null")
    lot_id: str | None = Field(None, description="lot id like LOT-0123 if written, else null")
    date_from: str | None = Field(None, description=(
        "delay: ORIGINAL arrival date phrase; outage: FIRST dark day phrase; quality: FIRST build day phrase"))
    date_to: str | None = Field(None, description=(
        "delay: NEW arrival date phrase; outage: LAST dark day phrase; quality: LAST build day phrase"))
    evidence: str = Field("", description="the exact sentence from the message this incident comes from")


class EventReading(BaseModel):
    category: Category
    incidents: list[IncidentReading] = Field(default_factory=list)
    rationale: str = ""
    # filled in by the reader wrapper, not by the model
    reader: str = ""
    model: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    error: str | None = None


def llm_json_schema() -> dict:
    """The schema the model must fill (without the bookkeeping fields)."""
    inc = IncidentReading.model_json_schema()
    return {
        "type": "object",
        "properties": {
            "category": {"type": "string", "enum": ["operational", "noise", "unconfirmed"]},
            "incidents": {"type": "array", "items": {
                "type": "object",
                "properties": {k: v for k, v in inc["properties"].items()},
                "required": ["kind", "supplier", "part", "plant", "shipment_id", "lot_id",
                             "date_from", "date_to", "evidence"],
            }},
            "rationale": {"type": "string"},
        },
        "required": ["category", "incidents", "rationale"],
    }
