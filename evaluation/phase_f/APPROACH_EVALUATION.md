# ADVS extraction approaches: an unbiased evaluation (Phase F, 2026-10-10)

Companion to `TECHNICAL_AUDIT.md` (same evidence labels: **[V]** verified in this repository, **[E]** external source, **[H]** hypothesis needing an experiment, **[U]** unknown). **Nothing here was measured on PaddleOCR-VL**: it is not installed, and the project constraint forbids adding it before the exam. External statements come from the pages listed in §2 and were read through an automatic page summary on 2026-10-10; they must be re-read at the source before they are quoted in a report.

## 1. The workload and the evidence that decides the question

| Fact | Value | Label |
|---|---|---|
| Documents in scope | 4 business (사업자등록증, 중소기업확인서, 국세 납세증명서, 4대 사회보험료 완납증명서) + 2 student (재학증명서, 성적증명서) | [V] |
| Data | fictional documents on seven real layouts: 299 dev files; two 279-file hold-out sets (now development data); hold-out 3 reserved and unseen | [V] |
| Machine values before any acceptance policy, three corpora, 790 evaluated fields per input type | digital 790 correct / 0 wrong; scans 741 / **0 wrong** / 49 unresolved (6.2 %); photos 752 / **0 wrong** / 38 unresolved (4.8 %) | [V] `results/denominators.txt` |
| Exact match, scans / photos | business number 160/160 and 159/160; valid_until 115/117 and 117/117; issue_date 55/55 | [V] |
| Where scans/photos fail | `university_name` 21/58 and 24/58 (71 of the 87 non-correct values); the rest are scattered single fields | [V] |
| OCR confidence as a signal | wrong values (4 `department`) sit at 0.992; confidence does not separate right from wrong | [V] `calibration_table.md` |
| Why scans still need people | the policy requires **independent** confirmation; 1 of 22 scanned dev submissions is decided without a person | [V] |
| Real photographs, real documents | no physical photographs; seven real mentor-sample **scans** were used in earlier phases for development (one known wrong OCR value at confidence 0.9166); the corpus is archived outside the repository and cannot be re-measured here | [U] |

**Reading of the evidence.** On this data, *recognition* of digits and dates is not the limiting factor; *proving* a recognised value is right (independent confirmation), a *layout/field-mapping* defect on student documents, and the *absence of real data* are. A better recogniser only helps if it (a) reads real photographs better than PP-OCRv5 (unknown, [U]), or (b) provides an **independent** second reading (unknown, [H]).

## 2. External facts about the candidate model (accessed 2026-10-10)

| Statement | Source | Label |
|---|---|---|
| PaddleOCR-VL: about 0.9 B parameters (model card lists 1.0 B in BF16), NaViT-style visual encoder + ERNIE-4.5-0.3B language model; **Apache-2.0** | https://huggingface.co/PaddlePaddle/PaddleOCR-VL | [E] |
| Supports **109 languages, Korean listed**; newer releases exist: v1.5 (2026-01-29: skew, warping, photographed documents, seals) and v1.6 (2026-05-28, now the default `pipeline_version`); the model card says a newer version is available | model card; https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PaddleOCR-VL.html | [E] |
| Official install uses `paddlepaddle-gpu>=3.2.1` and `paddleocr[doc-parser]>=3.4.0`. **ADVS pins `paddleocr==3.2.0` and `paddlepaddle==3.1.1`**, so an isolated environment is required | model card; `apps/api/pyproject.toml` | [E] + [V] |
| Hardware matrix: PaddlePaddle/Transformers need NVIDIA compute capability ≥ 7.0 and CUDA ≥ 11.8; vLLM needs CC ≥ 8.0 and CUDA ≥ 12.6; no minimum VRAM is stated; x64 CPU is supported through PaddlePaddle/Transformers; on Apple Silicon only the PaddlePaddle and MLX-VLM routes are marked supported; quick-start methods are "for validation only" | PaddleOCR-VL pipeline page | [E] |
| Running only the VLM does not reproduce the reported results; the full pipeline includes a layout model (PP-DocLayoutV2) | PaddleOCR-VL pipeline page | [E] |
| Reported benchmarks are on **OmniDocBench** (v1.5: 94.5 %; v1.6: 96.3 %, vendor-reported), MDPBench (overall 69.6, digital 87.6, photographed 63.6) and olmOCR-bench (80); none are Korean administrative certificates; no latency or memory figures are given | model card; pipeline page | [E] |
| PP-OCRv5 (the engine ADVS uses) lists Korean (`korean_PP-OCRv5_mobile_rec`) with **88.0 %** on a 5,007-image Korean text dataset (not administrative documents) | https://www.paddleocr.ai/latest/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.html | [E] |
| This machine: Apple M3 Pro, 18 GB, no NVIDIA GPU | `sysctl` | [V] |

