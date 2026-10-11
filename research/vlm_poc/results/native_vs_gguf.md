| file | pages | identical text | character similarity | blocks identical / total | native s | GGUF s |
|---|---|---|---|---|---|---|
| S01-1_재학증명서_사진.jpg | 1 | 1/1 | 1.0000 | 20/20 | 75.7 | 7.09 |
| S01-2_성적증명서_스캔.pdf | 1 | 0/1 | 0.8342 | 20/23 | 2213.0 | 12.15 |
| B01-4_4대사회보험료완납증명서_스캔.pdf | 1 | 1/1 | 1.0000 | 3/3 | 1193.5 | 11.4 |
| B01-3_납세증명서_스캔.pdf | 1 | 0/1 | 0.9970 | 12/16 | 171.1 | 12.03 |
| B01-1_사업자등록증_사진.jpg | 1 | 0/1 | 0.9970 | 21/23 | 89.9 | 8.17 |
| B01-2_중소기업확인서_사진.png | 1 | 0/1 | 0.9948 | 17/18 | 84.9 | 8.19 |
| B01-1_사업자등록증.pdf | 1 | 0/1 | 0.9939 | 21/23 | 95.1 | 10.68 |
| S10-1_재학증명서_스캔.pdf | 1 | 1/1 | 1.0000 | 19/20 | 73.3 | 7.02 |

Pages with identical text: 3/8

Field level (same 8 files, production extractors, adapter mode "both"): 30 expected fields; extracted value identical on the two routes for 29/30 (96.7%). The one difference: transcript `gpa` — native 3.87, GGUF 3.8, expected 3.80 (the GGUF route was right, the native route wrong). Native correct 26/30, GGUF correct 27/30. Native seconds are inflated by other jobs running on the machine at the same time (one page took 2213 s while the page parse and the evaluation were running); the first uncontended native page took 75.7 s (114 s earlier in the smoke test), GGUF 7–12 s.
Sample of 8 is small: it supports "no systematic degradation from the GGUF route", not "identical".
