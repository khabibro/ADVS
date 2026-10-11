# PaddleOCR-VL vs the current OCR — isolated comparison

**Recommendation: insufficient evidence to adopt; continue testing.** Details in section 6. Nothing here is part of the product; no VLM is in production.

## 1. What was compared, and on what

| | |
|---|---|
| **A — current reading** | Embedded PDF text for digital files; PaddleOCR PP-OCRv5 Korean (paddleocr 3.2.0, CPU) for scans and photos. Replayed from the cached OCR of the evaluation runs, so A is exactly what the system read. |
| **B — VLM only** | PaddleOCR-VL parses each page (layout model + VLM per block). `analysis/adapter.py` turns the blocks into text lines (table cells get synthetic grid boxes from row/column position, plus "label : value" row lines); the **same production extractors** then map text to fields. |
| **D — selective VLM** | The VLM re-reads field **crops** (every field the system leaves to a person, plus the high-risk fields: business number, validity/issue dates, GPA, student number), cut with the production second-pass geometry. It confirms or disputes A's value; it never supplies a new one. Prompt `OCR:`. |
| Scorer | The frozen `score_v2.py` (`score_field`), sha256 `49674a9c…2ad2594`. Ground truth: the corpus manifests. |
| Data | Development: `test_variants` (299 files), hold-out 1 and 2 (279 each, development data since Phase D). **Final: hold-out 3, run once** (273 files with expected fields). All fictional. |
| Unit | Field (the scorer's KNOWN_VALUE fields). Fields of one file are not independent, so intervals are slightly optimistic; they are Wilson intervals. |

The A replay here scores a little lower than the pipeline gates (scans 97.0% vs 97.5%): it extracts with the manifest's document type for every file (so classification errors do not hide fields) and includes the file-format and capture-quality sets.

### Variant, versions, hardware (exact)

- **Model:** `PaddlePaddle/PaddleOCR-VL-1.6`, Apache-2.0, 0.9 B parameters, revision `c5630abae1d940eafe0697512a0325494b02ab42` (2026-08-08). Latest stable at run time (the 1.0 card says it points to 1.6 as the newer version).
- **Weights actually run:** the official `PaddlePaddle/PaddleOCR-VL-1.6-GGUF` (revision `511b09642bb324401f15f97cc23bc67e8f0a291d`), **BF16 — not quantised** (verified from the GGUF header: file type `MOSTLY_BF16`, tensors BF16/F32). Served by **llama.cpp 0.6.0 (build 11429, Metal)**, driven through the official `PaddleOCRVL(vl_rec_backend="llama-cpp-server")` pipeline; layout model PP-DocLayoutV3 on CPU. (Our brief's wording "quantized GGUF" does not apply: the official GGUF is BF16.)
- **Python stack:** paddlepaddle 3.3.1 (CPU), paddleocr 3.7.0, paddlex 3.7.2, transformers 5.19.0.
- **Hardware:** MacBook Pro, Apple M3 Pro, 11 cores, 18 GB, macOS 26.6.2. No NVIDIA GPU.
- **Language support:** the 1.6 card lists "en, zh, multilingual" and does not name Korean (the 1.0 card does). Korean reading was verified by running it: it read every Korean field in the tables below.
- **Frozen configuration:** `config_frozen.json` and the scripts are hashed in `results/frozen.json` (combined sha256 `90f00bbf…e3ebd826`), recorded and committed (`f475fc9`) **before** the hold-out 3 run; the files were verified unchanged right before it. Settings (adapter mode, crop prompt, padding) were chosen on `test_variants` only (adapter variants: rows 842, pairs 895, grid 854, both 931 correct of 1035 fields).

### GGUF route vs the native route (validation sample)

The model card's primary route is native Paddle. It needs about 75–114 s per page on this machine (one page took 2213 s while other jobs ran), which made the full run impractical, so the GGUF route was used. Agreement on an 8-file sample (`results/native_vs_gguf.md`):

| | |
|---|---|
| Pages with identical text | 3 of 8; character similarity 0.83 (long table page) and 0.994–1.000 on the others |
| Extracted field values (30 fields, production extractors) | **identical for 29 of 30**; native correct 26, GGUF correct 27 (the one difference: transcript GPA, native 3.87, GGUF 3.8, expected 3.80) |
| Speed | native 73–95 s per page on the uncontended pages, GGUF 7–12 s |

This supports "no systematic degradation from the GGUF route"; it is a small sample (8 files).

## 2. Results on development data (used to set up; not a judgement)

Fields scored: 2,967 (872 digital, 1,305 scan, 790 photo). Per input type, all field types together:

| Input | n | A correct | B correct | A wrong non-null | B wrong non-null | B wrong and not on the page | B unresolved |
|---|---|---|---|---|---|---|---|
| digital | 872 | 872 (100.0%) [99.6–100.0] | 785 (90.0%) [87.9–91.8] | 0 (≤0.3%) | 3 (0.3%) | 3 | 84 |
| scan | 1,305 | 1,253 (96.0%) [94.8–96.9] | 1,144 (87.7%) [85.8–89.3] | 1 | 3 | 3 | 158 |
| photo | 790 | 785 (99.4%) [98.5–99.7] | 706 (89.4%) [87.0–91.3] | 0 (≤0.4%) | 3 | 3 | 81 |

Full tables per field group: `results/tables_development.md`.

## 3. Final judgement: hold-out set 3 (run once)

Fields scored: 960 (289 digital, 396 scan, 275 photo).

### 3.1 Accuracy, wrong values, hallucinations (value not printed on the page)

| Input | n | A correct | B correct | A wrong non-null | B wrong non-null (not on the page) | B unresolved |
|---|---|---|---|---|---|---|
| digital | 289 | 288 (99.7%) [98.1–99.9] | 259 (89.6%) [85.6–92.6] | 0 (rule of three ≤1.0%) | 6 (2.1%) [1.0–4.5] (6) | 24 |
| scan | 396 | 384 (97.0%) [94.8–98.3] | 353 (89.1%) [85.7–91.8] | 0 (≤0.8%) | 4 (1.0%) [0.4–2.6] (4) | 39 |
| photo | 275 | 273 (99.3%) [97.4–99.8] | 248 (90.2%) [86.1–93.2] | 0 (≤1.1%) | 1 (0.4%) [0.1–2.0] (1) | 26 |

By field group (hold-out 3, B correct): business number 100% / 98.6% / 96.4% (digital / scan / photo); dates 98.7% / 96.0% / 98.6%; student number and GPA 92.7% / 83.6% / 92.3%; names and text 77.2% / 82.7% / 80.2% (A: 99.1% / 96.9% / 98.1%). Business-number and date accuracy of A: 100% in all three input types (dates: 98.0% on scans).

Every B wrong non-null value was a value that is **not on the page** (a character misread that produces a different, plausible value). Examples (all fictional): `주식회사 새봄테스트` read as `주식회사 새붐테스트` (4 files); `윤견본` read as `윤건분` / `윤건본` (3 files); **GPA 3.80 read as 3.5** (2 files).

### 3.2 Joint errors (A and B on the same fields)

| Input | n | P(A err) | P(B err) | P(A err ∧ B err) | P(both wrong ∧ identical output) |
|---|---|---|---|---|---|
| digital | 289 | 1 (0.3%) | 30 (10.4%) | 0 (≤1.0%) | 0 (≤1.0%) |
| scan | 396 | 12 (3.0%) | 43 (10.9%) | 3 (0.8%) [0.3–2.2] | 0 (≤0.8%) |
| photo | 275 | 2 (0.7%) | 27 (9.8%) | 0 (≤1.1%) | 0 (≤1.4%) |

("err" = wrong or unresolved.) On development data the same quantities were 16 of 1,305 (scans) and 2 of 790 (photos) for "both err", 0 for "both wrong and identical" with bounds 0.2–0.4%. **A is almost never wrong on these clean synthetic documents, so the correlation table rests on very few joint events (3 on hold-out 3 scans).** It does not show independence; it shows no observed shared error.

### 3.3 Simulated automation gain (no production change)

If exact agreement between A's value and the VLM's reading were accepted as the independent confirmation, how many of the fields that **a person must confirm today** (scans and photos, A decision NEEDS_HUMAN) would be accepted, and how many of those would be wrong?

| Method | fields needing a person | accepted by agreement | of those wrong (simulated false auto-accepts) |
|---|---|---|---|
| B page parse | 230 | 205 (89.1%) [84.4–92.5] | **0 of 205 (≤1.5%)** |
| D field crops | 217 | 215 (99.1%) [96.7–99.7] | **0 of 215 (≤1.4%)** |

By field type (D): business number 36 of 37, dates 55 of 55, student number/GPA 27 of 27, names and text 97 of 98. Development data: D accepted 560 of 584 (95.9%) with 1 simulated wrong value among them (1/560, 0.2%, a name field).

### 3.4 Error catching on the injected-error suites (E1–E18)

The suites corrupt A's reading; the VLM reads the true pixels. Caught = VLM reading exists and differs from the injected value.

| Method | injected targets | caught | VLM reproduced the injected value | no usable reading |
|---|---|---|---|---|
| B page parse | 1,557 | 1,459 (93.7%) [92.4–94.8] | 0 (≤0.2%) | 98 |
| D field crop | 1,385 | 1,385 (100%) [99.7–100] | 0 (≤0.2%) | 0 |

This is a **simulation**: injected errors are not real OCR errors; it shows the VLM would not repeat them, not how often the real OCR errs.

### 3.5 Speed and memory

| | median | p95 | notes |
|---|---|---|---|
| B page parse (GGUF, Metal) | 8.3 s per page | 19.9 s | layout model on CPU |
| D field crop | 0.34 s | 0.79 s | per crop |
| Current OCR (A) | about 16 s per page on CPU (Phase E measurement) | | |
| Native Paddle VLM, CPU | 75–114 s per page | | uncontended pages |

Peak memory: llama-server about 2.1 GB resident plus the Python pipeline about 0.8 GB (observed with `ps`); not measured with a dedicated profiler.

## 4. Failure examples (fictional data)

- **Dropped label (native and GGUF identical):** `S01-1_재학증명서_사진.jpg` — the VLM wrote `：2023123456` and omitted the label `학번`, so the production extractor found no student number (27 student-number fields unresolved for B on `test_variants` alone). The same page is read correctly by A.
- **Misread characters:** 새봄 → 새붐, 견본 → 건분, GPA 3.80 → 3.5 (hold-out 3). All three produced a plausible wrong value rather than an empty one — the failure mode the project is built to avoid.
- **Table content read correctly but not mappable:** tax-certificate company name (45 hold-out 3 fields unresolved for B) and transcript GPA: the text is right (see `results/pages_*`), the production extractors rely on page geometry that a parsed table does not carry. This is a limit of the adapter and extractors, not of recognition.
- **Where B beats A:** 12 fields A left empty were read correctly by B (student numbers, a university name on a 90°-rotated scan, a company name on a photo). The two engines err differently.

## 5. What this does and does not show

- On clean synthetic documents the current OCR is already at 97–99.7% field accuracy with **0 wrong values on hold-out 3**; the VLM page parse is worse (89–90%) and produces wrong values (1–2%) the current system does not. **Method B is not a replacement.**
- **Method D behaves like a good independent confirmer in simulation**: it confirmed 215 of 217 fields that need a person today, with no wrong value accepted, and it never reproduced an injected error. If that held on real data, it could cut the human-review burden.
- It does **not** show: behaviour on real or physical captures (none exist yet), error independence under real noise, benefit where A actually errs (A had 12 scan errors), or deployment cost (a 0.9 B model on Apple Metal here; the product hardware is undecided).
- OCR-VL does not verify authenticity; neither engine can.

## 6. Decision against the pre-registered gate (`docs/planning/ROADMAP.md`, F1)

Adopt only if all hold:

| Condition | Evidence | Met? |
|---|---|---|
| Lower human-review rate **on the physical/real set** at an unchanged upper bound for false auto-accept and false READY | Only synthetic data exists; no physical or real set has been built or measured. Simulated gain on synthetic data is large (99% of review fields confirmable, 0 wrong, bound ≤1.4%). | **Not testable yet** |
| Independence shown by the correlation table wherever agreement is used | 0 identical-wrong events, but only 3 joint errors on scans: bound ≤0.8–1.4%, not independence | **Inconclusive** |
| Latency and hardware fit | 0.34 s per crop on Apple Metal; no deployment hardware chosen; CPU-only native route is 75–114 s per page | **Unknown** |
| Decision logic unchanged | Agreement-as-confirmation would be a new confirmation source for the auto-acceptance policy (a policy change to be pre-registered) | **Not applicable until designed** |

**Recommendation: insufficient evidence — continue testing.** Do not reject: method D looks promising in simulation. Do not adopt: the gate's central condition (a real or physical set) cannot be evaluated. Next step for the second-midterm iteration: build the physical capture set with an answer key, rerun A and D on it with the frozen configuration, and design agreement-as-confirmation as a pre-registered rule before measuring it.

## 7. Reproduce

See `README.md`. Hold-out 3 stage: `evaluation/phase_g/scripts/final_judgement.sh` (baseline, candidate, injections) and `final_judgement_vlm.sh` (this comparison) in the integrated branch, outputs in `evaluation/phase_g/final/` and `research/vlm_poc/results/`.

One process note: the first attempts of the hold-out 3 session aborted before reading any hold-out file (an argument-parsing error, then a missing `manifest.json` in the baseline worktree); the VLM stage was then re-run once because it pointed at the wrong data folder; the parse also ran stalled for part of an hour while the laptop slept, and was resumed under `caffeinate`. No setting was changed after seeing hold-out 3 results.
