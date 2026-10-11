# ADVS improvement approaches for the OCR-only MVP (Phase F, 2026-10-10; scope updated 2026-10-11)

Companion to `TECHNICAL_AUDIT.md` (same evidence labels: **[V]** verified in this repository, **[E]** external source, **[H]** hypothesis needing an experiment, **[U]** unknown). **Scope decision (owner, 2026-10-11): the MVP uses traditional OCR only.** The direction is: traditional OCR → deterministic field extraction and normalisation → validation and cross-document checks → safe submission decision. Approaches that add a second recognition model were removed from the project and from this document; only improvements to the existing pipeline remain. Traditional OCR does not guarantee authenticity and does not remove extraction errors, so uncertain or conflicting values continue to go to a person.

## 1. The workload and the evidence that decides the question

| Fact | Value | Label |
|---|---|---|
| Documents in scope | 4 business (사업자등록증, 중소기업확인서, 국세 납세증명서, 4대 사회보험료 완납증명서) + 2 student (재학증명서, 성적증명서) | [V] |
| Data | fictional documents on seven real layouts: 299 dev files; two 279-file hold-out sets (now development data); hold-out 3 judged once in Phase G | [V] |
| Machine values before any acceptance policy, three corpora, 790 evaluated fields per input type | digital 790 correct / 0 wrong; scans 741 / **0 wrong** / 49 unresolved (6.2 %); photos 752 / **0 wrong** / 38 unresolved (4.8 %) | [V] `results/denominators.txt` |
| Exact match, scans / photos | business number 160/160 and 159/160; valid_until 115/117 and 117/117; issue_date 55/55 | [V] |
| Where scans/photos fail | `university_name` 21/58 and 24/58 (71 of the 87 non-correct values); the rest are scattered single fields | [V] |
| OCR confidence as a signal | wrong values (4 `department`) sit at 0.992; confidence does not separate right from wrong | [V] `calibration_table.md` |
| Why scans still need people | the policy requires **independent** confirmation; 1 of 22 scanned dev submissions is decided without a person | [V] |
| Real photographs, real documents | no physical photographs; seven real mentor-sample **scans** were used in earlier phases for development (one known wrong OCR value at confidence 0.9166); the corpus is archived outside the repository and cannot be re-measured here | [U] |

**Reading of the evidence.** On this data, *recognition* of digits and dates is not the limiting factor; *proving* a recognised value is right (independent confirmation), a *layout/field-mapping* defect on student documents, and the *absence of real data* are. A better recogniser only helps if it (a) reads real photographs better than PP-OCRv5 (unknown, [U]), or (b) provides an **independent** second reading (unknown, [H]).


## 2. The recognition engine

| Statement | Source | Label |
|---|---|---|
| ADVS reads scans and photos with PP-OCRv5 (`korean_PP-OCRv5_mobile_rec`, `PP-OCRv5_mobile_det`) through PaddleOCR; ADVS pins `paddleocr==3.2.0` and `paddlepaddle==3.1.1` | `apps/api/pyproject.toml` | [V] |
| PP-OCRv5 lists Korean with **88.0 %** on a 5,007-image Korean text dataset (not administrative documents) | https://www.paddleocr.ai/latest/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.html | [E] |
| Digital PDFs are read from the embedded text layer where it is trustworthy (since Phase G only visible text) | `preprocessing/text_layer.py` | [V] |
| This machine: Apple M3 Pro, 18 GB, no NVIDIA GPU; OCR takes about 16 s per page on CPU | `sysctl`; `docs/midterm/RESULTS.md` | [V] |

## 3. What the current engine exposes (needed before designing routing)

| Signal | Exposed today? | Label |
|---|---|---|
| Per-line recognition confidence, polygon, detection box | yes (evidence `confidence`, `polygon`, `bounding_box`) | [V] |
| Per-character confidence, n-best alternatives | **no** | [V] |
| Calibrated probability | no; confidence is only a floor (0.90) | [V] |
| Second reading of the same crop (crop + autocontrast ×1.6), red-channel stamp pass | yes (`read_regions`; D3 stamp pass is on the unmerged branch). Same engine, so only partly independent | [V] |
| Format failures (business-number check digit, date logic, GPA arithmetic on the D3 branch) | yes | [V] |
| Cross-document agreement / disagreement, decision-relevance of a field, "near a decision boundary" | yes (auto-acceptance reasons; D3 `decision_relevant`) | [V] |
| Missing required field | yes (`REQUIRED_FIELD_UNRESOLVED`) | [V] |

