# P0 implementation log

## P0-001 issue-date locality
- Problem: footer label text globally suppressed valid bare issue-date inference.
- Reproduction: synthetic footer plus legitimate issue-date block returned null.
- Root cause: `issue_date_field` scanned the whole source for labels after labelled extraction failed.
- Fix: allow semantic bare issue-date inference unless a local unresolved issue-date label appears before the candidate on the same page; keep ambiguity abstention.
- Tests: `test_issue_date_footer_label_does_not_suppress_valid_bare_issue_date`, existing issue-date abstention tests.
- Result: footer case resolves; local unreadable label and ambiguous dates still abstain.

## P0-002 label matching semantics
- Problem: shorter aliases shadowed compound labels.
- Reproduction: `대표자` before `대표자 성명` captured `성명 ...`; `법인명` before `법인명칭` captured a suffix.
- Root cause: matching depended on caller list order.
- Fix: row label matching tries longer compact labels first for every call.
- Tests: compound label order test.
- Result: order independent for overlapping aliases.

## P0-003 review vocabulary
- Problem: extracted optional fields could not be reviewed because review target validation used only `EXPECTED_FIELDS`.
- Root cause: expected workflow fields and supported/reviewable fields were conflated.
- Fix: added derived `SUPPORTED_FIELDS` and `REVIEWABLE_FIELDS`; review and rule validation use reviewable fields while defaults continue to use expected fields.
- Tests: extractor-supported reviewability test plus full review/verification suites.
- Result: optional fields are reviewable without becoming default required.

## P0-004 comparison semantics
- Problem: safe whitespace differences caused deterministic mismatch.
- Root cause: field comparison used stored normalized value equality directly.
- Fix: added comparison-only keys that remove safe formatting differences without changing evidence values.
- Tests: company whitespace comparison test and full submission verification suite.
- Result: spacing-only company variation passes; no fuzzy identity matching added.

## P0-005 upload/resource separation
- Problem: storage validation applied OCR render DPI and render pixel budget to upload acceptance.
- Root cause: storage layer coupled to OCR rasterization configuration.
- Fix: PDF upload validation now checks parser safety, encryption, page count, and actual page dimensions; OCR render pixel checks remain in OCR processing.
- Tests: large valid PDF upload test and updated ingestion boundary test.
- Result: legitimate audited dimensions accepted; encrypted/corrupt PDFs still rejected.

## P0-006 OCR scheduler and timeout scope
- Problem: normal OCR contention returned terminal `OCR_BUSY`; timeout was scoped to whole document in provider.
- Root cause: non-blocking capacity acquisition and outer document-level OCR worker call.
- Fix: bounded OCR slot waits instead of failing; provider runs OCR inference per page with per-call timeout.
- Tests: timeout recovery/concurrency regression and full OCR provider suite.
- Result: second request waits; timeout does not permanently poison later work after native worker exits.

## P0-007 logging isolation
- Problem: app logs depended on root logger state.
- Root cause: `configure_logging` attached ADVS JSON logging only to root.
- Fix: app-owned logger `app` has its own handler and does not propagate to root.
- Tests: root level change logging regression.
- Result: app logs survive root level changes.

## P0-008 oversized PDF page box rejected at the OCR raster budget
- Problem: a legitimate scanned PDF whose page box is about 3x A4 and which carries a 72 DPI scan was rejected with `RESOURCE_LIMIT`. The PRE-P0 pipeline processed it, so P0 had introduced the rejection when it added the per-page pixel budget.
- Root cause: the budget was applied to the declared page box at the configured render DPI. Rasterising a 1117x1408 pt box at 288 DPI yields 25,163,776 px against a 25,000,000 cap. The page box overstates its own content by 4x, so the oversampling added cost and time without adding evidence.
- Fix: `PaddleOCRProvider._page_render_scale` derives, per page, the scale the page's embedded raster justifies and applies it only when the configured scale would breach the budget. It never renders below the source resolution, leaves any page already within budget untouched, and never downsamples a vector page, which has no source resolution to fall back to. The effective scale and the reason are recorded in the page transform metadata.
- Tests: oversized page box is rendered at its own resolution and not rejected; a page within budget still renders at the configured DPI; a vector page is never downscaled.
- Result: the document processes; the two corpus PDFs already within budget render bit-for-bit identically. The fix depends only on the relationship between a page's declared geometry and its embedded raster, so it generalises beyond the sample that exposed it.

## P0-009 validation harness could not locate the sample corpus
- Problem: the real-document runner raised `FileNotFoundError` for every sample, which had been recorded as the evaluation being blocked on a missing dataset.
- Root cause: the runner resolved samples against the Desktop root, while the samples live in a `samples` subfolder. The files were present the whole time.
- Fix: `desktop_dirs`/`resolve_source` search the sample subfolders and then the Desktop root, read-only, with an `ADVS_SAMPLE_DIR` override.
- Result: the corpus became evaluable. No source file was moved, renamed, copied or modified; ground truth, denominator and verdict semantics were untouched, so the PRE-P0 comparison remains valid.
