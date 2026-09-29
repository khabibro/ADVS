# ADVS Document-Intelligence Backend — Architecture BEFORE the audit

Captured at commit `2228b75` (branch `main`, clean worktree).
Produced by direct source reading; no behaviour was changed to produce this.

## 1. Complete stage map

| # | Stage | Module / symbol | Notes |
|---|-------|-----------------|-------|
| 1 | Upload route | `app/api/v1/routes.py` → `upload_document` | multipart, size/type validated in `app/core/errors.py` |
| 2 | File validation | `app/api/v1/routes.py`, `app/services/storage/local.py` | extension + magic-byte sniffing |
| 3 | Storage | `app/services/storage/local.py::LocalStorageService` | renames to a UUID; keeps `original_filename` in DB |
| 4 | PDF/image detection | `mime_type` on the `Document` row | mime is decided at upload, not re-derived |
| 5 | Embedded-text extraction | `preprocessing/processor.py::PdfProcessor.extract_text` | PyMuPDF `get_text("dict")` → one `OCRLine` per PDF text line, `confidence=None`, bbox in **PDF points** |
| 6 | Text-quality gate | `preprocessing/processor.py::is_meaningful_text` | `len>=30` **and** `>=15` alnum — **evaluated once for the whole document** |
| 7 | Rasterization | `ocr/providers.py::PaddleOCRProvider._input_images` | `fitz.Matrix(2,2)` → **144 DPI**, PNG, `alpha=False` |
| 8 | Preprocessing | `preprocessing/processor.py::ImagePreprocessor.normalize` | **DEAD CODE** — no caller anywhere in `app/` or `scripts/` |
| 9 | OCR provider | `ocr/providers.py::PaddleOCRProvider` | `lang=korean`, `korean_PP-OCRv5_mobile_rec` + `PP-OCRv5_mobile_det`, CPU |
| 10 | Orientation / unwarping | PaddleOCR kwargs | `use_doc_orientation_classify=False`, `use_doc_unwarping=False`, `use_textline_orientation=False` |
| 11 | OCR result representation | `ocr/models.py::OCRPage` / `OCRLine` / `BoundingBox` | line-level only; **no word/token level, no blocks, no tables** |
| 12 | Reading order | `ocr/text_assembly.py::order_lines` | y-band (`round(y_center/12)`) then x; **disabled entirely if any line lacks a bbox** |
| 13 | Classification | `classification/classifier.py::DocumentClassifier` | weighted keyword sum, `heuristic-v3`; **haystack includes `filename`** |
| 14 | Extractor selection | `extraction/registry.py::ExtractorRegistry` | one class per `DocumentType`; `UNKNOWN` → no extractor |
| 15 | Candidate discovery | `extraction/base.py::candidate_after_label` / `candidate_right_of_label` / `candidate_matching_line` | regex over *whole lines*; **first match wins** |
| 16 | Candidate selection | *none* | no ranking, no scoring, no competition between candidates |
| 17 | Normalization | `normalization/field_normalizer.py` | date / business number / GPA / text; returns `None` rather than guessing |
| 18 | Canonical result | `results.py::CanonicalDocumentResult.compose` | |
| 19 | Persistence | `services/processing.py::_persist_success` | `OCRResult`, `ExtractedField`, `ValidationResult` |
| 20 | Evidence policy | `evidence_sufficiency.py::EvidenceSufficiencyPolicy` | `evidence-policy-v1`, OCR floor `0.90` |
| 21 | Effective fields | `services/reviews.py`, `EvidenceSufficiencyPolicy.assess` | |
| 22 | Verification | `validation/engine.py`, `validation/submission.py` | fully deterministic |

## 2. Data-flow diagram