The confirmation policy therefore relies on **policy outcomes and format/consistency failures**, not on OCR confidence.

## 4. The approaches, one by one

Effort is relative (S/M/L) with its repository basis; no calendar estimate is given because the course dates are unconfirmed (see `TECHNICAL_AUDIT.md` §6, item 4).

### A. Existing OCR pipeline (PP-OCRv5 Korean mobile + deterministic extraction)

| Criterion | Assessment | Label |
|---|---|---|
| Expected extraction quality | 0 wrong machine values per 790 fields on synthetic scans/photos; 4.8–6.2 % unresolved; clean synthetic rendering, so real quality is unknown | [V] / [U] |
| Evidence available | scored runs, calibration table, injections E1–E18 | [V] |
| Korean suitability | PP-OCRv5 Korean model, 88.0 % vendor-reported on generic Korean text | [E] |
| Exact-field accuracy risk | digits/dates fine on synthetic data; `university_name` mapping defect; real photo noise unknown | [V] / [U] |
| False READY risk | 0 of n = 40 not-READY submissions per input type (95 % upper bound 7.5 %); 0 of 474 / 666 injected cases | [V] |
| Latency / hardware | about 16 s per page on this CPU; no GPU needed | [V] |
| Engineering effort | already built (S to maintain) | [V] |
| Integration risk | none | [V] |
| October / November / December | **yes / yes / yes** (baseline) | |
| Evidence needed to keep | real or physical-photo measurement | [H] |


### E. Deterministic and human-review improvements

| Criterion | Assessment | Label |
|---|---|---|
| Expected quality | targets the verified defects: `university_name` mapping (D-3), hidden-text trust (D-1), photo quality and perspective (D-6), D3 internal confirmations; no new model risk | [V] / [H] |
| Evidence available | the failures above are measured; D3 already shows decision-blocking fields falling from 5.41 to 2.68 on development data (unmerged) | [V] |
| Exact-field accuracy / false READY risk | lowest model risk; D3's stress suite showed one false auto-accept and one false READY in a specific correlated case on hold-out-2 data (C1c/C4/C5), none on the baseline, so deterministic confirmation also needs adversarial tests | [V] |
| Latency / hardware | no extra model; preprocessing adds milliseconds to seconds | [H] |
| Engineering effort | S to M per item (the extractors and the processor are small modules; D3 is thirteen commits already written) | [V] basis |
| Integration risk | low to medium, each behind tests and the rehearsal | [V] |
| October / November / December | **documentation only / yes, first / yes** | |
| Evidence needed | per-item before/after on the same labelled documents and on hold-out 3 | [H] |

### F. Joint consistency solver with calibrated (conformal) acceptance

| Criterion | Assessment | Label |
|---|---|---|
| Idea | choose the most probable assignment of all fields that satisfies every rule (check digits, cross-document equality, GPA arithmetic, validity profile); accept a value only when a conformal bound on its error is below α | [V] project master plan (design intent, not a measurement) |
| Status in the repository | **partial**: D3 implements internal confirmations (strategy S8) and decision-robust acceptance (S9) on an unmerged branch; D3-11 is an offline report of conformal threshold *suggestions* | [V] |
| Verified limits | (1) the engine exposes no n-best alternatives, so a solver over single readings degenerates to constraint checking, which D3 already does; (2) conformal calibration on the synthetic data has almost no errors (4 wrong values in the dev scan/photo calibration), so its bounds (0.3–1.8 % at α = 0.05) rest on error-free samples and cannot validate calibration; (3) the D3 suite found one false auto-accept (case E3c-both) | [V] |
| False READY risk | the solver can raise it if a rule is mis-specified; conformal validity needs data resembling deployment | [H] |
| Effort / integration | L (candidate graph, search, calibration set, risk tiers) | [V] basis |
| October / November / December | **no / finish D3 and judge it on hold-out 3; collect physical data for calibration / calibrated acceptance only with real error-bearing data** | |
| Evidence needed | a physical or real corpus with enough errors per field type (the D3 report itself notes 19 samples per field at α = 0.05 and 99 at α = 0.01 as minimums) | [V] |

