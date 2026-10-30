# ADVS on real scanned student certificates: test, fix, evaluate

Public report. It contains only counts, rates, field names and masked values. The documents, their crops, OCR text,
per-field values and screenshots are kept privately (git-ignored) and are not part of the repository.

- Frozen code under test: `45f1e3036c2fda8075e915f921bbc4203d76d8b1` (tag `real-docs-freeze-3`), branch `research/real-docs`.
- Baseline code: `main` at `101840661d91ccc9fab86774c969ea1edb1b6ce0`.
- Evaluation date for all runs: 2026-08-03 (the 90-day rule is inclusive: `age <= 90 days`; for an issue date of
  2026-07-29, 2026-10-27 is valid and 2026-10-28 gives `ISSUE_DATE_TOO_OLD`).
- OCR: PaddleOCR PP-OCRv5 Korean (traditional OCR only; no vision-language model, no LLM reader). Nothing was uploaded to any online service.
- Status of this report: seed B (held-out variants) is **done**. The fresh-capture test (3 newly issued certificates photographed with a phone, run once on the frozen commit and once on the baseline) is **done**: see section 9.

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

## 9. Fresh captures (test, run once on the frozen commit and once on the baseline)

### 9.1 Data and protocol

- Three certificates newly issued on 2026-10-30 to the owner (consent given): an enrolment certificate, a transcript on the 4.5 scale and a transcript on the 4.3 scale. Each was photographed once with an iPhone (G0, "as taken" and rotated upright). The test set was generated from those three photos with seed 20261030 (`manifest.json`, SHA-256 of all 80 files verified, none equal to the earlier originals): G1 flattened, G2 scan quality, G3 geometry, G3b rotation by 90 and 180 degrees (known limit, reported separately), G4 photo effects, G5 formats. The photos reached the generator at 2576x1449 px, so the flattened page is about 140 DPI effective (200 DPI for seed B).
- Gold values were drafted from the photos and **confirmed by the owner against the paper documents** (2026-10-30); the three internet issue numbers were re-checked against the full-resolution images. Scored fields: document type, `student_name`, `student_id` (transcripts; absent on the enrolment certificate), `university_name`, `department` (enrolment certificate only: the transcript has no department field), `issue_date`, `gpa`, `gpa_scale`. The printed 백분율 is not extracted (no such field) and is an observation only.
- Submissions: R45 = enrolment + transcript 4.5, R43 = enrolment + transcript 4.3, paired by group and recipe (54 pairs incl. the 2 iPhone-original pairs), 2 two-page PDFs, and every file alone for document-type results (81). 137 submissions per run. Inspection date 2026-11-02; expiry checks re-verified the G1 uploads on 2027-01-28 and 2027-01-29.
- Runs: the frozen commit `45f1e30` and the baseline `1018406`, each **once**, from clean checkouts, with the same inputs, live PaddleOCR, scratch database. No code was changed before or during the runs. Wall time 5,621 s (frozen) and 4,493 s (baseline). **Processing errors: 0** in both runs (no OCR_BUSY, no timeouts). Upload rejections: 7 per run, all in G0b (section 9.4).
- The variants (G1-G5) are correlated: they are 3 photographs. Intervals treat fields as independent and are optimistic.

### 9.2 Results per group, baseline then frozen

Fields correct = correct and auto-accepted + correct but sent to review + correctly absent. Wilson 95% in the brackets (percent range).

| group | subs | document type (files) | fields correct | auto-accepted | correct, to review | missing | wrong caught | wrong accepted | review fields / sub | false READY |
|---|---|---|---|---|---|---|---|---|---|---|
| **G0 real photos** baseline | 4 | 6/6 | 24/44 (54.5%, 40-68) | 0 | 20 | 20 | 0 | 0 | 10.00 | 0/4 |
| **G0 real photos** frozen | 4 | 6/6 | 25/44 (56.8%, 42-70) | 4 | 17 | 19 | 0 | 0 | 9.00 | 0/4 |
| G1 flat baseline | 4 | 5/6 | 22/44 (50.0%, 36-64) | 0 | 18 | 22 | 0 | 0 | 10.00 | 0/4 |
| G1 flat frozen | 4 | 5/6 | 22/44 (50.0%, 36-64) | 0 | 18 | 22 | 0 | 0 | 10.00 | 0/4 |
| G2 scan quality baseline | 12 | 17/18 | 78/132 (59.1%, 51-67) | 0 | 66 | 54 | 0 | 0 | 10.00 | 0/12 |
| G2 scan quality frozen | 12 | 17/18 | 82/132 (62.1%, 54-70) | 14 | 56 | 50 | 0 | 0 | 8.83 | 0/12 |
| G3 geometry baseline | 12 | 18/18 | 69/132 (52.3%, 44-61) | 0 | 57 | 61 | 2 | 0 | 10.00 | 0/12 |
| G3 geometry frozen | 12 | 18/18 | 69/132 (52.3%, 44-61) | 4 | 53 | 61 | 2 | 0 | 9.67 | 0/12 |
| G3b 90/180 degrees baseline | 4 | 4/6 | 15/44 (34.1%, 22-49) | 0 | 11 | 29 | 0 | 0 | 10.00 | 0/4 |
| G3b 90/180 degrees frozen | 4 | 4/6 | 17/44 (38.6%, 26-53) | 1 | 12 | 27 | 0 | 0 | 9.75 | 0/4 |
| G4 photo style baseline | 12 | 18/18 | 76/132 (57.6%, 49-66) | 0 | 64 | 54 | 2 | 0 | 10.00 | 0/12 |
| G4 photo style frozen | 12 | 18/18 | 79/132 (59.8%, 51-68) | 1 | 66 | 51 | 2 | 0 | 9.92 | 0/12 |
| G5 formats baseline | 6 | 6/6 | 30/44 (68.2%, 53-80) | 0 | 26 | 14 | 0 | 0 | 6.67 | 0/6 |
| G5 formats frozen | 6 | 6/6 | 30/44 (68.2%, 53-80) | 2 | 24 | 14 | 0 | 0 | 6.33 | 0/6 |

