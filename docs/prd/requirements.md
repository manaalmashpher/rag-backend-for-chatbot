# Requirements

## Functional Requirements (FR)

- **FR1. Upload**: Users can upload a document for ingestion.
- **FR2. File types**: Accept **PDF, DOCX, TXT, MD**. **Scanned PDFs (no OCR) are flagged/blocked** with a clear message.
- **FR3. Method selection**: At upload time, users must select one **chunking method** from the fixed list (no in‑app parameter tuning in MVP).
- **FR4. Preprocessing**: System normalizes text (whitespace, encoding) and extracts structure where possible (headings, paragraphs, tables/pages where applicable).
- **FR5. Embeddings**: Generate embeddings using a configurable provider/model (set via environment/config).
- **FR6. Ingestion**: Persist chunks + vectors to **Qdrant** with stable identifiers.
- **FR7. Lexical index**: Build/maintain a **minimal lexical index** (e.g., BM25/FTS) per corpus to enable hybrid search.
- **FR8. Hybrid query**: Provide a **search UI** that executes hybrid retrieval (semantic + lexical) and returns fused, ranked results with source attributions and chunk/method metadata.
- **FR9. LLM Integration**: Integrate configurable LLM service to synthesize retrieved chunks into coherent, contextual answers.
- **FR10. Answer Generation**: Generate natural language responses that directly address user queries using retrieved document chunks as context.
- **FR11. Auth**: **Email + password** authentication; single-tenant org scope.
- **FR12. Status & observability**: Show **ingestion status** (per document + per method) and log basic pipeline events; allow **CSV export** of evaluation metrics/logs.
- **FR13. (Removed — out of scope for MVP) Evaluation harness (seed set)**.
- **FR14. English-only UX**: UI copy, content, and queries are **English-only** for MVP.

## Non-Functional Requirements (NFR)

- **NFR1. Performance**: **Hybrid query** typical latency meets targets; **answer generation** p95 ≤ 3s; graceful degradation options documented.
- **NFR2. Reliability**: Low error rate; clear ingest status and error surfaces; retries/backoff; **LLM service fallback** to raw results on failure.
- **NFR3. Maintainability**: Configuration via environment/deploy-time files (embedding model, Qdrant endpoint, fusion weights, **LLM provider/model**); no runtime tuning UI in MVP.
- **NFR4. Security (MVP)**: HTTPS; store credentials securely; **RBAC/SSO and advanced hardening are out of scope**.
- **NFR5. Compatibility**: Handle listed file types; **no OCR**; clearly surface unsupported inputs and fallbacks.
- **NFR6. Data residency**: **No regional residency constraints** in MVP.
- **NFR7. Tenancy**: **Single-tenant** deployment; org-scoped data separation without multi-tenant UX.
- **NFR8. Observability**: Basic logs for ingest/query; optional **CSV** export of metrics; no dashboards.
- **NFR9. Quality Targets**: On seed set, initial targets: **Q1 ≥ 0.70**, **Q2 ≥ 0.85**, **Q3 ≥ 3/5**; **answer relevance ≥ 4/5**; if unmet, create mitigation backlog.
- **NFR10. Scalability (MVP)**: Light concurrency (single-digit users); design does not preclude future scaling.

---