### G. PDF text-layer trust check (hidden or OCR-generated text must not count as trusted digital text)

| Criterion | Assessment | Label |
|---|---|---|
| Verified gap | the pipeline trusts any text layer of ≥ 30 characters; the probe shows hidden text (render mode 3) overriding what a person sees | [V] |
| Proposed check | render each page, read the key field regions with OCR, compare with the text layer; detect invisible text with PyMuPDF text tracing (render mode, opacity, clipping, text under images); treat disagreeing or OCR-converted pages as OCR; record producer metadata | [H] (feasibility of each signal untested) |
| Note on "convert scans to PDF" | OCRmyPDF-style conversion adds a text layer produced by OCR: it does not make the content reliable; such a file would be read as "digital" today | [V] reasoning, consistent with the master plan |
| Not a solution to authenticity | the check detects text/visible mismatch only; forged but self-consistent documents need issuer or registry verification | |
| Effort / risk | S to M, low integration risk (one new gate before the "digital" decision) | [V] basis |
| October / November / December | **record the defect only / yes, first priority / yes** | |
| Evidence needed | manipulation tests (hidden text differs from the page), false-reject rate on the 299 + 279 + 279 genuine digital files (must stay at zero), runtime per page | [H] |

### H. Photo quality gate with perspective correction

| Criterion | Assessment | Label |
|---|---|---|
| Today | EXIF orientation and codec conversion only; PaddleOCR's document unwarping is explicitly **off** (`use_doc_unwarping=False`); no quality gate; no HEIC | [V] |
| Expected value | unknown: no physical photograph has been measured; the code comment records that measured skew in earlier rounds was below the level where correction helps | [U] / [V] |
| Risk | global pre-processing can damage one capture while helping another (documented in the code comment); needs per-image fallbacks | [V] |
| Effort | M (OpenCV 4.10 is already installed; threshold fitting needs a physical corpus) | [V] basis |
| October / November / December | **no / measure first on a physical corpus, then prototype offline / adopt only if the usable-photo rate rises without new errors** | |
| Evidence needed | printed fictional documents photographed with several phones and conditions; usable-photo rate and false-reject rate before and after | [H] |


## 5. Comparison at a glance

| Approach | Evidence today | False-READY exposure | Effort | Status |
|---|---|---|---|---|
| A existing OCR | [V] strong on synthetic, none on real | measured: 0 events, bounds in `EVALUATION_PROTOCOL.md` §5 | maintain | **kept as the engine** |
| E deterministic + review | measured defects, D3 evidence | lowest model risk | S–M each | implemented in Phase G (`university_name`), continues |
| F solver + conformal | D3 partial; synthetic data too clean | adversarial suite found 1 case (H14, owner-accepted) | L | D3 merged; calibration needs real data |
| G text-layer trust | defect verified, then fixed | closes a known hole | S–M | **implemented** (Phase G) |
| H photo gate + perspective | none | unknown | M | optional, after the physical corpus |

## 6. Recommendation

Keep approach A as the engine. Continue with the deterministic, measurable improvements: E (extraction and normalisation rules, review flow), G (text-layer trust, done), F (D3 internal confirmation, done; conformal thresholds need error-bearing real data) and, optionally, H. The decisive missing evidence is a physical-photo corpus with an answer key: on synthetic data recognition is already near-exact, and the limits are independent confirmation, the absence of real data and layout/field-mapping defects.

**What would change this recommendation.** A physical-photo measurement showing that PP-OCRv5 makes frequent digit or date errors on real captures, or a demonstration that a remaining extraction defect is a recognition problem rather than a field-mapping problem.
