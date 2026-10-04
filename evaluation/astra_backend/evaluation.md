# Astra backend evaluation

## Scope and denominator

Seven Desktop originals were processed locally through the real FastAPI upload → process → retrieve → verify endpoints using SQLite persistence. Originals were neither modified nor copied into Git. No document was sent to a cloud provider. FastAPI TestClient exercises HTTP routing and persistence; it is not a Docker deployment test.

The seven files are seven distinct byte-level files and visually distinct pages. All seven match the prior Round-2 inventory's file hashes; this is a repeat evaluation, not seven new independent samples. The audit's six-file statement is contradicted by the current files. There are five document types, four broad layout families, three scanned one-page PDFs, four images, and seven visible stamps/seals. Native image sizes range from 400×566 to 1200×1854. No born-digital, mixed PDF, national-tax, graduation, career, multipage, or rotated document occurs in this realistic set.

**NO RELIABLE HOLDOUT POSSIBLE.** All layouts had already influenced Round-2 development. A leave-one-layout-out claim would also be invalid retrospectively. New independent institutions/templates are required before estimating generalization.

## Versioned gold and scorer

Both measurements use dataset `desktop-2026-09-29-v1`, gold `astra-gold-1.2`, and scorer `astra-safety-1.1`. Original prior gold, its hash, and the v1.0/v1.1 intermediate versions remain in the private artifact directory. `gold_manifest.json` publishes only states, required flags, and correction history. Actual comparison values remain private.

Every original was visually inspected; low-resolution regions were enlarged. This is agent annotation with inherited prior labels, not independent dual-human adjudication. Corrections: the transcript JPEG explicitly supplies the overall GPA denominator; the enrollment image clearly states faculty/department; a disputed surname glyph is AMBIGUOUS rather than asserted wrong; previously unlabelled populated address and certificate-number fields were directly annotated. The old surname assertion is retained for sensitivity analysis, not silently discarded. Under that disputed assertion an additional wrong-name output would be counted.

The fixed recall denominator contains 34 PRESENT assertions. There are two ABSENT assertions and three AMBIGUOUS assertions. Every emitted populated field is counted, including ambiguous or unlabelled fields. Whitespace/Unicode presentation is ignored; business-number dash formatting is field-specific. Company punctuation and numeric signs are not globally erased. No production normalizer is used as the oracle.

Supported precision = supported correct populated / all populated; supported recall = supported correct / PRESENT assertions. Wrong non-null is separate from unresolved. Correct abstention requires ABSENT or NOT_EVIDENCED. AMBIGUOUS_GROUND_TRUTH and NOT_EVALUATED earn no precision credit. Unresolved-required uses the explicitly frozen study field profile; it includes required ambiguity. Evidence coverage means a source reference exists, not that the value is true.

The old scorer misclassified VERIFIED_ABSENT null as unresolved, read negative assertions from a nonexistent normalized_value key, skipped negative rechecks, excluded upload failures from denominators, and omitted populated unlabelled fields from precision. Its broad alphanumeric equality also erased meaningful punctuation. The replacement is pure and does not mutate historical records. Historical summaries remain historical; sanitized legacy report text was redacted without rewriting its numeric results.

The seven-document readiness statistic applies an explicit study profile requiring identity/institution/issue-date fields for student documents and identity/validity fields for business documents. It detects READY despite unresolved required evidence; this is stricter than the original seed's issue-date-only student rule. It also checks the five one-file projects known to lack other required documents. False NEEDS_CORRECTION is NOT EVALUATED: there are no independently adjudicated gold-READY complete projects. Passing this small set does not demonstrate general readiness safety.

