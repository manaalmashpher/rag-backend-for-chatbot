# Chatbot with RAG — MVP

## Product Requirements Document (PRD)

> Filename: `docs/prd.md`

---

## Change Log

| Date       | Version | Description                          | Author    |
| ---------- | ------- | ------------------------------------ | --------- |
| 2025-09-10 | 0.1     | Initial PRD draft from Project Brief | John (PM) |
| 2025-09-29 | 0.2     | Added LLM integration requirements   | John (PM) |

---

## Goals and Background Context

### Goals

- Enable a user to **upload a document**, then **select a chunking method** from a fixed list (see Appendix A), and **ingest** it via preprocessing + embeddings into a vector database (Qdrant).
- Support **retrieval** using **hybrid search** (semantic + keyword) with **cosine similarity** for ranking/fusion.
- **Generate coherent answers** from retrieved chunks using integrated LLM capabilities.
- Provide a **simple, English-only** web UI suitable for testing and iteration.
- Ship with **basic authentication** (email + password) and **single-tenant** (per org) setup.
- Expose **method visibility + ingestion status** so testers can confirm what ran.
- Produce **basic logs and optional CSV exports** to support evaluation.

### Background Context

This MVP is a lean, test-focused application to prove ingestion + retrieval quality for small corpora. We prioritize a minimal feature set and quick iteration over enterprise capabilities. Arabic/RTL, SSO/RBAC, and advanced hardening are explicitly deferred until after we validate the end-to-end flow. A lightweight lexical index is included to enable hybrid search alongside vector similarity.

---

## Requirements

### Functional Requirements (FR)

- **FR1. Upload**: Users can upload a document for ingestion.
- **FR2. File types**: Accept **PDF, DOCX, TXT, MD**. **Scanned PDFs (no OCR) are flagged/blocked** with a clear message.
- **FR3. Method selection**: At upload time, users must select one **chunking method** from the fixed list (no in‑app parameter tuning in MVP).
- **FR4. Preprocessing**: System normalizes text (whitespace, encoding) and extracts structure where possible (headings, paragraphs, tables/pages where applicable).
- **FR5. Embeddings**: Generate embeddings using a configurable provider/model (set via environment/config).
- **FR6. Ingestion**: Persist chunks + vectors to **Qdrant** with stable identifiers.
- **FR7. Lexical index**: Build/maintain a **minimal lexical index** (e.g., BM25/FTS) per corpus to enable hybrid search.
- **FR8. Hybrid query**: Provide a **search UI** that executes hybrid retrieval (semantic + lexical) and returns fused, ranked results with source attributions and chunk/method metadata.
- **FR9. LLM Integration**: ~~Integrate configurable LLM service to synthesize retrieved chunks into coherent, contextual answers.~~ **DEFERRED**
- **FR10. Answer Generation**: ~~Generate natural language responses that directly address user queries using retrieved document chunks as context.~~ **DEFERRED**
- **FR11. Auth**: **Email + password** authentication; single-tenant org scope.
- **FR12. Status & observability**: Show **ingestion status** (per document + per method) and log basic pipeline events; allow **CSV export** of evaluation metrics/logs.
- **FR13. (Removed — out of scope for MVP) Evaluation harness (seed set)**.
- **FR14. English-only UX**: UI copy, content, and queries are **English-only** for MVP.

### Non-Functional Requirements (NFR)

