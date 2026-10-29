# ADVS on real scanned student certificates: test, fix, evaluate

Public report. It contains only counts, rates, field names and masked values. The documents, their crops, OCR text,
per-field values and screenshots are kept privately (git-ignored) and are not part of the repository.

- Frozen code under test: `45f1e3036c2fda8075e915f921bbc4203d76d8b1` (tag `real-docs-freeze-3`), branch `research/real-docs`.
- Baseline code: `main` at `101840661d91ccc9fab86774c969ea1edb1b6ce0`.
- Evaluation date for all runs: 2026-08-03 (the 90-day rule is inclusive: `age <= 90 days`; for an issue date of
  2026-07-29, 2026-10-27 is valid and 2026-10-28 gives `ISSUE_DATE_TOO_OLD`).
- OCR: PaddleOCR PP-OCRv5 Korean (traditional OCR only; no vision-language model, no LLM reader). Nothing was uploaded to any online service.
- Status of this report: seed B (held-out variants) is **done**. The fresh-capture test (new phone photographs and
  re-scans of the same two certificates) is **pending**: see section 9.

## 1. Data and consent

| item | value |
|---|---|
| originals | 2 documents of the owner's own (one enrolment certificate, one transcript), 200 DPI JPEG scans, 1 page each, image only |
| consent | the owner gave it for testing and for a paper |
| variants | 34 submissions per seed, built from the two originals by `make_variants.py` (scan quality, geometry, phone photo, format, negative cases) |
| seed A | development variants: used while fixing, so it is development data |
| seed B | seed 2002, generated and **never opened or run until the final run**: the test set |
| fresh captures | pending (section 9) |

Variants of the same two documents are strongly correlated: 34 submissions are not 34 independent documents. All
intervals below treat fields as independent and are therefore optimistic. Treat them as indicative, not as a claim
about the population of certificates.

Ground truth for the originals was confirmed field by field by the owner. Semester-row values were not confirmed
and are not scored.

## 2. Protocol

- Every field is scored as: correct and auto-accepted, correct but sent to review, missing, wrong but caught
  (not auto-accepted, flagged), wrong and auto-accepted (**the failure that matters**), deliberately edited and caught,
  or correctly absent.
- "Pass" means each field is either extracted correctly or correctly sent to review with a reason. A wrong auto-accepted
  value, or a wrong READY, is a failure.
- The acceptance policy was never loosened. No fix is specific to these documents; each has a synthetic unit test.
- Seed A guided the fixes. Seed B was run once, on the frozen commit, after all code was frozen. Hold-out 3 is development data since
  Phase G, so its run is a regression check, not a test.

## 3. Results on the two originals (development)

| | baseline (`main`) | frozen commit |
|---|---|---|
| fields correct | 7/11 (63.6%, Wilson 35-85%) | **11/11** (100%, Wilson 74-100%) |
| wrong values | 0 | 0 |
| wrong values auto-accepted | 0 | 0 |
| missing | 4 | 0 |
| documents typed correctly | 2/2 | 2/2 |
| submission status | REVIEW_REQUIRED | REVIEW_REQUIRED |
| processing time per document | 34.6 s and 9.6 s | 48.8 s and 12.7 s |

The status stays REVIEW_REQUIRED because every value is either under the confidence floor or lacks independent
confirmation (section 7). That is the intended behaviour, not a bug.

## 4. Results on variants

All counts are fields (362 per seed: 66 documents). "Correct" includes correct abstentions.

### 4.1 Seed A (development), before and after

| group | submissions | fields correct, baseline | fields correct, frozen |
|---|---|---|---|
| scan quality | 9 | 65/99 | 90/99 |
| geometry | 7 | 40/77 | 58/77 |
| phone photo | 6 | 32/66 | 38/66 |
| formats | 5 | 25/44 | 43/44 |
| negative | 7 | 48/76 | 73/76 |
| **all** | **34** | **210/362 (58.0%, Wilson 52.9-63.0)** | **302/362 (83.4%, Wilson 79.2-86.9)** |

Documents typed correctly: 58/66 to 61/66. Missing fields: 149 to 55. False READY: 0/34 both. Wrong auto-accepts: 0.

The baseline auto-accepts nothing (0 fields); the frozen code auto-accepts 28. Both are so low because the
policy requires independent confirmation that a single scanned document rarely provides.

### 4.2 Seed B (test, run once on the frozen commit)

