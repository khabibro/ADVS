# Remaining failures and limitations

Evidence-driven. Each item is a measured observation from the final validation.
See `final_report.md` sections AA and AB for ranking.

## Accuracy

- **One wrong non-null personal name** from a scanned transcript, at 0.917 OCR
  confidence. Truthful evidence, wrong value. Contained by the evidence policy
  and unable to reach `READY`. Highest-priority defect carried forward.
- **Field recall 0.471.** Seventeen required fields unresolved across seven
  documents.
- OCR glyph errors without local uncertainty signals remain a limitation. P0
  added no dictionaries, no sample-specific corrections and no fuzzy identity
  matching.

## Structure — P1 territory

- **No table understanding.** A course table with seven distinct grade-point
  figures reads as seven conflicting candidates. The pipeline abstains. The
  earlier behaviour that appeared to resolve this selected the first match by
  reading order, which was correct only by accident.
- **Layout loss** on header-band and multi-line text, which is why university and
  department are unresolved on both enrollment and transcript samples.
- **Row grouping** across distant table cells does not pair label to value.
- **Section semantics** — separating a total row from per-block rows — are absent.

## Coverage gaps

- **Three supported document types are unexercised** by real input: graduation,
  career and national tax payment certificates.
- **No born-digital input.** Every corpus sample is an image-only scan, so the
  embedded-PDF-text ingestion and evidence route is entirely untested.
- **No real multi-page document.** Multi-page behaviour is validated only with
  mechanical fixtures, which support no accuracy claim.
- **No complete business pack.** The national tax payment certificate is absent
  from the corpus, so the four-document business workflow is
  `NOT_EVALUATED_COMPLETE_PACK`. Nothing was synthesised to fill the gap.

## Operational

- **Review load is structurally high.** Because every OCR-sourced value requires
  independent human confirmation, no scanned document can reach `READY` on
  machine output alone. All seven corpus documents ended in `REVIEW_REQUIRED`.
  This is safe but expensive.
- **Comparison normalisation differs between validation scopes.** Document scope
  lowercases and strips punctuation; submission-scope `string` comparison removes
  whitespace only. Both fail safe. See `security_regression.md`.

## Not started, by instruction

No new table engine, no new layout architecture, no VLM or LLM extraction, no
cloud OCR, no global deskew pipeline, no admin configuration UI.
