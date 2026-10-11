# Test Plan

Unit tests cover the classifier (all four types, UNKNOWN, ambiguity, generic-word resistance, OCR whitespace tolerance), the four document extractors (happy path, missing fields, false-positive resistance), field normalization (dates, business numbers, text), the validation engine (READY/REVIEW_REQUIRED/NEEDS_CORRECTION, DB-configured rules, always-on checks), OCR provider error handling (timeout/retry policy, 4xx vs 5xx, malformed/empty responses), OCR reading-order text assembly, and upload file validation (magic bytes, corrupt-file rejection, page limits).

Integration tests (`tests/test_pipeline_integration.py`) drive the real HTTP API end-to-end with `MockOCRProvider`: successful graduation/business-registration processing, an UNKNOWN document, an OCR failure (kept structurally distinct from UNKNOWN and from a validation failure), an expired SME confirmation certificate (NEEDS_CORRECTION), missing fields (REVIEW_REQUIRED, never a fabricated value), and reprocessing (no duplicate derived rows).

Submission-verification tests use persisted canonical field fixtures so business rules do not
depend on OCR. They cover required/optional documents, configured references, exact normalized
comparisons, inclusive validity boundaries, fixed-date student rules, Decimal GPA comparisons,
all four rule outcomes, null-derived failure prevention, status precedence, persistence,
re-verification, and stale-result invalidation.

OCR unit tests stub PaddleOCR inference and use `MockOCRProvider` for full API integration tests. Real PaddleOCR model downloads and inference are not part of `make check`/`make check-all`.

A dedicated evaluation toolkit (`evaluation/`, see `evaluation/README.md`) reports classification, extraction, status and false-READY metrics on the fictional test-variant sets (`evaluation/datasets/synthetic/`: 299 development files and two 279-file hold-out sets, now development data; a third hold-out set is reserved and unseen) with a frozen scorer, plus injected-error suites E1–E18 (`evaluation/harness/`, run with `evaluation/harness/run_variants.py`; `make eval-variants` runs a digital-only pass). Phase reports are in `evaluation/phase_*/`, the denominators and uncertainty for the safety claims in `evaluation/phase_f/`. It catches regressions and validates fixes with evidence; it does **not** show real-world accuracy -- no physical photographs and no consented real documents have been evaluated. Earlier phases used seven real mentor-sample scans (the "P2.1 corpus", now archived outside the repository, all OCR-only, one known wrong OCR value at confidence 0.9166 -- `evaluation/reports/ADVS_system_audit_report.md` F-010); the extractors were developed against them, so they cannot serve as an unbiased test. Current test totals (2026-10-10): backend 555 `pytest` tests, frontend 107 `vitest` tests, 15 Playwright end-to-end tests with axe checks; `make demo-rehearsal` replays the demo scenarios.

Phase G (2026-10-11): 613 backend tests (`apps/api/tests/test_phase_g_text_layer.py` for hidden PDF text, `test_phase_g_university_name.py`), 108 web unit tests, 22 browser tests of which 15 run (the 7 mentor-PDF journeys are skipped unless `MENTOR_DIR` points at real documents, which are deliberately not used) including axe; `scripts/demo_rehearsal` runs D1–D9. Gate scripts: `evaluation/phase_g/scripts/` (`dev_gates.sh`, `gate_summary.py`, `pdf_manipulation_suite.py`, `pdf_manipulation_pipeline.py`, `final_judgement.sh`).

MVP acceptance criteria include backend tests passing, frontend lint/typecheck/build passing, migrations running, Docker config/build validation, health endpoint responding, upload/process/classify/extract/validate workflow functioning, and no secrets in tracked files.
