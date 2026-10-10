# Tables — development data (test_variants + hold-out 1 + hold-out 2), final settings

Fields scored: 2967 (KNOWN_VALUE fields of files that both engines processed). Scorer `score_v2.py` sha256 `49674a9c03e464310cda0278782062e1a4b996e334ff8d8cbdc78d10b5ad2594`.

## 1. Exact-match accuracy, wrong non-null values and hallucinations (value not printed on the page)

| Input | Field group | n | A correct | B correct | A wrong non-null | B wrong non-null | B wrong and not on the page | B unresolved |
|---|---|---|---|---|---|---|---|---|
| digital | business number | 171 | 171/171 = 100.0% [97.8%–100.0%] | 170/171 = 99.4% [96.8%–99.9%] | 0/171 = 0.0% [0.0%–2.2%], rule of three ≤1.8% | 0/171 = 0.0% [0.0%–2.2%], rule of three ≤1.8% | 0/171 = 0.0% [0.0%–2.2%], rule of three ≤1.8% | 1/171 = 0.6% [0.1%–3.2%] |
| digital | dates | 227 | 227/227 = 100.0% [98.3%–100.0%] | 225/227 = 99.1% [96.8%–99.8%] | 0/227 = 0.0% [0.0%–1.7%], rule of three ≤1.3% | 0/227 = 0.0% [0.0%–1.7%], rule of three ≤1.3% | 0/227 = 0.0% [0.0%–1.7%], rule of three ≤1.3% | 2/227 = 0.9% [0.2%–3.2%] |
| digital | student number / GPA | 127 | 127/127 = 100.0% [97.1%–100.0%] | 99/127 = 78.0% [70.0%–84.3%] | 0/127 = 0.0% [0.0%–2.9%], rule of three ≤2.4% | 2/127 = 1.6% [0.4%–5.6%] | 2/127 = 1.6% [0.4%–5.6%] | 26/127 = 20.5% [14.4%–28.3%] |
| digital | names and text | 347 | 347/347 = 100.0% [98.9%–100.0%] | 291/347 = 83.9% [79.6%–87.4%] | 0/347 = 0.0% [0.0%–1.1%], rule of three ≤0.9% | 1/347 = 0.3% [0.1%–1.6%] | 1/347 = 0.3% [0.1%–1.6%] | 55/347 = 15.9% [12.4%–20.1%] |
| digital | ALL | 872 | 872/872 = 100.0% [99.6%–100.0%] | 785/872 = 90.0% [87.9%–91.8%] | 0/872 = 0.0% [0.0%–0.4%], rule of three ≤0.3% | 3/872 = 0.3% [0.1%–1.0%] | 3/872 = 0.3% [0.1%–1.0%] | 84/872 = 9.6% [7.8%–11.8%] |
| scan | business number | 225 | 225/225 = 100.0% [98.3%–100.0%] | 214/225 = 95.1% [91.5%–97.2%] | 0/225 = 0.0% [0.0%–1.7%], rule of three ≤1.3% | 0/225 = 0.0% [0.0%–1.7%], rule of three ≤1.3% | 0/225 = 0.0% [0.0%–1.7%], rule of three ≤1.3% | 11/225 = 4.9% [2.8%–8.5%] |
| scan | dates | 325 | 314/325 = 96.6% [94.0%–98.1%] | 320/325 = 98.5% [96.4%–99.3%] | 0/325 = 0.0% [0.0%–1.2%], rule of three ≤0.9% | 0/325 = 0.0% [0.0%–1.2%], rule of three ≤0.9% | 0/325 = 0.0% [0.0%–1.2%], rule of three ≤0.9% | 5/325 = 1.5% [0.7%–3.6%] |
| scan | student number / GPA | 214 | 205/214 = 95.8% [92.2%–97.8%] | 153/214 = 71.5% [65.1%–77.1%] | 0/214 = 0.0% [0.0%–1.8%], rule of three ≤1.4% | 1/214 = 0.5% [0.1%–2.6%] | 1/214 = 0.5% [0.1%–2.6%] | 60/214 = 28.0% [22.4%–34.4%] |
| scan | names and text | 541 | 509/541 = 94.1% [91.8%–95.8%] | 457/541 = 84.5% [81.2%–87.3%] | 1/541 = 0.2% [0.0%–1.0%] | 2/541 = 0.4% [0.1%–1.3%] | 2/541 = 0.4% [0.1%–1.3%] | 82/541 = 15.2% [12.4%–18.4%] |
| scan | ALL | 1305 | 1253/1305 = 96.0% [94.8%–96.9%] | 1144/1305 = 87.7% [85.8%–89.3%] | 1/1305 = 0.1% [0.0%–0.4%] | 3/1305 = 0.2% [0.1%–0.7%] | 3/1305 = 0.2% [0.1%–0.7%] | 158/1305 = 12.1% [10.4%–14.0%] |
| photo | business number | 160 | 159/160 = 99.4% [96.5%–99.9%] | 154/160 = 96.2% [92.1%–98.3%] | 0/160 = 0.0% [0.0%–2.3%], rule of three ≤1.9% | 0/160 = 0.0% [0.0%–2.3%], rule of three ≤1.9% | 0/160 = 0.0% [0.0%–2.3%], rule of three ≤1.9% | 6/160 = 3.8% [1.7%–7.9%] |
| photo | dates | 212 | 212/212 = 100.0% [98.2%–100.0%] | 211/212 = 99.5% [97.4%–99.9%] | 0/212 = 0.0% [0.0%–1.8%], rule of three ≤1.4% | 0/212 = 0.0% [0.0%–1.8%], rule of three ≤1.4% | 0/212 = 0.0% [0.0%–1.8%], rule of three ≤1.4% | 1/212 = 0.5% [0.1%–2.6%] |
| photo | student number / GPA | 113 | 112/113 = 99.1% [95.2%–99.8%] | 87/113 = 77.0% [68.4%–83.8%] | 0/113 = 0.0% [0.0%–3.3%], rule of three ≤2.7% | 3/113 = 2.7% [0.9%–7.5%] | 3/113 = 2.7% [0.9%–7.5%] | 23/113 = 20.4% [14.0%–28.7%] |
| photo | names and text | 305 | 302/305 = 99.0% [97.1%–99.7%] | 254/305 = 83.3% [78.7%–87.0%] | 0/305 = 0.0% [0.0%–1.2%], rule of three ≤1.0% | 0/305 = 0.0% [0.0%–1.2%], rule of three ≤1.0% | 0/305 = 0.0% [0.0%–1.2%], rule of three ≤1.0% | 51/305 = 16.7% [13.0%–21.3%] |
| photo | ALL | 790 | 785/790 = 99.4% [98.5%–99.7%] | 706/790 = 89.4% [87.0%–91.3%] | 0/790 = 0.0% [0.0%–0.5%], rule of three ≤0.4% | 3/790 = 0.4% [0.1%–1.1%] | 3/790 = 0.4% [0.1%–1.1%] | 81/790 = 10.3% [8.3%–12.6%] |