| group | submissions | docs typed | fields correct | wrong | missing | auto-accepted | wrong auto-accepted | review fields / submission | false READY |
|---|---|---|---|---|---|---|---|---|---|
| scan quality | 9 | 17/18 | 91/99 | 0 | 8 | 10 | 0 | 8.89 | 0 |
| geometry | 7 | 12/14 | 57/77 | 1 | 19 | 2 | 0 | 9.71 | 0 |
| phone photo | 6 | 9/12 | 42/66 | 0 | 24 | 2 | 0 | 9.67 | 0 |
| formats | 5 | 8/8 | 43/44 | 1 | 0 | 4 | 0 | 7.20 | 0 |
| negative | 7 | 14/14 | 73/76 | 3 | 0 | 7 | 0 | 8.71 | 0 |
| **all** | **34** | **60/66** | **306/362 (84.5%, Wilson 80.4-87.9)** | 5 | 51 | 25 | **0** | 8.91 | **0** |

- **False READY: 0/34** (rule of three: upper bound 8.8%).
- **Wrong auto-accepted fields: 0/25** (rule of three: upper bound 12.0%).
- All 34 submissions ended REVIEW_REQUIRED; none was READY, none NEEDS_CORRECTION. All 68 documents finished processing (no OCR error).

Breakdown of the 362 seed B fields:

| outcome | seed A | seed B |
|---|---|---|
| correct and auto-accepted | 28 | 25 |
| correct but sent to review | 240 | 247 |
| missing (not read) | 55 | 51 |
| wrong but caught | 2 | 2 |
| deliberately edited, caught | 3 | 3 |
| correctly absent | 34 | 34 |
| wrong and auto-accepted | **0** | **0** |

(The 5 "wrong" in the group table are the 2 wrong-but-caught and 3 deliberately edited negative cases; none was accepted.)

Seed B behaves like seed A within sampling noise (306 vs 302 correct; 51 vs 55 missing). The fixes were not overfitted to seed A in
any way these data can show, but the two seeds come from the same two documents.

Reasons correct values were still sent to a person (seed B): confidence below floor 75, semantic inference (unlabelled date) 52,
no independent confirmation 35, no rule for the field 28, grading-scale mismatch 27, other 30.

Missing fields by cause (seed B): label or value not read 27 (student id 10, university 6, name 5, date 4, others), document not classified 24
(6 documents x 4 fields).

## 5. Failure analysis: cause, fix, effect

Each fix is general (no special case for these documents) and has a synthetic unit test.

| # | root cause on the real scans | fix | effect on the originals |
|---|---|---|---|
| 1 | the detector fuses stacked label first syllables into one tall box | split such a box into one box per cell, only when every cell has a label tail to its right | student name and number read on the transcript |
| 2 | a letter-spaced issuer row is read one glyph per box; nothing assembled the row | assemble the row as a fallback, anchored at row start, requires the university suffix, rejects sentence prefixes | university name read |
| 3 | stray low-confidence marks inside a letter-spaced title break the contiguous title | drop tiny, low-confidence, letterless boxes for classification and the title gate only | enrolment certificate classified |
| 4 | a certificate serial "No. ...-..." in the title band trips the title gate | serial numbers are no longer treated as foreign text before the title | transcript title accepted |
| 5 | overlapping boxes duplicate a glyph | drop a glyph repeated by horizontally overlapping boxes | clean issuer name |
| 6 | stray ASCII specks on glyph boxes | ignore them in the issuer row | clean issuer name |

Submission rules changed along the way:

- **Student number is required on at least one document of the submission** (it was required on the enrolment certificate,
  which does not print one). When both documents print it, they are compared.
- **University is compared between the enrolment certificate and the transcript** (a gap that predated this work: only
  student name and number were compared). An error needs both values reliable and still different after normalising
  spacing, title and generic affixes; a one-character difference, or any missing or unconfirmed side, gives review, never an error.

Research used for the detection fixes: the PaddleOCR PP-OCRv5 documentation (`paddleocr.ai`, PP-OCRv5 algorithm page) and the DB post-processing
parameter references returned by the search (the `db_postprocess.py` sources and a PaddleOCR discussion on text-box splitting/merging)
to see whether detection thresholds could separate the fused label. Our own probe (`det_probe.py`, varied thresholds and
unclip ratio) found no setting that does, so the fixes are post-OCR. These sources were consulted, not copied; the conclusion comes from our probe.

Fictional-set effect of the v3 dataset change: the one S09 digital case moves from REVIEW_REQUIRED to READY once the university comparison exists
(`V3_CHANGELOG.md`; v2 manifests and the scorer are untouched).

## 6. Safety gates (on exactly `45f1e30`)

