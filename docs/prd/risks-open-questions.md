# Risks & Open Questions

## Key Risks (sample)

- **R1. PDF layout/table handling** may reduce chunk quality for method **(7)**; mitigation: degrade to paragraph-per-page with page refs.
- **R2. Tokenizer mismatch** between libs can skew chunk sizing; mitigation: standardize tokenizer + version pinning.
- **R3. Resource spikes** under fused queries; mitigation: cap batch sizes; profile and cache hot results.
- **R4. Evaluation subjectivity** for Q3; mitigation: simple rubric + double-rater subset.
- **R5. LLM response quality** may vary; mitigation: implement quality validation and fallback to raw results.
- **R6. LLM API reliability** could impact user experience; mitigation: robust error handling and graceful degradation.

## Open Questions

1. ~~Confirm **P1/P2** latency thresholds for hybrid queries.~~
2. Confirm initial **embedding model/provider** and dimension.
3. Agree on **Top‑K** and fusion weight defaults.
4. Define minimal **log fields** and CSV schema for evaluation outputs.
5. Confirm **LLM provider/model** selection and configuration approach.
6. Define **answer quality metrics** and validation criteria.

---
