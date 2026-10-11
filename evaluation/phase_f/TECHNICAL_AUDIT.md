# ADVS technical audit (Phase F, 2026-10-10)

Status: **documents only**. No production code was changed, nothing was committed or pushed, hold-out set 3 was not opened or run, and `phase-d3/internal-automation` was only read.

Evidence labels used in every table of this audit and of `APPROACH_EVALUATION.md`:

| Label | Meaning |
|---|---|
| **[V]** | Verified in this repository (code, committed report, or a probe run for this audit) |
| **[E]** | Supported by an external source (URL and access date given) |
| **[H]** | Hypothesis that needs an experiment |
| **[U]** | Unknown, no evidence available |

Implementation status words: **Implemented and verified**, **Implemented, not adequately tested**, **Partially implemented**, **Planned**, **Proposed research**.

## 1. What was inspected

| Source | What it is | Used for |
|---|---|---|
| Repository at `main` (`3381387`, clean except the uncommitted hold-out run log from the D3 work) | code, tests, docs, evaluation reports | source of truth |
| `evaluation/reports/` (`ADVS_system_audit_report.md`, `PHASE_B_REPORT.md`), `evaluation/phase_c/`, `phase_d/`, `phase_d2/`, `phase_e/`, `phase_e2/` | the phase reports and scored runs | evidence |
| `docs/midterm/` (`RESULTS.md`, `metrics.csv`, `ARCHITECTURE_SUMMARY.md`, `ROADMAP.md`, `DEMO_SCRIPT.md`, `ADVS_midterm.pptx/.pdf`, `slides_sources.md`, `screenshots_v2/`) | the October material | checked against code |
| `~/Downloads/ADVS_Master_Improvement_Plan.pdf` (11 pages, dated 2026-10-10) | the master improvement plan | context; checked against code |
| `~/Downloads/ADVS.pptx` (11 slides, image-only, 2026-09-14) | the September **plan** presentation (수행계획발표); no embedded text, read by rendering | historical context; conflicts listed in §6 |
| `~/Downloads/2026-2 종합설계프로젝트1 강의소개자료_김동균 교수님-3.pptx` | the course rules | presentation format and dates |
| `phase-d3/internal-automation` (read-only via `git show`) | unmerged D3 work | context only |
| `evaluation/reports/ADVS_system_audit_report.md` (earlier independent audit, 7 real documents) | findings F-001…F-013 and the real-corpus statements | context for real-data evidence |

**Not found:** the two Projects documents named in the brief (`ADVS_full_improvement_plan`, `ADVS_status_after_phaseE`) are not on this machine. `ADVS_Master_Improvement_Plan.pdf` appears to be the improvement plan and was used instead; if the Projects documents differ from it, this audit has not seen the differences.

## 2. Current architecture [V]

```
upload  ->  signature + decode validation  ->  local storage
        ->  PdfProcessor: PyMuPDF text layer (kept when >= 30 characters and >= 15 alphanumerics)
        ->  otherwise PaddleOCR (PP-OCRv5 Korean mobile detector + recogniser, CPU, one worker)
        ->  DocumentClassifier (deterministic keyword evidence, "heuristic-v4-abstain") + title gate
        ->  per-type extractor (label proximity / geometry) -> ExtractedValue + evidence (page, box, text)
        ->  field normaliser (dates, business numbers, names, GPA)
        ->  auto-acceptance policy (OCR values only; independent confirmation required)
        ->  workflow rules (database-driven checklist: required documents, validity, cross-document
            comparison, issue-date age, GPA threshold) -> submission status
        ->  review queue (confirm / correct / cannot determine) -> check re-runs
        ->  /overview read model -> Next.js web app (renders only what the API returned)
```

