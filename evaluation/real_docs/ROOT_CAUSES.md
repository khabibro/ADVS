# Fresh-capture accuracy: root causes (development data, masked)

Status: investigation only, **no application code changed**. The frozen result in `REAL_DOCS_REPORT.md` section 9 is untouched and stays the official test result for `real-docs-freeze-3`. From this document on, the fresh set (G0-G5) is **development data**: improvements are measured on it as development, and the final claim needs the new untouched set (`~/Desktop/fresh2/`).

Method: every statement below comes from the saved outputs of the frozen run (`results/fresh_frozen`, `results/fresh_base`) and from three read-only tools kept privately: a stage table (where a missing field first fails), an offline replay (classification and extraction re-run on the stored OCR lines: it reproduces all 78 document types and all 422 field values of the frozen run exactly, so it is a faithful test bench), and **prototypes** of candidate fixes applied by monkey-patching inside the replay (nothing in the repository changed). Prototype numbers are single-document runs ("singles", 34 fields for the real photos G0, 372 for G1-G5, 34 for the known-limit rotations G3b), machine values only, so they measure extraction, not the acceptance policy.

## 1. The headline finding: the pictures are mostly readable, the extraction is what fails

Of the 244 fields missing in the pair runs, the stage table finds the correct value text **present in the OCR output** for 207 (85%): the detector found it and the recogniser read it, and the extractor did not associate it with its field. Only 37 (15%) are real recognition failures (23 of them are the university name, a letter-spaced issuer line overlaid by the red seal). So "the photos are only 140 DPI" is **not** the main cause. Resolution is a real but secondary factor (section 4, cause 6).

| first failing stage | missing fields | share |
|---|---|---|
| recognition (value not in the OCR text) | 37 | 15% |
| association / parsing (value in the OCR text) | 207 | 85% |

## 2. Ranked causes

Share = fields recovered when only that prototype is switched on (G1-G5, 372 fields, 189 correct at baseline = 50.8%). The prototypes are measured together at the end of this section.

