# Gate summary F

| corpus | files scored | false READY (submissions) | digital field accuracy | scan field accuracy | photo field accuracy | university_name scan / photo | review fields per submission scan / photo | auto-decided scan / photo |
|---|---|---|---|---|---|---|---|---|
| dev | 22 sets | 0 | 251/251 (100.0%) | 239/240 (99.6%) | 239/240 (99.6%) | 18/18 (100.0%) / 18/18 (100.0%) | 3.73 / 3.09 | 4/22 / 5/22 |
| holdout | 25 sets | 0 | 286/286 (100.0%) | 270/275 (98.2%) | 273/275 (99.3%) | 18/20 (90.0%) / 19/20 (95.0%) | 4.16 / 3.52 | 3/25 / 4/25 |
| holdout2 | 25 sets | 0 | 286/286 (100.0%) | 270/275 (98.2%) | 273/275 (99.3%) | 20/20 (100.0%) / 20/20 (100.0%) | 3.84 / 3.72 | 4/25 / 4/25 |

## Injected-error suites E1-E18

| corpus | cases | false auto-accept (single-error classes) | false auto-accept (E3c-both, owner-accepted residual) | false READY (other cases) | false READY (that residual case) | 95% upper bound for false READY (rule of three) |
|---|---|---|---|---|---|---|
| dev | 1354 | 0 | 0 | 0 | 0 | 0.22% |
| holdout | 1532 | 0 | 0 | 0 | 0 | 0.20% |
| holdout2 | 1523 | 0 | 1 | 0 | 1 | 0.20% |
