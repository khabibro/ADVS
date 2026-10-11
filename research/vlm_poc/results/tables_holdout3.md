# Tables — hold-out 3 (final judgement, once)

Fields scored: 960 (KNOWN_VALUE fields of files that both engines processed). Scorer `score_v2.py` sha256 `49674a9c03e464310cda0278782062e1a4b996e334ff8d8cbdc78d10b5ad2594`.

## 1. Exact-match accuracy, wrong non-null values and hallucinations (value not printed on the page)

| Input | Field group | n | A correct | B correct | A wrong non-null | B wrong non-null | B wrong and not on the page | B unresolved |
|---|---|---|---|---|---|---|---|---|
| digital | business number | 58 | 58/58 = 100.0% [93.8%–100.0%] | 58/58 = 100.0% [93.8%–100.0%] | 0/58 = 0.0% [0.0%–6.2%], rule of three ≤5.2% | 0/58 = 0.0% [0.0%–6.2%], rule of three ≤5.2% | 0/58 = 0.0% [0.0%–6.2%], rule of three ≤5.2% | 0/58 = 0.0% [0.0%–6.2%], rule of three ≤5.2% |
| digital | dates | 76 | 76/76 = 100.0% [95.2%–100.0%] | 75/76 = 98.7% [92.9%–99.8%] | 0/76 = 0.0% [0.0%–4.8%], rule of three ≤3.9% | 0/76 = 0.0% [0.0%–4.8%], rule of three ≤3.9% | 0/76 = 0.0% [0.0%–4.8%], rule of three ≤3.9% | 1/76 = 1.3% [0.2%–7.1%] |
| digital | student number / GPA | 41 | 41/41 = 100.0% [91.4%–100.0%] | 38/41 = 92.7% [80.6%–97.5%] | 0/41 = 0.0% [0.0%–8.6%], rule of three ≤7.3% | 1/41 = 2.4% [0.4%–12.6%] | 1/41 = 2.4% [0.4%–12.6%] | 2/41 = 4.9% [1.3%–16.1%] |
| digital | names and text | 114 | 113/114 = 99.1% [95.2%–99.8%] | 88/114 = 77.2% [68.7%–83.9%] | 0/114 = 0.0% [0.0%–3.3%], rule of three ≤2.6% | 5/114 = 4.4% [1.9%–9.9%] | 5/114 = 4.4% [1.9%–9.9%] | 21/114 = 18.4% [12.4%–26.5%] |
| digital | ALL | 289 | 288/289 = 99.7% [98.1%–99.9%] | 259/289 = 89.6% [85.6%–92.6%] | 0/289 = 0.0% [0.0%–1.3%], rule of three ≤1.0% | 6/289 = 2.1% [1.0%–4.5%] | 6/289 = 2.1% [1.0%–4.5%] | 24/289 = 8.3% [5.6%–12.1%] |
| scan | business number | 72 | 72/72 = 100.0% [94.9%–100.0%] | 71/72 = 98.6% [92.5%–99.8%] | 0/72 = 0.0% [0.0%–5.1%], rule of three ≤4.2% | 0/72 = 0.0% [0.0%–5.1%], rule of three ≤4.2% | 0/72 = 0.0% [0.0%–5.1%], rule of three ≤4.2% | 1/72 = 1.4% [0.2%–7.5%] |
| scan | dates | 101 | 99/101 = 98.0% [93.1%–99.5%] | 97/101 = 96.0% [90.3%–98.4%] | 0/101 = 0.0% [0.0%–3.7%], rule of three ≤3.0% | 0/101 = 0.0% [0.0%–3.7%], rule of three ≤3.0% | 0/101 = 0.0% [0.0%–3.7%], rule of three ≤3.0% | 4/101 = 4.0% [1.6%–9.7%] |
| scan | student number / GPA | 61 | 56/61 = 91.8% [82.2%–96.4%] | 51/61 = 83.6% [72.4%–90.8%] | 0/61 = 0.0% [0.0%–5.9%], rule of three ≤4.9% | 1/61 = 1.6% [0.3%–8.7%] | 1/61 = 1.6% [0.3%–8.7%] | 9/61 = 14.8% [8.0%–25.7%] |
| scan | names and text | 162 | 157/162 = 96.9% [93.0%–98.7%] | 134/162 = 82.7% [76.2%–87.8%] | 0/162 = 0.0% [0.0%–2.3%], rule of three ≤1.9% | 3/162 = 1.9% [0.6%–5.3%] | 3/162 = 1.9% [0.6%–5.3%] | 25/162 = 15.4% [10.7%–21.8%] |
| scan | ALL | 396 | 384/396 = 97.0% [94.8%–98.3%] | 353/396 = 89.1% [85.7%–91.8%] | 0/396 = 0.0% [0.0%–1.0%], rule of three ≤0.8% | 4/396 = 1.0% [0.4%–2.6%] | 4/396 = 1.0% [0.4%–2.6%] | 39/396 = 9.8% [7.3%–13.2%] |
| photo | business number | 56 | 56/56 = 100.0% [93.6%–100.0%] | 54/56 = 96.4% [87.9%–99.0%] | 0/56 = 0.0% [0.0%–6.4%], rule of three ≤5.4% | 0/56 = 0.0% [0.0%–6.4%], rule of three ≤5.4% | 0/56 = 0.0% [0.0%–6.4%], rule of three ≤5.4% | 2/56 = 3.6% [1.0%–12.1%] |
| photo | dates | 74 | 74/74 = 100.0% [95.1%–100.0%] | 73/74 = 98.6% [92.7%–99.8%] | 0/74 = 0.0% [0.0%–4.9%], rule of three ≤4.1% | 0/74 = 0.0% [0.0%–4.9%], rule of three ≤4.1% | 0/74 = 0.0% [0.0%–4.9%], rule of three ≤4.1% | 1/74 = 1.4% [0.2%–7.3%] |
| photo | student number / GPA | 39 | 39/39 = 100.0% [91.0%–100.0%] | 36/39 = 92.3% [79.7%–97.3%] | 0/39 = 0.0% [0.0%–9.0%], rule of three ≤7.7% | 0/39 = 0.0% [0.0%–9.0%], rule of three ≤7.7% | 0/39 = 0.0% [0.0%–9.0%], rule of three ≤7.7% | 3/39 = 7.7% [2.7%–20.3%] |
| photo | names and text | 106 | 104/106 = 98.1% [93.4%–99.5%] | 85/106 = 80.2% [71.6%–86.7%] | 0/106 = 0.0% [0.0%–3.5%], rule of three ≤2.8% | 1/106 = 0.9% [0.2%–5.2%] | 1/106 = 0.9% [0.2%–5.2%] | 20/106 = 18.9% [12.6%–27.4%] |
| photo | ALL | 275 | 273/275 = 99.3% [97.4%–99.8%] | 248/275 = 90.2% [86.1%–93.2%] | 0/275 = 0.0% [0.0%–1.4%], rule of three ≤1.1% | 1/275 = 0.4% [0.1%–2.0%] | 1/275 = 0.4% [0.1%–2.0%] | 26/275 = 9.5% [6.5%–13.5%] |

