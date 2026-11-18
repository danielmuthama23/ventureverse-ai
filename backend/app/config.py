"""Runtime settings, read from environment variables (see ../.env.example)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


@dataclass(frozen=True)
class Settings:
    # LLM: open-weight model served locally by Ollama. "auto" falls back to an
    # offline template when Ollama is unreachable, so the app always runs.
    llm_mode: str = os.getenv("LLM_MODE", "auto")  # auto | ollama | offline
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-oss:20b")
    embed_mode: str = os.getenv("EMBED_MODE", "hashing")  # hashing | ollama
    embed_model: str = os.getenv("EMBED_MODEL", "nomic-embed-text")
    # Vector database. ":memory:" runs Qdrant in-process, otherwise a server URL.
    qdrant_url: str = os.getenv("QDRANT_URL", ":memory:")
    collection: str = os.getenv("QDRANT_COLLECTION", "venture_evidence")
    # Demo-only endpoints (ledger tampering) are on unless disabled.
    demo_mode: bool = os.getenv("DEMO_MODE", "true").lower() == "true"
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            o.strip()
            for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
            if o.strip()
        )
    )
    # BAND agent-to-agent collaboration. Live provider is opt-in.
    band_enabled: bool = os.getenv("BAND_ENABLED", "false").lower() == "true"
    band_api_key: str = os.getenv("BAND_API_KEY", "")
    band_agent_id: str = os.getenv("BAND_AGENT_ID", "")
    band_rest_url: str = os.getenv("BAND_REST_URL", "https://app.band.ai").rstrip("/")
    band_ws_url: str = os.getenv("BAND_WS_URL", "wss://app.band.ai/api/v1/socket/websocket")


settings = Settings()