## 2. Per document type (all input types together)

| Document type | n | A correct | B correct |
|---|---|---|---|
| BUSINESS_REGISTRATION_CERTIFICATE | 314 | 312/314 = 99.4% [97.7%–99.8%] | 313/314 = 99.7% [98.2%–99.9%] |
| ENROLLMENT_CERTIFICATE | 654 | 608/654 = 93.0% [90.7%–94.7%] | 565/654 = 86.4% [83.6%–88.8%] |
| NATIONAL_TAX_PAYMENT_CERTIFICATE | 399 | 398/399 = 99.7% [98.6%–100.0%] | 265/399 = 66.4% [61.6%–70.9%] |
| SME_CONFIRMATION_CERTIFICATE | 532 | 527/532 = 99.1% [97.8%–99.6%] | 532/532 = 100.0% [99.3%–100.0%] |
| SOCIAL_INSURANCE_PAYMENT_CERTIFICATE | 390 | 390/390 = 100.0% [99.0%–100.0%] | 373/390 = 95.6% [93.1%–97.3%] |
| TRANSCRIPT | 678 | 675/678 = 99.6% [98.7%–99.8%] | 587/678 = 86.6% [83.8%–88.9%] |

## 3. Joint errors, A (current OCR) and B (VLM page parse)

Error = not correct (wrong or unresolved). 'Identical' = both produced the same wrong value.

