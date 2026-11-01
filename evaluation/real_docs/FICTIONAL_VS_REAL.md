# Fictional vs real documents: where does the gap come from?

Masked: counts, rates and pixel statistics only. Tool: `fictional_vs_real.py` (private inputs). Code: `fix/orientation-issue-date` tip. Real = student fresh + seeds A/B + pair (development data) and the business generalisation run; fictional = dev set and hold-out 1 (v3 scorer).
Wilson 95% intervals. Fictional hold-out 1 is test data; the fictional dev set and all student real sets are development data; business real is the generalisation run.

## 1. Two stages

OCR stage = the gold value can be read in the OCR text of the page. Extraction stage = of the fields whose value IS in the text, the machine value equals the gold value.

| set | medium | fields | OCR stage (value in text) | extraction given text | accepted correct |
|---|---|---|---|---|---|
| student real | photo | 300 | 269 = 89.7% (85.7–92.6) | 200/269 = 74.3% (68.8–79.2) | 18 |
| student real | scan | 760 | 712 = 93.7% (91.7–95.2) | 608/712 = 85.4% (82.6–87.8) | 74 |
| business real | photo | 232 | 232 = 100% (98.4–100) | 175/232 = 75.4% (69.5–80.5) | 84 |
| business real | scan | 672 | 668 = 99.4% (98.5–99.8) | 521/668 = 78.0% (74.7–81.0) | 229 |
| business real | digital | 8 | 8/8 | 6/8 | 6 |
| all real | all | 1,972 | 1,889 = 95.8% (94.8–96.6) | 1,510/1,889 = 79.9% (78.1–81.7) | 411 |

Fictional (v3 scorer, OCR and extraction together, correct fields): dev 751/753 = 99.7% (99.0–99.9), hold-out 1 818/825 = 99.2% (98.3–99.6). Per type the scanned and image versions are 94–100% correct; the text-layer (digital) versions give the extraction stage alone (about 99–100%).

## 2. Reading

- **Business real: the OCR stage is not the gap** (99.4% of values are in the text) — the loss is the extraction stage (78%) and then the safety policy (only 319 of 702 correct fields are auto-accepted). Fictional business documents are extracted at 98–100%.
- **Student real photos: both stages lose** (OCR 89.7%, extraction 74.3%); student scans lose mostly at the extraction stage (85.4%) and at the policy.
- 0 wrong values were accepted in every real cell.

## 3. Effective text height (median OCR line height, pixels)

Real fresh photographs 22 px; real seed sets 39 px; fictional scanned about 43 px, fictional images about 29 px (recorded OCR cache). The fresh photographs are the smallest text and have the lowest correct rate (78.1%, against 85.4% and 86.2% on the seeds). Literature on OCR accuracy against pixel height is practitioner grade (Tesseract group, iDigBio, patents); here it is supporting, not tested.

## 4. Conclusion for the paper

The gap between fictional and real is mainly (i) layout variety that rules written for fictional templates do not cover (extraction stage), (ii) small text on photographs (OCR stage) and (iii) a deliberately strict acceptance policy. The first is shared by both families; the second is specific to student photographs.

## 5. 요약

가상 서류는 정확도 99%대이지만 실제 서류는 80% 안팎입니다. 사업자 실제 서류는 글자 읽기(OCR)는 99%로 문제가 없고, 읽은 글자에서 값을 뽑는 단계(약 78%)와 자동 승인 정책이 격차의 원인입니다. 학생 사진은 글자가 작아(줄 높이 22px) OCR 단계에서도 손실이 있습니다.
