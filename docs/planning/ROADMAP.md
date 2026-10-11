# ADVS roadmap (updated 2026-10-10, Phase F)

This file replaces the original Phase 1A–3 plan (kept in §9 as history). Evidence behind every statement is in `evaluation/phase_f/` (`TECHNICAL_AUDIT.md`, `APPROACH_EVALUATION.md`, `EVALUATION_PROTOCOL.md`). Evidence labels: **[V]** verified in this repository, **[E]** external source, **[H]** hypothesis needing an experiment.

**Dates.** The windows are **October, November and December 2026**. The course deck lists the first midterm presentation on 10/22 (week 8), the second on 11/19 (week 12) and the final on 12/10 (week 15), with a result report in mid-December; the master improvement plan assumes a midterm on 10/14. Precise dates below are therefore *conditional on the confirmed course deadlines*. Effort is given as S / M / L with its repository basis, not in days.

## 0. Status after Phase G (2026-10-11)

Presentation date: **2026-10-15**. Demo build: **`midterm-demo-v3`** (merge of `phase-g/integrated`); `midterm-demo-v2` and `midterm-demo-2026-10-14` are unchanged. Done in Phase G, with evidence in `evaluation/phase_g/PHASE_G_REPORT.md`:

| Roadmap item | Status |
|---|---|
| N2 PDF text-layer trust check (D-1) | **done**: hidden text is ignored and flagged `TEXT_LAYER_MISMATCH`; 0 of 705 manipulated copies missed, 0 of 307 normal pages flagged, 12/12 manipulated submissions held at 확인 필요 |
| N3 `university_name` (D-3) | **done**: scans 21/58 → 56/58, photos 24/58 → 57/58 (development); hold-out 3: 9/20 → 19/20 and 11/20 → 20/20 |
| N4 D3 merged, hold-out 3 judged once | **done**: 0 false 제출 가능 (0/14 per input type), injections 0/1,525, review fields per scan 7.68 → 4.28 |
| Scope decision (owner, 2026-10-11) | **OCR-only MVP.** The product direction is traditional OCR → deterministic extraction and normalisation → validation and cross-document checks → safe submission decision. No second recognition model is planned. |
| Still open | D-2 partly (policy by design), D-5 real/physical data, D-6 photo gate, D-7 background OCR, D-8–D-10 minor, D-11 login and PostgreSQL, the owner-accepted H14 residual risk |

## 1. Baseline (frozen at tag `midterm-demo-v2`)

- Pipeline: upload → PDF text layer or PaddleOCR (PP-OCRv5 Korean mobile) → deterministic classification → per-type extraction with evidence → auto-acceptance policy → database-driven rules → status → review → overview API → web app. No LLM and no second recognition model; this is the scope of the project. [V]
- Six mentor-defined document types; fictional data only; SQLite only; no login; admin app is a placeholder. [V]
- Results on synthetic data: digital 790/790 correct fields; scans 741/790 and photos 752/790 with **0 wrong** machine values; 0 false READY in 40 not-READY submissions per input type (95 % upper bound 7.5 %) and in 474 + 666 injected cases. Real-world risk is not measured. [V] (`evaluation/phase_f/results/denominators.txt`)

## 2. Confirmed issues (recorded; **no production change before the exam**)

D-1 hidden PDF text is trusted as a digital original (probe-verified); D-2 scans are almost never decided without a person (confirmation policy); D-3 scanned `university_name` extraction 21/58 and 24/58; D-4 OCR confidence is not informative; D-5 only synthetic data; D-6 no HEIC, perspective correction or quality gate; D-7 ~16 s per page on CPU; D-8 duplicate upload creates two rows; D-9 duplicate findings; D-10 look-alike issue attribution; D-11 SQLite, no auth, admin shell; D-12 stale documents (fixed by documents in this phase). Details and evidence: `evaluation/phase_f/TECHNICAL_AUDIT.md` §4.

## 3. October 2026: stabilise, document, present (no production code changes)

Goal: the demonstrated MVP is stable and every claim is true and traceable.

