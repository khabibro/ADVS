# ADVS midterm demo — presenter script (8–10 minutes)

Before you start: `make demo` (or `make demo-rehearsal` first — see the end). Open **http://localhost:3000/projects**. The eight demo submissions are already processed; the list shows D1 at the top. Browser zoom 100 %, window 1280×720 or larger. Do **not** change the 점검 기준일 (2026-10-05, the date the test documents were made for).

| # | Click | The audience should notice | Say (one sentence) |
|---|---|---|---|
| 0 | Project list | Eight cards, three status colours | "Each card is one submission; ADVS gives each one of three results." |
| 1 | **D1 정상 제출 (기업)** | Green **제출 가능**, four documents analysed, 0 issues; the note under it | "All four business documents are present, valid and consistent — and 제출 가능 means no problem found in our configured pre-check, not official approval." |
| 2 | Open a document via **결과 보기** → "근거 정보 보기" | Extracted fields, page number and source text | "Every value shows where it came from, so a person can check it." |
| 3 | Back, **D2 만료된 납세증명서** | Red **보완 필요**; card "유효기간이 만료되었습니다" with 유효기간 종료일 **2026. 08. 31.** vs 기준일 2026. 10. 05. | "The tax certificate expired on 31 August, so the system asks for a new one." |
| 4 | **D3 회사명 불일치** | 보완 필요; card shows "주식회사 테스트상사 ↔ 주식회사 가나다솔루션" | "The tax certificate belongs to a different company; ADVS compares the documents with each other." |
| 5 | **D4 회사명 표기 차이** | 제출 가능 although the name is written 주식회사 / (주) / ㈜ on different documents | "Same company, written four ways — ADVS normalises notation instead of raising a false alarm." |
| 6 | **D5 유사 문서 (지방세)** | **확인 필요**; 국세 납세증명서 slot empty; file flagged "문서 확인 필요" with "지원하지 않는 서류이거나 다른 종류의 서류일 수 있습니다" | "A local-tax certificate looks similar but is not the required national-tax one; ADVS refuses to count it and never says 제출 가능." |
| 7 | **D8 필수 서류 누락** | 보완 필요, 사업자등록증 slot "업로드 필요" | "A required document is missing." |
| 8 | **D7 정상 제출 (학생)** | 제출 가능 for the student workflow (재학증명서 + 성적증명서) | "The same engine runs the student workflow with its own rules, such as the 90-day issue date and the student number." |
| 9 | **D6 스캔본 제출 + 사람 확인** | 확인 필요 with **4건**; under 직접 확인할 항목 each value shows 자동 인식 값, the reason ("다른 서류나 재판독으로 같은 값을 확인하지 못했습니다") and OCR confidence; open a 결과 보기 → fields marked **자동 확인 · 다른 서류와 일치** | "On scans, ADVS accepted company names and business numbers by itself because other documents agree, and asks a person only for the four validity dates." |
| 10 | Click **확인하기** on an item → **검토 저장** (repeat for all four; "근거 정보 보기" first on one) | Items disappear; card says 점검 전 | "The reviewer compares the original and confirms; nothing is accepted silently." |
| 11 | **자동 점검 실행** | Status turns **제출 가능** | "After the review the pre-check runs again and the submission becomes 제출 가능." |
| 12 | (If asked) new submission → upload one PDF | "분석 중" state, then 분석 완료 | "Upload and analysis run live." |

Closing sentence: "Digital PDFs are read perfectly on our tests; scans need a person for what the system cannot confirm — and in every test run it never said 제출 가능 wrongly."

**Re-do step 10–11 for the audience?** Run `make demo-reset` (about 2 minutes), then D6 is back in its starting state.

## Live upload (step 12)
Use a **digital** PDF (analysis takes under a second), e.g. `evaluation/datasets/synthetic/test_variants/business/B01_all_valid/digital/`. A scanned PDF works but takes about 15–20 seconds per page while the OCR runs (the screen shows "분석 중"). The web upload accepts PDF files only.

## Avoid on stage
- Do not click **다시 점검** after changing the date; do not upload real or personal documents.
- Do not demo the admin app (http://localhost:3002): it is an empty shell.
- Do not say the system is "official" or "approved"; do not quote percentages beyond `RESULTS.md`.
- While a scan is being analysed the API is busy — don't click around other submissions.

## If something goes wrong
1. **Page shows an error or looks stale:** reload the browser tab. If the data looks wrong or a step was clicked twice: `make demo-reset` (clean database + all eight scenarios, ~2 min), then reload.
2. **Nothing loads at all:** `make demo-stop && make demo` (the OCR model warm-up is logged: `storage/demo/logs/api.log`, line "OCR model ready"). Port 3000 busy? Stop the other dev server first (`lsof -iTCP:3000 -sTCP:LISTEN`), or start with `WEB_PORT=3100 make demo`.
3. **Check everything in 4 minutes, the morning of the presentation:** `make demo-rehearsal` — prints a PASS/FAIL table for D1–D8 and ends with the demo in its clean state (it resets first).
4. **Fallback:** the screenshots in `docs/midterm/screenshots/` (1280×720; 1920×1080 in the sub-folder) show each scenario's final screen (`D1…D8_workspace.png`), the review flow (`R1…R4`) and a live upload (`U1…U3`). Show them as slides if the live demo cannot be recovered.
