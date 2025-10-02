# 13) Rate Limiting & Security Notes

- Rate limit `search` and `upload` (`RATE_LIMIT_QPS=5`).
- Validate JWT in non-local; allow dev header token locally.
- Password hashing (bcrypt/argon2) at web-app; backend trusts JWT.
- Secrets via env/manager; never log secrets.

---
