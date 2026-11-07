"""Minimal Ollama chat client (local SLM on the laptop GPU)."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass

import httpx

from ..config import settings


@dataclass
class LLMResult:
    text: str
    model: str
    tokens_in: int
    tokens_out: int
    latency_ms: int


class LLMUnavailable(RuntimeError):
    pass


def ollama_chat(system: str, user: str, schema: dict | None = None, model: str | None = None,
                temperature: float = 0.0, num_predict: int = 900, timeout: float = 180.0) -> LLMResult:
    cfg = settings()
    model = model or cfg.ollama_model
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": False,
        "think": False,
        "keep_alive": "30m",
        "options": {"temperature": temperature, "num_ctx": 4096, "num_predict": num_predict, "seed": 7},
    }
    if schema is not None:
        body["format"] = schema
    t0 = time.perf_counter()
    try:
        r = httpx.post(f"{cfg.ollama_url}/api/chat", json=body, timeout=timeout)
        if r.status_code == 400 and "think" in r.text:      # models without a thinking switch
            body.pop("think")
            r = httpx.post(f"{cfg.ollama_url}/api/chat", json=body, timeout=timeout)
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise LLMUnavailable(f"ollama: {e}") from e
    data = r.json()
    return LLMResult(
        text=data.get("message", {}).get("content", ""),
        model=model,
        tokens_in=int(data.get("prompt_eval_count", 0) or 0),
        tokens_out=int(data.get("eval_count", 0) or 0),
        latency_ms=int((time.perf_counter() - t0) * 1000),
    )


def ollama_available(model: str | None = None) -> bool:
    cfg = settings()
    try:
        r = httpx.get(f"{cfg.ollama_url}/api/tags", timeout=3)
        names = {m["name"] for m in r.json().get("models", [])}
        want = model or cfg.ollama_model
        return want in names or f"{want}:latest" in names
    except (httpx.HTTPError, ValueError, KeyError):
        return False


def warmup(model: str | None = None) -> bool:
    """Load the model into GPU memory before the first real event (cold loads can take a while)."""
    try:
        ollama_chat("Reply with OK.", "ping", model=model, num_predict=2, timeout=600)
        return True
    except LLMUnavailable:
        return False


def parse_json(text: str) -> dict:
    """Parse model output, tolerating code fences or leading chatter."""
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t[t.find("{"):]
    start, end = t.find("{"), t.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("no JSON object in model output")
    return json.loads(t[start:end + 1])
