# Readiness Matrix

Status key: **READY** · **FUNCTIONAL_BUT-LIMITED** · **PARTIAL** · **UNSAFE** · **NOT-IMPLEMENTED** · **NOT-EVALUATED**

"Not ready" merely because code exists is never sufficient. Every row carries measured evidence.

## Feature matrix

| Feature | Impl? | In prod path? | Tested? | Tested w/ realistic docs? | Safe? | Notes |
|---|---|---|---|---|---|---|
| Upload | ✅ | ✅ | ✅ | ✅ | ✅ | |
| File validation (signature, decoder, size, path) | ✅ | ✅ | ✅ 9 hostile probes | ✅ | ✅ | **7/7 rejected** |
| PDF support | ✅ | ✅ | ✅ | ✅ | ✅ | |
| PNG / JPEG / WEBP support | ✅ | ✅ | ✅ | ✅ all three | ✅ | WEBP needs conversion; verified |
| Digital PDF text extraction | ✅ | ✅ | ✅ | ❌ **no realistic sample** | ✅ | verified with a synthetic Korean-text PDF |
| Scanned PDF handling | ✅ | ✅ | ✅ | ✅ | ✅ | **6/6 realistic** |
| Mixed PDF handling | ✅ | ✅ | ✅ | ❌ synthetic only | ✅ | **verified with per-page `source_kind`** |
| Multi-page documents | ⚠️ | ✅ | ✅ | ❌ | ❌ **UNSAFE** | **6 dense pages fail OCR_TIMEOUT** (F-14) |
| Rasterization | ✅ | ✅ | ✅ | ✅ | ✅ | 288 DPI |
| Image preprocessing (EXIF, codec) | ✅ | ✅ | ✅ | ✅ | ✅ | correctly scoped, nothing destructive |
| Rotation / orientation | ⚠️ | ✅ | ✅ | ❌ | ⚠️ | retry is effectively always-on for sparse pages (F-18) |
| Deskew / perspective correction | ❌ | — | — | — | ✅ | **deliberately** absent; correctly so |
| OCR recognition | ✅ | ✅ | ⚠️ mocked only | ✅ | ⚠️ | **88 % line-level model; source of all 3 wrong values** |
| OCR geometry (polygon, det-conf, transform) | ✅ | ✅ | ⚠️ | ✅ | ✅ | **persisted but never consumed** |
| Reading order | ⚠️ | ✅ | ✅ | ✅ | ✅ | y-band + x only; sufficient for labels, not for tables |
| Layout reconstruction (regions, cells) | ❌ | — | — | — | ✅ | **the defining gap** |
| Table understanding | ❌ | — | — | ❌ | ✅ | **GPA unreachable on both transcripts** |
| Document classification | ✅ | ✅ | ✅ 18 | ✅ **6/6** | ✅ | never abstained on this set |
| UNKNOWN classification | ✅ | ✅ | ✅ | ✅ synthetic | ✅ | no fabricated fields — verified |
| Classification abstention | ✅ | ✅ | ✅ | ⚠️ not triggered by real data | ✅ | mechanism verified, threshold untested on real negatives |
| Field extraction | ⚠️ | ✅ | ✅ 89 | ✅ **9 CORRECT / 3 WRONG / 14 UNRESOLVED** | ⚠️ | |
| Candidate generation | ⚠️ | ✅ | ✅ | ✅ | ⚠️ | F-03, F-04 |
| Candidate ranking | ✅ | ✅ | ✅ | ✅ | ✅ | **conflict-abstains guard prevented a wrong GPA** |
| Shape validation | ✅ | ✅ | ✅ | ✅ | ⚠️ | `FREE_TEXT` for `business_address` is a no-op (F-12) |
| Date parsing | ✅ | ✅ | ✅ 15 | ⚠️ F-03 blocks it | ✅ | **conservative and correct** |
| Date ranges | ✅ | ✅ | ✅ 11 | ✅ | ✅ | all 4 dash variants + Korean particles |
| Business registration number | ✅ | ✅ | ✅ | ✅ 2/2 correct | ✅ | |
| Company name | ⚠️ | ✅ | ✅ | ⚠️ 1 wrong, 2 unresolved | ⚠️ | F-06, F-10 |
| University name | ⚠️ | ✅ | ✅ | ❌ 0 correct (all ambiguous GT) | ✅ | correctly abstained |
| Department | ❌ | ✅ | ✅ | ❌ all unresolved/ambiguous | ✅ | abstains safely (F-04 red test) |
| Student name | ⚠️ | ✅ | ✅ | ⚠️ 1 correct, 1 wrong, 1 ambiguous | ⚠️ | F-11 at confidence 0.9955 |
| Student id | ✅ | ✅ | ✅ | ✅ 2/2 correct | ✅ | |
| GPA / GPA scale | ❌ | ✅ | ✅ | ❌ 0/4 | ✅ | **table-bound; abstains safely** |
| Issue date | ❌ | ✅ | ✅ | ❌ **0/6** | ✅ | **systemic; abstains safely** |
| Validity dates (from/until) | ✅ | ✅ | ✅ | ✅ 2/2 correct | ✅ | `valid_from != valid_until` verified |
| Evidence / provenance | ✅ | ✅ | ✅ 10 | ✅ every populated field | ✅ | **truthful in every case observed** |
| OCR confidence | ✅ | ✅ | ✅ | ✅ | ⚠️ | policy correct, **presentation misleading** |
| Evidence sufficiency policy | ✅ | ✅ | ✅ | ✅ | ✅ | **the safety backbone** |
| Human review (4 decisions) | ✅ | ✅ | ✅ | ✅ | ✅ | all four verified |
| Human correction | ✅ | ✅ | ✅ | ✅ | ✅ | |
| Human rejection | ✅ | ✅ | ✅ | ✅ | ✅ | **the main defence against F-10/F-11** |
| Effective fields | ✅ | ✅ | ✅ | ✅ | ✅ | |
| Required-document checking | ✅ | ✅ | ✅ | ✅ | ✅ | |
| Required-field checking | ⚠️ | ✅ | ✅ | ⚠️ over-scoped | ⚠️ | never closes (F-16) |
| Cross-document comparison | ⚠️ | ✅ | ✅ | ❌ not exercised end-to-end | ⚠️ | two comparison semantics (F-17) |
| Expiration | ✅ | ✅ | ✅ | ✅ verified on an expired document | ✅ | **expired stays blocked even fully human-confirmed** |
| GPA rule | ✅ | ✅ | ✅ | ⚠️ unreachable from real docs | ✅ | configured in the seed, not hardcoded elsewhere |
| Submission verification | ✅ | ✅ | ✅ 33 | ✅ | ✅ | **0 false READY** |
| READY | ✅ | ✅ | ✅ | ✅ reachable **only** via full human review | ✅ | |
| REVIEW_REQUIRED | ✅ | ✅ | ✅ | ✅ | ✅ | |
| NEEDS_CORRECTION | ✅ | ✅ | ✅ | ✅ | ✅ | |
| PROCESSING | ✅ | ✅ | ✅ | ✅ | ⚠️ | no automatic recovery from a crash |
| FAILED | ✅ | ✅ | ✅ | ⚠️ transient causes become terminal (F-13) | ❌ **UNSAFE** | |
| Reprocessing | ✅ | ✅ | ✅ | ✅ | ✅ | version bump, stale reviews retained |
| Retry | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | manual only; F-13 |
| Stale-result invalidation | ✅ | ✅ | ✅ | ✅ | ✅ | snapshot hash verified |
| Concurrency safety | ⚠️ | ✅ | ❌ **no tests** | ❌ | ❌ **UNSAFE** | F-13 |
| Storage cleanup | ✅ | ✅ | ✅ | ✅ | ✅ | partial-file unlink verified |
| Logging | ⚠️ | ✅ | ❌ | ❌ | ⚠️ | **no per-stage trail in production** (F-15) |
| Privacy | ✅ | ✅ | ✅ | ✅ | ✅ | **no PII in logs; no external calls** |
| Security | ✅ | ✅ | ✅ 9 probes | ✅ | ✅ | |
| Evaluation tooling | ⚠️ | n/a | ✅ | ⚠️ | ⚠️ | **two scorers, inconsistent semantics** |

