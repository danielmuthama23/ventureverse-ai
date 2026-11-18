from __future__ import annotations

from typing import Any

from .config import band_config
from .client import BandRestClient
from .exceptions import BandAuthenticationError
from .mock_provider import MockBandProvider
from .schemas import AgentMessage, TaskRecord


class BandIntegrationAdapter:
    """Provider-independent application adapter with a verified REST implementation and mock fallback."""

    def __init__(self) -> None:
        self.config = band_config()
        self.mode = "band" if self.config.enabled else "mock"
        self.connected = False
        self.last_sync: str | None = None
        self.last_error: str | None = None
        self.chat_id: str | None = None
        self._mock = MockBandProvider()
        self._client = None
        if self.mode == "band":
            self._client = BandRestClient(self.config.rest_url, self.config.api_key, self.config.timeout)

    async def connect(self) -> dict[str, Any]:
        self.last_error = None
        if self.mode == "mock":
            result = await self._mock.connect()
            self.connected = True
            self.last_sync = result["connected"] and __import__("datetime").datetime.utcnow().isoformat()
            return {**result, "authentication": "simulated", "last_sync": self.last_sync}
        if not self.config.api_key or not self.config.agent_id:
            self.connected = False
            self.last_error = "BAND_AGENT_ID and BAND_API_KEY are required"
            raise BandAuthenticationError(self.last_error)
        try:
            profile = await self._client.get_profile()
            if not profile:
                raise BandAuthenticationError("BAND profile validation returned no identity")
            self.connected = True
            self.last_sync = __import__("datetime").datetime.utcnow().isoformat()
            return {"connected": True, "mode": "band", "authentication": "agent_api_key", "profile": profile.get("data"), "last_sync": self.last_sync}
        except Exception as exc:
            self.connected = False
            self.last_error = str(exc)
            raise

    async def disconnect(self) -> None:
        self.connected = False
        if self.mode == "mock":
            await self._mock.disconnect()

    async def register_agent(self, registration: dict[str, Any]) -> dict[str, Any]:
        if self.mode == "mock":
            return await self._mock.register_agent(registration)
        return {"registered": True, "agent_id": registration["agent_id"], "provider": "band", "local_identity_only": True}

    async def send_message(self, message: AgentMessage) -> AgentMessage:
        if self.mode == "mock":
            return await self._mock.send_message(message)
        if not self.connected:
            await self.connect()
        if not self.chat_id:
            room = await self._client.create_chat(title=f"VentureVerse {message.correlation_id}")
            self.chat_id = room["data"]["id"]
        recipients = [{"handle": message.recipient_agent, "kind": "mention"}]
        content = f"@{message.recipient_agent} {message.message_type}: {message.payload.get('summary', '')}"
        await self._client.send_message(self.chat_id, content, recipients)
        return message.model_copy(update={"status": "delivered"})

    async def receive_message(self) -> list[AgentMessage]:
        return await self._mock.receive_message() if self.mode == "mock" else []

    async def delegate_task(self, task: TaskRecord) -> TaskRecord:
        if self.mode == "mock":
            return await self._mock.delegate_task(task)
        if not self.connected:
            await self.connect()
        if not self.chat_id:
            room = await self._client.create_chat(title=f"VentureVerse {task.workflow_id}")
            self.chat_id = room["data"]["id"]
        return task

    async def publish_event(self, event: dict[str, Any]) -> dict[str, Any]:
        if self.mode == "mock":
            return await self._mock.publish_event(event)
        if not self.connected:
            await self.connect()
        if not self.chat_id:
            room = await self._client.create_chat(title="VentureVerse collaboration")
            self.chat_id = room["data"]["id"]
        await self._client.publish_event(self.chat_id, "thought", str(event.get("summary", "Agent event")), event)
        return event

    async def get_task_status(self, task_id: str) -> TaskRecord | None:
        return await self._mock.get_task_status(task_id) if self.mode == "mock" else None

    async def retrieve_shared_context(self, workflow_id: str) -> list[dict[str, Any]]:
        return await self._mock.retrieve_shared_context(workflow_id) if self.mode == "mock" else []

    async def status(self) -> dict[str, Any]:
        if self.mode == "mock":
            await self.connect()
        return {
            "connected": self.connected,
            "mode": self.mode,
            "authentication": "simulated" if self.mode == "mock" else ("configured" if self.connected else "not_configured"),
            "last_sync": self.last_sync,
            "error": self.last_error,
            "real_sdk_enabled": self.mode == "band",
        }
