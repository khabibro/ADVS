# Phase 4 notes for the applicant web (for Munira's review)

1. **Show the applicant their link.** After a submission is created the API returns `access_token`
   once. Show the full link (`/projects/{id}?token=...` or the agreed route), a **copy button** and a
   "이 링크를 저장해 두세요. 링크를 잃으면 제출 내용을 다시 열 수 없습니다" message. The token must
   not live only in browser storage (`submission-tokens.ts` is a convenience cache): opening the
   link on another device has to work, so the page reads the token from the link and stores it.
2. **Drafts and "제출하기".** Checks while uploading are previews dated today. Only the explicit
   "제출하기" button calls `POST /projects/{id}/finalise`, which freezes the check date. Say so on the
   button ("제출하면 오늘 날짜로 점검 기준일이 정해집니다").
3. **Home list.** `GET /projects` is admin-only; the applicant home lists the submissions known to
   this browser (stored tokens) or just opens the saved link.
4. **Image URLs** carry `?token=`; do not copy them into links the applicant shares.
