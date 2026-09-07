-- DE-04: ClickHouse interaction logs for the Analytics Dashboard
CREATE DATABASE IF NOT EXISTS icsa;

CREATE TABLE IF NOT EXISTS icsa.interaction_logs (
  id UUID DEFAULT generateUUIDv4(),
  session_id String,
  query_text String,
  matched_service_id String,
  matched_service_name String,
  office String,
  confidence Float32,
  response_time_ms UInt32,
  escalated UInt8,
  created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (created_at, office);
