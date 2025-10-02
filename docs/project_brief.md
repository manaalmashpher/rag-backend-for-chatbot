# Project Brief — Chatbot with RAG (MVP)

## Section 1 — Project Overview (Updated)

**Project name (working):** Chatbot with RAG — MVP

**Purpose (what we're building):** A basic, test-focused web app where a user can:

1. upload a document,
2. choose a chunking methodology from a provided list,
3. run preprocessing + embeddings,
4. ingest into a vector DB,
5. query with **hybrid search + cosine similarity** for retrieval,
6. receive **synthesized answers** from retrieved chunks using integrated LLM capabilities.

**Now vs later:**

- **Now (MVP/testing):** English-only UI, very basic feature set, no extra security hardening.
- **Later:** Arabic-first experience (RTL), stronger auth/RBAC, broader productionization.

**Key decisions already made:**

- **Vector DB:** Qdrant.
- **Search:** Hybrid (semantic + keyword) with cosine similarity.
- **Hybrid search components:** Include a **minimal lexical index** (e.g., BM25/FTS) to support hybrid search.
- **LLM Integration:** Configurable provider (OpenAI, Anthropic, local models) for answer synthesis.
- **Auth:** Simple email + password for now.
- **Hosting model:** **SaaS** (not self-hosted).
- **Tenancy:** **Single-tenant** (per org).
  - **Note:** Single org per deployment; org-scoped data separation (no multi-tenant UI or roles in MVP).
- **Data residency:** **None required for MVP** (no KSA constraint).
- **Corpus (initial):** ~200–300 pages worth of material; PDFs/DOCX/TXT/MD (non‑scanned preferred); **max 20 MB** per file.

**Provided by PM:**

- **Provided methods (MVP):**

- (1) Fixed token windows (sliding)
- (2) Sentence-based
- (3) Paragraph-based
- (4) Heading-aware (Markdown/HTML)
- (5) Semantic (similarity-driven)
- (6) Recursive character/token splitter
- (7) Table/page/layout-aware (for PDFs)
- (8) Hybrid hierarchical

**Out of scope for MVP (explicit):**

- **Arabic/RTL UI** and broader **i18n** work.
- **Multi‑tenant** features.
- **Advanced security hardening** beyond basic auth.
- **PII scrubbing/redaction** and automated compliance tooling.
- **Evaluation dashboards/analytics** (beyond basic logs).

**Glossary (to include later):** RTL, RBAC, SaaS vs on‑prem, PII vs PHI, data georesidency, i18n.

---

### Rationale & Assumptions (delta)

- **MVP simplicity:** Keeps scope tight for fast testing; postpones advanced enterprise controls until after proving ingestion + retrieval.
- **Qdrant:** Solid vector store with a straightforward API; reduces infra overhead vs rolling our own.
- **Hybrid search:** Balances semantic recall with keyword precision; needs a lightweight lexical index even in MVP.
- **SaaS + single-tenant:** Simplifies ops while providing per‑org isolation.

---

## Section 2 — Objectives & Success Criteria

**Primary objective:** Demonstrate end‑to‑end ingestion and retrieval with acceptable latency and relevance on a small seed set.

**Secondary objectives:**

- Provide a simple UI to upload docs, select chunking method, and query.
- Capture logs/metrics sufficient to judge readiness for a more formal evaluation later.

**Success measures (MVP proxies):**

- **Q1 (Hit@5)** ≥ **0.70**
- **Q2 (Hit@10)** ≥ **0.85**
- **Q3 (Median human relevance)** ≥ **3/5** on a seed set
- **Q4 (Answer relevance)** ≥ **4/5** on synthesized responses
- **P1 (p95 query latency)** ≤ **1.5s**
- **P2 (p99 query latency)** ≤ **3.0s**
- **P3 (Answer generation p95)** ≤ **3.0s**

---

## Section 3 — Scope, NFRs & Constraints

### 3.1 In‑Scope (MVP)

- File types: PDF, DOCX, TXT, MD (non‑scanned preferred; **no OCR**)
- Upload → extract → chunk → embed → index
- **Hybrid search** (vector + lexical) with fixed fusion weights
- **LLM integration** for answer synthesis from retrieved chunks
- Simple email/password auth; no SSO/RBAC
- English‑only

### 3.2 Out‑of‑Scope (MVP)

- Arabic/RTL & i18n beyond English
- Advanced security controls (SSO, RBAC)
- OCR for scanned PDFs
- Production dashboards/analytics

### 3.3 Performance Targets (tie‑in)

- Query latency: p95 ≤ 1.5s; p99 ≤ 3.0s (baseline env)
- Answer generation: p95 ≤ 3.0s (baseline env)
- Ingestion throughput: **200–300 pages** in ≤ 20 min end‑to‑end

### 3.4 Reliability & Stability

- **R1 Error rate:** < **1%** of operations (upload, ingest, query) return 5xx or unhandled exceptions.
- **R2 (MVP Idempotency)**: **Deferred.** Duplicate chunks on re‑ingest are acceptable during testing; de‑dup planned **post‑MVP**.
- **R3 Basic retry:** Network/timeout transient failures retried at least once and logged.

### 3.5 Security (MVP posture)

- HTTPS outside localhost; basic email/password login; no RBAC/SSO.

### 3.6 Hybrid Search Definition

- **BM25/FTS**: Common lexical search scoring / full‑text search.
- **Hybrid Fusion**: Combining vector and lexical scores into a final ranking.
- **Top‑K**: Number of results retrieved/returned.

### 3.7 Acceptance Checklist (MVP)

| ID  | Item                          | Target                                   | Owner    | Evidence                                | Notes                  | Pass? |
| --- | ----------------------------- | ---------------------------------------- | -------- | --------------------------------------- | ---------------------- | ----- |
| R1  | Error rate                    | < 1% 5xx/unhandled                       | QA       | Aggregate error counts across stages    | Error summary CSV      | [ ]   |
| R2  | Idempotency (Deferred in MVP) | N/A (Deferred)                           | PM       | N/A                                     | Scope note / changelog | [ ]   |
| R3  | Basic retry                   | At least one retry on transient failures | Dev      | Log samples showing retry attempts      | —                      | [ ]   |
| P1  | p95 latency                   | ≤ 1.5s                                   | Dev + QA | CSV metrics, logs                       | Baseline env           | [ ]   |
| P2  | p99 latency                   | ≤ 3.0s                                   | Dev + QA | CSV metrics, logs                       | Baseline env           | [ ]   |
| Q1  | Hit@5                         | ≥ 0.70                                   | Analyst  | CSV metrics + annotated queries         | Seed set               | [ ]   |
| Q2  | Hit@10                        | ≥ 0.85                                   | Analyst  | CSV metrics + annotated queries         | Seed set               | [ ]   |
| Q3  | Human relevance (median)      | ≥ 3/5                                    | Analyst  | Annotator notes + sample justifications | Seed set               | [ ]   |

---

## Section 4 — Technical Defaults

### 4.1 Embeddings & Storage

- Embedding provider/model via env (`EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`).
- Vector store: Qdrant; metadata per chunk `{doc_id, chunk_id, method, source, page/section}`.

### 4.2 Retrieval Defaults

- **Top‑K**: semantic=20, lexical=20; fused return **10**.
- **Fusion weights**: semantic **0.6**, lexical **0.4** (fixed for MVP).

### 4.3 Lexical Index

- Minimal BM25/FTS per corpus for hybrid search.

### 4.4 Language

- English‑only; **no OCR** for scanned PDFs.

### 4.5 Default Parameters

**Chunking defaults (may be tuned):**

- **(1) Fixed token windows (sliding)**: window **800** tokens, overlap **120**.
- **(2) Sentence‑based**: merge sentences up to **~800** tokens.
- **(3) Paragraph‑based**: merge paragraphs up to **~1000** tokens.
- **(4) Heading‑aware (Markdown/HTML)**: cap **~1200** tokens; include heading path in metadata.
- **(5) Semantic (similarity‑driven)**: detect topic boundaries; target **~700–1000** tokens; threshold **TBD**.
- **(6) Recursive character/token splitter**: fallback order headings→paragraph→sentence→token; cap **~1000** tokens; overlap **~100**.
- **(7) Table/page/layout-aware (PDFs)**: keep tables/pages intact; segment by regions; cap **~1000** tokens; **no OCR**.
- **(8) Hybrid hierarchical**: headings→sentence merge; cap **~1000** tokens; overlap **~120**.

**Query/retrieval defaults:**

- **Top‑K**: semantic=20, lexical=20; fused return **10**.
- **Fusion weights**: semantic **0.6**, lexical **0.4** (fixed for MVP).

**Embedding config:**

- **Provider/model**: **TBD via env** (e.g., `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`).

### 4.6 Non‑Functional Constraints

- **Reliability**: Basic retry on transient failures; **idempotency deferred in MVP**.
- **Security**: Email/password auth; HTTPS; no advanced hardening.
- **Performance**: Targets defined in Section 3.

---

## Section 5 — Risks & Assumptions (MVP)

### 5.1 Risk Register

> Likelihood: L (Low) / M (Medium) / H (High) · Impact: L/M/H · Status: unchecked until mitigated

| ID   | Risk                                                                                           | Likelihood | Impact | Mitigation                                                                | Owner        | Status |
| ---- | ---------------------------------------------------------------------------------------------- | ---------- | ------ | ------------------------------------------------------------------------- | ------------ | ------ |
| R-01 | **Hybrid requires lexical index**—without it, hybrid claims aren’t real                        | M          | H      | Implement minimal BM25/FTS, fixed fuse; unit test hybrid path             | Dev          | [ ]    |
| R-02 | **PDF extraction quality**—tables/figures/layout lost (no OCR)                                 | M          | H      | Use layout-aware method **(7)**; warn users; add sample PDFs to test pack | Dev + QA     | [ ]    |
| R-03 | **Semantic method (5) complexity**—boundary detection accuracy varies                          | M          | M      | Provide fallback to sentence‑based (2); cap chunk sizes; monitor Q1/Q2    | Dev + QA     | [ ]    |
| R-04 | **Latency spikes** (cold start, network)                                                       | M          | M      | Cache hot queries; pre‑warm; reduce Top‑K; profile                        | Dev          | [ ]    |
| R-05 | **Seed set bias** (quality metrics skew)                                                       | L          | M      | Diversify seed; document selection rationale; annotate edge cases         | Analyst      | [ ]    |
| R-06 | **Scanned PDFs without OCR**—ingest empty/partial text                                         | H          | M      | Block/flag uploads; user message; add to out‑of‑scope                     | PM           | [ ]    |
| R-07 | **Idempotency (post‑MVP)**—MVP allows duplicates; track duplication rate; plan de‑dup post‑MVP | M          | M      | Document deferral; add de‑dup to backlog; optionally log duplicate rate   | Dev + QA     | [ ]    |
| R-08 | **Evaluation subjectivity** for Q3 manual relevance                                            | M          | L      | Calibrate annotators; double‑label on a subset; keep notes with examples  | QA + Analyst | [ ]    |

### 5.2 Assumptions

- Logs/CSV exports are sufficient for MVP evaluation.
- Fusion weights can remain fixed for MVP.

### 5.3 Assumptions to Validate

- **V‑A1:** PDF layout extraction quality on our seed set (esp. tables).
- **V‑A2:** Semantic boundary detection (method 5) meets Q1/Q2 thresholds.
- **V‑A3:** Query latency p95/p99 targets on baseline environment.
- **V‑A4:** Duplicate rate under re‑ingest is acceptable for MVP (**idempotency deferred**); de‑dup slated post‑MVP.

---

## Section 6 — Milestones & Timeline (MVP)

### 6.1 Timeline at a Glance (4 weeks)

- **Week 1 — Bootstrap & Pipeline Skeleton**
  - Repo + env scaffolding, Qdrant connectivity, tokenizer choice, structured log format
  - Upload→extract→**chunk method (1)**→embed→index→**vector-only query** working
- **Week 2 — Chunking & Hybrid Search**
  - Integrate **all 8 provided methods** (1–8) with defaults
  - Build **lexical index** (BM25/FTS); implement **fixed fusion** (0.6 semantic / 0.4 lexical)
- **Week 3 — Evaluation & Performance**
  - Seed **test pack** (5 docs + Q/A); implement measurement (logs + optional CSV)
  - Hit **Q1/Q2/Q3** quality proxies; tune for **P1/P2** latency targets; implement retries
- **Week 4 — Hardening, Docs & Sign‑off**
  - UX clarity (method shown; ingestion status); reliability checks; finalize docs
  - Run **Acceptance Checklist**; record demo; stakeholder sign‑off

### 6.2 Milestones & Exit Criteria

| ID  | Milestone            | Target | Exit Criteria (tied to measures)                                                                       | Evidence                       |
| --- | -------------------- | ------ | ------------------------------------------------------------------------------------------------------ | ------------------------------ |
| M0  | Project Bootstrap    | End W1 | Vector‑only baseline working; logs in place.                                                           | Screen capture + logs          |
| M1  | Methods Integrated   | Mid W2 | All **8 methods** set up with defaults.                                                                | Per‑method pipeline logs       |
| M2  | Hybrid Search Online | End W2 | Lexical index built; fusion path wired; basic 10‑result retrieval                                      | Query logs + sample outputs    |
| M3  | Eval & Perf Pass     | Mid W3 | **Q1 ≥ 0.70, Q2 ≥ 0.85, Q3 ≥ 3/5**; **P1 ≤ 1.5s, P2 ≤ 3.0s** or mitigation backlog created.            | CSV metrics + notes            |
| M4  | Reliability          | End W3 | **R1** and **R3** satisfied (low error rate; basic retry logged). **R2 idempotency deferred for MVP.** | Retry evidence + error summary |
| M5  | UX & Docs            | Mid W4 | Method visibility + ingestion status; brief runbook finished.                                          | Screenshots + docs             |
| M6  | Acceptance & Demo    | End W4 | **Acceptance Checklist** all green or waivers filed; demo recorded; sign‑off.                          | Checklist + recording          |

### 6.3 Dependencies & Critical Path

- **Critical**: Embedding provider/model selection; Qdrant availability; lexical index implementation for hybrid; **PDF layout handling for method (7)**; tokenizer standardization to keep chunk limits consistent.
- **Sequencing**: M1 → M2 (hybrid needs methods + lexical); M2 → M3 (quality/perf need hybrid online).

### 6.4 Deliverables

- Code repo with pipeline, UI, and configs
- Seed **test pack** (docs + Q/A + answer locations)
- Metrics **CSV exports** and log samples
- This **Project Brief** and a short **Runbook** (install, config, operate)

### 6.5 Go/No‑Go Gates

- **Gate A (Post‑M2)**: Hybrid working; F3/F4 met; proceed to evaluation.
- **Gate B (Release)**: All Acceptance Checklist items green or accepted with explicit waivers.

### 6.6 Contingency Playbook (if targets slip)

- **p95 latency > 1.5s** → reduce Top‑K, cache hot results, profile bottlenecks
- **Semantic boundary quality low** → fall back to sentence‑based (2) or **hybrid hierarchical (8)**
- **PDF layout extraction weak** → degrade to paragraph‑per‑page with page refs

---

### Appendix A — Definitions

- **BM25/FTS** — Common lexical scoring / full‑text search
- **Hybrid Fusion** — Combined scoring from vector + lexical paths
- **Top‑K** — Candidate set size for retrieval

### Appendix B — Chunking Methods Cheat Sheet (Provided in MVP)

1. **Fixed token windows (sliding)** — 800 tokens / 120 overlap. _Strong baseline; uniform windows._
2. **Sentence‑based** — Merge sentences up to ~800 tokens. _Preserves semantics; punctuation‑dependent._
3. **Paragraph‑based** — Merge paragraphs up to ~1000 tokens. _Natural blocks; variable sizes._
4. **Heading‑aware (Markdown/HTML)** — Cap ~1200 tokens; record heading path. _Great for docs/manuals._
5. **Semantic (similarity‑driven)** — Boundary by topic shift; ~700–1000 tokens. _Higher quality; tune threshold._
6. **Recursive char/token splitter** — Fallback: headings→paragraph→sentence→token; cap ~1000 / overlap ~100. _Robust._
7. **Table/page/layout‑aware (PDFs)** — Keep tables/pages intact; cap ~1000; **no OCR**. _Preserve structure._
8. **Hybrid hierarchical** — Headings then sentence merge; ~1000 tokens; overlap ~120. _Balanced default for mixed tech docs._

### Appendix C — Default Parameters Snapshot (MVP)

- **Supported file types**: PDF, DOCX, TXT, MD (non‑scanned preferred). **Max 20 MB** per file.
- **Embeddings**: Provider/model set via env (`EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`).
- **Vector store**: Qdrant; metadata per chunk: `{doc_id, chunk_id, method, source, page/section}`.
- **Lexical index**: Minimal BM25/FTS per corpus.
- **Retrieval**: semantic top‑k=20, lexical top‑k=20, fused return=10; fusion weights **0.6/0.4** (semantic/lexical).
- **Language**: English‑only. **No OCR**. **No dashboards**; logs/CSV only.

### Appendix D — Test Pack Structure (Repo)

```
/testdata/
  docs/
    ...
```