## 2. Per document type (all input types together)

| Document type | n | A correct | B correct |
|---|---|---|---|
| BUSINESS_REGISTRATION_CERTIFICATE | 102 | 102/102 = 100.0% [96.4%–100.0%] | 102/102 = 100.0% [96.4%–100.0%] |
| ENROLLMENT_CERTIFICATE | 201 | 188/201 = 93.5% [89.3%–96.2%] | 180/201 = 89.6% [84.6%–93.1%] |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | 135 | 135/135 = 100.0% [97.2%–100.0%] | 88/135 = 65.2% [56.8%–72.7%] |
| SME_CONFIRMATION_CERTIFICATE | 180 | 179/180 = 99.4% [96.9%–99.9%] | 180/180 = 100.0% [97.9%–100.0%] |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | 132 | 132/132 = 100.0% [97.2%–100.0%] | 124/132 = 93.9% [88.5%–96.9%] |
| TRANSCRIPT | 210 | 209/210 = 99.5% [97.4%–99.9%] | 186/210 = 88.6% [83.6%–92.2%] |

## 3. Joint errors, A (current OCR) and B (VLM page parse)

Error = not correct (wrong or unresolved). 'Identical' = both produced the same wrong value.

| Input | Field group | n | P(A err) | P(B err) | P(A err and B err) | P(both wrong and identical output) |
|---|---|---|---|---|---|---|
| digital | business number | 58 | 0/58 = 0.0% [0.0%–6.2%], rule of three ≤5.2% | 0/58 = 0.0% [0.0%–6.2%], rule of three ≤5.2% | 0/58 = 0.0% [0.0%–6.2%], rule of three ≤5.2% | 0/58 = 0.0% [0.0%–6.2%], rule of three ≤5.2% |
| digital | dates | 76 | 0/76 = 0.0% [0.0%–4.8%], rule of three ≤3.9% | 1/76 = 1.3% [0.2%–7.1%] | 0/76 = 0.0% [0.0%–4.8%], rule of three ≤3.9% | 0/76 = 0.0% [0.0%–4.8%], rule of three ≤3.9% |
| digital | student number / GPA | 41 | 0/41 = 0.0% [0.0%–8.6%], rule of three ≤7.3% | 3/41 = 7.3% [2.5%–19.4%] | 0/41 = 0.0% [0.0%–8.6%], rule of three ≤7.3% | 0/41 = 0.0% [0.0%–8.6%], rule of three ≤7.3% |
| digital | names and text | 114 | 1/114 = 0.9% [0.2%–4.8%] | 26/114 = 22.8% [16.1%–31.3%] | 0/114 = 0.0% [0.0%–3.3%], rule of three ≤2.6% | 0/114 = 0.0% [0.0%–3.3%], rule of three ≤2.6% |
| digital | ALL | 289 | 1/289 = 0.3% [0.1%–1.9%] | 30/289 = 10.4% [7.4%–14.4%] | 0/289 = 0.0% [0.0%–1.3%], rule of three ≤1.0% | 0/289 = 0.0% [0.0%–1.3%], rule of three ≤1.0% |
| scan | business number | 72 | 0/72 = 0.0% [0.0%–5.1%], rule of three ≤4.2% | 1/72 = 1.4% [0.2%–7.5%] | 0/72 = 0.0% [0.0%–5.1%], rule of three ≤4.2% | 0/72 = 0.0% [0.0%–5.1%], rule of three ≤4.2% |
| scan | dates | 101 | 2/101 = 2.0% [0.5%–6.9%] | 4/101 = 4.0% [1.6%–9.7%] | 1/101 = 1.0% [0.2%–5.4%] | 0/101 = 0.0% [0.0%–3.7%], rule of three ≤3.0% |
| scan | student number / GPA | 61 | 5/61 = 8.2% [3.6%–17.8%] | 10/61 = 16.4% [9.2%–27.6%] | 1/61 = 1.6% [0.3%–8.7%] | 0/61 = 0.0% [0.0%–5.9%], rule of three ≤4.9% |
| scan | names and text | 162 | 5/162 = 3.1% [1.3%–7.0%] | 28/162 = 17.3% [12.2%–23.8%] | 1/162 = 0.6% [0.1%–3.4%] | 0/162 = 0.0% [0.0%–2.3%], rule of three ≤1.9% |
| scan | ALL | 396 | 12/396 = 3.0% [1.7%–5.2%] | 43/396 = 10.9% [8.2%–14.3%] | 3/396 = 0.8% [0.3%–2.2%] | 0/396 = 0.0% [0.0%–1.0%], rule of three ≤0.8% |
| photo | business number | 56 | 0/56 = 0.0% [0.0%–6.4%], rule of three ≤5.4% | 2/56 = 3.6% [1.0%–12.1%] | 0/56 = 0.0% [0.0%–6.4%], rule of three ≤5.4% | 0/56 = 0.0% [0.0%–6.4%], rule of three ≤5.4% |
| photo | dates | 74 | 0/74 = 0.0% [0.0%–4.9%], rule of three ≤4.1% | 1/74 = 1.4% [0.2%–7.3%] | 0/74 = 0.0% [0.0%–4.9%], rule of three ≤4.1% | 0/74 = 0.0% [0.0%–4.9%], rule of three ≤4.1% |
| photo | student number / GPA | 39 | 0/39 = 0.0% [0.0%–9.0%], rule of three ≤7.7% | 3/39 = 7.7% [2.7%–20.3%] | 0/39 = 0.0% [0.0%–9.0%], rule of three ≤7.7% | 0/39 = 0.0% [0.0%–9.0%], rule of three ≤7.7% |
| photo | names and text | 106 | 2/106 = 1.9% [0.5%–6.6%] | 21/106 = 19.8% [13.3%–28.4%] | 0/106 = 0.0% [0.0%–3.5%], rule of three ≤2.8% | 0/106 = 0.0% [0.0%–3.5%], rule of three ≤2.8% |
| photo | ALL | 275 | 2/275 = 0.7% [0.2%–2.6%] | 27/275 = 9.8% [6.8%–13.9%] | 0/275 = 0.0% [0.0%–1.4%], rule of three ≤1.1% | 0/275 = 0.0% [0.0%–1.4%], rule of three ≤1.1% |

