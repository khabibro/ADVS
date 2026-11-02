# Current UCWIT 2026 results

Use this file and `paper/PAPER_SUMMARY.md` as the source for the next midterm deck. Paper numbers are reproduced exactly. The result ledger cited below is read from commit `431aaf1` (`FINAL_RESULTS_2026-11-03.md`); the `real-docs-v6` tag identifies the final code, but does not contain that ledger file. Stage metrics and the 2,615-field review-cause percentages appear in the paper and are not repeated in the final-results ledger, so they are marked paper-reported rather than independently corroborated there.

## Data split

| Dataset | Development | Validation | Total | Source |
|---|---:|---:|---:|---|
| Students | Fresh 54 + seed A 27 = 81 | Seed B 27 | 108 valid | Final results §opening; paper Table 2 |
| Business | F21 38 valid | RS 38 valid | 78 valid + 2 multi-page never Ready | Final results §opening; paper Table 2 |

Student negatives: 14, all not Ready. Business invalid cases N1–N4 and N6: 0 Ready. N5 duplicate uploads are duplicate notices, not negatives. Paper Table 2 reports 95 business submissions as never Ready; the final-results ledger does not independently state that total. Sources: paper Table 2; final results §2 clarifies negative-case status and N5 handling.

## Paper evaluation numbers

| Result | Value | Paper location | Final-results support |
|---|---:|---|---|
| Synthetic development field accuracy | 99.7% | §5.1, Table 3 | Not restated in final-results ledger |
| Synthetic held-out 1 field accuracy | 99.2% | §5.1, Table 3 | Not restated in final-results ledger |
| Real fields, OCR stage | 95.8% of 1,972 | §5.1, Table 3 | Not restated in final-results ledger |
| Real fields, extraction | 79.9% of 1,972 | §5.1, Table 3 | Not restated in final-results ledger |
| Table 3 field rows | Student photo 300; student scan 760; business photo 232; business scan 672; other 8 | §5.1, Table 3 | Not restated in final-results ledger |
| Business never-Ready submissions | 95 | Table 2 | Paper-reported; not separately counted in final-results ledger |
| Fields not automatically accepted before improvements | 2,615 | §5.2 | Ledger has a different review-category table; denominator not corroborated |
| Review causes | Field mapping 38.7%; OCR 26.8%; cross-document comparison 23.2%; safety policy 9.3%; classification 2.0% | §5.2 | Not independently corroborated by final-results ledger |
| Business fully automatic, realistic date | 56/78 (71.8%) | Abstract; §5.3; Table 4 | Supported: final results §1, realistic total READY |
| Business at most one confirmation | 66/78 (84.6%) | §5.3; Table 4 | Supported: final results §1 |
| Business strict expiry-date case | 20/78 (25.6%) | Abstract; §5.3 | Supported as 4 dev + 16 validation: final results §1, harness date |
| Business open items | 6.9 → 0.63, averaged over 76 single-file submissions | Abstract; §5.3; Table 4 | Per split values supported: final results §1 (0.55 / 0.71); ledger does not report the pooled 0.63 |
| Student open items | 8.19 → 3.50 | Abstract; §5.3; Table 4 | Per-split development/validation results in final results §1 |
| Student at most one confirmation | 19/108 | §5.3; Table 4 | Supported: final results §1 (17 dev + 2 validation) |
| Student typed-GPA simulation | 17/108 fully automatic | Abstract; §5.3; Table 4 | Supported: final results §1 and §5 |
| Student, no GPA requirement | 19/108 fully automatic | §5.3 | Supported: final results §7 |
| Real-document wrong accepted values / wrong Ready | 0 / 0 | Abstract; §5.4 | Supported: final results §2 |
| Error-injection wrong value / wrong Ready | 1 / 0 across 6,815 | Abstract; §5.4 | Supported: final results §2 |
| “Safe for the decision” cases | 148 | §5.4 | Supported: final results §2 (`robust_wrong`) |
| Manipulated PDFs | 237 files per manipulation type; 0 hidden text read | Evaluation method §4; §5.4 | Supported: final results §2 |

## Before → after development steps

Values below are from the final-results ledger, which defines v4 as the start-of-loop step, v5 as S14, and v6 as S17. Business rows are development / validation. “Realistic” uses the paper’s normal check date; “harness” is the expiry-boundary check date.

| Metric | Start | v4 | v5 | v6 final | Source |
|---|---:|---:|---:|---:|---|
| Student ≤1 confirmation, dev / validation | 0 / 0 | 10 / 0 | 13 / 1 | 17 / 2 | Final results §1 |
| Student ≤2 confirmations, dev / validation | 0 / 0 | 10 / 0 | 13 / 1 | 17 / 2 | Final results §1 |
| Student open items, dev fresh / seed A | about 8 / about 8 | 3.81 / 4.37 | 3.78 / 4.33 | 3.57 / 3.48 | Final results §1 |
| Student open items, validation | about 8 | 4.19 | 4.15 | 3.37 | Final results §1 |
| Business fully automatic, realistic, dev / validation | 0 / 0 | 23 / 23 | 28 / 26 | 28 / 28 | Final results §1 |
| Business ≤1 confirmation, realistic, dev / validation | 0 / 0 | 25 / 28 | 30 / 32 | 32 / 34 | Final results §1 |
| Business fully automatic, harness, dev / validation | 0 / 0 | 0 / 11 | 4 / 14 | 4 / 16 | Final results §1 |
| Business ≤1 confirmation, harness, dev / validation | Not measured | 23 / 25 | 28 / 29 | 28 / 31 | Final results §1 |
| Business open items, realistic, dev / validation | 6.90 (all) | 1.18 / 1.29 | 0.66 / 0.82 | 0.55 / 0.71 | Final results §1 |
| Business READY / ≤1 confirmation, realistic, total | 0 / 0 | 46 / 53 | 54 / 62 | 56 / 66 | Final results §1 |

Applicant-entered GPA is a separate v6 simulation, not the default final policy: 17/108 student submissions fully automatic (15 development, 2 validation), 0 wrong. Source: final results §1 and §5.

## Review-category counts by version

This is the final-results ledger’s count table for valid real submissions. It is distinct from the paper §5.2 pre-improvement field-denominator percentages above.

| Category | Student v4 / v5 / final | Business v4 / v5 / final | Source |
|---|---:|---:|---|
| C1 OCR recognition | 307 / 293 / 246 | 49 / 28 / 24 | Final results §4 |
| C2 field mapping | 62 / 62 / 62 | 249 / 249 / 249 | Final results §4 |
| C3 cross-document comparison | 198 / 208 / 208 | 5 / 5 / 5 | Final results §4 |
| C4 classification | 8 / 8 / 8 | 0 / 0 / 0 | Final results §4 |
| C5 safety policy | 101 / 101 / 101 | 56 / 56 / 56 | Final results §4 |

## Safety and scope

- Real lanes: 0 wrong auto-accepted values and 0 false Ready decisions. Student negatives (14) and business N1–N4/N6 were never Ready. N5 duplicates are ignored and not negatives. Source: final results §2.
- Synthetic error injection: 6,815 cases across development and three hold-outs; 1 wrong confirmed value, 0 false Ready decisions; 148 decision-robust acceptances with correct verdicts. Source: final results §2.
- Manipulated PDFs: 237 copies per each of four manipulation types; 0 hidden tokens read and 0 pages still trusted. Source: final results §2.
- Limits: a few original student documents and one business per split; compressed photos; GPA entry is simulated; final GPA-setting injection runs are development-only; OCR was cached; cross-document checks cannot detect a consistently forged set. Source: paper §§4, 6; final results §6.
