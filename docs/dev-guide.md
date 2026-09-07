# ICSA Developer Guide

## Switching between mock and production mode (AI-10)

All routing is flag-based via `.env` — the mock classes are never deleted
(unit tests depend on them).

| Flag | Week 1 (dev) | Week 2+ (live) | Controls |
|---|---|---|---|
| `USE_MOCK_LLM` | `true` | `false` | `mock_llm_service` vs Groq/Llama (`llm_service`) |
| `USE_MOCK_VECTOR_STORE` | `true` | `false` | hard-coded 3 services vs real pgvector search |
| `USE_MOCK_LOGGING` | `true` | `false` | no-op vs async ClickHouse insert |
| `USE_MOCK_ANALYTICS` | `true` | `false` | canned dashboard data vs real ClickHouse queries |
| `VITE_USE_MOCK_API` (frontend `.env`) | `true` | `false` | FE mock responses vs real axios calls to `:8000` |

**Go-live sequence (Week 2, AI-10):**
1. Copy environment variables (`cp .env.example .env`) and configure them, then run `docker-compose up -d` → 3 healthy containers.
2. Option A (isang API call lang): `curl -X POST localhost:8000/api/admin/reindex` → poll `localhost:8000/api/admin/reindex/status` hanggang `done`.
   Option B (scripts, from `icsa-api/`): `python scripts/etl/extract_services.py` then `python scripts/run_embedding.py`.
3. Verify: `SELECT COUNT(*) FROM service_embeddings;` ≥ 70.
4. Flip all four backend flags to `false` in `.env`, restart uvicorn.
5. Flip `VITE_USE_MOCK_API=false` in `icsa-frontend/.env`, restart `npm run dev`.
6. Verify: `curl -X POST localhost:8000/api/chat -H "Content-Type: application/json" -d '{"query":"What documents for Transcript of Records?"}'` — answer must reference real PSS data, not `[MOCK ANSWER]`.
7. Unit tests must STILL pass: `pytest tests/ -v -k "not integration"`.
8. Run integration tests: `pytest tests/test_integration.py -v -m integration`.

## Validation scripts (Week 2–3)
```bash
cd icsa-api && python scripts/groq_load_test.py      # AI-11: 5 sequential live queries, all must be 200
python scripts/evaluate_accuracy.py   # AI-15: >= 7/10, auto-writes docs/accuracy-report.md
python scripts/latency_test.py        # AI-17: all < 6s, auto-writes docs/performance-report.md
```

## Error / fallback scenarios (AI-18)
1. Gibberish query → fixed no-context message (never hallucinate).
2. `GROQ_TIMEOUT_SECONDS=1` → fixed timeout message, not HTTP 500.
3. `USE_MOCK_LLM=true` → canned response, zero Groq calls.
4. `docker stop icsa-clickhouse` → `/api/chat` still returns HTTP 200 (logging is fire-and-forget).
5. Empty query → HTTP 400 `{"error":"Query cannot be empty","code":400}`.

## No-Touch rule (Golden Rule)
PSS is read via a SELECT-only role. Data flows one-way: PSS DB → ETL → pgvector.
Zero commits to the PSS repo. Zero INSERT/UPDATE/DELETE against PSS, ever.
