from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BandConfig:
    enabled: bool = os.getenv("BAND_ENABLED", "false").lower() == "true"
    api_key: str = os.getenv("BAND_API_KEY", "")
    agent_id: str = os.getenv("BAND_AGENT_ID", "")
    rest_url: str = os.getenv("BAND_REST_URL", "https://app.band.ai").rstrip("/")
    ws_url: str = os.getenv("BAND_WS_URL", "wss://app.band.ai/api/v1/socket/websocket")
    timeout: float = float(os.getenv("BAND_TIMEOUT_SECONDS", "15"))


def band_config() -> BandConfig:
    return BandConfig()
