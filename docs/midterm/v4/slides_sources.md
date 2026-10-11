# ADVS 1차 중간발표 (v4) — source of every number

Slide numbers refer to `ADVS_1차중간발표.pptx`. Every figure on a slide is listed here with the repository file and section. The original plan (schedule, roles) is `docs/planning/ADVS_original_plan.docx`, copied from the owner's `ADVS.docx` (slides 8–9 of its script).

| Slide | Number / claim | File | Section / line |
|---|---|---|---|
| 1 | Team, mentor, professor names; date | docs/midterm/slides_sources.md (v3 deck), course brief | slide 1 row |
| 2 | Five problem types (누락, 만료, 불일치, 중복, 유사 서류) | docs/midterm/RESULTS.md; evaluation/reports/ADVS_system_audit_report.md | requirements table / checks |
| 3 | Three statuses and their meaning; 제출 가능 is not official approval | README.md; docs/midterm/RESULTS.md | status paragraph, line 5 |
| 4 | Planned schedule by month (9월 설계, 10월 PDF·OCR·분류·추출, 11월 자동 점검·통합, 12월 평가·최종 시연) | docs/planning/ADVS_original_plan.docx (owner's 수행계획발표 script), 'Slide 8. 수행 일정 및 멘토링 계획' (not in the repository) | Slide 8 |
| 4 | Actual dates: first commit 2026-09-05; implementation added 2026-09-15; classification/extraction hardened 09-22; frontend workflow + real-document processing 09-29; OCR ingestion + verification safety 10-02; B-1..B-3 rule fixes and harness 10-04; phases C/D/D2 10-05..10-06; demo + UI/UX Part A + audit 10-10; Phase G and hold-out 3 10-11 | git log (dates of the commits named in the Phase B-G reports) | evaluation/reports/PHASE_B_REPORT.md, evaluation/phase_c|d|d2|e|e2|f|g reports |
| 4 | Mentor requirements 8 implemented / 1 partly / 2 planned (11 rows) | docs/midterm/RESULTS.md | table 'Mentor requirements → status' |
| 5 | Roles: 무니라 UI/UX·Frontend; 하비빌로 Backend·문서 분석·OCR/AI·점검 로직·통합·평가; shared 요구사항 분석·통합 테스트·멘토링·발표·문서화 | docs/planning/ADVS_original_plan.docx (owner's 수행계획발표 script), 'Slide 9. 팀원 간 역할 분배' | Slide 9 |
| 5 | Frontend deliverables (status banner, checklist, evidence view, review flow, uploader, axe checks) | evaluation/phase_e2/PHASE_E2_REPORT.md; evaluation/phase_e2/UX_AUDIT.md; docs/planning/ROADMAP.md | Part A report; N7 'frontend, Munira' |
| 5 | Backend/AI/evaluation deliverables (6 document types, frozen scorer, hold-out sets, independent confirmation, hidden-text check) | docs/midterm/RESULTS.md; evaluation/phase_d/PHASE_D_REPORT.md; evaluation/phase_g/PHASE_G_REPORT.md | requirements table; §2 G-1; §4 |
| 6 | Pipeline stages and stack (Next.js, FastAPI, PaddleOCR PP-OCRv5, Python, SQLite) | docs/architecture/ARCHITECTURE.md; README.md; apps/api/pyproject.toml | 'Document intelligence pipeline'; Tech Stack; paddle extra |
| 7 | Screenshot S1 (new submission, two of four documents) | docs/midterm/v4/screenshots/S1_upload.png | captured from `scripts/demo` on 2026-10-11, 점검 기준일 2026-10-05 |
| 8 | Screenshot S2 (D1 normal submission) | docs/midterm/v4/screenshots/S2_ready.png | demo scenario D1 (docs/midterm/DEMO_SCRIPT.md) |
| 9 | Screenshot S3 (evidence of 유효기간 종료일 in D1) | docs/midterm/v4/screenshots/S3_evidence.png | document detail page |
| 10 | Screenshot S4 (D2: 유효기간 종료일 2026. 08. 31. earlier than 점검 기준일 2026. 10. 05.) | docs/midterm/v4/screenshots/S4_expired.png | demo scenario D2 |
| 11 | Screenshot S5 (D3 company-name mismatch) | docs/midterm/v4/screenshots/S5_mismatch.png | demo scenario D3 |
| 12 | Screenshot S7 (D9 review: two 발급일 values with the cropped original) | docs/midterm/v4/screenshots/S7_review.png | demo scenario D9 |
| 13 | Screenshot S8 (D9 after review) | docs/midterm/v4/screenshots/S8_after_review.png | demo scenario D9, after the reviewer confirms both values |
| 14 | 0/14 false 제출 가능 on hold-out 3 per input type (95% upper bound 21.4%); 0/40 on development corpora | docs/midterm/RESULTS.md; evaluation/phase_g/results/denominators_final.txt; evaluation/phase_g/final/H3_integrated_report.md | Safety table row 1-2 |
| 14 | Digital 790/790 (dev) and 274/275 (hold-out 3) | docs/midterm/RESULTS.md; evaluation/phase_g/results/denominators_final.txt | Accuracy table row 1 |
| 14 | Scan fields 268/275 on hold-out 3, 0 wrong values | docs/midterm/RESULTS.md; evaluation/phase_g/final/H3_integrated.json | Accuracy table row 3; metrics.csv 'Phase G, hold-out 3' |
| 14 | Hidden-text PDFs: 12/12 held at 확인 필요 (TEXT_LAYER_MISMATCH), 0 reached 제출 가능 | evaluation/phase_g/results/pdf_manipulation_pipeline.md | table and last line |
| 15 | 11.64 baseline (every OCR field to a person), dev, scans | docs/midterm/metrics.csv | 'B0 baseline,dev,review burden scanned'; evaluation/phase_d/PHASE_D_REPORT.md §3 |
| 15 | 3.82 Phase D (independent confirmation), dev, scans | docs/midterm/metrics.csv | 'D (S7 before D2),dev,review burden scanned'; PHASE_D_REPORT.md §4 |
| 15 | 7.23 D2 after safety rules (title gate, boundary margins, second-pass limit; owner-approved), dev, scans | docs/midterm/metrics.csv; evaluation/phase_d2/PHASE_D2_REPORT.md | 'D2 final (main)'; §11 |
| 15 | 3.73 Phase G (D3 internal confirmation merged), dev, scans | evaluation/phase_g/results/gate_summary_dev_final.md; docs/midterm/RESULTS.md | dev row; 'Automation' table |
| 15 | Hold-out 3: 7.68 (main baseline) → 4.28 (integrated), scans | evaluation/phase_g/PHASE_G_REPORT.md; docs/midterm/metrics.csv | §4 table; 'Phase G, hold-out 3, review fields' |
| 15 | Techniques: independent confirmation, safety rules, internal confirmations (GPA arithmetic, validity date pairs, value printed twice) | evaluation/phase_d/PHASE_D_REPORT.md §4; evaluation/phase_d2/PHASE_D2_REPORT.md §4; evaluation/phase_g/PHASE_G_REPORT.md §3 |  |
| 16 | Scan fields 257 → 268 / 275; photo fields 264 → 273 / 275 (main baseline → integrated), 0 wrong | evaluation/phase_g/PHASE_G_REPORT.md | §4 hold-out 3 table; docs/midterm/metrics.csv 'Phase G, hold-out 3, field accuracy' |
| 16 | university_name scans 9 → 19 / 20, photos 11 → 20 / 20 (percent = counts / 20 or / 275) | evaluation/phase_g/PHASE_G_REPORT.md; docs/midterm/RESULTS.md | §4 table; Accuracy table row 4 |
| 17 | Seal over text → stamp-aware second-pass reading (red channel); no number shown | evaluation/phase_g/PHASE_G_REPORT.md | §3 (stamp-aware second-pass reading, line 82); cause (1)/(3) of university-name errors, line 37 |
| 17 | University name 21/58 → 56/58 (scans, dev corpora) | evaluation/phase_g/results/university_name_before_after.txt; docs/midterm/RESULTS.md | before/after block; Accuracy table row 4 |
| 17 | Hidden text: 0 of 705 manipulated copies missed; example dates are the manipulation used in the suite (2099-12-31) and the probe (2025-01-31 vs 2027-12-31) | evaluation/phase_g/results/pdf_manipulation_suite.md; evaluation/phase_f/results/text_layer_probe.txt | table; probe output |
| 17 | Overfitting found by unseen data: hold-out 1 digital 174/275 (63 %) → hold-out 2 275/275 after fixes | evaluation/phase_d/PHASE_D_REPORT.md §8-9; evaluation/phase_d2/PHASE_D2_REPORT.md §6 | digital extraction rows |
| 18 | Development documents 299 + 279 + 279 = 857; hold-out 3 has 279 files, judged once | evaluation/datasets/synthetic/test_variants/README.md; holdout/README.md; holdout2/README.md; holdout3 manifest | file counts; evaluation/phase_g/final/session_log.txt |
| 18 | Injected-error cases: dev corpora 1,968 + 2,238 + 2,238 = 6,444; hold-out 3 2,238 | evaluation/phase_g/results/dev_final/F_inj_dev.md, F_inj_holdout.md, F_inj_holdout2.md; evaluation/phase_g/final/H3_integrated_inj.md | header line 'cases N' |
| 18 | Manipulated PDFs 705 (extraction suite) and 12 (API) | evaluation/phase_g/results/pdf_manipulation_suite.md; pdf_manipulation_pipeline.md | tables |
| 18 | Tests: backend 613, web unit 108, Playwright 15 run (22 total, 7 skipped) | docs/midterm/RESULTS.md; docs/operations/testing.md | Safety heading; Phase G paragraph |
| 19 | Limits: fictional documents; scans/photos partly need a person; no authentication, SQLite only tested | docs/midterm/RESULTS.md | 'Honest limits' |
| 19 | OCR does not guarantee authenticity or remove extraction errors | docs/architecture/ARCHITECTURE.md | 'Document intelligence pipeline' scope paragraph |
| 20 | November/December tasks (physical corpus, photo quality gate, reviewer queue and admin screen, real-document pilot; login, privacy, audit log, PostgreSQL, deployment, optional National Tax Service lookup) | docs/planning/ROADMAP.md; docs/midterm/ROADMAP.md | §November, §December tables |
| 20 | Goals: keep false 제출 가능 at 0 and reduce review items further (acceptance criteria) | docs/planning/ROADMAP.md | 'Acceptance for November/December' |
| 20 | Dates 10/15, 11/19, 12/10 (course schedule; the course deck also lists 10/22 for the first midterm) | docs/planning/ROADMAP.md; evaluation/phase_f/TECHNICAL_AUDIT.md | Dates paragraph; conflicts table item 4 |
| 22 | Full table (all rows) | docs/midterm/RESULTS.md; docs/midterm/metrics.csv; evaluation/phase_g/results/gate_summary_dev_final.md; evaluation/phase_g/final/ | Safety, Accuracy and Automation tables; see slides 14-16 |
| 23 | Six supported document types and their checks | docs/midterm/RESULTS.md; docs/midterm/DEMO_SCRIPT.md; evaluation/phase_g/PHASE_G_REPORT.md (GPA arithmetic) | Mentor requirements table; demo steps |
| 24 | Screenshot S6 without callouts | docs/midterm/v4/screenshots/S6_lookalike.png | demo scenario D5 |
| 25 | Screenshot S9 without callouts | docs/midterm/v4/screenshots/S9_tampered.png | B01 submission with one tampered 납세증명서 (see make_tampered_pdf.py) |
| 26 | Screenshot S5b without callouts | docs/midterm/v4/screenshots/S5b_missing.png | demo scenario D8 |
| 27 | Screenshot S10 without callouts | docs/midterm/v4/screenshots/S10_admin.png | http://localhost:3002 (placeholder pages; only the document-type list shows data) |
| 28 | Demo scenarios D1-D9 and expected results | docs/midterm/DEMO_SCRIPT.md; scripts/demo_scenarios.py | SCENARIOS tuple; steps table |
