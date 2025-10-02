# 12) Performance Targets (Pinned)

- Hybrid search latency: **p95 ≤ 1.5s**, **p99 ≤ 3.0s** on seed corpus.
- **Answer generation latency: p95 ≤ 3.0s** on seed corpus.
- Ingestion throughput: **200–300 pages ≤ 20 min**.
- Upload limit: **20 MB**.

**Notes:**

- **Percentiles explained:** _p95_ means 95% of requests complete within the stated bound; _p99_ covers the tail (rare slow cases).
- **Testing policy:** During MVP **testing**, these targets are **reference‑only** (non‑binding); collect timings but do **not** gate pass/fail on these numbers.

---
