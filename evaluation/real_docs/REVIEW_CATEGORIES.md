# Why documents need a person: review categories (student and business)

Masked report: counts, reason codes and categories only. No document text, names, numbers or dates.
Tool: `review_categories.py` (private inputs, masked output). Code under test: `fix/orientation-issue-date` tip (rotation search + issue-date anchor), real sets run once on that commit.
Inputs: student fresh (56 submissions), seed A (34), seed B (34), business main run (202, generalisation run on the same commit). Rules unchanged: 0 wrong auto-accepted, 0 false 제출 가능.

Status: student rows are **development data** (the fixes were made on them). Business rows are the **generalisation run** ("fixes developed on student documents only"); business was not used for any code change.

## 1. Headline

- 2,615 gold fields were not auto-accepted (a person looks at them). 314 submissions, 186 valid ones, **0 reached 제출 가능**, 0 negatives READY, 0 wrong values effectively accepted.
- The mean valid submission has about 8 blocking fields. **No single category, fixed alone, makes any submission 제출 가능** (simulation, section 3). Only the whole set of causes together lets 127 of 186 through.
- The largest category is **C2 (field mapping/extraction)** at 38.7% (Wilson 36.8–40.5), then C1 (OCR) 26.8% (25.1–28.5), C3 (cross-document) 23.2% (21.6–24.9), C5 (policy) 9.3% (8.3–10.5), C4 (classification) 2.0% (1.5–2.6).

## 2. Frequencies

Per category (fields): C1 701 · C2 1011 · C3 607 · C4 52 · C5 244.

| family | C1 | C2 | C3 | C4 | C5 |
|---|---|---|---|---|---|
| business (generalisation) | 274 | 689 | 422 | 0 | 140 |
| student fresh | 197 | 166 | 56 | 24 | 44 |
| student seed A | 111 | 81 | 66 | 12 | 30 |
| student seed B | 119 | 75 | 63 | 16 | 30 |

By medium: scan C1 539 / C2 736 / C3 464 / C5 184 / C4 24; photo C1 162 / C2 270 / C3 143 / C5 60 / C4 28; digital C2 5.

Causes (primary, one per field):

| # | category | cause | fields |
|---|---|---|---|
| 1 | C2 | value is in the page text but was not extracted | 635 |
| 2 | C2 | value taken by position only (no label) | 367 |
| 3 | C3 | no second document confirms the value | 287 |
| 4 | C3 | another document reads it differently | 248 |
| 5 | C5 | no auto-accept rule for this field | 244 |
| 6 | C1 | confidence below the floor | 240 |
| 7 | C1 | second reading disagrees (name-like text) | 178 |
| 8 | C1 | confidence near the decision boundary | 143 |
| 9 | C3 | grading scale differs between documents | 72 |
| 10 | C4 | document typed wrongly or unknown | 52 |

By field (top): `issue_date` C2 764; university name C1 217; `valid_until` C3 174 and C1 169; representative name C5 140; company name C3 136; department C5 104; GPA scale C3 72; workplace name C3 70; business registration number C2 69; student name C1 67.

Blocker combinations on valid submissions (184 not READY): C1+C2+C3+C5 110 · C1+C2+C3 19 · C1+C2+C3+C4 13 · C1+C2+C5 12 · C1+C2+C3+C4+C5 11 · C2+C3+C5 10 · others ≤5 each. Four submissions are blocked by C4 alone.

## 3. "If fixed" simulation (counting only; a fixed field is counted as correct, so no wrong value is added by construction)

Valid submissions (186) that would be 제출 가능 if every field of a category were fixed:

| fixed | READY |
|---|---|
| none | 0 |
| C1 alone | 0 |
| C2 alone | 0 |
| C3 alone | 0 |
| C4 alone | 2 |
| C5 alone | 0 |
| C2+C3 | 1 |
| C2+C3+C5 | 11 (all business) |
| C1..C5 | 127 |

Of 1,561 blocking fields, fixing the best single cause (C2 not extracted) still leaves 1,231. Fixing **every** cause leaves 174 of 184 submissions with 0 blockers.
Reading: the gain is a stack, not a lever. Business is limited by C2 and C3 (issue date, company-name notation); the student photographs by C1.

## 4. Top 10 case studies (mechanism, alternatives, recommended fix)

Evidence quality: the citations are practitioner and preprint grade (patents, vendor documentation, arXiv), found by generic web search; none is a Korean-certificate study. Treat them as design support, not proof. Examples describe the pattern only; no values.

