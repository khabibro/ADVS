# Phase 6 mentor verification evaluation

Run from `apps/api`:

```bash
.venv312/bin/python scripts/eval_phase6_mentor.py \
  --output ../../evaluation/phase6/mentor_verification.json
```

The evaluator reconstructs the six supported mentor business packages in an isolated temporary
database. Each of the four in-scope PDFs follows the real upload, PaddleOCR, classification,
extraction, normalization, evidence, and persistence path before the project verification API is
called with the mentor README's explicit `2026-09-19` reference date.

The six local-tax PDFs remain outside the ADVS domain and are not processed. The artifact stores
only package scenario labels, processing counts, status, issue codes, unresolved-rule counts,
agreement with mentor scenario metadata, and safety metrics. It stores no PDFs, filenames, OCR
text, extracted values, or synthetic identities. Because the mentor materials have no field-level
answer key, this is controlled scenario agreement, not exact verification or real-world accuracy.