| # | Cause | Evidence | Affected fields | Share (prototype alone, G1-G5) | Proposed fix | Risk to safety |
|---|---|---|---|---|---|---|
| 1 | **Rows are built by chaining overlapping boxes** (`ocr/layout.py` `build_rows`: each box joins the row of the *previous* box when it overlaps it by half of the shorter height). A low-confidence box read from the red seal (a 77-px-high box at confidence 0.26 over the issuer block) overlaps the date, the "위의 사실을 증명합니다" line and the issuer glyphs, and chains them into one row. In the transcript header, one tall fused box bridges two label rows and the whole header becomes one row ("소 생년월일속 ... 학성 명:... 번:... 입학일자..."). Because the line pitch (about 19 px) is close to the text height (about 21 px) at this size, ordinary rows also chain. | stored rows of the G0 transcripts; the stamp-aware date rule (`_date_row_text`) cannot help because the issuer glyphs *precede* the date in x | `issue_date` (all transcripts, half of the enrolment reads), header name and number | boxes below 0.5 confidence not bridging rows: +19; rows clustered by distance to the row centre (also dropping those boxes): **+32** | build rows by clustering on the row centre with a tolerance of half the median text height; keep low-confidence boxes out of row building (they stay as their own rows, so nothing is deleted) | low: a value is still only taken from a box of its own row; unit tests with invented rows; risk is a change in row text that currently matches (measured on the fictional sets and seeds) |
| 2 | **Cumulative GPA is anchored to the exact text "총 취득학점"** (`extraction/base.py` `cumulative_gpa_candidates`, `startswith`). In the 4.5 photographs the recogniser wrote "총 취득학정" (점 read as 정), the anchor is lost, and the fallback (label path) abstains because the seven semester GPAs conflict. The 4.3 photographs were read "점" correctly. The same documents are read, the label differs by one syllable. | G0 and G1-G5: 4.5 transcript GPA read in 6 of 26 pairs, 4.3 in 18 of 26; replay shows the cumulative line itself ("평점평균:3.62/4.5백분:90.00/100") is read in both | `gpa`, `gpa_scale` (28 of the 52 transcripts, all groups) | tolerant anchor (정/점 and 평정/평점 only): **+48** | match the anchor through the existing confusion mechanism (the label only locates the line; the value must still parse as `x/y` and pass the existing scale checks), plus a layout cue that does not depend on the label (the cumulative line is the last 평점평균 line of the last column) | low: the anchor chooses a *line*, not a value; the result still goes through the GPA format checks (value <= scale) and the acceptance policy |
| 3 | **Stacked-label split needs the label tail and its colon in one box** (`ocr/layout.py` `split_stacked_label_boxes`, `_LABEL_TAIL_RE`). On the photographs the recogniser writes the second syllable alone ("번") and the colon with the value (":2023..."), so the fused tall box "학성" is not split, and the labels 학번 and 성명 never exist. | G0: fused box 23x44 px found, tails "번" + ":<10-digit number>" and "명:..." present; with the tail rule relaxed to "a 1-3 syllable box followed by a box that starts with a colon on the same row" the labels are recovered | `student_name`, `student_id` of both transcripts | **+20** (name +14, number +10) | accept a detached colon, still requiring every cell of the fused box to have such a tail | low: same guard (a tail must exist for every cell) |
| 4 | **University name is read from a letter-spaced issuer line that the red seal overlays** (letter-spaced glyph boxes, a stray `*"` mark from the seal, confidence 0.84). | 28 university-name fields missing in the pair runs: 19 near-misses of the recognised text, 4 absent, 5 present but not associated (and 24 still missing after prototypes 1-3); the `letter-spaced issuer row` assembly (fix 2 of the earlier round) tolerates ASCII noise but not a seal glyph inside the name | `university_name` (all documents) | not addressed by prototypes 1-3 (still 24 missing) | read the issuer line from the *red-suppressed* channel (the second pass already does this for values over a stamp), and accept the university from the label path "대학교" / the header when the issuer line is damaged | medium: a university string is compared across documents; any change needs the fictional university gate (hold-outs, 0 diffs) |
| 5 | **Document type not recognised for damaged titles and rotated pages.** The letter-spaced title "재 학 증 명 서" is read as separate pieces ("재 학 증", "서", "등명") in 2 upright enrolment files (G1 flat pdf, G2 JPEG q50) and as the first page of both two-page PDFs; the 90/180-degree photographs are read as noise (orientation retry only runs when mean confidence is low or very few characters are read). | replay: the four wrong types are all enrolment certificates, the same on both commits | document type, then every field of the file | affects 4 of 78 files plus 2 PDFs; a wrong type costs 5 fields each | title assembly across pieces (same letter-spaced logic as the issuer row); run the orientation retry when the title and labels are not found, not only when confidence is low | low for the title (the title gate stays); medium for orientation (a retry may give a different reading; the retry is only kept when its quality score is higher, existing rule) |
| 6 | **Text height: images are fed at their native size, PDFs are rendered at 288 DPI.** The original scans (200 DPI image-only PDFs) reach the recogniser at a median text height of 42 px; the phone images at 21 px (the flat G1 PNG, 14 px at 100 DPI). | median `bounding_box.height` per document from the stored OCR | all fields, mostly recognition failures | section 4: below about 15 px text height reading collapses; above it, upscaling adds at most 1-2 fields | a capture-quality gate with a retake message below a measured text height (about 13 px median, to be fixed on the next data), and no upscaling unless the gate shows a benefit | low (a message; no value changes) |
| 7 | **Name veto by the second pass.** 68 correct values (29% of the 234 values that were read correctly and sent to review) are stopped by `SECOND_PASS_CONTRADICTS_NAME`: the second pass (crop, x1.6) does not contain the first reading. | acceptance reasons of the frozen run | `student_name` | section 5: the veto fires on degraded photographs (blur, noise, rotated page) where the second reading really differs; the first reading was right in every case examined | **no change proposed** | high: this is a safety brake |
| 8 | **Acceptance policy keeps correct values in review by design.** `SEMANTIC_INFERENCE` 46 (unlabelled issue date), `NO_RULE_FOR_FIELD` 40 (department has no rule), `NO_INDEPENDENT_CONFIRMATION` 35, `CONFIDENCE_BELOW_FLOOR` 16, `NEAR_DECISION_BOUNDARY` 11, `GRADING_SCALE_MISMATCH` 7. | reason counts, G0-G5 without G3b, 234 values | automation, not accuracy | n/a | **no change proposed** to floors or confirmation requirements | n/a (hard rule) |

