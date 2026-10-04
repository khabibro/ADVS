# Remaining failures

Everything below is still true after this round. Nothing here is planned,
partially fixed, or "mostly working".

---

## 1. Dense multi-column transcript headers — R2-04

**What fails.** `student_name` and `student_id` are unresolved on a transcript
whose header OCR'd at mean confidence 0.905.

**Earliest responsible stage.** `OCR_TEXT_DETECTION`.

**Why.** The detector emitted a single box, `학성`, 88 px tall while every
neighbouring box on the same line is 42–45 px. It spans two physical text
lines *and* straddles two table columns: it is the first character of 학번 and
the first character of 성명 fused into one box. Row grouping then merged the two
lines into a single row, producing:

```
'소' | '생년월일:2003년4월18일' | '속:IT대학컴퓨터학부...' | '학성' | '번:[REDACTED_STUDENT_ID]' | '명:[REDACTED_STUDENT_NAME]' | '입학일자:...'
```

`학번` and `성명` are therefore never contiguous strings, so neither label can
match.

**Why it was not fixed.** Which column the character 학 belongs to no longer
exists anywhere in the pipeline — it was destroyed inside the box. A rule that
reconstructed it would be guessing, and a guessed student id is a wrong
non-null value. The remedy is a layout/table model, not heuristic tuning.

**Status.** Open. Needs a table-capable pipeline (PP-StructureV3 or equivalent)
evaluated as its own experiment with its own latency budget.

---

## 2. `university_name` under an official seal — R2-04, R2-07

**What fails.** Unresolved on both anonymised documents.

**Earliest responsible stage.** `OCR_RECOGNITION`.

**Why.** The institution name appears only in the signature block, where the
stamp overlaps it. `경북대학교 총장` is recognised as `경 북 대 학교 총 려니` —
the last character is destroyed by occlusion. The surviving fragment is
rejected by institution shape validation, which is the *correct* conservative
behaviour: emitting `총 려니` as a university name would be a wrong value.

**Status.** Open. Ground truth is PARTIAL for both: the name genuinely only
exists in the occluded signature block.

---

## 3. One wrong non-null value — R2-03

**What fails.** `student_name` is returned as a different surname from the one
printed.

**Earliest responsible stage.** `OCR_RECOGNITION`.

**Why.** The source is a 743×1020 JPEG — roughly 90 DPI for A4. One Hangul
syllable is misread at mean line confidence 0.910, and the resulting string is a
structurally valid personal name of legal length.

**Why it matters.** Confidence 0.917, evidence assessment `SUFFICIENT`, five
evidence boxes. Every safety mechanism in the system passed it. This is the
round's concrete demonstration that **OCR confidence is not correctness** — the
same conclusion the previous round reached, now on a different document.

**Status.** Open. Detecting it requires either a higher-resolution source or
cross-field consistency checking; neither is implemented.

---

## 4. `representative_name` on R2-06, `business_registration_number` on R2-01

**What fails.** Both unresolved despite the value being present in the OCR text.

**R2-06.** The document is 400×566 px — about 50 DPI for A4. `대표자명:` and
`[REDACTED_REPRESENTATIVE_NAME]` are recognised; the label is in the known-label list. The value sits on
the same row in the next box and is now resolved by E2/F04 for other fields, but
this particular pairing still yields nothing.

**R2-01.** `사업자등록번호` is recognised as `사업자동록번호` — one character
dropped by the recognizer. The number `123-45-67890` is present and correctly
read directly beside it, but the label no longer matches.

**Status.** Open. Both are single-character OCR damage to a label. The obvious
remedy — edit-distance label matching — was **deliberately not implemented**:
R2-01's row also contains `사업장관리번호 2023-123456-7` on the same line, and
loosened label matching is exactly how an 통합납부자번호 ends up captured as a
사업자등록번호. Conservative matching would need a measured false-positive rate
this dataset is too small to establish.

---

## 5. `department` on R2-05, and the meaning of `department` generally

**What fails.** Unresolved on R2-05. Ambiguous on R2-04 and R2-07.

**Why.** The documents carry several department-like strings:
`소속: IT대학 컴퓨터학부`, `전공: 글로벌소프트웨어공학전공`,
`복수전공: 영어영문학과`. Which one the single field `department` should hold is
a product decision, not something the document states. Ground truth is
AMBIGUOUS and scored `NOT_EVALUATED` for R2-04 and R2-07.

**Status.** Open product question.

---

## 6. Project-level `READY` while a document is `REVIEW_REQUIRED` — R2-05, R2-07

**What fails.** Submission verification reports `READY` while the document
panel reports `REVIEW_REQUIRED` for the same submission, with unread
`university_name`.

**Why.** Submission verification only evaluates the rules a workflow
configures. The seeded student workflow configures a date comparison on
`issue_date`; it says nothing about `university_name`, so that unread field is
invisible to it.

**Why it was not fixed.** What project-level `READY` *means* is a product
decision about submission semantics. Both panels report their own state
truthfully, so the UI is not misrepresenting the backend — but a user can see
two different answers for one submission, which is a real usability defect.

**Status.** Open question for the project owner. Not a code defect.

---

## 7. Rotation — untested this round

No rotated sample exists in the dataset. The conditional orientation retry was
left untouched. It remains a heuristic trigger (mean confidence < 0.80 or
< 120 characters per page) rather than an orientation measurement, and 180° /
270° are less well supported than 90°.

**Status.** Unverified. Cannot be claimed as supported.

---

## 8. `gpa` on R2-03, `gpa_scale` correctly withheld

`gpa` is unresolved on R2-03. The document prints `평균 평점 : 3.61` among
twenty-odd other decimals, and no `평점평균:`-style label was matched.

`gpa_scale` stays unresolved on R2-03 and that is **correct**: the document
prints `평점최고 : 4.5`, a historical maximum, not an explicit scale. Ground
truth is `NOT_EVIDENCED`. Inferring 4.5 here would be fabrication, and it is
marked `NOT_EVALUATED` rather than counted as a failure.

**Status.** `gpa` open; `gpa_scale` behaving correctly.

---

## 9. `valid_until` on R2-01 — behaving correctly

R2-01 prints `-` for both the 고용 and 산재 validity rows. Ground truth is
`VERIFIED_ABSENT` and the field is unresolved. **This is the right outcome**;
it is listed only because "unresolved" and "correct" look identical in the
metrics table.

---

## 10. Mentor controlled set — not re-run

The `학생용_가상데이터` folder was removed from `~/Desktop` during this session,
so `make eval-phase6` could not run. That dataset is **not** covered by this
round's regression evidence.

Synthetic dev (105 samples), synthetic held-out (32), recreated (5) and the
previous real certificate were all re-run and are unchanged.
