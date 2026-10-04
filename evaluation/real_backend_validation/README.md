# Real-Document Backend Validation & System Readiness Audit

**Date:** 2026-09-30
**Auditor:** independent audit pass (no prior report trusted)
**Repository state:** branch `main`, HEAD `721cc9d`, **45 modified tracked files, 13 untracked files already present and preserved**
**Method:** INSPECT → BASELINE → REAL-DOCUMENT TEST → TRACE FAILURES → AUDIT → RESEARCH → RECOMMEND

> **No commit, no push, no reset, no rebase, no force checkout, no worktree clean was performed.**
> Original Desktop documents were read only. Nothing was renamed, moved, deleted or uploaded externally.

---

## 1. What was actually run

| | |
|---|---|
| Live stack | **LOCAL BACKEND + LIVE DOCKER IMAGE BUILD.** `docker compose build api` completed successfully (`Image advs-api Built`, exit 0). Functional validation ran on the repository's supported local development path with **real uvicorn, real HTTP over a socket, real PaddleOCR 3.2.0 on CPU**, because that path uses the already-cached Korean PP-OCRv5 models. |
| API under test | `uvicorn app.main:app` on `127.0.0.1:8077`, Alembic migrations 0001→0006 applied, `scripts/seed.py` seeded the two shipped workflows. |
| Documents | 7 unique files found on `~/Desktop`, 7 unique SHA-256, **0 duplicates**. |
| Endpoints exercised | upload, process, processing-status, document detail, verify, verification, review-items, reviews, field review, project create/list/get, workflow list/get, delete. |
| Baseline rule | **The backend was NOT modified.** No production file was edited at any point. Two crashes of my own harness were fixed; one accidental file (`apps/api/_probe2.py`) was created and immediately removed — `git status` was re-verified byte-for-byte identical to the start. |

---

## 2. Dataset — the single most important dataset finding

**All three PDFs on the Desktop have ZERO text-layer characters and exactly one embedded image each.**
Every one of the 7 realistic documents is a **scan**. The `direct_pdf_text` path, the mixed-PDF path and the whole "evidence-sufficient without human review" path are **completely unexercised by realistic data**.

| ID | Type | Format | Pages | Notes |
|---|---|---|---|---|
| REAL-001 | — | PDF | 1 | **SUSPECT SYNTHETIC.** Named as a 4-day social-insurance certificate; content is a contribution-payment certificate issued by a Buddhist temple, carrying the canonical dummy business number and a literal "sample company" name. Produced by the previous round's generator. |
| REAL-002 | 사업자등록증 | PNG | 1 | 595×842 px = **72 DPI A4**. Lowest-quality source. |
| REAL-003 | 성적증명서 | JPEG | 1 | 743×1020. 3-column course table, ~90 rows. Header names one university, seal names another. |
| REAL-004 | 성적증명서 | PDF | 1 | 1240×1754 render. Clean, high quality, paired with REAL-007. |
| REAL-005 | 재학증명서 | WEBP | 1 | 1200×1854. Paired school/university naming conflict. |
| REAL-006 | 중소기업확인서 | JPG | 1 | **400×566 px — the smallest source in the set.** Validity expired 2022-03-31. |
| REAL-007 | 재학증명서 | PDF | 1 | 1240×1754 render. Clean. **Prints no student-id field at all.** |

Types represented: 4 distinct. Types **not** represented: 국세 납세증명서, 졸업증명서, 경력증명서, UNKNOWN.
Layout families: Certpia web-issued certificate (2), ruled official form (1), three-column course table (2), NTS business-registration form (1), SME confirmation (1).

**Ground truth** was established by the auditor independently, by visual inspection of every rendered original page plus targeted high-zoom crops of every disputed field. Ground-truth **values were kept in a directory outside the repository**. Fields that humans cannot adjudicate at the available resolution are recorded as `AMBIGUOUS`, and the system is not penalised for refusing them.

---

## 3. Baseline results — stated as counts, never as "works"

### Classification
**6 / 6 processable documents classified correctly. 0 wrong. 0 abstentions.**
(1 of 7 was rejected at upload — see F-01.) Classification is the strongest part of the system.

