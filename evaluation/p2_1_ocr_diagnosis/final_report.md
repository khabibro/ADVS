# P2.1 Final Report

## A. Verdict

**P2.1_PASS_WITH_WARNINGS**

**PHASE_9_READINESS = NO**

P2.1 did what it was asked: it built the observation-level ground truth P2
lacked, and it separated the failure stages that P2 could not separate. The
diagnosis is now measured rather than inferred, and it is specific enough to
act on.

It passes with warnings because of what the measurement exposed about the
*evidence*, not about the code: three findings would each be sufficient reason
to distrust a confident reading of this corpus, and none of them is about OCR.

No production code was changed. No OCR setting was changed. Nothing was
committed or pushed.

## B. The ten required answers

### 1. What information is visibly present?

Of 33 gold-evaluated fields: **28 values are visible and human-readable**,
**2 are absent by design** (a printed dash, an absent student-number row), and
**3 are visible but not readable** at the document's own resolution — two dense
address lines at ~48 DPI on a 400×566 raster, and one grade legend. No label is
printed at all for `university_name` on three documents, or for `issue_date` on
five.

### 2. What does OCR detect?

**Every one of them.** Across 33 evaluated fields: 26 values detected at their
own position, 1 detected elsewhere on the page, 1 with all characters present
but text near-correct, 2 detected but mis-transcribed. **0 not observed.**

All 650 observations carry a bounding box.

### 3. What does OCR recognize correctly?

**27 of 33 exactly.** 4 near or partial, 2 incorrect. But the distribution is
lopsided in a way that matters: in **5 of the 6 recognition failures the value
was read perfectly and the *label* was misread**. Short, letter-spaced,
low-contrast, two-to-seven-syllable labels are the weak point — not names, not
numbers, not dates.

### 4. Where does information disappear?

Thirteen distinct traces in `pipeline_trace.md`. It never disappears during
rendering, preprocessing, **detection**, observation storage, reading order or
normalisation. It disappears at three later stages:

- **Label matching** — 5 fields, blocked by a single wrong character in a label
  that is the key to the field.
- **Row construction and the bare-date rule** — 3 fields, one symptom, three
  unrelated mechanisms.
- **Structural interpretation** — 5 fields, where the value is only reachable
  by understanding that a spaced line above a signature names the issuer.

### 5. What percentage of failures are confirmed detection failures?

**0%.** 0 of 17.

Stated correctly: **no detection failure was confirmed.** This does **not** mean
none exist. Fragmentation and merge rates were not measured at all, and two
fields could not be tested because the frozen gold supplies no value for them.

### 6. What percentage are confirmed recognition failures?

**35.3%** — 6 of 17 failures (18.2% of all evaluated fields). Each traced to a
named mis-transcribed string.

### 7. What percentage are downstream extraction / association failures?

**Extraction: 23.5%** — 4 of 17 (12.1% of evaluated fields). Three are the
issuance-block date rule refusing a correctly-read date for three different
reasons; one is a genuine alias-vocabulary gap.

**Association: 0%.** No field was ever populated with the wrong value *from a
correctly-read observation*. Association is not a problem on this corpus.

### 8. Is the structural layer useful?

**No. It resolved 0 of the 9 fields it was aimed at.**

Run against the same observations, for exactly the fields where OCR was already
correct and the backend still failed:

| Generator | State | Candidates |
|---|---|---|
| `header_value_candidate` | active | **0 of 9** |
| `section_scoped_values` | hard-disabled by P1 measurement | 0 |
| `issuer_block_candidate` | hard-disabled by P1 measurement | 0 |

Its geometry is computed successfully — up to 16 column bands, 9 sections, 144
header/value pairs — and still yields nothing usable. Two of three generators
are already permanently disabled in code as documented negative results.

**KEEP_DORMANT.** There is nothing to activate.

### 9. What is the dominant measured failure category?

**Recognition failure** — 6 of 17 failures, the largest single category.

But the honest reading is that **recognition is not the binding constraint.**
Perfect recognition would leave **9 fields still unresolved**: 5 structural and
4 extraction. Those 9 are not fixable by any recognizer, any DPI, any
preprocessing, any model and any VLM. Recognition is the largest category and
roughly half the problem.

### 10. What should P2.2 investigate next?

**Not an OCR upgrade.** In priority order:

1. **Row construction.** The highest-leverage defect. One rule
   (`standalone_date_candidate`) losing 3 fields for 3 unrelated reasons, and
   `build_rows` merging course tables, stamps and issuance blocks, is a single
   shared cause. It is also pure local logic — testable without OCR at all.
