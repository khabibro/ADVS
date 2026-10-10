# ADVS progress report, November 2026 (second midterm) — TEMPLATE

Status of every section: **PENDING** unless stated. Do not fill a section with a number that was not measured. Cite the source file or run for every number, with its denominator (n) and, for any "0 failures" claim, the 95 % upper bound (rule of three, ≈ 3/n). Format required by the course for a midterm presentation: project analysis and design, progress, issues and their solutions, schedule (`종합설계프로젝트1 강의소개자료`, slide 6).

## 1. October baseline and progress
- Baseline build: tag `midterm-demo-v2` (frozen). **Known at this date:** see `evaluation/phase_f/TECHNICAL_AUDIT.md` and `results/denominators.txt`. PENDING: what changed since October, by task ID (`docs/planning/ROADMAP.md` §4).
- Mentor meetings held and decisions (the course asks for weekly meetings and minutes with photos): PENDING.

## 2. Extraction error analysis
- Error counts per cause (image quality, text recognition, layout parsing, field mapping, verification logic, annotation): PENDING.
- `university_name` on scanned student documents: before / after (baseline 21/58 scans, 24/58 photos): PENDING.
- PDF text-layer trust check: manipulation tests passed / total, false rejects on genuine digital files (must be 0): PENDING.

## 3. Evaluation dataset and methodology
- Physical corpus: number of documents by type and capture condition, annotation process, agreement between annotators: PENDING.
- Real-document pilot (read-only, counts only), authorisation status: PENDING.
- Judgement sets used and how often (hold-out 3 for D3, once): PENDING.
- Metric definitions as in `evaluation/phase_f/EVALUATION_PROTOCOL.md`: unchanged unless stated.

## 4. D3 result
- Acceptance table, false READY and false auto-accept with n and bounds, burden numbers, merge decision: PENDING.

## 5. OCR versus VLM feasibility (only if attempted)
- Thresholds fixed **before** the experiment (ε for joint errors, minimum improvement, latency budget): PENDING — write them here first.
- Environment, model revision, hardware: PENDING.
- Per-reader and hybrid metrics, error-correlation table, failure cases: PENDING.
- If not attempted: reason (hardware, time, data) and what was improved instead: PENDING.

## 6. Decision and rationale
Proceed / defer / reject integration of PaddleOCR-VL, with the evidence for the decision: PENDING.

## 7. Remaining risks and next steps
PENDING (start from `docs/planning/ROADMAP.md` §7).
