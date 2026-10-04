# Phase B Report — Safety Fixes, Measured Before and After

Branch `phase-b/safety-fixes`, from `main` at `6f7605f7eb26273be012ae68a693c3aa2c12540b`.
Not pushed, not merged. `p2.2/issue-date-label-gate` untouched throughout.

## Decisions used

- **DECISION_1** (company-name mismatch severity): `UNDECIDED` →
  **default applied** — a remaining mismatch after legal-entity-notation
  normalization is still `NEEDS_CORRECTION`. No severity code was changed;
  B-4 only added the normalization step before the existing comparison.
- **DECISION_2** (unsupported look-alike documents): `UNDECIDED` →
  **default applied** — 지방세 납세증명서, 휴학증명서, 졸업예정증명서 all
  classify as `UNKNOWN` with `needs_review=true`. No new `DocumentType` was
  added.

## Test-variant move

- Source: `~/Desktop/ADVS_test_variants/` (already unzipped; no
  `ADVS_test_variants_ALL.zip` was present on the Desktop at the time of
  this phase — only the one candidate folder existed, so no ambiguity to
  resolve).
- Verified before moving: 299 files listed in `manifest.json`, all present,
  all SHA-256 matched, `contains_real_personal_data: false` at the top
  level and on every one of the 299 per-file entries.
- Moved (`mv`, not copy) to `evaluation/datasets/synthetic/test_variants/`.
  Hash check re-run after the move: 299/299 present, 0 missing, 0 hash
  mismatches.
- `.gitignore`: added `evaluation/datasets/synthetic/test_variants/{business,student,formats}/`
  (the ~45MB of generated document binaries — regenerable from
  `_generator/` + `manifest.json`). `README.md`, `manifest.json`, and
  `_generator/` are tracked. Confirmed with `git check-ignore -v` and
  `git status` before staging — no document binary was ever staged.
  Commit `ae51680`.

## Each fix

### B-1 — Missing-field safety net (audit F-001)

**Problem:** one configured `REQUIRED_FIELD` rule for any field silently
disabled the default missing-field check for every other field of that
document type, at the validation engine
(`_has_required_field_rule`/`_handle_required_field`) and the service
layer (`services/document_validation.py::configured_document_rules`, via
`services/requirements.py::required_fields`).

**Files changed:**
- `apps/api/app/document_intelligence/validation/engine.py` — replaced
  the boolean suppress/don't-suppress gate with
  `_explicit_required_fields()` (new, computes the set of fields a
  configured `REQUIRED_FIELD` rule actually names); `validate_document`
  now runs the default net restricted to `EXPECTED_FIELDS[actual_type]`
  minus that set, instead of skipping it entirely;
  `_default_required_field_issues` gained a `restrict_to` parameter.
- `apps/api/app/services/requirements.py::required_fields` — changed from
  "explicit rules replace the default set" to "explicit rules add to the
  default set" (one-line change to the base-case initialization).
- `apps/api/app/services/document_validation.py::configured_document_rules` —
  changed from "skip auto-fill if any `REQUIRED_FIELD` rule exists" to
  "auto-fill every default field not already explicitly named".

**Tests:** `apps/api/tests/test_b1_required_field_additive.py` (new, 6
cases) — failing-then-passing confirmed directly (ran before the fix:
4/6 failed; after: 6/6 passed). Also updated, to match the corrected
behavior rather than the bug: `test_astra_consistency.py` (1 test
rewritten to assert the additive result, 1 fixture given its
previously-exempted default fields), `test_astra_document_state.py` (1
fixture repurposing-document-type fix, 1 duplicate-row fix),
`test_field_reviews.py` (`required=False` on its transcript test
checklist, matching the real seeded checklist, since these fixtures were
explicitly "focused" and relied on the old exemption; 4 business/SME
fixtures given their default fields), `test_submission_verification_api.py`
(4 fixtures given their default fields).

**Commit:** `1881e3a`. Full suite at that commit: 374 passed. ruff
check/format, mypy clean.

