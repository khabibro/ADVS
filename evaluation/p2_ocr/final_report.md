# P2 Final Report

## A. Executive Verdict
**P2_FAIL.** The baseline was reproduced, but the observation-level annotation needed to separate detection from recognition was not available, no candidate OCR change could be ranked on correctness, and no OCR change was justified. No production code was changed. **PHASE_9_READINESS: NO.** This is an evidence-completeness verdict, not a claim that PaddleOCR is inherently inadequate.

## B. Repository State
Starting and ending HEAD: `48e3824a780e3c051cba2d2eb1838851db1fcf1e`; branch `main`; `origin/main` matched at start. No commit or push was made. Initial tracked diff was empty. P1 artifacts and unrelated pre-existing untracked evaluation files were retained.

## C. P1 Closure
P1 production-path outcomes were reproduced on the current real OCR stack: 16 correct, 1 incorrect non-null, 17 unresolved, 7 not evaluated, field recall 0.4706, False READY 0/7. The earlier 0.471 is unchanged when rounded. No historical P0/P1 gold or score was overwritten.

## D. Structural Layer Decision
See [structural_layer_decision.md](../p1_layout/structural_layer_decision.md). Generic geometry primitives remain inert (`KEEP_DORMANT`); unsafe candidate-generation adapters are classified `REMOVE` from production, while retained artifacts are not deleted. P1 tests are `TEST_ONLY`; benchmark artifacts are `EVALUATION_ONLY`. No structural method was activated. The layer has no authoritative production consumer and must not turn speculative layout candidates into fields.

## E. GPA Gold Review
See [gpa_gold_review.md](../p1_layout/gpa_gold_review.md). One transcript’s GPA is `AMBIGUOUS`; the other’s visible cumulative summary supports `KNOWN_VALUE`. The “first reading-order GPA is overall” assumption is unjustified for the ambiguous page. Frozen gold v1 remains unchanged; an ignored runtime gold v2 was versioned and hashed. On v2, the unchanged run scores 16 correct, 1 incorrect, 16 unresolved, 8 not evaluated, recall 0.4848, False READY 0. The recall change is a denominator/semantic-gold change, not OCR improvement. The frozen scorer also checks null before `VERIFIED_ABSENT`, so two absent values are labeled unresolved; that historical scorer behavior was not changed.

## F. Dataset Integrity
Seven private originals were fingerprinted before and after with SHA-256, size, and mtime; all remained unchanged. The manifest has seven safe IDs and seven unique hashes, no filenames or private text ([manifest](dataset_manifest.json)). Original dataset hash inventory is recorded in ignored runtime state only.

## G. P2 Baseline
Python 3.12.14; PaddlePaddle 3.1.1; PaddleOCR 3.2.0; PaddleX 3.2.1; CPU. Fresh OCR completed for 7 documents/7 pages, 650 observations with bounding boxes, and exactly reproduced cached P1 page and line text 7/7. This demonstrates reproducibility, not correctness. Baseline details are in [baseline_state.md](baseline_state.md) and [observation_baseline.json](observation_baseline.json).

## H. Pipeline Definition
Visible source → PDF/image normalization and rendering → text detection → recognition → preserved OCR observations → structure → candidate generation → field resolution → evidence policy → verification. Current real OCR and production HTTP replay are measured; box-level visible-text annotation is not. The evidence supports exact localization only at alias/text comparison and candidate diagnosis levels, not a detection-versus-recognition split.

## I. Observation-Level Ground Truth
The 17 unresolved fields were manually checked for label/value visibility and compared with OCR text. Counts: 12 visible applicable labels, 5 label-not-applicable; 14 visible expected values, 1 ambiguous/partial, 2 value-not-applicable. Four expected aliases appeared in observations; one further visible synonym was read but is absent from the extractor alias set. Eleven of 14 expected visible values had exact normalized OCR text. These are text-presence counts, not detection or recognition rates. Per-field safe traces: [field_pipeline_trace.json](field_pipeline_trace.json). No independently reviewed box-level gold exists; formal detection and recognition rates remain unscored.

