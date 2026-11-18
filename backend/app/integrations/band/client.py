from __future__ import annotations

import httpx

from .exceptions import BandAuthenticationError, BandConnectionError


class BandRestClient:
    """Direct client for verified BAND Agent API endpoints."""

    def __init__(self, rest_url: str, api_key: str, timeout: float = 15.0) -> None:
        self.rest_url = rest_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key, "Content-Type": "application/json"}

    async def get_profile(self) -> dict:
        return await self._request("GET", "/api/v1/agent/me")

    async def create_chat(self, title: str | None = None) -> dict:
        payload = {"chat": {"title": title}} if title else {}
        return await self._request("POST", "/api/v1/agent/chats", json=payload)

    async def send_message(self, chat_id: str, content: str, mentions: list[dict]) -> dict:
        payload = {"message": {"content": content, "mentions": mentions}}
        return await self._request("POST", f"/api/v1/agent/chats/{chat_id}/messages", json=payload)

    async def publish_event(self, chat_id: str, event_type: str, content: str, metadata: dict | None = None) -> dict:
        event = {"message_type": event_type, "content": content}
        if metadata is not None:
            event["metadata"] = metadata
        return await self._request("POST", f"/api/v1/agent/chats/{chat_id}/events", json={"event": event})

    async def get_context(self, chat_id: str, limit: int = 50) -> dict:
        return await self._request("GET", f"/api/v1/agent/chats/{chat_id}/context", params={"limit": limit})

    async def list_tasks(self, chat_id: str) -> dict:
        return await self._request("GET", f"/api/v1/agent/chats/{chat_id}/tasks")

    async def get_task(self, chat_id: str, task_id: str) -> dict:
        return await self._request("GET", f"/api/v1/agent/chats/{chat_id}/tasks/{task_id}")

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(method, self.rest_url + path, headers=self._headers(), **kwargs)
        except httpx.TimeoutException as exc:
            raise BandConnectionError("BAND request timed out") from exc
        except httpx.RequestError as exc:
            raise BandConnectionError("Could not reach BAND") from exc
        if response.status_code in (401, 403):
            raise BandAuthenticationError("BAND rejected the agent API key")
        if response.status_code >= 400:
            raise BandConnectionError(f"BAND returned HTTP {response.status_code}")
        if response.status_code == 204:
            return {}
        return response.json()