| ID | Task | Why | What changes / where | How | Test and completion measure | Dependencies, fallback |
|---|---|---|---|---|---|---|
| O1 | Freeze the demo | the exam needs the rehearsed build | nothing; tag `midterm-demo-v2` is the demo | present from the tag; new work only on branches | `make demo-rehearsal` passes 3 times in a row the morning of the talk | fallback tag `midterm-demo-2026-10-14` |
| O2 | Align documents with code | conflicts between deck, plans and code (`TECHNICAL_AUDIT.md` §6) | `docs/midterm/*`, `docs/planning/*`, architecture, testing and classification docs, READMEs | edit documents only | every number in the deck traces to `slides_sources.md`, with n and uncertainty for safety claims | none |
| O3 | Record defects for November | D-1…D-11 must not be lost | this roadmap, `TECHNICAL_AUDIT.md` | list with evidence and owner | each has an ID, evidence and a milestone | none |
| O4 | **Confirm the date and the format with the TA or professor** | course deck: 5 min + 2 min Q&A (time over = penalty), first midterm 10/22; master plan: 10/14 and a 10-minute talk | none | ask; adapt the deck (it has a marked 5-minute path) | a written confirmation | if unconfirmed, prepare both: 5-minute path and 10-minute version |
| O5 | Backup demo | a 5-minute slot cannot hold a live demo | a recorded 60–90 s clip of D1, D2 and D6 plus the screenshots in `docs/midterm/screenshots_v2/` | screen recording | plays offline | live demo only in Q&A |
| O6 | (Optional, no code) start the physical corpus | the single biggest evidence gap (D-5) | print 10–15 fictional test documents; photograph (2 phones, desk, angle, lamp glare, shadow) and scan at 200 and 300 DPI | follow `EVALUATION_PROTOCOL.md` §1–2 | files stored with the capture conditions | continues in November |
| O7 | Keep hold-out set 3 unseen | it is the only judgement set for D3 | none | no run, no inspection | `holdout_runs.log` shows no hold-out-3 entry from this phase | none |

**Acceptance for October:** documents consistent with code; rehearsal 3×; hold-out 3 untouched; demo tag unchanged; the format question answered or both formats prepared.

**Deferred on purpose (not in October):** any change to extraction, classification, validation, policy or dependencies; D3 merge; login; PostgreSQL.

## 4. November 2026: measure, fix the verified defects, test feasibility

Goal: a controlled research and engineering iteration. Mandatory items first; optional research only if the mandatory ones are on track.

### Mandatory

| ID | Task | Why | Where | How | Test and completion measure | Dependencies, fallback |
|---|---|---|---|---|---|---|
| N1 | Freeze the October baseline and extend the measurement | one reproducible reference for all comparisons | `evaluation/harness/*` (scorer extensions in a new version), `evaluation/phase_f/` | add required-field recall, per-field tables and failure-cause labels; keep scorer v2 results reproducible | the baseline report reproduces `results/denominators.txt` from a clean checkout | S–M; none |
| N2 | **Text-layer trust check (G)** | closes D-1: hidden or OCR-generated text must not count as trusted digital text | `preprocessing/processor.py`, a new gate in `services/processing.py`, tests | render pages, OCR key regions, compare with the text layer; detect invisible text with PyMuPDF text tracing; record producer metadata; disagreeing pages go to the OCR path and are flagged | manipulation tests (hidden text differs from the visible page); **0 false rejects** on the 299 + 279 + 279 genuine digital files; runtime per page reported | S–M; fallback: reject suspicious PDFs to 확인 필요 |
| N3 | Fix scanned `university_name` extraction (E) | D-3: 71 of 87 non-correct values | student extractors in `document_intelligence/extraction/` | error-attribution first (layout vs recognition vs mapping), then a targeted parser | before/after on the same labelled documents; transcripts and enrolment certificates ≥ the digital level or an explained residual | S–M; fallback: leave to review |
| N4 | **Finish D3 and judge it once on hold-out 3** | measured burden reduction (5.41 → 2.68 decision-blocking fields on development data) | branch `phase-d3/internal-automation` | acceptance table; judge once; report n and bounds | 0 false READY and 0 wrong auto-accepts on all suites **or** the owner accepts the documented residual (E3c-both); demo scenario D6 and the rehearsal updated before merge | depends on O7; fallback: keep unmerged, report as research |
| N5 | Physical corpus and ground truth | closes D-5 | `evaluation/phase_f/` data (not committed if large), schema in `EVALUATION_PROTOCOL.md` §2 | two-person readability marking; guard the judgement split | counts per document type and capture condition; baseline measured on it | needs people and time; fallback: smaller corpus, wider reported bounds |
| N6 | Real-document pilot (read-only, counts only) | the "fictional documents" limit | none in code; a protocol | agree scope with the mentor and 플래시21; report counts only | counts of classified, extracted, needs-human; no content in the repository | needs authorisation; fallback: stay with the physical corpus |
| N7 | Reviewer queue and admin checklist screen (frontend, Munira) | UX audit items UX-19/20/21 | `apps/web`, `apps/admin` | follow `evaluation/phase_e2/UX_AUDIT.md` Part B | Playwright + axe tests; demo rehearsal | independent of N2–N6 |
| N8 | PostgreSQL and concurrency tests | the code targets PostgreSQL, tests ran on SQLite | `apps/api` tests, Docker Compose | run the suite and rehearsal on PostgreSQL; concurrent uploads and reviews | suite green on both databases; no locking failures | S–M; fallback: document SQLite-only limits |
| N9 | Small defects D-8, D-9, D-10 | UX and honesty | upload service, rule results | de-duplicate at the source, attribute issues correctly | unit tests; rehearsal | S |

