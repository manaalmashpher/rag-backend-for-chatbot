# MVP Scope

## Core Features (Must Have)

- End-to-end pipeline: **Upload → Preprocess → Embed → Ingest (Qdrant)**.
- **Chunking method selection** from fixed list at upload time.
- **Hybrid search** (semantic + lexical) with fused ranking and source attributions.
- **LLM integration** for answer synthesis from retrieved chunks.
- **Email/password auth** and **single-tenant** deployment.
- **Status visibility** for ingestion and simple **logs/CSV** export.

## Out of Scope (MVP)

- Arabic/RTL UI and broader i18n
- RBAC and SSO
- Multi-tenant features
- Advanced security hardening and compliance tooling
- Automated PII scrubbing/redaction
- Analytics dashboards beyond logs/CSV
- OCR for scanned PDFs

## MVP Success Criteria

- **Quality**: Hit@5 ≥ 0.70; Hit@10 ≥ 0.85; Median human relevance ≥ 3/5 on seed set; **Answer relevance ≥ 4/5**.
- **Performance**: p95 ≤ 1.5s; p99 ≤ 3.0s; **Answer generation p95 ≤ 3s**.
- **Ingestion**: 200–300 pages ≤ 20 min.

---
