# Injection results — S1 injection proj

- Suite SHA-256 `a81e4ef2ebfc97c3bf2646952b2c3a532e2cab33b4ecace8365cc9c685a484fd`, seed 20261005, git `bf0106c`, strategy `S1`, project values `True`
- Scorer v2 SHA-256 `49674a9c03e464310cda0278782062e1a4b996e334ff8d8cbdc78d10b5ad2594`; cases: 428

`planned` = enumerated cases; `exercised` = the un-injected control run read the target field correctly (so the injection is meaningful); `effective` = the pipeline actually read the injected wrong value.

| Injection | Planned | Exercised | Effective (wrong value read) | False auto-accept | False READY | Not auto-accepted | READY | NEEDS_CORRECTION | REVIEW_REQUIRED |
|---|---|---|---|---|---|---|---|---|---|
| E1-one | 44 | 42 | 42 | 0 | 0 | 42 | 0 | 13 | 29 |
| E2-all | 22 | 22 | 22 | 0 | 0 | 22 | 0 | 6 | 16 |
| E3-all | 22 | 22 | 22 | 0 | 0 | 22 | 0 | 6 | 16 |
| E3-one | 44 | 43 | 43 | 0 | 0 | 43 | 0 | 15 | 28 |
| E4-one | 44 | 44 | 0 | 0 | 0 | 44 | 0 | 14 | 30 |
| E5-all | 20 | 18 | 18 | 18 | 0 | 0 | 0 | 18 | 0 |
| E5-one | 40 | 36 | 36 | 36 | 0 | 0 | 0 | 36 | 0 |
| E6-one | 4 | 4 | 3 | 1 | 0 | 3 | 0 | 0 | 4 |
| E6-one-both | 4 | 4 | 3 | 1 | 0 | 3 | 0 | 0 | 4 |
| E7-all | 24 | 24 | 24 | 24 | 0 | 0 | 0 | 24 | 0 |
| E7-one | 48 | 46 | 46 | 46 | 0 | 0 | 0 | 46 | 0 |
| E8-one | 18 | 18 | 18 | 18 | 0 | 0 | 0 | 2 | 16 |
| E8-one-both | 18 | 18 | 18 | 18 | 0 | 0 | 0 | 2 | 16 |
| E9-one | 38 | 32 | 32 | 32 | 0 | 0 | 0 | 8 | 24 |
| E9-one-both | 38 | 32 | 32 | 32 | 0 | 0 | 0 | 8 | 24 |

Totals: planned 428, exercised 405, effective 359.

**Totals: false auto-accept 226, false READY 0.**

## Leaks