Combined effect of the three extraction prototypes (cause 1 as row clustering, cause 2, cause 3), development data, singles, machine values:

| set | frozen | 3 prototypes | change |
|---|---|---|---|
| G0 real photos (34 fields) | 16 correct, 18 missing | **32 correct, 2 missing** | +16 |
| G1-G5 (372 fields) | 189 correct (50.8%), 183 missing, 2 wrong | **310 correct (83.3%)**, 62 missing, 2 wrong | +121, no new wrong value |
| G3b rotations (34 fields) | 15 | 19 | +4 |
| seed B stored OCR (368 field readings) | 307 correct, 10 wrong, 51 missing | 313 correct, 10 wrong, 45 missing | +6, wrong unchanged |
| seed A stored OCR (368 field readings) | 303 correct, 10 wrong, 55 missing | 314 correct, 10 wrong, 44 missing | +11, wrong unchanged |

(The 10 "wrong" in seeds A and B are the deliberately edited and look-alike negative cases; they are not accepted by the policy.) These figures are **offline prototypes on development data**; the real fixes will be re-measured through the full pipeline and the gates.

## 3. Questions asked, answered

1. **Why is the 4.5 transcript's GPA read in 6 of 26 pairs and the 4.3 transcript's in 18?** Cause 2: the anchor syllable. The recogniser read "학정" on the 4.5 photographs and "학점" on the 4.3 ones; the rest of the layout is identical. With the tolerant anchor the prototype reads GPA and scale in 50 of 52 documents.
2. **Why are name, 학번 and issue date never read on the transcripts of G0?** Name and number: causes 3 and 1 (fused label not split; header rows chained into one row). Issue date: cause 1 (the seal box chains the date into the issuer row, so the row is not a bare date).
3. **Why did the expiry checks all end in REVIEW_REQUIRED?** Confirmed, by design. The issue date on these documents is an unlabelled date inferred from its position; the extractor marks it `needs_review` (`SEMANTIC_INFERENCE`) and the engine routes an unresolved value to review (`_unresolved_field`), so the age rule is never applied. Decision-robust acceptance (`decision_robust.py`, D3-5) exists but excludes values that need review (`auto_acceptance.py:734`). **A decision-robust *failure* rule is feasible and would be safe in the 보완-필요 direction**, with one prerequisite: `decision_robust.outcomes()` evaluates `max_age` as `reference - date <= days` and ignores the engine's upper bound (a date after the check date also fails). For "2026-10-30" the table's plausible readings include 2028-10-30, 2062-10-30 and 2076-10-30, which the model calls "valid" (negative age) and the engine rejects, so today the robust decision is wrongly "not robust" on the expiry check and, in the other direction, the model could call a future misreading harmless. Fix the model first (add the upper bound), test with injections, then add a rule: *if every plausible reading fails the rule, report 보완 필요 (not 제출 가능, not auto-accept)*. It can never produce READY, only a stronger "expired" message, so it does not touch the false-READY gate.
4. **Two-page PDFs.** Confirmed partly: the pipeline already classifies every page (`processing._split_multi_document`), but when pages are different *supported* types it flags the file and **extracts only the first type**; it never creates a second document. In the two test PDFs the first page (the enrolment certificate) is classified UNKNOWN (damaged letter-spaced title, cause 5), so only one supported type exists, nothing is flagged, the file is typed TRANSCRIPT and the enrolment certificate is missing. Needed: per-page document typing that yields one document per supported page, plus the title fix.
5. **백분율.** There is no extractor for it (the field list has no such name); it is printed on every GPA line and read correctly ("백분:90.00/100" with the 율 often dropped). Adding it as an *observation* (not a decision input) is trivial and independent of the other fixes.

## 4. Resolution sweep (development pages, frozen pipeline, live OCR)

Three real pages (enrolment certificate, 4.5 and 4.3 transcript; the flat G1 PNG) rescaled with Lanczos and run through the frozen pipeline with live OCR; 17 scored fields; machine values; development data, so indicative only (3 documents).

