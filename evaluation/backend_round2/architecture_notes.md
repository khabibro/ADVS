# Architecture notes — after round 2

Describes how a document actually travels through ADVS after this round, and
why each stage behaves the way it does. Written for a reviewer who has not read
the previous audit.

---

## 1. Source selection — `services/processing.py::_obtain_source`

The single change from the previous round's per-page routing, and the source of
this round's most serious finding.

```
PDF?  ── yes ──> extract text layer ──> per page: usable? keep : needs OCR
      │
      no
      └────────> one page, needs OCR
```

Pages are then merged, sorted by page number, and each page carries its own
provenance, so a mixed digital/scanned PDF records which pages came from where.

**The trap.** Page enumeration must come from *the document*, not from *the
text layer*. The previous version enumerated OCR candidates from the text-layer
result, which is empty for a non-PDF — so an image document had an empty page
list and the OCR branch was never entered. Enumerating from the document is a
one-line difference and the difference between working and silently producing
nothing.

---

## 2. Image preparation — `preprocessing/processor.py::ImagePreprocessor`

Applies **only** when something is actually wrong, and writes a copy so stored
bytes and the upload checksum are untouched.

| Condition | Action |
|---|---|
| EXIF orientation ≠ 1 | `exif_transpose` — neither Pillow's `Image.open` nor PaddleOCR's loader applies it, so a phone capture tagged 6 otherwise reaches the detector sideways |
| suffix not in {jpg, jpeg, png, bmp} | transcode to PNG — PaddleOCR reads a fixed suffix set and cannot open `.webp` |
| neither | return the original path untouched |

Deliberately **not** present: deskew, denoising, contrast stretching,
binarisation. Measured skew stayed far below any threshold where correction
helps, and each of those can improve one capture while damaging the next.

---

## 3. OCR — `ocr/providers.py::PaddleOCRProvider`

* **288 DPI** rasterization for PDFs (4× the 72 DPI point grid). Retained from
  the previous round on measurement; not re-tuned.
* **Conditional orientation retry.** One extra pass with PaddleOCR's
  orientation classifier, but *only* when the first pass looks
  orientation-damaged (mean line confidence < 0.80, or < 120 characters per
  page). Keeping whichever pass scores better on confidence-weighted characters
  means an upright document never enters the path — always-on orientation was
  measured to drop mean confidence 0.933 → 0.717 on a real certificate.

---

## 4. Row grouping — `ocr/layout.py::build_rows`

**Unchanged this round.** Re-tested against all seven documents and found
correct.

Boxes join a row when they vertically overlap by ≥ 50 % of the shorter height,
then sort left to right. This is what reconstructs `성 명 :` from two boxes and
`재 학 증 명 서` from five. Rows never span pages.

Its known limit, confirmed this round: a box tall enough to span two text lines
bridges them into one row. See `remaining_failures.md` §1.

---

## 5. Candidate generation — `extraction/base.py::_row_candidates`

Walks consecutive segment runs (up to 5) so a label split across boxes still
matches, then resolves the value four ways:

```
label run ends with a colon and has text after it  -> that text
label run ends with no colon and has text after it -> that text
label run ends mid-segment, more segments follow   -> the NEXT segment (value_from_other_segment)
label run ends and there are no more segments      -> nothing
```

The fourth case gained a sibling this round: a label run that ends **on its
colon with nothing after it** now also falls through to the next segment. Ruled
tables and form layouts put the label and the value in separate boxes far more
often than in one, and treating "no value in this box" as "no value on this row"
abandoned real documents — an SME confirmation lost its company name, its
representative and its entire validity range to it.

Shape validation is then a hard gate: a candidate that is not structurally
possible for its field is rejected rather than ranked.

---

## 6. Normalization — `normalization/field_normalizer.py`

`canonicalize_numeric_text` folds NFKC and the dash family
(`‐ ‑ ‒ – — ― − ﹘ ﹣ －`) to ASCII. NFKC alone does not touch U+2013, and a
recognizer emitting typographic hyphens produced a document whose business
number and both validity dates all failed to match — on text that was otherwise
read correctly at 0.867 mean confidence.

Every normalizer returns `None` for ambiguous or invalid input. Nothing is
repaired, rounded or inferred.

---

## 7. The missing-field safety net — `validation/engine.py`

```
always:  expiration check (whenever a valid_until exists)
always:  missing-field net   <-- unless a REQUIRED_FIELD rule is configured
then:    configured rules
```

The middle line is unconditional because it is a statement about the *document's
evidence*, not about project policy. Previously any non-empty rule list
replaced it, so a checklist containing only submission-scope rule types produced
zero issues and a document with everything unresolved was `READY`.

Only a `REQUIRED_FIELD` rule may redefine "required", because that is the one
rule type that genuinely expresses it.

Narrowing this net to `EXPECTED_FIELDS` was tried and **reverted** — see
`experiments.md` E2. Which fields a type requires is a product decision.

---

## 8. Where confidence is decided

There is no confidence stage inside `process()`. Confidence is a *read-time*
policy (`evidence_sufficiency.py`): a field is shown as trustworthy only when it
has a value, evidence, is not marked for review, and its supporting OCR lines
meet the confidence floor.

This round produced the counterexample that matters: R2-03's `student_name`
came back with confidence 0.917 and assessment `SUFFICIENT`, and was **wrong**.
Confidence is evidence quality, not correctness.