Totals:

| set | baseline | frozen |
|---|---|---|
| G0 (the three real photos, as taken and upright) | 24/44 (54.5%, 40-68) | 25/44 (56.8%, 42-70) |
| G1-G5 without G3b (computer-made variants of the 3 photos) | 275/484 (56.8%, 52-61) | 282/484 (58.3%, 54-63) |
| all scored groups with G0 and G3b | 314/572 (54.9%, 51-59) | 324/572 (56.6%, 53-61) |
| document type, all files alone (incl. G0, G3b) | 74/78 (94.9%, 88-98) | 74/78 (94.9%, 88-98) |
| wrong values auto-accepted | 0/0 (nothing auto-accepted) | **0/26** (rule of three upper 11.5%) |
| false READY | 0/54 (upper 5.6%) | 0/54 (upper 5.6%) |
| statuses | 54 of 54 pairs REVIEW_REQUIRED | 54 of 54 pairs REVIEW_REQUIRED |
| submissions flagged `CLASSIFICATION_REQUIRES_REVIEW` (52 pairs) | 50 | 10 |
| document processing time, p50 / p95 / max | 26.2 / 50.8 / 70.1 s | 34.0 / 72.2 / 84.7 s |

Reading of the numbers:

- **The frozen code is safe on the new documents: 0 wrong auto-accepts and 0 false READY.** Every pair ends REVIEW_REQUIRED; the system abstains rather than guesses.
- **The improvement over the baseline is small here**: +1 field on G0, +7 over G1-G5, but the fixes do remove most classification reviews (50 to 10 submissions) and allow 26 auto-accepts where the baseline allows none.
- **Accuracy is clearly lower than on seed B (84.5%)**: 56.8% on the real photos. The new photographs are lower in resolution (about 140 DPI effective) and are different documents, so seed B's result does not generalise to them. This is a negative result and is reported as it is: the two certificates of seeds A and B were also the documents the fixes were developed on.
- **Where the fields are lost (G0, frozen)**: both transcripts lose `student_name`, `student_id` and `issue_date` (the header row, 6 of 6 reads missing for each in G0), and the 4.5 transcript also loses `gpa` and `gpa_scale`; the enrolment certificate is read (name, university, department read correctly; `issue_date` missing on 2 of the 4 photo reads). No wrong value was read on G0.
- **Wrong caught (4, G3 and G4)**: a value was read incorrectly and was not accepted. No wrong value was ever accepted.

### 9.3 4.5 scale versus 4.3 scale transcript

| | 4.5 transcript | 4.3 transcript |
|---|---|---|
| `gpa` and `gpa_scale` read (pair submissions, frozen and baseline, 26 each) | 6/26, always correct | 18/26, always correct |
| auto-accepted | 0/26 | 0/26 |
| reasons the correct value went to review | no independent confirmation, second pass disagreed | near the decision boundary, confidence below floor, no independent confirmation |
| GPA rule (>= 3.0) | never evaluated (the value is not accepted, so it is unresolved, never a failure) | same |
| `GRADING_SCALE_MISMATCH` | appears as a review reason on 2 geometry variants of the 4.5 transcript, and as a field reason, not as a submission issue | not seen |
| printed 백분율 | printed (90.00 on both) but **not extracted** | same |

Observations (not scored): the printed legend is 4.3-based on both transcripts, but the 4.5 transcript states its GPA "/4.5" (the same inconsistency as in section 7). The cumulative GPA is 3.62/4.5 on one transcript and 3.40/4.3 on the other while the 백분율 is the same (90.00): 3.40/4.3 is not a proportional conversion of 3.62/4.5 (that would give about 3.46). This is why a threshold on the raw GPA is scale-blind (a design question for the next task, not decided here).

### 9.4 Upload of the original iPhone photos (G0b): frozen-version finding

