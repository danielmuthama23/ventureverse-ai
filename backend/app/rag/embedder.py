"""Embedders. The hashing embedder is dependency-free and deterministic, so the
whole stack runs offline. The Ollama embedder uses a real open-weight model."""
from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

import httpx

STOP = set(
    "a an the and or of to in on for with is are was be by as at it its that this from will can have has "
    "not no so if but into than then them their these those our your you we i about more most who which what how".split()
)


def tokenize(text: str) -> list[str]:
    words = [w for w in re.sub(r"[^a-z0-9 ]+", " ", text.lower()).split() if w and w not in STOP]
    return [w[:-1] if len(w) > 4 and w.endswith("s") else w for w in words]


class Embedder(Protocol):
    dim: int

    def embed(self, text: str) -> list[float]: ...


class HashingEmbedder:
    """Signed feature hashing of unigrams and bigrams, L2-normalised."""

    def __init__(self, dim: int = 512) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        toks = tokenize(text)
        feats = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
        vec = [0.0] * self.dim
        counts: dict[str, int] = {}
        for f in feats:
            counts[f] = counts.get(f, 0) + 1
        for f, c in counts.items():
            h = int.from_bytes(hashlib.blake2b(f.encode(), digest_size=8).digest(), "big")
            vec[h % self.dim] += (1.0 if (h >> 40) & 1 else -1.0) * (1 + math.log(c))
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


class OllamaEmbedder:
    """Embeddings from a local Ollama server (for example nomic-embed-text)."""

    def __init__(self, url: str, model: str) -> None:
        self.url, self.model = url.rstrip("/"), model
        self.dim = len(self.embed("dimension probe"))

    def embed(self, text: str) -> list[float]:
        r = httpx.post(f"{self.url}/api/embeddings", json={"model": self.model, "prompt": text}, timeout=30)
        r.raise_for_status()
        return r.json()["embedding"]