Consequence: a PaddleOCR-VL proof of concept cannot be assumed to run on the development Mac at useful speed; it probably needs a CUDA machine or a measured CPU/MLX run ([H]). Latency, memory and Korean certificate accuracy are **[U]** until measured.

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

Routing to a second model can therefore be built on **policy outcomes and format/consistency failures**, not on OCR confidence.

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

### B. PaddleOCR-VL as the only extraction model

| Criterion | Assessment | Label |
|---|---|---|
| Expected quality | strong vendor benchmark results on document parsing; nothing on Korean certificates; generative decoding can in principle substitute or invent characters, which is the risk that matters for exact digits | [E] / [H] |
| Evidence available | none in this repository | [U] |
| Korean suitability | Korean is listed among 109 languages | [E] |
| Exact-field accuracy risk | possible wrong digits, omitted fields, hallucinated values, output inconsistency between runs; per-character confidence is not exposed by the pipeline in the documentation read | [H] / [U] |
| False READY risk | unknown; a fluent wrong value without a usable confidence is the worst case for a policy that depends on independent confirmation | [H] |
| Latency / hardware | not published; vLLM needs CC ≥ 8.0 and CUDA ≥ 12.6; no stated VRAM minimum; Apple Silicon support is limited | [E] / [U] |
| Engineering effort | L: replace the line-and-box contract that extractors, evidence and the review crop depend on (new layout-block adapter); dependency conflict with the pinned Paddle versions | [V] basis |
| Integration risk | high | [H] |
| October / November / December | **no / no (PoC only, in isolation) / only if the PoC beats A on the metrics in `EVALUATION_PROTOCOL.md`** | |
| Evidence needed before adoption | same-document comparison on physical photos and a real pilot; error correlation; latency on the target hardware | [H] |

### C. Both engines on every document

| Criterion | Assessment | Label |
|---|---|---|
| Expected quality | on clean synthetic data both are probably near-perfect, so agreement carries almost no information; on difficult photos it could help or not | [H] |
| Evidence available | none | [U] |
| Exact-field accuracy / false READY risk | agreement of two models trained on overlapping data is not independent confirmation; the repository already learned this with "two passes over the same pixels are not two witnesses" and H14-type correlated errors | [V] (lesson) / [H] |
| Latency / hardware | at least the sum of both (A alone is already ~16 s per page on CPU) | [V] + [U] |
| Engineering effort | M to L (adapter, merge/fusion, disagreement handling, storage of two readings, UI for alternatives) | [V] basis |
| Integration risk | medium to high; doubles failure modes | [H] |
| October / November / December | **no / measurement only (offline, on recorded outputs) / only if correlation is low** | |
| Evidence needed | the joint-error table: for each field type, P(both wrong) and P(both wrong with the same output) on physical or real images; agreement counts as evidence only where that probability is below a pre-set ε | [H] |

### D. Existing OCR first, selective VLM verification

| Criterion | Assessment | Label |
|---|---|---|
| Expected quality | targets exactly the cases ADVS cannot confirm today (OCR-only fields without another source); gain depends on independence and on VLM accuracy for those fields | [H] |
| Evidence available | none for the VLM; the routing signals exist (§3) | [V] / [U] |
| Routing signals | missing required field, format/check-digit failure, no independent confirmation, cross-document disagreement, near a decision boundary, decision-relevant field. **Not** OCR confidence | [V] |
| Exact-field accuracy / false READY risk | a VLM answer that agrees with OCR is worth something only if their errors are independent ([H]); a disagreement must go to a person, never to an automatic winner | [H] |
| Latency / hardware | the VLM runs only on selected crops or pages; but in the current policy most decision-driving OCR fields are "unconfirmed", so the selected share is large (about 60 % of scanned fields were not auto-accepted on dev) | [V] |
| Engineering effort | M: a second `read_regions`-style provider behind the existing interface; the interface already accepts additional readings | [V] basis |
| Integration risk | medium, contained: it can be added as another **evidence source** without changing the decision logic | [H] |
| October / November / December | **no / isolated offline PoC / conditional adoption** | |
| Evidence needed | the same as C plus the human-review rate at a fixed upper bound on false auto-accept | [H] |

