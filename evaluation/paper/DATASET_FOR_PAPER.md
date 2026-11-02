# Real-document evaluation set: paper fact sheet

Masked summary only. No certificate values, identities, or images are reproduced here. The final-results ledger is available at commit `431aaf1` and will be present on `main`; it is a later documentation commit than the `real-docs-v6` code tag, whose tree does not contain this file. Use the final paper and ledger together, and retain uncertainty notes where the ledger does not give a requested breakdown.

## 1. Student set

**Count and split.** Confirmed: 108 valid = seed A 27 + seed B 27 + fresh 54. Student development is fresh 54 + seed A 27 = 81; validation is seed B 27. Sources: `evaluation/paper/FINAL_RESULTS_2026-11-03.md` §opening; tagged `make_variants.py`; tagged `make_fresh_submissions.py`. Commands: `git show 431aaf1:evaluation/paper/FINAL_RESULTS_2026-11-03.md`; `git show real-docs-v6:evaluation/real_docs/make_variants.py`; masked counts from private submissions.

**Seed recipe (valid conditions).** The tagged `make_variants.py` defines 27 valid transformations applied to both source scans; it declares seeds A (development) and B (test). The available private seed-A `RECIPE.json` lists the same transformation families. Conditions and parameters:

- Scan quality (9): DPI 150; DPI 300; grayscale; Otsu binarization; JPEG quality 50, 70, or 90; Gaussian noise sigma 6; combined DPI 150 + grayscale + JPEG 70.
- Geometry (8): signed rotations of 1°, 2°, and 3° (sign is seed-selected); rotations 90° and 180°; shear factor 0.02; margin crop fraction 0.012.
- Phone-photo simulation (6): mild (perspective .015, lighting .25, defocus 3, cast .05); tilt (.03, .35, defocus 3, .08); shadow (.02, .55, defocus 3, .06); motion (.02, .30, motion strength 4, .05); defocus (.02, .30, defocus 7, .05); warm (.025, .40, defocus 3, .18). Each also uses JPEG quality 85.
- Formats (4): PDF, JPG, PNG, WEBP.

Sources: `evaluation/real_docs/make_variants.py` at `real-docs-v6`; `data/private_real/variants/seedA/RECIPE.json`. Commands: `git show real-docs-v6:evaluation/real_docs/make_variants.py`; `python3` JSON read of the private recipe (variant ids, group, and params only).

**Seed negatives.** Seven per seed, 14 total: edited issue date, edited GPA, inclusive expiry boundary, expired boundary, duplicate upload, hidden text, and identity mismatch. Final results group the student negatives as expired, wrong document in a required slot, missing document, or mismatched person; all 14 were never Ready. Sources: private seed A/B `SUBMISSIONS.json` files (condition labels/count only); final results §2; tagged `make_variants.py`. Command: masked Python count of submission IDs; `git show 431aaf1:evaluation/paper/FINAL_RESULTS_2026-11-03.md`.

**Fresh set.** Confirmed: 54 valid pair submissions, 27 per transcript scale. The G0b iPhone-original pairs are included: the private submission manifest has 2 G0b pairs within the 54. Per scale, the 27 conditions are G0 (2), G0b (1), G1 (2), G2 (6), G3 (6), G3b (2), G4 (6), and G5 (2). The builder also creates single-document diagnostic submissions, outside this 54-pair paper denominator. Sources: final results §opening; private `fresh/SUBMISSIONS.json`; tagged `make_fresh_submissions.py`. Command: masked Python counts by `kind` and `group`, no filenames or values printed.

Available manifest parameters (per transcript scale; crop pixels and flattening DPI vary by source page):

- G0: original as-taken photo and upright-rotated photo.
- G1: perspective-flattened page (effective DPI roughly 137–146) and flattened image-only PDF at the same DPI.
- G2: grayscale; adaptive binarization (block 31, C 12); JPEG quality 50 or 70; Gaussian noise sigma 8; downsample to 100 DPI.
- G3: rotations −3°, −1.5°, +1.5°, +3°; horizontal shear 3%; margin crop about 28–30 px.
- G3b: 90° and 180° rotations.
- G4: perspective strength .06; lighting gradient strength .35; motion blur kernel 5; defocus sigma 1.2; warm cast; seeded combined rotation/perspective/shadow/cast/blur.
- G5: JPEG quality 90 and WEBP. These are the final two conditions per scale.

Sources: `evaluation/real_docs/make_fresh_submissions.py` at tag; `data/private_real/fresh/manifest.json`; `data/private_real/fresh/README.md`. Commands: `git show real-docs-v6:evaluation/real_docs/make_fresh_submissions.py`; a Python JSON read selecting only `group` and `recipe` keys.

**Originals and resolution.** Seeds A/B are variants of 2 physical image-only scanned certificates (enrollment and transcript); each embedded image is 1653×2338 px, with a nominal 200-DPI source as described in the paper. Fresh uses 3 phone photos: enrollment and transcripts on 4.3 and 4.5 scales, received at 2576×1449 px. Exact issue dates are intentionally omitted. Seed transcript scale is **UNVERIFIED**. Sources: paper §4; `data/private_real/fresh/README.md`; private seed original PDFs (image dimensions only). Commands: masked PyMuPDF image-dimension read; `sed -n` of fresh README.

## 2. Business set

**Count.** Confirmed by paper Table 2 and final results §opening: 19 conditions × 4 single-file valid sets + 2 multi-page submissions = 78 total. Development has 38 valid submissions from company F21; validation has 38 from company RS. The 2 multi-page submissions are extra and never Ready.

