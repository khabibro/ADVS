# Current Backend Architecture — traced from source, not from documentation

## The real production path

```
HTTP upload  routes.py:327 upload_document
  └─ LocalStorageService.save_upload                    storage/local.py:90
       ├─ extension allowlist                          (.pdf .png .jpg .jpeg .webp)
       ├─ stream to UUID-named file, sha256, size cap  (20 MB, 1 MB chunks)
       ├─ magic-byte signature check                    _matches_signature:73
       ├─ _validate_decodable:125
       │    ├─ PDF: fitz open, needs_pass, page_count,
       │    │       per-page pixel check @ OCR render DPI, cumulative
       │    │       max_pdf_render_pixels, max_pdf_pages
       │    └─ IMG: Pillow open, DecompressionBombWarning→error, format match,
       │             n_frames==1, verify(), load()
       ├─ Document row + invalidate_submission_verification
       └─ on any exception: rollback + unlink the partial file

HTTP process  routes.py:461 process_document → DocumentProcessingService.process
  │
  ├─ consistency.lock_document_project                  services/consistency.py:41
  │    └─ SQLite: no-op UPDATE on project row (takes the write lock)
  │       Postgres: SELECT … FOR UPDATE
  ├─ UPDATE Document SET status=PREPROCESSING … RETURNING   ← atomic claim
  │    (loser of a race returns 200 with the current document)
  ├─ invalidate_document_project_verification            services/verification.py:70
  │
  ├─ _obtain_source                                            processing.py:185
  │    ├─ detected_mime(path)  ← bytes, not client MIME
  │    ├─ PDF: PdfProcessor.extract_text  (PyMuPDF get_text("dict"))
  │    │        per-line bbox + text, source="direct_pdf_text",
  │    │        coordinate_space="pdf_point", confidence=None
  │    ├─ is_meaningful_text() per page  (≥30 chars AND ≥15 alnum)
  │    │        ├─ usable page  → kept as embedded_pdf_text
  │    │        └─ needs OCR    → PaddleOCR (whole doc is OCR'd; usable pages dropped)
  │    └─ non-PDF: exactly one page, always OCR
  │
  ├─ PaddleOCRProvider.extract_document                     ocr/providers.py:267
  │    └─ worker.run_ocr  → single ThreadPoolExecutor(max_workers=1)
  │         + BoundedSemaphore(1); >120 s → OCR_TIMEOUT; busy → OCR_BUSY
  │       ├─ _input_images: PDF → 288 DPI raster (PyMuPDF); IMG → EXIF-transpose
  │       │               + PNG conversion for non-native suffixes
  │       ├─ _predict → PaddleOCR.predict()
  │       ├─ _normalize_page → _flatten_result / _item_to_line
  │       │      → OCRLine(text, conf, bbox, polygon, det_conf)
  │       │      → assemble_page_text (reading order: y-band then x)
  │       └─ _retry_with_orientation  (fires if mean conf<0.80 OR chars<120)
  │
  ├─ classify(assembled_text, filename)             classification/classifier.py:176
  │    keyword weights TITLE 5.0 / IDENTIFIER 3.0 / SUPPORT 1.0 / GENERIC 0.25
  │    abstain if score < 1.0 OR no signal ≥ 3.0
  │    abstain if (winner − runner) ≤ 1.0
  │    filename deliberately EXCLUDED from the haystack
  │
  ├─ ExtractorRegistry.extract(type, OCRDocumentResult)   extraction/base.py
  │    ├─ _source_observations → order_lines → build_rows (vertical overlap ≥ 0.5·h)
  │    │      page-scoped; each segment keeps its own EvidenceRef
  │    ├─ _row_candidates / _below_row_candidates
  │    │      label patterns tolerate intra-label spaces, ≤5 segment runs,
  │    │      colon / space / right-of-label-with-geometry
  │    ├─ is_valid_value  → shape gate per field kind (fields.py)
  │    ├─ looks_like_boilerplate
  │    ├─ candidate_after_label → prefers explicit-separator class;
  │    │      CONFLICT WITHIN the strongest class ⇒ None (abstains)
  │    └─ per-type helpers: text_field, date_field, issue_date_field,
  │           business_number_field, valid_until_field, gpa_field/scale,
  │           standalone_date_candidate (issuance-block inference)
  │
  ├─ validate_effective_document                        services/document_validation.py:69
  │    ├─ policy_gated_fields → EvidenceSufficiencyPolicy.assess
  │    │     non-SUFFICIENT ⇒ normalized_value := NULL, needs_review := True
  │    ├─ duplicate = same submission + same checksum + different row
  │    └─ ValidationEngine.validate_document
  │         EXPECTED_DOCUMENT_TYPE, DUPLICATE_DOCUMENT, APPLICANT_NAME_MATCH,
  │         COMPANY_NAME_MATCH, always-on DATE_NOT_EXPIRED when valid_until present,
  │         default REQUIRED_FIELD net (suppressed only by a real REQUIRED_FIELD rule),
  │         plus configured document-scope rules
  │
  ├─ _persist_success  (single transaction)            processing.py:311
  │    ├─ lock_document_project; invalidate verification; invalidate reviews
  │    ├─ DELETE OCRResult + ExtractedField + document-scope ValidationResult
  │    │     (submission-scope rows preserved)
  │    ├─ INSERT OCRResult (per page, per-source), ExtractedField (with evidence),
  │    │     ValidationResult
  │    ├─ document.document_type, classification_meta, error_code := NULL
  │    └─ processing_version += 1
  │
  └─ on failure: _fail  →  status=FAILED, error_code from a closed taxonomy,
                  previous generation retained, verification invalidated

HTTP detail  routes.py:375 get_document
  ├─ CanonicalDocumentResult.from_persisted   (never re-runs OCR)
  ├─ EffectiveFieldResolver.resolve per field (machine vs current review vs none)
  ├─ re-derives validation from EFFECTIVE values (not from stored machine issues)
  └─ overall_status = ValidationEngine.overall_status(issues)
        forced REVIEW_REQUIRED unless COMPLETED ∧ not UNKNOWN ∧ not classification needs_review

HTTP review  routes.py:534 → FieldReviewService.submit
  ├─ re-reads the target under the project lock
  ├─ requires expected_processing_version == current  ⇒ else 409 STALE_PROCESSING_VERSION
  ├─ CONFIRMED: no corrected value, machine value must exist
  │  CORRECTED : value required and must normalise for that field
  │  REJECTED / CANNOT_DETERMINE: no corrected value
  ├─ supersede prior current review (is_current=False, superseded_at)
  ├─ store original raw/normalized + evidence fingerprint
  └─ invalidate_submission_verification

HTTP verify  routes.py:476 → SubmissionVerificationService.verify
  ├─ lock_project; refuse a workflow with no requirements
  ├─ _requirements: DATE_NOT_EXPIRED → DATE_COMPARISON on EVALUATION_DATE;
  │                 any document-scope rule that has no submission-scope
  │                 implementation ⇒ RuleConfigurationError (never silently ignored)
  ├─ _documents: effective values + assessment state + review id per field
  ├─ engine.verify
  │    ├─ _resolve_documents: classification-needs-review → UNRESOLVED;
  │    │     not-all-COMPLETED → refuse to pick an older upload;
  │    │     >1 distinct checksum → MULTIPLE_DOCUMENTS_REQUIRE_REVIEW;
  │    │     differing effective signatures → DUPLICATE_RESULTS_CONFLICT;
  │    │     otherwise earliest created_at
  │    ├─ required-field unresolved per requirement
  │    ├─ APPLICANT_NAME_MATCH / COMPANY_NAME_MATCH  (student_name for student types,
  │    │   workplace_name for social insurance)
  │    ├─ auto validity check when valid_until is required and no DATE_COMPARISON exists
  │    └─ FIELD_COMPARISON / DATE_COMPARISON / NUMERIC_COMPARISON / ISSUE_DATE_MAX_AGE
  ├─ _snapshot: sha256 over workflow + requirements + documents + identity + versions
  └─ _persist: project.status = aggregate_status(issues)

HTTP read verification  routes.py:494 → get_latest
  ├─ recompute the snapshot; any mismatch ⇒ invalidate + is_current=False
  └─ READY is downgraded if no submission-scope rows exist
```

