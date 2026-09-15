# Documents Domain

Supported MVP document types: `GRADUATION_CERTIFICATE`, `CAREER_CERTIFICATE`, `BUSINESS_REGISTRATION_CERTIFICATE`, `SME_CONFIRMATION_CERTIFICATE`, plus fallback `UNKNOWN`.

## Processing states

`UPLOADED -> PREPROCESSING -> OCR_PROCESSING -> OCR_COMPLETED -> CLASSIFYING -> EXTRACTING -> VALIDATING -> COMPLETED`, or `FAILED` at any point. A failed document always carries `error_code` (one of the `ProcessingErrorCode` values in `docs/domains/ocr.md`) and a fixed safe `error_message` -- never the raw exception text, and it never remains silently stuck in a processing state.

`DocumentProcessingService.process()` (`services/processing.py`) coordinates the stages; it does not implement OCR/classification/extraction/validation itself -- those live in `document_intelligence/*`. Each stage commits its own state transition before the next stage runs, so no long OCR step holds an open multi-stage transaction.

## Reprocessing

Calling `/process` on an already-`COMPLETED` document is a no-op (returns immediately). Reprocessing a document in any other state (e.g. retried after `FAILED`) **replaces** its derived rows -- existing `OCRResult`, `ExtractedField`, and `ValidationResult` rows for that document are deleted before the new ones are inserted, so retries never accumulate duplicates.

## API surface

`GET /documents/{id}` returns processing status, detected type, `classification_confidence` + `classification_meta` (heuristic score/evidence/alternatives -- never a calibrated probability), extracted fields (with `extraction_method`/`source_text` provenance), validation results, and a computed `overall_status` (READY/REVIEW_REQUIRED/NEEDS_CORRECTION). `READY` means only that the configured pre-check found no clear problem; it is not official approval. The API never exposes the internal storage path or raw provider payloads.

Upload validation, storage-key generation (UUID, not the original filename), checksums, and safe filename sanitization are owned by `services/storage/local.py`.

## Known limitations

- No async worker/queue -- `/process` runs synchronously in the request.
- No page-level bounding-box provenance on extracted fields (only on raw OCR lines).
- No cross-document validation (e.g. matching a business number across two documents in the same submission) beyond what an admin-configured `BUSINESS_REGISTRATION_NUMBER_MATCH` rule with an explicit expected value can express.