**Conditions.** The private business manifest confirms these 19 valid condition recipes per each of 14 originals: G0 original as received; G1 200-DPI image-only PDF and PNG; G2 grayscale, adaptive binarization (31/C12), JPEG quality 50, Gaussian noise sigma 8, downsample to 150 DPI; G3 rotations ±2°, shear 3%, margin crop; G3b rotations 90°/180°; G4 perspective (.06), lighting gradient (.35), motion 5 + defocus .8, seeded combined photo effects; G5 WEBP. This is 1 + 2 + 5 + 4 + 2 + 4 + 1 = 19 conditions. Source: `data/private_real/business/manifest.json`; command: Python JSON read of only `group` and `recipe` fields.

**P1–P4 and multiplicity.** The manifest README says the sources cover 14 documents from two companies, but P1–P4's exact document combinations and company assignment must be verified against the masked submission structure; **UNVERIFIED** here. The rationale for four sets is also **UNVERIFIED**. Do not publish source filenames or company names. Source: `data/private_real/business/README.md`; command: `sed -n` read, with names suppressed from this fact sheet.

**Multi-page files.** There are 2 business multi-page PDFs, each combining 3 certificate pages. They are included in the total of 78; neither is Ready. The paper/results state their never-Ready outcome but do not give a more specific reason. Sources: private business manifest; paper Table 2 and §5.3; final results §opening. Command: masked manifest read of recipe descriptions and page counts.

**Negatives.** Classes: N1 expired national-tax certificate; N2 expired social-insurance certificate; N3 company mismatch; N4 local-tax look-alike in place of national-tax document; N5 duplicate upload; N6 old certificate. Final results states N1 (19/19) reached review, N6 reached expiry in 16/19, and N1–N4 and N6 had zero Ready. N5 is a duplicate notice and not a negative. The per-class submission counts for the paper’s 95 never-Ready total are **UNVERIFIED**; the final ledger’s broader 114-case lane does not map directly to that paper total. Sources: `data/private_real/business/README.md`; final results §§2, 6.

## 3. Table 2 fields

Paper Table 3 reports 300 student-photo + 760 student-scan + 232 business-photo + 672 business-scan + 8 other = 1,972 fields. These are pre-improvement OCR/extraction evaluation counts; the final-results ledger does not restate row denominators or define whether a file repeated across submissions is recounted. Unique-file versus submission counting remains **UNVERIFIED**. Source: paper §5.1, Table 3; final results does not independently report these fields.

## 4. “2,615 fields not accepted”

The paper §5.2 reports 2,615 fields not auto-accepted before improvements and gives five cause shares. The final-results ledger does not identify the submission set or code version for that denominator and does not repeat the shares. Its relationship to the 1,972 Table 3 count is **UNVERIFIED**; do not treat 2,615 as a complement of 1,972. Source: paper §5.2; final results §4 reports a different versioned category table.

## 5. Safety negatives / never-READY

Student: 14 negatives grouped as expired, wrong document in a required slot, missing document, or mismatched person; all were never Ready. Business: paper Table 2 reports 95 never-Ready; final results confirms N1–N4 and N6 had zero Ready and N5 is a duplicate notice, but does not independently report the 95 count. Sources: paper Table 2; final results §2.

## 6. Development versus validation

Confirmed split: students 81 development / 27 validation; business 38 development / 38 validation. The two multi-page business submissions are extra to the 76 single-file submissions; final results place them outside the per-company 38 valid single-file cohorts. Sources: final results §opening; paper Table 2 and §5.3.

## 7. Paper number discrepancies

Provenance distinction: the paper’s Table 2 counts 78 business submissions (76 single-file plus 2 multi-page) and 95 never-Ready. The broader final-results business lane reports 202 scored submissions and 114 N1–N6 cases. These are different populations; the final ledger does not map the paper’s 95 never-Ready cases to the broader lane. Student totals and the 81/27 split match the final ledger. Table 3 field rows and §5.2 denominator/shares are paper-reported but not independently stated in final results.

Sources: `evaluation/paper/PAPER_NUMBERS.md` at tag; command: `git show real-docs-v6:evaluation/paper/PAPER_NUMBERS.md`.

## Draft compact table: Real evaluation data

Counts below distinguish supported information from claims not verified against the requested final-results file.

| Measure | Students | Business |
|---|---:|---:|
| Originals | 2 scans + 3 phone photos | 14 files / 2 companies |
| Conditions | 27 per transcript scale; G0b included in 54 | 19 |
| Valid submissions | 27 + 27 + 54 = 108 | 19 × 4 + 2 = 78 |
| Never-READY | 14 negatives | 95 (paper Table 2; not separately stated in final ledger) |
| Dev / validation | 81 / 27 | 38 / 38 |

## Verification commands used

- `git tag --list 'real-docs-v6'`
- `git ls-tree -r --name-only real-docs-v6 | rg 'evaluation/paper|real_docs|data/private_real'`
- `git show real-docs-v6:evaluation/paper/PAPER_NUMBERS.md`
- `git show real-docs-v6:evaluation/real_docs/make_variants.py`
- `git show real-docs-v6:evaluation/real_docs/make_fresh_submissions.py`
- `git show 431aaf1:evaluation/paper/FINAL_RESULTS_2026-11-03.md`
- `python3` JSON reads restricted to private manifest `group`/`recipe` and recipe `id`/`group`/`params` keys
- `sed -n` reads of `data/private_real/fresh/README.md` and `data/private_real/business/README.md`
