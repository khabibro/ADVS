# Injection results — S6 injection proj

- Suite SHA-256 `a81e4ef2ebfc97c3bf2646952b2c3a532e2cab33b4ecace8365cc9c685a484fd`, seed 20261005, git `09966c8`, strategy `S6`, project values `True`
- Scorer v2 SHA-256 `49674a9c03e464310cda0278782062e1a4b996e334ff8d8cbdc78d10b5ad2594`; cases: 428

`planned` = enumerated cases; `exercised` = the un-injected control run read the target field correctly (so the injection is meaningful); `effective` = the pipeline actually read the injected wrong value.

| Injection | Planned | Exercised | Effective (wrong value read) | False auto-accept | False READY | Not auto-accepted | READY | NEEDS_CORRECTION | REVIEW_REQUIRED |
|---|---|---|---|---|---|---|---|---|---|
| E1-one | 44 | 24 | 24 | 0 | 0 | 24 | 0 | 20 | 4 |
| E2-all | 22 | 14 | 14 | 0 | 0 | 14 | 0 | 11 | 3 |
| E3-all | 22 | 14 | 14 | 0 | 0 | 14 | 0 | 11 | 3 |
| E3-one | 44 | 26 | 26 | 0 | 0 | 26 | 0 | 22 | 4 |
| E4-one | 44 | 21 | 0 | 0 | 0 | 21 | 0 | 17 | 4 |
| E5-all | 20 | 7 | 7 | 0 | 0 | 7 | 0 | 0 | 7 |
| E5-one | 40 | 23 | 23 | 0 | 0 | 23 | 0 | 0 | 23 |
| E6-one | 4 | 3 | 2 | 0 | 0 | 3 | 0 | 2 | 1 |
| E6-one-both | 4 | 3 | 2 | 1 | 0 | 2 | 0 | 2 | 1 |
| E7-all | 24 | 24 | 24 | 0 | 0 | 24 | 0 | 4 | 20 |
| E7-one | 48 | 45 | 45 | 0 | 0 | 45 | 0 | 35 | 10 |
| E8-one | 18 | 7 | 7 | 0 | 0 | 7 | 0 | 0 | 7 |
| E8-one-both | 18 | 7 | 7 | 7 | 0 | 0 | 0 | 0 | 7 |
| E9-one | 38 | 19 | 19 | 0 | 0 | 19 | 0 | 0 | 19 |
| E9-one-both | 38 | 19 | 19 | 7 | 0 | 12 | 0 | 0 | 19 |

Totals: planned 428, exercised 256, effective 233.

**Totals: false auto-accept 15, false READY 0.**

## Leaks

| Case | status | injected → accepted value |
|---|---|---|
| B05/scanned:E6-valid_until:B05-3_납세증명서_스캔.pdf:both | NEEDS_CORRECTION | valid_until: 2026-08-31→2028-08-31 |
| S01/scanned:E9:S01-1_재학증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2023123456→2023128456 |
| S01/images:E8:S01-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S02/images:E8:S02-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S03/scanned:E9:S03-1_재학증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2023123456→2073123456 |
| S03/images:E9:S03-1_재학증명서_사진.jpg:both | REVIEW_REQUIRED | student_id: 2023123456→2023128456 |
| S05/scanned:E9:S05-1_재학증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2023123456→2023123466 |
| S05/images:E8:S05-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S06/images:E9:S06-1_재학증명서_사진.jpg:both | REVIEW_REQUIRED | student_id: 2023123456→2023123458 |
| S08/scanned:E9:S08-1_재학증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2023123456→7023123456 |
| S08/images:E8:S08-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S09/images:E8:S09-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S09/images:E9:S09-2_성적증명서_사진.png:both | REVIEW_REQUIRED | student_id: 2023123456→2023123466 |
| S10/scanned:E8:S10-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S10/images:E8:S10-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