## 4. Simulated automation gain if exact agreement were accepted as confirmation (no production change)

Rows are fields that the current system leaves to a person (A decision NEEDS_HUMAN, scans and photos). Agreement = both engines produced the same normalised value.

| Method | Field group | fields needing a person | would be auto-accepted | of those wrong (simulated false auto-accepts) |
|---|---|---|---|---|
| B page parse | business number | 37 | 36/37 = 97.3% [86.2%–99.5%] | 0/36 = 0.0% [0.0%–9.6%], rule of three ≤8.3% |
| B page parse | dates | 56 | 52/56 = 92.9% [83.0%–97.2%] | 0/52 = 0.0% [0.0%–6.9%], rule of three ≤5.8% |
| B page parse | student number / GPA | 32 | 25/32 = 78.1% [61.2%–89.0%] | 0/25 = 0.0% [0.0%–13.3%], rule of three ≤12.0% |
| B page parse | names and text | 105 | 92/105 = 87.6% [80.0%–92.6%] | 0/92 = 0.0% [0.0%–4.0%], rule of three ≤3.3% |
| B page parse | ALL | 230 | 205/230 = 89.1% [84.4%–92.5%] | 0/205 = 0.0% [0.0%–1.8%], rule of three ≤1.5% |
| D selective crops | business number | 37 | 36/37 = 97.3% [86.2%–99.5%] | 0/36 = 0.0% [0.0%–9.6%], rule of three ≤8.3% |
| D selective crops | dates | 55 | 55/55 = 100.0% [93.5%–100.0%] | 0/55 = 0.0% [0.0%–6.5%], rule of three ≤5.5% |
| D selective crops | student number / GPA | 27 | 27/27 = 100.0% [87.5%–100.0%] | 0/27 = 0.0% [0.0%–12.5%], rule of three ≤11.1% |
| D selective crops | names and text | 98 | 97/98 = 99.0% [94.4%–99.8%] | 0/97 = 0.0% [0.0%–3.8%], rule of three ≤3.1% |
| D selective crops | ALL | 217 | 215/217 = 99.1% [96.7%–99.7%] | 0/215 = 0.0% [0.0%–1.8%], rule of three ≤1.4% |

