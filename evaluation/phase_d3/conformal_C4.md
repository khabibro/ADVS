# D3-11 conformal threshold suggestions on development data (C4; 1543 OCR field values)

Calibration data = development sets only; synthetic, so for comparison until real reviewed data exist. The hand-picked floors stay in production.

# Conformal threshold suggestions (alpha = 0.05; samples needed per field >= 19)

Suggested only; production keeps the hand-picked floor.

| Field | current floor | suggested threshold | accepted | wrong | bound |
|---|---|---|---|---|---|
| business_registration_number | 0.9 | 0.882 | 319 | 0 | 0.0031 |
| company_name | 0.9 | 0.838 | 240 | 0 | 0.0041 |
| department | - | 0.811 | 55 | 0 | 0.0179 |
| gpa | - | 0.913 | 58 | 0 | 0.0169 |
| gpa_scale | - | 0.913 | 58 | 0 | 0.0169 |
| issue_date | - | 0.928 | 110 | 0 | 0.009 |
| student_id | - | 0.888 | 106 | 0 | 0.0093 |
| student_name | - | 0.862 | 115 | 0 | 0.0086 |
| university_name | - | 0.889 | 92 | 0 | 0.0108 |
| valid_from | - | 0.940 | 78 | 0 | 0.0127 |
| valid_until | - | 0.887 | 232 | 0 | 0.0043 |
| workplace_name | - | 0.945 | 80 | 0 | 0.0123 |

# Conformal threshold suggestions (alpha = 0.01; samples needed per field >= 99)

Suggested only; production keeps the hand-picked floor.

| Field | current floor | suggested threshold | accepted | wrong | bound |
|---|---|---|---|---|---|
| business_registration_number | 0.9 | 0.882 | 319 | 0 | 0.0031 |
| company_name | 0.9 | 0.838 | 240 | 0 | 0.0041 |
| department | - | — (insufficient data: have 55, need 99) | | | |
| gpa | - | — (insufficient data: have 58, need 99) | | | |
| gpa_scale | - | — (insufficient data: have 58, need 99) | | | |
| issue_date | - | 0.928 | 110 | 0 | 0.009 |
| student_id | - | 0.888 | 106 | 0 | 0.0093 |
| student_name | - | 0.862 | 115 | 0 | 0.0086 |
| university_name | - | — (insufficient data: have 92, need 99) | | | |
| valid_from | - | — (insufficient data: have 78, need 99) | | | |
| valid_until | - | 0.887 | 232 | 0 | 0.0043 |
| workplace_name | - | — (insufficient data: have 80, need 99) | | | |