| Case | status | injected → accepted value |
|---|---|---|
| B01/scanned:E7-one:B01-4_4대사회보험료완납증명서_스캔.pdf | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 데스트상사 |
| B01/scanned:E7-one:B01-2_중소기업확인서_스캔.pdf | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테스드상사 |
| B01/scanned:E7-all | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 테스트상자; company_name: 테스트상사→주식회사 테스트상자; company_name: 테스트상사→주식회사 테스트상자; company_name: 테스트상사→주식회사 테스트상자 |
| B01/images:E7-one:B01-4_4대사회보험료완납증명서_사진.jpg | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사데스트상사 |
| B01/images:E7-one:B01-2_중소기업확인서_사진.png | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테스트상자 |
| B01/images:E7-all | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사테스드상사; company_name: 테스트상사→주식회사 테스드상사; company_name: 테스트상사→주식회사테스드상사; company_name: 테스트상사→주식회사테스드상사 |
| B02/scanned:E7-one:B02-3_납세증명서_스캔.pdf | NEEDS_CORRECTION | company_name: 테스트상사→(주)데스트상사 |
| B02/scanned:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→(주)테스트성사; company_name: 테스트상사→(주)테스트성사; workplace_name: 테스트상사→테스트성사(주) |
| B02/images:E7-one:B02-3_납세증명서_사진.webp | NEEDS_CORRECTION | company_name: 테스트상사→(주)데스트상사 |
| B02/images:E7-one:B02-2_중소기업확인서_사진.png | NEEDS_CORRECTION | company_name: 테스트상사→(주)테스드상사 |
| B02/images:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→(주)테스드상사; company_name: 테스트상사→(주)테스드상사; workplace_name: 테스트상사→테스드상사(주); company_name: 테스트상사→주식회사테스드상사 |
| B03/scanned:E7-one:B03-2_중소기업확인서_스캔.pdf | NEEDS_CORRECTION | company_name: 테스트상사→주식회사데스트상사 |
| B03/scanned:E7-one:B03-3_납세증명서_스캔.pdf | NEEDS_CORRECTION | company_name: 가나다솔루션→주식회사 가나다술루션 |
| B03/scanned:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테스트상자; company_name: 가나다솔루션→주식회사 가나다솔자션; workplace_name: 테스트상사→주식회사 테스트상자; company_name: 테스트상사→주식회사테스트상자 |
| B03/images:E7-one:B03-2_중소기업확인서_사진.png | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테스트상자 |
| B03/images:E7-one:B03-4_4대사회보험료완납증명서_사진.jpg | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 데스트상사 |
| B03/images:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테소트상사; workplace_name: 테스트상사→주식회사 테소트상사; company_name: 가나다솔루션→주식회사가소다솔루션; company_name: 테스트상사→주식회사테소트상사 |
| B04/scanned:E7-one:B04-2_중소기업확인서_스캔.pdf | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테스트성사 |
| B04/scanned:E7-one:B04-1_사업자등록증_스캔.pdf | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테소트상사 |
| B04/scanned:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테스트상자; company_name: 테스트상사→주식회사테스트상자; workplace_name: 테스트상사→주식회사 테스트상자; company_name: 테스트상사→주식회사 테스트상자 |
| B04/images:E7-one:B04-1_사업자등록증_사진.jpg | NEEDS_CORRECTION | company_name: 테스트상사→주식회사데스트상사 |
| B04/images:E7-one:B04-4_4대사회보험료완납증명서_사진.jpg | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 테스드상사 |
| B04/images:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테스트성사; workplace_name: 테스트상사→주식회사 테스트성사; company_name: 테스트상사→주식회사테스트성사; company_name: 테스트상사→주식회사 테스트성사 |
| B05/scanned:E7-one:B05-4_4대사회보험료완납증명서_스캔.pdf | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 테스트성사 |
| B05/scanned:E7-one:B05-3_납세증명서_스캔.pdf | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테스드상사 |
| B05/scanned:E7-all | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 테소트상사; company_name: 테스트상사→주식회사 테소트상사; company_name: 테스트상사→주식회사테소트상사 |
| B05/scanned:E6-valid_until:B05-3_납세증명서_스캔.pdf | REVIEW_REQUIRED | valid_until: 2026-08-31→2028-08-31 |
| B05/scanned:E6-valid_until:B05-3_납세증명서_스캔.pdf:both | REVIEW_REQUIRED | valid_until: 2026-08-31→2028-08-31 |
| B05/images:E7-one:B05-1_사업자등록증_사진.jpg | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테소트상사 |
| B05/images:E7-one:B05-2_중소기업확인서_사진.png | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테스드상사 |
| B05/images:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테스드상사; company_name: 테스트상사→주식회사 테스드상사; company_name: 테스트상사→주식회사테스드상사; workplace_name: 테스트상사→주식회사 테스드상사 |
| B06/scanned:E7-one:B06-1_사업자등록증_스캔.pdf | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테스드상사 |
| B06/scanned:E7-one:B06-4_4대사회보험료완납증명서_스캔.pdf | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 테스드상사 |
| B06/scanned:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테소트상사; workplace_name: 테스트상사→주식회사 테소트상사; company_name: 테스트상사→주식회사 테소트상사 |
| B06/images:E7-one:B06-1_사업자등록증_사진.jpg | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테스트상자 |
| B06/images:E7-one:B06-4_4대사회보험료완납증명서_사진.jpg | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사테스드상사 |
| B06/images:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테스트상자; workplace_name: 테스트상사→주식회사테스트상자; company_name: 테스트상사→주식회사테스트상자; company_name: 테스트상사→주식회사 테스트상자 |
| B07/scanned:E7-one:B07-3_납세증명서_스캔.pdf | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테스트상자 |
| B07/scanned:E7-one:B07-2_중소기업확인서_스캔.pdf | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테소트상사 |
| B07/scanned:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 데스트상사; company_name: 테스트상사→주식회사 데스트상사; workplace_name: 테스트상사→주식회사 데스트상사; company_name: 테스트상사→주식회사데스트상사 |
| B07/images:E7-one:B07-3_납세증명서_사진.webp | NEEDS_CORRECTION | company_name: 테스트상사→주식회사데스트상사 |
| B07/images:E7-one:B07-2_중소기업확인서_사진.png | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테소트상사 |
| B07/images:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테소트상사; company_name: 테스트상사→주식회사 테소트상사; company_name: 테스트상사→주식회사테소트상사; workplace_name: 테스트상사→주식회사 테소트상사 |
| B08/scanned:E7-one:B08-3_4대사회보험료완납증명서_스캔.pdf | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 테스드상사 |
| B08/scanned:E7-one:B08-2_납세증명서_스캔.pdf | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테소트상사 |
| B08/scanned:E7-all | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 테스드상사; company_name: 테스트상사→주식회사 테스드상사; company_name: 테스트상사→주식회사 테스드상사 |
| B08/images:E7-one:B08-2_납세증명서_사진.png | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테소트상사 |
| B08/images:E7-one:B08-1_중소기업확인서_사진.jpg | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테스트상자 |
| B08/images:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테스트성사; company_name: 테스트상사→주식회사 테스트성사; workplace_name: 테스트상사→주식회사 테스트성사 |
| B09/scanned:E7-one:B09-4_4대사회보험료완납증명서_스캔.pdf | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 테스드상사 |
| B09/scanned:E7-one:B09-3_납세증명서_스캔 (사본).pdf | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테소트상사 |
| B09/scanned:E7-all | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 테스트상자; company_name: 테스트상사→주식회사테스트상자; company_name: 테스트상사→주식회사 테스트상자; company_name: 테스트상사→주식회사테스트상자 |
| B09/images:E7-one:B09-2_중소기업확인서_사진.png | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테스트상자 |
| B09/images:E7-one:B09-3_납세증명서_사진.webp | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테스드상사 |
| B09/images:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 데스트상사; company_name: 테스트상사→주식회사데스트상사; company_name: 테스트상사→주식회사데스트상사; workplace_name: 테스트상사→주식회사 데스트상사; company_name: 테스트상사→주식회사데스트상사 |
| B10/scanned:E7-one:B10-3_납세증명서_스캔.pdf | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테소트상사 |
| B10/scanned:E7-one:B10-2_중소기업확인서_스캔.pdf | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테소트상사 |
| B10/scanned:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테소트상사; company_name: 테스트상사→주식회사 테소트상사; workplace_name: 테스트상사→주식회사 테소트상사; company_name: 테스트상사→주식회사테소트상사 |
| B10/images:E7-one:B10-4_4대사회보험료완납증명서_사진.jpg | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 테스드상사 |
| B10/images:E7-one:B10-3_납세증명서_사진.webp | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테스드상사 |
| B10/images:E7-all | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 데스트상사; company_name: 테스트상사→주식회사데스트상사; company_name: 테스트상사→주식회사 데스트상사; company_name: 테스트상사→주식회사데스트상사 |
| B11/scanned:E7-one:B11-4_4대사회보험료완납증명서_스캔.pdf | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 데스트상사 |
| B11/scanned:E7-all | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 테소트상사; company_name: 테스트상사→주식회사테소트상사; company_name: 테스트상사→주식회사 테소트상사 |
| B11/images:E7-one:B11-1_사업자등록증_사진.jpg | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테소트상사 |
| B11/images:E7-one:B11-2_중소기업확인서_사진.png | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테스트성사 |
| B11/images:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테스트상자; company_name: 테스트상사→주식회사 테스트상자; workplace_name: 테스트상사→주식회사 테스트상자 |
| B12/scanned:E7-one:B12-5_4대사회보험료완납증명서_스캔.pdf | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 데스트상사 |
| B12/scanned:E7-one:B12-3_중소기업확인서_스캔.pdf | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테소트상사 |
| B12/scanned:E7-all | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 데스트상사; company_name: 테스트상사→주식회사 데스트상사; company_name: 테스트상사→주식회사데스트상사; company_name: 테스트상사→주식회사데스트상사; company_name: 테스트상사→주식회사데스트상사 |
| B12/images:E7-one:B12-4_납세증명서_사진.jpg | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테스트성사 |
| B12/images:E7-one:B12-5_4대사회보험료완납증명서_사진.png | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 테스트상자 |
| B12/images:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테스트상자; workplace_name: 테스트상사→주식회사 테스트상자; company_name: 테스트상사→주식회사테스트상자; company_name: 테스트상사→주식회사테스트상자; company_name: 테스트상사→주식회사 테스트상자 |
| S01/scanned:E5-one:S01-1_재학증명서_스캔.pdf | NEEDS_CORRECTION | student_name: 김테스트→김테스드 |
| S01/scanned:E5-one:S01-2_성적증명서_스캔.pdf | NEEDS_CORRECTION | student_name: 김테스트→김테소트 |
| S01/scanned:E5-all | NEEDS_CORRECTION | student_name: 김테스트→김테스드; student_name: 김테스트→김테스드 |
| S01/scanned:E8:S01-2_성적증명서_스캔.pdf | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S01/scanned:E8:S01-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S01/scanned:E9:S01-1_재학증명서_스캔.pdf | REVIEW_REQUIRED | student_id: 2023123456→2023128456 |
| S01/scanned:E9:S01-1_재학증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2023123456→2023128456 |
| S01/scanned:E9:S01-2_성적증명서_스캔.pdf | REVIEW_REQUIRED | student_id: 2023123456→2023128456 |
| S01/scanned:E9:S01-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2023123456→2023128456 |
| S01/images:E5-one:S01-2_성적증명서_사진.png | NEEDS_CORRECTION | student_name: 김테스트→김데스트 |
| S01/images:E5-one:S01-1_재학증명서_사진.jpg | NEEDS_CORRECTION | student_name: 김테스트→길테스트 |
| S01/images:E5-all | NEEDS_CORRECTION | student_name: 김테스트→김테스드; student_name: 김테스트→김테스드 |
| S01/images:E8:S01-2_성적증명서_사진.png | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S01/images:E8:S01-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S01/images:E9:S01-2_성적증명서_사진.png | REVIEW_REQUIRED | student_id: 2023123456→2023123466 |
| S01/images:E9:S01-2_성적증명서_사진.png:both | REVIEW_REQUIRED | student_id: 2023123456→2023123466 |
| S01/images:E9:S01-1_재학증명서_사진.jpg | REVIEW_REQUIRED | student_id: 2023123456→2023123458 |
| S01/images:E9:S01-1_재학증명서_사진.jpg:both | REVIEW_REQUIRED | student_id: 2023123456→2023123458 |
| S02/scanned:E5-one:S02-2_성적증명서_스캔.pdf | NEEDS_CORRECTION | student_name: 김테스트→김테스드 |
| S02/scanned:E5-one:S02-1_재학증명서_스캔.pdf | NEEDS_CORRECTION | student_name: 김테스트→김테스드 |
| S02/scanned:E5-all | NEEDS_CORRECTION | student_name: 김테스트→길테스트; student_name: 김테스트→길테스트 |
| S02/scanned:E8:S02-2_성적증명서_스캔.pdf | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S02/scanned:E8:S02-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S02/scanned:E9:S02-1_재학증명서_스캔.pdf | REVIEW_REQUIRED | student_id: 2023123456→2023123455 |
| S02/scanned:E9:S02-1_재학증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2023123456→2023123455 |
| S02/scanned:E9:S02-2_성적증명서_스캔.pdf | REVIEW_REQUIRED | student_id: 2023123456→2023123455 |
| S02/scanned:E9:S02-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2023123456→2023123455 |
| S02/images:E5-one:S02-1_재학증명서_사진.jpg | NEEDS_CORRECTION | student_name: 김테스트→김데스트 |
| S02/images:E5-one:S02-2_성적증명서_사진.png | NEEDS_CORRECTION | student_name: 김테스트→김테소트 |
| S02/images:E5-all | NEEDS_CORRECTION | student_name: 김테스트→김데스트; student_name: 김테스트→김데스트 |
| S02/images:E8:S02-2_성적증명서_사진.png | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S02/images:E8:S02-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S02/images:E9:S02-1_재학증명서_사진.jpg | REVIEW_REQUIRED | student_id: 2023123456→7023123456 |
| S02/images:E9:S02-1_재학증명서_사진.jpg:both | REVIEW_REQUIRED | student_id: 2023123456→7023123456 |
| S02/images:E9:S02-2_성적증명서_사진.png | REVIEW_REQUIRED | student_id: 2023123456→2023173456 |
| S02/images:E9:S02-2_성적증명서_사진.png:both | REVIEW_REQUIRED | student_id: 2023123456→2023173456 |
| S03/scanned:E5-one:S03-1_재학증명서_스캔.pdf | NEEDS_CORRECTION | student_name: 김테스트→길테스트 |
| S03/scanned:E5-one:S03-2_성적증명서_스캔.pdf | NEEDS_CORRECTION | student_name: 김테스트→김데스트 |
| S03/scanned:E5-all | NEEDS_CORRECTION | student_name: 김테스트→김테스드; student_name: 김테스트→김테스드 |
| S03/scanned:E8:S03-2_성적증명서_스캔.pdf | REVIEW_REQUIRED | gpa: 2.70→3.7 |
| S03/scanned:E8:S03-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | gpa: 2.70→3.7 |
| S03/scanned:E9:S03-1_재학증명서_스캔.pdf | NEEDS_CORRECTION | student_id: 2023123456→2073123456 |
| S03/scanned:E9:S03-1_재학증명서_스캔.pdf:both | NEEDS_CORRECTION | student_id: 2023123456→2073123456 |
| S03/scanned:E9:S03-2_성적증명서_스캔.pdf | NEEDS_CORRECTION | student_id: 2023123456→2023128456 |
| S03/scanned:E9:S03-2_성적증명서_스캔.pdf:both | NEEDS_CORRECTION | student_id: 2023123456→2023128456 |
| S03/images:E5-one:S03-1_재학증명서_사진.jpg | NEEDS_CORRECTION | student_name: 김테스트→길테스트 |
| S03/images:E5-one:S03-2_성적증명서_사진.png | NEEDS_CORRECTION | student_name: 김테스트→길테스트 |
| S03/images:E5-all | NEEDS_CORRECTION | student_name: 김테스트→김테소트; student_name: 김테스트→김테소트 |
| S03/images:E8:S03-2_성적증명서_사진.png | REVIEW_REQUIRED | gpa: 2.70→3.7 |
| S03/images:E8:S03-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 2.70→3.7 |
| S03/images:E9:S03-2_성적증명서_사진.png | NEEDS_CORRECTION | student_id: 2023123456→2023128456 |
| S03/images:E9:S03-2_성적증명서_사진.png:both | NEEDS_CORRECTION | student_id: 2023123456→2023128456 |
| S03/images:E9:S03-1_재학증명서_사진.jpg | NEEDS_CORRECTION | student_id: 2023123456→2023128456 |
| S03/images:E9:S03-1_재학증명서_사진.jpg:both | NEEDS_CORRECTION | student_id: 2023123456→2023128456 |
| S04/scanned:E5-one:S04-1_재학증명서_스캔.pdf | NEEDS_CORRECTION | student_name: 김테스트→김테소트 |
| S04/scanned:E5-one:S04-2_성적증명서_스캔.pdf | NEEDS_CORRECTION | student_name: 김테스트→김테스드 |
| S04/scanned:E5-all | NEEDS_CORRECTION | student_name: 김테스트→김데스트; student_name: 김테스트→김데스트 |
| S04/scanned:E8:S04-2_성적증명서_스캔.pdf | REVIEW_REQUIRED | gpa: 3.10→3.8 |
| S04/scanned:E8:S04-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | gpa: 3.10→3.8 |
| S04/scanned:E9:S04-2_성적증명서_스캔.pdf | REVIEW_REQUIRED | student_id: 2023123456→7023123456 |
| S04/scanned:E9:S04-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2023123456→7023123456 |
| S04/images:E5-one:S04-2_성적증명서_사진.png | NEEDS_CORRECTION | student_name: 김테스트→김테스드 |
| S04/images:E5-one:S04-1_재학증명서_사진.jpg | NEEDS_CORRECTION | student_name: 김테스트→길테스트 |
| S04/images:E5-all | NEEDS_CORRECTION | student_name: 김테스트→길테스트; student_name: 김테스트→길테스트 |
| S04/images:E8:S04-2_성적증명서_사진.png | REVIEW_REQUIRED | gpa: 3.10→3.8 |
| S04/images:E8:S04-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.10→3.8 |
| S04/images:E9:S04-2_성적증명서_사진.png | REVIEW_REQUIRED | student_id: 2023123456→2023123455 |
| S04/images:E9:S04-2_성적증명서_사진.png:both | REVIEW_REQUIRED | student_id: 2023123456→2023123455 |
| S05/scanned:E5-one:S05-1_재학증명서_스캔.pdf | NEEDS_CORRECTION | student_name: 김테스트→김데스트 |
| S05/scanned:E5-one:S05-2_성적증명서_스캔.pdf | NEEDS_CORRECTION | student_name: 이샘플→미샘플 |
| S05/scanned:E5-all | NEEDS_CORRECTION | student_name: 김테스트→길테스트; student_name: 이샘플→길샘플 |
| S05/scanned:E8:S05-2_성적증명서_스캔.pdf | NEEDS_CORRECTION | gpa: 3.80→4.4 |
| S05/scanned:E8:S05-2_성적증명서_스캔.pdf:both | NEEDS_CORRECTION | gpa: 3.80→4.4 |
| S05/scanned:E9:S05-2_성적증명서_스캔.pdf | NEEDS_CORRECTION | student_id: 2023123456→2023173456 |
| S05/scanned:E9:S05-2_성적증명서_스캔.pdf:both | NEEDS_CORRECTION | student_id: 2023123456→2023173456 |
| S05/scanned:E9:S05-1_재학증명서_스캔.pdf | NEEDS_CORRECTION | student_id: 2023123456→2023123466 |
| S05/scanned:E9:S05-1_재학증명서_스캔.pdf:both | NEEDS_CORRECTION | student_id: 2023123456→2023123466 |
| S05/images:E5-one:S05-2_성적증명서_사진.png | NEEDS_CORRECTION | student_name: 이샘플→이샘풀 |
| S05/images:E5-one:S05-1_재학증명서_사진.jpg | NEEDS_CORRECTION | student_name: 김테스트→김테소트 |
| S05/images:E5-all | NEEDS_CORRECTION | student_name: 이샘플→미샘플; student_name: 김테스트→미테스트 |
| S05/images:E8:S05-2_성적증명서_사진.png | NEEDS_CORRECTION | gpa: 3.80→4.4 |
| S05/images:E8:S05-2_성적증명서_사진.png:both | NEEDS_CORRECTION | gpa: 3.80→4.4 |
| S05/images:E9:S05-2_성적증명서_사진.png | NEEDS_CORRECTION | student_id: 2023123456→2823123456 |
| S05/images:E9:S05-2_성적증명서_사진.png:both | NEEDS_CORRECTION | student_id: 2023123456→2823123456 |
| S05/images:E9:S05-1_재학증명서_사진.jpg | NEEDS_CORRECTION | student_id: 2023123456→2028123456 |
| S05/images:E9:S05-1_재학증명서_사진.jpg:both | NEEDS_CORRECTION | student_id: 2023123456→2028123456 |
| S06/scanned:E5-one:S06-2_성적증명서_스캔.pdf | NEEDS_CORRECTION | student_name: 김테스트→김데스트 |
| S06/scanned:E5-one:S06-1_재학증명서_스캔.pdf | NEEDS_CORRECTION | student_name: 김테스트→길테스트 |
| S06/scanned:E5-all | NEEDS_CORRECTION | student_name: 김테스트→김테소트; student_name: 김테스트→김테소트 |
| S06/scanned:E8:S06-2_성적증명서_스캔.pdf | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S06/scanned:E8:S06-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S06/scanned:E9:S06-1_재학증명서_스캔.pdf | REVIEW_REQUIRED | student_id: 2023123456→2023173456 |
| S06/scanned:E9:S06-1_재학증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2023123456→2023173456 |
| S06/scanned:E9:S06-2_성적증명서_스캔.pdf | REVIEW_REQUIRED | student_id: 2023123456→2023123466 |
| S06/scanned:E9:S06-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2023123456→2023123466 |
| S06/images:E5-one:S06-2_성적증명서_사진.png | NEEDS_CORRECTION | student_name: 김테스트→길테스트 |
| S06/images:E5-one:S06-1_재학증명서_사진.jpg | NEEDS_CORRECTION | student_name: 김테스트→길테스트 |
| S06/images:E5-all | NEEDS_CORRECTION | student_name: 김테스트→길테스트; student_name: 김테스트→길테스트 |
| S06/images:E8:S06-2_성적증명서_사진.png | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S06/images:E8:S06-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S06/images:E9:S06-2_성적증명서_사진.png | REVIEW_REQUIRED | student_id: 2023123456→2023173456 |
| S06/images:E9:S06-2_성적증명서_사진.png:both | REVIEW_REQUIRED | student_id: 2023123456→2023173456 |
| S06/images:E9:S06-1_재학증명서_사진.jpg | REVIEW_REQUIRED | student_id: 2023123456→2023123458 |
| S06/images:E9:S06-1_재학증명서_사진.jpg:both | REVIEW_REQUIRED | student_id: 2023123456→2023123458 |
| S08/scanned:E5-one:S08-2_성적증명서_스캔.pdf | NEEDS_CORRECTION | student_name: 김테스트→김테스드 |
| S08/scanned:E5-one:S08-1_재학증명서_스캔.pdf | NEEDS_CORRECTION | student_name: 김테스트→김테스드 |
| S08/scanned:E5-all | NEEDS_CORRECTION | student_name: 김테스트→김데스트; student_name: 김테스트→김데스트 |
| S08/scanned:E8:S08-2_성적증명서_스캔.pdf | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S08/scanned:E8:S08-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S08/scanned:E9:S08-1_재학증명서_스캔.pdf | REVIEW_REQUIRED | student_id: 2023123456→7023123456 |
| S08/scanned:E9:S08-1_재학증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2023123456→7023123456 |
| S08/scanned:E9:S08-2_성적증명서_스캔.pdf | REVIEW_REQUIRED | student_id: 2023123456→2023128456 |
| S08/scanned:E9:S08-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2023123456→2023128456 |
| S08/images:E5-one:S08-2_성적증명서_사진.png | NEEDS_CORRECTION | student_name: 김테스트→김테소트 |
| S08/images:E5-one:S08-1_재학증명서_사진.jpg | NEEDS_CORRECTION | student_name: 김테스트→김데스트 |
| S08/images:E5-all | NEEDS_CORRECTION | student_name: 김테스트→김테스드; student_name: 김테스트→김테스드 |
| S08/images:E8:S08-2_성적증명서_사진.png | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S08/images:E8:S08-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S08/images:E9:S08-2_성적증명서_사진.png | REVIEW_REQUIRED | student_id: 2023123456→2023123466 |
| S08/images:E9:S08-2_성적증명서_사진.png:both | REVIEW_REQUIRED | student_id: 2023123456→2023123466 |
| S08/images:E9:S08-1_재학증명서_사진.jpg | REVIEW_REQUIRED | student_id: 2023123456→2023128456 |
| S08/images:E9:S08-1_재학증명서_사진.jpg:both | REVIEW_REQUIRED | student_id: 2023123456→2023128456 |
| S09/scanned:E5-one:S09-1_재학증명서_스캔.pdf | NEEDS_CORRECTION | student_name: 김테스트→김테소트 |
| S09/scanned:E5-one:S09-2_성적증명서_스캔.pdf | NEEDS_CORRECTION | student_name: 김테스트→김테소트 |
| S09/scanned:E5-all | NEEDS_CORRECTION | student_name: 김테스트→김테스드; student_name: 김테스트→김테스드 |
| S09/scanned:E8:S09-2_성적증명서_스캔.pdf | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S09/scanned:E8:S09-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S09/scanned:E9:S09-2_성적증명서_스캔.pdf | REVIEW_REQUIRED | student_id: 2023123456→2823123456 |
| S09/scanned:E9:S09-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2023123456→2823123456 |
| S09/images:E5-one:S09-1_재학증명서_사진.jpg | NEEDS_CORRECTION | student_name: 김테스트→김테스드 |
| S09/images:E5-one:S09-2_성적증명서_사진.png | NEEDS_CORRECTION | student_name: 김테스트→김테소트 |
| S09/images:E5-all | NEEDS_CORRECTION | student_name: 김테스트→김데스트; student_name: 김테스트→김데스트 |
| S09/images:E8:S09-2_성적증명서_사진.png | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S09/images:E8:S09-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S09/images:E9:S09-2_성적증명서_사진.png | REVIEW_REQUIRED | student_id: 2023123456→2023123466 |
| S09/images:E9:S09-2_성적증명서_사진.png:both | REVIEW_REQUIRED | student_id: 2023123456→2023123466 |
| S10/scanned:E5-one:S10-2_성적증명서_스캔.pdf | NEEDS_CORRECTION | student_name: 김테스트→김데스트 |
| S10/scanned:E5-one:S10-1_재학증명서_스캔.pdf | NEEDS_CORRECTION | student_name: 김테스트→길테스트 |
| S10/scanned:E5-all | NEEDS_CORRECTION | student_name: 김테스트→김테스드; student_name: 김테스트→김테스드 |
| S10/scanned:E8:S10-2_성적증명서_스캔.pdf | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S10/scanned:E8:S10-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S10/scanned:E9:S10-2_성적증명서_스캔.pdf | REVIEW_REQUIRED | student_id: 2023123456→2023123466 |
| S10/scanned:E9:S10-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2023123456→2023123466 |
| S10/scanned:E9:S10-1_재학증명서_스캔.pdf | REVIEW_REQUIRED | student_id: 2023123456→2023123455 |
| S10/scanned:E9:S10-1_재학증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2023123456→2023123455 |
| S10/images:E5-one:S10-1_재학증명서_사진.jpg | NEEDS_CORRECTION | student_name: 김테스트→길테스트 |
| S10/images:E5-one:S10-2_성적증명서_사진.png | NEEDS_CORRECTION | student_name: 김테스트→김테스드 |
| S10/images:E5-all | NEEDS_CORRECTION | student_name: 김테스트→길테스트; student_name: 김테스트→길테스트 |
| S10/images:E8:S10-2_성적증명서_사진.png | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S10/images:E8:S10-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S10/images:E9:S10-2_성적증명서_사진.png | REVIEW_REQUIRED | student_id: 2023123456→7023123456 |
| S10/images:E9:S10-2_성적증명서_사진.png:both | REVIEW_REQUIRED | student_id: 2023123456→7023123456 |
| S10/images:E9:S10-1_재학증명서_사진.jpg | REVIEW_REQUIRED | student_id: 2023123456→2073123456 |
| S10/images:E9:S10-1_재학증명서_사진.jpg:both | REVIEW_REQUIRED | student_id: 2023123456→2073123456 |
