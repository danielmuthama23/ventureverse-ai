"""Qdrant-backed evidence store with payload filters (agent, mission)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from qdrant_client import QdrantClient, models

from .. import data_loader
from ..config import settings
from .embedder import Embedder, HashingEmbedder, OllamaEmbedder

BASE_SCOPE = ""  # payload mission_id of the shared sample corpus


@dataclass
class Hit:
    id: str
    score: float
    payload: dict[str, Any]


class EvidenceStore:
    def __init__(self, embedder: Embedder, url: str = ":memory:", collection: str = "venture_evidence") -> None:
        self.embedder = embedder
        self.collection = collection
        self.client = QdrantClient(":memory:") if url == ":memory:" else QdrantClient(url=url)
        if self.client.collection_exists(collection):
            self.client.delete_collection(collection)
        self.client.create_collection(
            collection, vectors_config=models.VectorParams(size=embedder.dim, distance=models.Distance.COSINE)
        )
        self.count = 0

    @staticmethod
    def _pid(doc_id: str, scope: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{scope}/{doc_id}"))

    def upsert(self, doc_id: str, text: str, payload: dict[str, Any], scope: str = BASE_SCOPE) -> None:
        self.client.upsert(
            self.collection,
            points=[
                models.PointStruct(
                    id=self._pid(doc_id, scope),
                    vector=self.embedder.embed(text),
                    payload={**payload, "doc_id": doc_id, "mission_id": scope},
                )
            ],
        )
        self.count += 1

    def search(self, query: str, k: int = 6, *, agent: str | None = None, scope: str | None = None) -> list[Hit]:
        must: list[models.Condition] = [
            models.FieldCondition(key="mission_id", match=models.MatchAny(any=[BASE_SCOPE, scope or BASE_SCOPE]))
        ]
        if agent:
            must.append(models.FieldCondition(key="agent", match=models.MatchValue(value=agent)))
        res = self.client.query_points(
            self.collection, query=self.embedder.embed(query), limit=k, query_filter=models.Filter(must=must)
        )
        return [Hit(id=p.payload["doc_id"], score=float(p.score), payload=p.payload) for p in res.points]

    def size(self, scope: str | None = None) -> int:
        flt = models.Filter(
            must=[models.FieldCondition(key="mission_id", match=models.MatchAny(any=[BASE_SCOPE, scope or BASE_SCOPE]))]
        )
        return self.client.count(self.collection, count_filter=flt, exact=True).count


_store: EvidenceStore | None = None


def build_embedder() -> Embedder:
    if settings.embed_mode == "ollama":
        return OllamaEmbedder(settings.ollama_url, settings.embed_model)
    return HashingEmbedder()


def get_store() -> EvidenceStore:
    """Process-wide store, filled once with the sample corpus."""
    global _store
    if _store is None:
        store = EvidenceStore(build_embedder(), settings.qdrant_url, settings.collection)
        for c in data_loader.claims():
            if c["extra"]:  # follow-up evidence is indexed per mission, only when the founder requests research
                continue
            store.upsert(
                c["id"],
                f'{c["claim"]} {c["text"]} {c["source"]}',
                {"agent": c["agent"], "collection": c["collection"], "title": c["source"], "text": c["text"], "is_claim": True},
            )
        _store = store
    return _store


def index_claim(store: EvidenceStore, c: dict, scope: str) -> None:
    store.upsert(
        c["id"],
        f'{c["claim"]} {c["text"]} {c["source"]}',
        {"agent": c["agent"], "collection": c["collection"], "title": c["source"], "text": c["text"], "is_claim": True},
        scope=scope,
    )


def reset_store() -> None:
    global _store
    _store = None
