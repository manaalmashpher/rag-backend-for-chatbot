# 10) API Contracts (Examples)

## 10.1 `POST /api/upload`

**Request:** multipart `file`, `doc_title`, `chunk_method` ∈ **{1,2,3,4,5,6,7,8}**  
**Response:** `201 Created`

```json
{ "doc_id": "doc_01HFX…", "ingestion_id": "ing_01HFX…" }
```

## 10.2 `GET /api/ingestions/{id}`

**Response:** `200 OK`

```json
{
  "id": "ing_01HFX…",
  "doc_id": "doc_01HFX…",
  "status": "indexing",
  "counts": { "chunks": 128, "vectors": 128 },
  "blocked_reason": null,
  "errors": []
}
```

## 10.3 `GET /api/search?q=...`

**Response:** `200 OK`

```json
{
  "params": {
    "topk_vec": 20,
    "topk_lex": 20,
    "w_sem": 0.6,
    "w_lex": 0.4,
    "include_answer": true
  },
  "latency_ms": 1200,
  "results": [
    {
      "doc_id": "doc_01HFX…",
      "chunk_id": "ch_00045",
      "method": 4,
      "page_from": 2,
      "page_to": 3,
      "snippet": "…",
      "score": 0.82
    }
  ],
  "answer": {
    "text": "Based on the retrieved documents, the answer to your query is...",
    "sources": ["doc_01HFX…"],
    "confidence": 0.85,
    "generated_at": "2025-09-29T00:00:00Z"
  }
}
```

---
