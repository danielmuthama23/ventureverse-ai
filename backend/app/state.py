"""In-memory mission state. One Mission per founder session."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from .ledger import Ledger


@dataclass
class Mission:
    idea: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created: float = field(default_factory=time.time)
    ended: float | None = None
    done: set[str] = field(default_factory=set)
    found: list[str] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)
    verdicts: dict[str, dict] = field(default_factory=dict)
    excluded: set[str] = field(default_factory=set)
    score: int = 0
    streak: int = 0
    run_ms: float = 0.0
    manual_minutes: int = 0
    researched: bool = False
    weak: list[dict] = field(default_factory=list)
    weak_scored: bool = False
    weak_city: str | None = None
    approved: bool = False
    report: dict | None = None
    ledger: Ledger = field(default_factory=Ledger)
    rec: dict | None = None  # {"city": str, "scores": {...}}

    @property
    def combo(self) -> float:
        return 1 + min(self.streak, 4) * 0.25


class MissionStore:
    def __init__(self) -> None:
        self._m: dict[str, Mission] = {}

    def create(self, idea: str) -> Mission:
        m = Mission(idea=idea)
        self._m[m.id] = m
        return m

    def get(self, mission_id: str) -> Mission | None:
        return self._m.get(mission_id)


missions = MissionStore()