### Fields (36 evaluated verdicts)

| Verdict | Count |
|---|---|
| CORRECT | 9 |
| **INCORRECT_NON_NULL** | **3** |
| UNRESOLVED | 14 |
| CORRECT_ABSTENTION | 1 |
| AMBIGUOUS_GROUND_TRUTH | 7 |
| NOT_EVALUATED | 2 |
| **Unlabelled populated (hallucinated)** | **0** |

- Supported-field **precision 0.75** (9 correct / 12 populated)
- Supported-field **recall 0.35** (9 correct / 26 assertable)
- **False READY: 0 observed.** No project reached READY without every field being human-resolved.
- **Hallucinated fields: 0.** This is a genuinely good result and must not be buried.

### The 3 wrong non-null values — every one listed

| Sample | Field | Confidence | Used by a rule? | Earliest failing stage |
|---|---|---|---|---|
| REAL-007 | `student_name` | **0.9955** | yes — `APPLICANT_NAME_MATCH` | OCR_RECOGNITION (1 Hangul vowel substitution) |
| REAL-006 | `company_name` | 0.9660 | yes — required + `FIELD_COMPARISON` | OCR_RECOGNITION (2 syllable substitutions) |
| REAL-002 | `business_address` | 0.9119 | no (today) | OCR_RECOGNITION (3 substitutions) |

**The most confident machine value in the entire dataset (0.9955) is wrong.** This is the empirical
answer to "can the system produce confident wrong values?" — **yes — and OCR confidence does not
detect it.**

### What kept them safe
`EvidenceSufficiencyPolicy` marks **every** OCR-sourced value `REVIEW_REQUIRED` with reason
`OCR_REQUIRES_CONFIRMATION`. A populated-but-ungated OCR value therefore never reaches a deterministic
rule. Confirmed on all 6 documents: `machine_normalized_value` present, `effective_normalized_value`
absent, `effective_source = UNAVAILABLE`.

> **Consequence that must be stated plainly: because all 7 realistic documents are scans, ADVS can
> only reach READY on this dataset after a human resolves every extracted field.** I verified READY
> is reachable that way (E3), and that an expired document still cannot reach it (E4).

---

## 4. Findings that are bugs, not limitations

All reproduced minimally; all fixable without new infrastructure.

| ID | Severity | Finding |
|---|---|---|
| **F-14** | **CRITICAL** | `ocr_timeout_seconds=120` applies to the whole document while a dense A4 page costs ~25.4 s. Measured: 1 page 25.7 s OK, 3 pages 76.3 s OK, **6 pages FAILS at 120.0 s**. `max_pdf_pages=30` is unreachable. A timed-out job also keeps the single OCR worker busy, so the next request fails with `OCR_BUSY` too. **Realistic multi-page submission packs cannot be processed at all.** |
| **F-03** | HIGH | `issue_date` is null on 3 of 6 documents because the guard before the semantic fallback substring-matches the **entire page**, and the standard Certipia footer literally contains the issue-date label plus a suffix. Reproduced: correct date with the footer removed, null with it present. This blocks the student workflow's only configured rule. |
| **F-13** | HIGH | Two documents processed concurrently → the loser is **permanently FAILED** (`OCR_BUSY`). A transient capacity condition becomes a terminal document state. |
| **F-16** | HIGH | 10 field/document combinations are **structurally unresolvable by a human** because `EXPECTED_FIELDS` (which gates review) omits fields the extractors actually produce. Also makes document-scope status permanently `REVIEW_REQUIRED` for any OCR document. |
| **F-04** | MEDIUM | `SMEConfirmationExtractor` passes its representative labels in the wrong order, shadowing the compound label. Verified: wrong order → `None`; right order → correct value. The sibling extractor already fixed this exact class. |
| **F-01** | HIGH | A legitimate 1117×1408 pt government form is rejected at upload by **0.65 %** because the storage layer projects the OCR render DPI and compares the derived raster against the *input-image* pixel budget. |
| **F-15** | MEDIUM | **The deployed server emits no per-stage audit records.** PaddleOCR model construction sets the **root** logger to WARNING; ADVS's JSON handler is on the root logger, so every record after the first OCR call is silently dropped. Verified: a successful process emitted 1 record instead of 6, and the per-page source-provenance record is never written. |
| **F-17** | MEDIUM | Two different comparison semantics for the same job: document scope strips whitespace/punctuation, submission `FIELD_COMPARISON` requires exact equality. Two correct company names differing by one space produce a blocking `INFORMATION_MISMATCH`. Reproduced through the engine. |
| **F-08/F-09** | MEDIUM | `build_rows` merges a bare issue date with stamp/table fragments (vertical overlap only, no gap or height test), and the issuance-anchor lookahead is a fixed 3 rows, which a dense transcript defeats. |
| **F-18** | LOW | The "conditional" orientation retry is effectively always-on for any page under 120 characters, doubling OCR cost and feeding the F-14 cascade. |

