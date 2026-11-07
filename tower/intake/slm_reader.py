"""READER-A: the local small language model reads the event into an EventReading."""
from __future__ import annotations

from pydantic import ValidationError

from .llm import LLMUnavailable, ollama_chat, parse_json
from .prompts import READER_SYSTEM, reader_user
from .schemas import EventReading, llm_json_schema


def read(event: dict, model: str | None = None) -> EventReading:
    try:
        res = ollama_chat(READER_SYSTEM, reader_user(event["text"], event.get("source", "")),
                          schema=llm_json_schema(), model=model)
    except LLMUnavailable as e:
        return EventReading(category="unconfirmed", reader="slm", model=model, error=str(e))
    try:
        reading = EventReading.model_validate(parse_json(res.text))
        err = None
    except (ValueError, ValidationError) as e:
        reading, err = EventReading(category="unconfirmed"), f"invalid model output: {e}"[:300]
    # schema-level guardrail: categories without incidents carry no incidents
    if reading.category != "operational":
        reading.incidents = []
    return reading.model_copy(update={
        "reader": "slm", "model": res.model, "tokens_in": res.tokens_in, "tokens_out": res.tokens_out,
        "latency_ms": res.latency_ms, "error": err,
    })