### E. Deterministic and human-review improvements without a second model

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

| Approach | Evidence today | False-READY exposure | Effort | October | November | December |
|---|---|---|---|---|---|---|
| A existing OCR | [V] strong on synthetic, none on real | measured: 0 events, bounds in `EVALUATION_PROTOCOL.md` §5 | maintain | **keep** | keep as baseline | keep |
| B VLM only | none | unknown, plausibly worse | L | no | isolated PoC only | no unless PoC wins |
| C both on every document | none | unknown; agreement not proof | M–L | no | offline measurement | only if correlation is low |
| D OCR + selective VLM | none (routing signals exist) | depends on independence | M | no | isolated offline PoC | conditional |
| E deterministic + review | measured defects, D3 evidence | lowest model risk | S–M each | docs only | **first** | yes |
| F solver + conformal | D3 partial; synthetic data too clean | adversarial suite found 1 case | L | no | finish D3, collect data | conditional on data |
| G text-layer trust | defect verified | closes a known hole | S–M | record | **first** | yes |
| H photo gate + perspective | none | unknown | M | no | measure, prototype | conditional |

## 6. Recommendations by milestone

**October (now to the exam).** Present approach A as the baseline and approaches E, G, H as the *measured* next steps; present B, C, D as *evaluated, not integrated*. No dependency, model or code change. Record D-1, D-3, D-8 to D-10 for November. Update documents so that every claim carries its denominator (`EVALUATION_PROTOCOL.md`).

**November (progress report).** In this order: (1) freeze the October baseline (tag `midterm-demo-v2`); (2) text-layer trust check (G) with manipulation tests; (3) diagnose and fix `university_name` on student documents (E) with before/after on the same labelled documents; (4) finish D3 and judge it once on hold-out 3, with n and bounds; (5) build the physical-photo corpus and the field-level answer key; (6) **only if** (1)–(5) are on track, an isolated PaddleOCR-VL proof of concept (separate environment, recorded OCR outputs, offline comparison on the same documents, correlation table). If hardware or time make the comparison unreliable, say so and improve the baseline instead; the PoC is optional.

**December (final).** Decide from the evidence. Adopt selective VLM verification (D) **only if all of these hold**, with thresholds fixed in the November plan *before* looking at results: it lowers the human-review rate on the physical/real set at an unchanged upper bound for false auto-accept and false READY; the joint-error table shows independence where agreement is used as evidence; latency and hardware fit the deployment; the integration keeps the decision logic unchanged. Otherwise **keep A + E (+ D3 if it passes)** and report the VLM result as a negative or inconclusive finding. Reject B unless it beats A on exact-field accuracy for the decision-driving fields *and* provides a usable uncertainty signal.

**What would change this recommendation.** A physical-photo measurement showing that PP-OCRv5 makes frequent digit or date errors on real captures (raises the value of C/D); a measured joint-error table showing independence (supports D); a VLM run showing hallucinated digits on certificates (rejects B and weakens D); a demonstration that the `university_name` defect is a recognition problem, not a mapping problem (shifts effort from E to a better reader); an official statement of VRAM and latency that fits the available hardware.

## 7. Isolated PoC requirements (for November, if attempted)

| Item | Requirement | Label |
|---|---|---|
| Environment | separate virtual environment or container; `paddlepaddle(-gpu) >= 3.2.1`, `paddleocr[doc-parser] >= 3.4.0`; never in the production extra | [E] |
| Hardware | an NVIDIA GPU with compute capability ≥ 8.0 and CUDA ≥ 12.6 for vLLM serving, or a measured CPU / MLX-VLM run on the Mac; VRAM minimum not published | [E] / [U] |
| Disk | Docker images of 8 to 13 GB are mentioned | [E] |
| Data | recorded OCR outputs and images of the physical corpus; no real personal documents leave the authorised machine | [V] policy |
| Output | a table per field type with both engines' outputs, the joint-error rate, the human-review rate at fixed bounds, and latency; stored under `evaluation/phase_f/` and never wired into the API | |