---

## 5. Where the failures actually originate

| Stage | Failures | Verdict |
|---|---|---|
| FILE_VALIDATION | F-01 | **Root cause is a layering violation**, not a limit. |
| ORIENTATION | F-18 | Heuristic debt. |
| LAYOUT_LOSS / TABLE_STRUCTURE | F-05, F-07, F-08 | **The architectural gap.** The row model cannot represent a table; the cleanest scan yields zero fields. |
| OCR_RECOGNITION | F-06, F-10, F-11, F-12 | **Dominant cause of wrong values.** Published Korean line-level accuracy of the chosen recogniser is **88.0 %**; per-character accuracy is materially lower. |
| OCR_SEGMENTATION | F-05 | Adjacent table-column labels cross-merged. |
| FIELD_CANDIDATE_GENERATION | F-03 | The single highest-value cheap fix in the whole system. |
| FIELD_CANDIDATE_PAIRING | F-04 | Cheap fix. |
| NORMALIZATION | — | **Probed and sound.** 56/57 pure-function probes pass; the one deviation was my own incorrect expectation of a documented behaviour. |
| EVIDENCE | — | **Truthful.** Every populated field's evidence points at the row the value came from, with page, bbox, source kind and coordinate space. It cannot reveal a recognition error, and no mechanism claims it can. |
| CONFIDENCE | — | **Honest in intent, misleading in presentation.** The policy document says so explicitly and the code follows it, but the UI-facing 0.99 is still the highest number on a wrong field. |
| HUMAN_REVIEW | F-16 | Correct in principle; blocked in practice by a vocabulary mismatch. |
| VERIFICATION | F-17 | Deterministic and safe; inconsistent comparison semantics. |
| CONCURRENCY | F-13, F-14 | Not safe under normal concurrent use. |
| API | F-15 | Functionally correct; not diagnosable. |
| EVALUATION | F-02 | A prior evaluation file was synthetic while presented as realistic. |

---

## 6. Root causes, ranked

1. **No structure layer.** ADVS has excellent recognition and no understanding of tables, cells or
   regions. Every table-heavy document (both transcripts, the ruled form) collapses. This single
   omission explains F-05, F-07, F-08 and much of the review burden.
2. **A recogniser at 88 % line-level Korean accuracy feeding a system that shows confidence to 3 dp.**
   The gate around it is correct; the numbers presented above it are not.
3. **Per-document resource budgets on a single-worker synchronous OCR.** F-13, F-14, F-18.
4. **Heuristics tuned on assumptions rather than measurements** — label-list ordering, fixed row
   lookaheads, page-wide substring guards.
5. **Two overlapping field vocabularies** (`EXPECTED_FIELDS` vs what extractors produce). F-16, F-17.
6. **Third-party libraries mutating global process state.** F-15.
7. **Dataset provenance not tracked.** F-02.

---

## 7. Quality gates — verbatim results