- **Backend:** FastAPI, SQLAlchemy 2, Alembic, PyMuPDF, Pillow; PaddleOCR 3.2.0 / PaddlePaddle 3.1.1 as an optional extra (`apps/api/pyproject.toml`). **No LLM, second recognition model or network model call exists** (`grep -iw "llm|openai|anthropic"` finds only the comment "No LLM" in `classifier.py`).
- **Database:** SQLAlchemy models for PostgreSQL; all runs and tests used **SQLite** (WAL mode since Phase E2).
- **Frontend:** Next.js 15 web app (applicant and reviewer flows); the admin app is an empty placeholder.
- **Status model:** 제출 가능 / 확인 필요 / 보완 필요, worst effect wins; missing evidence yields 확인 필요, never a pass.
- **Processing is synchronous:** OCR runs inside the HTTP request, on one worker, about 16 s per scanned page on this CPU (`docs/midterm/RESULTS.md`).
- **Machine used:** Apple M3 Pro, 18 GB RAM, no NVIDIA GPU (`sysctl`, 2026-10-10).

## 3. Existing working functionality

| Capability | Status | Evidence |
|---|---|---|
| Six mentor-defined document types: classification and field extraction | **Implemented and verified (synthetic data only)** | digital 790/790 evaluated fields correct over three corpora; `evaluation/phase_f/results/denominators.txt` |
| Digital-PDF path | **Implemented and verified (synthetic)**; trust of the text layer is **not** checked (§4, D-1) | 240/240 dev, 275/275 hold-out 1, 275/275 hold-out 2 |
| OCR path for scans and photos | **Implemented and verified (synthetic), assisted mode** | 0 wrong machine values in 790 evaluated fields per version; 4.8–6.2 % unresolved; only 1 of 22 scanned dev submissions decided without a person |
| Auto-acceptance policy (independent confirmation) | **Implemented and verified (synthetic)** | `evaluation/phase_d2/PHASE_D2_REPORT.md` §11; 0 false auto-accepts on E1–E12 |
| Cross-document and rule checks | **Implemented and verified (synthetic)** | submission verification tests (`tests/test_submission_verification*.py`) and the scored runs |
| Look-alike / unknown documents (title gate) | **Implemented and verified (synthetic)** | `phase_d2` E10 suite, B11 and S07 never 제출 가능 |
| Review flow, evidence page images, status banner, automatic re-check | **Implemented and verified** | 15 Playwright tests, 107 unit tests, axe 0 serious/critical, `evaluation/phase_e2/PHASE_E2_REPORT.md` |
| Demo reset, rehearsal, pre-loaded scenarios D1–D8 | **Implemented and verified** | three consecutive passing rehearsals at tag `midterm-demo-v2` |
| Photo handling: EXIF orientation, WEBP/other codec conversion | **Partially implemented** | `ImagePreprocessor` only does these two things (code comment says deskew etc. were deliberately left out); no HEIC (`ALLOWED_EXT` has pdf/png/jpg/jpeg/webp); no perspective correction, no quality gate |
| Text-layer trust check, provenance, manipulation detection | **Planned** (not implemented) | §4 D-1, probe result |
| D3 internal-consistency and decision-robust acceptance | **Implemented, unmerged, not judged on hold-out set 3** | branch `phase-d3/internal-automation`; the merge attempt was stopped because it changes demo scenario D6 |
| Second OCR engine, n-best alternatives, calibrated (conformal) acceptance in production | **Planned / proposed research** | D3 contains only an offline conformal *suggestion* report (`D3-11`) |
| Authentication, per-project access, audit log, background jobs, PostgreSQL test, admin screen | **Planned** | `docs/security/document-privacy.md`, `docs/domains/admin.md`, ROADMAP |

## 4. Confirmed defects and limitations (to be recorded for November; **no production change before the exam**)

