# ADVS midterm demo — presenter script, v2 (8–10 minutes)

This script is for the **v2 interface** (tag `midterm-demo-v2`). The v1 script and tag (`midterm-demo-2026-10-14`) stay available: `DEMO_SCRIPT_v1.md`.

Before you start: `make demo` (and, the morning of the presentation, `make demo-rehearsal`). Open **http://localhost:3000/projects**. Eight submissions are already processed; the list shows D1 at the top with each one's status and what to do. Browser zoom 100 %, window 1280×720 or larger. Do **not** change the 점검 기준일 (2026-10-05, the date the test documents were made for).

| # | Click | The audience should notice | Say (one sentence) |
|---|---|---|---|
| 0 | Project list | Eight cards: status, "아래 N개 항목을 보완해 주세요" and "필수 서류 x / y 확인 완료" on each | "Every submission tells you its state and what to do next, before you open it." |
| 1 | **D1 정상 제출 (기업)** | Green banner **제출 가능** "(공식 승인 아님)", four rows **제출됨 · 확인 완료**, no issue list | "All four documents are present, valid and consistent — and 제출 가능 means no problem found in our configured pre-check, not official approval." |
| 2 | **서류 내용·근거 보기** on one row | The page image next to the fields; every field has a badge (디지털 원본 / 자동 확인 — …); click a field and its box lights up on the page | "Every value shows where it came from, so a person can check it in seconds." |
| 3 | Back, **D2 만료된 납세증명서** | Red banner **보완 필요 · 아래 1개 항목을 보완해 주세요**; the row says 보완 필요; the issue reads "유효기간 종료일 2026. 08. 31. — 점검 기준일 2026. 10. 05.보다 이전입니다" with **해결 방법** | "It names the date, the document, and how to fix it." |
| 4 | **D3 회사명 불일치** | The issue quotes both names: “주식회사 테스트상사” ≠ “주식회사 가나다솔루션” | "The tax certificate belongs to another company; ADVS compares the documents with each other." |
| 5 | **D4 회사명 표기 차이** | 제출 가능 although 주식회사 / (주) / ㈜ are written differently | "Same company written four ways — notation is normalised, no false alarm." |
| 6 | **D5 유사 문서 (지방세)** | **확인 필요**; the 국세 납세증명서 row says **미제출**; the file sits under "확인이 필요한 파일" with "지원하지 않는 서류이거나 다른 종류의 서류일 수 있습니다" | "A local-tax certificate looks similar but is not the required one; ADVS refuses to count it and never says 제출 가능." |
| 7 | **D8 필수 서류 누락** | 보완 필요; the 사업자등록증 row says **미제출** with an **업로드** button in the row | "A missing document is marked right where it belongs." |
| 8 | (Live) in the D8 row click **업로드** and choose `B01-1_사업자등록증.pdf` (digital, under a second) | "분석 중" with the elapsed time, then the banner turns **제출 가능** on its own | "Upload, analysis and the check run live, and nobody has to press a check button." |
| 9 | **D7 정상 제출 (학생)** | 제출 가능 for the student workflow | "The same engine runs the student workflow with its own rules (90-day issue date, student number)." |
| 10 | **D6 스캔본 제출 + 사람 확인** | Yellow banner **확인 필요 · 담당자 확인이 필요한 항목이 4개 있습니다**; "확인할 항목 4개 · 0 / 4 완료"; each value has the **cropped original** with the label and the value outlined, and the reason ("다른 서류나 재판독으로 같은 값을 확인하지 못했습니다") | "On scans ADVS accepted the names and business numbers by itself because other documents agree; it asks a person only for the four validity dates." |
| 11 | Click **원본과 같음 · 확인 (Enter)** once; then press **Enter** three more times (focus moves to the next item) | Progress "1 / 4 … 4 / 4 완료"; after the last one the banner changes by itself to **제출 가능** with "방금 확인 필요 → 제출 가능(으)로 바뀌었습니다" | "The reviewer compares the original and confirms; the pre-check re-runs automatically." |

Closing sentence: "Digital PDFs are read perfectly on our tests; scans need a person for what the system cannot confirm — and in every test run it never said 제출 가능 wrongly."

**To show the review again:** `make demo-reset` (about 2 minutes), then D6 is back in its starting state.

## Live upload notes
- Digital PDFs finish in under a second; a scanned PDF or a photo takes about 15 seconds per page (the screen shows 분석 중 and the elapsed seconds, and says so).
- Photos (JPG, PNG, WEBP) are accepted like PDFs.
- An unsupported or damaged file is explained in plain Korean with what to do (try a `.txt` file or `F16a_사업자등록증_손상.pdf` from the test set if asked).

## Avoid on stage
- Do not change the 점검 기준일 or use "날짜를 바꿔 다시 점검하기"; do not upload real or personal documents.
- Do not demo the admin app (http://localhost:3002): it is an empty shell until the November work.
- Do not say the system is "official" or "approved".
- While a scan is being analysed other screens keep working, but the analysis itself takes its time.

## If something goes wrong
1. **A page shows an error or looks stale:** reload the tab. If the data looks wrong or a step was done twice: `make demo-reset`, then reload.
2. **Nothing loads at all:** `make demo-stop && make demo` (the OCR model warm-up is logged: `storage/demo/logs/api.log`, line "OCR model ready"). Port 3000 busy? Stop the other dev server (`lsof -iTCP:3000 -sTCP:LISTEN`) or start with `WEB_PORT=3100 make demo`.
3. **Check everything in 4 minutes the morning of the presentation:** `make demo-rehearsal` — D1–D8 through the API, then a browser check that every screen shows what the API decided; ends with the demo in its clean state.
4. **Fallback screenshots:** `docs/midterm/screenshots_v2/1280x720/` (plus `1920x1080/` and `390x844_mobile/`): each scenario (`D1…D8_workspace.png`), the review flow (`R1…R4`), the upload flow (`U0…U2`), the evidence page (`D6_document_detail.png`) and the error states (`E1`, `E2`). Before/after pairs are in `before/`.
5. **Fall back to the previous version:** `git checkout midterm-demo-2026-10-14 && make demo-reset` and present from `DEMO_SCRIPT_v1.md`.
