# Injection results — S7 injection noproj

- Suite SHA-256 `a81e4ef2ebfc97c3bf2646952b2c3a532e2cab33b4ecace8365cc9c685a484fd`, seed 20261005, git `bf0106c`, strategy `S7`, project values `False`
- Scorer v2 SHA-256 `49674a9c03e464310cda0278782062e1a4b996e334ff8d8cbdc78d10b5ad2594`; cases: 428

`planned` = enumerated cases; `exercised` = the un-injected control run read the target field correctly (so the injection is meaningful); `effective` = the pipeline actually read the injected wrong value.

| Injection | Planned | Exercised | Effective (wrong value read) | False auto-accept | False READY | Not auto-accepted | READY | NEEDS_CORRECTION | REVIEW_REQUIRED |
|---|---|---|---|---|---|---|---|---|---|
| E1-one | 44 | 42 | 42 | 0 | 0 | 42 | 0 | 8 | 34 |
| E2-all | 22 | 22 | 22 | 0 | 0 | 22 | 0 | 4 | 18 |
| E3-all | 22 | 22 | 22 | 0 | 0 | 22 | 0 | 4 | 18 |
| E3-one | 44 | 43 | 43 | 0 | 0 | 43 | 0 | 8 | 35 |
| E4-one | 44 | 44 | 0 | 0 | 0 | 44 | 0 | 8 | 36 |
| E5-all | 20 | 18 | 18 | 0 | 0 | 18 | 0 | 2 | 16 |
| E5-one | 40 | 36 | 36 | 0 | 0 | 36 | 0 | 4 | 32 |
| E6-one | 4 | 4 | 3 | 0 | 0 | 4 | 0 | 0 | 4 |
| E6-one-both | 4 | 4 | 3 | 1 | 0 | 3 | 0 | 0 | 4 |
| E7-all | 24 | 24 | 24 | 0 | 0 | 24 | 0 | 4 | 20 |
| E7-one | 48 | 46 | 46 | 0 | 0 | 46 | 0 | 8 | 38 |
| E8-one | 18 | 18 | 18 | 0 | 0 | 18 | 0 | 0 | 18 |
| E8-one-both | 18 | 18 | 18 | 18 | 0 | 0 | 0 | 0 | 18 |
| E9-one | 38 | 32 | 32 | 0 | 0 | 32 | 0 | 4 | 28 |
| E9-one-both | 38 | 32 | 32 | 4 | 0 | 28 | 0 | 4 | 28 |

Totals: planned 428, exercised 405, effective 359.

**Totals: false auto-accept 23, false READY 0.**

## Leaks

| Case | status | injected → accepted value |
|---|---|---|
| B05/scanned:E6-valid_until:B05-3_납세증명서_스캔.pdf:both | REVIEW_REQUIRED | valid_until: 2026-08-31→2028-08-31 |
| S01/scanned:E8:S01-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S01/images:E8:S01-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S02/scanned:E8:S02-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S02/images:E8:S02-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S03/scanned:E8:S03-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | gpa: 2.70→3.7 |
| S03/images:E8:S03-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 2.70→3.7 |
| S04/scanned:E8:S04-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | gpa: 3.10→3.8 |
| S04/scanned:E9:S04-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2023123456→7023123456 |
| S04/images:E8:S04-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.10→3.8 |
| S04/images:E9:S04-2_성적증명서_사진.png:both | REVIEW_REQUIRED | student_id: 2023123456→2023123455 |
| S05/scanned:E8:S05-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S05/images:E8:S05-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S06/scanned:E8:S06-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S06/images:E8:S06-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S08/scanned:E8:S08-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S08/images:E8:S08-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S09/scanned:E8:S09-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S09/scanned:E9:S09-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2023123456→2823123456 |
| S09/images:E8:S09-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S09/images:E9:S09-2_성적증명서_사진.png:both | REVIEW_REQUIRED | student_id: 2023123456→2023123466 |
| S10/scanned:E8:S10-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S10/images:E8:S10-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