| Gate | Result |
|---|---|
| `git diff --check` | **PASS** |
| `ruff check .` | **PASS** |
| `ruff format --check .` | **CODE FAILURE (cosmetic)** — 3 files would be reformatted: `extraction/base.py`, `services/verification.py`, `tests/test_astra_ingestion.py`. Not run by `make check`. |
| `mypy --explicit-package-bases app` | **PASS** — no issues in 57 source files |
| `pytest` | **CODE FAILURE — 2 failed, 338 passed** |
| `pnpm lint` | **PASS** |
| `pnpm typecheck` | **PASS** |
| `pnpm test` | **PASS** — 94 web tests; admin and contracts have no tests |
| `pnpm build` | **PASS** |
| `make migration-check` | **PASS** — head `0006_field_reviews` |
| `make docker-check` | **PASS** |
| `pnpm env:validate` | **PASS** |
| `pnpm security:audit` | **PASS** |
| `docker compose build api` | **PASS** |

### The two pytest failures

1. **`test_primary_department_beats_secondary_double_major`** — a regression test written *for exactly
   the REAL-007 department case*, left **red**. Its docstring states the intent: prefer the primary
   major over the double major. It fails: the extractor returns `None`. A previous developer documented
   a real-document defect as a test and did not make it pass. This independently corroborates my
   finding on REAL-007.
2. **`test_document_api_serializes_enum_and_canonical_display_name`** — `DocumentRead` gained a required
   `processing_version` field and the test was not updated. Schema drift.

**The repository does not currently pass its own quality gate.** `make check` and `make test` fail.

---

## 8. Test-suite quality

340 collected. Composition:

| Category | Present? |
|---|---|
| Unit (pure functions, normalisers, classifier, layout) | **Strong** — 53 + 36 + 18 + 5 tests |
| DB integration (migrations, documents, reviews, submission verification) | **Strong** — 6 migration tests + 17 consistency + 11 document-state |
| HTTP integration (`TestClient`) | **Present** — workflows, submission verification API, review flows |
| Mocked OCR | **Yes, and only this** — 59 monkeypatch/stub sites |
| **Real PaddleOCR engine in CI** | **ABSENT.** No test instantiates `PaddleOCR(`. |
| **Real pipeline on a real document file** | **ABSENT.** All "real document" tests hand-build `OCRPage`/`OCRLine` fixtures. |
| Realistic-document regression coverage | Present but **red** (see above) and expressed as synthetic fixtures |
| Concurrency | **ABSENT** |
| Security | Present at the API boundary (9 probes, all pass) |

**False-confidence areas:** the OCR adapter's actual result parsing (`_flatten_result`, `_item_to_line`,
`_bbox`, `_polygon`) has never been exercised against a real PaddleOCR 3.2.0 response in CI;
`make check` explicitly excludes OCR evaluation; and "real document regression" tests assert beliefs
about documents rather than OCR behaviour.

---

## 9. Performance (this machine: Apple silicon, 11 CPU, PaddleOCR CPU)

| Metric | Value |
|---|---|
| OCR per document, 1-page realistic | median **6.7 s**, min 4.4 s, max 39.3 s (n=16 runs) |
| End-to-end `/process` HTTP, realistic | 4.4 s – 26.6 s |
| Synthetic dense A4 page | **25.4 s** per page |
| Multi-page ceiling | **~4 pages** before `OCR_TIMEOUT` |
| OCR concurrency | **1 document per process** |
| Same input, repeat run | 26.2 s vs 39.3 s (**1.5× variance**) |

Little sample size; these are single-run observations on one machine and must not be generalised.

---

## 10. Privacy and security

- No realistic document, OCR text, name, student id, business number or certificate number was sent to
  any external service. Everything ran locally. Ground-truth values stayed outside the repository.
- Every artifact written under `evaluation/real_backend_validation/` passed an automated PII scrub
  assertion (business-number, resident-number, 8-digit student/certificate and internet-issuance
  number patterns) before being written.
- Logs inspected: the application's own structured records contain **no OCR text and no PII** — only
  document IDs, durations, counts and error codes. That is by design and it is correct. (It is also
  why the audit trail is sparse: see F-15.)
- Upload security: 7/7 hostile probes rejected (PNG renamed to `.pdf`, truncated PDF, disallowed
  extension, path-traversal filename, empty file, 20000×20000 PNG, >20 MB). Signature check, decoder
  validation, multi-frame rejection and `img.load()` are all genuinely implemented.
