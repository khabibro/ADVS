# D2 injection results — B0-D2 dev

- Frozen Phase D suite SHA-256 `a81e4ef2ebfc97c3bf2646952b2c3a532e2cab33b4ecace8365cc9c685a484fd`; D2 suite SHA-256 `08229da0419528164cd863a29a449016febe1bae99369d99214130a9e59f3f57`; scorer v2 `49674a9c03e464310cda0278782062e1a4b996e334ff8d8cbdc78d10b5ad2594`
- corpus `dev`, git `d78db60`, project values `False`, cases 474

| Injection | Cases | False auto-accept | False READY | READY | NEEDS_CORRECTION | REVIEW_REQUIRED | E10: classified as a supported type |
|---|---|---|---|---|---|---|---|
| E1 | 42 | 0 | 0 | 0 | 8 | 34 | - |
| E10 | 24 | 8 | 8 | 8 | 0 | 16 | 8 |
| E11-both | 16 | 8 | 4 | 4 | 0 | 12 | - |
| E12-both | 6 | 6 | 0 | 0 | 0 | 6 | - |
| E2 | 22 | 0 | 0 | 0 | 4 | 18 | - |
| E3 | 65 | 0 | 0 | 0 | 12 | 53 | - |
| E4 | 44 | 0 | 0 | 0 | 8 | 36 | - |
| E5 | 54 | 0 | 0 | 0 | 6 | 48 | - |
| E6 | 4 | 0 | 0 | 0 | 0 | 4 | - |
| E6-both | 4 | 1 | 0 | 0 | 0 | 4 | - |
| E7 | 70 | 0 | 0 | 0 | 12 | 58 | - |
| E8 | 18 | 0 | 0 | 0 | 0 | 18 | - |
| E8-both | 18 | 18 | 0 | 0 | 0 | 18 | - |
| E9 | 32 | 0 | 0 | 0 | 4 | 28 | - |
| E9-both | 32 | 4 | 0 | 0 | 4 | 28 | - |

**Totals: false auto-accept 45, false READY 12.**

## Leaks

| Case | status | detail |
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
| B05/scanned:E11-valid_until+0:B05-3_납세증명서_스캔.pdf | REVIEW_REQUIRED | valid_until: 2026-08-31→2026-10-05 |
| B05/scanned:E11-valid_until+1:B05-3_납세증명서_스캔.pdf | REVIEW_REQUIRED | valid_until: 2026-08-31→2026-10-06 |
| B05/scanned:E11-valid_until+3:B05-3_납세증명서_스캔.pdf | REVIEW_REQUIRED | valid_until: 2026-08-31→2026-10-08 |
| B05/scanned:E11-valid_until+7:B05-3_납세증명서_스캔.pdf | REVIEW_REQUIRED | valid_until: 2026-08-31→2026-10-12 |
| B05/images:E11-valid_until+0:B05-3_납세증명서_사진.webp | READY | valid_until: 2026-08-31→2026-10-05 |
| B05/images:E11-valid_until+1:B05-3_납세증명서_사진.webp | READY | valid_until: 2026-08-31→2026-10-06 |
| B05/images:E11-valid_until+3:B05-3_납세증명서_사진.webp | READY | valid_until: 2026-08-31→2026-10-08 |
| B05/images:E11-valid_until+7:B05-3_납세증명서_사진.webp | READY | valid_until: 2026-08-31→2026-10-12 |
| S03/scanned:E12-gpa->3.00:S03-2_성적증명서_스캔.pdf | REVIEW_REQUIRED | gpa: 2.70→3 |
| S03/scanned:E12-gpa->3.05:S03-2_성적증명서_스캔.pdf | REVIEW_REQUIRED | gpa: 2.70→3.05 |
| S03/scanned:E12-gpa->3.10:S03-2_성적증명서_스캔.pdf | REVIEW_REQUIRED | gpa: 2.70→3.1 |
| S03/images:E12-gpa->3.00:S03-2_성적증명서_사진.png | REVIEW_REQUIRED | gpa: 2.70→3 |
| S03/images:E12-gpa->3.05:S03-2_성적증명서_사진.png | REVIEW_REQUIRED | gpa: 2.70→3.05 |
| S03/images:E12-gpa->3.10:S03-2_성적증명서_사진.png | REVIEW_REQUIRED | gpa: 2.70→3.1 |
| B11/scanned:E10:B11-3_지방세납세증명서_스캔.pdf:지방세->지방새 | READY | type=NATIONAL_TAX_PAYMENT_CERTIFICATE acted=['business_registration_number', 'company_name', 'valid_until'] |
| B11/scanned:E10:B11-3_지방세납세증명서_스캔.pdf:지방세->지빙세 | READY | type=NATIONAL_TAX_PAYMENT_CERTIFICATE acted=['business_registration_number', 'company_name', 'valid_until'] |
| B11/scanned:E10:B11-3_지방세납세증명서_스캔.pdf:지방세->X방세 | READY | type=NATIONAL_TAX_PAYMENT_CERTIFICATE acted=['business_registration_number', 'company_name', 'valid_until'] |
| B11/scanned:E10:B11-3_지방세납세증명서_스캔.pdf:지방세->지세 | READY | type=NATIONAL_TAX_PAYMENT_CERTIFICATE acted=['business_registration_number', 'company_name', 'valid_until'] |
| B11/images:E10:B11-3_지방세납세증명서_사진.webp:지방세->지방새 | READY | type=NATIONAL_TAX_PAYMENT_CERTIFICATE acted=['business_registration_number', 'company_name', 'valid_until'] |
| B11/images:E10:B11-3_지방세납세증명서_사진.webp:지방세->지빙세 | READY | type=NATIONAL_TAX_PAYMENT_CERTIFICATE acted=['business_registration_number', 'company_name', 'valid_until'] |
| B11/images:E10:B11-3_지방세납세증명서_사진.webp:지방세->X방세 | READY | type=NATIONAL_TAX_PAYMENT_CERTIFICATE acted=['business_registration_number', 'company_name', 'valid_until'] |
| B11/images:E10:B11-3_지방세납세증명서_사진.webp:지방세->지세 | READY | type=NATIONAL_TAX_PAYMENT_CERTIFICATE acted=['business_registration_number', 'company_name', 'valid_until'] |
