"""Loads the sample dataset. Everything in app/data is invented demo data."""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from .config import DATA_DIR


@lru_cache(maxsize=None)
def _load(name: str) -> Any:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def agents() -> list[dict]:
    return _load("agents.json")


def agent_by_id() -> dict[str, dict]:
    return {a["id"]: a for a in agents()}


def claims() -> list[dict]:
    return _load("claims.json")


def claim_by_id() -> dict[str, dict]:
    return {c["id"]: c for c in claims()}


def venture() -> dict:
    return _load("venture.json")