### B-2 — Validity and issue-date age vs. the submission's own date

**Problem:** `DATE_NOT_EXPIRED`, the always-on expiration check, and
`ISSUE_DATE_MAX_AGE` compared against `date.today()` (server local date,
no timezone) in three places in `validation/engine.py`
(`_always_on_expiration_issues` ~L196-233, `_handle_date_not_expired`
~L312-350, `_handle_issue_date_max_age` ~L352-393).

**Fix:**
- Found a usable stored date: `Submission.created_at`
  (`TimestampMixin`, `DateTime(timezone=True)`, set once at creation) —
  **no migration needed**.
- `apps/api/app/services/document_validation.py` — new
  `submission_reference_date(submission)`: converts `created_at` to
  Asia/Seoul via `zoneinfo.ZoneInfo`, treating a naive timestamp as UTC
  rather than guessing (SQLite does not strictly enforce
  `timezone=True`); returns `None`, never a guess, if there's no
  submission.
- `apps/api/app/document_intelligence/validation/engine.py` —
  `validate_document` gained `reference_date: date | None = None`,
  threaded through `_apply_configured_rule` into all three date-using
  functions. Every internal `date.today()` call removed. `None` →
  `REFERENCE_DATE_UNAVAILABLE` (`WARNING`), never a comparison.
- `services/document_validation.py::validate_effective_document` — the
  one production call site — now passes
  `submission_reference_date(submission)` through.

**Tests:** `apps/api/tests/test_b2_validity_reference_date.py` (new, 15
cases: UTC→KST conversion including a midnight-crossing timestamp, a
naive-timestamp guard, boundary dates for both the always-on and
configured expiry checks, a same-result-60-days-later check,
`ISSUE_DATE_MAX_AGE` boundaries, and the unknown-reference-date review
path for both checks) — 13/15 passed on first run against the already-
fixed code (the boundary/stability/unknown-date logic was correct on
first attempt); 2 failed only due to a test-construction bug
(`Submission.__new__` bypassing SQLAlchemy instrumentation), fixed in the
test itself, not production code. Five pre-existing tests
(`test_validation.py` ×3, `test_b1_required_field_additive.py` ×1,
`test_round2_real_document_fixes.py` ×1) exercised date comparisons
without a reference date and were updated to supply one explicitly.

**Commit:** `860171d`. Full suite: 408 passed. ruff check/format, mypy
clean (required one dict value-type annotation, `_RULE_HANDLERS: dict[RuleType, Callable[..., list[ValidationIssue]]]`,
once the handler signatures stopped being structurally identical).

### B-3 — Look-alike documents (audit F-003)

**Problem:** title signals in `classification/classifier.py` were plain
substring matches with no boundary check. `지방세납세증명서` contains
`납세증명서`, the national-tax `TITLE`-weight signal, so a local tax
certificate classified as `NATIONAL_TAX_PAYMENT_CERTIFICATE` at confidence
0.9 with `needs_review=False`.

**Fix:** `apps/api/app/document_intelligence/classification/classifier.py` —
one new table, `UNSUPPORTED_LOOK_ALIKE_TITLES` (3 entries, each commented
with which modeled type it looks like and why), checked at the top of
`classify()` before any scoring. Any match returns `UNKNOWN` with
`needs_review=True` unconditionally.

**Tests:** `apps/api/tests/test_b3_lookalike_classification.py` (new, 7
cases) — failing-then-passing confirmed (1/7 failed before the fix — only
지방세, since 휴학/졸업예정 did not trigger the bug by accident of the
existing signal set, confirmed directly rather than assumed; 7/7 passed
after).

**Commit:** `3378933`. Full suite: 391 passed. ruff check/format, mypy
clean.

### B-4 — Company-name legal-entity notation (audit F-002)

