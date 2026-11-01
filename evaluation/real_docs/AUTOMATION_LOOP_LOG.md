# Automation loop log (masked)

Branch `auto/real-automation` (from `fix/orientation-issue-date`, gated tip). Counts, categories, reason codes and field names only; no document values.
Measurement: `run_real.py --ocr-cache` (OCR read once, replayed afterwards), `loop_score.py` (READY, correct READY, verification issues per valid submission), `review_categories.py`.
Development: student fresh G0–G5, G0b, seed A, real pair; business F21. Validation (aggregate only, failures not read): student seed B; business RS.

## Scoreboard (correct 제출 가능 among valid submissions)

| cycle | commit | student dev | student validation | business dev | business validation | wrong READY | negatives READY |
|---|---|---|---|---|---|---|---|
| start (gated tip) | d9c6c2b | 0/81 | 0/27 | 0/40 | 0/38 | 0 | 0 |

## Cycle 0: baseline and how the loop is measured

- Valid submissions that are not READY have, on average, 7.65 verification issues (student 8.19, business 6.9). These are the real blockers: only fields a rule uses can block (`used_by_rules`), so decision-relevance already holds; the earlier "8.47 blocking fields" counted every gold field.
- Business dev (F21) valid submissions: 5.3 blocking rule-used fields each. Main reasons: company/workplace name disagrees with another document (86 field cases: legal-form or shortened notation), `valid_until` near the decision boundary (34) and without independent confirmation (32+).
- **Test-design observation:** the harness check date of the G0 valid business submissions equals the last valid day of the 국세 납세증명서 (0 days) and is 13 days before the 4대보험 expiry. That is a boundary case by construction, so a refusal is correct. A second, realistic check date (a few days after issue) is added as a separate dev run; the original definition is kept and reported too.
- Harness change (no application code): `--ocr-cache` makes a cycle minutes instead of hours.

## Owner-decision proposals

(none yet)
