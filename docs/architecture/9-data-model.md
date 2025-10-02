# 9) Data Model

## 9.1 Relational Schema (Postgres)

```sql
CREATE TABLE documents (
  id           TEXT PRIMARY KEY,
  title        TEXT NOT NULL,
  mime         TEXT NOT NULL,
  bytes        INTEGER NOT NULL,
  sha256       TEXT NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE ingestions (
  id           TEXT PRIMARY KEY,
  doc_id       TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  method       INTEGER NOT NULL,
  status       TEXT NOT NULL, -- queued|extracting|chunking|embedding|indexing|done|failed|blocked_scanned_pdf
  error        JSONB,
  started_at   TIMESTAMPTZ,
  finished_at  TIMESTAMPTZ
);

CREATE TABLE chunks (
  id           TEXT PRIMARY KEY,
  doc_id       TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  method       INTEGER NOT NULL,
  page_from    INTEGER,
  page_to      INTEGER,
  hash         TEXT NOT NULL,
  text         TEXT NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE search_logs (
  id           TEXT PRIMARY KEY,
  query        TEXT NOT NULL,
  params_json  JSONB NOT NULL,
  latency_ms   INTEGER NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## 9.2 Lexical FTS Configuration

```sql
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
ALTER TABLE chunks
  ADD COLUMN tsv tsvector GENERATED ALWAYS AS (
    to_tsvector('english', unaccent(text))
  ) STORED;
CREATE INDEX IF NOT EXISTS idx_chunks_tsv ON chunks USING GIN(tsv);
```

## 9.3 Qdrant Collection & Payload

**Collection config (example):**

```json
{
  "vectors": { "size": 1536, "distance": "Cosine" },
  "optimizers_config": { "default_segment_number": 2 }
}
```

**Payload fields:** `doc_id, chunk_id, method, page_from, page_to, hash, source`.

---
