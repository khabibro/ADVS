# ADVS System Audit

Independent technical audit. Read-only on production throughout: no tracked
file was modified, no git write occurred, no gold annotation or scorer was
touched. All scratch work (probes, this report) lives under
`evaluation/system_audit/`. Audit date: 2026-10-04. Repository: branch
`main`, HEAD `48e3824a780e3c051cba2d2eb1838851db1fcf1e` (confirmed unchanged
at the end of this audit).

---

## 1. Executive summary

**Core question: how correct, complete, and trustworthy is ADVS today,
relative to the project it is supposed to deliver?**

It is a genuinely deterministic, evidence-gated pipeline with real,
non-trivial safety machinery — not a thin demo wrapped around a model. The
core philosophy ("rules decide, evidence supports, humans review
uncertainty") is implemented in actual code, not just asserted in
documentation: every OCR-derived field is unconditionally routed to human
review regardless of confidence, machine evidence and human corrections are
stored in genuinely separate columns, and stale reviews are invalidated by
a real processing-version mechanism, not a comment. At the same time, this
audit found and **reproduced** a concrete, realistic path to a false READY
verdict, and a concrete, realistic path to a false document-type
misclassification and a false cross-document mismatch — each triggerable by
ordinary, foreseeable configuration or document variety, not adversarial
input.

**Three most important strengths (verified, not asserted):**
1. The evidence-sufficiency policy is **general**, not case-specific: *any*
   OCR-sourced field is routed to `REVIEW_REQUIRED` regardless of
   confidence (F-010). This is a stronger, more defensible protection than
   a confidence threshold, and it explains why all 7 real documents in the
   P2.1 corpus required review — that is policy, not a gap.
2. Stale human reviews are invalidated by an actual `processing_version` +
   evidence-fingerprint mechanism after reprocessing, and machine evidence
   is stored separately from human corrections with no overwrite path found
   (F-012, F-013).
3. The document classifier is a deliberately simple, explainable,
   keyword-weighted heuristic with a documented abstention rule, and that
   abstention rule demonstrably prevents at least one real historical
   confusion (재학증명서/졸업증명서) by requiring a strong (not just
   cumulative weak) signal before committing to a type (F-011).

**Three most important risks (reproduced, not hypothesized):**
1. **A single, ordinary checklist-configuration choice produces a silent
   false READY.** Configuring one `REQUIRED_FIELD` rule for any one field
   disables the blanket missing-field safety net for *every other field* of
   that document type, at both the validation-engine layer and the
   service layer that assembles rules. A probe with `valid_from`/
   `valid_until` both unresolved, under a checklist that only requires
   `company_name`, produces **zero issues and `overall_status = READY`**
   (F-001, S0). This is the single most important finding in this audit.
2. **Company-name matching does not normalize Korean legal-entity
   notation.** `주식회사 X`, `(주)X`, `㈜X`, and `X(주)` — four entirely
   ordinary ways the same company's name appears across different
   certificate types — normalize to four different comparison strings,
   empirically reproduced (F-002, S1). This sits directly in the business
   workflow's core cross-document check.
3. **The classifier confidently misclassifies a real, unmodeled document
   type into a modeled one.** A local tax certificate (지방세
   납세증명서, not represented anywhere in `DocumentType`) is classified as
   `NATIONAL_TAX_PAYMENT_CERTIFICATE` (국세, a different certificate) at
   confidence 0.9 with `needs_review=False`, because the title signal
   match is a bare substring check (F-003, S1).

**One-sentence answer:** ADVS's deterministic core is more carefully built
than its headline test-pass numbers would suggest on their own, but it
contains at least one reproducible false-READY path and two reproducible
false-positive-match paths that a real deployment would hit under ordinary
use, not edge-case abuse — so it is trustworthy in its safety *philosophy*
and in large parts of its *implementation*, but not yet trustworthy as a
*whole system* without fixing F-001 specifically before anything else.

---

## 2. Scorecard

No overall average is given; these areas are not interchangeable.

| Area | Score /5 | Basis |
|---|---|---|
| Requirements coverage | 3 | All 8 mentor/proposal document types have `EXPECTED_FIELDS`, an extractor, and a classifier signal set. One field (`department` on `REAL-004`/`TRANSCRIPT`) is gold-annotated for a document type whose schema doesn't define it at all — a traceability gap between gold and production schema (see §9, carried from the prior gold-adjudication task). |
| Pipeline correctness | 3 | Stage-by-stage walkthrough (§5) found the pipeline does what it claims for the common path; one confirmed metadata-reporting bug (F-005) and one confirmed safety-net bypass (F-001) live in this layer. |
| Extraction quality | 3 | Field-level logic is careful and well-commented (see `gpa_field`/`gpa_scale_field`, date-range parsing) but normalization has a real gap (F-004 checksum) and comparison has a real gap (F-002 company-name variants). |
| Verification logic | 2 | Precedence (`NEEDS_CORRECTION > REVIEW_REQUIRED > READY`) is correctly implemented at both the per-document and submission level (verified by direct code read, §5). But F-001 is in this layer and is severe enough to cap the score. |
| Safety invariants | 2 | Several invariants genuinely HOLD (null≠failure in the default path, stale-review invalidation, machine/human separation). One concretely VIOLATED (F-001) under a realistic configuration. |
| Human review | 4 | The evidence-sufficiency policy is general and conservative (F-010); review decisions are structurally separated from machine data (F-013); `apps/admin`, the UI that would configure the F-001 trap, has **zero tests** (F-008), which is the main deduction. |
| Evaluation methodology | 3 | The scorer's 33-field denominator reproduces exactly from the raw gold file by independent recount (§7). The corpus itself is explicitly 2 real + 5 synthetic/recreated documents, single-page, which the P2.1 report itself already states cannot support a field-quality estimate — this audit did not find reason to disagree. |
| Test quality | 3 | 386 backend tests pass (0 failures, reproduced); 94/94 web frontend tests pass (reproduced, exact match to the cited claim); `apps/admin` has 0 tests. Sampling (§8) found safety-critical tests that exercise real production code paths, not mocks of their own assertions — but F-001's exact configuration shape (partial `REQUIRED_FIELD` list) does not appear to be covered by an existing test, which is how it survived undetected. |
| Architecture / configurability | 4 | Clean separation: classifier/extractor/normalizer/validator are independent, swappable, and the dormant structural layer is verifiably unreferenced (F-014) rather than merely claimed dormant. Rule configuration is genuinely data-driven (`ConfiguredRule`, DB-backed), not per-customer code forks. |
| Robustness | 2 | Pixel-budget and render-scale handling is thoughtful (documented rationale, `source_resolution_fit`), but the DPI it *reports* for a downscaled page is wrong (F-005), and PostgreSQL-specific concurrency and migration-vs-model consistency could not be verified in this environment at all (§10). |
| Security / privacy | 2 | No authentication or authorization exists anywhere in the API (F-007) — acceptable for the current capstone/demo phase, a hard blocker before any deployment handling real PII. Upload path-traversal guarding is real and well-built (F-019). The repo's own "security:audit" script is a narrow 5-point string check, not a vulnerability scan (F-009). |
| Frontend correctness | 2 (low confidence) | Both `apps/web` and `apps/admin` build and typecheck cleanly, and web's 94 tests pass, but this audit did not read frontend component code in depth (see §10) — this score is a floor set by build/test success, not a ceiling set by a code review. |

---

## 3. Repository state

- `git rev-parse HEAD`: `48e3824a780e3c051cba2d2eb1838851db1fcf1e`, branch `main` — matches the claimed starting state exactly, both before and after this audit (re-checked at the end; no drift).
- `git status --porcelain`: one pre-existing modified tracked file
  (`apps/api/app/document_intelligence/extraction/base.py`, not touched by
  this audit) and a set of pre-existing untracked evaluation/test
  directories, all left untouched. `evaluation/system_audit/` is the only
  new content this audit added.
- **Dependency versions** (installed, `apps/api/.venv312`, Python 3.12.14 —
  the correct interpreter; a second, stray `.venv` is Python 3.14.3,
  incompatible with `pyproject.toml`'s `requires-python = ">=3.12,<3.13"`,
  see F-017): FastAPI 0.141.1, Pydantic 2.13.5, Pydantic-settings 2.15.0,
  SQLAlchemy 2.0.54, Alembic 1.20.0, psycopg 3.3.6, PyMuPDF 1.28.2, Pillow
  12.3.0, **PaddleOCR 3.2.0 / PaddlePaddle 3.1.1 exact pins, matching the
  claim exactly** (`pyproject.toml` pins these with `==`; every other
  backend dependency is pinned with `>=`, not exact). Frontend: Next.js
  15.5.25 installed against a `^15.0.0` spec, React 19, TypeScript 5.5,
  Tailwind 3.4 — matches the claimed stack.
- **Committed private data**: searched the **entire** git history (`git log
  --all --diff-filter=A --name-only`), not just the current tree, for any
  PDF/PNG/JPEG/WEBP ever added, and separately for any path under
  `evaluation/datasets/real/`, `evaluation/private_runtime/`,
  `evaluation/backend_round2/work/`, `evaluation/gold/real/`. Result: every
  committed document image/PDF lives under `evaluation/datasets/synthetic/`
  or `evaluation/datasets/recreated/` — which `.gitignore`'s own comment
  states are fictional and intentionally safe to commit. No real/private
  path was ever added in any commit. `sample_data/` contains only a text
  fixture. This is a clean, verified result (F-015), not an assumption.
- Two tracked test files reference `REAL-00x` by name
  (`test_real_document_regressions.py`, `test_round2_real_document_fixes.py`);
  both were spot-read and use synthesized fixtures with a docstring
  explicitly stating the no-real-data policy — consistent with the above.
- **Repo map**: pnpm monorepo — `apps/api` (FastAPI backend), `apps/web`
  (applicant-facing Next.js app), `apps/admin` (checklist/rule
  configuration Next.js app), `packages/*` (shared UI, generated API
  contracts), `infra/`, `docs/`, `evaluation/` (a large, mostly-untracked
  set of phase-by-phase evaluation artifacts), `.github/` (CI config, not
  separately audited here). `apps/api/alembic/versions/` holds 6 linear
  migrations, `0001_initial` → `0006_field_reviews`, single head.
- Two minor, unexplained artifacts at repo root, both untracked: `txt.txt`
  (empty file) and `temp` (a 33 KB Mach-O arm64 executable of unknown
  origin) — F-018, informational only, not a git-hygiene issue since
  neither is tracked.

---

## 4. Requirements traceability matrix

Full depth was spent on the mentor-required business and student
workflows; `GRADUATION_CERTIFICATE`/`CAREER_CERTIFICATE` (proposal-only,
not in the mentor table) were checked at the schema/extractor level only,
not probed with the same depth as the four-table requirement below.

### Business workflow

| Document | Required check | Implemented? | Where | How it decides | Configurable? | Tested? | Real-input evidence | Gaps/risks |
|---|---|---|---|---|---|---|---|---|
| 사업자등록증 (reference) | company name, business number, "other reference info" extraction | Yes | `extraction/business_registration.py`; `EXPECTED_FIELDS[BUSINESS_REGISTRATION_CERTIFICATE]` = company_name, business_registration_number | Label-keyed regex/text extraction (rule-based, no model) | Field set is a code constant, not DB-configurable; rule *application* (required/optional) is DB-configurable | Yes, extractor-level tests exist | 1 real-ish (`near-real`) sample in gold (R2-02) | None beyond F-002/F-004 below |
| 중소기업확인서 | company name + business number match reference; validity/submission-date requirement | Partial | `validate_document()`/`_handle_business_number_match`, `_apply_configured_rule` for `COMPANY_NAME_MATCH`/`BUSINESS_REGISTRATION_NUMBER_MATCH`/`DATE_NOT_EXPIRED` | Deterministic string-equality after `comparable()` normalization; date comparison via `date.fromisoformat(...) >= date.today()` | Yes — rule params (`field`, `expected_value`, `max_age_days`) are DB rows | Yes (`test_*validation*`, engine-level) | None in the 7-document real corpus (no SME certificate present) | **F-002** (company-name variant mismatch), **F-001** (missing-field net bypass reachable for this exact document type's `valid_from`/`valid_until`) |
| 국세 납세증명서 | company name + business number match; valid at submission time | Partial | Same engine path as above; `EXPECTED_FIELDS` = company_name, business_registration_number, valid_until | Same mechanism | Yes | Yes | None in corpus | Same F-002/F-001 exposure; **F-003** (classifier confuses this type with the unmodeled local-tax certificate) |
| 4대 사회보험료 완납증명서 | business number + workplace name match; valid at submission time | Yes (logic present) | `extraction/social_insurance_payment.py`; `EXPECTED_FIELDS` = workplace_name, business_registration_number, valid_until | Same mechanism, `workplace_name` substituted for `company_name` in the label set only | Yes | Yes | Not in the 7-doc corpus for this exact type beyond what P2.1 covered (R2-01 is this type) | Same F-001/F-002 exposure |

### Student workflow

| Document | Required check | Implemented? | Where | How it decides | Configurable? | Tested? | Real-input evidence | Gaps/risks |
|---|---|---|---|---|---|---|---|---|
| 재학증명서 | university, department, student number, issue date, configurable issue-date rule | Yes | `extraction/enrollment.py`; `EXPECTED_FIELDS` = student_name, university_name, department, student_id, issue_date; `ISSUE_DATE_MAX_AGE` rule type | Label-keyed extraction + `_handle_issue_date_max_age` (configurable `max_age_days`, default 90) | Yes | Yes | 2 real/near-real samples in gold | None found beyond general F-001/F-002 exposure |
| 성적증명서 (optional) | issue date, GPA, configurable GPA threshold | Yes, with one caveat | `extraction/transcript.py`; `EXPECTED_FIELDS` = student_name, university_name, student_id, issue_date, gpa, gpa_scale | `gpa_field`/`gpa_scale_field` both parse a `"score/scale"` pattern from the *same* label-matched candidate text (confirmed by direct code read, carried from the prior gold-adjudication task in this session) | GPA threshold itself: **not found as a `RuleType`** — `RuleType` has no GPA-specific comparison beyond the generic `NUMERIC_COMPARISON` submission-scope rule type, which was not probed in this audit | Partially — extractor-level tests exist; the GPA-threshold *rule path* specifically was not exercised by a probe here | 2 real transcripts in gold (R2-03, R2-04) | **F-004** on any business-number field this document shares indirectly via cross-document checks is N/A here (transcripts carry no business number); the `department` field on `TRANSCRIPT` gold/schema mismatch noted above is a traceability gap, not an extraction bug |

**Status/precedence/principles row:**

| Requirement | Implemented? | Where | Verified how |
|---|---|---|---|
| READY/NEEDS_CORRECTION/REVIEW_REQUIRED enum, PROCESSING/FAILED elsewhere | Yes | `app/core/domain.py` `OverallStatus` (3 values) + `ProcessingStatus` (9 stage values incl. `FAILED`) | Direct read |
| Precedence NEEDS_CORRECTION > REVIEW_REQUIRED > READY | Yes, at both levels | `validation/engine.py::overall_status` (per-document); `validation/submission.py` lines ~133-137 (submission-level aggregation across documents) | Direct read of both aggregation functions, independently implementing the same precedence |
| Missing evidence ≠ deterministic failure | **Partial — HOLDS by default, VIOLATED under a realistic configuration** | `evidence_sufficiency.py`, `validation/engine.py::_default_required_field_issues` vs. F-001 | Probe (`probe_required_field_net.py`) |
| Machine extraction immutable; human corrections stored separately | Yes | `models/entities.py` `ExtractedField` vs. `FieldReview.original_*`/`reviewed_*` columns | Direct schema read; no write path found that mutates `ExtractedField` after creation |
| Stale reviews not reused after reprocessing | Yes | `services/reviews.py`, `processing_version`/`is_current`/`stale_at`/`original_evidence_fingerprint` | Direct read + existing test files (`test_field_reviews.py` et al.) |
| Configure workflows, don't rewrite engine per customer | Yes | `ConfiguredRule`/`DocumentRequirement`/`ValidationRule` DB rows feed a fixed, generic `ValidationEngine` | Direct read of `_apply_configured_rule` dispatch table |

---

## 5. Pipeline walk-through

Traced the real production path for a PDF/image document, reading the code
actually invoked (confirmed via import/call-site checks, not assumed):

1. **Upload & storage** (`api/v1/routes.py`, `services/storage/local.py`):
   filename sanitized (`sanitize_filename`), extension/MIME checked against
   `ALLOWED_EXT`/`ALLOWED_MIME` allow-lists, size capped
   (`max_upload_size_bytes`), stored path resolved and checked to be inside
   the storage root (two-layer guard: basename-only construction, then
   `.resolve()` + parents containment — F-019, real, not just a string the
   narrow audit script checks for).
2. **Duplicate detection**: SHA-256 checksum compared **within the same
   submission only** (`Document.submission_id == document.submission_id`)
   — confirmed intentional scoping, not a bug: the same file legitimately
   reappears across different submissions/projects.
3. **Page rendering** (`ocr/providers.py`): PDF pages rendered via PyMuPDF
   at a configured scale (288 DPI nominal → scale 4.0). A pixel-budget
   check (`_exceeds_page_budget`) can trigger `source_resolution_fit`,
   which renders at the page's own embedded-raster resolution instead of
   upsampling a low-res scan to the configured DPI — a reasoned, documented
   design decision (`_page_render_scale` docstring), not an oversight.
   **However**, the per-page metadata field `OCRPage.metadata["render_dpi"]`
   (set in `_normalize_page`, line ~480) is computed from the provider's
   fixed `self.render_scale`, not from the actual per-page scale that
   `_page_render_scale` returned for that page — so a page rendered via
   `source_resolution_fit` reports the wrong DPI under this key, while a
   separate, correctly-computed `effective_render_dpi` key exists in a
   different metadata dict from the PDF-rendering generator. **This is the
   exact, previously-flagged REAL-001 "288 vs 108" discrepancy, and the
   code confirms it is a reporting bug in one specific metadata field, not
   a rendering bug** (F-005).
4. **Preprocessing**: `ImagePreprocessor` exists; a tracked regression test
   (`test_round2_real_document_fixes.py`, finding R2-05) documents that it
   once had zero callers while EXIF orientation went uncorrected — the test
   file's docstring states this was fixed; not independently re-verified
   beyond reading that the test currently passes (it does, per §8).
5. **Embedded-text vs. OCR decision**: not independently traced in depth in
   this audit; the entire 7-document real corpus has 0 embedded-text
   documents (confirmed independently by the gold-file read in §7), so this
   decision path is **evidence-free for real documents** in this audit, same
   caveat P2.1 already carried.
6. **OCR provider**: `get_ocr_provider` dispatches on `settings.ocr_provider`
   (default `"paddle"`, confirmed in both `config.py` and `.env.example`).
   `MockOCRProvider` is reachable by setting `OCR_PROVIDER=mock` in any
   environment — **no environment-aware guard** prevents this in a
   production deployment (F-006); requires an explicit misconfiguration to
   trigger, not a latent default.
7. **Observation objects → layout/row grouping → classification →
   candidate generation → normalization → field resolution**: traced via
   `classification/classifier.py` (read in full, §6) and
   `extraction/base.py`/`extraction/transcript.py`/`sme_confirmation.py`
   (read in full/part). The dormant "structural" candidate-generation
   module (`extraction/structural.py`) has **zero importers anywhere under
   `app/`** (grep-confirmed) and `registry.py`'s extractor wiring does not
   reference it — the "dormant, unreachable" claim is **verified**, not
   just repeated (F-014).
8. **Evidence/provenance attachment, evidence policy/confidence**:
   `evidence_sufficiency.py`'s `EvidenceSufficiencyPolicy.assess()` is
   called from `services/document_validation.py::policy_gated_fields` and
   `services/reviews.py` — confirmed wired into the real path, not dead
   code. Any field with OCR-sourced evidence unconditionally receives the
   `OCR_REQUIRES_CONFIRMATION` reason and is therefore never `SUFFICIENT`
   regardless of confidence (F-010) — the strongest, most general safety
   property found in this audit. The parallel path for `embedded_pdf_text`
   evidence *can* reach `SUFFICIENT` (no OCR-confirmation reason applies),
   and this path is **completely unexercised by the current real corpus**
   (0/7 documents have an embedded text layer) — its safety is unverified
   empirically, only by code read.
9. **Validation rules / cross-document verification / status
   aggregation**: traced in full, §4's status/precedence row and §6's F-001.
10. **Human review queue / effective values**: `services/reviews.py`'s
    `EffectiveFieldResolver` combines machine fields with current,
    non-stale reviews; separate storage confirmed (F-013).
11. **API response / frontend display**: not traced at the same depth —
    see §10 for what was and wasn't checked here.

**Information-loss points identified:** none that silently *fabricate* a
value were found (the "take the first match" pattern the handoff mentions
for one historical GPA case was traced to `candidate_after_label` /
`GPA_RE.fullmatch`, which is a label-anchored, fail-closed regex, not a
first-match-wins heuristic over multiple candidates — current code does
not reproduce that historical pattern in the GPA path as read). The one
confirmed information-*distortion* point is F-005 (DPI metadata), which
loses truthful provenance, not the underlying value.

---

## 6. Safety invariant results

| Invariant | Result | Evidence |
|---|---|---|
| No False READY | **VIOLATED** (reproducible under a realistic config) | F-001, `probe_required_field_net.py` output: Case B — `valid_from`/`valid_until` both unresolved, one `REQUIRED_FIELD` rule scoped to `company_name` → **0 issues, `overall_status = READY`** |
| Null ≠ failure | **PARTIAL** — holds by default (`_default_required_field_issues` emits `WARNING`→`REVIEW_REQUIRED` for any unresolved field), but the same configuration that triggers F-001 also silently drops the "null" warning entirely for unlisted fields, rather than degrading it — it just disappears | Same probe, Case A vs Case B |
| Precedence NEEDS_CORRECTION > REVIEW_REQUIRED > READY | **HOLDS** | Direct read, `engine.py::overall_status` and `submission.py` aggregation, both implement identical precedence independently |
| Review-required fields never auto-decide | **HOLDS**, by construction | `ValidationEngine._supported_value` returns `None` whenever `field.needs_review` is true, so such a field can never satisfy a configured comparison/required-field check and cannot itself produce a `PASS` |
| High-confidence wrong values | **HOLDS, generally** | F-010 — protection is confidence-independent (any OCR evidence ⇒ review required), not a narrow fix aimed at the known REAL-003 case specifically |
| Stale reviews | **HOLDS** | F-012, version/fingerprint-gated, existing tests |
| Human corrections don't overwrite machine evidence | **HOLDS** | F-013, separate columns, no mutation path found |
| Validity logic boundary cases (expiry on/around submission day, timezone) | **PARTIAL / not fully probed** | Code uses `date.fromisoformat(value) >= date.today()` — a document expiring *today* is treated as still valid (an inclusive, defensible reading, not obviously wrong) — but `date.today()` takes the **server's local date**, with no explicit `Asia/Seoul` handling found anywhere searched; a server running in UTC near Korean midnight could evaluate a boundary date one day off. Not empirically tested against a live boundary in this audit — flagged `UNTESTABLE` here for want of time, not because it was tried and passed |
| Reference document (missing/duplicate 사업자등록증) | **Not independently probed** | `validate_required_documents` (submission-level, `REQUIRED_DOCUMENT` rule) reads correctly for the missing case by direct code inspection; the two-different-business-registration-certs-uploaded case was not probed |
| Duplicates (same file twice, same content different filename, different files same type) | **HOLDS for same-submission same-checksum; by-design out of scope for cross-submission** | §5 item 2; same-content-different-filename is covered since the check is checksum-based, not filename-based |

---

## 7. Claims verification table

| Claim | Source | Reproduced? | Command | Result |
|---|---|---|---|---|
| 368 backend tests passing | P2.1 quality gates | **Not verbatim — suite has grown** | `.venv312/bin/python -m pytest -q` | **386 passed, 0 failed**, 29.0s. Directionally consistent (more tests added since the historical snapshot: `test_p1_layout.py`, `test_p2_2_issue_date_attribution.py`, `test_round2_real_document_fixes.py`, `test_real_document_regressions.py` are untracked/new relative to that snapshot). Not a contradiction, but the literal "368" does not reproduce today. |
| 94 frontend tests passing | P2.1 quality gates | **Yes, exact match** | `pnpm --filter @advs/web test -- --run` | 9 test files, **94 passed (94)** |
| (implicit) admin frontend tests | — | N/A, claim is silent on this | `pnpm --filter @advs/admin test -- --run` | **"@advs/admin has no component tests yet"** — 0 tests. The "94 frontend tests" claim, read literally, is accurate for `web` but says nothing about `admin`, which has none (F-008). |
| 33 evaluated fields (P2.1) | P2.1 final report | **Yes, exact match, independently recounted** | direct Python count over `evaluation/backend_round2/work/ground_truth_v2.json`'s `gt` values | `VERIFIED(30) + VERIFIED_ABSENT(2) + PARTIAL(1) = 33`; `AMBIGUOUS(3) + NOT_EVIDENCED(1) = 4` not-evaluated — matches the claimed 33/4 split exactly from the raw gold file, not from the report's own prose |
| Structural layer resolves 0/9 target fields | P2.1 final report | **Not re-run** (would require executing the dormant module against observations — out of this audit's read-only/no-new-OCR-run scope) | — | Not independently reproduced; this audit instead verified the **reachability** claim (zero importers, F-014), which is a different and arguably more important check for a "dormant" claim |
| Synthetic classification 32/32; Extraction completeness 85/106→100/106; Post-P0 real 7/7, 16 CORRECT, recall 0.471; Safety: False READY 0, null-derived failures 0, stale reviews used 0 | Phase 5 / P0 / Phase 7 | **Not reproduced** | — | Out of practical time budget for this pass; these are historical point-in-time claims about an earlier code state and would require re-running phase-specific scripts this audit did not attempt. Listed here, not silently dropped — see §10. |
| Backend lint/type clean | implicit | **Yes** | `ruff check .` → `All checks passed!`; `mypy --explicit-package-bases app` (per `Makefile`, not the naive `mypy app` invocation, which fails on a module-resolution config error unrelated to type correctness) → `Success: no issues found in 63 source files` | Clean |
| Frontend lint/typecheck/build clean | implicit | **Yes** (lint/typecheck were cache hits, not forced-fresh; build was forced fresh for `@advs/web`) | `pnpm lint`, `pnpm typecheck`, `pnpm build` | All green; `@advs/web` build ran fresh end-to-end (6 pages); `@advs/admin` build log was a cache replay of a prior successful build, not independently re-executed fresh in this session |
| Repo "security:audit" passes | implicit | **Yes, but narrow** | `node scripts/security-audit.mjs` → `Security audit passed.` | Read the script: it is 5 static string-presence checks (no `.env` tracked, no OCR-secret string in frontend files, `ALLOWED_MIME`/`ALLOWED_EXT`/`sanitize_filename`/`.resolve()` present *by name* in one file, no `print(` in the OCR provider). **Not** a dependency-vulnerability scan, **not** a live traversal/auth test (F-009) |
| Migrations consistent with models | implicit | **Inconclusive** | `alembic upgrade head` (SQLite) → clean, 6 revisions applied; `alembic check` → reports `modify_type` drift (`NUMERIC()`→`UUID()`) on every UUID column across all 11 tables | Very likely a SQLite UUID-type-reflection artifact (SQLite has no native UUID affinity) rather than genuine drift, but **not verified against PostgreSQL** — no local Postgres instance was available in this environment. Reported here as **UNVERIFIED**, not as "probably fine" (F-016) |

---

## 8. Findings

Ordered by severity. `OBSERVED` unless marked `INFERRED`.

### F-001 — S0 — Partial REQUIRED_FIELD checklist silently disables the missing-field safety net for every other field

**OBSERVED, High confidence.**

**Evidence:** `apps/api/app/document_intelligence/validation/engine.py`
`_has_required_field_rule` (suppresses the blanket net the instant *any*
`REQUIRED_FIELD` rule exists, regardless of which field it names) and
`_handle_required_field` (only checks the field named in `rule.params`
when one is given); `apps/api/app/services/document_validation.py`
`configured_document_rules` (the same suppression condition, independently,
at the service layer: the safe auto-fill of `DEFAULT_REQUIRED_FIELDS` is
skipped the instant the checklist has *any* `REQUIRED_FIELD` rule).
Reproduced in `evaluation/system_audit/probe_required_field_net.py`
against the real `ValidationEngine`/`ExtractedValue` classes:

```
=== Case A: no configured_rules at all (pure default net) ===
  REQUIRED_FIELD passed=False severity=WARNING code=MISSING_REQUIRED_FIELD   (company-adjacent)
  REQUIRED_FIELD passed=False severity=WARNING code=MISSING_REQUIRED_FIELD
  overall_status = REVIEW_REQUIRED

=== Case B: ONE configured REQUIRED_FIELD rule, targeting company_name only ===
  overall_status = READY
```

In Case B, `valid_from` and `valid_until` are both unresolved (`None`) in
the input fields, exactly as they would be for a genuinely missing
validity period on an SME confirmation certificate. Zero issues are raised
for them.

**Steelman:** the suppression exists for a documented reason — a prior bug
(`R2-02` regression, see code comment) where *any* configured rule at all
silenced the net, so a checklist with only unrelated comparison rules
produced zero issues for every unresolved field. The current fix narrows
the trigger to specifically `REQUIRED_FIELD` rules, on the reasoning that
"only this rule type redefines what a document must supply." That
reasoning is sound for a checklist that lists *all* required fields
explicitly — the bug is that it also fires, with the same full suppression,
for a checklist that names only *one* field.

**Does the steelman hold?** No. The documented reasoning is about *whether*
any REQUIRED_FIELD rule exists, not about *which* fields it covers. A
checklist author adding "company_name is required" through a UI (there is
no code in this audit confirming the `apps/admin` UI prevents or warns
against a partial list — and `apps/admin` has zero tests, F-008) has no way
to know this also silently waives every other field's presence check for
that document type, with no compensating warning anywhere in the system.

**Impact:** a configuration mistake that is easy to make and invisible to
the person making it can turn a document with a missing, unresolved
validity date into `READY` — the exact failure mode `_always_on_expiration_issues`
(the one unconditional check in the file) was explicitly written to guard
against, except that check *also* only fires when `valid_until` resolves
to a value; it is silent, not a backstop, when the field is unresolved.

**Recommendation:** make the service-layer auto-fill
(`configured_document_rules`) additive rather than all-or-nothing — union
the admin's explicit `REQUIRED_FIELD` fields with `DEFAULT_REQUIRED_FIELDS`
for any field the admin did not explicitly mention, rather than skipping
the defaults entirely the moment one explicit rule exists. This is a
small, localized, well-scoped fix; it does not require touching OCR,
extraction, or the review UI.

---

### F-002 — S1 — Company-name comparison does not normalize Korean legal-entity notation

**OBSERVED, High confidence, empirically reproduced.**

**Evidence:** `apps/api/app/document_intelligence/validation/engine.py`
`comparable()` = `re.sub(r"[\s\W_]+", "", value.lower())`. Reproduced
directly against this exact function:

```
'주식회사 글로벌데이터로드' -> '주식회사글로벌데이터로드'
'(주)글로벌데이터로드'      -> '주글로벌데이터로드'
'㈜글로벌데이터로드'        -> '글로벌데이터로드'
'글로벌데이터로드(주)'      -> '글로벌데이터로드주'
```

Four ordinary ways to write the same company name produce four different
comparison keys. `㈜` (U+3283, a single CJK "circled ideograph" symbol) is
a non-word character under Python's `\W` and is stripped entirely; the
parenthesized form `(주)` strips only the parentheses, leaving the bare `주`
syllable; the spelled-out `주식회사` form is retained in full. None collapse
to the same key.

**Steelman:** `COMPANY_NAME_MATCH` only fires when both an expected name
and an extracted `company_name` field are present (`engine.py`, line
~108), so this does not by itself cause a false READY — it causes a false
`NEEDS_CORRECTION` (an `ERROR`-severity mismatch) when the two source
documents legitimately use different notations for the same company, which
is routine in real Korean paperwork (사업자등록증 often prints the full
`주식회사`, while a 중소기업확인서 or 국세납세증명서 for the same company may
print `(주)` or `㈜`).

**Does the steelman hold?** Yes, this is specifically a false-reject risk,
not a false-accept risk — but it sits exactly in the mentor-required
"company name matches the reference" check for 3 of the 4 business-workflow
document types, so a false reject here routinely blocks a correct
submission.

**Recommendation:** normalize known Korean legal-entity markers
(`주식회사`, `(주)`, `㈜`, trailing `(주)`) to a single canonical token (or
strip them consistently) before comparison, the same way date and business-
number normalization already strip format noise.

---

### F-003 — S1 — Classifier confidently misclassifies a real, unmodeled document type into a modeled one

**OBSERVED, High confidence, empirically reproduced.**

**Evidence:** `apps/api/app/document_intelligence/classification/classifier.py`.
`DocumentType` has no local-tax (지방세) certificate at all — only
`NATIONAL_TAX_PAYMENT_CERTIFICATE` (국세). The national-tax signal set
includes `Signal("납세증명서", TITLE)` (weight 5.0) matched by plain
substring containment (`signal.text in haystack`, after whitespace
squashing). Reproduced directly against `DocumentClassifier.classify()`:

```python
local_tax_text = "지방세 납세증명서\n납세자명 : 홍길동\n유효기한 : 2026-12-31\n"
# -> predicted_type: NATIONAL_TAX_PAYMENT_CERTIFICATE
#    confidence_score: 0.9
#    evidence: ['납세증명서', '납세자명', '유효기한']
#    needs_review: False
```

"지방세납세증명서" contains "납세증명서" as a trailing substring, so the
TITLE-weight signal fires on a document whose actual title is a different
certificate, and no competing `DocumentType` exists to create the ambiguity
margin that would otherwise force an abstention to `UNKNOWN`.

**Steelman:** the system is only required to model the document types in
the mentor's table, and a local-tax certificate was never one of them —
so classifying it at all might be considered out of scope.

**Does the steelman hold?** No — the risk is not that the system fails to
*recognize* a local-tax certificate (that would be a correct `UNKNOWN`
abstention, which the classifier is explicitly designed to do when signals
are weak). The risk is that it *confidently asserts* the document is a
different, specific, modeled certificate type, at `needs_review=False`,
which would route it straight into the national-tax validation path
(checking a business number and expiry against the wrong legal document)
rather than to human review.

**Recommendation:** make at least the national-tax TITLE signal
title-anchored or boundary-checked (e.g. require it not be immediately
preceded by "지방세"/"지방"), or add a small negative-signal set for known
near-duplicate real document types the system does not model, mirroring
the `MIN_STRONG_SIGNAL_WEIGHT`/ambiguity-margin mechanism that already
protects the 재학증명서/졸업증명서 pair (F-011) against the same class of
risk.

---

### F-004 — S2 — No checksum validation on Korean business registration numbers

**OBSERVED, High confidence (code read; the Korean business-registration-number check-digit algorithm is a documented public standard this audit did not re-derive from first principles, but whose *absence* in this code is directly visible).**

**Evidence:** `apps/api/app/document_intelligence/normalization/field_normalizer.py`
`normalize_business_number()` validates only the digit-grouping *shape*
(`\d{3}[- ]?\d{2}[- ]?\d{5}`, 10 digits) via `BUSINESS_NUMBER_RE`; no
check-digit computation is present anywhere in the file or in
`extraction/base.py`'s `business_number_field`.

**Steelman:** shape validation plus independent cross-document comparison
(two OCR reads of "the same" number must still match character-for-character)
already catches many realistic OCR digit errors, since a shape-valid but
digit-wrong number from one document is unlikely to equal a shape-valid
number from another unless the error is correlated.

**Does the steelman hold?** Partially. It protects the cross-document
*comparison* case reasonably well (an isolated digit flip on one document
won't coincidentally equal the other document's number), but it does
nothing for the single-document case — a `BUSINESS_REGISTRATION_CERTIFICATE`
used as the reference, uploaded alone, with one OCR-misread digit, is
accepted as a "VERIFIED"-looking value with no internal consistency check
at all, and becomes the reference every other document is compared
against.

**Recommendation:** add the standard weighted check-digit validation
(weights `1,3,7,1,3,7,1,3,5`, final digit derived from
`(sum + floor(9th_digit*5/10)) mod 10`) as an additional gate in
`normalize_business_number`, returning `None` (not a guess) on failure,
consistent with the file's own stated philosophy ("never invents a value").

---

### F-005 — S2 — `render_dpi` metadata reports the configured DPI, not the actual per-page DPI, when a page is downscaled

**OBSERVED, High confidence — resolves the previously-flagged but
unexplained REAL-001 "288 vs 108" discrepancy to its root cause.**

**Evidence:** `apps/api/app/document_intelligence/ocr/providers.py`.
`_page_render_scale()` (and its caller) correctly compute a per-page
`(scale, reason)` and store it as `effective_render_dpi` in the
PDF-rendering generator's transform dict (line ~376: `"effective_render_dpi":
int(72 * scale)`). But `_normalize_page()` (line ~480) independently sets
`metadata["render_dpi"] = int(72 * self.render_scale)`, where
`self.render_scale` is the **provider-level, globally configured** scale
set once in `__init__` from `settings.paddle_ocr_render_dpi` — not the
per-page `scale` that `_page_render_scale` computed for that specific
page. When `source_resolution_fit` reduces a page's actual scale below the
configured value (to avoid upsampling a low-resolution embedded raster — a
reasoned, documented, and correct design decision on its own terms), the
`render_dpi` key silently keeps reporting the unused configured value.

**Steelman:** the downscale behavior itself is intentional and well-justified
(the docstring on `_page_render_scale` explains exactly why: "a page box
routinely overstates the resolution of the raster it wraps ... multiplies
memory and OCR time ... producing no additional evidence"). One could argue
`render_dpi` is meant to document "what was *configured*," and
`effective_render_dpi` is the field meant to document "what was *actually
used*," by design — i.e., two different, both-intentional questions.

**Does the steelman hold?** Only partially — the field is literally named
`render_dpi` (not `configured_render_dpi`) and lives at the same
dict-nesting level as other **per-page, per-document** observational facts
(`doc_orientation`, `provider_version`), which invites a reader (a human
reviewer, or any future evaluator script) to treat it as describing this
page, not the provider's static configuration. The correctly-scoped field
already exists under a different key one level up, making the `render_dpi`
field redundant at best and misleading at worst.

**Recommendation:** either thread the per-page `scale` into
`_normalize_page()` so `render_dpi` reflects the actual page, or rename
the field to make its static, configuration-level meaning unambiguous.

---

### F-006 — S3 — No environment-aware guard on `OCR_PROVIDER=mock`

**OBSERVED, Medium confidence.** `get_ocr_provider()` accepts `mock` in any
environment; `app_env` is read elsewhere (`safe_log_context`) but never
checked against `ocr_provider` anywhere this audit found. Default is safely
`paddle`, and `.env.example` sets `OCR_PROVIDER=paddle` correctly — this
requires an explicit misconfiguration to reach, not a latent default.
**Recommendation:** optionally raise if `app_env` indicates production and
`ocr_provider == "mock"`; low priority.

---

### F-007 — S1 (production-readiness, not a core-workflow defect) — No authentication or authorization anywhere in the API

**OBSERVED, High confidence.** All 21 `Depends(...)` usages in
`app/api/v1/routes.py` are `Depends(get_db)` only. No `Depends` wraps an
identity/auth check anywhere searched in `app/api` or `app/core`. A `User`
model exists (`email`, `display_name`) and `Project.owner_id` is a foreign
key to it, but nothing in the traced request path resolves "who is
calling" or checks it against `owner_id` before reading/writing a
project, document, or review. Any caller who knows or guesses a project
UUID can read or modify it.

**Steelman:** this is a capstone-project system at an explicitly pre-Phase-9
stage (per the P2.1 report this audit's predecessor task read, readiness
was already assessed `NO` for reasons unrelated to auth), and the mentor's
required-behavior table does not list authentication as a check to
implement — it may simply not have been in scope yet.

**Does the steelman hold?** For the "demo readiness" question (§10), yes.
For "real-document readiness" and especially "production readiness," no —
the documents this system is explicitly built to process carry resident
registration numbers, student numbers, and business registration numbers
(confirmed present in the private gold annotations read during the prior
gold-adjudication task in this session), so an unauthenticated API is a
hard blocker before any deployment that would touch a real user's real
documents, not a nice-to-have.

**Recommendation:** out of scope to design here; flagged as the clearest
single gap between "works for a demo" and "safe for a pilot with real
users."

---

### F-008 — S3 — `apps/admin` has zero tests

**OBSERVED, High confidence.** `pnpm --filter @advs/admin test -- --run`
outputs `"@advs/admin has no component tests yet"` and exits 0 (a stub
script, not a real test runner invocation). Notable specifically because
`apps/admin` is the UI surface where the F-001 checklist configuration
would be authored by a human, and it has the one build route in the whole
system (`/rules`, confirmed present in the production build output) most
directly implicated in that finding.

---

### F-009 — S3 — The repo's "security:audit" script is a narrow static check, not a vulnerability scan

**OBSERVED, High confidence.** `scripts/security-audit.mjs` (39 lines)
performs exactly 5 checks: no tracked `.env*` file, no `OCR_SECRET` string
literal in `apps/web`/`apps/admin` source, and that three specific strings
(`ALLOWED_MIME`, `ALLOWED_EXT`, `sanitize_filename`, `.resolve()`) appear
*by name* in `storage/local.py`, plus no `print(` call in the OCR provider
file. It does not run `npm audit`/`pip-audit`, does not test path
traversal behaviorally, and does not touch authentication at all (there is
none to test, per F-007). "Security audit passed" in any report should be
read at this scope, not as a general security clearance.

---

### F-010 — Positive — The evidence-sufficiency policy is general, not case-specific

**OBSERVED, High confidence.** `evidence_sufficiency.py`'s
`EvidenceSufficiencyPolicy.assess()` unconditionally appends
`OCR_REQUIRES_CONFIRMATION` to `reasons` whenever any evidence item has
`source_kind == "ocr"` (line ~87-91), and returns `SUFFICIENT` only when
`reasons` is empty — meaning **every** OCR-sourced field is routed to
`REVIEW_REQUIRED`, independent of its confidence score. This is a stronger
property than "confidence ≥ 0.90 passes"; it directly explains why the
P2.1 corpus's known wrong value (confidence 0.9166) was still caught, and
why all 7 real documents in that corpus required review — that outcome is
this policy working as designed on an all-OCR corpus, not an evaluation
gap. Confirmed wired into the real path via `services/document_validation.py`
and `services/reviews.py` (not dead code). Caveat: the parallel
`embedded_pdf_text`-only path can reach `SUFFICIENT` and is completely
unexercised by the current real corpus (0/7 real documents have embedded
text) — this audit verified the code's logic for that path but could not
verify it empirically for lack of a real embedded-text sample.

---

### F-011 — Positive — The classifier's strong-signal requirement prevents a real, previously-documented confusion

**OBSERVED, High confidence.** `MIN_STRONG_SIGNAL_WEIGHT = IDENTIFIER`
requires at least one `IDENTIFIER`-or-stronger signal hit before a type is
ever asserted (not just `UNKNOWN`), and the code's own comment cites a
concrete historical regression this was built to fix: an unrelated document
containing only `대학교`+`학과` (both `SUPPORT`-weight, shared between
`ENROLLMENT_CERTIFICATE` and `GRADUATION_CERTIFICATE`) was confidently
misclassified in 6/85 dev samples before this rule existed. Walking the
current `SIGNALS` table confirms both types' `SUPPORT`-only shared terms
cannot alone clear `MIN_STRONG_SIGNAL_WEIGHT`, so a title-misread document
of either type now correctly abstains to `UNKNOWN` rather than guessing.
Notably, the *same class* of protection does not extend to every pair —
see F-003, where a `TITLE`-weight substring match alone is sufficient and
no competing modeled type exists to trigger the ambiguity margin.

---

### F-012 — Positive — Stale-review invalidation is real, version-tracked, and tested

**OBSERVED, High confidence.** `FieldReview` carries `processing_version`,
`is_current`, `stale_at`, `superseded_at`, and
`original_evidence_fingerprint`; `services/reviews.py` compares
`review.processing_version == document.processing_version` and
`stale_at is None` before treating a review as current, and marks prior
reviews stale (`is_current=False`, `stale_at=now`) on reprocessing. Covered
by `tests/test_field_reviews.py` and three other test files referencing
`stale`.

---

### F-013 — Positive — Machine evidence and human corrections are structurally separate, with no overwrite path found

**OBSERVED, High confidence.** `ExtractedField` has no "corrected value"
column; `FieldReview` stores `original_raw_value`/`original_normalized_value`
and `reviewed_raw_value`/`reviewed_normalized_value` as distinct columns on
a distinct table. No code path was found in this audit that writes to
`ExtractedField` after its initial creation.

---

### F-014 — Positive — The dormant structural layer's unreachability is verified, not asserted

**OBSERVED, High confidence.** `grep -rln "extraction.structural"` across
`app/` returns no importers; `extraction/registry.py`'s `_EXTRACTORS` dict
(the only extractor dispatch table in production) does not reference the
module. The claim this audit's predecessor task (P2.1) made about this
module was independently re-verified here from scratch, not taken on
trust.

---

### F-015 — Positive — No hardcoded document-specific or personal data found in production code

**OBSERVED, High confidence.** Grepped `app/` for literal Korean names,
university names, and `REAL-00x` identifiers seen during this session's
prior work; zero matches in production code (only two *test* files
reference `REAL-00x`, and only in prose/docstrings describing which
regression they pin, with synthesized fixtures). Cross-checked against the
full git history finding in §3.

---

### F-016 — UNVERIFIED (not a pass, not a fail) — Migration/model consistency against PostgreSQL

**Could not verify.** `alembic check` against a fresh SQLite database
reports `modify_type` drift (`NUMERIC()` → `UUID()`) on every UUID-typed
column across all 11 tables. This is most plausibly a SQLite
type-reflection artifact — SQLite has no native UUID column affinity, so
reflecting a column declared `UUID(as_uuid=True)` back from a live SQLite
schema cannot agree with the Python-side type regardless of whether the
migration is actually correct — but this environment has no PostgreSQL
instance, so the claim could not be checked against the actual target
dialect either way. Reported as unverified, not as "probably fine."

---

### F-017 — S3 — Two Python virtualenvs, one incompatible with the pinned Python version

**OBSERVED.** `apps/api/.venv312` (Python 3.12.14) matches
`requires-python = ">=3.12,<3.13"`; a second `apps/api/.venv` is Python
3.14.3, outside that range. The `Makefile`/root `package.json` default to
`.venv312` correctly, so this is a stray-artifact risk (an engineer running
a bare `venv/bin/...` command by habit) rather than an active bug.

---

### F-018 — Informational — Unexplained untracked binary at repo root

**OBSERVED.** `temp` (33 KB, Mach-O 64-bit arm64 executable) and `txt.txt`
(empty) sit untracked at the repository root. Not a git-hygiene issue
(neither is tracked), but unexplained provenance; not investigated further
(executing an unknown binary was out of scope for a read-only audit).

---

### F-019 — Positive — Upload path-traversal guard is real, not just a name the audit script checks for

**OBSERVED, High confidence.** `services/storage/local.py` constructs the
stored path from `Path(storage_key).name` (basename only, stripping any
`../` components before path construction at all), then independently
verifies the `.resolve()`d path is contained within the resolved storage
root before use — a second, defense-in-depth layer beyond the basename
strip. Read the actual logic, not just confirmed the string `security-audit.mjs`
checks for is present.

---

### F-020 — S2 — Test-count claim precision

**OBSERVED.** See §7. The literal "368 backend tests" does not reproduce
today (386 do, 0 failing) because the suite has grown; the "94 frontend
tests" claim reproduces exactly but is silent on `apps/admin`'s 0 tests.
Neither is a fabricated number, but neither should be re-cited without the
date/HEAD it was measured at.

---

## 9. Evaluation and dataset assessment

The scorer and gold file (`evaluation/backend_round2/work/ground_truth_v2.json`,
schema `p2-1-observation-ground-truth-v2`/gold `v2`) were read, not edited,
consistent with this audit's constraints — the pending gold-adjudication
task for `REAL-003 gpa_scale`, `REAL-004 department`, `REAL-003 gpa` is a
separate, already-tracked piece of work this audit deliberately did not
touch or resolve (confirmed by reading the file but not writing to it).

**What the current numbers mean:** the 33-field denominator is real and
independently reproducible by direct count (§7), not a report artifact.
**What they do not mean:** a field-level accuracy estimate for ADVS in
general. The real corpus is 7 single-page documents, 2 genuinely personal
(`REAL-003`, `REAL-006`) and 5 synthetic-realistic or recreated (three with
obvious placeholder identities, per the gold file's own `source_category`
annotations read in this session). `BUSINESS_REGISTRATION_CERTIFICATE`,
`SME_CONFIRMATION_CERTIFICATE` have **zero or one** real example each
within this corpus (confirmed by `document_type` tally across the 7
samples read in this and the prior session). Any accuracy or recall figure
drawn from these 7 documents is a statement about this small, mostly-
synthetic mixture, not about Korean administrative paper in general — the
P2.1 report already says this, and this audit's independent reading of the
same gold file did not find reason to disagree or to soften it.

**Gold-quality observation carried forward, not resolved:** the `department`
field is gold-annotated for `REAL-004`/`TRANSCRIPT` even though
`EXPECTED_FIELDS[DocumentType.TRANSCRIPT]` in production code does not
include `department` at all (confirmed independently in this audit at
`apps/api/app/core/domain.py`, matching what the dedicated gold-adjudication
task found and flagged separately). This audit does not resolve it — that
is explicitly the other task's scope — but notes it here because it bears
on requirements traceability (§4): a gold-evaluated field with no
production schema entry cannot be meaningfully scored against this
system's own stated field set for that document type.

---

## 10. What I could not verify, and why

- **Full reproduction of every historical headline number** (Synthetic
  classification 32/32; Extraction completeness 85/106→100/106; Post-P0
  real 7/7 classification, 16 fields CORRECT, recall 0.471; Phase 7 safety
  claims: False READY 0, null-derived failures 0, stale reviews used 0).
  These are point-in-time claims tied to specific earlier phase scripts;
  reproducing them would mean locating and re-running each phase's own
  harness against the code at that historical point or re-deriving
  equivalent numbers against current code, which this audit's time budget
  did not reach after the depth spent on §6-§8's safety-invariant work.
  Not claimed true or false — simply not re-run.
- **PostgreSQL-specific behavior** (migration drift, §7/F-016; concurrency
  under real contention). No PostgreSQL instance was available in this
  environment; `docker-compose.yml` defines one but starting it was not
  attempted (judged out of scope for a read-only code/behavior audit
  without the user's explicit go-ahead to stand up infrastructure).
  Everything database-related in this audit ran against SQLite only.
- **Frontend component-level correctness** (§10.9 in the brief: status-label
  wording honesty, evidence display accuracy, review-decision round-trip,
  multi-file upload/duplicate-click protection). Both apps were confirmed
  to build and typecheck cleanly and `@advs/web`'s 94 tests pass, but this
  audit did not read `apps/web/src`/`apps/admin/src` component code. The
  frontend-correctness score in §2 is explicitly a floor, not a ceiling.
  This is the largest unaddressed section relative to the brief's ask.
  Finding in text form says so (F-020 only indirectly touches this).
- **Boundary-date and timezone edge cases empirically** — read the code
  (`date.today()`, no explicit `Asia/Seoul` handling found), but did not
  write a probe that actually crosses a UTC/KST day boundary.
  **Reference-document edge cases** (no 사업자등록증 uploaded at all; two
  conflicting 사업자등록증 uploaded) — read the relevant code paths
  (`validate_required_documents`) but did not probe them directly the way
  F-001 was probed.
- **Dependency vulnerability scan** — `npm audit`/`pip-audit` were not run;
  the repo's own "security:audit" script does not run them either (F-009).
- **GPA-threshold rule path** (`NUMERIC_COMPARISON`/the submission-scope
  comparison rules in `validation/submission.py`) — read that the rule type
  exists and is dispatched, but did not probe a configured GPA threshold
  end-to-end the way F-001's `REQUIRED_FIELD` path was probed.
- **The `temp` binary at repo root** — not executed or further inspected,
  consistent with a read-only audit of unknown, untracked binary content.

---

## 11. Prioritized recommendations

Smallest, evidence-backed next steps, respecting the project's own stated
sequence (gold adjudication → corrected baseline → targeted P2.2
intervention). None of these propose replacing OCR, adding an LLM/VLM, or
any redesign.

1. **Fix F-001 first, before anything else in this list.** It is the only
   `S0` finding and the only one that produces a false `READY`. The fix is
   small and localized (§8, F-001's recommendation) — make
   `configured_document_rules`'s default-field auto-fill additive to, not
   replaced by, an admin's explicit partial `REQUIRED_FIELD` list. Add a
   regression test shaped exactly like `probe_required_field_net.py`'s
   Case B to `apps/api/tests/` so this cannot silently regress again.
2. **Fix F-002** (company-name legal-entity-notation normalization) next —
   it directly blocks the mentor-required business-workflow matching check
   for realistic input, and the fix is a small, bounded addition to
   existing normalization code, not a new subsystem.
3. **Fix F-003** (national/local tax substring collision) — narrow or
   anchor the `납세증명서` TITLE signal, or extend the existing ambiguity
   mechanism (already proven to work for the enrollment/graduation case,
   F-011) to cover this pair too.
4. **Add F-004's checksum validation** to `normalize_business_number` — a
   contained, well-specified addition consistent with the file's existing
   fail-closed philosophy.
5. **Fix F-005's metadata field** (thread the real per-page scale into
   `render_dpi`, or rename it) — low effort, removes a misleading
   provenance field before anyone builds tooling that trusts it.
6. **Add `apps/admin` test coverage (F-008)**, starting with the
   `/rules` checklist-authoring flow — this is the UI surface that creates
   the exact configuration shape F-001 depends on; a test here would have
   caught F-001's user-facing consequence even before the engine-level fix.
7. Everything else in this report (F-006, F-007, F-009, F-016, F-017,
   F-018, F-020) is lower-severity or explicitly a production-readiness
   item rather than a correctness defect in the current phase — track, but
   do not block the next evaluation phase on them.

This sequencing deliberately does **not** touch gold annotations, OCR, or
the structural layer — consistent with both this audit's constraints and
the project's own stated phase ordering.

---

## 12. Appendix

**Environment:** macOS (darwin), repo at `/Users/admin/Documents/ADVS`,
Python 3.12.14 (`apps/api/.venv312`), Node via pnpm workspace, Next.js
15.5.25.

**Commands run (exact):**
```
git rev-parse HEAD ; git status --porcelain ; git branch --show-current
git log --all --diff-filter=A --name-only --pretty=format:   (full history scan)
git check-ignore -v ...
.venv312/bin/python -V ; .venv312/bin/pip list
.venv312/bin/python -m pytest -q
.venv312/bin/ruff check .
.venv312/bin/mypy --explicit-package-bases app
pnpm lint ; pnpm typecheck ; pnpm build
pnpm --filter @advs/web test -- --run
pnpm --filter @advs/admin test -- --run
node scripts/security-audit.mjs
DATABASE_URL="sqlite:///..." .venv312/bin/alembic upgrade head
DATABASE_URL="sqlite:///..." .venv312/bin/alembic check
grep -rn ... (classifier signals, hardcoding search, auth search, as cited inline per finding)
.venv312/bin/python3 evaluation/system_audit/probe_required_field_net.py
.venv312/bin/python3 <<EOF ... comparable() variants ... EOF
.venv312/bin/python3 <<EOF ... DocumentClassifier local-tax probe ... EOF
```

**Probe scripts saved under `evaluation/system_audit/`:**
- `probe_required_field_net.py` — F-001's reproduction (kept as a
  candidate regression test shape, not wired into the real suite by this
  audit).
- `notes.md` — working notes and plan, kept for traceability.

No other files were created or modified outside `evaluation/system_audit/`.
`git status --porcelain` at the end of this audit shows the identical
pre-existing diff this audit started with, plus the new, untracked
`evaluation/system_audit/` directory.