## J. Missing-Label Reproduction
The reported 8/17 is independently reproduced only as “expected extractor label alias absent from OCR text.” Of these, one field has no applicable label on the source and one has a visible, OCR-readable synonym outside the alias set. Therefore seven visible labels lack their expected alias observation. Each has no demonstrated box-level hit/miss judgment, so zero can honestly be called a confirmed detection failure or confirmed recognition failure. The 7/17 visible-label misses remain unseparated. No unnecessary label/value text is reproduced here.

## K. Failure Taxonomy
Measured unresolved-field diagnosis: 8 expected alias absent (including one absent source label and one alias-vocabulary issue); 3 adjacent-column contamination; 2 shape-rejected candidates; 1 association issue; 1 ranked-path versus production-path mismatch; 1 untraced. These categories describe candidate/extractor diagnosis and are not mutually exclusive root-cause counts for OCR. See [failure_taxonomy.md](failure_taxonomy.md). Root causes such as border interference, contrast, stamp overlap, and glyph class remain unverified.

## L. Rendering Audit
Dataset includes PDF page sizes of 1117×1408 pt and 595.08×841.68 pt plus source images from 400×566 to 1200×1854 px; source DPI was not consistently determinable. Current configuration uses resolution-aware rendering with nominal 288 DPI, scale clamp 1.5–6, image dimension cap 16000, 25M image pixels, and 250M total PDF raster pixels. Three PDF pages were compared at 200/288/300 DPI. Page text matched the 288-DPI reference on 0/3, 3/3, and 1/3 pages respectively; line counts and timings varied. No variant has annotated correctness, so 288 remains baseline for reproducibility/resource policy, not proven optimal accuracy. No evidence supports removing the P0 resource protections.

## M. Preprocessing Benchmark
Grayscale, contrast, sharpening, thresholding, denoise, and upscaling were not benchmarked: no measured box-level error category justified choosing them, and no observation gold would establish benefit versus damage. No preprocessing improvement is claimed.

## N. Detection Analysis
All 650 OCR observations have boxes, but that does not establish recall. No box-level text regions were annotated, so detection recall and fragmentation/merge rates are unscored. Confirmed detection failures: 0; this means none confirmed, not none present.

## O. Recognition Analysis
Text agreement with the frozen OCR cache is 7/7 pages and 7/7 line sets. On unresolved expected visible values, exact normalized text appears for 11/14. Because a missed string could be detection, recognition, or annotation/normalization, recognition accuracy is not inferable. See [recognition_error_analysis.md](recognition_error_analysis.md) and [detection_error_analysis.md](detection_error_analysis.md).

## P. Korean Recognition Errors
The known wrong non-null personal-name field demonstrates a high-confidence Korean recognition/extraction error (confidence 0.9166); it remains review-required and was not used to claim automatic correctness. No private correction dictionary or token-level private text analysis was created. Character-substitution, spacing, digit, punctuation, and mixed-script error frequencies remain unmeasured.

## Q. Current OCR Configuration
Authoritative provider is PaddleOCR, Korean, `PP-OCRv5_mobile_det` plus `korean_PP-OCRv5_mobile_rec`, CPU. No explicit detector/recognizer threshold override, batch override, or fixed CPU-thread override was found. PDF nominal render DPI 288; textline orientation disabled; document orientation is conditional on retry; worker timeout 120 s; max pages 30. Image, pixel, and temp-byte limits are listed in baseline state. Numeric Paddle defaults are not pinned in ADVS settings, a reproducibility limitation.

