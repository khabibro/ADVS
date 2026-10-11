# D3 injection results — C1b holdout2

- Suites: Phase D `a81e4ef2ebfc97c3bf2646952b2c3a532e2cab33b4ecace8365cc9c685a484fd`, D2 `08229da0419528164cd863a29a449016febe1bae99369d99214130a9e59f3f57`, D3 `968e4c1ab48fe106488ad3a97ecc3656a59250be6cfe613731bd1e1b9909459c`; scorer v2 `49674a9c03e464310cda0278782062e1a4b996e334ff8d8cbdc78d10b5ad2594`
- corpus `holdout2`, git `a3d12a3`, cases 2238

| Injection | Cases | False auto-accept | False READY | decision changed (E16/E17) | READY | NEEDS_CORRECTION | REVIEW_REQUIRED |
|---|---|---|---|---|---|---|---|
| E1 | 51 | 0 | 0 | 0 | 0 | 8 | 43 |
| E10 | 24 | 0 | 0 | 0 | 0 | 0 | 24 |
| E11-both | 16 | 0 | 0 | 0 | 0 | 0 | 16 |
| E12-both | 6 | 0 | 0 | 0 | 0 | 0 | 6 |
| E13 | 40 | 0 | 0 | 0 | 0 | 0 | 40 |
| E13-both | 40 | 0 | 0 | 0 | 0 | 0 | 40 |
| E13c | 40 | 0 | 0 | 0 | 0 | 0 | 40 |
| E13c-both | 40 | 0 | 0 | 0 | 0 | 0 | 40 |
| E14 | 218 | 0 | 0 | 0 | 2 | 28 | 188 |
| E14-both | 218 | 0 | 0 | 0 | 1 | 28 | 189 |
| E14c | 26 | 0 | 0 | 0 | 0 | 4 | 22 |
| E14c-both | 26 | 0 | 0 | 0 | 0 | 4 | 22 |
| E15 | 32 | 0 | 0 | 0 | 0 | 4 | 28 |
| E15-both | 32 | 0 | 0 | 0 | 0 | 4 | 28 |
| E16 | 56 | 0 | 0 | 0 | 8 | 6 | 42 |
| E17 | 108 | 0 | 0 | 0 | 12 | 12 | 84 |
| E2 | 26 | 0 | 0 | 0 | 0 | 4 | 22 |
| E3 | 77 | 0 | 0 | 0 | 0 | 12 | 65 |
| E3c | 78 | 0 | 0 | 0 | 0 | 12 | 66 |
| E3c-both | 52 | 1 | 1 | 0 | 1 | 8 | 43 |
| E4 | 52 | 0 | 0 | 0 | 0 | 8 | 44 |
| E5 | 58 | 0 | 0 | 0 | 0 | 6 | 52 |
| E6 | 4 | 0 | 0 | 0 | 0 | 0 | 4 |
| E6-both | 4 | 0 | 0 | 0 | 0 | 0 | 4 |
| E7 | 83 | 0 | 0 | 0 | 0 | 12 | 71 |
| E8 | 20 | 0 | 0 | 0 | 0 | 0 | 20 |
| E8-both | 20 | 0 | 0 | 0 | 0 | 0 | 20 |
| E9 | 38 | 0 | 0 | 0 | 0 | 4 | 34 |
| E9-both | 38 | 0 | 0 | 0 | 0 | 4 | 34 |

**Totals: false auto-accept 1, false READY 1.**

## Leaks

| Case | status | detail |
|---|---|---|
| H14/images:E3c-one:H14-1_사업자등록증_사진.jpg:both | READY | business_registration_number: 4028561724→4028516724 |