| Input | Field group | n | P(A err) | P(B err) | P(A err and B err) | P(both wrong and identical output) |
|---|---|---|---|---|---|---|
| digital | business number | 171 | 0/171 = 0.0% [0.0%–2.2%], rule of three ≤1.8% | 1/171 = 0.6% [0.1%–3.2%] | 0/171 = 0.0% [0.0%–2.2%], rule of three ≤1.8% | 0/171 = 0.0% [0.0%–2.2%], rule of three ≤1.8% |
| digital | dates | 227 | 0/227 = 0.0% [0.0%–1.7%], rule of three ≤1.3% | 2/227 = 0.9% [0.2%–3.2%] | 0/227 = 0.0% [0.0%–1.7%], rule of three ≤1.3% | 0/227 = 0.0% [0.0%–1.7%], rule of three ≤1.3% |
| digital | student number / GPA | 127 | 0/127 = 0.0% [0.0%–2.9%], rule of three ≤2.4% | 28/127 = 22.0% [15.7%–30.0%] | 0/127 = 0.0% [0.0%–2.9%], rule of three ≤2.4% | 0/127 = 0.0% [0.0%–2.9%], rule of three ≤2.4% |
| digital | names and text | 347 | 0/347 = 0.0% [0.0%–1.1%], rule of three ≤0.9% | 56/347 = 16.1% [12.6%–20.4%] | 0/347 = 0.0% [0.0%–1.1%], rule of three ≤0.9% | 0/347 = 0.0% [0.0%–1.1%], rule of three ≤0.9% |
| digital | ALL | 872 | 0/872 = 0.0% [0.0%–0.4%], rule of three ≤0.3% | 87/872 = 10.0% [8.2%–12.1%] | 0/872 = 0.0% [0.0%–0.4%], rule of three ≤0.3% | 0/872 = 0.0% [0.0%–0.4%], rule of three ≤0.3% |
| scan | business number | 225 | 0/225 = 0.0% [0.0%–1.7%], rule of three ≤1.3% | 11/225 = 4.9% [2.8%–8.5%] | 0/225 = 0.0% [0.0%–1.7%], rule of three ≤1.3% | 0/225 = 0.0% [0.0%–1.7%], rule of three ≤1.3% |
| scan | dates | 325 | 11/325 = 3.4% [1.9%–6.0%] | 5/325 = 1.5% [0.7%–3.6%] | 4/325 = 1.2% [0.5%–3.1%] | 0/325 = 0.0% [0.0%–1.2%], rule of three ≤0.9% |
| scan | student number / GPA | 214 | 9/214 = 4.2% [2.2%–7.8%] | 61/214 = 28.5% [22.9%–34.9%] | 5/214 = 2.3% [1.0%–5.4%] | 0/214 = 0.0% [0.0%–1.8%], rule of three ≤1.4% |
| scan | names and text | 541 | 32/541 = 5.9% [4.2%–8.2%] | 84/541 = 15.5% [12.7%–18.8%] | 7/541 = 1.3% [0.6%–2.6%] | 0/541 = 0.0% [0.0%–0.7%], rule of three ≤0.6% |
| scan | ALL | 1305 | 52/1305 = 4.0% [3.1%–5.2%] | 161/1305 = 12.3% [10.7%–14.2%] | 16/1305 = 1.2% [0.8%–2.0%] | 0/1305 = 0.0% [0.0%–0.3%], rule of three ≤0.2% |
| photo | business number | 160 | 1/160 = 0.6% [0.1%–3.5%] | 6/160 = 3.8% [1.7%–7.9%] | 0/160 = 0.0% [0.0%–2.3%], rule of three ≤1.9% | 0/160 = 0.0% [0.0%–2.3%], rule of three ≤1.9% |
| photo | dates | 212 | 0/212 = 0.0% [0.0%–1.8%], rule of three ≤1.4% | 1/212 = 0.5% [0.1%–2.6%] | 0/212 = 0.0% [0.0%–1.8%], rule of three ≤1.4% | 0/212 = 0.0% [0.0%–1.8%], rule of three ≤1.4% |
| photo | student number / GPA | 113 | 1/113 = 0.9% [0.2%–4.8%] | 26/113 = 23.0% [16.2%–31.6%] | 1/113 = 0.9% [0.2%–4.8%] | 0/113 = 0.0% [0.0%–3.3%], rule of three ≤2.7% |
| photo | names and text | 305 | 3/305 = 1.0% [0.3%–2.9%] | 51/305 = 16.7% [13.0%–21.3%] | 1/305 = 0.3% [0.1%–1.8%] | 0/305 = 0.0% [0.0%–1.2%], rule of three ≤1.0% |
| photo | ALL | 790 | 5/790 = 0.6% [0.3%–1.5%] | 84/790 = 10.6% [8.7%–13.0%] | 2/790 = 0.3% [0.1%–0.9%] | 0/790 = 0.0% [0.0%–0.5%], rule of three ≤0.4% |

