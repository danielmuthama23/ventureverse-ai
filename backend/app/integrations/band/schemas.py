from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


class AgentRegistration(BaseModel):
    agent_id: str
    name: str
    description: str
    capabilities: list[str]


class AgentMessage(BaseModel):
    message_id: str
    correlation_id: str
    task_id: str | None = None
    sender_agent: str
    recipient_agent: str
    message_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: dict[str, Any] = Field(default_factory=dict)
    requires_response: bool = False
    status: Literal["pending", "delivered", "failed", "completed"] = "pending"


class TaskRecord(BaseModel):
    task_id: str
    workflow_id: str
    subject: str
    assignee: str
    dependencies: list[str] = Field(default_factory=list)
    status: Literal["pending", "in_progress", "blocked", "completed", "failed"] = "pending"
    result: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ContextReference(BaseModel):
    context_id: str
    workflow_id: str
    originating_agent: str
    source_document: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    relevance: float = Field(ge=0, le=1)
    version: int = 1
    payload: dict[str, Any] = Field(default_factory=dict)
