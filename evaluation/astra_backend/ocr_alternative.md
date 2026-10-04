# Isolated local Korean OCR comparison

Experiment: ASTRA-OCR-ALT-01. OCR evaluation date: 2026-09-29. Frozen-gold scoring completed: 2026-09-30. This is a controlled provider/segmentation experiment, not the final hardened application's acceptance evaluation. No raw document, text, or field value is included here.

## Question and decision

Would a credible CPU-local alternative recover the difficult transcript and low-resolution stamped-document fields more safely than the existing Korean Paddle configuration?

On this three-document development subset, **no replacement is justified**. Tesseract recovered some fields missed by the starting Paddle pipeline, but yielded far fewer supported correct fields overall and one proven wrong populated value in each segmentation mode. Those wrong outputs also exposed unsafe behavior in the starting ADVS extractor. Retain the explicit Korean Paddle configuration, repair the demonstrated downstream defects, and evaluate a layout/table parser separately if a larger independent dataset justifies it. This is not a universal provider ranking.

## Reproducibility and privacy

Both cached Paddle observations and new Tesseract observations passed through the same immutable starting classifier, reading-order assembler, and extractor. Using the starting extractor intentionally isolates a provider change from the concurrent application repairs. The word-to-line Tesseract adapter groups TSV words by block/paragraph/line IDs, unions their boxes, and averages word confidence; this is a lossy line adapter, not a native table representation. Its average recognition confidence is not a correctness probability.

