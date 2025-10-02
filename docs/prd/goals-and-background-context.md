# Goals and Background Context

## Goals

- Enable a user to **upload a document**, then **select a chunking method** from a fixed list (see Appendix A), and **ingest** it via preprocessing + embeddings into a vector database (Qdrant).
- Support **retrieval** using **hybrid search** (semantic + keyword) with **cosine similarity** for ranking/fusion.
- **Generate coherent answers** from retrieved chunks using integrated LLM capabilities.
- Provide a **simple, English-only** web UI suitable for testing and iteration.
- Ship with **basic authentication** (email + password) and **single-tenant** (per org) setup.
- Expose **method visibility + ingestion status** so testers can confirm what ran.
- Produce **basic logs and optional CSV exports** to support evaluation.

## Background Context

This MVP is a lean, test-focused application to prove ingestion + retrieval quality for small corpora. We prioritize a minimal feature set and quick iteration over enterprise capabilities. Arabic/RTL, SSO/RBAC, and advanced hardening are explicitly deferred until after we validate the end-to-end flow. A lightweight lexical index is included to enable hybrid search alongside vector similarity.

---
