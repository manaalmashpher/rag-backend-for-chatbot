# 8) Configuration (Environment Variables)

| Key                           | Purpose                          | Example / Default    |
| ----------------------------- | -------------------------------- | -------------------- |
| `EMBEDDING_PROVIDER`          | which provider to call           | `openai`             |
| `EMBEDDING_MODEL`             | model id (dim must match Qdrant) | `e3-small`           |
| `EMBED_DIM`                   | vector dimension                 | `1536`               |
| `QDRANT_URL`                  | Qdrant endpoint                  | `http://qdrant:6333` |
| `QDRANT_COLLECTION`           | collection name                  | `corpus_default`     |
| `DATABASE_URL`                | Postgres connection string       | `postgres://…`       |
| `TOPK_VEC`                    | vector top-K                     | `20`                 |
| `TOPK_LEX`                    | lexical top-K                    | `20`                 |
| `FUSE_SEM_WEIGHT`             | semantic weight                  | `0.6`                |
| `FUSE_LEX_WEIGHT`             | lexical weight                   | `0.4`                |
| `MAX_UPLOAD_MB`               | upload size cap                  | `20`                 |
| `JWT_ISSUER` / `JWT_AUDIENCE` | token validation (if enabled)    |                      |
| `RATE_LIMIT_QPS`              | per-IP or per-user search rate   | `5`                  |

---