- **NFR1. Performance**: **Hybrid query** typical latency meets targets; **answer generation** p95 ≤ 3s; graceful degradation options documented.
- **NFR2. Reliability**: Low error rate; clear ingest status and error surfaces; retries/backoff; ~~**LLM service fallback** to raw results on failure.~~ **DEFERRED**
- **NFR3. Maintainability**: Configuration via environment/deploy-time files (embedding model, Qdrant endpoint, fusion weights, ~~**LLM provider/model**~~); no runtime tuning UI in MVP.
- **NFR4. Security (MVP)**: HTTPS; store credentials securely; **RBAC/SSO and advanced hardening are out of scope**.
- **NFR5. Compatibility**: Handle listed file types; **no OCR**; clearly surface unsupported inputs and fallbacks.
- **NFR6. Data residency**: **No regional residency constraints** in MVP.
- **NFR7. Tenancy**: **Single-tenant** deployment; org-scoped data separation without multi-tenant UX.
- **NFR8. Observability**: Basic logs for ingest/query; optional **CSV** export of metrics; no dashboards.
- **NFR9. Quality Targets**: On seed set, initial targets: **Q1 ≥ 0.70**, **Q2 ≥ 0.85**, **Q3 ≥ 3/5**; ~~**answer relevance ≥ 4/5**~~; if unmet, create mitigation backlog.
- **NFR10. Scalability (MVP)**: Light concurrency (single-digit users); design does not preclude future scaling.

---

## User Interface Design Goals (High-Level)

- **Primary flows**: (1) **Upload & Ingest** with method selection; (2) **Search & Results** with source snippets and metadata; (3) **Answer Generation** with synthesized responses.
- **Information architecture**: Minimal navigation—top-level tabs or sections for **Upload**, **Ingestion Status**, and **Search**.
- **Feedback & Errors**: Clear progress and completion states; explicit messages for blocked formats (e.g., scanned PDFs) and failed steps.
- **Method visibility**: Surface chosen chunking method and key preprocessing details in status and result views.
- **Answer Display**: Present both raw search results and synthesized answers with clear source attribution.
- **Accessibility & i18n**: English-only now; plan for RTL/i18n post-MVP.

---

## MVP Scope

**Note:** LLM integration (Epic 9) has been deferred for future implementation. The MVP will provide raw search results with source attributions instead of synthesized answers.

### Core Features (Must Have)

- End-to-end pipeline: **Upload → Preprocess → Embed → Ingest (Qdrant)**.
- **Chunking method selection** from fixed list at upload time.
- **Hybrid search** (semantic + lexical) with fused ranking and source attributions.
- ~~**LLM integration** for answer synthesis from retrieved chunks.~~ **DEFERRED**
- **Email/password auth** and **single-tenant** deployment.
- **Status visibility** for ingestion and simple **logs/CSV** export.

### Out of Scope (MVP)

- Arabic/RTL UI and broader i18n
- RBAC and SSO
- Multi-tenant features
- Advanced security hardening and compliance tooling
- Automated PII scrubbing/redaction
- Analytics dashboards beyond logs/CSV
- OCR for scanned PDFs

### MVP Success Criteria

- **Quality**: Hit@5 ≥ 0.70; Hit@10 ≥ 0.85; Median human relevance ≥ 3/5 on seed set; ~~**Answer relevance ≥ 4/5**~~.
- **Performance**: p95 ≤ 1.5s; p99 ≤ 3.0s; ~~**Answer generation p95 ≤ 3s**~~.
- **Ingestion**: 200–300 pages ≤ 20 min.

---

## Success Metrics

- **Quality**: **Q1 ≥ 0.70**, **Q2 ≥ 0.85**, **Q3 ≥ 3/5** on seed set; ~~**Answer relevance ≥ 4/5**~~.
- **Performance**: **Hybrid query latency p95 ≤ 1.5s, p99 ≤ 3.0s; ~~answer generation p95 ≤ 3s~~; ingestion throughput (200–300 pages) ≤ 20 min.**
- **Reliability**: Meaningful error messages for blocked inputs and failed steps; ~~**LLM service fallback** to raw results.~~ **DEFERRED**
- **Usability**: Testers complete upload→ingest→query→answer flow without assistance.

---

## Technical Considerations

### Platform Requirements

- **Target**: Web app (tester-facing), light concurrency.
- **Browser Support**: Modern evergreen browsers.
- **Performance**: Targets per **NFR1**.

### Technology Preferences

