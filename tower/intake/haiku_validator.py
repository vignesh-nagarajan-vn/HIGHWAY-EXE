"""VALIDATOR: Claude Haiku as an independent third reader.

Called only when READER-A (local SLM) and READER-B (grammar) ground to different results, so the
bigger model audits instead of doing the routine work. Uses the same prompt and the same schema
(through structured outputs), so its vote is directly comparable.
"""
from __future__ import annotations

import json
import time

from pydantic import ValidationError

from ..config import settings
from .prompts import READER_SYSTEM, reader_user
from .schemas import EventReading

_NULLABLE = {"type": ["string", "null"]}
STRICT_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": ["operational", "noise", "unconfirmed"]},
        "incidents": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["supplier_delay", "plant_outage", "quality_hold"]},
                    "supplier": _NULLABLE, "part": _NULLABLE, "plant": _NULLABLE,
                    "shipment_id": _NULLABLE, "lot_id": _NULLABLE,
                    "date_from": _NULLABLE, "date_to": _NULLABLE,
                    "evidence": {"type": "string"},
                },
                "required": ["kind", "supplier", "part", "plant", "shipment_id", "lot_id",
                             "date_from", "date_to", "evidence"],
                "additionalProperties": False,
            },
        },
        "rationale": {"type": "string"},
    },
    "required": ["category", "incidents", "rationale"],
    "additionalProperties": False,
}


def available() -> bool:
    return bool(settings().anthropic_key)


def read(event: dict) -> EventReading:
    cfg = settings()
    if not cfg.anthropic_key:
        return EventReading(category="unconfirmed", reader="haiku", model=cfg.anthropic_model,
                            error="ANTHROPIC_API_KEY not set")
    import anthropic

    client = anthropic.Anthropic(api_key=cfg.anthropic_key, timeout=60.0, max_retries=2)
    t0 = time.perf_counter()
    try:
        resp = client.messages.create(
            model=cfg.anthropic_model,
            max_tokens=2000,
            system=READER_SYSTEM,
            messages=[{"role": "user", "content": reader_user(event["text"], event.get("source", ""))}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": STRICT_SCHEMA}},
        )
    except anthropic.APIStatusError as e:
        return EventReading(category="unconfirmed", reader="haiku", model=cfg.anthropic_model,
                            error=f"anthropic {e.status_code}: {e.message}"[:300])
    except anthropic.APIConnectionError as e:
        return EventReading(category="unconfirmed", reader="haiku", model=cfg.anthropic_model,
                            error=f"anthropic connection error: {e}"[:300])
    latency = int((time.perf_counter() - t0) * 1000)
    meta = {"reader": "haiku", "model": cfg.anthropic_model, "latency_ms": latency,
            "tokens_in": resp.usage.input_tokens, "tokens_out": resp.usage.output_tokens}
    if resp.stop_reason == "refusal":
        return EventReading(category="unconfirmed", error="validator refused", **meta)
    text = next((b.text for b in resp.content if b.type == "text"), "")
    try:
        reading = EventReading.model_validate(json.loads(text))
    except (ValueError, ValidationError) as e:
        return EventReading(category="unconfirmed", error=f"invalid validator output: {e}"[:300], **meta)
    if reading.category != "operational":
        reading.incidents = []
    return reading.model_copy(update=meta)
