# ADVS — Midterm results (2026-10-15, build `midterm-demo-v3.2`; pipeline and numbers identical to `midterm-demo-v3`)

**AI 기반 행정 제출서류 분석 및 자동 점검 시스템 (ADVS).** ADVS reads Korean administrative documents (embedded PDF text, or OCR for scans and photos), classifies them, extracts fields with their evidence, and checks a submission against a workflow checklist. It answers 제출 가능 / 보완 필요 / 확인 필요 with a reason per issue; a person confirms only the values the system cannot confirm itself. 제출 가능 means "no blocking issue found in the configured pre-check", not official approval.

All numbers: **fictional test documents** built on the layouts of a few real samples, run through the real pipeline by scripts. Sources are repo paths; "dev" = `test_variants` (22 sets × digital/scanned/images), hold-out sets 1 and 2 (development data); **hold-out set 3 was judged once** on the Phase G build (below).

## Mentor requirements → status
| Requirement | Status | Note |
|---|---|---|
| Business: 사업자등록증, 중소기업확인서, 국세 납세증명서, 4대 사회보험료 완납증명서 | implemented | classification + field extraction; digital and scanned |
| Student: 재학증명서, 성적증명서 | implemented | |
| Required-document check | implemented | demo D8 |
| Validity / expiry check | implemented | demo D2 |
| Cross-document match (company name, business number, student number/name) | implemented | company-name notation (주식회사/(주)/㈜) normalised; demo D3, D4 |
| Student: issue date within 90 days; student number required | implemented | configurable seed rule (`scripts/seed.py`) |
| GPA threshold | partly | rule exists (seed value 3.0); the mentor's real threshold is **to be confirmed** |
| Look-alike / unsupported document (e.g. 지방세 instead of 국세) | implemented | never 제출 가능; held for 확인 필요 (demo D5) |
| Human review of unconfirmed values | implemented | demo D9 (D6 is now decided automatically) |
| Official verification (National Tax Service API, issuance numbers) | planned | `ROADMAP.md` |
| Authentication, privacy controls, audit log | planned | not built |

## Safety (re-checked on the v3 build: 613 backend tests, 108 web unit tests, 22 browser tests (15 run, 7 skipped: they need the mentor's real documents, deliberately not used), rehearsal 3/3 runs)
| Measure | Result (events / n) | 95 % upper bound | Source |
|---|---|---|---|
| False 제출 가능, submissions whose correct status is not READY, development + hold-outs 1–2, per input type | **0 / 40** (12 + 14 + 14; the same scenario types re-instantiated) | 7.5 % (about 21 % counting each scenario type once) | `evaluation/phase_g/results/denominators_final.txt` |
| False 제출 가능, **hold-out 3 (judged once)**, per input type | **0 / 14** (digital, scans, photos) | 21.4 % (14 scenario types) | `evaluation/phase_g/final/H3_integrated_report.md`, `denominators_final.txt` |
| False 제출 가능, injected OCR errors E1–E18, development / hold-out 1 / hold-out 2 / **hold-out 3** | **0 / 1,354**, **0 / 1,532**, **1 / 1,523** (the owner-accepted H14 case: both OCR passes make the same error), **0 / 1,525** | 0.22 %, 0.20 %, 0.20 %, 0.20 % (cases share base documents: optimistic) | `evaluation/phase_g/results/gate_summary_dev_final.md`, `evaluation/phase_g/final/H3_integrated_inj.md` |
| False auto-accepts on single-error injections | **0** in all four suites (the only false auto-accept is the H14 case above) | | same |
| Manipulated PDFs (hidden text: invisible, white-on-white, tiny): hidden date and number never read | **0 / 705** missed; pipeline run: **0 / 12** reached 제출 가능, 12 / 12 flagged `TEXT_LAYER_MISMATCH` | 0.43 % (705), 25 % (12) | `evaluation/phase_g/results/pdf_manipulation_suite.md`, `pdf_manipulation_pipeline.md` |
| False alarms on normal digital PDFs | **0 / 307** pages flagged | 1.0 % | `evaluation/phase_g/results/false_alarm_digital_pdfs.txt` |

These bounds describe the **synthetic** test data only; the real-world false-제출-가능 rate is not measured and cannot be stated. Extracting visible text does not prove a document is authentic.

## Accuracy (machine value, before any acceptance policy)
| Measure | Development corpora (dev + hold-outs 1–2, 790 fields per input type) | Hold-out 3, judged once | Source |
|---|---|---|---|
| Digital extraction, fields correct | **790 / 790** | 274 / 275 (baseline: the same 274 / 275; one student name on a layout without a student number) | `denominators_final.txt` |
| Scans, fields correct (0 wrong) | **779 / 790 (98.6 %)** (before Phase G: 741 / 790) | **268 / 275 (97.5 %)** (main baseline 257 / 275) | same |
| Photos, fields correct (0 wrong) | **785 / 790 (99.4 %)** (before: 752 / 790) | **273 / 275 (99.3 %)** (main baseline 264 / 275) | same |
| `university_name` on scans / photos | **56 / 58, 57 / 58** (before: 21 / 58, 24 / 58) | **19 / 20, 20 / 20** (main baseline 9 / 20, 11 / 20) | `evaluation/phase_g/results/university_name_before_after.txt`, hold-out 3 reports |
| Classification | 100 % match on development data | 1 scanned enrolment certificate misclassified on hold-out 3 (baseline: the same one) | `H3_integrated_report.md` |

## Automation (OCR scans and photos; review burden = fields a person must still check, per submission)
| Stage | Scanned / images | Source |
|---|---|---|
| Baseline B0 (every OCR field to a person) | 11.64 / 11.64 | `evaluation/phase_d/PHASE_D_REPORT.md` §3 |
| D2 (the v2 demo build) | 7.23 / 6.59 dev | `evaluation/phase_d2/PHASE_D2_REPORT.md` §11 |
| **v3 build** (D3 internal automation merged) | **3.73 / 3.09 dev**; 4.16 / 3.52 hold-out 1; 3.84 / 3.72 hold-out 2 | `evaluation/phase_g/results/gate_summary_dev_final.md` |
| **Hold-out 3, judged once** | **4.28 / 4.08** (main baseline 7.68 / 7.32) | `evaluation/phase_g/final/` |
Auto-decided scanned submissions (no person needed): 4 of 22 scans and 5 of 22 photos on dev (v2: 1 and 1); 2 of 25 on hold-out 3 (baseline 1 of 25). The clean scan D6 now reaches 제출 가능 without a reviewer; D9 (scanned student documents) still needs two confirmations.

## Honest limits
- **Fictional documents** on a few real layouts; digital extraction fit those layouts once already (63 % on the first hold-out, fixed in D2). A **real-document pilot is still to come**.
- Residual risks: the H14 case (a misread repeated identically on several documents corroborates itself when no application value exists) remains an **owner-accepted residual**: 1 false auto-accept and 1 false 제출 가능 in the 1,523 hold-out 2 injections, none on hold-out 3; no special-case code was added for it.
- Hold-out set 3 was judged **once** on the Phase G build. A raw OCR capture of it had been logged on 2026-10-06 and was never scored; its OCR cache was reused (OCR does not depend on the code under test).
- Digital PDFs are no longer trusted blindly: invisible, white-on-white, tiny and covered text is ignored and flagged. Not covered: forged but visible content, and authenticity in general.
- No authentication or access control; tested on SQLite only (PostgreSQL is configured in Docker Compose but not tested this phase); the admin app is an empty shell.
- OCR scans take about 16 s per page on this Mac (CPU); digital documents ~0.1 s per submission.
