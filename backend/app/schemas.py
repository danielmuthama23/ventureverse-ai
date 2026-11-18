"""API request and response models."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["verified", "estimate", "hypothesis"]


class MissionCreate(BaseModel):
    idea: str = Field(min_length=12, max_length=1000)


class LabelRequest(BaseModel):
    label: Status


class CheckpointAction(BaseModel):
    action: Literal["approve", "challenge", "research"]
    weaknesses: list[int] = Field(default_factory=list, description="Indexes of weaknesses the founder believes are real")


class RagSearch(BaseModel):
    query: str = Field(min_length=2, max_length=300)
    k: int = Field(default=5, ge=1, le=10)
    mission_id: str | None = None


class RagIngest(BaseModel):
    mission_id: str
    text: str = Field(min_length=8, max_length=2000)


class ScenarioRequest(BaseModel):
    budget: float = Field(ge=0, le=1_000_000)
    cost_per_customer: float = Field(gt=0, le=100_000)
    churn: float = Field(gt=0, lt=1)


class AgentMessageRequest(BaseModel):
    correlation_id: str = Field(min_length=1, max_length=128)
    task_id: str | None = None
    sender_agent: str = Field(min_length=1, max_length=64)
    recipient_agent: str = Field(min_length=1, max_length=64)
    message_type: str = Field(min_length=1, max_length=128)
    payload: dict = Field(default_factory=dict)
    requires_response: bool = False


class TaskDelegationRequest(BaseModel):
    workflow_id: str = Field(min_length=1, max_length=128)
    assignee: str = Field(min_length=1, max_length=64)
    subject: str = Field(min_length=1, max_length=300)
    dependencies: list[str] = Field(default_factory=list)
