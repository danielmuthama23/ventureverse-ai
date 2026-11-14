"""VentureVerse API."""
from __future__ import annotations

import hashlib
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import data_loader, llm, scoring
from .agents import orchestrator as orch
from .config import settings
from .rag.store import get_store
from .schemas import CheckpointAction, LabelRequest, MissionCreate, RagIngest, RagSearch, ScenarioRequest
from .state import Mission, missions
from .tools.gateway import ToolError, call_tool


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_store()  # build the Qdrant collection once at startup
    yield


app = FastAPI(title="VentureVerse API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["*"], allow_headers=["*"])


def _mission(mission_id: str) -> Mission:
    m = missions.get(mission_id)
    if m is None:
        raise HTTPException(404, "mission not found")
    return m


def _claim_view(m: Mission, cid: str) -> dict:
    c = data_loader.claim_by_id()[cid]
    view = {
        "id": cid, "agent": c["agent"], "city": c["city"], "claim": c["claim"], "text": c["text"],
        "source": c["source"], "method": c["method"], "collection": c["collection"], "url": c["url"],
        "source_confidence": c["source_confidence"], "label": m.labels.get(cid), "verdict": None,
    }
    if cid in m.labels:  # the truth is revealed only after the founder commits to a label
        v = m.verdicts[cid]
        view["verdict"] = {"correct": v["ok"], "points": v["pts"], "truth": c["truth"], "why": c["why"]}
    return view


def _view(m: Mission) -> dict:
    ag = data_loader.agents()
    return {
        "id": m.id, "idea": m.idea, "topic": m.ledger.topic,
        "phase": "sealed" if m.approved else "checkpoint" if "critic" in m.done else "research",
        "agents": [{**a, "status": orch.agent_status(m, a["id"])} for a in ag],
        "claims": [_claim_view(m, i) for i in m.found],
        "score": m.score, "combo": m.combo, "reviewed": len(m.labels),
        "recommendation": m.rec, "approved": m.approved, "ledger_length": len(m.ledger.entries),
        "report": m.report, "agent_seconds": round(m.run_ms / 1000, 2), "manual_minutes_assumed": m.manual_minutes,
        "created": m.created,
    }


def _guard(fn):
    try:
        return fn()
    except orch.OrchestrationError as e:
        raise HTTPException(e.status, str(e)) from e


@app.get("/api/health")
async def health():
    return {"status": "ok", "llm": await llm.backend_name(), "embedder": settings.embed_mode,
            "vector_store": "qdrant:" + settings.qdrant_url, "passages": get_store().size(), "demo_mode": settings.demo_mode}


@app.get("/api/world")
async def world():
    """Static scene data: agents, cities, competitors, customer segments."""
    v = data_loader.venture()
    return {"agents": data_loader.agents(), "cities": v["cities"], "competitors": v["competitors"],
            "competitor_edges": v["competitor_edges"], "segments": v["segments"], "leads": v["leads"]}


@app.post("/api/missions", status_code=201)
async def create_mission(body: MissionCreate):
    m = missions.create(body.idea.strip())
    m.ledger.record("session.created", {"ideaHash": hashlib.sha256(m.idea.encode()).hexdigest(), "agents": len(data_loader.agents()), "model": await llm.backend_name()})
    return _view(m)


@app.get("/api/missions/{mission_id}")
async def get_mission(mission_id: str):
    return _view(_mission(mission_id))


@app.post("/api/missions/{mission_id}/agents/{agent_id}/run")
async def run_agent(mission_id: str, agent_id: str):
    m = _mission(mission_id)
    try:
        result = await orch.run_agent(m, agent_id)
    except orch.OrchestrationError as e:
        raise HTTPException(e.status, str(e)) from e
    except ToolError as e:
        raise HTTPException(502, str(e)) from e
    except RuntimeError as e:
        raise HTTPException(503, str(e)) from e
    return {**result, "mission": _view(m)}


@app.post("/api/missions/{mission_id}/claims/{claim_id}/label")
async def label(mission_id: str, claim_id: str, body: LabelRequest):
    m = _mission(mission_id)
    result = _guard(lambda: orch.label_claim(m, claim_id, body.label))
    return {**result, "mission": _view(m)}


@app.get("/api/missions/{mission_id}/checkpoint")
async def checkpoint(mission_id: str):
    return _guard(lambda: orch.open_checkpoint(_mission(mission_id)))


@app.post("/api/missions/{mission_id}/checkpoint")
async def act(mission_id: str, body: CheckpointAction):
    m = _mission(mission_id)
    try:
        result = await orch.act_on_checkpoint(m, body.action, body.weaknesses)
    except orch.OrchestrationError as e:
        raise HTTPException(e.status, str(e)) from e
    return {**result, "mission": _view(m)}


@app.get("/api/missions/{mission_id}/ledger")
async def ledger(mission_id: str):
    m = _mission(mission_id)
    return {"topic": m.ledger.topic, "simulated": True, "entries": [
        {"seq": e.seq, "ts": e.ts, "type": e.type, "payload_hash": e.payload_hash, "prev": e.prev, "entry_hash": e.entry_hash, "tx": e.tx}
        for e in m.ledger.entries]}


@app.post("/api/missions/{mission_id}/ledger/verify")
async def verify(mission_id: str):
    res = _mission(mission_id).ledger.verify()
    return {"ok": all(r["payload_ok"] and r["link_ok"] for r in res), "entries": res}


@app.post("/api/missions/{mission_id}/ledger/tamper")
async def tamper(mission_id: str):
    if not settings.demo_mode:
        raise HTTPException(403, "demo endpoints are disabled")
    if not _mission(mission_id).ledger.tamper():
        raise HTTPException(409, "ledger is empty")
    return {"tampered": True}


@app.post("/api/missions/{mission_id}/ledger/restore")
async def restore(mission_id: str):
    if not settings.demo_mode:
        raise HTTPException(403, "demo endpoints are disabled")
    return {"restored": _mission(mission_id).ledger.restore()}


@app.post("/api/rag/search")
async def rag_search(body: RagSearch):
    hits = await call_tool("search_evidence", {"query": body.query, "k": body.k, "mission_id": body.mission_id})
    return {"query": body.query, "passages": get_store().size(body.mission_id), "hits": hits}


@app.post("/api/rag/ingest")
async def rag_ingest(body: RagIngest):
    m = _mission(body.mission_id)
    return {"passages": orch.ingest_note(m, body.text)}


@app.post("/api/scenario")
async def scenario(body: ScenarioRequest):
    try:
        return await call_tool("scenario_simulate", body.model_dump())
    except ToolError as e:
        raise HTTPException(422, str(e)) from e


# Serve the built frontend when present (single-process deployment).
_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _dist.exists():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        f = _dist / path
        return FileResponse(f if path and f.is_file() else _dist / "index.html")
