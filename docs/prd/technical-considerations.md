# Technical Considerations

## Platform Requirements

- **Target**: Web app (tester-facing), light concurrency.
- **Browser Support**: Modern evergreen browsers.
- **Performance**: Targets per **NFR1**.

## Technology Preferences

- **Vector DB**: **Qdrant**.
- **Search**: **Hybrid** (semantic + keyword) with cosine similarity; include **minimal lexical index** (BM25/FTS).
- **LLM**: **Configurable provider** (OpenAI, Anthropic, local models) with environment-based configuration.
- **Auth**: Email + password (MVP).
- **Hosting**: **SaaS**, single-tenant per deployment.

## Architecture Considerations

- **Repository**: Simple mono or polyrepo acceptable; keep config-driven.
- **Service Architecture**: Minimal services sufficient for MVP; avoid premature microservices.
- **Integration Requirements**: Stable IDs for chunks; ingest + lexical index jobs; **LLM service integration**.
- **Security/Compliance**: HTTPS; credential hygiene; **LLM API key management**; defer enterprise controls post-MVP.

---
