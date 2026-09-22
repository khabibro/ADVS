# Test Plan

Unit tests cover the classifier (all four types, UNKNOWN, ambiguity, generic-word resistance, OCR whitespace tolerance), the four document extractors (happy path, missing fields, false-positive resistance), field normalization (dates, business numbers, text), the validation engine (READY/REVIEW_REQUIRED/NEEDS_CORRECTION, DB-configured rules, always-on checks), OCR provider error handling (timeout/retry policy, 4xx vs 5xx, malformed/empty responses), OCR reading-order text assembly, and upload file validation (magic bytes, corrupt-file rejection, page limits).

Integration tests (`tests/test_pipeline_integration.py`) drive the real HTTP API end-to-end with `MockOCRProvider`: successful graduation/business-registration processing, an UNKNOWN document, an OCR failure (kept structurally distinct from UNKNOWN and from a validation failure), an expired SME confirmation certificate (NEEDS_CORRECTION), missing fields (REVIEW_REQUIRED, never a fabricated value), and reprocessing (no duplicate derived rows).

Submission-verification tests use persisted canonical field fixtures so business rules do not
depend on OCR. They cover required/optional documents, configured references, exact normalized
comparisons, inclusive validity boundaries, fixed-date student rules, Decimal GPA comparisons,
all four rule outcomes, null-derived failure prevention, status precedence, persistence,
re-verification, and stale-result invalidation.

OCR unit tests stub PaddleOCR inference and use `MockOCRProvider` for full API integration tests. Real PaddleOCR model downloads and inference are not part of `make check`/`make check-all`.

A dedicated evaluation toolkit (`evaluation/`, see `evaluation/README.md`) reports classification/extraction/validation metrics against a deterministic synthetic benchmark (112 samples across the four document types plus UNKNOWN, split 70/30 dev/held-out). Run `make eval` to regenerate the benchmark and score gold text; run `make eval-paddle` to process renderable samples through real PaddleOCR. It is useful for catching regressions and validating targeted fixes with evidence, not for claiming real-world accuracy -- no real or anonymized documents have been evaluated yet (see `evaluation/datasets/real/README.md`).

MVP acceptance criteria include backend tests passing, frontend lint/typecheck/build passing, migrations running, Docker config/build validation, health endpoint responding, upload/process/classify/extract/validate workflow functioning, and no secrets in tracked files.
