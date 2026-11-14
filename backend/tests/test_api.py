from app import data_loader
from tests.conftest import run_all


def test_health(client):
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["llm"] == "offline-template" and h["passages"] == 26


def test_validation_rejects_short_idea(client):
    assert client.post("/api/missions", json={"idea": "short"}).status_code == 422


def test_agents_respect_dependencies(client, mission):
    mid = mission["id"]
    r = client.post(f"/api/missions/{mid}/agents/growth/run")
    assert r.status_code == 409 and "waiting for" in r.json()["detail"]
    assert client.post(f"/api/missions/{mid}/agents/founder/run").status_code == 200
    assert client.post(f"/api/missions/{mid}/agents/founder/run").status_code == 409
    assert client.post(f"/api/missions/{mid}/agents/nope/run").status_code == 404


def test_claims_hide_truth_until_labelled(client, mission):
    mid = mission["id"]
    run_all(client, mid, "market")
    claims = client.get(f"/api/missions/{mid}").json()["claims"]
    assert claims and all(c["label"] is None and c["verdict"] is None for c in claims)
    assert "truth" not in str(claims) and "signal" not in str(claims)
    cid = next(c["id"] for c in claims if c["id"] == "M1")
    wrong = client.post(f"/api/missions/{mid}/claims/{cid}/label", json={"label": "hypothesis"}).json()
    assert wrong["correct"] is False and wrong["points"] == -25 and wrong["truth"] == "verified"
    assert client.post(f"/api/missions/{mid}/claims/{cid}/label", json={"label": "verified"}).status_code == 409
    assert client.post(f"/api/missions/{mid}/claims/ZZ/label", json={"label": "verified"}).status_code == 404


def test_combo_scoring(client, mission):
    mid = mission["id"]
    run_all(client, mid, "market")
    pts = [client.post(f"/api/missions/{mid}/claims/{c}/label", json={"label": t}).json()["points"]
           for c, t in [("M1", "verified"), ("M2", "verified"), ("M3", "verified")]]
    assert pts == [100, 125, 150]


def test_full_game_approve_flow(client, mission):
    mid = mission["id"]
    assert client.get(f"/api/missions/{mid}/checkpoint").status_code == 409
    run_all(client, mid)
    cp = client.get(f"/api/missions/{mid}/checkpoint").json()
    assert cp["recommendation"]["city"] == "Nairobi" and len(cp["weaknesses"]) == 5
    assert "real" not in str(cp)
    claims = client.get(f"/api/missions/{mid}").json()["claims"]
    for c in claims:  # label everything with the right status
        t = data_loader.claim_by_id()[c["id"]]["truth"]
        client.post(f"/api/missions/{mid}/claims/{c['id']}/label", json={"label": t})
    cp = client.get(f"/api/missions/{mid}/checkpoint").json()
    assert cp["recommendation"]["city"] == "Nakuru" and cp["unreviewed"] == 0
    done = client.post(f"/api/missions/{mid}/checkpoint", json={"action": "approve", "weaknesses": [0, 1]}).json()
    rep = done["report"]
    assert rep["matches_evidence"] and rep["approved_city"] == "Nakuru" and rep["full_review_bonus"]
    assert done["mission"]["phase"] == "sealed"
    assert client.post(f"/api/missions/{mid}/checkpoint", json={"action": "approve"}).status_code == 409
    led = client.get(f"/api/missions/{mid}/ledger").json()
    assert [e["type"] for e in led["entries"]] == ["session.created", "research.snapshot", "decision.approved", "report.sealed"]
    assert client.post(f"/api/missions/{mid}/ledger/verify").json()["ok"] is True
    assert client.post(f"/api/missions/{mid}/ledger/tamper").status_code == 200
    assert client.post(f"/api/missions/{mid}/ledger/verify").json()["ok"] is False
    client.post(f"/api/missions/{mid}/ledger/restore")
    assert client.post(f"/api/missions/{mid}/ledger/verify").json()["ok"] is True


def test_approving_on_face_value_is_penalised(client, mission):
    mid = mission["id"]
    run_all(client, mid)
    rep = client.post(f"/api/missions/{mid}/checkpoint", json={"action": "approve", "weaknesses": []}).json()["report"]
    assert rep["approved_city"] == "Nairobi" and rep["best_supported_city"] == "Nakuru" and not rep["matches_evidence"]


def test_challenge_and_research(client, mission):
    mid = mission["id"]
    run_all(client, mid)
    for c in ("U2", "G1", "G4"):
        client.post(f"/api/missions/{mid}/claims/{c}/label", json={"label": "hypothesis"})
    ch = client.post(f"/api/missions/{mid}/checkpoint", json={"action": "challenge", "weaknesses": [0]}).json()
    assert {"U2", "G1"} <= set(ch["dropped"])
    assert ch["city"] == "Nakuru"
    rs = client.post(f"/api/missions/{mid}/checkpoint", json={"action": "research"}).json()
    assert rs["added"] == ["X1", "X2", "X3"]
    own = client.post("/api/rag/search", json={"query": "ten Nairobi buyers decided on price first", "k": 1, "mission_id": mid}).json()
    assert own["hits"][0]["id"] == "X1"
    assert client.post(f"/api/missions/{mid}/checkpoint", json={"action": "research"}).status_code == 409
    assert client.post(f"/api/missions/{mid}/checkpoint", json={"action": "challenge", "weaknesses": [99]}).status_code == 400


def test_rag_search_and_ingest_scope(client, mission):
    other = client.post("/api/missions", json={"idea": "Another agricultural idea in Kenya"}).json()["id"]
    r = client.post("/api/rag/search", json={"query": "which city has the fewest competitors", "k": 5}).json()
    assert len(r["hits"]) == 5
    n = client.post("/api/rag/ingest", json={"mission_id": mission["id"], "text": "Kisumu co-op chairs pay suppliers late."}).json()["passages"]
    own = client.post("/api/rag/search", json={"query": "Kisumu co-op chairs pay suppliers late", "k": 1, "mission_id": mission["id"]}).json()
    foreign = client.post("/api/rag/search", json={"query": "Kisumu co-op chairs pay suppliers late", "k": 1, "mission_id": other}).json()
    assert own["hits"][0]["title"] == "Founder note" and foreign["hits"][0]["title"] != "Founder note" and n == 27


def test_scenario_endpoint(client):
    assert client.post("/api/scenario", json={"budget": 1000, "cost_per_customer": 20, "churn": 0.1}).json()["steady_state"] == 500
    assert client.post("/api/scenario", json={"budget": 1000, "cost_per_customer": 0, "churn": 0.1}).status_code == 422
