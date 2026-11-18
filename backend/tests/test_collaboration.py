import pytest

from app.integrations.band.mock_provider import MockBandProvider
from app.integrations.band.schemas import AgentMessage, TaskRecord
from app.agents.collaboration import collaboration


def test_mock_provider_auth_and_round_trip():
    import asyncio

    async def run():
        provider = MockBandProvider()
        assert (await provider.connect())["mode"] == "mock"
        assert await provider.register_agent({"agent_id": "research-agent", "name": "Research", "description": "Research", "capabilities": ["market"]}
        ) == {"registered": True, "agent_id": "research-agent", "provider": "mock"}
        message = AgentMessage(message_id="m1", correlation_id="w1", sender_agent="research-agent", recipient_agent="finance-agent", message_type="research.completed", payload={"findings": []})
        delivered = await provider.send_message(message)
        assert delivered.status == "delivered"
        assert len(await provider.receive_message()) == 1

    asyncio.run(run())


def test_duplicate_message_is_idempotent():
    import asyncio

    async def run():
        provider = MockBandProvider()
        await provider.connect()
        message = AgentMessage(message_id="same", correlation_id="w", sender_agent="a", recipient_agent="b", message_type="test")
        first = await provider.send_message(message)
        second = await provider.send_message(message)
        assert first == second
        assert len(provider.messages) == 1

    asyncio.run(run())


def test_task_delegation_and_status():
    import asyncio

    async def run():
        provider = MockBandProvider()
        await provider.connect()
        task = TaskRecord(task_id="t1", workflow_id="w1", subject="Research Kenya market", assignee="market")
        delegated = await provider.delegate_task(task)
        assert delegated.status == "pending"
        assert await provider.get_task_status("t1") == delegated

    asyncio.run(run())


def test_band_status_and_registry(client):
    status = client.get("/api/band/status")
    assert status.status_code == 200
    body = status.json()
    assert body["mode"] in ("mock", "band")
    if body["mode"] == "mock":
        assert body["authentication"] == "simulated"
    registry = client.get("/api/agents/registry")
    assert registry.status_code == 200
    ids = {a["agent_id"] for a in registry.json()["agents"]}
    assert ids == {"founder", "market", "competitor", "customer", "leads", "growth", "critic", "orchestrator-agent"}


def test_message_validation_duplicate_and_task_api(client, mission):
    mid = mission["id"]
    duplicate = {
        "correlation_id": f"workflow-{mid}",
        "sender_agent": "market",
        "recipient_agent": "growth",
        "message_type": "research.completed",
        "payload": {"summary": "Kenyan market findings"},
        "requires_response": True,
    }
    first = client.post("/api/agents/messages", json=duplicate)
    assert first.status_code == 200
    message_id = first.json()["message_id"]
    assert client.post("/api/agents/messages", json={**duplicate, "payload": {"summary": "changed"}}).status_code == 200
    assert client.post("/api/agents/delegate", json={"workflow_id": f"workflow-{mid}", "assignee": "growth", "subject": "Synthesize findings", "dependencies": ["market"]}).status_code == 200
    assert any(m["message_id"] == message_id for m in client.get("/api/agents/messages").json()["messages"])


def test_collaborative_workflow(client, mission):
    mid = mission["id"]
    workflow = client.post(f"/api/workflows/collaborative-venture/{mid}")
    assert workflow.status_code == 200
    body = workflow.json()
    assert body["status"] == "waiting_for_human"
    assert body["checkpoint_required"] is True
    assert set(body["parallel_wave"]) == {"market", "competitor", "customer"}
    view = client.get(f"/api/workflows/{body['workflow_id']}")
    assert view.status_code == 200
    assert view.json()["completed"] == 7