2. **The three issue-date refusals, individually.** All three are *conservative*
   refusals: the field goes missing rather than wrong. Each is a precise,
   narrow rule relaxation with an obvious safety argument. Cheapest real recall
   available, and it must not weaken the ambiguity guard.
3. **Label robustness.** 5 fields die on one wrong character in a label. Worth
   asking whether label matching should be tolerant of a single-character
   substitution inside a matched label — and if so, proving it cannot promote
   an adjacent value. This is the one change that could also reduce the
   *recognition* count, by making misreads survivable rather than by improving
   the recognizer.
4. **Two gold annotations to adjudicate** (see warning 2). Until these are
   resolved, the denominator for any future comparison is uncertain.
5. **Only then**, with the remaining 6 recognition failures isolated, decide
   whether an OCR change is justified.

## C. Structural layer decision

**KEEP_DORMANT.** Reinforced by measurement rather than by caution: 0 of 9.

The P1 classification stands — generic geometry primitives stay inert, and the
speculative candidate-generation adapters in `extraction/structural.py` remain
`REMOVE` from the production path. That module is untracked and **has no
production importer**; `extraction/registry.py` does not reference it. Its two
candidate generators are hard-disabled in code, and the third returns `None` on
every case that matters here. Nothing was deleted; the negative results remain
documented in place.

## D. OCR decision

**Current baseline retained. A change is NOT justified by this evidence.**

PaddleOCR 3.2.0 CPU, `PP-OCRv5_mobile_det` + `korean_PP-OCRv5_mobile_rec`,
resolution-aware rendering, 288 DPI nominal.

The test that was missing in P2 now exists, and it says: **detection is not the
bottleneck.** Not one human-readable value went unobserved. A detector swap
would be aimed at a problem this corpus does not have.

Recognition errors are real and are the largest single category, but:

- **9 of 17 failures would survive perfect recognition.**
- **No alternative OCR configuration was scored**, because observation-level
  gold did not exist until this phase. Scoring one now would be the *first*
  honest comparison available — which is exactly what P2.2 item 5 should do,
  after the extraction work, so that OCR is judged against a downstream that
  can actually use what it reads.
- Nothing here measures whether a stronger recognizer would fix labels
  *and* keep values correct. Those are separable and were not separated.

**Insufficient evidence to select an OCR improvement** — not because the
evidence is absent, but because half the failure mass sits downstream of where
an OCR change can reach.

## E. Overfitting audit

Every candidate fix was tested against: *would this still make sense if these
seven documents were replaced tomorrow with seven different Korean
administrative documents?*

| Candidate fix | Domain-general? | Verdict |
|---|---|---|
| Relax the bare-date rule when a preceding row is boilerplate | Yes — these forms all print prose above the signature block | **Viable** |
| Make row grouping refuse to merge a dense table with an adjacent block | Yes — layout-generic | **Viable** |
| Tolerate one substituted character inside a matched label | Yes — needs a safety proof | **Conditional** |
| Add `소속` to the enrollment department aliases | **Yes** — standard Korean university enrolment-certificate field for college/faculty | **Viable** |
| Add `보험소멸일` to social-insurance validity aliases | Yes — but the document genuinely has no value there | **Rejected**: fixes nothing, and the current output is already correct |
| Add an issuer-signature-block fallback for `university_name` | Yes in principle — **but measured at 0 for 3 fields** | **Rejected on evidence** |

**Rejected as overfitting, and not implemented:**

- Any alias or rule keyed to one document's exact string.
- Any threshold tuned to these seven documents' pixel geometry.
- Any correction dictionary containing a personal name, organisation or
  identifier — none was created, and the one wrong value was deliberately not
  "fixed", because a correction dictionary is the textbook way to make one
  document look better while the recogniser stays the same.
- Anything derived from a single document's coordinates.

The `소속` alias is the only vocabulary change recommended, and it is
recommended precisely because it is a **standard domain label**, not because
one document printed it. It should still be validated against synthetic
fixtures first.

## F. Warnings

**1. This corpus cannot support a field-quality estimate.**
Two documents are genuinely personal; **five are realistic synthetic or
recreated material, three with obvious placeholder identities**. Any recall
figure derived from these seven is dominated by synthetic content. Real-scanner
behaviour is represented by two documents.

