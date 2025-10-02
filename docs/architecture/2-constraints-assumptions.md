# 2) Constraints & Assumptions

- **File types:** PDF, DOCX, TXT, MD. **Max 20 MB**. **No OCR** (scanned PDFs blocked/flagged).
- **Language:** English‑only for MVP.
- **Chunking methods (fixed, selectable at upload):** **1, 2, 3, 4, 5, 6, 7, 8.**
- **Embedding provider/model:** **TBD via env**; dimensions & tokenizer standardized and pinned.
- **LLM provider/model:** **Groq** (primary), configurable via env (OpenAI, Anthropic, local models); API keys and parameters configurable.
- **Retrieval defaults:** semantic top‑k=20; lexical top‑k=20; fused return=10; **weights 0.6/0.4** (semantic/lexical).
- **Answer synthesis:** **p95 ≤ 3s** latency; quality validation with fallback to raw results.
- **Persistence:** **Qdrant** for vectors; **Relational DB** (proposed: Postgres) for metadata & lexical FTS; object storage for originals.
- **Auth:** Email/password via web app; backend validates session/JWT; HTTPS required.
- **Deployment:** SaaS, **single‑tenant** per deployment; light concurrency (single‑digit users).
- **Observability:** Structured logs only (console + file). No metrics, no dashboards.

---
