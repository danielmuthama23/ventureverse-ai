"""Multi-agent orchestrator with a human checkpoint.

A small explicit state machine: agents unlock when their dependencies are done,
the critic runs last, and then the graph pauses until the founder acts. The
same shape maps onto LangGraph (nodes = agents, interrupt() at the checkpoint)
without adding a framework dependency here."""
from __future__ import annotations

import re
import time
import uuid
from typing import Any

from .. import data_loader, llm, scoring
from ..ledger import canonical, sha256
from ..rag.store import get_store, index_claim
from ..state import Mission
from ..tools.gateway import call_tool
from .summaries import offline_summary

SYSTEM = (
    "You are the {name} in a founder research team. Use ONLY the numbered passages. "
    "Do not invent facts or numbers. Do not call anything verified, estimated or hypothetical: "
    "the founder decides that. Reply in at most five plain sentences."
)


class OrchestrationError(Exception):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def idea_profile(idea: str) -> dict:
    t = idea.lower()
    sector = "Agriculture" if re.search(r"agri|farm|crop|harvest|produce|maize|dairy", t) else "Not detected"
    geo = "Kenya" if re.search(r"kenya|nairobi|nakuru|eldoret|kisumu|mombasa", t) else "Not detected"
    model = "Marketplace" if re.search(r"marketplace|platform|app", t) else "Not detected"
    return {"sector": sector, "geo": geo, "model": model, "matched": sector != "Not detected" and geo != "Not detected"}


def agent_status(m: Mission, agent_id: str) -> str:
    if agent_id in m.done:
        return "done"
    if m.approved:
        return "locked"
    needs = data_loader.agent_by_id()[agent_id]["needs"]
    return "ready" if all(n in m.done for n in needs) else "locked"


def refresh_scores(m: Mission, force: bool = False) -> None:
    if force or "growth" in m.done:
        sc = scoring.city_scores(m.found, m.labels, m.excluded)
        m.rec = {"city": scoring.top_city(sc), "scores": sc}


