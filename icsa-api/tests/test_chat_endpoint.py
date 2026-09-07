"""AI-08: /api/chat endpoint tests (2) — FastAPI TestClient, no running server."""


def test_valid_query_returns_200(client):
    resp = client.post("/api/chat", json={"query": "how to get medical certificate"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"]
    assert data["response_time_ms"] >= 0
    assert "escalated" in data and "confidence" in data


def test_empty_query_returns_400(client):
    resp = client.post("/api/chat", json={"query": "   "})
    assert resp.status_code == 400
    assert resp.json() == {"error": "Query cannot be empty", "code": 400}
