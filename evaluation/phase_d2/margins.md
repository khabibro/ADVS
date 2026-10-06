# Decision-boundary margins (D2-2) and plausibility bound (D2-5)

Policy table: `BOUNDARY_MARGINS` and `MAX_VALIDITY_SPAN_DAYS` in `apps/api/app/document_intelligence/auto_acceptance.py`.

| Parameter | Value | Why |
|---|---|---|
| `date_days` (N) | **10 days** | E11 moves an expired `valid_until` / too-old `issue_date` to 0, 1, 3 or 7 days on the valid side of the boundary. 10 keeps a margin over the largest tested shift and over the largest jump a *day-digit* confusion can cause (0↔8 = 8 days). Single-glyph confusions of a date (explicit table 0↔8, 1↔7, 3↔8, 5↔6, 6↔8, 2↔7) over the 14 distinct dates of both development sets give 91 valid alternatives: 16.5 % move the date ≤ 7 days (day digit), 2.2 % about a month (month digit 5↔6), 81 % move it by more than 200 days (year or month tens digit). A larger N would only add the month-digit class (+2 %), but it would send every 납세증명서 / 완납증명원 (they normally expire 20–30 days after issue) to a human and remove the scanned all-valid READY, so N is deliberately small. |
| `gpa` (X) | **0.5** | E12 moves a GPA below the 3.0 threshold to 3.00–3.10 (distance ≤ 0.1). First-decimal confusions move a GPA 0.1–0.8 (9 alternatives over the development GPAs: ≤ 0.5 covers 67 %). 0.8 would also catch 3.8 against the 3.0 threshold and send ordinary GPAs to a human. |
| `MAX_VALIDITY_SPAN_DAYS` | **400** | A year/month digit misread (the 81 % class above) moves a validity end by years; a certificate's validity never exceeds about one year (SME: 355 days in both development sets; tax / social: 30). A `valid_until` more than 400 days after the issue date (or the validity start), or before the issue date, is not auto-accepted. |

A margin only applies to a value confirmed **only** by a second OCR pass; values confirmed by another document or by the application value are unchanged.

Residual (D2-5): a misread that is identical in both passes, lands well clear of every boundary and keeps the dates mutually plausible (for example a day-and-month digit pair) is still auto-accepted. See the report.
