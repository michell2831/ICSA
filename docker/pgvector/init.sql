-- DE-03: pgvector schema for ICSA service embeddings
-- Dimension 384 matches sentence-transformers all-MiniLM-L6-v2.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS service_embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  service_id VARCHAR(100) NOT NULL UNIQUE,  -- UNIQUE enables ON CONFLICT upsert for nightly re-index
  service_name VARCHAR(500),
  office VARCHAR(200),
  text_chunk TEXT NOT NULL,
  sla_target_value NUMERIC,
  sla_target_unit VARCHAR(50),
  embedding vector(384) NOT NULL,
  created_at TIMESTAMP DEFAULT now()
);

ALTER TABLE service_embeddings ADD COLUMN IF NOT EXISTS sla_target_value NUMERIC;
ALTER TABLE service_embeddings ADD COLUMN IF NOT EXISTS sla_target_unit VARCHAR(50);

CREATE INDEX IF NOT EXISTS idx_se
  ON service_embeddings USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);