```mermaid
flowchart TD
    U[Upload] --> S[LocalStorageService<br/>UUID filename]
    S --> R{_obtain_source}
    R -->|"mime == pdf"| P[PdfProcessor.extract_text]
    P --> G{is_meaningful_text<br/>WHOLE DOC}
    G -->|"yes"| E[Embedded text<br/>OCRPage/OCRLine, conf=None,<br/>bbox in PDF points]
    G -->|"no"| O[OCRProvider.extract_document]
    O --> RA[fitz.Matrix(2,2)<br/>144 DPI raster]
    RA --> PA[PaddleOCR detect+recognize<br/>korean_PP-OCRv5_mobile]
    PA --> NL[_normalize_page<br/>per-box OCRLine]
    E --> AS[assemble_document_text]
    NL --> AS
    AS --> CL[DocumentClassifier.classify<br/>text + FILENAME]
    CL --> EX[ExtractorRegistry.extract]
    EX --> CA[candidate_after_label<br/>regex per line, FIRST match]
    CA --> NM[normalize_*]
    NM --> CD[CanonicalDocumentResult]
    CD --> DB[(OCRResult / ExtractedField /<br/>ValidationResult)]
    DB --> EP[EvidenceSufficiencyPolicy<br/>OCR floor 0.90]
    EP --> EF[EffectiveField]
    EF --> VE[ValidationEngine<br/>deterministic]
```

## 3. Structural properties (the ones that matter)

**What is preserved:** page number, per-line bbox, per-line OCR confidence, `source_kind` (`ocr` vs `embedded_pdf_text`), `coordinate_space` (`pixel` vs `pdf_point`), raw-vs-normalized separation, full evidence list per field.

**What is lost, irreversibly:**

1. **Word/token granularity.** PaddleOCR 3.x returns per-text-line polys; `ocr.py` returns per-line `rec_texts`/`rec_scores`. The code never requests or stores word boxes. Two boxes that the *detector* split apart are permanently indistinguishable from two unrelated boxes.
2. **Table structure.** There is no table model anywhere. A key/value grid is just N rows of text.
3. **Block type.** `PP-StructureV3` layout output (`doc_title` / `table` / `seal` / …) is never requested; the pipeline runs bare `PaddleOCR` text detection + recognition only.
4. **Intra-row provenance.** Once several boxes are concatenated into one line, the mapping from a matched substring back to *which* box it came from is lost (`EvidenceRef` records only the whole line's bbox).

## 4. Confidence semantics as they stand

- `OCRPage.confidence` = **unweighted mean** of line confidences (`providers.py:229`).
- `ExtractedValue.confidence` = **min** over evidence-line confidences (`extraction/base.py:_value`).
- Embedded-PDF-text lines carry `confidence=None`, so a field read from a text layer has `confidence=None`.
- `EvidenceSufficiencyPolicy` only looks at the OCR evidence's min confidence vs `0.90`. It does **not** consider candidate ambiguity, label quality, geometry, or value-shape validity.

## 5. Invariants that are actually enforced today

- `normalize_*` returns `None` rather than guessing (dates, GPA out of range, invalid calendar dates).
- `ExtractedValue.needs_review=True` whenever the field is missing.
- Validation is deterministic and never calls a model.
- `ExtractorRegistry` refuses to extract for `UNKNOWN`.

## 6. Documented/assumed vs. actually supported (real-document conditions)

| Condition | Assumption in code | Actually supported? |
|---|---|---|
| Digitally generated PDF | yes | yes, via `PdfProcessor` |
| Scanned PDF | yes (OCR fallback) | yes, but only 144 DPI and no orientation/deskew |
| Mixed digital+scan PDF | treated as one document | **no** — one gate decides the whole document |
| Mobile photo | no code path | **no** — no perspective correction, no EXIF (preprocessor is dead code) |
| Rotated document | no | **no** — all three Paddle orientation modules are disabled |
| Skewed scan | no | **no** |
| Low-resolution scan | no | **no** (no upscaling) |
| Stamps / seals | no | no — seal text is merged into body rows |
| Tables | no | **no** — no table model |
| Multi-column | no | **no** — global y-band sort, not column detection |
| Multi-page | partly | page number kept; but label/value can pair **across** pages |
| Mixed Korean/English/digits | yes | yes |
| Unusual fonts / font encoding | assumed fine | untested |
| Noisy background | no | no preprocessing at all |
| Photocopies | assumed like scans | untested |
| Handwriting | no | no |

## 7. Where "first match wins" bites

`candidate_after_label` returns the **first** line matching a label, in page/reading order. There is no scoring, no competition between candidates, and no field-type check on the captured value when a separator was present. `_adjacent_value_allowed` is only consulted when there is *no* separator, so `label: anything` is always accepted.
