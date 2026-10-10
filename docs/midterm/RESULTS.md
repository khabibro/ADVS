# ADVS — Midterm results (2026-10-14)

**AI 기반 행정 제출서류 분석 및 자동 점검 시스템 (ADVS).** ADVS reads Korean administrative documents (embedded PDF text, or OCR for scans and photos), classifies them, extracts fields with their evidence, and checks a submission against a workflow checklist. It answers 제출 가능 / 보완 필요 / 확인 필요 with a reason per issue; a person confirms only the values the system cannot confirm itself. 제출 가능 means "no blocking issue found in the configured pre-check", not official approval.

All numbers: **fictional test documents** built on the layouts of a few real samples, run through the real pipeline by scripts. Sources are repo paths; "dev" = `test_variants` (22 sets × digital/scanned/images) and hold-out set 1 (used as development data after Phase D); hold-out 2 was judged once.

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
| Human review of unconfirmed values | implemented | demo D6 |
| Official verification (National Tax Service API, issuance numbers) | planned | `ROADMAP.md` |
| Authentication, privacy controls, audit log | planned | not built |

## Safety (re-checked: 555 backend tests pass (re-run 2026-10-10 on the v2 branch); rehearsal 3/3 runs)
| Measure | Result (events / n) | 95 % upper bound | Source |
|---|---|---|---|
| False 제출 가능, submissions whose correct status is not READY, development + hold-outs 1–2, per input type | **0 / 40** (12 + 14 + 14; the same 12–14 scenario types re-instantiated) | 7.5 % (about 21 % counting each scenario type once) | `evaluation/phase_f/results/denominators.txt` |
| False 제출 가능, dev data (all sets, all versions) | **0** | see the row above | `evaluation/phase_d2/B2_D2_dev_report.md`, `B2_D2_holdout_report.md` |
| False 제출 가능, hold-out 2 (judged once, before the final policy change) | **0** (included in the 40) | | `evaluation/phase_d2/PHASE_D2_REPORT.md` §6 |
| False 제출 가능, injected OCR errors E1–E12 | **0 / 474** (dev) and **0 / 666** (hold-out 1) | 0.63 % and 0.45 % (cases share their base documents: optimistic) | `B2_D2_inj_dev.md`, `B2_D2_inj_holdout.md` |
| Wrong auto-accepted values, same runs (incl. the common-mode variants) | **0** | same | same |
| Wrong values acted on, hold-out 2 | 0 | | `PHASE_D2_REPORT.md` §6 |

These bounds describe the **synthetic** test data only; the real-world false-제출-가능 rate is not measured and cannot be stated.

## Accuracy
| Measure | Dev | Hold-out | Source |
|---|---|---|---|
| Digital extraction, fields correct | 240/240 | 275/275 (set 1), 275/275 (set 2, judged once) | `B2_D2_dev_report.md`, `B2_D2_holdout_report.md`, `PHASE_D2_REPORT.md` §6 |
| Per type, hold-out 2 (BR / SME / tax / social / enrolment / transcript) | – | 28/28, 56/56, 42/42, 41/41, 48/48, 60/60 | `PHASE_D2_REPORT.md` §6 |
| Classification (all versions) | 100 % match (incl. 3 look-alike sets → UNKNOWN) | digital 79/79, scanned 79/79, images 78/79 (set 1) | `B2_D2_dev_report.md` §2, `B2_D2_holdout_report.md` |
| Scanned / photo fields correct, wrong | 228 and 230 of 240, 0 wrong | 254 and 258 of 275, 0 wrong | same reports §3 |

## Automation (OCR scans and photos; review burden = fields a person must still check, per submission)
| Stage | Scanned / images | Source |
|---|---|---|
| Baseline B0 (every OCR field to a person) | 11.64 / 11.64 | `evaluation/phase_d/PHASE_D_REPORT.md` §3 |
| Phase D (before D2 safety fixes) | 3.82 / 3.55 dev | `PHASE_D_REPORT.md` §4 |
| **D2 final (this demo build, on `main`)** | **7.23 / 6.59 dev** (−38 % / −43 %); 7.40 / 6.84 hold-out 1 | `B2_D2_dev_report.md` §5, `PHASE_D2_REPORT.md` §11 |
| D3 (unmerged branch, **not in the demo**) | 3.82 / 3.14 dev, total; decision-blocking 2.68 / 2.09 | `phase-d3/internal-automation:evaluation/phase_d3/D3_configs.md` |
On the D2 final build, decision-blocking vs total fields (D3 measurement of the same policy, dev): 5.41 / 4.82 vs 7.23 / 6.59 (same file). Digital documents: 0.91 fields per submission. Auto-accepted OCR fields: 40.4 % scanned / 46.2 % images (dev). The safety policy of D2 cost about 3 fields per scan (dates and GPA now always need a person) — a deliberate, owner-approved trade.

## Honest limits
- **Fictional documents** on a few real layouts; digital extraction fit those layouts once already (63 % on the first hold-out, fixed in D2). A **real-document pilot is still to come**.
- Residual risks: a misread repeated identically on several documents can corroborate itself when no application value exists (the H14-type case, `PHASE_D_REPORT.md` §5, §8; never 제출 가능 in any measured run). D3's extended injection suite (E13–E18, unmerged branch) found **1 false auto-accept** under the D2 policy (case E3c-both on hold-out-2 data, 0 false 제출 가능; `D3_configs.md`).
- Hold-out set 3 has **not been judged** — gap (a raw OCR capture was logged on 2026-10-06 but never scored). The final D2 policy was not re-judged on hold-out 2 (used up); it is stricter than what was judged.
- **A PDF's text layer is trusted without checking** (verified probe: hidden text overrides what the page shows; `evaluation/phase_f/results/text_layer_probe.txt`) — recorded for November.
- No authentication or access control; tested on SQLite only (PostgreSQL is configured in Docker Compose but not tested this phase); the admin app is an empty shell.
- OCR scans take about 16 s per page on this Mac (CPU); digital documents ~0.1 s per submission.
