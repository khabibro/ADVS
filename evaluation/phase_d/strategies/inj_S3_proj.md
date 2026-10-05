# Injection results — S3 injection proj

- Suite SHA-256 `a81e4ef2ebfc97c3bf2646952b2c3a532e2cab33b4ecace8365cc9c685a484fd`, seed 20261005, git `09966c8`, strategy `S3`, project values `True`
- Scorer v2 SHA-256 `49674a9c03e464310cda0278782062e1a4b996e334ff8d8cbdc78d10b5ad2594`; cases: 428

`planned` = enumerated cases; `exercised` = the un-injected control run read the target field correctly (so the injection is meaningful); `effective` = the pipeline actually read the injected wrong value.

| Injection | Planned | Exercised | Effective (wrong value read) | False auto-accept | False READY | Not auto-accepted | READY | NEEDS_CORRECTION | REVIEW_REQUIRED |
|---|---|---|---|---|---|---|---|---|---|
| E1-one | 44 | 24 | 24 | 0 | 0 | 24 | 0 | 18 | 6 |
| E2-all | 22 | 14 | 14 | 0 | 0 | 14 | 0 | 10 | 4 |
| E3-all | 22 | 14 | 14 | 0 | 0 | 14 | 0 | 10 | 4 |
| E3-one | 44 | 26 | 26 | 0 | 0 | 26 | 0 | 19 | 7 |
| E4-one | 44 | 21 | 0 | 0 | 0 | 21 | 0 | 15 | 6 |
| E5-all | 20 | 7 | 7 | 6 | 0 | 1 | 0 | 6 | 1 |
| E5-one | 40 | 23 | 23 | 0 | 0 | 23 | 0 | 0 | 23 |
| E6-one | 4 | 3 | 2 | 0 | 0 | 3 | 0 | 2 | 1 |
| E6-one-both | 4 | 3 | 2 | 0 | 0 | 3 | 0 | 2 | 1 |
| E7-all | 24 | 24 | 24 | 22 | 0 | 2 | 0 | 22 | 2 |
| E7-one | 48 | 45 | 45 | 0 | 0 | 45 | 0 | 4 | 41 |
| E8-one | 18 | 7 | 7 | 0 | 0 | 7 | 0 | 0 | 7 |
| E8-one-both | 18 | 7 | 7 | 0 | 0 | 7 | 0 | 0 | 7 |
| E9-one | 38 | 19 | 19 | 0 | 0 | 19 | 0 | 0 | 19 |
| E9-one-both | 38 | 19 | 19 | 0 | 0 | 19 | 0 | 0 | 19 |

Totals: planned 428, exercised 256, effective 233.

**Totals: false auto-accept 28, false READY 0.**

## Leaks