### Optional research (only if N1–N5 are on track)

| ID | Task | Why | How | Completion measure | Fallback |
|---|---|---|---|---|---|
| R1 | Photo quality gate and perspective correction (H) | D-6 | measure on the physical corpus first; prototype offline with OpenCV (already installed); never wire globally without a per-image fallback | usable-photo rate and false-reject rate before/after | document that it was not justified |
| R3 | Conformal acceptance on real or physical data | the synthetic data have too few errors for calibration | needs error-bearing data (D3 report: ≥ 19 samples per field at α = 0.05, ≥ 99 at α = 0.01) | per-field bounds with sample sizes | keep hand-set floors |

**Acceptance for November:** baseline report (N1) with n and bounds; N2 and N3 verified before/after; D3 judged once with a merge decision; physical corpus with an answer key and measured baseline; remaining risks listed.

## 5. December 2026: final system and evaluation

| ID | Task | Why | Completion measure | Fallback |
|---|---|---|---|---|
| F2 | Authentication, per-project access, roles | production gap (`docs/security/document-privacy.md`) | every route protected; tests for cross-project access | document as future work |
| F3 | Privacy: no personal data in logs, retention and deletion, audit log | same | log inspection tests; retention job; audit view | document |
| F4 | Optional external checks (National Tax Service registry API; issuance-number links) | the only route to authenticity beyond text/visible consistency | works behind a switch, only with the mentor's agreement | omit |
| F5 | End-to-end suite, regression tests, deployment instructions, final architecture document | final exam and result report | a fresh deployment works from the documents; suites green | trim scope |
| F6 | Final evaluation report and presentation | graded deliverable | reproducible metrics with n and bounds; failure analysis; honest limits (`docs/planning/DECEMBER_FINAL_REPORT_TEMPLATE.md`) | none |

**Acceptance for December:** the final comparison (baseline vs the final build) reproducible from the repository; false READY reported with its denominator and bound on a fresh judgement set and on the real pilot if authorised; security basics in place; deployment verified; limitations stated.

## 6. Scope

The MVP uses traditional OCR only (PP-OCRv5 Korean through PaddleOCR; embedded PDF text where a trustworthy text layer exists). Improvements stay deterministic and measurable: extraction and normalisation rules, validation and cross-document checks, the confirmation policy, the PDF text-layer check, and (optionally) a photo quality gate. Traditional OCR does not guarantee authenticity and does not eliminate extraction errors; uncertain or conflicting values go to a person.

## 7. Dependencies and risks

| Risk | Mitigation |
|---|---|
| Course dates and format unconfirmed (10/14 vs 10/22; 5 min) | O4; two versions of the talk |
| Real data and physical captures need people and authorisation | start O6 in October; N5 before N6 |
| D3 changes demo D6 and its stress suite found one false READY in a correlated case | judge once on hold-out 3; owner decision on the residual; update demo and rehearsal before merge |
| Synthetic data too clean to calibrate or to show OCR differences | physical corpus; do not quote bounds as real-world |
| Parallel work causes merge conflicts | one branch per task, merge main into the branch (no rebase), full gates and rehearsal after every merge |
| Scope creep | optional items are dropped first; mandatory work = N1–N5, N7–N9, F2, F3, F5, F6 |

## 8. Explicitly deferred or out of scope

Fine-tuning OCR models; production second OCR engine; HEIC and multi-document splitting beyond what exists; new document types (졸업증명서 and 경력증명서 stay supported but out of the demo); GPU server deployment; legal or official verification of authenticity (text extraction is not authenticity verification).

## 9. History: the original plan (superseded)

Phase 1A bootstrap (monorepo, upload, mock OCR, PaddleOCR interface, frameworks); 1B functional MVP; 1C accuracy improvement (*"consider optional LLM extraction"*); 1D evaluation and delivery; Phase 2 document expansion; Phase 3 production hardening; and a list of twenty questions for 플래시21 (document types, sample documents, mandatory fields, validity rules, name matching, low-confidence handling, manual correction, retention, authentication, admin interface, export, deployment, languages, accuracy threshold). The questions on validity rules, name matching, manual correction and the accuracy threshold were answered in practice by the mentor-defined checklist and the review flow; the retention, authentication and deployment questions are still open and belong to December.