1. **Issue date on the page but not extracted (C2, 635 incl. issue_date)**
   Mechanism: the date is a bare date line without a label; the extractor needs a unique date plus an issuer anchor, and a seal can leave a digit fragment on the date row. Business certificates also carry several dates.
   Alternatives: (a) anchor from above (certification sentence): done for student scans, **no effect on business** (152 of 208 unread business fields are still `issue_date`); (b) per-type layout rules from the page region; (c) a layout-aware model (LayoutLM, arXiv 1912.13318) — heavier and outside the traditional-OCR rule.
   Fix: add a business anchor from the certificate layout (synthetic test, invented values), then a new generalisation round.
2. **Value taken by position only (C2, 367)** — the label is missing or split, so the extractor falls back to position. Alternative: require the label or a known column, otherwise review (already the safe default). Fix: better matching of split labels.
3. **No second document confirms the value (C3, 287; valid_until 168, GPA 66)** — a value that appears once cannot be cross-checked. Alternative: accept a single digital-text-layer source that passes format and arithmetic checks (policy decision for the owner). Fix: none in code until decided.
4. **Another document reads it differently (C3, 248; company 132, workplace 70)** — notation differences (legal form, spaces, parenthesised Latin, shortened form). Alternatives: longest-first legal-form suffix list; alias list per applicant. Fix: normalisation settings in the admin checklist editor; strict comparison stays the default.
5. **No auto-accept rule for the field (C5, 244; representative 140, department 96)** — by design. Alternative: add a rule after the field is measured as reliable. Fix: owner decision.
6. **Confidence below the floor (C1, 240; university 73, student ID 51, name 42)** — small text on photos (median OCR line height 22 px on the fresh photos against 39 px on the seeds; OCR accuracy tracks text pixel height: Tesseract group, iDigBio about 20 px x-height). Alternatives: capture guidance in the UI, crop and upscale (measured: within noise), a second engine. Fix: capture guidance in the web UI (Munira); the floor stays.
7. **Second reading disagrees on name-like text (C1, 178)** — the confirmation re-read is a safety check, so the escalation is correct. Alternative: allow near matches only with label agreement. Not recommended now.
8. **Near the decision boundary (C1, 143)** — calibration. Research: confidence calibration and reject option (Mor and Wolf, arXiv 1805.11161; ExtractConf, arXiv 2606.24420). Fix: calibrate per field on a held-out set; the floor is changed only by the owner.
9. **Grading scale differs between documents (C3, 72)** — compare only after conversion; keep review when a scale is missing.
10. **Document typed wrongly (C4, 52), and 지방세 typed as 국세** — rotated or damaged titles, and the look-alike local-tax certificate. This one is **safety-critical**: 2 of 4 real 지방세 originals were typed 국세 with no flag. Seal removal before OCR is the usual advice (ABBYY, patents), but the safer fix is classification from the issuer line and form number rather than the title.

## 5. 요약 (멘토용 1페이지)

**목적**: 사람이 다시 확인해야 하는 서류가 왜 많은지 원인을 5가지로 나눠 세었습니다. 안전 기준(잘못된 자동 승인 0, 잘못된 제출 가능 0)은 모든 실험에서 지켜졌습니다.

**숫자** (학생 124건 + 사업자 202건 제출, 필드 2,615개가 사람 확인):
- C2 항목 구분/필드 매핑 38.7% — 글자는 읽었는데 값을 못 뽑음 (발급일이 764건으로 가장 큼)
- C1 OCR 인식 26.8% — 사진 속 작은 글자, 낮은 신뢰도
- C3 문서 간 비교 23.2% — 확인해 줄 두 번째 서류가 없거나 표기가 다름 (회사명, 유효기간)
- C5 안전 정책 9.3% — 자동 승인 규칙이 아직 없는 항목 (대표자, 학과)
- C4 문서 분류 2.0% — 제목이 훼손·회전된 문서, 지방세를 국세로 오인

**핵심**: 한 가지만 고쳐서는 제출 가능이 늘지 않습니다(서류 한 건당 막는 항목 평균 8개). 모든 원인을 고치면 186건 중 127건이 통과합니다. 사업자 서류는 C2+C3+C5를 함께 고치면 78건 중 11건이 통과합니다.

**먼저 할 일**: ① 지방세/국세 구분(안전 문제, 4건 중 2건이 표시 없이 오분류) ② 사업자 서류 발급일 추출 ③ 회사명 표기 정규화(관리자 설정) ④ 촬영 안내(해상도). 신뢰도 기준은 낮추지 않습니다.

**주의**: 사업자 서류 결과는 학생 서류로 만든 수정의 일반화 시험입니다(사업자 서류로 수정하지 않음). 인용한 연구 근거는 논문·특허·실무 자료 수준입니다.
