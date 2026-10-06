# D2 injection results — B1-D2 holdout

- Frozen Phase D suite SHA-256 `a81e4ef2ebfc97c3bf2646952b2c3a532e2cab33b4ecace8365cc9c685a484fd`; D2 suite SHA-256 `08229da0419528164cd863a29a449016febe1bae99369d99214130a9e59f3f57`; scorer v2 `49674a9c03e464310cda0278782062e1a4b996e334ff8d8cbdc78d10b5ad2594`
- corpus `holdout`, git `d2848b6`, project values `False`, cases 666

| Injection | Cases | False auto-accept | False READY | READY | NEEDS_CORRECTION | REVIEW_REQUIRED | E10: classified as a supported type |
|---|---|---|---|---|---|---|---|
| E1 | 51 | 0 | 0 | 0 | 6 | 45 | - |
| E10 | 24 | 0 | 0 | 0 | 0 | 24 | 4 |
| E11-both | 16 | 0 | 0 | 0 | 0 | 16 | - |
| E12-both | 6 | 0 | 0 | 0 | 0 | 6 | - |
| E2 | 26 | 0 | 0 | 0 | 3 | 23 | - |
| E3 | 77 | 0 | 0 | 0 | 9 | 68 | - |
| E3c | 78 | 0 | 0 | 0 | 9 | 69 | - |
| E3c-both | 52 | 0 | 0 | 0 | 6 | 46 | - |
| E4 | 51 | 0 | 0 | 0 | 6 | 45 | - |
| E5 | 60 | 0 | 0 | 0 | 0 | 60 | - |
| E6 | 4 | 0 | 0 | 0 | 0 | 4 | - |
| E6-both | 4 | 1 | 0 | 0 | 0 | 4 | - |
| E7 | 83 | 0 | 0 | 0 | 9 | 74 | - |
| E8 | 20 | 0 | 0 | 0 | 0 | 20 | - |
| E8-both | 20 | 10 | 0 | 0 | 0 | 20 | - |
| E9 | 36 | 0 | 0 | 0 | 0 | 36 | - |
| E9-both | 36 | 5 | 0 | 0 | 0 | 36 | - |

**Totals: false auto-accept 16, false READY 0.**

## Leaks

| Case | status | detail |
|---|---|---|
| B05/scanned:E6-valid_until:B05-3_납세증명서_스캔.pdf:both | REVIEW_REQUIRED | valid_until: 2026-09-07→2028-09-07 |
| S01/scanned:E8:S01-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S01/images:E8:S01-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S02/scanned:E8:S02-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S02/images:E8:S02-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S03/scanned:E9:S03-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2022087654→2022037654 |
| S04/scanned:E8:S04-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | gpa: 3.10→3.8 |
| S04/scanned:E9:S04-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2022087654→7022087654 |
| S04/images:E8:S04-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.10→3.8 |
| S06/scanned:E8:S06-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S06/scanned:E9:S06-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2022087654→2022067654 |
| S06/images:E8:S06-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S09/scanned:E9:S09-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2022087654→2022087664 |
| S09/images:E9:S09-2_성적증명서_사진.png:both | REVIEW_REQUIRED | student_id: 2022087654→2022067654 |
| S10/scanned:E8:S10-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S10/images:E8:S10-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