| Item | Recorded state |
|---|---|
| Starting Git commit | `721cc9dfa6ba9d0691ddb355ea62912ab3ea128a` |
| Starting worktree patch SHA-256 | `1ad21f2870369d75c3822d6bb80f10cd4c13463e151339777de0736a18e7101f` |
| Extractor snapshot tree SHA-256 | `2a381961cb2918462a13a98a36a7275cfe61ae396bcd494bc902ad676c16658b` |
| Dataset | `desktop-2026-09-29-v1`, subset ASTRA-R03/R04/R06 |
| Gold | `astra-gold-1.2`; SHA-256 `ebadf40f56600753529a4f7d783b41dd4472905965bd87247f7b3d5e9926c1a3` |
| Scorer | `astra-safety-1.1`; SHA-256 `91837a9a48f9d89f77bc8c5018c133659da10c7e1de4e1c273213e379aa5fc6c` |
| Existing runtime | Python 3.12.14; PaddleOCR 3.2.0; PaddlePaddle 3.1.1; PaddleX 3.2.1 |
| Existing Korean recognizer | `korean_PP-OCRv5_mobile_rec`; model and configuration hashes in the safe JSON |
| Alternative | Tesseract 5.5.2; OEM 1; Korean-only `tessdata_fast/kor.traineddata`; PSM 3 and PSM 6 |
| Alternative model SHA-256 | `6b85e11d9bbf07863b97b3523b1b112844c43e713df8b66418a081fd1060b3b2` |
| Model source | [Official Korean model](https://github.com/tesseract-ocr/tessdata_fast/blob/main/kor.traineddata) |
| Rendering | PyMuPDF 1.28.2, 250 DPI for the scanned PDF; image originals unchanged |

The model was downloaded into an isolated temporary directory. No production dependency was installed or changed. All OCR ran locally. Originals were not changed or copied into Git. Private TSVs, recognized text, evidence details, and rendered pages remain outside Git. [Safe JSON](ocr_alternative.safe.json) records every scored field without values, confusion matrices, provider/weight metadata, and timings.

The three chosen samples target pre-existing failures; they are not an independent holdout. No mode was selected retrospectively per sample. Other PSMs, the larger `tessdata_best` model, English-plus-Korean recognition, preprocessing, and language-specific fine-tuning were not tested. This comparison therefore evaluates these explicit configurations, not Tesseract's best attainable performance.

## Fixed-denominator results

There are 20 field assertions: 18 PRESENT and two AMBIGUOUS. Every populated field is accounted for; no unlabelled populated output occurred. Supported recall is correct PRESENT values / 18. Supported precision is supported correct values / all populated values, including populated ambiguous values in the denominator. An ambiguous value is not labelled incorrect without evidence, but is not credited as supported correct. Null on ambiguous gold is not credited as a correct absence. The subset has no ABSENT assertions; correct-abstention count is therefore zero for all three arms and does not measure negative-case skill.

| Metric | Cached Paddle + starting extractor | Tesseract PSM 3 + same extractor | Tesseract PSM 6 + same extractor |
|---|---:|---:|---:|
| Supported correct fields | 11 | 1 | 3 |
| All populated fields | 12 | 2 | 4 |
| Wrong non-null | 0 | 1 | 1 |
| Populated ambiguous | 1 | 0 | 0 |
| Unresolved PRESENT fields | 7 | 16 | 14 |
| Supported precision | 11/12 (91.7%) | 1/2 (50.0%) | 3/4 (75.0%) |
| Supported recall | 11/18 (61.1%) | 1/18 (5.6%) | 3/18 (16.7%) |
| Unresolved study-required fields | 4 | 9 | 9 |
| Correct classifications | 3/3 | 2/3 | 3/3 |
| Classification abstentions | 0/3 | 1/3 | 0/3 |
| Study-required document success | 1/3 | 0/3 | 0/3 |
| Populated fields with any evidence | 12/12 | 2/2 | 4/4 |
| Completed OCR/extraction attempts | 3/3 | 3/3 | 3/3 |

Evidence coverage above measures presence only; even wrong values had evidence. It does not measure correct association, readability, sufficient evidence, or eligibility for deterministic verification. Study-required fields are the frozen evaluation profile, not a declaration of every production workflow's requirements. Final review burden, evidence sufficiency, project verification, False READY, and false correction are **NOT EVALUATED** in this extraction-only replay. The stored per-field `needs_review` flags are historical extractor flags, not the final policy.

## Per-document and per-field observations

Counts below are correct / wrong / unresolved PRESENT, followed by ambiguous assertions. They cover all 20 assertions in each arm.

| Sample / family | Paddle | PSM 3 | PSM 6 |
|---|---|---|---|
| ASTRA-R03: transcript JPEG, 743×1020, dense table and watermark/seal | 2 / 0 / 3; 1 ambiguous populated | 0 / 1 / 4; 1 ambiguous null | 1 / 0 / 4; 1 ambiguous null |
| ASTRA-R04: scanned multi-column transcript, PDF page rendered 2067×2923 | 3 / 0 / 3; 1 ambiguous null | 0 / 0 / 6; 1 ambiguous null; classification UNKNOWN | 2 / 1 / 3; 1 ambiguous null |
| ASTRA-R06: stamped SME image, 400×566 | 6 / 0 / 1 | 1 / 0 / 6 | 0 / 0 / 7 |

Paddle correctly supplied ASTRA-R03 student ID/university, ASTRA-R04 GPA/scale/issue date, and ASTRA-R06 company/business number/certificate number/issue date/validity endpoints. PSM 3 supplied only ASTRA-R06 company correctly and contaminated ASTRA-R03 student ID. PSM 6 recovered ASTRA-R03 GPA and ASTRA-R04 student name/scale, but selected the wrong GPA scope for ASTRA-R04. Full field verdicts and confusion matrices are in the safe JSON. The ambiguous ASTRA-R03 surname is deliberately not counted as a proven recognition error under corrected gold.

## Trace of every wrong populated output

### ASTRA-R03 student ID, PSM 3

The original page, OCR TSV/line grouping, selected candidate, and stored evidence were inspected locally. The correct eight identifier digits occurred verbatim within the selected recognized row, but punctuation/border artifacts survived around them in the emitted value. The selected evidence was one broad header row. Its averaged word confidence was about 0.63, but the old extractor still marked the field as not needing review.

- Detection/segmentation: the row crossed label/value and nearby table-rule material. Exact detection accuracy cannot be quantified without box annotations.
- Recognition: the identifier digits were present, but extraneous rule-like punctuation was also recognized. Earliest observed corrupting stage: OCR_RECOGNITION, with OCR_SEGMENTATION contributing broad context.
- Candidate generation/pairing: the label was found and a candidate including the true digits was generated; `label_match` selected the contaminated string.
- Boundary/validation: `student_id` fell back to FREE_TEXT in the starting field-kind map; the surrounding artifacts were admitted. Normalization did not introduce the artifacts.
- Safety effect: wrong non-null identifier with evidence; not evidence that a final READY would pass because verification was not run.
- Defensible fix direction: preserve candidate boundaries and introduce conservative identifier-shape handling with abstention. Do not strip arbitrary characters until a known answer appears. Wider-row contamination and punctuation provide observable rejection signals.

### ASTRA-R04 overall GPA, PSM 6

The original page shows multiple semester-average rows and a separate cumulative summary in a multi-column layout. The selected evidence box maps to a semester GPA near the upper part of the middle course column, not the overall summary. Its numeric value was present in that recognized evidence. The expected overall value did not survive verbatim in the full alternative OCR text; this is evidence of recognition/segmentation loss as well, not proof that glyph recognition alone caused the wrong selection.

- Detection/layout: multi-column content and repeated GPA labels lost their table/section relationship. Earliest demonstrated semantic-scope loss: OCR_SEGMENTATION / TABLE_STRUCTURE.
- Recognition: a plausible semester value survived; the cumulative answer was unavailable in normalized OCR text.
- Candidate selection: the starting GPA helper used legacy first-label matching without field-aware ranking. The generic label `평점` permitted a semester row to supply the overall field. Normalization validly parsed the wrong semantic candidate.
- Evidence/policy: one existing evidence row, averaged confidence about 0.85, and a valid GPA number did not establish cumulative scope. The old extractor's flag did not request review.
- Safety effect: plausible wrong non-null GPA; a downstream GPA threshold could be wrong if it trusted this association. No such project verdict was evaluated here.
- Defensible fix direction: explicitly distinguish cumulative from term/course scope; require a supported cumulative label/cell relationship or abstain when repeated candidates remain ambiguous. Preserve optional table structure rather than adding sample-specific text corrections. Candidate disagreement, semester context, and cross-column geometry are existing warning signals.

These traces distinguish recognition from our own acceptance algorithms: changing the provider created different text/layout observations, but the starting extractor converted both uncertain situations into populated fields. A stronger OCR engine alone does not repair this class of error.

## Segmentation ablation and timings

PSM 3 uses automatic layout; PSM 6 treats the page as one uniform block. Both modes were run for every sample. PSM 6 produced more text on both transcripts and restored ASTRA-R04 classification, but also conflated semester/cumulative scope and lost the SME company's otherwise correct output. This is a rejected blanket configuration change, not evidence to pick the best mode after seeing gold.

| Sample | PSM 3 OCR wall time | PSM 6 OCR wall time | Render time |
|---|---:|---:|---:|
| ASTRA-R03 | 1.094 s | 2.234 s | Image original, no render |
| ASTRA-R04 | 2.199 s | 3.780 s | 0.272 s |
| ASTRA-R06 | 0.249 s | 0.241 s | Image original, no render |
| Median; range | 1.094 s; 0.249–2.199 s | 2.234 s; 0.241–3.780 s | One PDF observation |

These are single local subprocess observations, including process/model initialization, not production throughput. Paddle's cached full-processing durations include different stages and are not comparable pure OCR timings; no speed ratio is claimed. Peak memory, initialization in isolation, temporary-disk peak, and repeated-run variance were not measured in this experiment. Box/character counts in the safe artifact describe output granularity and volume, not detection accuracy or CER/WER. Full character-transcription and detection-box gold do not exist, so those accuracy measures are NOT EVALUATED.

## Failed trials and limitations

The isolated model directory initially lacked Tesseract's named TSV config; explicit `tessedit_create_tsv=1` corrected the runner. Leptonica also failed to open one rendered image through `/tmp`; canonicalizing to `/private/tmp` fixed that file-open trial. Neither setup failure was silently counted as successful OCR or folded into field accuracy. Their private diagnostic records were retained.

There is NO RELIABLE HOLDOUT POSSIBLE for this small reused set. The experiment did not install or run PP-Structure, Surya, docTR, EasyOCR, cloud providers, or a VLM. It did not measure stamp removal, dewarping, OCR orientation toggles, alternative DPI, or provider ensembling. These remain explicit untested alternatives, not implied successes. Any next parser experiment needs independently annotated layouts, competing-semester summaries, low-resolution identifiers, and negative/ambiguous cases; every newly populated value must retain evidence and be scored.
