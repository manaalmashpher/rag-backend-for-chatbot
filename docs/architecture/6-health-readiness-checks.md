# 6) Health & Readiness Checks

Define two lightweight endpoints:

- `GET /healthz` — **Liveness**: returns `200` if the process is up and can accept connections.
- `GET /readyz` — **Readiness**: verifies dependencies and returns component statuses: Qdrant (collection ping), Postgres (`SELECT 1`), Embedding provider (no‑op or cached warmup), **LLM service** (health check or no‑op).

**Response shape (example):**

```json
{
  "status": "ready",
  "components": {
    "qdrant": "ok",
    "postgres": "ok",
    "embeddings": "ok",
    "llm": "ok"
  },
  "checked_at": "2025-09-29T00:00:00Z"
}
```

---