- Unhandled-exception handler returns `str(exc)` in non-production. Acceptable for development, must
  be pinned before any shared deployment.

---

## 11. What is finished and what is not

| Component | Status | Evidence |
|---|---|---|
| Upload validation & path safety | **READY** | 7/7 hostile probes rejected |
| Storage isolation & cleanup | **READY** | UUID keys, traversal-checked, delete cleans up |
| PDF routing (digital / scanned / mixed) | **READY** | Mixed PDF verified end-to-end with correct per-page `source_kind` |
| Evidence & provenance model | **READY** | Truthful page/bbox/source-kind/coord-space on every populated field |
| Normalisation | **READY** | 56/57 probes pass; dates, ranges, business numbers, GPA all conservative |
| Document classification | **FUNCTIONAL_BUT_LIMITED** | 6/6 correct here; keyword-heuristic, never abstained once |
| OCR adapter | **FUNCTIONAL_BUT_LIMITED** | Works on real Korean scans; never covered by CI |
| Human review (CONFIRMED/CORRECTED/REJECTED/CANNOT_DETERMINE) | **FUNCTIONAL_BUT_LIMITED** | All four decisions verified; 10 field combos unreachable (F-16) |
| Submission verification engine | **READY** | Deterministic, null-safe, version-guarded, snapshot-invalidated |
| Effective-field resolver | **READY** | Correctly separates machine vs effective values |
| Status aggregation & READY semantics | **READY** | 0 false READY observed across all scenarios |
| Duplicate handling | **FUNCTIONAL_BUT_LIMITED** | Cross-document duplicates reviewed; identical files silently deduped at submission scope (flagged at document scope) |
| Concurrency safety | **UNSAFE** | F-13, F-14 |
| Layout / table understanding | **NOT_IMPLEMENTED** | No layout model, no cell grid, no reading-order model |
| Deskew / perspective / unwarping | **NOT_IMPLEMENTED** | Deliberately disabled; acceptable |
| Evaluation tooling | **FUNCTIONAL_BUT_LIMITED** | Two scorers with different semantics; the older one hides hallucinated fields and conflates abstention with correctness |
| Storage cleanup of failed uploads | **READY** | Verified in code and by hostile probes |

---

## 12. Answers to the 45 verdict questions (condensed)

