# VentureVerse AI

![VentureVerse AI](./1.png)

VentureVerse is a founder-facing market validation game: a founder enters a business idea, the app runs research agents, scores the opportunity, and surfaces a checkpoint where the founder decides whether to proceed, challenge, or ask for more evidence.

The project is a full-stack monorepo for collaborative, founder-led venture validation, combining:

- A Python/FastAPI backend for missions, scoring, routing, and the game loop
- A React + Vite frontend for the interactive dashboard and command-center UI
- Qdrant-backed evidence retrieval and MCP tool integrations
- Local Kenyan market maps and a simulated hash-chained ledger
- **BAND agent-to-agent collaboration** for structured messages, delegation, shared context, and workflow visibility

## Key features

| Feature | What VentureVerse provides |
| --- | --- |
| **AI-powered venture research** | Runs market, competitor, customer, lead, growth, and critical-review agents. |
| **BAND agent collaboration** | Connects VentureVerse agents through a provider-independent collaboration layer with mock mode and verified BAND live-provider support. |
| **Interactive command center** | Uses React, Vite, a 3D stage, evidence panels, maps, mission controls, and a live Collaboration Center. |
| **Human governance** | Keeps consequential decisions behind APPROVE, CHALLENGE, and RESEARCH MORE checkpoints. |
| **Evidence and retrieval** | Uses Qdrant-backed semantic search and MCP tools for bounded, auditable research. |
| **Trust and audit trail** | Records mission decisions in a simulated hash-chained ledger and collaboration event history. |

## Contents

