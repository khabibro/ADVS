# Injection results — S1 injection noproj

- Suite SHA-256 `a81e4ef2ebfc97c3bf2646952b2c3a532e2cab33b4ecace8365cc9c685a484fd`, seed 20261005, git `09966c8`, strategy `S1`, project values `False`
- Scorer v2 SHA-256 `49674a9c03e464310cda0278782062e1a4b996e334ff8d8cbdc78d10b5ad2594`; cases: 428

`planned` = enumerated cases; `exercised` = the un-injected control run read the target field correctly (so the injection is meaningful); `effective` = the pipeline actually read the injected wrong value.

| Injection | Planned | Exercised | Effective (wrong value read) | False auto-accept | False READY | Not auto-accepted | READY | NEEDS_CORRECTION | REVIEW_REQUIRED |
|---|---|---|---|---|---|---|---|---|---|
| E1-one | 44 | 24 | 24 | 0 | 0 | 24 | 0 | 5 | 19 |
| E2-all | 22 | 14 | 14 | 0 | 0 | 14 | 0 | 2 | 12 |
| E3-all | 22 | 14 | 14 | 0 | 0 | 14 | 0 | 2 | 12 |
| E3-one | 44 | 26 | 26 | 0 | 0 | 26 | 0 | 8 | 18 |
| E4-one | 44 | 21 | 0 | 0 | 0 | 21 | 0 | 7 | 14 |
| E5-all | 20 | 7 | 7 | 7 | 0 | 0 | 0 | 0 | 7 |
| E5-one | 40 | 23 | 23 | 23 | 0 | 0 | 0 | 0 | 23 |
| E6-one | 4 | 3 | 2 | 1 | 0 | 2 | 0 | 0 | 3 |
| E6-one-both | 4 | 3 | 2 | 1 | 0 | 2 | 0 | 0 | 3 |
| E7-all | 24 | 24 | 24 | 24 | 0 | 0 | 0 | 7 | 17 |
| E7-one | 48 | 45 | 45 | 45 | 0 | 0 | 0 | 33 | 12 |
| E8-one | 18 | 7 | 7 | 7 | 0 | 0 | 0 | 0 | 7 |
| E8-one-both | 18 | 7 | 7 | 7 | 0 | 0 | 0 | 0 | 7 |
| E9-one | 38 | 19 | 19 | 19 | 0 | 0 | 0 | 0 | 19 |
| E9-one-both | 38 | 19 | 19 | 19 | 0 | 0 | 0 | 0 | 19 |

Totals: planned 428, exercised 256, effective 233.

**Totals: false auto-accept 153, false READY 0.**

## Leaks

