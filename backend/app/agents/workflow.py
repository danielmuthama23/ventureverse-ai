from __future__ import annotations

import asyncio
from typing import Any

from .. import data_loader
from ..state import Mission
from . import orchestrator
from .collaboration import collaboration


async def run_collaborative(m: Mission) -> dict[str, Any]:
    workflow_id = f"workflow-{m.id}"
    await collaboration.publish(workflow_id, "workflow.started", "Collaborative venture evaluation started", {"idea": m.idea})
    await collaboration.register([
        *data_loader.agents(),
        {"id": "orchestrator-agent", "name": "VentureVerse Orchestrator", "focus": "workflow coordination and delegation", "tool": "workflow_orchestrate"},
    ])
    tasks: list[dict[str, Any]] = []

    async def run_one(agent_id: str, recipient: str = "orchestrator") -> dict:
        task = await collaboration.delegate(workflow_id, agent_id, f"Execute {agent_id}", [])
        await collaboration.send("orchestrator-agent", agent_id, workflow_id, "task.assigned", {"task_id": task.task_id, "idea": m.idea}, task.task_id)
        result = await orchestrator.run_agent(m, agent_id)
        completed = await collaboration.complete_task(task.task_id, {"summary": result["summary"], "claim_ids": result["claim_ids"]})
        await collaboration.send(agent_id, recipient, workflow_id, f"{agent_id}.completed", {"summary": result["summary"], "claim_ids": result["claim_ids"]}, task.task_id, True)
        tasks.append({"task_id": task.task_id, "agent": agent_id, "status": completed.status})
        collaboration.add_context(workflow_id, agent_id, f"mission:{m.id}", {"summary": result["summary"], "claim_ids": result["claim_ids"]}, 0.9)
        return result

    await run_one("founder")
    first_wave = await asyncio.gather(run_one("market"), run_one("competitor"), run_one("customer"))
    await run_one("leads")
    await run_one("growth")
    await run_one("critic")

    return {
        "workflow_id": workflow_id,
        "mission_id": m.id,
        "status": "waiting_for_human",
        "tasks": tasks,
        "parallel_wave": [r["agent"] for r in first_wave],
        "checkpoint_required": True,
    }