**2. Two frozen gold annotations disagree with the documents. Both were left
unchanged, and both are flagged.**
- `REAL-003` `gpa_scale` is golded `NOT_EVIDENCED` ("only a historical maximum
  is present"), but OCR reads a **full A+–F numeric scale legend** in the
  footer. A human at high zoom should see it too.
- `REAL-004` `department` carries a gold value that **does not appear anywhere
  on the page**, in any observation.
- `REAL-003` `gpa` is golded `AMBIGUOUS`, yet the document prints a cumulative
  total row (`총취득학점` / `총평점` / `총평점평균`) in its header block, which
  looks like an overall value. This was verified only from OCR output, not by
  human re-inspection at high zoom.

Consequence: **the evaluated-field denominator (33) may be wrong.** The frozen
scorer treats `AMBIGUOUS` and `NOT_EVIDENCED` as not-evaluated. If
`REAL-003`'s `gpa` and `gpa_scale` are re-adjudicated as checkable, the
denominator becomes 35 and two fields move from "not evaluated" to measured.
No other phase should compare its numbers to this distribution until a human
adjudicates these three. **This is the highest-priority follow-up, ahead of any
optimisation work** — otherwise P2.2 optimises against a target that moves.

**3. Page metadata misreports render DPI.** `metadata.render_dpi` reports the
*configured* 288 DPI for every page, but REAL-001 is actually rendered at
**108 DPI** (scale 1.5, `source_resolution_fit`). The true value is only in
`metadata.transform.effective_render_dpi`. Any provenance or evidence record
reading `render_dpi` is wrong for that document.

**4. "288 DPI baseline" is not literally true of this corpus.** Effective
resolution at the detector ranges from ~48 DPI to 288 DPI. Four of seven
documents reach OCR at native raster resolution with no upsampling.

**5. My own blind annotation disagreed with the frozen gold twice, and the gold
was right both times.** At low zoom I misread a university name (gold and OCR
agreed against me) and a representative name on the 400×566 raster. This is
recorded because it is the strongest available argument for keeping the frozen
gold as the reference rather than substituting fresh annotation: the
high-zoom-verified gold caught errors that fresh low-zoom reading introduced.

**6. Detection recall and fragmentation were not measured.** Only presence of a
value's characters was tested. Whether one line was split into several boxes, or
two lines merged, is unmeasured. "0 detection failures" must not be read as
"detection is perfect".

**7. Multipage and concurrency pass on a narrow scope.** Multipage used repeats
of one page, not differing content per page. Concurrency was two workers, one
run, on SQLite, in two *different* projects — so the per-project lock was never
contended and PostgreSQL behaviour is unverified. See `concurrency.md`.

**8. Docker image build was not attempted.** Compose config validated only.

## G. Baseline preservation

The historical P2 baseline was recorded, not recomputed: **field recall
0.4706, wrong non-null 1, False READY 0/7, processed 7/7, classification 7/7,
all 7 requiring review, 288 DPI nominal, current PaddleOCR configuration.**

The frozen gold and frozen scorer were read but **not edited**, and no
evaluator defect was found that would justify versioning one. The independent
33-field denominator reconstructed by this phase's own diagnostic matched the
frozen scorer's, which is a cross-check on both.

## H. Phase 9 readiness

**PHASE_9_READINESS = NO.**

Not because tests fail — all 13 gates pass. Because:

1. **One wrong non-null value remains**, at OCR confidence 0.9166, caught only
   by the last-line evidence policy rather than by the extractor's own
   judgement. A marginally higher confidence on the same error would not have
   been caught automatically.
2. **All 7 real documents still require human review**, and 17 of 33 evaluated
   fields remain unresolved.
3. **Three gold annotations are now known to be questionable**, so the
   measurement denominator itself is unsettled.
4. **Concurrency and multipage are verified only on a narrow scope**, on SQLite,
   with the per-project lock untested.
5. **No production OCR improvement has been selected**, and this phase's
   evidence says the next gains are not in OCR.

Passing tests do not upgrade readiness. Nothing in P2.1 changes that.

## I. Git state

| Property | Value |
|---|---|
| Branch | `main` |
| HEAD | `48e3824a780e3c051cba2d2eb1838851db1fcf1e` — unchanged |
| Tracked files modified | 0 |
| Tracked diff / diff --stat | empty |
| Commits | 0 |
| Pushes | 0 |
| History rewritten / config or identity changed | no |

Untracked additions: `evaluation/p2_1_ocr_diagnosis/`. All pre-existing
untracked P1/P2 artifacts retained untouched. Private runtime data lives under
gitignored `evaluation/private_runtime/p2_1/` and does not appear in
`git status`.

## J. Next phase

**P2.2 — downstream extraction and row-construction repair, plus gold
adjudication.** Not an OCR phase.

Sequenced as: adjudicate the three questionable gold annotations → repair row
construction → relax the three issue-date refusals individually, each with a
safety argument → prove or reject single-character label tolerance → then, and
only then, score one OCR alternative against a downstream that can use it.

**P2.2 must not be started automatically.**