| Case | status | injected → accepted value |
|---|---|---|
| B01/scanned:E7-one:B01-4_4대사회보험료완납증명서_스캔.pdf | REVIEW_REQUIRED | workplace_name: 테스트상사→주식회사 데스트상사 |
| B01/scanned:E7-one:B01-2_중소기업확인서_스캔.pdf | REVIEW_REQUIRED | company_name: 테스트상사→주식회사 테스드상사 |
| B01/scanned:E7-all | REVIEW_REQUIRED | workplace_name: 테스트상사→주식회사 테스트상자; company_name: 테스트상사→주식회사 테스트상자; company_name: 테스트상사→주식회사 테스트상자 |
| B01/images:E7-one:B01-4_4대사회보험료완납증명서_사진.jpg | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사데스트상사 |
| B01/images:E7-one:B01-2_중소기업확인서_사진.png | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테스트상자 |
| B01/images:E7-all | REVIEW_REQUIRED | workplace_name: 테스트상사→주식회사테스드상사; company_name: 테스트상사→주식회사 테스드상사; company_name: 테스트상사→주식회사테스드상사; company_name: 테스트상사→주식회사테스드상사 |
| B02/scanned:E7-one:B02-3_납세증명서_스캔.pdf | REVIEW_REQUIRED | company_name: 테스트상사→(주)데스트상사 |
| B02/scanned:E7-all | REVIEW_REQUIRED | company_name: 테스트상사→(주)테스트성사; company_name: 테스트상사→(주)테스트성사; workplace_name: 테스트상사→테스트성사(주) |
| B02/images:E7-one:B02-3_납세증명서_사진.webp | NEEDS_CORRECTION | company_name: 테스트상사→(주)데스트상사 |
| B02/images:E7-one:B02-2_중소기업확인서_사진.png | NEEDS_CORRECTION | company_name: 테스트상사→(주)테스드상사 |
| B02/images:E7-all | REVIEW_REQUIRED | company_name: 테스트상사→(주)테스드상사; company_name: 테스트상사→(주)테스드상사; workplace_name: 테스트상사→테스드상사(주); company_name: 테스트상사→주식회사테스드상사 |
| B03/scanned:E7-one:B03-2_중소기업확인서_스캔.pdf | NEEDS_CORRECTION | company_name: 테스트상사→주식회사데스트상사 |
| B03/scanned:E7-one:B03-3_납세증명서_스캔.pdf | NEEDS_CORRECTION | company_name: 가나다솔루션→주식회사 가나다술루션 |
| B03/scanned:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테스트상자; company_name: 가나다솔루션→주식회사 가나다솔자션; workplace_name: 테스트상사→주식회사 테스트상자; company_name: 테스트상사→주식회사테스트상자 |
| B03/images:E7-one:B03-2_중소기업확인서_사진.png | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테스트상자 |
| B03/images:E7-one:B03-4_4대사회보험료완납증명서_사진.jpg | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 데스트상사 |
| B03/images:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테소트상사; workplace_name: 테스트상사→주식회사 테소트상사; company_name: 가나다솔루션→주식회사가소다솔루션; company_name: 테스트상사→주식회사테소트상사 |
| B04/scanned:E7-one:B04-2_중소기업확인서_스캔.pdf | REVIEW_REQUIRED | company_name: 테스트상사→주식회사 테스트성사 |
| B04/scanned:E7-all | REVIEW_REQUIRED | company_name: 테스트상사→주식회사 테스트상자; workplace_name: 테스트상사→주식회사 테스트상자; company_name: 테스트상사→주식회사 테스트상자 |
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
| B06/scanned:E7-all | REVIEW_REQUIRED | company_name: 테스트상사→주식회사테소트상사; workplace_name: 테스트상사→주식회사 테소트상사; company_name: 테스트상사→주식회사 테소트상사 |
| B06/images:E7-one:B06-1_사업자등록증_사진.jpg | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테스트상자 |
| B06/images:E7-one:B06-4_4대사회보험료완납증명서_사진.jpg | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사테스드상사 |
| B06/images:E7-all | REVIEW_REQUIRED | company_name: 테스트상사→주식회사테스트상자; workplace_name: 테스트상사→주식회사테스트상자; company_name: 테스트상사→주식회사테스트상자; company_name: 테스트상사→주식회사 테스트상자 |
| B07/scanned:E7-one:B07-3_납세증명서_스캔.pdf | REVIEW_REQUIRED | company_name: 테스트상사→주식회사 테스트상자 |
| B07/scanned:E7-one:B07-2_중소기업확인서_스캔.pdf | REVIEW_REQUIRED | company_name: 테스트상사→주식회사 테소트상사 |
| B07/scanned:E7-all | REVIEW_REQUIRED | company_name: 테스트상사→주식회사 데스트상사; company_name: 테스트상사→주식회사 데스트상사; workplace_name: 테스트상사→주식회사 데스트상사 |
| B07/images:E7-one:B07-3_납세증명서_사진.webp | NEEDS_CORRECTION | company_name: 테스트상사→주식회사데스트상사 |
| B07/images:E7-one:B07-2_중소기업확인서_사진.png | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테소트상사 |
| B07/images:E7-all | REVIEW_REQUIRED | company_name: 테스트상사→주식회사테소트상사; company_name: 테스트상사→주식회사 테소트상사; company_name: 테스트상사→주식회사테소트상사; workplace_name: 테스트상사→주식회사 테소트상사 |
| B08/scanned:E7-one:B08-3_4대사회보험료완납증명서_스캔.pdf | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 테스드상사 |
| B08/scanned:E7-one:B08-2_납세증명서_스캔.pdf | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테소트상사 |
| B08/scanned:E7-all | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 테스드상사; company_name: 테스트상사→주식회사 테스드상사; company_name: 테스트상사→주식회사 테스드상사 |
| B08/images:E7-one:B08-2_납세증명서_사진.png | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테소트상사 |
| B08/images:E7-one:B08-1_중소기업확인서_사진.jpg | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테스트상자 |
| B08/images:E7-all | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테스트성사; company_name: 테스트상사→주식회사 테스트성사; workplace_name: 테스트상사→주식회사 테스트성사 |
| B09/scanned:E7-one:B09-4_4대사회보험료완납증명서_스캔.pdf | REVIEW_REQUIRED | workplace_name: 테스트상사→주식회사 테스드상사 |
| B09/scanned:E7-one:B09-3_납세증명서_스캔 (사본).pdf | REVIEW_REQUIRED | company_name: 테스트상사→주식회사테소트상사 |
| B09/scanned:E7-all | REVIEW_REQUIRED | workplace_name: 테스트상사→주식회사 테스트상자; company_name: 테스트상사→주식회사테스트상자; company_name: 테스트상사→주식회사테스트상자 |
| B09/images:E7-one:B09-2_중소기업확인서_사진.png | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테스트상자 |
| B09/images:E7-one:B09-3_납세증명서_사진.webp | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테스드상사 |
| B09/images:E7-all | REVIEW_REQUIRED | company_name: 테스트상사→주식회사 데스트상사; company_name: 테스트상사→주식회사데스트상사; company_name: 테스트상사→주식회사데스트상사; workplace_name: 테스트상사→주식회사 데스트상사; company_name: 테스트상사→주식회사데스트상사 |
| B10/scanned:E7-one:B10-3_납세증명서_스캔.pdf | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테소트상사 |
| B10/scanned:E7-one:B10-2_중소기업확인서_스캔.pdf | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테소트상사 |
| B10/scanned:E7-all | REVIEW_REQUIRED | company_name: 테스트상사→주식회사 테소트상사; company_name: 테스트상사→주식회사 테소트상사; workplace_name: 테스트상사→주식회사 테소트상사; company_name: 테스트상사→주식회사테소트상사 |
| B10/images:E7-one:B10-4_4대사회보험료완납증명서_사진.jpg | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 테스드상사 |
| B10/images:E7-one:B10-3_납세증명서_사진.webp | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테스드상사 |
| B10/images:E7-all | REVIEW_REQUIRED | workplace_name: 테스트상사→주식회사 데스트상사; company_name: 테스트상사→주식회사데스트상사; company_name: 테스트상사→주식회사 데스트상사; company_name: 테스트상사→주식회사데스트상사 |
| B11/scanned:E7-one:B11-4_4대사회보험료완납증명서_스캔.pdf | NEEDS_CORRECTION | workplace_name: 테스트상사→주식회사 데스트상사 |
| B11/scanned:E7-all | REVIEW_REQUIRED | workplace_name: 테스트상사→주식회사 테소트상사; company_name: 테스트상사→주식회사테소트상사; company_name: 테스트상사→주식회사 테소트상사 |
| B11/images:E7-one:B11-1_사업자등록증_사진.jpg | NEEDS_CORRECTION | company_name: 테스트상사→주식회사테소트상사 |
| B11/images:E7-one:B11-2_중소기업확인서_사진.png | NEEDS_CORRECTION | company_name: 테스트상사→주식회사 테스트성사 |
| B11/images:E7-all | REVIEW_REQUIRED | company_name: 테스트상사→주식회사테스트상자; company_name: 테스트상사→주식회사 테스트상자; workplace_name: 테스트상사→주식회사 테스트상자 |
| B12/scanned:E7-one:B12-5_4대사회보험료완납증명서_스캔.pdf | REVIEW_REQUIRED | workplace_name: 테스트상사→주식회사 데스트상사 |
| B12/scanned:E7-one:B12-3_중소기업확인서_스캔.pdf | REVIEW_REQUIRED | company_name: 테스트상사→주식회사 테소트상사 |
| B12/scanned:E7-all | REVIEW_REQUIRED | workplace_name: 테스트상사→주식회사 데스트상사; company_name: 테스트상사→주식회사 데스트상사; company_name: 테스트상사→주식회사데스트상사; company_name: 테스트상사→주식회사데스트상사; company_name: 테스트상사→주식회사데스트상사 |
| B12/images:E7-one:B12-4_납세증명서_사진.jpg | REVIEW_REQUIRED | company_name: 테스트상사→주식회사 테스트성사 |
| B12/images:E7-one:B12-5_4대사회보험료완납증명서_사진.png | REVIEW_REQUIRED | workplace_name: 테스트상사→주식회사 테스트상자 |
| B12/images:E7-all | REVIEW_REQUIRED | company_name: 테스트상사→주식회사 테스트상자; workplace_name: 테스트상사→주식회사 테스트상자; company_name: 테스트상사→주식회사테스트상자; company_name: 테스트상사→주식회사테스트상자; company_name: 테스트상사→주식회사 테스트상자 |
| S01/scanned:E5-one:S01-1_재학증명서_스캔.pdf | REVIEW_REQUIRED | student_name: 김테스트→김테스드 |
| S01/scanned:E9:S01-1_재학증명서_스캔.pdf | REVIEW_REQUIRED | student_id: 2023123456→2023128456 |
| S01/scanned:E9:S01-1_재학증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2023123456→2023128456 |
| S01/images:E5-one:S01-2_성적증명서_사진.png | REVIEW_REQUIRED | student_name: 김테스트→김데스트 |
| S01/images:E5-one:S01-1_재학증명서_사진.jpg | REVIEW_REQUIRED | student_name: 김테스트→길테스트 |
| S01/images:E5-all | REVIEW_REQUIRED | student_name: 김테스트→김테스드; student_name: 김테스트→김테스드 |
| S01/images:E8:S01-2_성적증명서_사진.png | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S01/images:E8:S01-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S01/images:E9:S01-2_성적증명서_사진.png | REVIEW_REQUIRED | student_id: 2023123456→2023123466 |
| S01/images:E9:S01-2_성적증명서_사진.png:both | REVIEW_REQUIRED | student_id: 2023123456→2023123466 |
| S01/images:E9:S01-1_재학증명서_사진.jpg | REVIEW_REQUIRED | student_id: 2023123456→2023123458 |
| S01/images:E9:S01-1_재학증명서_사진.jpg:both | REVIEW_REQUIRED | student_id: 2023123456→2023123458 |
| S02/images:E5-one:S02-1_재학증명서_사진.jpg | REVIEW_REQUIRED | student_name: 김테스트→김데스트 |
| S02/images:E5-one:S02-2_성적증명서_사진.png | REVIEW_REQUIRED | student_name: 김테스트→김테소트 |
| S02/images:E5-all | REVIEW_REQUIRED | student_name: 김테스트→김데스트; student_name: 김테스트→김데스트 |
| S02/images:E8:S02-2_성적증명서_사진.png | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S02/images:E8:S02-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S02/images:E9:S02-1_재학증명서_사진.jpg | REVIEW_REQUIRED | student_id: 2023123456→7023123456 |
| S02/images:E9:S02-1_재학증명서_사진.jpg:both | REVIEW_REQUIRED | student_id: 2023123456→7023123456 |
| S02/images:E9:S02-2_성적증명서_사진.png | REVIEW_REQUIRED | student_id: 2023123456→2023173456 |
| S02/images:E9:S02-2_성적증명서_사진.png:both | REVIEW_REQUIRED | student_id: 2023123456→2023173456 |
| S03/scanned:E5-one:S03-1_재학증명서_스캔.pdf | REVIEW_REQUIRED | student_name: 김테스트→길테스트 |
| S03/scanned:E9:S03-1_재학증명서_스캔.pdf | REVIEW_REQUIRED | student_id: 2023123456→2073123456 |
| S03/scanned:E9:S03-1_재학증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2023123456→2073123456 |
| S03/images:E5-one:S03-1_재학증명서_사진.jpg | REVIEW_REQUIRED | student_name: 김테스트→길테스트 |
| S03/images:E9:S03-1_재학증명서_사진.jpg | REVIEW_REQUIRED | student_id: 2023123456→2023128456 |
| S03/images:E9:S03-1_재학증명서_사진.jpg:both | REVIEW_REQUIRED | student_id: 2023123456→2023128456 |
| S04/scanned:E5-one:S04-1_재학증명서_스캔.pdf | REVIEW_REQUIRED | student_name: 김테스트→김테소트 |
| S04/images:E5-one:S04-1_재학증명서_사진.jpg | REVIEW_REQUIRED | student_name: 김테스트→길테스트 |
| S05/scanned:E5-one:S05-1_재학증명서_스캔.pdf | REVIEW_REQUIRED | student_name: 김테스트→김데스트 |
| S05/scanned:E9:S05-1_재학증명서_스캔.pdf | REVIEW_REQUIRED | student_id: 2023123456→2023123466 |
| S05/scanned:E9:S05-1_재학증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2023123456→2023123466 |
| S05/images:E5-one:S05-2_성적증명서_사진.png | REVIEW_REQUIRED | student_name: 이샘플→이샘풀 |
| S05/images:E5-one:S05-1_재학증명서_사진.jpg | REVIEW_REQUIRED | student_name: 김테스트→김테소트 |
| S05/images:E5-all | REVIEW_REQUIRED | student_name: 이샘플→미샘플; student_name: 김테스트→미테스트 |
| S05/images:E8:S05-2_성적증명서_사진.png | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S05/images:E8:S05-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S05/images:E9:S05-2_성적증명서_사진.png | REVIEW_REQUIRED | student_id: 2023123456→2823123456 |
| S05/images:E9:S05-2_성적증명서_사진.png:both | REVIEW_REQUIRED | student_id: 2023123456→2823123456 |
| S05/images:E9:S05-1_재학증명서_사진.jpg | REVIEW_REQUIRED | student_id: 2023123456→2028123456 |
| S05/images:E9:S05-1_재학증명서_사진.jpg:both | REVIEW_REQUIRED | student_id: 2023123456→2028123456 |
| S06/images:E5-one:S06-1_재학증명서_사진.jpg | REVIEW_REQUIRED | student_name: 김테스트→길테스트 |
| S06/images:E9:S06-1_재학증명서_사진.jpg | REVIEW_REQUIRED | student_id: 2023123456→2023123458 |
| S06/images:E9:S06-1_재학증명서_사진.jpg:both | REVIEW_REQUIRED | student_id: 2023123456→2023123458 |
| S08/scanned:E5-one:S08-1_재학증명서_스캔.pdf | REVIEW_REQUIRED | student_name: 김테스트→김테스드 |
| S08/scanned:E9:S08-1_재학증명서_스캔.pdf | REVIEW_REQUIRED | student_id: 2023123456→7023123456 |
| S08/scanned:E9:S08-1_재학증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2023123456→7023123456 |
| S08/images:E5-one:S08-2_성적증명서_사진.png | REVIEW_REQUIRED | student_name: 김테스트→김테소트 |
| S08/images:E5-one:S08-1_재학증명서_사진.jpg | REVIEW_REQUIRED | student_name: 김테스트→김데스트 |
| S08/images:E5-all | REVIEW_REQUIRED | student_name: 김테스트→김테스드; student_name: 김테스트→김테스드 |
| S08/images:E8:S08-2_성적증명서_사진.png | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S08/images:E8:S08-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S08/images:E9:S08-2_성적증명서_사진.png | REVIEW_REQUIRED | student_id: 2023123456→2023123466 |
| S08/images:E9:S08-2_성적증명서_사진.png:both | REVIEW_REQUIRED | student_id: 2023123456→2023123466 |
| S08/images:E9:S08-1_재학증명서_사진.jpg | REVIEW_REQUIRED | student_id: 2023123456→2023128456 |
| S08/images:E9:S08-1_재학증명서_사진.jpg:both | REVIEW_REQUIRED | student_id: 2023123456→2023128456 |
| S09/scanned:E5-one:S09-1_재학증명서_스캔.pdf | REVIEW_REQUIRED | student_name: 김테스트→김테소트 |
| S09/images:E5-one:S09-1_재학증명서_사진.jpg | REVIEW_REQUIRED | student_name: 김테스트→김테스드 |
| S09/images:E5-one:S09-2_성적증명서_사진.png | REVIEW_REQUIRED | student_name: 김테스트→김테소트 |
| S09/images:E5-all | REVIEW_REQUIRED | student_name: 김테스트→김데스트; student_name: 김테스트→김데스트 |
| S09/images:E8:S09-2_성적증명서_사진.png | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S09/images:E8:S09-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S09/images:E9:S09-2_성적증명서_사진.png | REVIEW_REQUIRED | student_id: 2023123456→2023123466 |
| S09/images:E9:S09-2_성적증명서_사진.png:both | REVIEW_REQUIRED | student_id: 2023123456→2023123466 |
| S10/scanned:E5-one:S10-2_성적증명서_스캔.pdf | REVIEW_REQUIRED | student_name: 김테스트→김데스트 |
| S10/scanned:E5-one:S10-1_재학증명서_스캔.pdf | REVIEW_REQUIRED | student_name: 김테스트→길테스트 |
| S10/scanned:E5-all | REVIEW_REQUIRED | student_name: 김테스트→김테스드; student_name: 김테스트→김테스드 |
| S10/scanned:E8:S10-2_성적증명서_스캔.pdf | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S10/scanned:E8:S10-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S10/scanned:E9:S10-2_성적증명서_스캔.pdf | REVIEW_REQUIRED | student_id: 2023123456→2023123466 |
| S10/scanned:E9:S10-2_성적증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2023123456→2023123466 |
| S10/scanned:E9:S10-1_재학증명서_스캔.pdf | REVIEW_REQUIRED | student_id: 2023123456→2023123455 |
| S10/scanned:E9:S10-1_재학증명서_스캔.pdf:both | REVIEW_REQUIRED | student_id: 2023123456→2023123455 |
| S10/images:E5-one:S10-1_재학증명서_사진.jpg | REVIEW_REQUIRED | student_name: 김테스트→길테스트 |
| S10/images:E5-one:S10-2_성적증명서_사진.png | REVIEW_REQUIRED | student_name: 김테스트→김테스드 |
| S10/images:E5-all | REVIEW_REQUIRED | student_name: 김테스트→길테스트; student_name: 김테스트→길테스트 |
| S10/images:E8:S10-2_성적증명서_사진.png | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S10/images:E8:S10-2_성적증명서_사진.png:both | REVIEW_REQUIRED | gpa: 3.80→4.4 |
| S10/images:E9:S10-2_성적증명서_사진.png | REVIEW_REQUIRED | student_id: 2023123456→7023123456 |
| S10/images:E9:S10-2_성적증명서_사진.png:both | REVIEW_REQUIRED | student_id: 2023123456→7023123456 |
| S10/images:E9:S10-1_재학증명서_사진.jpg | REVIEW_REQUIRED | student_id: 2023123456→2073123456 |
| S10/images:E9:S10-1_재학증명서_사진.jpg:both | REVIEW_REQUIRED | student_id: 2023123456→2073123456 |