| Case | status | injected → accepted value |
|---|---|---|
| B01/scanned:E7-all | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 테스트상자; company_name: 테스트상사→주식회사 테스트상자; company_name: 테스트상사→주식회사 테스트상자 |
| B01/images:E7-all | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사테스드상사; company_name: 테스트상사→주식회사 테스드상사; company_name: 테스트상사→주식회사테스드상사; company_name: 테스트상사→주식회사테스드상사 |
| B02/scanned:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→(주)테스트성사; company_name: 테스트상사→(주)테스트성사; workplace_name: 테스트상사→테스트성사(주) |
| B02/images:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→(주)테스드상사; company_name: 테스트상사→(주)테스드상사; workplace_name: 테스트상사→테스드상사(주); company_name: 테스트상사→주식회사테스드상사 |
| B04/scanned:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테스트상자; workplace_name: 테스트상사→주식회사 테스트상자; company_name: 테스트상사→주식회사 테스트상자 |
| B04/images:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테스트성사; workplace_name: 테스트상사→주식회사 테스트성사; company_name: 테스트상사→주식회사테스트성사; company_name: 테스트상사→주식회사 테스트성사 |
| B05/scanned:E7-all | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 테소트상사; company_name: 테스트상사→주식회사 테소트상사; company_name: 테스트상사→주식회사테소트상사 |
| B05/images:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테스드상사; company_name: 테스트상사→주식회사 테스드상사; company_name: 테스트상사→주식회사테스드상사; workplace_name: 테스트상사→주식회사 테스드상사 |
| B06/scanned:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테소트상사; workplace_name: 테스트상사→주식회사 테소트상사; company_name: 테스트상사→주식회사 테소트상사 |
| B06/images:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테스트상자; workplace_name: 테스트상사→주식회사테스트상자; company_name: 테스트상사→주식회사테스트상자; company_name: 테스트상사→주식회사 테스트상자 |
| B07/scanned:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 데스트상사; company_name: 테스트상사→주식회사 데스트상사; workplace_name: 테스트상사→주식회사 데스트상사 |
| B07/images:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테소트상사; company_name: 테스트상사→주식회사 테소트상사; company_name: 테스트상사→주식회사테소트상사; workplace_name: 테스트상사→주식회사 테소트상사 |
| B08/scanned:E7-all | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 테스드상사; company_name: 테스트상사→주식회사 테스드상사; company_name: 테스트상사→주식회사 테스드상사 |
| B08/images:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테스트성사; company_name: 테스트상사→주식회사 테스트성사; workplace_name: 테스트상사→주식회사 테스트성사 |
| B09/scanned:E7-all | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 테스트상자; company_name: 테스트상사→주식회사테스트상자; company_name: 테스트상사→주식회사테스트상자 |
| B09/images:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 데스트상사; company_name: 테스트상사→주식회사데스트상사; company_name: 테스트상사→주식회사데스트상사; workplace_name: 테스트상사→주식회사 데스트상사; company_name: 테스트상사→주식회사데스트상사 |
| B10/scanned:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테소트상사; company_name: 테스트상사→주식회사 테소트상사; workplace_name: 테스트상사→주식회사 테소트상사; company_name: 테스트상사→주식회사테소트상사 |
| B10/images:E7-all | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 데스트상사; company_name: 테스트상사→주식회사데스트상사; company_name: 테스트상사→주식회사 데스트상사; company_name: 테스트상사→주식회사데스트상사 |
| B11/scanned:E7-all | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 테소트상사; company_name: 테스트상사→주식회사테소트상사; company_name: 테스트상사→주식회사 테소트상사 |
| B11/images:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테스트상자; company_name: 테스트상사→주식회사 테스트상자; workplace_name: 테스트상사→주식회사 테스트상자 |
| B12/scanned:E7-all | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 데스트상사; company_name: 테스트상사→주식회사 데스트상사; company_name: 테스트상사→주식회사데스트상사; company_name: 테스트상사→주식회사데스트상사; company_name: 테스트상사→주식회사데스트상사 |
| B12/images:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테스트상자; workplace_name: 테스트상사→주식회사 테스트상자; company_name: 테스트상사→주식회사테스트상자; company_name: 테스트상사→주식회사테스트상자; company_name: 테스트상사→주식회사 테스트상자 |
| S01/images:E5-all | NEEDS_CORRECTION | student_name: 김테스트→김테스드; student_name: 김테스트→김테스드 |
| S02/images:E5-all | NEEDS_CORRECTION | student_name: 김테스트→김데스트; student_name: 김테스트→김데스트 |
| S08/images:E5-all | NEEDS_CORRECTION | student_name: 김테스트→김테스드; student_name: 김테스트→김테스드 |
| S09/images:E5-all | NEEDS_CORRECTION | student_name: 김테스트→김데스트; student_name: 김테스트→김데스트 |
| S10/scanned:E5-all | NEEDS_CORRECTION | student_name: 김테스트→김테스드; student_name: 김테스트→김테스드 |
| S10/images:E5-all | NEEDS_CORRECTION | student_name: 김테스트→길테스트; student_name: 김테스트→길테스트 |