async def run_agent(m: Mission, agent_id: str) -> dict[str, Any]:
    agents = data_loader.agent_by_id()
    if agent_id not in agents:
        raise OrchestrationError(f"unknown agent '{agent_id}'", 404)
    if m.approved:
        raise OrchestrationError("mission is sealed", 409)
    if agent_id in m.done:
        raise OrchestrationError(f"{agent_id} already ran", 409)
    if agent_status(m, agent_id) != "ready":
        missing = [n for n in agents[agent_id]["needs"] if n not in m.done]
        raise OrchestrationError(f"{agent_id} is waiting for: {', '.join(missing)}", 409)

    agent, t0, trace = agents[agent_id], time.perf_counter(), []

    def log(kind: str, text: str) -> None:
        trace.append({"kind": kind, "text": text})

    log("sys", f'orchestrator: run graph node "{agent_id}"')
    by_id = data_loader.claim_by_id()
    own = [c for c in data_loader.claims() if c["agent"] == agent_id and not c["extra"]]
    claims_found: list[dict] = []
    extra = ""

    if own:
        query = f'{m.idea} {agent["focus"]}'
        args = {"query": query, "agent": agent_id, "k": len(own), "mission_id": m.id}
        log("out", f'mcp tools/call search_evidence(agent="{agent_id}", k={len(own)})')
        hits = await call_tool("search_evidence", args)
        ranked = {h["id"]: h["score"] for h in hits}
        log("out", f"qdrant.query_points collection=venture_evidence filter=agent:{agent_id}")
        if hits:
            log("in", f'best cosine {hits[0]["score"]:.3f} ({hits[0]["id"]}), lowest {hits[-1]["score"]:.3f}')
        # The corpus for this agent is always surfaced; ranking only orders it.
        claims_found = sorted(own, key=lambda c: -ranked.get(c["id"], 0.0))
        for c in claims_found:
            if c["id"] not in m.found:
                m.found.append(c["id"])
        if agent_id == "competitor":
            comps = await call_tool("competitors_search", {"region": "KE", "limit": 5})
            log("in", f"competitors_search -> {len(comps)} competitors")
        if agent_id == "customer":
            segs = await call_tool("segments_discover", {})
            log("in", f"segments_discover -> {len(segs)} segments")
        if agent_id == "leads":
            leads = await call_tool("leads_find", {"min_fit": 0})
            log("in", f"leads_find -> {len(leads)} candidate leads")
    else:
        log("out", f"critic audits {len(m.found)} findings already in the mission (no tool call needed)")

    if agent_id == "growth":
        refresh_scores(m, force=True)
        sc = m.rec["scores"]  # type: ignore[index]
        extra = f'Draft recommendation: launch in {m.rec["city"]} first. Scores use each source\'s own confidence until you label the claims.\n'  # type: ignore[index]
        sim = await call_tool("scenario_simulate", {"budget": 1500, "cost_per_customer": 22, "churn": 0.08})
        log("in", f'scenario_simulate -> steady state {sim["steady_state"]} customers (scenario, not a forecast)')
        m.ledger.record("research.snapshot", {"findings": len(m.found), "draft": m.rec["city"], "scores": sc})  # type: ignore[index]
        log("sys", f"hcs.submit topic={m.ledger.topic} seq={len(m.ledger.entries)} research.snapshot (simulated)")
    if agent_id == "critic":
        city = m.rec["city"] if m.rec else "n/a"  # type: ignore[index]
        extra = (
            f"Audit of the case for {city}: {round(scoring.hypothesis_share(m.found, city) * 100)}% of its positive "
            "evidence rests on hypotheses. Some possible weaknesses may not hold up.\n"
        )

    passages = "\n".join(f'[{i + 1}] {c["source"]}: {c["text"]}' for i, c in enumerate(claims_found))
    fallback = offline_summary(agent, idea_profile(m.idea), claims_found, extra)
    log("out", f"llm.generate model={llm.settings.llm_model} (falls back to offline template if Ollama is down)")
    summary, backend = await llm.generate(SYSTEM.format(name=agent["name"]), f"Idea: {m.idea}\n\nPassages:\n{passages}", fallback)
    log("in", f"summary produced by {backend}")

    m.done.add(agent_id)
    ms = (time.perf_counter() - t0) * 1000
    m.run_ms += ms
    m.manual_minutes += agent["manual_minutes"]
    if agent_id != "growth":
        refresh_scores(m)
    return {"agent": agent_id, "summary": summary, "llm_backend": backend, "trace": trace, "claim_ids": [c["id"] for c in claims_found], "duration_ms": round(ms)}


def label_claim(m: Mission, claim_id: str, label: str) -> dict:
    claim = data_loader.claim_by_id().get(claim_id)
    if claim is None or claim_id not in m.found:
        raise OrchestrationError("claim not found in this mission", 404)
    if m.approved:
        raise OrchestrationError("mission is sealed", 409)
    if claim_id in m.labels:
        raise OrchestrationError("claim already reviewed", 409)
    ok = label == claim["truth"]
    m.labels[claim_id] = label
    if ok:
        m.streak += 1
        pts = round(100 * (1 + min(m.streak - 1, 4) * 0.25))
    else:
        m.streak, pts = 0, -25
    m.score += pts
    m.verdicts[claim_id] = {"ok": ok, "pts": pts}
    refresh_scores(m)
    return {"correct": ok, "points": pts, "truth": claim["truth"], "why": claim["why"]}


def open_checkpoint(m: Mission) -> dict:
    if "critic" not in m.done:
        raise OrchestrationError("the critic has not finished yet", 409)
    if m.approved:
        raise OrchestrationError("mission is sealed", 409)
    refresh_scores(m)
    city = m.rec["city"]  # type: ignore[index]
    if not m.weak or m.weak_city != city:
        m.weak = scoring.weaknesses(m.found, city)
        m.weak_city = city
    by_id = data_loader.claim_by_id()
    support = [i for i in m.found if by_id[i]["city"] == city and by_id[i]["signal"] > 0]
    return {
        "recommendation": {"city": city, "scores": m.rec["scores"]},  # type: ignore[index]
        "supporting_claim_ids": support,
        "weaknesses": [w["text"] for w in m.weak],
        "unreviewed": len(m.found) - len(m.labels),
        "can_request_research": not m.researched,
    }