## 4. Simulated automation gain if exact agreement were accepted as confirmation (no production change)

Rows are fields that the current system leaves to a person (A decision NEEDS_HUMAN, scans and photos). Agreement = both engines produced the same normalised value.

| Method | Field group | fields needing a person | would be auto-accepted | of those wrong (simulated false auto-accepts) |
|---|---|---|---|---|
| B page parse | business number | 104 | 97/104 = 93.3% [86.8%–96.7%] | 0/97 = 0.0% [0.0%–3.8%], rule of three ≤3.1% |
| B page parse | dates | 188 | 175/188 = 93.1% [88.5%–95.9%] | 0/175 = 0.0% [0.0%–2.1%], rule of three ≤1.7% |
| B page parse | student number / GPA | 68 | 47/68 = 69.1% [57.4%–78.8%] | 0/47 = 0.0% [0.0%–7.6%], rule of three ≤6.4% |
| B page parse | names and text | 280 | 218/280 = 77.9% [72.6%–82.3%] | 0/218 = 0.0% [0.0%–1.7%], rule of three ≤1.4% |
| B page parse | ALL | 640 | 537/640 = 83.9% [80.9%–86.5%] | 0/537 = 0.0% [0.0%–0.7%], rule of three ≤0.6% |
| D selective crops | business number | 103 | 100/103 = 97.1% [91.8%–99.0%] | 0/100 = 0.0% [0.0%–3.7%], rule of three ≤3.0% |
| D selective crops | dates | 177 | 177/177 = 100.0% [97.9%–100.0%] | 0/177 = 0.0% [0.0%–2.1%], rule of three ≤1.7% |
| D selective crops | student number / GPA | 58 | 58/58 = 100.0% [93.8%–100.0%] | 0/58 = 0.0% [0.0%–6.2%], rule of three ≤5.2% |
| D selective crops | names and text | 246 | 225/246 = 91.5% [87.3%–94.3%] | 1/225 = 0.4% [0.1%–2.5%] |
| D selective crops | ALL | 584 | 560/584 = 95.9% [94.0%–97.2%] | 1/560 = 0.2% [0.0%–1.0%] |

