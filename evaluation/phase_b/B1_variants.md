# B1 — Variant Harness Results (after B-1 … B-4)

Same scope, same flags, same harness as B0 (`evaluation/phase_b/B0_variants.md`):
full digital pass (83 files, all 22 scenario sets), branch
`phase-b/safety-fixes` at this phase's final commit. Raw output:
`evaluation/phase_b/B1_variants_digital.json`.

## 1. Digital pass — expected vs actual, by set

Submission-level status is **unchanged from B0 for every set** — still
REVIEW_REQUIRED everywhere a confound applies. This is expected and
explained in §3/§4: the two confounds B0 identified (the 4대보험 document
misclassifying to UNKNOWN; company_name/representative_name/business_address
not extracting from several digital documents) are untouched by B-1..B-4
by design (out of this phase's scope), and they independently force
REVIEW_REQUIRED regardless of what the four fixes change underneath.

| Set | B0 actual | B1 actual | Changed? |
|---|---|---|---|
| B01 | REVIEW_REQUIRED | REVIEW_REQUIRED | No (confounded, as B0 documented) |
| B02 | REVIEW_REQUIRED | REVIEW_REQUIRED | No (confounded) |
| B03 | REVIEW_REQUIRED | REVIEW_REQUIRED | No (confounded) |
| B04 | NEEDS_CORRECTION | NEEDS_CORRECTION | No |
| B05 | NEEDS_CORRECTION | NEEDS_CORRECTION | No |
| B06 | REVIEW_REQUIRED | REVIEW_REQUIRED | No (confounded; date-stability confirmed separately, §3) |
| B07 default | REVIEW_REQUIRED | REVIEW_REQUIRED | No |
| B07 partial checklist | REVIEW_REQUIRED | REVIEW_REQUIRED | No (confounded, inconclusive both times) |
| B08 | REVIEW_REQUIRED | REVIEW_REQUIRED | No (confounded) |
| B09 | REVIEW_REQUIRED | REVIEW_REQUIRED | No |
| B10 | REVIEW_REQUIRED | REVIEW_REQUIRED | No (F-004 untouched, as instructed) |
| B11 | REVIEW_REQUIRED | REVIEW_REQUIRED | **Submission status unchanged, but the underlying classification changed -- see §3** |
| B12 | REVIEW_REQUIRED | REVIEW_REQUIRED | No |
| S01 | REVIEW_REQUIRED | REVIEW_REQUIRED | No (confounded) |
| S02 | REVIEW_REQUIRED | REVIEW_REQUIRED | No (confounded) |
| S03 | REVIEW_REQUIRED | REVIEW_REQUIRED | No (confounded) |
| S04 | REVIEW_REQUIRED | REVIEW_REQUIRED | No |
| S05 | REVIEW_REQUIRED | REVIEW_REQUIRED | No |
| S06 | REVIEW_REQUIRED | REVIEW_REQUIRED | No |
| S07 | REVIEW_REQUIRED | REVIEW_REQUIRED | No change needed -- both look-alikes were already UNKNOWN in B0 |
| S08 | REVIEW_REQUIRED | REVIEW_REQUIRED | No |
| S09 | REVIEW_REQUIRED | REVIEW_REQUIRED | No |
| S10 | REVIEW_REQUIRED | REVIEW_REQUIRED | No (confounded) |

## 2. False READY count

**0**, same as B0. No submission in any set or version returned READY when
expected was not READY, and none did in B0 either.

## 3. The four target bugs, after the fix, checked directly

- **B11 (F-003): fixed, confirmed end-to-end.**
  `B11-3_지방세납세증명서.pdf` now classifies as **`UNKNOWN`**, matching
  the manifest's `expected_classification` (`classification_comparison:
  MATCH`) -- in B0 this was `NATIONAL_TAX_PAYMENT_CERTIFICATE`
  (`MISMATCH`). This is a direct, real-pipeline confirmation of B-3, not
  just the unit tests. The *submission* status stays REVIEW_REQUIRED
  rather than becoming the manifest's predicted NEEDS_CORRECTION --
  explained in §5 (surprise): an `UNKNOWN` classification correctly
  triggers review (`UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW`), which is a
  *safer* outcome than the manifest assumed, not a weaker one. Correct
  abstention, not a confident wrong document type.
- **S07: still correct**, now by explicit design rather than accident --
  both look-alikes remain `UNKNOWN`/`MATCH`, unchanged from B0 (B0 already
  found this pair didn't trigger the bug; B-3's table now covers them
  explicitly regardless of future signal changes).
- **B02 (F-002) and B07 partial-checklist (F-001): still inconclusive on
  this specific input**, for the exact same reason B0 found -- the 4대보험
  document still classifies `UNKNOWN` in both sets (B-3's look-alike table
  doesn't apply to it; this is the *separate*, out-of-scope extraction/
  classification gap from B0 §4, untouched by this phase), which forces
  REVIEW_REQUIRED before the REQUIRED_FIELD-net or company-name-comparison
  logic is ever reached. **Both fixes are proven instead by their dedicated
  unit tests** (`test_b1_required_field_additive.py`, 6/6 passing;
  `test_b4_company_name_notation.py`, 10/10 passing) and are confirmed not
  to have regressed anything: ruff/mypy/the full 408-test backend suite are
  green at every commit.
- **B06 (validity-reference): fixed, confirmed by a dedicated check**
  (`evaluation/phase_b/confirm_b2_day_stability.py`,
  `B2_day_stability_confirmation.json`): the same B06 tax-certificate
  document's per-document status, read with the server clock mocked to
  2026-10-05, 2026-10-06, and 60 days later, is now **identical across all
  three** (`stable_across_server_clock: true`) -- in Phase A's A5 check
  (pre-fix, same document, same method), this exact comparison *changed*
  (`REVIEW_REQUIRED` → `NEEDS_CORRECTION`/`EXPIRED_DOCUMENT`). This is a
  clean, direct, apples-to-apples before/after result.

## 4. Surprises

No new surprises beyond what B0 already documented (the two confounds,
unchanged and untouched). One clarification worth stating plainly: B11's
submission status staying at REVIEW_REQUIRED rather than reaching the
manifest's predicted NEEDS_CORRECTION is **not** a fix shortfall -- an
`UNKNOWN`-classified document correctly can't also assert "this document
type's required check failed," because there is no required check for a
type the system declined to name. Review is the correct, safe terminus
here; the manifest's prediction assumed a different (also safe) path
through NEEDS_CORRECTION that this document doesn't reach because of the
other, separate classification confound on the same submission's 4대보험
document forcing review regardless.
