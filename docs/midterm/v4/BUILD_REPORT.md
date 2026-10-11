# BUILD_REPORT — ADVS 1차 중간발표 (v4, visual deck)

## Files
- `docs/midterm/v4/ADVS_1차중간발표.pptx` (16:9, native shapes and charts) and `ADVS_1차중간발표.pdf` (submit file, about 3 MB, limit 20 MB)
- `screenshots/` S1–S10 (3840×2160 = 1920×1080 @2x, no callouts) + `meta.json`; `capture_screenshots.mjs`, `make_tampered_pdf.py`; `build_deck_v4.py` (builder); `slides_sources.md`; `contact_sheet.png`
- `docs/midterm/ADVS_midterm.pptx` and its PDF were not touched. Nothing was committed or pushed.

## Counts and timing
- 21 main slides + 8 appendix slides (A1 numbers, A2 document types, A3 ×4 extra screenshots without callouts, A4 demo scenarios D1–D9, A5 sources).
- Estimated talk time: ★ path (slides 1–8, 10, 12, 14, 15, 20, 21) about 295 s (4:55); all 21 main slides about 430 s (7:10). Appendix is for Q&A only.

## Criteria → slides
| # | Criterion | Slides |
|---|---|---|
| 1 | Progress vs plan | 4 (Gantt plan vs actual) |
| 2 | Roles | 5 |
| 3 | Plan validity / realism | 3, 6, 18, 19 |
| 4 | Progress vs difficulty, with screenshots | 7–13, 15, 16, 17 |
| 5 | Future plan | 20 |

## Words per slide
"Body words" counts running text only (excludes title, chart, tile and callout labels, which are short labels). Limit about 15.
| Slide | Body words | Notes seconds | ★ |
|---|---|---|---|
| 1 | 0 | 10 | ★ |
| 2 | 7 | 15 | ★ |
| 3 | 13 | 20 | ★ |
| 4 | 0 | 30 | ★ |
| 5 | 11 | 25 | ★ |
| 6 | 0 | 25 | ★ |
| 7 | 0 | 15 | ★ |
| 8 | 0 | 20 | ★ |
| 9 | 0 | 15 |  |
| 10 | 0 | 20 | ★ |
| 11 | 0 | 15 |  |
| 12 | 0 | 25 | ★ |
| 13 | 0 | 15 |  |
| 14 | 9 | 20 | ★ |
| 15 | 10 | 30 | ★ |
| 16 | 12 | 20 |  |
| 17 | 0 | 30 |  |
| 18 | 6 | 25 |  |
| 19 | 12 | 15 |  |
| 20 | 9 | 30 | ★ |
| 21 | 0 | 10 | ★ |
| 22 | 16 | 0 |  |
| 23 | 0 | 0 |  |
| 24 | 0 | 0 |  |
| 25 | 0 | 0 |  |
| 26 | 0 | 0 |  |
| 27 | 0 | 0 |  |
| 28 | 0 | 0 |  |
| 29 | 0 | 0 |  |

## Unsourced or external items (please check)
- **Original planned schedule and roles come from outside the repository**: the owner's `ADVS.docx` (now `docs/planning/ADVS_original_plan.docx`) / `ADVS_SCRIPTS.docx` (slides 8–9 of that script). The Gantt grey bars are those monthly plans; the green bars are approximate, from commit dates. No percent-complete is claimed.
- Course dates 11/19 and 12/10 come from the course deck as recorded in `docs/planning/ROADMAP.md`; 10/15 for the first midterm is now confirmed by the professor and fixed in that file.
- No number was estimated or rounded. Percentages on slide 16 are computed from the printed counts (e.g. 268/275).
- `evaluation/cleanup_ocr_only/CLEANUP_REPORT.md` named in the brief does not exist; not needed.

## Checks run
- Every slide rendered to PNG and inspected (callouts, overflow, Korean glyphs, charts); screenshot slides use crops of 1320 px width placed at 11.3 in (about 85 %), undistorted.
- Search of all slide text and notes for VLM / PaddleOCR-VL / LLM / Claude / GPT: 0 hits.
- Personal data: only fictional TEST SAMPLE documents; the only names are the team, mentor and professor on the title slide.
- Font: Korean runs set to Apple SD Gothic Neo (east-asian typeface), Latin Helvetica Neue. On a machine without them PowerPoint substitutes (Malgun Gothic/Arial); `pdffonts` is not installed here, so the PDF's font table was read with PyMuPDF: AppleSDGothicNeo (Regular, Bold), HelveticaNeue, HiraginoSans, PingFangSC and others are all embedded subsets; only Apple Color Emoji is stored as inline Type 3 glyphs. Submit the PDF.
- Demo stack was stopped after capture.

## Three presenting tips
1. Spend the saved time on slides 14–15: say the problem first (11.64 items per scan), then the change, then the number; admit that 7.23 rose because safety was tightened.
2. Always say the denominator and "fictional documents" when quoting 0/14; if asked why not zero risk, answer with the 21.4 % upper bound.
3. On screenshot slides name callout 1, 2, 3 in order and stop; do not read the page text.