| ID | Finding | Evidence | Severity | Where it would be fixed |
|---|---|---|---|---|
| **D-1** | **Hidden text in a PDF is trusted as a digital original.** A PDF whose visible page says 유효기간 2025-01-31 (an image) and whose invisible text layer (render mode 3) says 2027-12-31 is read as `direct_pdf_text` with the 2027 date. `is_meaningful_text` only checks length and character classes. | [V] probe `evaluation/phase_f/scripts/text_layer_probe.py`, output `results/text_layer_probe.txt` | High (authenticity and false-READY path), but exam-irrelevant: the demo uses only fictional files | `preprocessing/processor.py` + new trust check (November) |
| **D-2** | Scans and photos are almost never decided without a person: 1 of 22 scanned dev submissions was auto-decided; 92–100 % of scanned submissions need at least one human step. Cause is the confirmation policy, not recognition. | [V] `denominators.txt`, `B2_D2_dev_report.md` §5 | Medium (by design, safety first) | D3 / solver work (November) |
| **D-3** | **Scanned `university_name` extraction fails often:** 21/58 (scanned) and 24/58 (photos) correct, versus 58/58 digital; it accounts for 71 of the 87 non-correct machine values on scans/photos. Digits and dates are not the problem (business number 160/160 and 159/160, dates 98–100 %). | [V] `denominators.txt` | Medium: an extraction/layout (field mapping) defect | `extraction/*` student extractors (November, Approach E) |
| **D-4** | OCR confidence does not separate right from wrong: the only wrong values on dev scans (4 `department` values) carry 0.992 confidence. | [V] `evaluation/phase_d/calibration_table.md` | Design constraint: confidence cannot be a routing signal alone | policy (already floor-only) |
| **D-5** | Synthetic scans/photos are clean: the evidence cannot support any real-world accuracy claim. Photographs were only generated, never physically captured. The only real documents ever used are **seven mentor-sample scans** (the "P2.1 corpus": all OCR-only, none with an embedded text layer, one known wrong OCR value at confidence 0.9166); they were used to develop the extractors, are archived outside the repository (`~/ADVS_archive_20261004/`), and have no field-level ground truth in the repository, so they cannot be an unbiased test. | [V] `docs/midterm/RESULTS.md`; `evaluation/reports/ADVS_system_audit_report.md` F-010 and §7; the corpus itself is **[U]** (not in the repository) | High for the final exam, not for October | physical corpus + pilot (November); the master plan's "read-only check of the 7 archived documents" is a counts-only sanity check, not a judgement |
| D-6 | No HEIC, no perspective correction, no capture-quality gate. | [V] code | Medium | photo quality gate (November, optional) |
| D-7 | OCR speed about 16 s per page on CPU; synchronous request. | [V] `RESULTS.md`, Phase E reports | Medium | background jobs (December) |
| D-8 | Uploading the same file twice creates two document rows; only the check reports a notice. | [V] `evaluation/phase_e2/UX_AUDIT.md`, screenshot `15_same_document_twice.png` | Low | November |
| D-9 | The same finding can be reported twice by two rules (e.g. a date on scans); the API de-duplicates only in `/overview`. | [V] `PHASE_E_REPORT.md` §5 | Low | November |
| D-10 | D5 look-alike: the issue is attached to the 국세 납세증명서 requirement while the file is UNKNOWN; the manifest expects 보완 필요, the system says 확인 필요. | [V] `PHASE_E_REPORT.md` §5 | Low | November |
| D-11 | SQLite only, no login, admin app is a shell. | [V] | Known | December |
| D-12 | Stale documentation (§6). | [V] | Medium for the exam (honesty) | now (documents only) |

## 5. Test coverage and evidence

| Evidence | Size | What it proves | What it does not prove |
|---|---|---|---|
| Backend `pytest` (`apps/api/tests`) | 555 tests passing at tag `midterm-demo-v2` (re-run for this audit, see `PHASE_F_REPORT.md` §E) | classifier, extractors, rules, verification, review, overview, upload, pages | real OCR accuracy (OCR is stubbed or mocked in tests) |
| Frontend `vitest` | 107 tests | presentation logic, copy coverage for every issue code, review panel, upload queue | visual quality |
| Playwright + axe | 15 tests | applicant and reviewer flows, accuracy of screen vs API, accessibility, layout | cross-browser, load |
| Scored evaluation runs (scorer v2, frozen) on 299 + 279 + 279 fictional files | `evaluation/phase_d2/*.json` | extraction, classification, status, false READY on synthetic data | real-world behaviour; generalisation beyond the seven source layouts |
| Injected-error suites E1–E12 (474 dev, 666 hold-out 1 cases); E1–E18 on the D3 baseline (1353, 1532, 1523 cases) | `B2_D2_inj_*.md`; `phase-d3…/D3_configs.md` | no false READY and no false auto-accept for the injected misreads (one false auto-accept, no false READY, in E3c-both on hold-out-2 data in the D3 suite) | independence: the cases are derived from the same base documents |
| Overfitting grep | 75 values, 0 hits | no test values in production code | |

