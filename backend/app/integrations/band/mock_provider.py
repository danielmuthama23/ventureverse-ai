from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from .schemas import AgentMessage, TaskRecord


class MockBandProvider:
    """Deterministic local provider for development and tests."""

    def __init__(self) -> None:
        self.connected = False
        self.agents: dict[str, dict[str, Any]] = {}
        self.messages: dict[str, AgentMessage] = {}
        self.tasks: dict[str, TaskRecord] = {}
        self.events: list[dict[str, Any]] = []
        self.context: dict[str, dict[str, Any]] = {}
        self.last_sync: str | None = None

    async def connect(self) -> dict[str, Any]:
        self.connected = True
        self.last_sync = datetime.utcnow().isoformat()
        return {"connected": True, "mode": "mock", "authentication": "simulated"}

    async def disconnect(self) -> None:
        self.connected = False

    async def register_agent(self, registration: dict[str, Any]) -> dict[str, Any]:
        agent_id = registration["agent_id"]
        self.agents[agent_id] = registration
        return {"registered": True, "agent_id": agent_id, "provider": "mock"}

    async def send_message(self, message: AgentMessage) -> AgentMessage:
        if message.message_id in self.messages:
            return self.messages[message.message_id]
        delivered = message.model_copy(update={"status": "delivered"})
        self.messages[delivered.message_id] = delivered
        self.last_sync = datetime.utcnow().isoformat()
        return delivered

    async def receive_message(self) -> list[AgentMessage]:
        return list(self.messages.values())

    async def delegate_task(self, task: TaskRecord) -> TaskRecord:
        self.tasks[task.task_id] = task
        return task

    async def publish_event(self, event: dict[str, Any]) -> dict[str, Any]:
        stored = {**event, "event_id": event.get("event_id") or uuid.uuid4().hex}
        self.events.append(stored)
        self.last_sync = datetime.utcnow().isoformat()
        return stored

    async def get_task_status(self, task_id: str) -> TaskRecord | None:
        return self.tasks.get(task_id)

    async def retrieve_shared_context(self, workflow_id: str) -> list[dict[str, Any]]:
        return [v for v in self.context.values() if v.get("workflow_id") == workflow_id]
