# 1) Context & Goals (MVP)

- **Purpose:** Implement a lean backend that ingests user‑uploaded documents, chunks them using a **fixed method list**, embeds chunks, stores vectors for **hybrid retrieval (semantic + lexical)** with cosine similarity, and **synthesizes answers** using integrated LLM capabilities.
- **Scope (backend only):** File intake API, preprocessing & chunking, embeddings, vector storage (**Qdrant**), **lexical index**, hybrid query service, **LLM integration service**, answer synthesis pipeline, simple auth integration, structured logs.
- **Non‑goals (MVP):** Arabic/RTL, RBAC/SSO, multi‑tenant controls, OCR for scanned PDFs, advanced security hardening, dashboards, **evaluation harness**, **dead‑letter queues**, **explicit caching layers**.

**Success at GA (backend):**

- End‑to‑end pipeline operational: _Upload → Extract → Chunk → Embed → Qdrant + Lexical → Hybrid Query → LLM Synthesis → Answer Response_.
- Meets baseline **quality** (sanity checks) and acceptable **latency** on seed pack (informal).
- **Answer synthesis** operational with configurable LLM providers and quality validation.
- Basic retry & error surfacing; method & status visible to UI.

---