The honest denominator for the safety claim is small. Among submissions whose correct status is **not** READY there are n = 40 per input type over the three corpora (the same 22–25 scenarios with different values, so they are not independent samples); 0 false READY gives a 95 % upper bound of **7.5 %** by the rule of three. The injected-error suites are larger (n = 474 to 1532) and give tighter bounds (0.2–0.6 %) but share their base documents. See `EVALUATION_PROTOCOL.md` §5.

## 6. Conflicts between code, documents and presentations

| # | Document says | Code / evidence says | Resolution |
|---|---|---|---|
| 1 | September plan deck (`ADVS.pptx`, slides 6–7): ADVS is a **hybrid with an LLM** for ambiguous text; stack includes LLM | No LLM anywhere; classification and extraction are deterministic (`classifier.py` says "No LLM") | The deck and documents state that the system uses traditional OCR and deterministic rules only; this is the project scope (owner decision, 2026-10-11) |
| 2 | September deck, slide 3: MVP types are 졸업증명서, 경력증명서, 사업자등록증, 중소기업확인서 | Current scope is the mentor's six (four business, two student); 졸업/경력 support is preserved but not in the demo | Report scope as the six; mention history |
| 3 | September deck, slide 7: PostgreSQL in the stack | Models target PostgreSQL; everything was run and tested on SQLite | State "PostgreSQL schema, tested on SQLite" |
| 4 | Course deck (slide 5): **5 minutes presentation + 2 minutes Q&A**, penalty for overtime; **first midterm presentation 10/22 (week 8)**, second 11/19, final 12/10 | The master plan and the deck brief say the midterm is **2026-10-14** and plan a 10-minute talk plus demo | **Open question for the owner:** confirm the date and the allowed time. The deck now marks a 5-minute path (§ deck notes) |
| 5 | `docs/architecture/ARCHITECTURE.md`: module map lists only graduation/career/business/sme extractors, no `auto_acceptance`, `title_gate`, `evidence`; "client explicitly re-runs verification" | Eight extractors; auto-acceptance, title gate, evidence, overview read model exist; the web app re-runs the check automatically | Updated (documents only) |
| 6 | `docs/operations/testing.md`: "112 samples across the four…", four extractors | 299 + 279 + 279 fictional files; eight extractors; 555 + 107 + 15 tests | Updated |
| 7 | `docs/domains/classification.md`: `heuristic-v2`, no title gate | classifier version is `heuristic-v4-abstain` with a title gate | Updated |
| 8 | `README.md`: "CURRENT PHASE: Phase 2" | The project is in the midterm stabilisation phase | Updated |
| 9 | `docs/planning/ROADMAP.md`: Phase 1A–3 plan, "consider optional LLM extraction"; `DEVELOPMENT_PLAN.md`: a 4-week plan | Both predate the real schedule | Replaced by the current roadmap (history kept) |
| 10 | `evaluation/README.md`: only Phase B, "legacy datasets moved out" | Phase C–F reports and scored runs are in the repository | Updated |
| 11 | Master plan: "D3 ≈ −47–51 % on scans in development runs; scans 'assisted mode' ≈ 40 % of fields confirmed" | D3 numbers are on the unmerged branch (decision-blocking 5.41 → 2.68, i.e. −50 %; total unconfirmed 7.23 → 3.82); 40.4 % / 46.2 % auto-accepted on main | Consistent; deck labels D3 as 진행 중 |
| 12 | Master plan, §7: "present from tag `midterm-demo-v2`, new work on branches" | `main` contains the deck and docs after the tag | Consistent |
| 13 | Master plan: "Digital PDFs fully automatic and reliable, 0 false 제출 가능" | True on synthetic files; the text layer is trusted without checking (D-1) | The deck's limits slide and Q&A prepare for this |

## 7. Files that need updating (and what was done)