| gate | result |
|---|---|
| backend tests, ruff, format, mypy | 656 passed, all clean |
| web `pnpm check` | passed (web tests served from cache; web code unchanged since the previous full run, which had 109 tests) |
| Playwright + axe | 22 passed, 7 skipped (they need real mentor PDFs) |
| `make demo-rehearsal` x3 consecutively | 3/3 ALL PASS (D9 46.9, 47.0, 46.8 s) |
| manipulated-PDF suite | 711/711 handled, 0 hidden tokens read |
| fictional injected cases (E1-E18), dev / hold-out 1 / 2 / 3 | 0/1354, 0/1532, 1/1518, 0/1527 false auto-accept |
| false READY under dataset v3 | 0 in all four corpora |
| field-level diff against the previous freeze | 0 on all four corpora (v2 and v3 views), real pair and seed A identical |
| privacy scan of the branch | 10 commits, one author, no AI trailers, no private paths, no tier-1 term; 75 lines in `holdout2/manifest_v3.json` contain a generic department string produced by the fictional generator (already in the v2 manifest on `main`) |

The one injected false auto-accept (hold-out 2, "H14") is a known residual of the cross-document agreement rule and
predates this work. Under dataset v2, S09 digital shows as a false READY purely because the frozen v2 scorer predates the
university comparison; under v3 it is expected READY and is correct. Hold-out 3 S09 digital stays REVIEW_REQUIRED because of an older extraction miss on
that fictional layout (conservative, not a false READY).

## 7. Limitations (known, not hidden)

- **Low automation on real scans.** Every submission in both seeds ended REVIEW_REQUIRED. Only 6.9% of seed B fields were auto-accepted; 8.9 review fields per submission. The system is
  safe here by abstaining, not useful as an automatic decider on single scanned certificates.
- **Missing fields remain**: 14.1% of seed B fields (phone photos and geometry variants are the worst: 24/66 and 19/77 missing).
- **90 and 180 degree rotation**: the orientation retry only triggers on low mean confidence or very few characters; rotated pages are partly lost.
- **Dropped label head**: when OCR drops the first syllable of a header label, the field is missed.
- **`GRADING_SCALE_MISMATCH`**: the document's own legend prints A+ = 4.3 while its GPAs are stated "/4.5"; the check flags it, which is correct
  behaviour on an inconsistent document, but it keeps the GPA in review. Accepted as a known limitation.
- **The printed GPA (3.62) does not match the recomputation from the semester table (about 3.65).** Cause unknown (the semester rows were never confirmed). Recomputation
  is not counted as confirmation unless it matches exactly.
- **Department is not compared**: the transcript has no `department` field, so there is nothing to compare it with.
- **The unlabelled issue date always goes to review** (semantic inference needs internal confirmation).
- **OCR worker**: Python cannot kill a hung native inference. The worker now waits a bounded time for its slot, recycles
  the executor and drops the cached engines, and the waiting call fails with `OCR_BUSY` (a processing error, never a verdict). The hung
  native thread stays alive until the process restarts. Found because one seed A run hung for over an hour inside a native call (not reproducible on the same input).
- **Two documents only.** Seeds A and B are variants of the same two certificates. Fresh captures are the only independent test (pending).
- Three older tracked tests contain a tier-2 string from before this work (the guard checks added lines only).
- The unlabelled intermittent rehearsal failure seen once earlier (a D9 classified UNKNOWN under load) was not reproduced in 20 repeated document runs and 6 further rehearsals; its root cause is unproven.

## 8. Processing time

Live PaddleOCR on CPU, one document at a time, per document including the second pass:

| set | documents | p50 | p95 | max |
|---|---|---|---|---|
| seed B | 68 | 33.6 s | 52.3 s | 92.6 s |
| originals | 2 | 12.7 s / 48.8 s | | |

Total seed B wall time 2077 s for 68 documents.

## 9. Fresh captures: PENDING

The owner will place new phone photographs and re-scans of the same two certificates in `~/Desktop/fresh/`. They will be run
**once** on the same frozen commit (`45f1e30`) and reported as a separate section here. Gold values are inherited from the originals. Nothing will be tuned on them.
This section has no results yet.

## 10. Reproducibility

- Code: `45f1e3036c2fda8075e915f921bbc4203d76d8b1`; baseline `main` `101840661d91ccc9fab86774c969ea1edb1b6ce0`.
- Variants: `evaluation/real_docs/make_variants.py` (seeds in the private `RECIPE.json`; seed B = 2002).
- Run: `cd apps/api && PYTHONPATH=. .venv312/bin/python ../../evaluation/real_docs/run_real.py --submissions <SUBMISSIONS.json> --eval-date 2026-08-03 --out <dir>` (scratch DB, live OCR).
- Score: `score_real.py` (originals), `score_variants_real.py` and `breakdown_variants_real.py` (variants).
- Fictional gates: `evaluation/real_docs/gate_corpus_v3.sh <label> <dev|holdout|holdout2|holdout3> <out>`.
- Determinism: the same files give bit-identical results across fresh processes and repeats in one process (20 runs checked earlier); seed A on the frozen commit reproduced the previous freeze with 0 differences.
- Statistics: Wilson 95% intervals; the rule of three when the count is 0.
