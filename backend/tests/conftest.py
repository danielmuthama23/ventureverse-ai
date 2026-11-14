import os

# Tests never need Ollama: force the offline template and in-process Qdrant.
os.environ["LLM_MODE"] = "offline"
os.environ["QDRANT_URL"] = ":memory:"
os.environ["EMBED_MODE"] = "hashing"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def mission(client):
    r = client.post("/api/missions", json={"idea": "An AI-powered agricultural marketplace for farmers in Kenya"})
    assert r.status_code == 201
    return r.json()


def run_all(client, mid, upto="critic"):
    order = ["founder", "market", "competitor", "customer", "leads", "growth", "critic"]
    for a in order[: order.index(upto) + 1]:
        r = client.post(f"/api/missions/{mid}/agents/{a}/run")
        assert r.status_code == 200, r.text
