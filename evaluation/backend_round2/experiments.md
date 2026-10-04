# Experiments

Each entry records a hypothesis, what was measured, and what was decided. An
experiment that did not survive is kept here with its reasoning, because "we
tried it and rejected it" is evidence too.

---

## E1 — Non-PDF source selection

**Hypothesis.** Page enumeration for OCR is coupled to the PDF text-extraction
path, so image documents produce an empty page list and never reach OCR.

**Baseline.** R2-02 / R2-03 / R2-06 completed in 5.5–6.9 ms with zero
`OCRResult` rows, `UNKNOWN` type and no fields. A PDF-only hypothesis was
confirmed by `git show 2228b75:…/processing.py`, where any non-PDF took the OCR
branch.

**Treatment.** A non-PDF upload is enumerated as exactly one page that only OCR
can read.

**Result.** 6/7 → 7/7 processed. Classification 3/7 → 7/7.

**Decision.** Adopt. This is a correctness fix with no measurement attached to
it — the baseline was simply broken.

---

## E2 — Narrowing the missing-field net to EXPECTED_FIELDS

**Hypothesis.** The net fires for every field the extractor declares, including
opportunistic ones. Scoping it to the domain's own `EXPECTED_FIELDS` would
match what the read-time `missing_expected_fields` list shows the user.

**Result — rejected.** Implemented, measured, reverted.

| | net over all fields | net over EXPECTED_FIELDS |
|---|---|---|
| dev validation accuracy | 83/86 | 80/86 |
| dev samples changed | 0 | 7 |

Seven synthetic samples moved, and **five of them were new false READY**: a
사업자등록증 missing 사업의 종류 and a SMEs confirmation missing an issue date
flipped `REVIEW_REQUIRED` → `READY`. Two were improvements (gold `PASS`, the
old behaviour was a false alarm).

**Decision. Rejected.** The change silences a real "this document is
incomplete" signal to fix a real false alarm, and *which fields a document type
requires* is a product decision, not a bug fix. The final change is strictly
minimal: the net is suppressed only when a checklist actually configures a
`REQUIRED_FIELD` rule — the one rule type that genuinely redefines "required".
Synthetic dev/held-out/recreated are then bit-identical to the baseline.

---

## E3 — Bare issue date in the issuance block

**Hypothesis.** Certificates print the issue date as an unlabelled line, so a
label-only search can never find it. Four of seven documents show this.

**Treatment A — uniqueness only.** Answer when every bare date on the document
normalizes to the same value.

**Result — rejected.** An existing regression test
(`test_transcript_does_not_guess_issue_date_or_gpa_from_unlabeled_numbers`)
correctly refuses it: a lone `2026-09-20` in a transcript body next to grades
became the issue date. Uniqueness is necessary and not sufficient.

**Treatment B — uniqueness *and* issuance context.** Also require the rows just
below the bare date, on the same page, to name an issuer.

**Result.** R2-04, R2-05, R2-06, R2-07 issue dates recovered, all four correct.
The transcript-body test still passes.

**Guard rails recorded.** The issuer vocabulary is closed and enumerated
(institution nouns + Korean officer-title suffixes). It never crosses a page
boundary. It only runs when the labelled search found nothing, so a document
that *has* an issue-date label which failed to read still reports unresolved
rather than silently substituting another date. Two bare dates that disagree
leave the field unresolved.

**Decision.** Adopt.

---

## E4 — 288 DPI retested

**Kept.** Not re-tuned. Every document that reached OCR was recognised at mean
line confidence 0.82–0.96, and the defects found were not resolution-shaped.
Raising resolution was rejected: PaddleOCR already resizes past its own
`max_side_limit` (5632×4468 → 4000), so higher input DPI costs time and memory
without increasing the pixels the detector sees. Measured end-to-end processing
time is in `comparison.json`; the increase there is explained by OCR now
actually running on the three image documents, not by a resolution change.

---

## E5 — Conditional orientation retry

**Kept, unchanged.** No rotated sample exists in this dataset. It was not
exercised, so it was not touched. The property that matters — that an upright
document never enters the retry path — is pinned by the existing threshold
tests, and the live run confirms upright pages are unaffected: all seven
classified correctly with no retry.

**Open.** Rotation remains partially supported. The retry fires when mean
confidence < 0.80 or fewer than 120 characters per page, which is a heuristic,
not an orientation measurement.

---

## E6 — Table parsing (PP-StructureV3)

**Deferred, not attempted.** R2-04's student name and student id are lost
because the detector produced one box, `학성`, 88 px tall where its neighbours
are 42–45 px, straddling two text lines and two table columns. The column
membership of each character is destroyed *inside the box*. No amount of
row-grouping or candidate-ranking heuristic can recover it, and any rule that
tried would be inventing a mapping.

Running a layout/table model is the principled remedy and is a genuine
experiment. It was **not** run in this round because it is an architecture
decision with its own latency and CPU budget, and this round's mandate was to
fix proven defects and leave Round-2 changes reviewable. It is the top
recommendation in `remaining_failures.md`.

---

## E7 — Deskew and image preprocessing

**Rejected for now.** `ImagePreprocessor` existed with zero callers. Rather than
wire it in wholesale, it was refactored into *conditional* preparation with a
deliberately narrow scope: EXIF orientation (a declaration of how pixels should
display, which the OCR loader ignores) and codec (PaddleOCR cannot open
`.webp` at all). Both apply only when actually wrong; a normal JPEG or PNG takes
exactly the path it took before.

Deskew, denoising, contrast stretching and binarisation were **not** added.
Measured skew across both real-document rounds stayed far below any threshold
where correction helps, and each of these can improve one capture while
damaging the next. Adding them without evidence would be the kind of
"it looks cleaner" change this round is meant to avoid.

---

## E8 — Business-registration-number checksum

**Investigated, not implemented.** There is no published Korean government
checksum for 사업자등록번호. The 10 digits are `NNN-NN-NNNNN` (앞 6 = 국세번호
based, 뒤 4 = 순번) with **no** algorithmic validity test — the tax office does
not expose one. The only authoritative check is a live 국세청 API lookup.

**Decision.** Do not implement. A fabricated checksum would reject valid
numbers or accept invalid ones, and it would give false assurance that the
system validates business numbers, which it does not. Verified against
국세청和技术 sources during the round.

---

## E9 — Live platform verification

Ran the full browser-equivalent sequence against the running `docker compose`
stack — create project → upload → process → detail → verify → reviews → refresh
— for all seven documents.

Result: identical behaviour to the in-process harness, `LIVE PLATFORM FAILURES:
0`, refresh and reprocess stable on every document. This is what established
that the in-process evaluation reflects deployed behaviour and not a test
artifact.