## What is not ready — blocking, important, future

### BLOCKER (must be fixed before Phase 9 or a multi-document demo)
1. **F-14** — per-document OCR timeout makes multi-page documents impossible; cascades into `OCR_BUSY`.
2. **F-13** — transient OCR capacity permanently fails a document.
3. **F-03** — `issue_date` null on 3 of 6 documents; blocks the student workflow's only rule.
4. **2 red tests** — `make test` fails; one documents the REAL-007 defect.
5. **F-01** — a legitimate oversized government form cannot be uploaded.
6. **F-16** — 10 field/document combinations cannot be human-resolved; document status never closes.

### IMPORTANT (strongly recommended before Phase 9)
7. **F-15** — no per-stage audit trail; rule evaluation cannot be diagnosed in production.
8. **F-04** — label shadowing; a readable field guaranteed null on every SME certificate.
9. **F-17** — two comparison semantics; false blocking `INFORMATION_MISMATCH` on correct data.
10. **F-05 / F-07** — no layout/table layer; transcripts yield 0/6 and 3/6 fields.
11. **F-02** — a synthetic specimen is presented as a realistic document.
12. **Evaluator consolidation** on the better scorer semantics.
13. A trustworthy realistic corpus with independent human ground truth and per-sample provenance.

### FUTURE
14. Layout/table structure stage (PP-StructureV3 + SLANeXt_wired).
15. Seal recognition; stamp artefacts currently break row grouping.
16. Per-field corroboration signals for reviewer guidance.
17. Confidence *reasons* surfaced instead of a bare number.
18. CLOVA OCR specialised model for 사업자등록증 (only if the privacy constraint is relaxed).
19. Optional VLM proposal generator (never authoritative).
20. Deskew / perspective correction — only with evidence it helps.