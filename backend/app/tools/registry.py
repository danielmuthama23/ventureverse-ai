"""Plain functions the agents call. They are exposed to agents as MCP tools by
mcp_server/server.py, so every call goes through the Model Context Protocol."""
from __future__ import annotations

from .. import data_loader
from ..rag.store import get_store


def search_evidence(query: str, agent: str | None = None, k: int = 6, mission_id: str | None = None) -> list[dict]:
    """Semantic search over the evidence store (Qdrant). Statuses are withheld: the founder decides them."""
    by_id = data_loader.claim_by_id()
    out = []
    for h in get_store().search(query, k, agent=agent, scope=mission_id):
        c = by_id.get(h.id)
        out.append(
            {
                "id": h.id,
                "score": round(h.score, 4),
                "title": h.payload["title"],
                "text": h.payload["text"],
                "url": c["url"] if c else None,
                "collection": h.payload["collection"],
            }
        )
    return out


def competitors_search(region: str = "KE", limit: int = 5) -> list[dict]:
    """Tracked competitors with pricing and overlap. Sample data."""
    comps = data_loader.venture()["competitors"]
    return [
        {k: c[k] for k in ("id", "name", "kind", "price", "strength", "overlap", "good", "bad")}
        for c in sorted(comps, key=lambda c: -c["overlap"])[:limit]
    ]


def segments_discover() -> list[dict]:
    """Customer segments with relative size and pain. Hypotheses until the founder interviews them."""
    return [
        {k: s[k] for k in ("id", "name", "size", "pain", "channel")} | {"status": "hypothesis"}
        for s in data_loader.venture()["segments"]
    ]


def leads_find(min_fit: int = 0) -> list[dict]:
    """Candidate leads ranked by fit. Unverified: the founder chooses who to contact."""
    leads = [l for l in data_loader.venture()["leads"] if l["fit"] >= min_fit]
    return [l | {"status": "unverified"} for l in sorted(leads, key=lambda l: -l["fit"])]


def scenario_simulate(budget: float, cost_per_customer: float, churn: float, months: int = 12) -> dict:
    """Active customers over time: a scenario, not a forecast."""
    if cost_per_customer <= 0 or not 0 < churn < 1 or budget < 0:
        raise ValueError("cost_per_customer must be > 0, churn in (0,1), budget >= 0")
    series, active = [0.0], 0.0
    for _ in range(months):
        active = active * (1 - churn) + budget / cost_per_customer
        series.append(round(active, 2))
    return {"series": series, "steady_state": round(budget / cost_per_customer / churn, 1)}