## R. Primary-Source Research
**Documented facts:** official PaddleOCR docs list the Korean/English PP-OCRv5 mobile recognizer as `korean_PP-OCRv5_mobile_rec` (14 MB; vendor-reported benchmark is not an ADVS result); official recognition docs describe module configuration; official PP-OCRv6 discussion does not establish Korean recognition support. Sources: [PP-OCRv5 multilingual models](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.en.md), [text recognition module](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/module_usage/text_recognition.en.md), [PP-OCRv6 Korean discussion](https://github.com/PaddlePaddle/PaddleOCR/discussions/18249), [official OCRv3 Korean config](https://github.com/PaddlePaddle/PaddleOCR/blob/main/configs/rec/PP-OCRv3/multi_language/korean_PP-OCRv3_mobile_rec.yml).

**Measured result:** current cached models run on CPU in this environment. **Inference:** without box-gold and correctness scoring, the research does not justify a newer detector, server model, or recognizer swap. No official evidence was found that would support assuming newer means Korean-capable or better for these documents. CLOVA was not contacted and no private documents were uploaded.

## S. OCR Candidates
Current baseline was run. 200/288/300 DPI render variants were run on three PDFs with real OCR but correctness unscored. Grayscale/contrast/upscale and alternative detector/recognizer candidates were not run. A stronger official Korean server recognizer candidate was not established. Cloud OCR was not used. Full candidate table: [ocr_benchmark_results.json](ocr_benchmark_results.json).

## T. Benchmark Protocol
Baseline uses identical seven originals, real PaddleOCR, unchanged gold/evaluator, and the production upload/process/retrieve/reprocess path. DPI comparison used the same three PDF inputs and local CPU. Alternative OCR configurations were not evaluated, so this is not a completed candidate bake-off.

## U. Benchmark Results
Current OCR: 650 lines/boxes; label/value detection and recognition rates unscored. Field results: 16 correct, 1 incorrect non-null, 17 unresolved, 7 not evaluated, 0 hallucinated, precision 0.9412, v1 recall 0.4706, False READY 0/7. The alternative render runs cannot be ranked by correctness.

## V. Selected Configuration
Retain the current 288-DPI resolution-aware renderer and cached Korean PP-OCRv5 mobile models as the **unchanged baseline**, not as a demonstrated best OCR architecture. It is the only fully reproduced production candidate and alternatives lack observation truth. No production integration/change is warranted.

## W. Observation-Level Improvement
No justified observation-level improvement was established: expected-label aliases 4/12, plus one visible synonym; exact OCR text for expected values 11/14. Before/after improvement is zero/unknown; detection and recognition metrics are unscored.

## X. Field-Level Improvement
Frozen gold v1: recall 0.4706 → 0.4706; correct 16 → 16; unresolved 17 → 17. No OCR or production code change. Versioned semantic gold v2 separately scores recall 0.4848 because of two GPA gold decisions, not OCR.

## Y. Wrong Non-Null Analysis
One wrong non-null remains before/after. It is the known high-confidence name error, and the production status remains review-required. No wrong-value rate increase or safety weakening occurred; no claim of correctness from confidence is made.

## Z. Evidence Integrity
No private OCR text, values, screenshots, or source filenames were written to tracked P2 artifacts. Observations were compared using safe IDs and booleans/counts. Raw OCR and field values stayed in ignored runtime files. Existing untracked P1 artifacts are retained; review them before any future staging.

## AA. Confidence Analysis
No confidence threshold was tuned. Confidence 0.9166 accompanies the known wrong name and is direct counter-evidence to treating OCR confidence as truth. Calibration bins cannot be meaningfully estimated from one wrong field and no box-level observation gold.

## AB. Structural Layer Re-Evaluation
Not run as an old-vs-improved OCR comparison because no improved OCR configuration was selected. P1’s unchanged structural benchmark remains the only evidence; no structure was modified or activated. See P1 decision document.

## AC. Transcript GPA
No GPA candidate was forcibly resolved. The ambiguous transcript stays ambiguous; the second transcript’s cumulative summary is the v2 known-value target. Frozen v1 remains immutable. Improved-OCR GPA reevaluation was inapplicable because no improved OCR was selected.

## AD. False READY
Real production-path result 0/7. Existing adversarial test suite passed as part of repository tests, but the requested independent live scenario matrix (wrong number, expiry, unknown, stale review, conflicts, concurrency races, etc.) was not re-run end-to-end in this task. No expanded matrix denominator is claimed.

## AE. Human Review
All seven real documents ended `REVIEW_REQUIRED` (7/7 review burden). Review remains the safety outcome; no UI or evidence policy was changed.

## AF. Multi-Page
P2 production documents are all one page. The local real-provider 1/3/6-page probe reached its first (1-page) test call but was interrupted when that call did not return within the probe window. No output for any individual page-count case was emitted, so no multipage pass is claimed. This does not substitute for authoritative API workflow tests, queue timing, memory, or resource-budget checks.

## AG. Concurrency
The same probe attempted two distinct documents concurrently through the provider, but emitted no per-call output before the subsequent 1-page call stalled and was interrupted. Thus completion/outcomes are inconclusive; it is not a same-project/different-project authoritative API race test. No concurrency safety pass is claimed.

## AH. Reprocessing
Production HTTP replay completed process/readback/reprocess for 7/7. Field results/readback stable 7/7 and no duplicate rows 7/7.

## AI. UNKNOWN / Out-of-Scope
No new unrelated-document UNKNOWN/security integration matrix was run. Existing repository tests passed. No filename-based classification changes or shortcut were introduced; no production code changed.

## AJ. Performance
Fresh page OCR median 12.716 s, maximum 39.331 s. Full one-page production first-process median 12.275 s, maximum 39.903 s; first-process aggregate 128.632 s; harness with reprocessing 256.4 s. No valid 3/6-page API latency, queue wait, or memory result is claimed.

## AK. Security / Privacy
Private originals read-only and fingerprint-verified unchanged before/after. No cloud provider or external LLM/VLM received documents. Private gold/raw OCR stayed ignored outside tracked artifacts. No dependencies were added.

## AL. Overfitting Audit
No sample names, private organizations, identifiers, dates, filenames, OCR strings, coordinates, or expected values were introduced into production code; no production code changed. Evaluation uses safe IDs.

## AM. Quality Gates
PASS: `make check` (368 backend tests; frontend lint/typecheck/tests, 94 frontend tests), `ruff format --check .`, P2 helper `ruff check`, P2 JSON parse, `make migration-check`, `make docker-check`, `pnpm build`, `pnpm env:validate`, `pnpm security:audit`, and `git diff --check`. Docker image build passed on the approved escalated retry after sandbox host-path denial. Whitespace scan found no trailing whitespace in P2 artifacts or P1 decision documents.

## AN. Files Changed
Production files: none. Test files: none. Evaluation files: P1 closure docs and sanitized P2 reports/scripts only. Dependencies: none. Migrations: none. Private runtime files are ignored and not listed as tracked changes.

## AO. Dependencies
No dependency or lockfile changes.

## AP. Remaining Limitations
No box-level observation gold; no actual detection-versus-recognition split; OCR alternatives/preprocessing not quality-scored; no complete live False READY matrix; no complete API-level concurrency or multipage resource test; one wrong high-confidence field remains; frozen scorer null/VERIFIED_ABSENT ordering limitation.

## AQ. Claim Boundaries
Seven documents only. Text equality to prior OCR output is reproducibility, not accuracy. DPI results are observation changes, not quality gains. Alias absence does not prove detection or recognition failure. Provider-level probes do not prove workflow concurrency safety. No broad Korean OCR superiority claims.

## AR. P2 Verdict
**P2_FAIL.** The critical required stage diagnosis and candidate comparison are not evidenced sufficiently to pass. No unjustified OCR/provider change was made.

## AS. Phase 9 Readiness
**NO.** A wrong non-null extraction remains, 17 unresolved fields persist in v1 scoring, all real samples require review, and observation correctness by stage is not established.

## AT. Recommended Next Step
Annotate visible label/value regions for the 17 unresolved cases plus a representative sample of already-correct fields, then score detection and recognition separately. Use that evidence to select one targeted OCR/render/preprocessing experiment and re-run the full production and safety matrix.

## AU. Git Final State
No commit or push. Starting and ending HEAD: `48e3824a780e3c051cba2d2eb1838851db1fcf1e`; branch `main`. `git diff --check` passed; tracked diff/stat are empty. Worktree contains untracked P1 artifacts, pre-existing unrelated evaluation/temp files, and the new sanitized `evaluation/p2_ocr/` artifacts. No tracked files were modified.