## Before versus after

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| SUPPORTED_FIELD_PRECISION | 0.8571 | NOT EVALUATED | NOT EVALUATED |
| SUPPORTED_FIELD_RECALL | 0.5294 | NOT EVALUATED | NOT EVALUATED |
| WRONG_NON_NULL_COUNT | 1 | NOT EVALUATED | NOT EVALUATED |
| CORRECT_ABSTENTION_COUNT | 2 | NOT EVALUATED | NOT EVALUATED |
| UNRESOLVED_REQUIRED_COUNT | 8 | NOT EVALUATED | NOT EVALUATED |
| EVIDENCE_COVERAGE | 1.0000 | NOT EVALUATED | NOT EVALUATED |
| CLASSIFICATION_ACCURACY | 1.0000 | NOT EVALUATED | NOT EVALUATED |
| CLASSIFICATION_ABSTENTION_RATE | 0.0000 | NOT EVALUATED | NOT EVALUATED |
| DOCUMENT_SUCCESS_RATE | 0.1429 | NOT EVALUATED | NOT EVALUATED |
| REVIEW_RATE | 1.0000 | NOT EVALUATED | NOT EVALUATED |
| FALSE_READY_COUNT | 2 | NOT EVALUATED | NOT EVALUATED |
| FALSE_NEEDS_CORRECTION_COUNT | NOT EVALUATED | NOT EVALUATED | NOT EVALUATED |

## Per-document results

C=correct, W=wrong non-null, U=unresolved PRESENT, A=correctly abstained, G=ambiguous gold. Final means latest recorded after run; if no after exists this table is explicitly baseline-only.

| Sample | Type | Before C/W/U/A/G | After C/W/U/A/G | Project before → after |
|---|---|---|---|---|
| ASTRA-R01 | SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | 1/0/2/1/0 | NOT RUN | NEEDS_CORRECTION → NOT RUN |
| ASTRA-R02 | BUSINESS_REGISTRATION_CERTIFICATE | 1/1/3/0/0 | NOT RUN | NEEDS_CORRECTION → NOT RUN |
| ASTRA-R03 | TRANSCRIPT | 2/0/3/0/1 | NOT RUN | NEEDS_CORRECTION → NOT RUN |
| ASTRA-R04 | TRANSCRIPT | 3/0/3/0/1 | NOT RUN | NEEDS_CORRECTION → NOT RUN |
| ASTRA-R05 | ENROLLMENT_CERTIFICATE | 3/0/2/0/0 | NOT RUN | READY → NOT RUN |
| ASTRA-R06 | SME_CONFIRMATION_CERTIFICATE | 6/0/1/0/0 | NOT RUN | NEEDS_CORRECTION → NOT RUN |
| ASTRA-R07 | ENROLLMENT_CERTIFICATE | 2/0/1/1/1 | NOT RUN | READY → NOT RUN |

## Per-field results

| Field | Before correct/wrong/unresolved | After correct/wrong/unresolved |
|---|---|---|
| business_address | 0/1/0 | NOT RUN |
| business_item | 0/0/0 | NOT RUN |
| business_registration_number | 2/0/1 | NOT RUN |
| business_type | 0/0/0 | NOT RUN |
| certificate_number | 1/0/0 | NOT RUN |
| company_name | 1/0/1 | NOT RUN |
| department | 0/0/1 | NOT RUN |
| gpa | 1/0/1 | NOT RUN |
| gpa_scale | 1/0/1 | NOT RUN |
| issue_date | 4/0/3 | NOT RUN |
| representative_name | 0/0/2 | NOT RUN |
| student_id | 2/0/1 | NOT RUN |
| student_name | 2/0/1 | NOT RUN |
| university_name | 1/0/3 | NOT RUN |
| valid_from | 1/0/0 | NOT RUN |
| valid_until | 1/0/0 | NOT RUN |
| workplace_name | 1/0/0 | NOT RUN |

## Classification confusion matrix

Before and latest after (when present) both retain all input files in the denominator.

| Gold type | Before predicted distribution | After predicted distribution |
|---|---|---|
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | {'SOCIAL_INSURANCE_PAYMENT_CERTIFICATE': 1} | NOT RUN |
| BUSINESS_REGISTRATION_CERTIFICATE | {'BUSINESS_REGISTRATION_CERTIFICATE': 1} | NOT RUN |
| TRANSCRIPT | {'TRANSCRIPT': 2} | NOT RUN |
| ENROLLMENT_CERTIFICATE | {'ENROLLMENT_CERTIFICATE': 2} | NOT RUN |
| SME_CONFIRMATION_CERTIFICATE | {'SME_CONFIRMATION_CERTIFICATE': 1} | NOT RUN |

