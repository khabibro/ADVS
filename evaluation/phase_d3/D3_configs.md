# Phase D3 configuration comparison (development data: test_variants, hold-out 1, hold-out 2)

| Config | Corpus | false READY | decision-blocking scanned / images | total unconfirmed scanned / images | auto-decided scanned / images | mean process ms |
|---|---|---|---|---|---|---|
| B0_D3 (C0) | dev | 0 | 5.41 / 4.82 | 7.23 / 6.59 | 1/22 / 1/22 | 31.2 / 37.8 |
| B0_D3 (C0) | holdout | 0 | 5.68 / 5.24 | 7.4 / 6.84 | 1/25 / 1/25 | 31.7 / 38.3 |
| B0_D3 (C0) | holdout2 | 0 | 5.64 / 5.56 | 7.36 / 7.12 | 1/25 / 1/25 | 31.0 / 38.7 |
| C1c (S8) | dev | 0 | 2.73 / 2.09 | 3.86 / 3.14 | 3/22 / 5/22 | 32.0 / 39.2 |
| C1c (S8) | holdout | 0 | 3.2 / 2.8 | 4.52 / 3.96 | 3/25 / 4/25 | 31.7 / 38.6 |
| C1c (S8) | holdout2 | 0 | 3 / 2.84 | 3.96 / 3.72 | 3/25 / 4/25 | 34.3 / 41.1 |
| C4 (S8+D3-7..9) | dev | 0 | 2.68 / 2.09 | 3.82 / 3.14 | 4/22 / 5/22 | 2088.1 / 609.1 |
| C4 (S8+D3-7..9) | holdout | 0 | 3.16 / 2.76 | 4.48 / 3.92 | 3/25 / 4/25 | 1893.0 / 592.3 |
| C4 (S8+D3-7..9) | holdout2 | 0 | 2.96 / 2.84 | 3.92 / 3.72 | 4/25 / 4/25 | 1998.1 / 619.7 |
| C5 (S9+D3-7..9) | dev | 0 | 2.68 / 2.09 | 3.82 / 3.14 | 4/22 / 5/22 | 199.2 / 200.4 |
| C5 (S9+D3-7..9) | holdout | 0 | 3.16 / 2.76 | 4.48 / 3.92 | 3/25 / 4/25 | 26.3 / 31.0 |
| C5 (S9+D3-7..9) | holdout2 | 0 | 2.96 / 2.84 | 3.92 / 3.72 | 4/25 / 4/25 | 24.6 / 30.3 |

## Injections E1-E18: false auto-accept / false READY (classes with a non-zero count are listed)

| Config | Corpus | cases | false auto-accept | false READY | classes with a non-zero count |
|---|---|---|---|---|---|
| B0_D3 | dev | 1353 | 0 | 0 | - |
| B0_D3 | holdout | 1532 | 0 | 0 | - |
| B0_D3 | holdout2 | 1523 | 1 | 0 | E3c-both (1/0) |
| C1c | dev | 1353 | 0 | 0 | - |
| C1c | holdout | 1532 | 0 | 0 | - |
| C1c | holdout2 | 1523 | 1 | 1 | E3c-both (1/1) |
| C4 | dev | 1354 | 0 | 0 | - |
| C4 | holdout | 1532 | 0 | 0 | - |
| C4 | holdout2 | 1523 | 1 | 1 | E3c-both (1/1) |
| C5 | dev | 1354 | 0 | 0 | - |
| C5 | holdout | 1532 | 0 | 0 | - |
| C5 | holdout2 | 1523 | 1 | 1 | E3c-both (1/1) |
