"""Plain HTTP client for the organisers' enterprise server (GET /events, GET /tools, POST /act)."""
from __future__ import annotations

import time

import httpx

from ..config import settings


class TransportError(RuntimeError):
    pass


class EnterpriseHTTP:
    def __init__(self, base_url: str | None = None, timeout: float = 30.0):
        self.base = (base_url or settings().enterprise_url).rstrip("/")
        self.http = httpx.Client(timeout=timeout)

    def events(self) -> list[dict]:
        return self.http.get(f"{self.base}/events").json()

    def tools(self) -> list[dict]:
        return self.http.get(f"{self.base}/tools").json()

    def act(self, event_id: str, tool: str, args: dict, retries: int = 3) -> dict:
        """One tool call. Retries only transport failures; a 4xx tool error is returned as data."""
        last = None
        for attempt in range(retries):
            try:
                r = self.http.post(f"{self.base}/act", json={"event_id": event_id, "tool": tool, "args": args})
                body = r.json()
                if r.status_code == 200:
                    return {"ok": True, "result": body}
                return {"ok": False, "error": body.get("error", f"HTTP {r.status_code}")}
            except (httpx.TransportError, ValueError) as e:
                last = e
                time.sleep(0.3 * (2 ** attempt))
        raise TransportError(f"enterprise server unreachable: {last}")

    def alive(self) -> bool:
        try:
            return self.http.get(f"{self.base}/tools", timeout=3).status_code == 200
        except httpx.HTTPError:
            return False