- **Vector DB**: **Qdrant**.
- **Search**: **Hybrid** (semantic + keyword) with cosine similarity; include **minimal lexical index** (BM25/FTS).
- **LLM**: ~~**Configurable provider** (OpenAI, Anthropic, local models) with environment-based configuration.~~ **DEFERRED**
- **Auth**: Email + password (MVP).
- **Hosting**: **SaaS**, single-tenant per deployment.

### Architecture Considerations

- **Repository**: Simple mono or polyrepo acceptable; keep config-driven.
- **Service Architecture**: Minimal services sufficient for MVP; avoid premature microservices.
- **Integration Requirements**: Stable IDs for chunks; ingest + lexical index jobs; ~~**LLM service integration**.~~ **DEFERRED**
- **Security/Compliance**: HTTPS; credential hygiene; ~~**LLM API key management**~~; defer enterprise controls post-MVP.

---

## Constraints & Assumptions

- **A1. Corpus size**: ~200–300 pages total for MVP.
- **A2. Language**: English-only UI/content.
- **A3. File types**: PDF/DOCX/TXT/MD; **no OCR**.
- **A4. Chunking methods**: Fixed list (no runtime tuning); defaults documented.
- **A5. Fusion**: Default weights (e.g., semantic 0.6 / lexical 0.4) and Top‑K defined via config.
- **A6. Embeddings**: Provider/model set via environment; at least one viable model available.
- **A7. LLM Integration**: ~~Provider/model configurable via environment; fallback to raw results on failure.~~ **DEFERRED**
- **A8. Deployment**: SaaS, single-tenant; light concurrency.
- **A9. Observability**: Logs and optional CSV exports; no dashboards.
- **A10. Data residency**: Not required for MVP.
- **A11. Scanned PDFs are blocked/flagged (no OCR in MVP).**

---

## Risks & Open Questions

### Key Risks (sample)

- **R1. PDF layout/table handling** may reduce chunk quality for method **(7)**; mitigation: degrade to paragraph-per-page with page refs.
- **R2. Tokenizer mismatch** between libs can skew chunk sizing; mitigation: standardize tokenizer + version pinning.
- **R3. Resource spikes** under fused queries; mitigation: cap batch sizes; profile and cache hot results.
- **R4. Evaluation subjectivity** for Q3; mitigation: simple rubric + double-rater subset.
- **R5. LLM response quality** may vary; mitigation: implement quality validation and fallback to raw results. **DEFERRED**
- **R6. LLM API reliability** could impact user experience; mitigation: robust error handling and graceful degradation. **DEFERRED**

### Open Questions

1. ~~Confirm **P1/P2** latency thresholds for hybrid queries.~~
2. Confirm initial **embedding model/provider** and dimension.
3. Agree on **Top‑K** and fusion weight defaults.
4. Define minimal **log fields** and CSV schema for evaluation outputs.
5. ~~Confirm **LLM provider/model** selection and configuration approach.~~ **DEFERRED**
6. ~~Define **answer quality metrics** and validation criteria.~~ **DEFERRED**

---

## Milestones (Reference)

- **M0–M6** staged plan covering baseline ingestion/search, methods integration, hybrid online, eval & perf, reliability, UX/docs, and acceptance.

---

## Appendix A — Chunking Methods (Fixed List)

The following methods MUST be present in MVP (selectable at upload time):

1. **Fixed token windows (sliding)**
2. **Sentence-based**
3. **Paragraph-based**
4. **Heading-aware (Markdown/HTML)**
5. **Semantic (similarity-driven)**
6. **Recursive character/token splitter**
7. **Table/page/layout-aware (for PDFs)**
8. **Hybrid hierarchical**

---

## Appendix B — Glossary (selected)

- **Hybrid search**: Combining semantic vector similarity with keyword retrieval (e.g., BM25) for balanced recall/precision.
- **Qdrant**: Vector database used for storing embeddings and enabling vector similarity search.
- **Seed set**: Curated set of documents and Q/A pairs used to evaluate retrieval quality.
- **LLM Integration**: Large Language Model integration for synthesizing retrieved chunks into coherent answers.
- **Answer Synthesis**: Process of converting retrieved document chunks into natural language responses that directly address user queries.
