# 4) API (Draft) — trimmed for MVP

- `POST /api/upload` — multipart; params: `chunk_method` (enum), `doc_title`.
- `GET /api/ingestions/{id}` — status + counts.
- `GET /api/search?q=...` — hybrid query; returns ranked results with `{doc, chunk_id, method, snippet, score, page/section}` + **synthesized answer**.
- `GET /api/search?q=...&include_answer=true` — optional answer generation parameter.

---
