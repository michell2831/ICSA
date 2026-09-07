# ICSA — Source of Truth

Single reference for architecture decisions. Kapag may conflict sa ibang docs, ito ang masusunod.

## The Golden Rule (No-Touch)
PSS (Capstone 1) is a sealed, trusted data source. ICSA:
- connects via a **read-only PostgreSQL role** (`readonly_icsa`, SELECT-only)
- makes **zero writes** to PSS (no INSERT/UPDATE/DELETE, no DDL, no schema changes)
- adds **zero commits** to the PSS repo — ICSA is a physically separate repository
- data flows **one-way**: PSS DB → ETL/reindex → pgvector

## Data source policy
- **Production data source: the real PSS database.** Lahat ng sagot ng chatbot ay galing sa
  PSS services na na-embed sa pgvector via the reindex pipeline.
- The 15-record fixture (`icsa-api/tests/fixtures/services_fixture.json`) is **unit-test
  data only** — never the runtime data source. It is built from real Citizen's Charter
  batch records so tests stay realistic.
- Two ways to pull PSS data in:
  1. **API**: `POST /api/admin/reindex` (on-demand, background) → poll `/api/admin/reindex/status`
  2. **Scripts/cron**: `extract_services.py` + `run_embedding.py` (nightly 2 AM, DE-07)

## Architecture (sidecar microservice)
| Component | Tech | Port | Role |
|---|---|---|---|
| PSS (legacy) | NestJS + PostgreSQL | 3000/4000/5432 | untouched source of truth |
| icsa-api | FastAPI (Python 3.11) | 8000 | RAG orchestration microservice |
| pgvector | Postgres 15 + pgvector | 5433 | 384-dim service embeddings (semantic search) |
| ClickHouse | clickhouse-server | 8123/9000 | append-only interaction logs (analytics) |
| icsa-frontend | React 18 + Vite + TS | 5173 | Chatbot UI + Analytics Dashboard |

## Pipeline (synchronous, per citizen query)
query → validate → embed locally (all-MiniLM-L6-v2, 384-dim) → pgvector cosine top-3
→ threshold 0.30 (below = fixed no-context message, never hallucinate)
→ Groq (Llama 3.1, temp 0.1, answer ONLY from context) → hallucination keyword guard
→ escalation if confidence < 0.50 or answer says "please visit"
→ async fire-and-forget ClickHouse log → ChatResponse (< 6s target)

## Terminology
Groq = inference API provider · Llama = LLM family hosted on Groq ·
Ollama = optional local fallback only · Claude Pro = AI Specialist's coding tool (not part of the system) ·
Grok = unrelated product

## Non-negotiables
1. No real credentials in Git (`.env` only; `.env.example` placeholders).
2. Model names / tokens / timeouts read from `.env` — never hardcoded.
3. Mock classes are never deleted — unit tests depend on them.
4. Below-threshold retrieval → fixed message. The chatbot never invents requirements, steps, or SLA values.