| File | Why | Done in this phase |
|---|---|---|
| `docs/midterm/ADVS_midterm.pptx` and `.pdf`, `slides_sources.md` | add n and uncertainty for the safety claim, honest approach comparison, October scope, November and December plans, the 5-minute path | yes (documents only) |
| `docs/midterm/ROADMAP.md`, `docs/planning/ROADMAP.md`, `docs/planning/DEVELOPMENT_PLAN.md` | stale phase plans | yes |
| `docs/midterm/RESULTS.md`, `metrics.csv` | add n and bounds to the safety rows | yes |
| `docs/architecture/ARCHITECTURE.md`, `docs/operations/testing.md`, `docs/domains/classification.md`, `README.md`, `evaluation/README.md`, `docs/DOCUMENTATION_INDEX.md` | stale statements (§6) | yes |
| `docs/planning/NOVEMBER_REPORT_TEMPLATE.md`, `DECEMBER_FINAL_REPORT_TEMPLATE.md` | new templates (pending sections, no fabricated results) | yes |
| Production code | none before the exam | **no change** |

## 8. Risks that could affect the October exam

| Risk | Likelihood / impact | Mitigation (no code change) |
|---|---|---|
| **Date and format mismatch**: the course deck says first midterm is 10/22 and each team has 5 minutes + 2 minutes Q&A | unknown / high | confirm with the TA or professor; the deck has a marked 5-minute path; consider a recorded demo clip |
| The live demo cannot fit a 5-minute slot | medium / high | recorded 60–90 s clip or screenshots; live demo during Q&A only |
| D3 unmerged and changes D6 | known | present from `midterm-demo-v2`; D3 only as 진행 중 on the roadmap |
| Questions about forged PDFs, real documents, LLM use | high / medium | answers prepared in the deck notes: D-1 was a recorded gap (fixed in Phase G), no real documents yet, no LLM or second recognition model is used |
| Port 3000 or OCR warm-up on stage | medium / medium | `make demo-rehearsal` the morning of the talk; fallback tag `midterm-demo-2026-10-14` |
| Hold-out set 3 status: the run log (uncommitted, 2026-10-06 13:45) records a raw OCR capture (`H3_chosen_raw.json`, git-ignored); it was never scored here, but the owner should confirm that nobody read its results before D3 is judged on it | low / medium | do not open it; confirm with the owner |
| Claims drifting from evidence | medium / high | every number in the deck is in `slides_sources.md`, with n and uncertainty for safety claims |

## 9. Audit conclusion

The October system is a **well-tested pipeline on synthetic data** whose strength is safe abstention, not OCR sophistication. On the available evidence, **recognition is not the bottleneck** (0 wrong machine values per 790 fields; business numbers and dates are almost always read correctly even on scans); the bottlenecks are (a) the cost of proving a correct OCR value is correct (the confirmation policy), (b) an extraction/layout defect on student documents (`university_name`), and (c) the absence of any real or physical data. That conclusion drives the recommendation in `APPROACH_EVALUATION.md`.

## 10. Status after Phase G (added later; sections 1–9 describe the audit as written)

| ID | Status | Evidence |
|---|---|---|
| D-1 hidden PDF text trusted | **Fixed on `phase-g/fixes`**: only visible text is read; pages with hidden date/number text, unreadable fonts, picture pages or overlapping texts go to OCR; `TEXT_LAYER_MISMATCH` is raised when the hidden tokens are not on the page | `apps/api/tests/test_phase_g_text_layer.py`; 0 flagged pages on 307 development PDFs, text identical to the old extraction |
| D-3 `university_name` on scans/photos | **Fixed (development data)**: 21/58 → 56/58 scans, 24/58 → 57/58 photos, 0 wrong values | `evaluation/phase_g/results/university_name_before_after.txt`, `apps/api/tests/test_phase_g_university_name.py` |
| D-2, D-4 | D-2 addressed by D3 (separate branch); D-4 is a design constraint | `evaluation/phase_d3/` |
| D-5, D-6, D-7, D-8, D-9, D-10, D-11 | Deferred, see `evaluation/phase_g/PHASE_G_REPORT.md` for reasons and target milestones | — |
| D-12 stale documents | Remaining items fixed (`layout/` line, `date.today()` note in the test-set README, text-layer description) | git history of `phase-g/fixes` |
