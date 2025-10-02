# 7) Error Model (JSON)

All error responses follow a single envelope so the frontend can handle uniformly.

```json
{
  "error": {
    "code": "INGEST_FAILED",
    "message": "Embedding provider timed out",
    "details": { "doc_id": "abc123" },
    "requestId": "req_01HF…"
  }
}
```

HTTP status codes: 400, 401/403, 404, 409, 429, 500/502/504.

---