- [Current stack](#current-stack)
- [Project layout](#project-layout)
- [Quick start](#quick-start)
- [Current app behavior](#current-app-behavior)
- [Map and region view](#map-and-region-view)
- [BAND Agent-to-Agent Collaboration](#band-agent-to-agent-collaboration)
- [Backend API summary](#backend-api-summary)
- [Testing](#testing)
- [Optional local model setup](#optional-local-model-setup)
- [Notes](#notes)

## Current stack

- Backend: Python 3.11, FastAPI, Qdrant-backed retrieval, MCP client/server integration
- Frontend: React 18, TypeScript, Vite, React Three Fiber, Leaflet + React Leaflet
- Storage: in-memory mission state plus Qdrant for evidence passages
- AI: local Ollama when available; otherwise a deterministic offline-template fallback
- Demo mode: sample market data, simulated Hedera-style ledger anchoring, and offline-safe behavior

## Project layout

```text
venture-verse/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── orchestrator.py
│   │   │   └── summaries.py
│   │   ├── data/
│   │   │   ├── agents.json
│   │   │   ├── claims.json
│   │   │   └── venture.json
│   │   ├── rag/
│   │   │   ├── embedder.py
│   │   │   └── store.py
│   │   ├── tools/
│   │   │   ├── gateway.py
│   │   │   └── registry.py
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── data_loader.py
│   │   ├── ledger.py
│   │   ├── llm.py
│   │   ├── main.py
│   │   ├── schemas.py
│   │   ├── scoring.py
│   │   └── state.py
│   ├── mcp_server/
│   │   └── server.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_api.py
│   │   ├── test_ledger.py
│   │   ├── test_llm.py
│   │   ├── test_mcp.py
│   │   └── test_scoring.py
│   ├── .venv/
│   ├── pytest.ini
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── CheckpointModal.tsx
│   │   │   ├── Chips.tsx
│   │   │   ├── EvidencePanel.tsx
│   │   │   ├── LedgerPanel.tsx
│   │   │   ├── LocationMap.tsx
│   │   │   ├── MissionPanel.tsx
│   │   │   ├── RagPanel.tsx
│   │   │   ├── Scene.tsx
│   │   │   └── Simulator.tsx
│   │   ├── lib/
│   │   │   ├── api.ts
│   │   │   ├── types.ts
│   │   │   └── useMission.ts
│   │   ├── main.tsx
│   │   ├── styles.css
│   │   └── vite-env.d.ts
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── e2e/
│   ├── smoke.mjs
│   └── package.json
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── README.md
└── .gitignore
```

## Quick start

Requirements: Python 3.11+ and Node 20+.

### Option 1: install and run the project from the repo root

```bash
cd /path/to/venture-verse
make install
make serve
```

This installs backend Python dependencies, installs frontend npm dependencies, builds the React app, and serves the app on:
- http://127.0.0.1:8000

### Option 2: run backend and frontend separately

```bash
cd backend
python3.11 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs at http://localhost:5173 and the backend remains on http://localhost:8000.

## Useful Make targets

```bash
make install
make dev-api
make dev-web
make build
make serve
make test
make e2e
```

Current meanings:
- `make install`: installs Python + Node dependencies
- `make dev-api`: runs the backend in reload mode on port 8000
- `make dev-web`: runs the frontend Vite dev server on port 5173
- `make build`: builds the production frontend bundle
- `make serve`: builds the frontend and serves the app via FastAPI on port 8000
- `make test`: runs backend pytest
- `make e2e`: installs Playwright dependencies and runs the smoke test against the app

## Current app behavior

The app is a mission-driven research simulator based on a founder brief.

A founder can:
- enter a business idea
- trigger a mission
- run seven agents in sequence
- inspect evidence and claims
- apply labels to claims
- review a recommendation checkpoint
- verify the ledger history

The dashboard currently includes:

- A command-center / 3D stage
- A mission panel with a founder brief and agent queue
- Evidence and ledger tabs
- A **BAND Collaboration Center** for agent status, messages, task progress, events, and analytics
- A location map that centers Nairobi while showing the broader Kenyan market footprint, including the other relevant cities and towns in the same visual

## Map and region view

The current map behavior intentionally emphasizes Nairobi as the anchor city, while showing the surrounding market cities in the same map frame. This makes the launch city feel central without losing the wider regional context.

The city ring overlays and labels are driven by the mission data and the current venture dataset in:
- `backend/app/data/venture.json`
- `frontend/src/components/LocationMap.tsx`

## BAND Agent-to-Agent Collaboration

VentureVerse can run as a mock collaboration system with no external credentials, or use the verified BAND Agent API with one registered Band agent identity.

### Official capabilities verified

- Band agents authenticate with an agent API key (`band_a_...`) sent in `X-API-Key`.
- Agent API: `/api/v1/agent/me`, `/api/v1/agent/chats`, `/api/v1/agent/chats/{chat_id}/messages`, `/api/v1/agent/chats/{chat_id}/events`, `/api/v1/agent/chats/{chat_id}/context`, and room task endpoints.
- BAND routes text messages by room mentions; events record thoughts, tool calls, task activity and human attention.
- Agent context and task status are rehydrated from Band REST endpoints.
- Band Cloud REST defaults are `https://app.band.ai` and `wss://app.band.ai/api/v1/socket/websocket`.

This provider boundary uses verified REST operations. SDK/WebSocket-specific room streaming is not presented as live until credentials are configured and a dedicated live test passes.

### Architecture

```mermaid
flowchart LR
  U[Founder] --> O[Existing Orchestrator]
  O --> M[Market]
  O --> C[Competitor]
  O --> CU[Customer]
  CU --> L[Leads]
  M & C & L --> G[Growth]
  G --> R[Critic]
  R --> H[Human APPROVE/CHALLENGE/RESEARCH]
  H --> Report[Sealed Venture Report]

  O <--> CM[Collaboration Store]
  CM <--> PA[Provider Adapter]
  PA <--> MOCK[Mock Provider]
  PA <--> BAND[Verified BAND REST Agent API]
  CM <--> Q[Qdrant + MCP Tools]
```

### Mock mode

Mock mode is the default:

```bash
BAND_ENABLED=false
```

Start the app normally. Open the **Collaboration Center** tab and choose **Run collaborative workflow**. Messages, tasks, events and analytics are clearly local simulated activity.

### Enable real BAND

1. Create or sign in to `https://app.band.ai`.
2. Open **Agents** and select **Connect remote agent**.
3. Register a remote agent and copy its ID and one-time agent API key (format `band_a_...`).
4. Set:

```bash
BAND_ENABLED=true
BAND_AGENT_ID=<registered-agent-uuid>
BAND_API_KEY=<agent-api-key>
BAND_REST_URL=https://app.band.ai
BAND_WS_URL=wss://app.band.ai/api/v1/socket/websocket
```

5. Restart FastAPI. `GET /api/band/status` validates configuration and calls `GET /api/v1/agent/me`.
6. Never commit `.env`, `agent_config.yaml`, API keys or credentials.

### Collaboration API

- `GET /api/band/status`
- `POST /api/band/connect`
- `GET /api/agents/registry`
- `GET /api/agents/messages`
- `POST /api/agents/messages`
- `POST /api/agents/delegate`
- `GET /api/agents/tasks/{task_id}`
- `POST /api/workflows/collaborative-venture/{mission_id}`
- `GET /api/workflows/{workflow_id}`
- `GET /api/workflows/{workflow_id}/events`
- `WS /ws/collaboration`

### Agricultural marketplace demonstration

Create a mission with: `AI-powered agricultural marketplace in Kenya`. Open **Collaboration Center**, run the collaborative workflow, then review the existing evidence and use the checkpoint to APPROVE, CHALLENGE or request further RESEARCH. Synthetic evidence is clearly identified by the existing demo/sample data model.

### BAND tests

```bash
cd backend
python -m pytest -q tests/test_collaboration.py
```

Mock tests do not require BAND credentials. Live integration tests require a dedicated test agent and credentials.

## Backend API summary

The current app exposes these routes through FastAPI:

- `GET /api/health` — returns backend health, active LLM, embedder mode, vector store state, and passage count
- `GET /api/world` — returns the world model: agents, cities, competitors, segments, and leads
- `POST /api/missions` — creates a mission from a founder idea
- `POST /api/missions/{id}/agents/{agent}/run` — runs an agent for a mission
- `GET /api/missions/{id}/checkpoint` — opens a checkpoint view
- `POST /api/missions/{id}/checkpoint` — approves, challenges, or requests more research
- `GET /api/missions/{id}/ledger` — reads the mission ledger
- `POST /api/missions/{id}/ledger/verify` — verifies the hash chain
- `POST /api/rag/search` — searches the evidence store
- `POST /api/rag/ingest` — ingests founder notes into the mission store
- `POST /api/scenario` — runs the scenario simulation tool

The interactive OpenAPI docs are available at:
- http://localhost:8000/docs

## Testing

```bash
cd backend
python -m pytest -q
```

This project currently includes backend tests covering the API, ledger, scoring logic, LLM client behavior, and MCP interactions.

## Optional local model setup

If Ollama is installed locally, the app will use it automatically when available.

```bash
ollama serve
ollama pull gpt-oss:20b
```

When Ollama is reachable, `/api/health` reflects the active model. When it is not, the app falls back to a deterministic offline template so the demo still runs.

## Notes

- The current venture data is sample/demo data for the app’s gameplay and research flow.
- The ledger is a simulated hash-chained flow intended for challenge/demo use rather than production blockchain anchoring.
- The app is designed for human decision-making: the founder stays in control of approvals and checkpoint decisions.
