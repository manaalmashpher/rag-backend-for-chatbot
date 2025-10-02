# Constraints & Assumptions

- **A1. Corpus size**: ~200–300 pages total for MVP.
- **A2. Language**: English-only UI/content.
- **A3. File types**: PDF/DOCX/TXT/MD; **no OCR**.
- **A4. Chunking methods**: Fixed list (no runtime tuning); defaults documented.
- **A5. Fusion**: Default weights (e.g., semantic 0.6 / lexical 0.4) and Top‑K defined via config.
- **A6. Embeddings**: Provider/model set via environment; at least one viable model available.
- **A7. LLM Integration**: Provider/model configurable via environment; fallback to raw results on failure.
- **A8. Deployment**: SaaS, single-tenant; light concurrency.
- **A9. Observability**: Logs and optional CSV exports; no dashboards.
- **A10. Data residency**: Not required for MVP.
- **A11. Scanned PDFs are blocked/flagged (no OCR in MVP).**

---
