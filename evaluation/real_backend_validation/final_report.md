# Final Engineering Report

Full detail is in the sibling documents; this is the definitive summary.
Baseline was frozen before any analysis. **No production code was modified.**

---

## A. Executive summary

**How strong is the backend right now?** Its *safety* is genuinely strong; its *accuracy* is weak.

**What works** — classification (6/6 correct), normalisation (56/57 probes), evidence & provenance
(truthful on every populated field), the submission-verification engine (0 false READY across 8
scenarios), the effective-field resolver, storage isolation, upload security (7/7 hostile probes
rejected), transaction locking, staleness invalidation.

**What does not** — extraction recall is **9 correct / 3 wrong / 14 unresolved** across 36 field
verdicts. The highest-quality scan in the set produced **0 of 6 fields**. `issue_date` failed on
**6 of 6**. `gpa` failed on **both** transcripts. Multi-page documents cannot be processed at all.

**Is it safe?** Yes, and unusually so: **0 hallucinated fields, 0 false READY, correct UNKNOWN
handling, correct null semantics.** Every OCR-sourced value is gated behind human confirmation, which
is precisely why 3 confident wrong values did not become false decisions. **This property must not be
traded for accuracy.**

**The most important finding:** the most confident machine value in the whole dataset (**0.9955**) is
**wrong** — a single Hangul vowel substitution on a student's name, adjudicated at 2.2× zoom. OCR
confidence is not a correctness probability, and the recogniser in use is documented at **88 % line-level**
Korean accuracy.

---

## B–C. Repository and architecture

Branch `main`, HEAD `721cc9d`, 45 modified + 13 untracked files **preserved untouched**. Full production
path traced in `architecture_current.md`. Dependency direction is correct and the deterministic spine
(evidence → policy → review → effective → rules → status) is sound.

---

## D–G. Implementation, dataset, coverage, duplicates

Feature matrix in `readiness_matrix.md`. 7 unique documents, **7 unique hashes, 0 duplicates**.
4 types represented; 국세납세증명서 / 졸업증명서 / 경력증명서 / real-UNKNOWN **not represented**.

> **Dataset finding that invalidates prior claims:** all 3 PDFs have **zero text-layer characters**.
> Every realistic document is a scan, so the digital-PDF path, the mixed path and the
> "no human review needed" path are **entirely unexercised by real data**.
> **And one of the 7 files is a synthetic specimen presented as realistic** (F-02) — it was evidently
> produced by the previous round's generator.

---

## H–I. Ground truth and methodology

Ground truth established independently by visual inspection of every rendered original page plus
high-zoom crops of every disputed field; values kept **outside** the repository. 7 fields recorded
`AMBIGUOUS` and the system was **not** penalised for refusing them.

Evaluator audited. The newer `eval_lib/safety.py` is sound (fixed denominators, VERIFIED_ABSENT,
negative assertions, duplicate detection). The older `eval_lib/metrics.py` has two serious weaknesses:
it iterates **gold keys only**, so **hallucinated fields are invisible**; and it scores
`gold None == pred None` as "correct", **conflating abstention with correctness**. Consolidate on the
better semantics.

---

## J–N. Live application, pipeline, per-document, per-field, classification

**LIVE STACK (local backend) + docker image build verified.** Real uvicorn, real socket, real PaddleOCR
3.2.0 on CPU. Persistence across restart confirmed (52 projects, identical status distribution).

| | |
|---|---|
| Documents reaching COMPLETED | **6 / 7** (1 rejected at upload) |
| Classification | **6/6 correct, 0 wrong, 0 UNKNOWN** |
| Fields CORRECT | **9** |
| Fields **INCORRECT_NON_NULL** | **3** |
| Fields UNRESOLVED | **14** |
| Correct abstentions | **1** (+7 ambiguous) |
| **Hallucinated fields** | **0** |
| Supported-field precision / recall | **0.75 / 0.35** |
| **False READY** | **0** across 8 scenarios |
| Review rate | 6/6 (100 % — by design) |

---

## O–Q. OCR, layout, tables

**Recognition:** excellent readable text, 88 %-line-level model, all 3 wrong values from here.
**Detection/segmentation:** adjacent table-column labels cross-merged (REAL-004: `학 번` + `성 명` → `학성`).
**Geometry:** preserved (polygon, det-conf, transform) but **never consumed**; `results._evidence_from_dict`
is lossy. **Reading order:** y-band + x — adequate for labels, inadequate for tables.
**Layout:** **NOT IMPLEMENTED.** **Tables:** **NOT IMPLEMENTED.**