**Problem:** `comparable()` in `validation/engine.py` turned `주식회사 X`,
`(주)X`, `㈜X`, `X(주)` into four different comparison keys. This affected
two real paths: `ValidationEngine.validate_document`'s project-level
`COMPANY_NAME_MATCH`, and — the one the real seeded business checklist
actually uses — `validation/submission.py`'s `_field_comparison` /
`_comparison_key` for `FIELD_COMPARISON` rules comparing
`company_name`/`workplace_name` across documents.

**Fix:**
- `apps/api/app/document_intelligence/normalization/field_normalizer.py` —
  new `strip_legal_entity_markers()` + `LEGAL_ENTITY_MARKERS` tuple (주식회사,
  (주), ㈜, 유한회사, (유), 유한책임회사, 합자회사, 합명회사, 사단법인, (사),
  재단법인, (재), Co.,/Co., Ltd., Inc., Corp.). Strips a marker only as a
  whole token at the start or end, never from the middle.
- `validation/engine.py` — new `comparable_company_name()`, used only at
  the `COMPANY_NAME_MATCH` call site.
- `validation/submission.py` — `_field_comparison` strips markers from
  both sides before computing `_comparison_key`, only when `source_name`
  or `target_name` is in a new `_COMPANY_NAME_FIELDS = {"company_name",
  "workplace_name"}`. Every other field, including
  `business_registration_number`, is untouched.