| # | Question | Answer |
|---|---|---|
| 1 | Processes the realistic Desktop documents? | 6 of 7 reached COMPLETED; 1 was rejected at upload. |
| 2 | How many unique documents tested? | **7** (7 unique hashes, 0 duplicates). |
| 3 | Which types work reliably? | Classification: SME, business registration, transcript, enrollment (4/4). Extraction: **none reliably**; SME recovered the most fields (6 of 7). |
| 4 | Which types are weak? | All of them for extraction. Transcripts weakest structurally (0 of 6 and 3 of 6). |
| 5 | Which types not tested? | 국세 납세증명서, 졸업증명서, 경력증명서, UNKNOWN-from-real-input. |
| 6 | Classification accuracy | **6/6 = 100 %** on this set. |
| 7 | Fields correct | **9** |
| 8 | Fields wrong non-null | **3** |
| 9 | Fields unresolved | **14** |
| 10 | Correct abstentions | **1** (+7 ambiguous, not penalised) |
| 11 | OCR recognition the main bottleneck? | **Yes** — the source of all 3 wrong values and of F-06. |
| 12 | OCR detection/segmentation a bottleneck? | **Yes** — cross-merged table labels (F-05). |
| 13 | Layout a bottleneck? | **Yes, and the biggest structural one** — the row model cannot represent tables. |
| 14 | Extraction logic a bottleneck? | **Partly** — F-03 and F-04 are pure logic bugs worth fixing immediately. |
| 15 | Is normalisation safe? | **Yes.** Verified over 57 probes. |
| 16 | Is evidence truthful? | **Yes.** It points at the real source row; it cannot reveal a recognition error, and does not claim to. |
| 17 | Is confidence meaningful? | As a *policy input* yes; as a *number shown to a reviewer* **no** — the 0.9955 value is wrong. |
| 18 | Does human review work? | **Yes**, correctly, for every field that is reachable. |
| 19 | Does reprocessing preserve safety? | **Yes** — version bump, stale reviews invalidated and retained, previous good state preserved on failure. |
| 20 | Is verification deterministic? | **Yes.** |
| 21 | Is verification using current evidence? | **Yes** — input-snapshot hash + version, verified by invalidation on every mutation. |
| 22 | Can stale READY occur? | Not observed. Snapshot mismatch forces `is_current=False`. |
| 23 | Can False READY occur? | **Not observed in 8 scenarios.** Requires human resolution of every field first. |
| 24 | Are missing values handled safely? | **Yes** — null is never treated as pass, and never as expired/mismatch. |
| 25 | Can confident wrong values occur? | **YES — 3 times, one at confidence 0.9955.** Contained by the OCR confirmation gate, not by confidence. |
| 26 | Are duplicates safe? | **Yes** for differing copies (reviewed). Identical files are silently deduped at submission scope — worth surfacing. |
| 27 | Is UNKNOWN safe? | **Yes** — no fabricated fields, not READY, forces review. |
| 28 | Are tables handled adequately? | **No.** This is the clearest capability gap. |
| 29 | Are mixed PDFs handled? | **Yes**, and verified with correct per-page provenance. |
| 30 | Are images handled? | **Yes** — PNG/JPEG/WEBP all verified end-to-end. |
| 31 | Is file validation secure enough? | **Yes.** |
| 32 | Is OCR scalable enough for the capstone? | **No** — one worker, ~4-page ceiling, concurrent submissions fail. |
| 33 | Privacy issues? | **None found.** Local-only; logs contain no PII. |
| 34 | Data-integrity issues? | No corruption. One dataset-provenance problem (F-02). |
| 35 | Is the architecture fundamentally sound? | **Yes, with one missing layer.** The dependency direction and the evidence→policy→human→rules spine are right. The absence of layout/table structure is the gap. |
| 36 | Components to keep? | Evidence model, normalisation, classifier, submission engine, effective resolver, evidence policy, storage isolation, transaction locking. |
| 37 | Need improvement? | Row grouping, candidate label matching, review vocabulary, comparison semantics, document validation scoping, resource budgets, logging. |
| 38 | Should be replaced? | The OCR *resource model* (synchronous single worker with per-document timeout). |
| 39 | Is a redesign justified? | **No.** A structural OCR layer is additive; the deterministic spine must not be rewritten. |
| 40 | Highest-priority problem? | **The missing layout/table-structure layer**, made survivable first by fixing the per-document OCR timeout. |
| 41 | Next five actions? | F-14 → F-03 → F-04 → F-16 → F-15. |
| 42 | Strong enough for a capstone demo? | **With conditions** — see below. |
| 43 | Must fix before demo? | F-14, F-03, F-15, the 2 red tests, and a demo dataset of ≥2 pages per document. |
| 44 | Can safely wait? | Orientation, duplicate surfacing, address validation, deskew. |
| 45 | Should Phase 9 begin? | **YES_WITH_CONDITIONS** — see §13. |

---

## 13. Phase-9 readiness

### **YES_WITH_CONDITIONS**

Phase 9 (configurable rules / admin) is *conceptually* the right next step: the verification engine is
already rule-driven, DB-backed, and refuses unsafe configurations by design
(`RuleConfigurationError` for anything it cannot evaluate safely). Phase 9 mostly adds authoring
surface over machinery that exists.

But it must not start while these are true, because Phase 9's value is entirely a function of whether
the *inputs* are trustworthy:

**Blocking conditions**
1. **F-14** — the timeout/scalability defect must be fixed, or Phase 9's rule work will be judged on
   documents that cannot be processed at all.
2. **F-03 + F-04** — cheap, certain correctness bugs that make whole field classes null on real documents.
3. **The 2 red tests** — `make test` must be green before any rule engine change.
4. **F-16** — Phase 9 lets an admin *configure required fields*. Today an admin cannot even review
   10 of the field/document combinations the system produces. Shipping configurable rules on top of
   an unreconciled field vocabulary would formalise the inconsistency.

