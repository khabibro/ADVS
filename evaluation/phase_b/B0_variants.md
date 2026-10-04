# B0 — Variant Harness Results (before any Phase B fix)

Run via `evaluation/phase_b/run_variants.py` against the real FastAPI
service path (TestClient → upload → process → verify), ephemeral scratch
SQLite DB, branch `phase-b/safety-fixes`, clock fixed to the manifest's
`submission_date` (2026-10-05).

**Scope actually run for B0**, and why: the full **digital** pass (83
files, all 22 scenario sets — fast, no OCR, seconds total) plus **one
scanned spot-check** (B01, confirming the expected REVIEW_REQUIRED
pattern, 48.9s for 4 documents). The full scanned+images pass (216 files)
and the full format-set pass (92 files) were **not** run for B0 — at
~12s/document of real CPU OCR, that is 2+ hours, and the acceptance
criteria in this phase are about **digital-set** behavior specifically (the
README states plainly: "the bug-exposing scenarios only show their bug on
digital sets"; scanned/images are expected to uniformly land at
REVIEW_REQUIRED per audit F-010, which is already independently
established, not something this run needed to re-prove at full scale).
This is a scope-narrowing decision made for time, stated here rather than
silently; B1's regression pass should extend scanned/images coverage if
time allows.

Raw digital-pass output: `evaluation/phase_b/B0_variants_digital.json`.

## 1. Digital pass — expected vs actual, by set

| Set | Expected | Actual | Comparison |
|---|---|---|---|
| B01 all valid | READY | REVIEW_REQUIRED | MISMATCH — see §4 |
| B02 name notation | READY (same company) | REVIEW_REQUIRED | MISMATCH — confounded, see §4 |
| B03 different company | NEEDS_CORRECTION | REVIEW_REQUIRED | MISMATCH — confounded |
| B04 business-number off by one digit | NEEDS_CORRECTION | NEEDS_CORRECTION | **MATCH** |
| B05 expired | NEEDS_CORRECTION | NEEDS_CORRECTION | **MATCH** |
| B06 expiry on submission day | READY if inclusive — record actual | REVIEW_REQUIRED | RECORD — confounded; see §3 for the clean date-dependence result underneath |
| B07 validity missing, default checklist | REVIEW_REQUIRED | REVIEW_REQUIRED | **MATCH** |
| B07 validity missing, partial checklist | — | REVIEW_REQUIRED | inconclusive, see §3 |
| B08 missing reference doc | NEEDS_CORRECTION | REVIEW_REQUIRED | MISMATCH — confounded |
| B09 duplicate upload | record actual | REVIEW_REQUIRED | RECORD |
| B10 bad check digit | REVIEW_REQUIRED | REVIEW_REQUIRED | **MATCH** (F-004 untouched, as instructed) |
| B11 지방세 look-alike | NEEDS_CORRECTION | REVIEW_REQUIRED | MISMATCH overall, but classification itself is the clean signal — see §3 |
| B12 two reference docs | record actual | REVIEW_REQUIRED | RECORD |
| S01 all valid | READY | REVIEW_REQUIRED | MISMATCH — confounded |
| S02 issue date 120d old | NEEDS_CORRECTION | REVIEW_REQUIRED | MISMATCH — confounded |
| S03 GPA below threshold | NEEDS_CORRECTION | REVIEW_REQUIRED | MISMATCH — confounded |
| S04 GPA scale 4.3 | record actual | REVIEW_REQUIRED | RECORD |
| S05 name differs | record actual | REVIEW_REQUIRED | RECORD |
| S06 department differs | record actual | REVIEW_REQUIRED | RECORD |
| S07 휴학/졸업예정 look-alikes | NEEDS_CORRECTION | REVIEW_REQUIRED | MISMATCH overall, but **classification itself already matches** (both UNKNOWN) — see §3 |
| S08 issue date blank | REVIEW_REQUIRED | REVIEW_REQUIRED | **MATCH** |
| S09 no student number | REVIEW_REQUIRED | REVIEW_REQUIRED | **MATCH** |
| S10 table-style transcript | READY | REVIEW_REQUIRED | MISMATCH — confounded |

## 2. False READY count

**0.** No submission, in any set or version run, returned READY when the
manifest's expectation was not READY. (Several sets went the *other*
direction — expected READY, actual REVIEW_REQUIRED — which is the
conservative/safe direction, not a false READY.)

## 3. The four target bugs, checked directly (not just via submission status)

Submission-level status alone is not a clean signal for several of these
sets because of confounds found in §4 — so each bug was also checked at
the most specific level that actually isolates it.

- **B02 (F-002, company-name notation):** the submission lands at
  REVIEW_REQUIRED regardless (confound: the 4대보험 document misclassifies
  to UNKNOWN independently — see §4), so the submission status cannot show
  this bug cleanly on B0. The underlying mechanism (`comparable()` in
  `validation/engine.py`) was already confirmed broken by direct unit
  testing in the system audit (F-002) and is unchanged at this commit;
  fixed in B-4, verified by dedicated unit tests, not solely by this
  harness run.
