"""Shared pytest fixtures. Run from icsa-api/:  pytest tests/ -v"""
import os
import sys

import pytest

API_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # icsa-api/
sys.path.insert(0, API_DIR)

# Unit tests always run against mocks — no real DB or Groq needed (AI-08).
os.environ.setdefault("USE_MOCK_LLM", "true")
os.environ.setdefault("USE_MOCK_VECTOR_STORE", "true")
os.environ.setdefault("USE_MOCK_LOGGING", "true")
os.environ.setdefault("USE_MOCK_ANALYTICS", "true")


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    from main import app
    return TestClient(app)


@pytest.fixture(scope="session")
def pgvector_dsn():
    return os.getenv("PGVECTOR_URL", "postgresql://postgres:postgres@localhost:5433/postgres")


@pytest.fixture(scope="session")
def clickhouse_host():
    return os.getenv("CLICKHOUSE_HOST", "localhost")


@pytest.fixture(scope="session")
def clickhouse_password():
    return os.getenv("CLICKHOUSE_PASSWORD", "")


@pytest.fixture(scope="session")
def fixture_services():
    import json
    path = os.path.join(API_DIR, "tests", "fixtures", "services_fixture.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)