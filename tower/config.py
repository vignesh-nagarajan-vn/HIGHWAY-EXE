"""Paths and runtime settings. Everything can be overridden from the environment or .env."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

ROOT = Path(__file__).resolve().parent.parent
if load_dotenv:
    load_dotenv(ROOT / ".env")

PACKAGE_DIR = ROOT / "vendor" / "hack_the_highway_package"
DATA_DIR = PACKAGE_DIR / "data"
EVENTS_PATH = DATA_DIR / "events.json"
HANDBOOK_PATH = DATA_DIR / "policy_handbook.md"
RUNS_DIR = ROOT / "runs"


@dataclass(frozen=True)
class Settings:
    ollama_url: str = field(default_factory=lambda: os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"))
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "qwen3:4b"))
    anthropic_model: str = field(default_factory=lambda: os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5"))
    anthropic_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    enterprise_url: str = field(default_factory=lambda: os.getenv("ENTERPRISE_URL", "http://127.0.0.1:8000"))
    # Rule 3 says a transfer may go to "any day with a free slot"; "today" is the literal reading.
    transfer_from: str = field(default_factory=lambda: os.getenv("TRANSFER_FROM", "today"))


def settings() -> Settings:
    return Settings()