- **B07 under the partial checklist (F-001):** **inconclusive on this
  input.** Both the default and the partial-checklist run return
  REVIEW_REQUIRED, for the *same* reason in both cases
  (`UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW` from the misclassified
  4대보험 document) — the specific REQUIRED_FIELD-suppression path B-1
  targets was never reached by either run, so this file cannot distinguish
  "fixed" from "still broken" at the submission-status level. The
  underlying mechanism was already confirmed broken by direct
  engine/service-layer testing in the system audit and in Phase A's A5
  check (same confound, same conclusion there); B-1 is verified primarily
  by unit tests, with this harness re-run in B1 to confirm status.
- **B11 (F-003, 지방세 look-alike):** **clean, direct confirmation.**
  `B11-3_지방세납세증명서.pdf` classifies as `NATIONAL_TAX_PAYMENT_CERTIFICATE`
  (should be `UNKNOWN` per the manifest) — `classification_comparison:
  MISMATCH`. This is independent of the submission-status confounds and
  directly reproduces audit finding F-003 on a real, rendered document
  (not just a hand-written text probe).
- **S07 (look-alikes, 휴학/졸업예정):** **already correct, not broken.**
  Both `휴학증명서` and `졸업예정증명서` classify as `UNKNOWN` already —
  `classification_comparison: MATCH` for both, on B0, before any fix. This
  is explainable, not a contradiction: unlike 지방세납세증명서 (which
  contains "납세증명서" as a trailing substring of the national-tax TITLE
  signal), neither "휴학증명서" nor "졸업예정증명서" contains "재학증명서"
  or "졸업증명서" as a substring, so the classifier's existing
  strong-signal floor already abstains correctly for this pair. B-3 still
  implements the general look-alike mechanism DECISION_2 asks for, which
  keeps this pair correct **by explicit design** rather than by accident
  of the current signal set — not "fixing" S07 so much as making its
  already-correct result robust to future signal changes.
- **B06 (validity vs. submission date):** **clean, direct confirmation**
  of day-dependence, already measured in Phase A's A5 (same documents,
  same finding): submission-level status changes between evaluation dates
  2026-10-05 and 2026-10-06 (`REVIEW_REQUIRED` → `NEEDS_CORRECTION` with
  `EXPIRED_DOCUMENT`), and the per-document `ValidationEngine` path shows
  the same pattern via the server clock. B0's digital-pass run above used
  2026-10-05 only; the day-dependence itself was already established in
  Phase A and is re-verified as part of B-2's own tests.

## 4. Surprises

**The dominant pattern:** nearly every digital "should be READY or a
specific NEEDS_CORRECTION" set instead lands at `REVIEW_REQUIRED`, for one
or both of two reasons that are **not** among B-1..B-4's targets:

1. **The digital 4대사회보험료완납증명서 document classifies as `UNKNOWN`
   in every set that includes it** (B01, B02, B06, B07, B11, and by
   extension any business set using this layout) — confirmed by direct
   inspection of the per-file classification result, not inferred. This
   single confound alone is enough to force `REVIEW_REQUIRED` via
   `UNCLASSIFIED_DOCUMENT_REQUIRES_REVIEW`, independent of anything B-1..B-4
   touch. **Not investigated further or fixed here** — out of this phase's
   scope (not one of F-001/F-002/F-003/validity-reference), flagged for
   Phase C.
2. **`company_name`, `representative_name`, and `business_address` do not
   extract at all from `B01-1_사업자등록증.pdf`** (confirmed by reading the
   raw `extracted_fields` response directly: `raw_value: null,
   normalized_value: null, needs_review: true` for all three, even though
   the classifier's own evidence list shows the labels "대표자" and "사업장
   소재지" are present in the document's text). `business_registration_number`
   and `business_type`/`business_item` **do** extract correctly from the
   same file via the same `embedded_pdf_text` source, so this is not a
   wholesale text-layer failure — specific label/value associations are
   failing for specific fields on this rebuilt-HTML-template document.
   Each unresolved required field independently triggers
   `REQUIRED_FIELD_UNRESOLVED`, which alone would keep the submission at
   `REVIEW_REQUIRED` even if the classification confound (above) were
   fixed. **Not investigated further or fixed here** — not one of the four
   target defects; flagged for Phase C.
3. A semantically-inferred `issue_date` (extraction_method
   `document_semantic_issue_date`) is read correctly but never reaches an
   effective value, because the evidence-sufficiency policy's
   `SEMANTIC_INFERENCE` reason routes it to review unconditionally — this
   is the policy working exactly as designed (audit F-010, explicitly
   out of scope to change per this phase's hard constraints), not a bug,
   but it compounds with #2 to keep every business set at
   `REVIEW_REQUIRED`.

**Net effect:** the B0 digital pass, on its own, is not a clean before/after
instrument for B02 and B07 at the submission-status level, because of
confounds #1 and #2 above, present before any Phase B code is touched.
B06 and B11 are unaffected by this and remain clean, direct evidence. §3
above states exactly how each of the four bugs was actually verified given
this.

No evidence policy, extraction logic, or production code was changed to
investigate or work around any of this — per instruction.
