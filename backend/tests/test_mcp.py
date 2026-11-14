import pytest
from mcp.client import Client

from app.tools.gateway import ToolError, call_tool
from mcp_server.server import server


async def test_server_lists_tools():
    async with Client(server) as c:
        names = {t.name for t in (await c.list_tools()).tools}
    assert names == {"search_evidence", "competitors_search", "segments_discover", "leads_find", "scenario_simulate"}


async def test_search_evidence_through_protocol():
    hits = await call_tool("search_evidence", {"query": "commission rates competitors charge", "k": 3})
    assert len(hits) == 3 and hits[0]["score"] >= hits[-1]["score"]
    assert all("verified" not in h and "truth" not in h for h in hits)  # statuses are withheld


async def test_agent_filter():
    hits = await call_tool("search_evidence", {"query": "farmers", "agent": "leads", "k": 10})
    assert hits and {h["id"][0] for h in hits} == {"L"}


async def test_scenario_and_validation():
    r = await call_tool("scenario_simulate", {"budget": 1500, "cost_per_customer": 22, "churn": 0.08})
    assert len(r["series"]) == 13 and r["steady_state"] == pytest.approx(852.3, abs=0.1)
    with pytest.raises(ToolError):
        await call_tool("scenario_simulate", {"budget": 1, "cost_per_customer": 0, "churn": 0.1})