## 5. Method D: VLM reading of field crops (confirms or disputes A's value)

| Input | Field group | crops | VLM parsed reading equals the expected value | A value wrong | of those, VLM disputes A | A value right | of those, VLM confirms A |
|---|---|---|---|---|---|---|---|
| digital | business number | 171 | 171/171 = 100.0% [97.8%–100.0%] | 0 | n/a | 171 | 171/171 = 100.0% [97.8%–100.0%] |
| digital | dates | 227 | 226/227 = 99.6% [97.5%–99.9%] | 0 | n/a | 227 | 226/227 = 99.6% [97.5%–99.9%] |
| digital | student number / GPA | 96 | 96/96 = 100.0% [96.2%–100.0%] | 0 | n/a | 96 | 96/96 = 100.0% [96.2%–100.0%] |
| digital | ALL | 494 | 493/494 = 99.8% [98.9%–100.0%] | 0 | n/a | 494 | 493/494 = 99.8% [98.9%–100.0%] |
| scan | business number | 225 | 222/225 = 98.7% [96.2%–99.5%] | 0 | n/a | 225 | 222/225 = 98.7% [96.2%–99.5%] |
| scan | dates | 314 | 314/314 = 100.0% [98.8%–100.0%] | 0 | n/a | 314 | 314/314 = 100.0% [98.8%–100.0%] |
| scan | student number / GPA | 153 | 153/153 = 100.0% [97.6%–100.0%] | 0 | n/a | 153 | 153/153 = 100.0% [97.6%–100.0%] |
| scan | names and text | 175 | n/a | 1 | 0/1 = 0.0% [0.0%–79.3%], n too small for a bound | 174 | 160/174 = 92.0% [86.9%–95.1%] |
| scan | ALL | 867 | 689/692 = 99.6% [98.7%–99.9%] | 1 | 0/1 = 0.0% [0.0%–79.3%], n too small for a bound | 866 | 849/866 = 98.0% [96.9%–98.8%] |
| photo | business number | 159 | 159/159 = 100.0% [97.6%–100.0%] | 0 | n/a | 159 | 159/159 = 100.0% [97.6%–100.0%] |
| photo | dates | 212 | 212/212 = 100.0% [98.2%–100.0%] | 0 | n/a | 212 | 212/212 = 100.0% [98.2%–100.0%] |
| photo | student number / GPA | 84 | 84/84 = 100.0% [95.6%–100.0%] | 0 | n/a | 84 | 84/84 = 100.0% [95.6%–100.0%] |
| photo | names and text | 71 | n/a | 0 | n/a | 71 | 64/71 = 90.1% [81.0%–95.1%] |
| photo | ALL | 526 | 455/455 = 100.0% [99.2%–100.0%] | 0 | n/a | 526 | 519/526 = 98.7% [97.3%–99.4%] |

## 6. Error catching on the injected-error suites (E1–E18)

The suite corrupts the OCR reading of a field; the VLM reads the real pixels. Caught = the VLM value exists and differs from the injected one.

| Method | injected targets with a reading | caught | missed (VLM reproduces the injected value) | no usable reading |
|---|---|---|---|---|
| B page parse | 4331 | 3876/4331 = 89.5% [88.5%–90.4%] | 0/4331 = 0.0% [0.0%–0.1%], rule of three ≤0.1% | 455 |
| D field crop | 3828 | 3828/3828 = 100.0% [99.9%–100.0%] | 0/3828 = 0.0% [0.0%–0.1%], rule of three ≤0.1% | 0 |

## 7. Speed

- B page parse: 824 files, 852 pages; per page median 9.3 s, mean 11.4 s, p95 22.3 s (Apple M3 Pro, llama.cpp Metal, layout model on CPU; other jobs were running at the same time on part of the data, so these are upper bounds).
- D field crop: 1887 crops; median 0.37 s, mean 0.53 s, p95 1.32 s per crop.