## Authoritative vs legacy vs dead

| Path | Status |
|---|---|
| `DocumentProcessingService.process` | **Authoritative.** Single orchestration point; the docstring says so. |
| `ExtractionInput = str \| OCRDocumentResult` | **Legacy but intentional.** Plain-text input is the mock/eval path and is exercised by unit tests; the geometry-free branch is real, not dead. |
| `candidate_after_label(source, labels)` with no `field_name` | **Legacy, unranked.** Used by `date_field`, `gpa_field`, `business_number_field`, `valid_until_field`, `gpa_scale_field`. Bypasses shape validation and the conflict guard. |
| `candidate_matching_line` | Live, used only by `TranscriptExtractor._university_name`. |
| `EvidenceRef.detection_confidence`, `.polygon`, `.transform` | **Populated and persisted, never consumed** by any decision. |
| `OCRLine.orientation_degrees` | **Dead.** Never set by any provider. |
| `EvidenceRef` reconstruction in `results._evidence_from_dict` | **Lossy**: drops `polygon`, `detection_confidence`, `transform`. Used only by `CanonicalDocumentResult.from_persisted`, which feeds `missing_expected_fields` — not the evidence the API returns. |
| `MockOCRProvider` | Deliberate test double, selected by a filename hint. **Not on the production path.** |
| `scripts/recover_processing.py` | Operational tool for stuck PROCESSING rows. Never invoked by the API. |
| `LEGACY_OVERALL_STATUS_MAP` / `normalize_overall_status` | Compatibility shim for the pre-Phase-3 `PASS`/`REVIEW` values. |

## Duplicate / bypass audit

- **No extraction path bypasses `is_valid_value`.** Every candidate goes through it in `rank_candidates`.
- **No path bypasses the evidence gate.** `policy_gated_fields` is applied on both the write path
  (`_calculate_validation`) and the read path (`get_document`).
- **No path bypasses the project lock.** Every mutating endpoint calls `lock_project` or
  `lock_document_project` first.
- **No path fabricates a required-field default.** `required_fields()` raises rather than guessing.
- **One genuine double-computation:** `validate_effective_document` runs twice per document view
  (once at process time, once at every `GET /documents/{id}`). Correctness is fine; it is wasted work
  and two places to keep in sync.

## Invariants enforced only in Python

| Invariant | Enforced in DB? |
|---|---|
| one current review per (document, field) | **Yes** — partial unique index |
| storage key unique | **Yes** — `UNIQUE` |
| duplicate detection | **No** — Python query in `document_validation.py` |
| effective value = machine ∨ current review | **No** — Python only |
| verification matches current inputs | **No** — snapshot hash in `ValidationResult.details` |
| `valid_until` past ⇒ expired | **No** — engine only |
| field name ∈ `EXPECTED_FIELDS[type]` | **No** — Python only (**F-16**) |

Foreign keys exist but **no `ON DELETE` cascade is declared** on any FK; project deletion is handled
by an explicit manual sequence in `delete_project` (delete reviews, delete validation results, null
out audit-log references, delete project, then unlink files). That is correct but hand-maintained —
one missed row type leaks.