# OCR Pipeline

PDFs are opened with PyMuPDF. `PdfProcessor.extract_text` returns the embedded text layer plus a deterministic `has_meaningful_text` decision (`is_meaningful_text`, currently a 30-character floor, isolated in `preprocessing/processor.py` so the threshold is independently testable). The text layer is trusted only for text a person can see (`preprocessing/text_layer.py`): invisible text (render mode 3, zero opacity, tiny, off the page), text that changes no pixel when drawn (white on white, covered by an image), unreadable font encodings, pages that are mostly pictures and overlapping different texts are not used. A page whose layer is meaningful and trusted is used directly and OCR is skipped; every other page goes to an `OCRProvider`. When hidden text carries a date or number that the OCR of the page does not show, the document gets the review issue `TEXT_LAYER_MISMATCH` (possible manipulation) and is never 제출 가능. Producer, creator and signature fields are recorded in `classification_meta.text_layer.provenance` for audit only; they never confirm a value. Extracting visible text does not prove the document is authentic.

`OCRProvider` (`document_intelligence/ocr/providers.py`) defines `extract_document(path, mime_type, original_filename)` and `health_check()`. Provider selection is configured with `OCR_PROVIDER=mock|paddle`; PaddleOCR is the only real OCR provider, while mock remains for deterministic tests.

- `PaddleOCRProvider` -- local OCR provider. It lazy-loads PaddleOCR once per provider instance, defaults to CPU (`PADDLE_OCR_DEVICE=cpu`), uses Korean language configuration (`PADDLE_OCR_LANG=korean`), and explicitly selects `korean_PP-OCRv5_mobile_rec` for Korean/English/numeric recognition plus `PP-OCRv5_mobile_det` for detection. Install with `pip install -e ".[paddle]"` in `apps/api`; standard unit tests stub inference and do not download model weights. Model cache location is controlled by PaddleOCR by default or `PADDLE_OCR_CACHE_DIR` when set.
- `MockOCRProvider` -- deterministic double used in automated tests. It never calls a network. Fixture text is selected by a filename hint (`graduation`, `career`, `career_partial`, `business`, `sme`, `sme_expired`, `unknown`, `empty`, plus the sentinel `ocr_failure` which makes it raise, to test failure handling end-to-end) so integration tests can exercise every document type and the OCR-failure path through the real upload -> process API. Both providers return the same `OCRPage`/`OCRLine` model -- nothing downstream depends on either provider's raw shape.

**Normalized representation** (`document_intelligence/ocr/models.py`): `OCRDocumentResult` (provider, pages, assembled_text, page_count) wraps `OCRPage` (page_number, text, lines, confidence, duration_ms, metadata) wraps `OCRLine` (text, confidence, `BoundingBox | None`). PaddleOCR polygons/boxes are parsed into `BoundingBox`; when present, `text_assembly.order_lines` sorts lines by a coarse vertical band then horizontal position before joining them into `page.text`. When no bounding boxes are available, provider order is preserved rather than guessed. Page boundaries are preserved when assembling multi-page `assembled_text` (blank line between pages).

**Failure taxonomy** (`ProcessingErrorCode` in `core/errors.py`, raised as `OCRProviderError(code, message)`): `OCR_TIMEOUT`, `OCR_PROVIDER_ERROR`, `OCR_INVALID_RESPONSE`, `OCR_EMPTY_RESULT`, plus upload-time `UNSUPPORTED_FILE`/`CORRUPT_DOCUMENT` and the generic `PROCESSING_FAILED` fallback. These persist onto `Document.error_code`/`error_message` with a fixed safe message (`PROCESSING_ERROR_MESSAGES`) -- the raw exception text is never persisted or returned by the API. **An OCR failure is not the same as `document_type = UNKNOWN`**: on OCR failure, classification never runs at all (`classification_confidence`/`classification_meta` stay null); `UNKNOWN` means classification ran and evidence was insufficient.

**Upload safety**: file signature (magic bytes) is checked against the claimed extension, independent of the client-supplied `Content-Type` header; the file is then opened for real (`fitz.open` / `PIL.Image.verify`) to reject corrupt/truncated uploads, and PDFs exceeding `MAX_PDF_PAGES` are rejected before processing.

Full OCR text and document bytes are never logged. Structured stage logs (`ocr_started`/`ocr_completed`/etc.) carry only `document_id`, stage, duration, provider name, and page/field counts.

PaddleOCR versioning for the current evaluation target: `paddleocr==3.2.0` and `paddlepaddle==3.1.1` are pinned in the optional `paddle` extra. The backend runtime is constrained to Python `>=3.12,<3.13` so the pinned PaddlePaddle wheel is available. PaddleOCR documentation identifies `korean_PP-OCRv5_mobile_rec` as an ultra-light Korean PP-OCRv5 recognition model supporting Korean, English, and numeric text. CPU mode is mandatory-supported; GPU is configurable by setting `PADDLE_OCR_DEVICE`.

PaddleOCR evaluation is opt-in:

```bash
cd apps/api
.venv/bin/python scripts/eval_run.py --mode paddle --output paddle_latest
```

The evaluation emphasizes downstream classification, extraction, validation, false READY, failures, and latency. It does not print OCR text or field values. If real/anonymized samples are absent, the report must say `REAL OCR EVALUATION: NOT YET AVAILABLE`; synthetic rendered samples are development evidence only.

Technical privacy boundary: PaddleOCR runs locally with no external OCR API request or per-request OCR fee, but requires local compute, dependency/model management, and model cache storage. This is a technical boundary, not a legal/compliance conclusion.

Known limitations: bounding-box reading order is a coarse heuristic (single vertical band size, no multi-column layout detection); no measured accuracy against real scanned Korean documents yet (see `docs/domains/classification.md` for the same caveat on classification).