| scale | median text height | document types | fields correct, frozen extraction | fields correct, with prototypes 1-3 |
|---|---|---|---|---|
| x0.50 | 11 px | 3/3 | 10/17 | 10/17 |
| x0.71 | 15 px | 3/3 | 8/17 | 16/17 |
| x1.00 (as photographed) | 21 px | 3/3 | 10/17 | 16/17 |
| x1.44 | 30 px | 3/3 | 11/17 | 15/17 |
| x2.00 | 44 px | 3/3 | 12/17 | 16/17 |

Reading: with the extraction as it is, fields correct move from 10 to 12 when the text is made twice as large, and the same page becomes 16/17 at its own size once the extraction causes are fixed; making text larger adds nothing then. Reading really degrades only at about 11 px text height (10/17 even with fixed extraction). The originals reach the recogniser at 42 px because image-only PDFs are rendered at 288 DPI; the phone images are not upscaled and sit at 21 px, which is enough. **Resolution is a secondary cause**; the useful measure is a capture-quality gate (minimum text height with a retake message) rather than upscaling. Direct supporting observation: the three iPhone originals at 4032 px (post-fix G0b) give 30-50 px text and read name, date and GPA on both transcripts; section 12 of the report.

## 5. Second-pass name veto

The second pass (crop, x1.6, red-suppressed when a seal overlaps) was replayed on every single-file case of the frozen run in which a correctly read name was vetoed with `SECOND_PASS_CONTRADICTS_NAME` (4 documents) and on the two upright enrolment certificates for comparison.

- On the clean upright photographs the second reading contains the first (10 characters against 8: the crop adds the label's colon and a neighbour), so the name is not contradicted (reason `NO_INDEPENDENT_CONFIRMATION`).
- The vetoed documents are a rotated page (second reading 3 characters, confidence 0.23) and three blurred photographs (defocus, motion blur): the second reading differs from the first, which was correct in all 4 cases.
- In the pair runs the reason appears 68 times, by group: G4 photo effects 23, G2 scan quality 15, G3 geometry 13, G5 formats 8, G0 5, G1 4: degraded or rotated pixels.

Conclusion: the veto is doing what it was built for (disagreement on a degraded picture); it costs automation on blurred photographs, not accuracy. No change proposed. A permissive change here would be exactly the kind that lets a misread name through.

## 6. Research that influenced the proposals

- PaddleOCR PP-OCRv5 documentation: detection parameters `text_det_limit_type` / `text_det_limit_side_len` (default benchmark setting "min" / 736) and mobile versus server detector, https://www.paddleocr.ai/latest/version3.x/algorithm/PP-OCRv5/PP-OCRv5.html . The recogniser used here is `korean_PP-OCRv5_mobile_rec` (the only Korean PP-OCRv5 recogniser; 88.0% on the PaddleOCR Korean test set, https://huggingface.co/PaddlePaddle/korean_PP-OCRv5_mobile_rec ). The server detector (`PP-OCRv5_server_det`) gave similar character error rates with the Korean recogniser at about twice the CPU time in an independent informal test of 140 images, https://wikidocs.net/441124 : **not a candidate**, since the lost fields are association failures, not detections.
- No source was needed for causes 1-3: they are ADVS layout and extraction logic, shown by the stored lines.

## 7. Proposed order of fixes (for your approval; nothing is implemented)

1. Cause 2 (GPA anchor): smallest change, largest single gain (+48 fields), one function.
2. Cause 1 (rows): largest structural gain with the most regression surface; needs the full fictional gates.
3. Cause 3 (detached colon in stacked labels).
4. Cause 5 (title across pieces; orientation retry when the title is not found) and per-page document typing for multi-certificate PDFs.
5. 백분율 as an observation; decision-robust failure rule (after fixing `outcomes()`).
6. Causes 4, 6, 7 only after their measurements, each behind its own gate.
Each fix: one commit, a synthetic test on invented data, the full gate list, and the effect reported on development data and the fictional sets. Nothing relaxes a confidence floor or confirmation rule, and nothing is tuned on the future untouched set.