**Root cause of the biggest failures:** `build_rows` merges by vertical overlap only, so a **table row's
cells collapse into one TextRow**. REAL-004's header — five logically separate fields — became one
7-segment row. This is an architectural gap, not a patchable bug.

---

## R–W. Extraction, wrong values, normalisation, evidence

**Every INCORRECT_NON_NULL, listed:**

| Sample | Field | Conf | Rule-fed? | Earliest stage |
|---|---|---|---|---|
| REAL-007 | `student_name` | **0.9955** | yes (`APPLICANT_NAME_MATCH`) | OCR_RECOGNITION |
| REAL-006 | `company_name` | 0.9660 | yes (required + `FIELD_COMPARISON`) | OCR_RECOGNITION |
| REAL-002 | `business_address` | 0.9119 | no | OCR_RECOGNITION |

**A near-miss worth recording:** on REAL-004 the detector mis-read a student id (`2023034478` for
`2020304478`) — had the label not also been destroyed, that would have been a fourth confident wrong
identifier on a clean scan.

**Normalisation: SAFE.** 56/57 probes pass. Dates, all 4 dash variants, Korean particles, reversed and
multi-period ranges all abstain correctly. **Evidence: TRUTHFUL** in every case observed — including for
wrong values, where the evidence correctly describes *what was read*.

---

## X–Z. Confidence, review, effective fields

Confidence is **honest as a policy input, misleading as a presented number**. Human review works
correctly for all four decisions and is the reason nothing dangerous escaped. Effective fields are
computed correctly. **10 field/document combinations are structurally unresolvable** because
`EXPECTED_FIELDS` (which gates review) omits fields extractors produce (F-16).

---

## AA–AF. Workflows, verification, null safety, false READY, status semantics

Business and student workflows both exercised over real HTTP. Null safety is **thoroughly correct** —
every probe passed. `EXPIRED_DOCUMENT` holds even with **every** field human-confirmed. **0 false READY.**
Status semantics are sound; READY is reachable only via full human resolution.

**One false-blocking bug:** two different comparison semantics in one product produce a blocking
`INFORMATION_MISMATCH` for company names differing by one space (F-17, reproduced through the engine).

---

## AG–AQ. Reprocessing, concurrency, API, storage, DB, transactions, security, privacy, performance

Reprocessing and stale invalidation are **correct**. Same-document concurrency is **safe**.
**Different-document concurrency is UNSAFE** (F-13). **Multi-page is UNSAFE** (F-14).

API contract clean; 7/7 hostile upload probes rejected; no PII in logs; **no external calls made**.
Measured: OCR median 6.7 s / max 39.3 s per document; dense page **25.4 s**; **~4-page ceiling**;
1 document at a time; 1.5× run-to-run variance.

---

## AR–AU. Dead code, test quality, gaps, synthetic-vs-real gap

Dead: `OCRLine.orientation_degrees`, `EvidenceRef` fields that nothing consumes, the unranked
`candidate_after_label` path still used by all date/GPA helpers, lossy evidence reconstruction.

**340 tests; 2 red. No test instantiates `PaddleOCR(`. No test runs a real pipeline on a real file.
No concurrency tests.** All "real document regression" tests are hand-built fixtures asserting beliefs.
`make check` excludes OCR evaluation by design.

**Synthetic vs realistic gap — the headline:** the synthetic benchmark reports near-perfect results
because synthetic labels are generated by the same heuristics being tested. On real documents the
system produced **0/6 fields** on its cleanest input and **0/6 `issue_date`**. The gap is not a few
points; it is categorical, and it is caused by a missing structure layer plus recogniser limits that
synthetic fixtures never exercise.

---

## AV–AW. Failure taxonomy and ranked root causes

1. **No layout/table-structure layer** — F-05, F-07, F-08, and most of the review burden.
2. **88 %-line-level recogniser feeding a UI that shows confidence to 3 dp** — F-06, F-10, F-11, F-12.
3. **Per-document resource budget on a single synchronous worker** — F-13, F-14, F-18.
4. **Heuristics tuned by assumption** — F-03, F-04, F-08, F-09.
5. **Two overlapping field vocabularies** — F-16, F-17.
6. **Third-party global state trusted** — F-15.
7. **Storage layer leaking OCR knowledge** — F-01.
8. **Dataset provenance untracked** — F-02.