**Strongly recommended but not blocking**
5. **F-15** — without the per-stage audit trail, Phase 9 rule evaluation cannot be diagnosed in production.
6. A realistic dataset with ≥3 multi-page documents and ≥2 real UNKNOWN inputs.

**Do NOT do before Phase 9**
- Do not add an LLM/VLM extraction path. The measured failure mode is missing *structure* and an
  88 %-accurate recogniser; a VLM would remove the very thing (deterministic evidence) that makes ADVS
  defensible.
- Do not widen `MIN_SCORE_FOR_CONFIDENT_TYPE` or relax any evidence gate to "improve" metrics.
- Do not lower the confirmation floor.

---

## 14. Capstone MVP readiness

**Not yet demonstrable on a realistic multi-document pack. Demonstrable today on a single-page,
human-reviewed walkthrough.**

A capstone demonstration is defensible **if and only if** F-14, F-03, F-15 and the red tests are
fixed first, and the demo dataset contains no multi-page document and no table-heavy transcript. The
safety story is genuinely strong and demonstrable: 0 false READY, 0 hallucinated fields, correct
UNKNOWN handling, correct null semantics, deterministic verification with snapshot invalidation. The
*accuracy* story is not, and should not be presented as one.

---

## 15. Prioritised improvements (not implemented — see the fix plan in `improvement_options.md`)

**P0 — correctness & safety**
- F-14 per-document OCR timeout / single-worker resource model
- F-03 page-wide substring guard on the issue-date fallback
- F-04 label ordering in the SME extractor (+ sweep 3 shadowed label lists)
- F-15 root-logger capture by PaddleOCR
- Fix the 2 red tests; add `ruff format --check` to the gate

**P1 — realistic extraction reliability**
- F-16 reconcile `EXPECTED_FIELDS` with extractor output
- F-01 decouple the pixel budget from the OCR render DPI
- F-17 unify comparison semantics
- F-08/F-09 bound row merging; make the issuance anchor distance-based
- Corpus of ≥30 real documents with independent ground truth and per-class provenance

**P2 — architecture**
- **Add a layout/table-structure stage (PP-StructureV3 + SLANeXt_wired) behind the existing OCR adapter.**
  Same recogniser, one extra layer, and it unlocks transcripts and the ruled form.
- Queue-based OCR job handling; keep HTTP short
- Per-field corroboration signals for reviewer guidance
- Fix `issue_date_field`/`EXTRACTOR_VERSION` bookkeeping and consolidate the two evaluation scorers

**P3 — future**
- CLOVA OCR specialised model for 사업자등록증 (Korean data residency, purpose-built for this exact document)
- Seal recognition (`use_seal_recognition`) to stop stamp artefacts polluting rows
- Optional VLM path, strictly as a *proposal generator* feeding the existing evidence gate — never as an authority

---

## 16. Artifacts in this directory

All sanitized; automated PII assertions passed before writing.

| File | Contents |
|---|---|
| `dataset_inventory.json` | Hashes, formats, page counts, dimensions, no text |
| `baseline.json` | Per-document baseline: type, statuses, field presence/assessment, verification issues. No values. |
| `per_field.json` | 36 field verdicts with expected state and adjudication notes |
| `confusion_matrix.json` | Classification confusion + aggregates |
| `failure_ledger.json` | 18 failures with root cause and suggested improvement |
| `behaviour_checks.json` | 55 behavioural checks over review/reprocess/duplicates/UNKNOWN/READY/null-safety/API/security |
| `concurrency_checks.json` | Concurrency and multi-page capacity probes |
| `mixed_pdf_checks.json` | Mixed-source routing and per-field provenance |
| `normalisation_probes.json` | 57 pure-function probes (literals omitted) |
| `system_state.md` | Repository and environment state |
| `architecture_current.md` | The real production path, traced |
| `architecture_analysis.md` | Strengths, weaknesses, heuristic debt |
| `research_review.md` | Current OCR/layout/semantic/cloud options |
| `improvement_options.md` | P0–P3 fix plan with alternatives and regression risk |
| `readiness_matrix.md` | Component × status |