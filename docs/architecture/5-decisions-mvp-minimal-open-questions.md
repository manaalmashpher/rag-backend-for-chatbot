# 5) Decisions (MVP) & Minimal Open Questions

**Pinned for MVP:**

- **Lexical index:** Postgres FTS in the primary DB.
- **Vector DB:** Qdrant, single collection (single‑tenant deployment).
- **Fusion:** semantic K=20, lexical K=20, fused return=10, weights 0.6/0.4.
- **Upload policy:** PDF/DOCX/TXT/MD, max 20 MB. Scanned PDFs blocked/flagged; no OCR.

**Minimal Open Questions:**

1. **Embedding model default** — propose `e3‑small`‑class, 1536‑dim; override via env if needed.
2. **Auth handoff** — confirm whether backend should require a signed session/JWT in MVP or accept a dev header token only.
3. **Chunk metadata** — any extra fields needed beyond `{doc_id, chunk_id, method, hash, source, page/section}` for your UI? (e.g., section titles).

---
