# P0 reproduced failures

Synthetic, non-sensitive diagnostics confirmed these current defects before production fixes:

| Finding | Status | Reproduction |
|---|---|---|
| F-01 upload resource check | CONFIRMED | A generated 1117×1408 pt valid PDF was rejected with `PIXEL_BUDGET_EXCEEDED` because storage projected OCR render pixels. |
| F-03 issue date | CONFIRMED | A valid bare issue date followed by an issuer was suppressed when footer text contained an issue-date-like label. |
| F-04 compound label shadowing | CONFIRMED | Short aliases such as `대표자` and `법인명` captured tails of compound labels when ordered before `대표자 성명` and `법인명칭`. |
| F-13 concurrent OCR | CONFIRMED | A second OCR call returned terminal `OCR_BUSY` while one native OCR call was active. |
| F-14 timeout/capacity | PARTIALLY_CONFIRMED | Timeout stopped waiting but left capacity unavailable until the native worker exited; the provider also scoped timeout to the whole document. |
| F-15 logging | CONFIRMED | Application logs depended on root logger level; after root was set to WARNING, app INFO logs disappeared. |
| F-16 review vocabulary | CONFIRMED | Extracted fields such as business address, business type, representative name, certificate number, and issue date were outside the review gate. |
| F-17 comparison semantics | CONFIRMED | Safe whitespace variation in company names produced `INFORMATION_MISMATCH`. |

The historical report of exactly two failing tests was not reproduced on clean `721cc9d` or current `main`; it appears to have described an intermediate uncommitted state from prior work.

## Addendum from final validation

Each finding above was re-tested against the completed P0 tree. All are fixed.
F-13, F-14 and F-15 were additionally re-verified against the **real** PaddleOCR
provider rather than a mock; see `multipage_validation.md`,
`concurrency_validation.md` and `security_regression.md`.

**F-01 had a second, distinct failure that P0 itself introduced.** Separating
storage security from the OCR raster budget was necessary but not sufficient.
The per-page pixel budget added by `fa38ef8` was applied to the PDF page box at
the configured render DPI, so a legitimate page whose box is about 3× A4 and
which carries a 72 DPI scan rendered 0.65 % over the budget and was rejected
with `RESOURCE_LIMIT`, failing in 14 ms. The PRE-P0 pipeline processed that same
document successfully, so this was a regression introduced during P0 rather than
a pre-existing defect.

The fix renders a page at the resolution its own embedded raster justifies —
never below it, only when the configured scale would breach the budget, never for
a vector page. Pages already within budget are unchanged. Three regression tests
were added. No sample value, dimension or filename is encoded in the fix. Details
and measurements are in `security_regression.md` section F-01.

The claim about the two historically reported red tests remains **not reproduced
on any committed revision**, re-checked in this run against a full suite of 350
passing tests.
