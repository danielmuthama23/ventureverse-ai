"""Tamper-evident decision ledger.

Each entry holds the SHA-256 of its payload and of the previous entry, so
editing any record breaks verification. Only hashes would leave the machine.
`SimulatedHCS` stands in for Hedera Consensus Service: swap it for a client
that submits `message` to a real topic using the Hedera SDK."""
from __future__ import annotations

import copy
import hashlib
import json
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

GENESIS = "0" * 64


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class Anchor(Protocol):
    topic: str

    def submit(self, message: str) -> str: ...


class SimulatedHCS:
    """No network call. Returns a transaction id shaped like Hedera's."""

    def __init__(self) -> None:
        self.topic = f"0.0.{random.randint(7_000_000, 7_999_999)}"

    def submit(self, message: str) -> str:
        return f"{self.topic}@{int(time.time())}.{random.randint(0, 999_999_999):09d}"


@dataclass
class Entry:
    seq: int
    ts: str
    type: str
    payload: dict
    payload_hash: str
    prev: str
    entry_hash: str
    tx: str


@dataclass
class Ledger:
    anchor: Anchor = field(default_factory=SimulatedHCS)
    entries: list[Entry] = field(default_factory=list)
    _backup: dict | None = None

    @property
    def topic(self) -> str:
        return self.anchor.topic

    @staticmethod
    def _entry_hash(prev: str, seq: int, ts: str, type_: str, payload_hash: str) -> str:
        return sha256("|".join([prev, str(seq), ts, type_, payload_hash]))

    def record(self, type_: str, payload: dict) -> Entry:
        prev = self.entries[-1].entry_hash if self.entries else GENESIS
        seq, ts = len(self.entries) + 1, datetime.now(timezone.utc).isoformat()
        payload = copy.deepcopy(payload)
        ph = sha256(canonical(payload))
        eh = self._entry_hash(prev, seq, ts, type_, ph)
        tx = self.anchor.submit(canonical({"type": type_, "seq": seq, "payloadHash": ph}))
        e = Entry(seq, ts, type_, payload, ph, prev, eh, tx)
        self.entries.append(e)
        return e

    def verify(self) -> list[dict]:
        out, prev = [], GENESIS
        for e in self.entries:
            payload_ok = sha256(canonical(e.payload)) == e.payload_hash
            link_ok = e.prev == prev and self._entry_hash(e.prev, e.seq, e.ts, e.type, e.payload_hash) == e.entry_hash
            out.append({"seq": e.seq, "payload_ok": payload_ok, "link_ok": link_ok})
            prev = e.entry_hash
        return out

    # Demo helpers: show that verification catches edits.
    def tamper(self) -> bool:
        if not self.entries:
            return False
        if self._backup is None:
            self._backup = copy.deepcopy(self.entries[0].payload)
        self.entries[0].payload["tampered"] = True
        return True

    def restore(self) -> bool:
        if self._backup is None:
            return False
        self.entries[0].payload = self._backup
        self._backup = None
        return True