**Tests:** `apps/api/tests/test_b4_company_name_notation.py` (new, 10
cases) — failing-then-passing confirmed (6/10 failed before the fix: all
4 submission-level notation variants plus 3 of 4 engine-level ones; the
guard and genuinely-different-company tests already passed, confirming
they weren't accidentally too strict; 10/10 passed after).

**Commit:** `271990d`. Full suite: 384 passed. ruff check/format, mypy
clean.

(Commit order on the branch is B-1 → B-4 → B-3 → B-2; each is independently
tested and independently green — order reflects implementation convenience,
not a dependency between fixes.)

## B0 vs B1 comparison and acceptance table

Full detail: `evaluation/phase_b/B0_variants.md`, `B1_variants.md`,
`B1_regression.md`.

| Criterion | Required | Result |
|---|---|---|
| False READY on variant sets | 0 in B0-fixed areas and 0 overall in B1 | **PASS** — 0 in both B0 and B1 |
| B07 digital, partial checklist | READY in B0 → REVIEW_REQUIRED in B1 | **INCONCLUSIVE on this input, both before and after** — the 4대보험 document in this set classifies `UNKNOWN` (a separate, out-of-scope extraction/classification gap already present in B0), which forces REVIEW_REQUIRED before the REQUIRED_FIELD-net path is reached either way. B0 was *already* REVIEW_REQUIRED, not READY, on this specific file — the manifest's predicted READY-in-B0 was not reproduced even before the fix. B-1 itself is proven by its dedicated, directly-failing-then-passing unit/service tests instead. |
| B02 digital | NEEDS_CORRECTION in B0 → READY in B1 (or per DECISION_1) | **INCONCLUSIVE on this input, both before and after**, same confound (the 4대보험 document, plus `company_name` not extracting from the 사업자등록증 in this set at all, so the comparison this fix targets never runs on this file). B-4 proven by its dedicated tests instead. |
| B11 digital | READY in B0 → NEEDS_CORRECTION in B1; the 지방세 file UNKNOWN | **PARTIAL PASS, and the deviation is explained, not hidden**: B0 was REVIEW_REQUIRED (not READY) for this submission even before the fix, same confound as above on this set's own 4대보험 document. But the 지방세 file's *own classification* is the direct, clean, real-pipeline signal, and it changed exactly as intended: `NATIONAL_TAX_PAYMENT_CERTIFICATE`/`MISMATCH` in B0 → `UNKNOWN`/`MATCH` in B1. Submission status stays REVIEW_REQUIRED in B1 too, which is the safe direction (correct abstention), not NEEDS_CORRECTION as the manifest predicted — explained in `B1_variants.md` §5. |
| S07 | both look-alikes UNKNOWN in B1 | **PASS** — both were already `UNKNOWN` in B0 (this pair didn't trigger the bug by accident of the prior signal set) and remain `UNKNOWN` in B1, now by explicit, documented design. |
| B06 | same result whatever day the harness runs | **PASS, directly confirmed** — `confirm_b2_day_stability.py`: the same document's per-document result is identical across three different server-clock dates (`stable_across_server_clock: true`); in Phase A's pre-fix A5 check, the same comparison *changed*. |
| B10 | still fails (F-004 is Phase C); unchanged is expected | **PASS** — unchanged, `REVIEW_REQUIRED` in both B0 and B1 (not confidently wrong, just not caught — F-004 untouched as instructed). |
| Every other set | no change from B0 unless explained by B-1…B-4 | **PASS** — every set's submission status is identical between B0 and B1 (see `B1_variants.md` §1 table); every difference is at the sub-submission level (classification for B11) and is explained above, not silent. |
| Real corpus (REAL-001..007) | CORRECT not lower, WRONG non-null not higher; False READY 0 | **PASS by code-path analysis, not re-measurement** — source folder no longer available (see `B1_regression.md`); B-1..B-4 touch no extraction code, and B-3's new check matches none of this corpus's genuine document types, so the field-level and classification scores cannot have changed. Stated as inferred, not measured. |
| Mentor synthetic set | classification not lower than baseline | **Still NOT REPRODUCIBLE** — source folder unavailable, unchanged from Phase A. No substitute used. |
| Quality gates | full backend suite green; ruff, format, mypy clean | **PASS** — 408 passed at the final commit (`860171d`); ruff check/format and mypy clean at every one of the four fix commits individually, not just at the end. |

## Surprises and open issues

- **The dominant confound carried over unchanged from B0 to B1, exactly as
  predicted**: the 4대보험 digital document misclassifying to `UNKNOWN`,
  and `company_name`/`representative_name`/`business_address` not
  extracting from several digital documents in this test-variant set.
  Neither is one of F-001/F-002/F-003/the validity-reference issue, and
  neither was touched. **Open issue for Phase C or later**: find out why
  (which label-matching assumption the rebuilt HTML-based templates don't
  satisfy), without assuming it's the same root cause as any audit
  finding.
- **B10 / F-004** (business-number check-digit validation) — explicitly
  deferred to a later phase, as instructed. Still `REVIEW_REQUIRED` (not
  confidently wrong), unchanged.
- **Real-corpus and mentor-set regression checks are inferred, not
  measured**, because their source folders are no longer present on this
  machine. This is the single biggest gap in this phase's own rigor,
  stated plainly rather than worked around. If the source documents become
  available again, re-running `run_round2.py` + `summarise.py` (real
  corpus) and a copy of `eval_phase5_mentor.py` with only its source path
  changed (mentor set, per the Phase A instruction on how to do this
  without editing the original) are the direct checks.
- **No digital "all valid" set (B01, S01, S10) reaches READY**, in either
  B0 or B1 — fully diagnosed in `B0_variants.md` §4 (two confounds, not
  three of the four Phase B bugs) and unchanged in B1 because neither
  confound was in scope.

## Exact commands to reproduce B0 and B1

```bash
# B0 (before any fix): git checkout the commit before B-1 (1881e3a^)
# B1 (after all four fixes): current branch tip

cd apps/api
./.venv312/bin/python ../../evaluation/phase_b/run_variants.py \
    --output ../../evaluation/phase_b/B{0,1}_variants_digital.json \
    --skip-ocr --skip-formats

# B-2 day-stability confirmation (either commit)
./.venv312/bin/python ../../evaluation/phase_b/confirm_b2_day_stability.py

# Full quality gates (run at every fix commit in this phase)
./.venv312/bin/python -m pytest -q
./.venv312/bin/ruff check .
./.venv312/bin/ruff format --check .
./.venv312/bin/mypy --explicit-package-bases app
```