async def act_on_checkpoint(m: Mission, action: str, picked: list[int]) -> dict:
    if "critic" not in m.done:
        raise OrchestrationError("the critic has not finished yet", 409)
    if m.approved:
        raise OrchestrationError("mission is sealed", 409)
    if not m.weak:
        open_checkpoint(m)
    if any(i < 0 or i >= len(m.weak) for i in picked):
        raise OrchestrationError("weakness index out of range")
    weak_points = 0
    if not m.weak_scored:  # the weakness review is scored once
        m.weak_scored = True
        for i, w in enumerate(m.weak):
            weak_points += 50 if ((i in picked) == w["real"]) else -25
        m.score += weak_points

    if action == "challenge":
        dropped = [i for i in m.found if m.labels.get(i) == "hypothesis" and data_loader.claim_by_id()[i]["city"]]
        m.excluded.update(dropped)
        m.score += 40
        before = m.rec["city"]  # type: ignore[index]
        refresh_scores(m)
        m.ledger.record("decision.challenged", {"previous": before, "excluded": dropped, "weaknesses": picked})
        return {"action": action, "weakness_points": weak_points, "dropped": dropped, "previous_city": before, "city": m.rec["city"]}  # type: ignore[index]

    if action == "research":
        if m.researched:
            raise OrchestrationError("extra research was already requested", 409)
        m.researched = True
        m.score += 20
        extras = [c for c in data_loader.claims() if c["extra"]]
        for c in extras:
            index_claim(get_store(), c, m.id)
        added = [c["id"] for c in extras]
        m.found.extend(i for i in added if i not in m.found)
        await call_tool("segments_discover", {})
        m.ledger.record("decision.research_requested", {"added": added})
        refresh_scores(m)
        return {"action": action, "weakness_points": weak_points, "added": added}

    # approve
    truth = scoring.city_scores(m.found, m.labels, m.excluded, "truth")
    best, city = scoring.top_city(truth), m.rec["city"]  # type: ignore[index]
    right, unreviewed = city == best, len(m.found) - len(m.labels)
    m.score += 300 if right else -150
    if not unreviewed:
        m.score += 100
    m.approved, m.ended = True, time.time()
    acknowledged = [m.weak[i]["text"] for i in picked]
    m.ledger.record("decision.approved", {"city": city, "approvedBy": "founder", "weaknessesAcknowledged": acknowledged, "labels": m.labels, "unreviewed": unreviewed})
    report_hash = sha256(canonical({"idea": m.idea, "city": city, "scores": m.rec["scores"], "findings": m.found, "labels": m.labels}))  # type: ignore[index]
    m.ledger.record("report.sealed", {"reportHash": report_hash})
    m.report = {
        "matches_evidence": right,
        "approved_city": city,
        "best_supported_city": best,
        "approved_score": truth[city],
        "best_score": truth[best],
        "weakness_points": weak_points,
        "reviewed": len(m.labels),
        "total_claims": len(m.found),
        "full_review_bonus": unreviewed == 0,
        "manual_minutes_assumed": m.manual_minutes,
        "agent_seconds": round(m.run_ms / 1000, 2),
        "session_minutes": round((m.ended - m.created) / 60, 2),
        "report_hash": report_hash,
    }
    return {"action": action, "weakness_points": weak_points, "report": m.report}


def ingest_note(m: Mission, text: str) -> int:
    store = get_store()
    note_id = f"N{uuid.uuid4().hex[:6]}"
    store.upsert(note_id, text, {"agent": "founder", "collection": "founder-docs", "title": "Founder note", "text": text, "is_claim": False}, scope=m.id)
    return store.size(m.id)