## Wrong populated values and visual trace

Baseline ASTRA-R02 business_address contains a one-glyph Hangul recognition substitution. Original and detection/evidence overlays were inspected privately. Detection covers the correct address row, label recognition and reading order are correct, the selected candidate points to that row, and normalization does not create the substitution. OCR confidence is about 0.912 and the old evidence policy marks it SUFFICIENT. This field was absent from old gold, so the prior headline precision silently excluded it. The machine value remains a recognition problem unless the final run explicitly changes it; evidence review can prevent unsafe use without pretending the glyph was repaired.

ASTRA-R03 disputed surname is an annotation uncertainty, not a confirmed recognition failure in this evaluation. The original low-resolution crop and selected source boxes were inspected. The old field assembled five evidence boxes, including unrelated identity cells; provenance abundance did not prove correctness. Ambiguous output remains counted in the precision denominator and requires review.

`failure_ledger.json` retains fixed synthetic failures and every realistic unresolved/ambiguous/absent observation with an earliest-stage diagnosis. Transcript header merging is detector segmentation; overall GPA pairing is table structure; the address is recognition; missing standalone institution associations are candidate generation. These categories are not interchangeable.

## Separate synthetic benchmark

Gold-text runs isolate deterministic classification/extraction and do not measure OCR or production evidence policy. Positive synthetic, old out-of-scope negatives, and public-reference recreations are separate. Dev and historical held_out are exported separately; existing development history means the split is not a fresh independent holdout. Original negative gold includes document types later added to product scope, so some apparent classification errors are obsolete-ontology labels; those labels are retained and disclosed instead of silently corrected.

| Group/split | Before count | Before precision / recall / wrong | After precision / recall / wrong |
|---|---:|---|---|
| SYNTHETIC_REALISTIC/dev | 83 | 0.9157 / 0.9105 / 0 | NOT RUN |
| NEGATIVE_OUT_OF_SCOPE/dev | 19 | 0.0000 / NOT EVALUATED / 0 | NOT RUN |
| RECREATED_FROM_PUBLIC_REFERENCE/dev | 3 | 1.0000 / 1.0000 / 0 | NOT RUN |
| SYNTHETIC_REALISTIC/held | 24 | 0.9073 / 0.8954 / 2 | NOT RUN |
| NEGATIVE_OUT_OF_SCOPE/held | 6 | 0.0000 / NOT EVALUATED / 0 | NOT RUN |
| RECREATED_FROM_PUBLIC_REFERENCE/held | 2 | 1.0000 / 1.0000 / 0 | NOT RUN |

## Performance and reproducibility

| End-to-end processing | Before ms | After ms |
|---|---:|---:|
| median | 8365.7238 | NOT RUN |
| min | 4447.2593 | NOT RUN |
| max | 26866.6900 | NOT RUN |

One pass per phase, CPU local inference. The first call includes lazy provider initialization and is not a separately measured initialization benchmark. No production throughput claim is justified. Upload elapsed time and source-page durations remain in private records; renderer-specific CPU/memory and peak temporary-disk usage were not instrumented. Configured PDF rendering is 288 DPI; an initial harness metadata literal erroneously said 250, so the derived report explicitly corrects it using persisted page metadata without rewriting raw historical output.

Each run records git commit, backend source-tree hash, starting dirty patch hash, scorer hash, provider/package versions, model-file SHA-256 hashes, source-page metadata, and evaluation date. Backend source snapshots permit rerunning the baseline. Model hashes identify the cached weights actually used, but no claim of bitwise reproducibility across CPUs/Paddle builds is made.

## Limits and next data

All seven current realistic files were already available to prior development; small-sample results are descriptive only. Acquire independently annotated templates from additional institutions, real mixed born-digital/scanned multipage files, national-tax documents, controlled rotations, stamp occlusion and resolution variants, and paired complete project bundles. Resolve the ambiguous surname and department semantics with a human annotator. Measure wrong values, abstention, and review workload on a withheld set before adopting a different OCR/layout provider or relaxing association rules. No broad production-readiness claim is supported.