## 5. Method D: VLM reading of field crops (confirms or disputes A's value)

| Input | Field group | crops | VLM parsed reading equals the expected value | A value wrong | of those, VLM disputes A | A value right | of those, VLM confirms A |
|---|---|---|---|---|---|---|---|
| digital | business number | 58 | 58/58 = 100.0% [93.8%–100.0%] | 0 | n/a | 58 | 58/58 = 100.0% [93.8%–100.0%] |
| digital | dates | 76 | 76/76 = 100.0% [95.2%–100.0%] | 0 | n/a | 76 | 76/76 = 100.0% [95.2%–100.0%] |
| digital | student number / GPA | 31 | 31/31 = 100.0% [89.0%–100.0%] | 0 | n/a | 31 | 31/31 = 100.0% [89.0%–100.0%] |
| digital | ALL | 165 | 165/165 = 100.0% [97.7%–100.0%] | 0 | n/a | 165 | 165/165 = 100.0% [97.7%–100.0%] |
| scan | business number | 72 | 71/72 = 98.6% [92.5%–99.8%] | 0 | n/a | 72 | 71/72 = 98.6% [92.5%–99.8%] |
| scan | dates | 100 | 100/100 = 100.0% [96.3%–100.0%] | 0 | n/a | 100 | 100/100 = 100.0% [96.3%–100.0%] |
| scan | student number / GPA | 44 | 44/44 = 100.0% [92.0%–100.0%] | 0 | n/a | 44 | 44/44 = 100.0% [92.0%–100.0%] |
| scan | names and text | 63 | n/a | 0 | n/a | 63 | 62/63 = 98.4% [91.5%–99.7%] |
| scan | ALL | 279 | 215/216 = 99.5% [97.4%–99.9%] | 0 | n/a | 279 | 277/279 = 99.3% [97.4%–99.8%] |
| photo | business number | 56 | 56/56 = 100.0% [93.6%–100.0%] | 0 | n/a | 56 | 56/56 = 100.0% [93.6%–100.0%] |
| photo | dates | 74 | 74/74 = 100.0% [95.1%–100.0%] | 0 | n/a | 74 | 74/74 = 100.0% [95.1%–100.0%] |
| photo | student number / GPA | 31 | 31/31 = 100.0% [89.0%–100.0%] | 0 | n/a | 31 | 31/31 = 100.0% [89.0%–100.0%] |
| photo | names and text | 35 | n/a | 0 | n/a | 35 | 35/35 = 100.0% [90.1%–100.0%] |
| photo | ALL | 196 | 161/161 = 100.0% [97.7%–100.0%] | 0 | n/a | 196 | 196/196 = 100.0% [98.1%–100.0%] |

## 6. Error catching on the injected-error suites (E1–E18)

The suite corrupts the OCR reading of a field; the VLM reads the real pixels. Caught = the VLM value exists and differs from the injected one.

| Method | injected targets with a reading | caught | missed (VLM reproduces the injected value) | no usable reading |
|---|---|---|---|---|
| B page parse | 1557 | 1459/1557 = 93.7% [92.4%–94.8%] | 0/1557 = 0.0% [0.0%–0.2%], rule of three ≤0.2% | 98 |
| D field crop | 1385 | 1385/1385 = 100.0% [99.7%–100.0%] | 0/1385 = 0.0% [0.0%–0.3%], rule of three ≤0.2% | 0 |

## 7. Speed

- B page parse: 270 files, 277 pages; per page median 8.3 s, mean 9.9 s, p95 19.9 s (Apple M3 Pro, llama.cpp Metal, layout model on CPU; other jobs were running at the same time on part of the data, so these are upper bounds).
- D field crop: 640 crops; median 0.34 s, mean 0.37 s, p95 0.79 s per crop.
