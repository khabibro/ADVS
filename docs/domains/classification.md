# Classification Domain

`DocumentClassifier` (`document_intelligence/classification/classifier.py`, `classifier_version = "heuristic-v2"`) is a deterministic, explainable keyword-evidence classifier. No ML/LLM.

Each document type has a fixed signal list, each signal weighted by how strong evidence it is:

- **TITLE** (5.0) -- the document's own printed title (e.g. `사업자등록증`)
- **IDENTIFIER** (3.0) -- characteristic of the type but can appear on others (e.g. `사업자등록번호` also appears on an SME confirmation certificate)
- **SUPPORT** (1.0) -- commonly present but not distinctive on its own
- **GENERIC** (0.25) -- a bare word that alone proves very little

A type is only ever predicted (instead of `UNKNOWN`) once its summed weighted score clears `MIN_SCORE_FOR_CONFIDENT_TYPE` (1.0) -- generic words alone can never cross that floor. `confidence_score` is `winner / (winner + runner_up)`, capped at 0.99: **this is a heuristic evidence ratio, not a calibrated probability.**

Matching collapses whitespace on both the signal text and the haystack before comparing, so an OCR line-wrap inside a label (e.g. `사업자\n등록증`) still matches -- this is whitespace-only tolerance, not fuzzy/edit-distance matching, so it cannot turn unrelated text into a false match.

**UNKNOWN**: returned whenever the winning score is below the confident-type floor. Means "we read the document but could not reliably tell what it is" -- distinct from an OCR failure (see `docs/domains/ocr.md`), which never reaches classification at all.

**Ambiguity / review flag**: `needs_review = true` whenever the top two candidates' scores are within `AMBIGUITY_MARGIN` (1.0) of each other, even though a winner is still returned. The system never silently picks one of two similarly-supported types with false confidence.

`ClassificationResult` carries `predicted_type`, `confidence_score`, `score` (raw heuristic sum), `evidence` (matched signal strings for the winner), `alternatives` (every type with a positive score, most cases 0-3 entries), `needs_review`, `classifier_version`. This is persisted on `Document.classification_meta` (JSON) alongside `classification_confidence` -- evidence is our own fixed label vocabulary, never raw OCR text, so it is safe to store and log.

Known limitations: signal weights are hand-assigned, not learned; measured against a synthetic benchmark only, not real-world documents (see `evaluation/README.md`); business-registration-number-bearing types (`BUSINESS_REGISTRATION_CERTIFICATE`, `SME_CONFIRMATION_CERTIFICATE`) share an IDENTIFIER/SUPPORT signal, which is the main source of intended ambiguity between those two types. As of the P1.5 baseline, a confident prediction requires at least one IDENTIFIER-or-TITLE-weight signal to have matched -- SUPPORT/GENERIC evidence alone, however much of it accumulates, now falls back to UNKNOWN (see `evaluation/reports/baseline_2026-09-09.md` for the finding that motivated this).