---

## AX. Top 10 risks

| # | Risk | Severity |
|---|---|---|
| 1 | Multi-page documents always fail — the core use case is unsupported | CRITICAL |
| 2 | Confident wrong values reach reviewers with no corroboration signal | HIGH |
| 3 | Concurrent submissions permanently fail documents | HIGH |
| 4 | `issue_date` systematically null → student workflow rule unusable | HIGH |
| 5 | 10 field/document combos cannot be human-resolved; status never closes | HIGH |
| 6 | No audit trail in production — failures are undiagnosable | MEDIUM |
| 7 | A synthetic specimen is being reported as realistic | MEDIUM |
| 8 | Cross-document comparison can falsely block on correct data | MEDIUM |
| 9 | A legitimate oversized official form cannot be uploaded | HIGH |
| 10 | The quality gate is red — no regression protection while Phase 9 lands | HIGH |

---

## AY–BD. Readiness

See `readiness_matrix.md`. **READY:** upload/storage security, PDF+image routing incl. mixed,
evidence model, normalisation, submission engine, effective resolver, status aggregation,
transactions. **FUNCTIONAL_BUT-LIMITED:** classification, OCR adapter, human review, duplicates,
evaluation tooling. **PARTIAL:** field extraction, cross-document comparison, logging, reprocessing.
**UNSAFE:** concurrency, multi-page handling. **NOT-IMPLEMENTED:** layout reconstruction, table
understanding, deskew/perspective. **NOT-EVALUATED:** 4 document types, any real UNKNOWN input,
anything under load.

---

## BE–BO. Architecture, debt, research, keep/improve/replace

**Strengths:** correct dependency direction; a real abstention spine; truthful evidence; the
confirmation gate; verification that refuses unsafe configuration; genuine SQLite concurrency
workaround; end-to-end staleness handling.

**Weaknesses:** no structure layer; confidence presented as truth; wrong-shaped resource model; two
vocabularies; heuristics tuned by assumption; global state trusted.

**Research conclusion:** **PP-StructureV3 + SLANeXt_wired** is the single highest-leverage change —
same validated recogniser, adds layout + wired-table structure + cell coordinates, runs on CPU,
preserves determinism and the evidence model. **Reject PP-OCRv6 for Korean** (Korean not in its
language set). Keep VLMs out of the authoritative path. **CLOVA OCR's Korean business-registration
specialised model** is the targeted contingency for the worst document type.

**No redesign is justified.** Three additive changes: structure stage, queued OCR, single-sourced
vocabulary.

---

## BP–BU. Prioritised plan, gates, git state

Full plan with alternatives, files, tests, regression risk and expected benefit in
`improvement_options.md`. **P0:** F-14, F-03, F-04, F-15, make the gate green. **P1:** F-16, F-01,
F-17, F-08/09, trustworthy corpus. **P2:** structure stage, queue, corroboration signals.
**P3:** CLOVA OCR, seal recognition, optional VLM proposal path.

**Nothing was implemented.** Stop condition verified: `git status --short`, `git diff --stat`
(45 files / 1553 insertions / 323 deletions — identical to the start), `git diff --check` clean.
HEAD `721cc9d`. Desktop originals' mtimes unchanged.

---

## BV. Final engineering verdict

**Is the architecture fundamentally sound?** Yes — and its safety properties are better than most
systems at this stage. **What is single-priority?** Add the missing structure layer, but make the
system survivable first by fixing the per-document OCR timeout.

**Is the backend strong enough for a capstone demonstration?**
**With conditions.** It is defensible today only as a single-page, human-reviewed walkthrough that
leads with abstention and evidence. It is **not** yet defensible as a realistic multi-document
submission check.

**Should Phase 9 begin? YES_WITH_CONDITIONS.** Phase 9's value is a function of input trustworthiness,
and the inputs are currently weak. Blocked on F-14, F-03, F-04, F-16 and a green gate.

**What must NOT be changed:** the evidence-sufficiency gate, the conflict-abstains guard, the
verification engine's refusal to guess about configuration, the dependency direction, and the
"UNRESOLVED over a confident guess" principle. These are the reason the system is safe rather than
merely imperfect.