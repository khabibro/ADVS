# History audit — `721cc9d..f641fee`

## Commits in range

| Commit | Author | Date | Purpose | Production | Test | Evaluation | Notes |
|---|---|---|---|---|---|---|---|
| `fa38ef8` | KHABIBILLO <khabibillionaire@gmail.com> | 2026-10-02 22:52:05 +0900 | Harden OCR ingestion and processing reliability | yes | yes | no | Introduced the OCR worker slot, per-page OCR timeouts, and the resource budgets (`max_image_dimension`, `max_image_pixels`, `max_pdf_render_pixels`, `max_ocr_temp_bytes`, `ocr_timeout_seconds`). Also reworked preprocessing and the OCR provider. This is the commit that introduced the oversized-page-box rejection documented in `desktop_samples_results.md`. |
| `2326ed1` | KHABIBILLO <khabibillionaire@gmail.com> | 2026-10-02 22:52:24 +0900 | Strengthen extraction and verification safety | yes | yes | no | Label/candidate selection rework in the base extractor, field normalisation, document-scope validation engine, submission verification, evidence sufficiency policy, review/requirement services, and storage validation. Added `worker.py`, `consistency.py`, `document_validation.py`, `requirements.py`, `eval_lib/safety.py`, `recover_processing.py`. |
| `f641fee` | KHABIBILLO <khabibillionaire@gmail.com> | 2026-10-02 22:52:36 +0900 | Update document review contracts and UI integration | partly | yes | no | Contract and UI surface for reviews: `routes.py`, `schemas/api.py`, `openapi.json`, `packages/contracts/src/openapi.ts`, `ReviewSection.tsx`, `presentation.ts`, and the matching frontend tests. Production API surface plus generated contract, no new document intelligence. |

Totals for the range: **58 files changed, 3835 insertions, 323 deletions.**
History was not rewritten; all three commits are reachable from `origin/main`
and retain their original author and timestamps.

## Why the previously reported two red tests are no longer reproducible

The prior report claimed a historical failure of exactly two tests. That claim
was re-checked rather than accepted:

1. It was already recorded as not reproducible on a clean `721cc9d` checkout.
2. This run re-ran the full backend suite on the current tree: **350 passed,
   0 failed**, including the three regression tests added by this validation.
3. The most plausible explanation is that the claim described an **intermediate
   uncommitted working state** from earlier work rather than any committed
   revision. Nothing in the committed range `721cc9d..f641fee` reproduces it.

The claim is therefore recorded as **not reproducible on any committed
revision**, and is not treated as an open defect. It is not counted as a
regression baseline.

## Author note

`721cc9d` and `2228b75` are authored by `Munira <munira@knu.ac.kr>`; every
commit from `6a73d37` onward, including all three commits in this range, is
authored by `KHABIBILLO <khabibillionaire@gmail.com>`. This audit did not
alter authorship.

## Consequence for the denominator

Because `721cc9d` is the direct parent of the P0 range, it is a valid **PRE-P0**
reference. `evaluation/p0_backend/historical_comparison.md` re-ran that exact
revision against the same frozen gold with the same evaluator, so the PRE-P0 vs
POST-P0 comparison is apples-to-apples rather than a comparison against a
remembered number.