The three original photos (4032x2268 px, EXIF orientation 1, GPS tag present, 2 frames) were uploaded as taken. **All 3 files were rejected as `CORRUPT_DOCUMENT` on both commits (7 upload attempts per commit: 4 in the two pairs, 3 alone)**, so no result exists for them.

- Cause: the photos are MPO files (a JPEG with a second embedded image, here a 210 KB gain map). `apps/api/app/services/storage/local.py:154-163` requires `img.format == "JPEG"` and a single frame; Pillow reports `MPO` with 2 frames, so the check raises `ValueError('Decoder format mismatch')`, mapped to `CORRUPT_DOCUMENT`.
- User-facing effect: the web message (`copy.ts:341`) tells the user the file may be damaged although it decodes without error. Any iPhone photo with an HDR gain map will be rejected the same way.
- Not caused by size, EXIF orientation or the decoder. Fixing it is the separate task `fix/phone-photo-upload`; its result will be reported as a separate "post-fix" row, not merged into the tables above.
- Both runs therefore tested the as-taken photos only in the downscaled form (2576x1449) that the generator received (G0).

### 9.5 Expiry checks (G1, 4 pairs)

Expected: 2027-01-28 (last valid day, issue + 90 days) valid; 2027-01-29 `ISSUE_DATE_TOO_OLD` and 보완 필요.
Actual (frozen and baseline, all 4 pairs): REVIEW_REQUIRED on the main date and on both expiry dates; `ISSUE_DATE_TOO_OLD` was **not** raised on 2027-01-29. The enrolment certificate's issue date was not auto-accepted (semantic inference, or not read), so the age rule has no reliable value to judge and the engine routes it to a person instead of failing it. This is the intended conservative behaviour (never a false failure and never a false pass) but the expected 보완 필요 for an expired certificate only appears after a person confirms the date. The boundary rule itself is covered by unit tests (inclusive, 90 days).

### 9.6 Other findings

- **Two-page PDFs (enrolment + transcript in one file), 2 files**: the system types the file as one document (TRANSCRIPT) and reports the enrolment certificate as missing: NEEDS_CORRECTION on both commits. This is a false 보완 필요 (the applicant did submit both) and it fails safe; splitting a multi-certificate PDF is not implemented.
- **G3b (90/180 degrees)**: 38.6% fields correct (baseline 34.1%), documents typed 4/6: the known rotation limitation.
- Document type: 74/78 files typed correctly on both commits; the 4 wrong are all enrolment certificates (G1 one, G2 one, G3b two): the same four files on both commits.

### 9.7 Gates

The code under test is unchanged since the freeze, so the gates of section 6 stand (they were run on `45f1e30`). Re-run in this session: web lint, typecheck and `vitest` **without cache**: passed, 109 tests (the web code is identical to the freeze: no difference in `apps/web` or `packages` between `45f1e30` and this branch).

### 9.8 For the paper

- Headline on real fresh photos (G0, frozen): 25/44 fields correct (56.8%, Wilson 42-70), 0 wrong auto-accepted, 0/4 false READY; 4 of 44 fields auto-accepted. All variants (G1-G5 without G3b): 282/484 (58.3%, Wilson 54-63), 0/21 wrong auto-accepted, 0/46 false READY.
- Safety held on documents the code had never seen (0 wrong auto-accepts, 0 false READY; baseline likewise). Accuracy did not transfer from the development documents: on seed B 84.5%, on fresh photos 56.8%.
- Automation is low: no submission reached READY; 9 review fields per pair on average. The system works as a safe pre-filter, not as an automatic decider on phone photographs.
- Limitations: three documents of one person; low-resolution photographs; header row of the transcripts not read; GPA on the 4.5 transcript mostly unread; no 백분율 extraction; rotation by 90 or 180 degrees; two-page PDFs not split; iPhone MPO photos rejected at upload (frozen version).

## 10. Reproducibility

- Code: `45f1e3036c2fda8075e915f921bbc4203d76d8b1`; baseline `main` `101840661d91ccc9fab86774c969ea1edb1b6ce0`.
- Variants: `evaluation/real_docs/make_variants.py` (seeds in the private `RECIPE.json`; seed B = 2002).
- Run: `cd apps/api && PYTHONPATH=. .venv312/bin/python ../../evaluation/real_docs/run_real.py --submissions <SUBMISSIONS.json> --eval-date 2026-08-03 --out <dir>` (scratch DB, live OCR).
- Score: `score_real.py` (originals), `score_variants_real.py` and `breakdown_variants_real.py` (variants).
- Fictional gates: `evaluation/real_docs/gate_corpus_v3.sh <label> <dev|holdout|holdout2|holdout3> <out>`.
- Determinism: the same files give bit-identical results across fresh processes and repeats in one process (20 runs checked earlier); seed A on the frozen commit reproduced the previous freeze with 0 differences.
- Statistics: Wilson 95% intervals; the rule of three when the count is 0.
