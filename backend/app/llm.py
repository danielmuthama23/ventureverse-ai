"""LLM client. Talks to a local Ollama server (open-weight gpt-oss) and falls
back to an offline template, so the app never needs a paid API."""
from __future__ import annotations

import time

import httpx

from .config import settings

_health: tuple[float, bool] = (0.0, False)


async def ollama_up() -> bool:
    """Cached reachability check (30 s)."""
    global _health
    now = time.monotonic()
    if now - _health[0] < 30 and _health[0] > 0:
        return _health[1]
    try:
        async with httpx.AsyncClient(timeout=1.0) as c:
            ok = (await c.get(f"{settings.ollama_url}/api/tags")).status_code == 200
    except Exception:
        ok = False
    _health = (now, ok)
    return ok


async def backend_name() -> str:
    if settings.llm_mode == "offline":
        return "offline-template"
    return f"ollama:{settings.llm_model}" if await ollama_up() else "offline-template"


async def generate(system: str, prompt: str, fallback: str) -> tuple[str, str]:
    """Returns (text, backend). Uses the fallback text when Ollama is unavailable."""
    if settings.llm_mode == "offline" or not await ollama_up():
        if settings.llm_mode == "ollama":
            raise RuntimeError("LLM_MODE=ollama but the Ollama server is unreachable")
        return fallback, "offline-template"
    try:
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(
                f"{settings.ollama_url}/api/chat",
                json={
                    "model": settings.llm_model,
                    "stream": False,
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                },
            )
            r.raise_for_status()
            text = r.json()["message"]["content"].strip()
            return (text or fallback), f"ollama:{settings.llm_model}"
    except Exception:
        if settings.llm_mode == "ollama":
            raise
        return fallback, "offline-template"
