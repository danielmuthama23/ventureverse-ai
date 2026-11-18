from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from ..integrations.band.adapter import BandIntegrationAdapter
from ..integrations.band.schemas import AgentMessage, TaskRecord


class CollaborationStore:
    def __init__(self) -> None:
        self.adapter = BandIntegrationAdapter()
        self.messages: dict[str, AgentMessage] = {}
        self.tasks: dict[str, TaskRecord] = {}
        self.events: list[dict[str, Any]] = []
        self.context: dict[str, dict[str, Any]] = {}

    async def connect(self) -> dict[str, Any]:
        return await self.adapter.connect()

    async def register(self, agents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results = []
        for agent in agents:
            registration = {
                "agent_id": agent["id"],
                "name": agent["name"],
                "description": agent.get("focus", "VentureVerse agent"),
                "capabilities": [agent.get("tool", "research")],
            }
            results.append(await self.adapter.register_agent(registration))
        return results

    async def send(self, sender: str, recipient: str, correlation_id: str,
                   message_type: str, payload: dict[str, Any], task_id: str | None = None,
                   requires_response: bool = False) -> AgentMessage:
        message = AgentMessage(
            message_id=uuid.uuid4().hex,
            correlation_id=correlation_id,
            task_id=task_id,
            sender_agent=sender,
            recipient_agent=recipient,
            message_type=message_type,
            payload=payload,
            requires_response=requires_response,
        )
        delivered = await self.adapter.send_message(message)
        self.messages[delivered.message_id] = delivered
        self.events.append({
            "event_id": uuid.uuid4().hex,
            "workflow_id": correlation_id,
            "task_id": task_id,
            "type": "agent.message",
            "summary": f"{sender} -> {recipient}: {message_type}",
            "timestamp": datetime.utcnow().isoformat(),
            "sender": sender,
            "recipient": recipient,
        })
        return delivered

    async def delegate(self, workflow_id: str, assignee: str, subject: str,
                       dependencies: list[str], result: dict[str, Any] | None = None) -> TaskRecord:
        task = TaskRecord(
            task_id=uuid.uuid4().hex,
            workflow_id=workflow_id,
            subject=subject,
            assignee=assignee,
            dependencies=dependencies,
            status="in_progress",
            result=result,
        )
        saved = await self.adapter.delegate_task(task)
        self.tasks[saved.task_id] = saved
        self.events.append({
            "event_id": uuid.uuid4().hex,
            "workflow_id": workflow_id,
            "task_id": saved.task_id,
            "type": "task.delegated",
            "summary": f"Delegated {subject} to {assignee}",
            "timestamp": datetime.utcnow().isoformat(),
        })
        return saved

    async def complete_task(self, task_id: str, result: dict[str, Any]) -> TaskRecord:
        task = self.tasks[task_id]
        completed = task.model_copy(update={"status": "completed", "result": result, "updated_at": datetime.utcnow()})
        self.tasks[task_id] = completed
        self.events.append({
            "event_id": uuid.uuid4().hex,
            "workflow_id": task.workflow_id,
            "task_id": task_id,
            "type": "task.completed",
            "summary": f"{task.assignee} completed {task.subject}",
            "timestamp": datetime.utcnow().isoformat(),
        })
        await self.adapter.publish_event(completed.model_dump(mode="json") | {"type": "task.completed"})
        return completed

    def add_context(self, workflow_id: str, agent_id: str, source: str,
                    payload: dict[str, Any], relevance: float = 1.0) -> dict[str, Any]:
        context_id = uuid.uuid4().hex
        ref = {
            "context_id": context_id,
            "workflow_id": workflow_id,
            "originating_agent": agent_id,
            "source_document": source,
            "created_at": datetime.utcnow().isoformat(),
            "relevance": relevance,
            "version": 1,
            "payload": payload,
        }
        self.context[context_id] = ref
        return ref

    async def publish(self, workflow_id: str, event_type: str, summary: str,
                      payload: dict[str, Any] | None = None) -> dict[str, Any]:
        event = {
            "event_id": uuid.uuid4().hex,
            "workflow_id": workflow_id,
            "type": event_type,
            "summary": summary,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload or {},
        }
        self.events.append(event)
        await self.adapter.publish_event(event)
        return event


collaboration = CollaborationStore()
