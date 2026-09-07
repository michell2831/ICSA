"""AI-14: Integration tests - enabled in Week 3 (real pgvector + real
ClickHouse populated, per AI-09/AI-10)."""
import pytest


@pytest.mark.integration
def test_full_chat_flow(client, clickhouse_host, clickhouse_password):
    from clickhouse_driver import Client as CH
    ch = CH(host=clickhouse_host, user="default", password=clickhouse_password)
    before = ch.execute("SELECT COUNT(*) FROM icsa.interaction_logs")[0][0]
    r = client.post("/api/chat", json={"query": "What is needed for Good Moral Certificate?"})
    assert r.status_code == 200
    assert len(r.json()["answer"]) > 10
    after = ch.execute("SELECT COUNT(*) FROM icsa.interaction_logs")[0][0]
    assert after == before + 1


@pytest.mark.integration
def test_similarity_search_live(pgvector_dsn):
    from services.vector_store import search_similar
    results = search_similar("Good Moral Certificate", top_k=1)
    assert len(results) > 0
    assert results[0]["similarity"] > 0.30


@pytest.mark.integration
def test_analytics_top_services_live(client):
    # ENH-01: analytics endpoints now require a PSS-issued token.
    import base64
    import json

    claims = {"userId": "u1", "username": "test", "armsRole": "SUPER_ADMIN", "office": "ALL", "isCrossOffice": True}
    token = "mock-token-" + base64.b64encode(json.dumps(claims).encode()).decode()

    r = client.get("/api/analytics/top-services?limit=5", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    assert "service_name" in data[0]


@pytest.mark.integration
def test_no_context_response_live(client):
    r = client.post("/api/chat", json={"query": "asdfghjkl qwerty 99999"})
    assert r.status_code == 200
    a = r.json()["answer"].lower()
    assert any(w in a for w in ["please visit", "do not have", "don't have", "assist", "pup caloocan", "services"])