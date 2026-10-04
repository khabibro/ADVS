# Real-document validation — Round 2

Baseline commit: `721cc9dfa6ba9d0691ddb355ea62912ab3ea128a` ("Improve real-document processing and extraction")

This directory holds safe, value-free results for round 2. Everything here is
derived from local runs on the project owner's own machine. **No document was
uploaded anywhere, no external OCR or LLM/VLM service was called, and no
document, OCR dump or ground-truth value is committed.**

---

## What was evaluated

Seven documents the project owner placed at the top level of `~/Desktop`:

| ID | Document | Type | Source | Sensitivity | Layout family |
|---|---|---|---|---|---|
| R2-01 | 4대 사회보험료 완납증명서 | SOCIAL_INSURANCE | synthetic placeholder | none | full table, label left / value right |
| R2-02 | 사업자등록증 | BUSINESS_REGISTRATION | near-real | none | letter-spaced key/value + 2D barcodes |
| R2-03 | 성적증명서 | TRANSCRIPT | **real** | high (personal) | dense 3-column course table |
| R2-04 | 성적증명서 | TRANSCRIPT | near-real, anonymised | none | 3-column course table |
| R2-05 | 재학증명서 | ENROLLMENT | **real** | high (personal) | letter-spaced key/value + stamp |
| R2-06 | 중소기업확인서 | SME_CONFIRMATION | near-real | low | letter-spaced key/value, ~50 DPI |
| R2-07 | 재학증명서 | ENROLLMENT | near-real, anonymised | none | letter-spaced key/value + stamp |

Discovery had to be Unicode-tolerant: the Korean filenames are stored in NFD on
this filesystem while the names are written in NFC. Exact byte matching finds
nothing.

## Headline result

| | baseline | final | delta |
|---|---|---|---|
| Documents uploaded | 6 / 7 | 7 / 7 | +1 |
| Rejected at upload | 1 | 0 | -1 |
| Classification correct | 3 / 7 | **7 / 7** | +4 |
| Fields CORRECT | 4 | **17** | +13 |
| Fields INCORRECT | 0 | 1 | +1 |
| Fields UNRESOLVED | 25 | **16** | -9 |
| Field precision | 1.000 | 0.944 | -0.056 |
| Field recall | 0.138 | **0.500** | +0.362 |
| **False READY documents** | 3 | **0** | -3 |

Two things to read carefully:

* **Precision dipped because coverage grew.** The baseline produced four values
  and all four were right. It produced them on the one document that happened
  to survive routing. Adding capacity recovered thirteen more fields, one of
  which is wrong. A wrong value is worse than a missing one, so this is a real
  cost — but it is now *visible* and *reported*, which is the point of the
  wrong-non-null metric.
* **Recall is the honest headline.** 0.50 means half of what these documents
  actually state is still not extracted. That is the real state of the system,
  not a rounding artefact.

## What was found

The round found **one catastrophic regression, one critical safety hole and
four high-severity extraction defects**, all against the code as committed.
The full taxonomy with evidence is in `failure_analysis.json`.

The single most important finding: **every PNG and JPEG upload was being
processed to nothing.** Source selection enumerated the pages needing OCR from
the PDF text layer; a non-PDF never appears there, so OCR was never called. The
document finished `COMPLETED` with zero text, `UNKNOWN` type and no fields —
looking exactly like success. This was introduced by the previous round's
per-page routing fix, which improved mixed PDFs and, in doing so, silently
disabled the entire image path. Three of the seven documents were affected.

Second: **a checklist could switch off the missing-field safety net.** Any
non-empty configured rule list replaced the net, and when none of those rules
was executable at document scope the engine emitted nothing and the status
defaulted to `READY`. Three documents with every required field unresolved were
reported ready to submit.

## What is still not working

* Dense multi-column transcript headers. One OCR box spans two text lines and
  two table columns, which destroys which-column-belong-to information before
  any layout stage runs. This is a table-structure problem, not a
  heuristic-tuning problem.
* `university_name` when the only instance of the name is under an official
  seal — the last character is occluded, and shape validation correctly
  refuses the fragment.
* One Hangul syllable misread in a personal name at 743×1020 px, reported with
  confidence 0.917 and a `SUFFICIENT` evidence assessment. Confidence is not
  correctness, and this is the round's proof of it.
* Project-level verification can report `READY` while the same document reports
  `REVIEW_REQUIRED`. Raised as a product question, not fixed here.

## Reading order

1. `dataset_summary.json` — what was tested, safe metadata only
2. `baseline_summary.json` / `final_summary.json` — full metrics
3. `comparison.json` — before/after
4. `failure_analysis.json` — taxonomy by earliest responsible stage
5. `experiments.md` — what was tried, what was rejected, and why
6. `remaining_failures.md` — precise statement of what still fails
7. `architecture_notes.md` — how the pipeline works after this round

`work/` is gitignored and holds the raw runs, the rendered pages used for
visual inspection, and the ground-truth annotations transcribed from the
documents. It contains personal data and must never be committed.
