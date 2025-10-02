# 15) Scanned-PDF Detection (No OCR in MVP)

If characters/page `< 20` on ≥ 80% of pages, set status `blocked_scanned_pdf` and surface `blocked_reason: "scanned_pdf"` in status API. \*
