# A1 — Repository State and Decision Memo

Branch `main`, HEAD `48e3824a780e3c051cba2d2eb1838851db1fcf1e`. `git status
--porcelain` matches the state recorded at the start of every prior phase
in this session exactly: one modified tracked file, a fixed list of
untracked paths. No drift found. Nothing was committed, pushed, or
otherwise written to git in producing this memo; the one `git worktree
add`/`remove` pair used below left no trace (`git worktree list` shows
only `main` and one pre-existing, unrelated worktree this session did not
create and did not touch).

## 1–2. The uncommitted change: `extraction/base.py`

Full diff reviewed (`git diff -- apps/api/app/document_intelligence/extraction/base.py`).

**What it changes, in plain words:** the extractor has a rule that an
issue-date found as a bare, unlabelled date near an issuer signature block
is only trusted if no *unfulfilled label* for that date appears earlier on
the page — the idea being that if the document clearly tried to label the
date and the label's own value came back unreadable, inferring the date
from a bare fallback would hide that loss rather than report it. The bug
this change fixes: that "unfulfilled label" check matched a label word
*anywhere inside a row's text*, including inside an ordinary sentence. Some
certificates (the comment cites a social-insurance payment certificate)
print a prose sentence in their issuance block that happens to contain the
word for "issued" as part of normal Korean prose, not as a field label. A
row like that was wrongly treated as an unfulfilled label, so a bare date
that had in fact been read correctly, with every other safety guard
already passed, was discarded — the field went missing instead of taking
the correct value. The fix adds a 24-character-or-less, digit-free
"looks like a label, not a sentence" gate (`_row_states_a_label`) before a
row is allowed to count as an unfulfilled label at all.

**Which tests depend on it:** `apps/api/tests/test_p2_2_issue_date_attribution.py`
imports `_LABEL_ROW_MAX_CHARS` and `_row_states_a_label` directly from
`base.py`. Verified empirically, not just by reading the import list: this
test file was copied into a clean `git worktree` checked out at the
current committed HEAD (i.e., **without** this diff) and run there. Result:

```
ImportError: cannot import name '_LABEL_ROW_MAX_CHARS' from
'app.document_intelligence.extraction.base'
```

— a collection failure, not a test failure. The test file cannot even be
collected against committed HEAD; it is unconditionally coupled to this
exact uncommitted diff. No other test file in the repository imports
`_row_states_a_label`, `_has_unresolved_label_before_candidate`, or
`_LABEL_ROW_MAX_CHARS` (checked by grep across `tests/`).

## 3. Untracked test files

**Correction to this phase's own framing:** of the four files named in the
prompt, only **two** are actually untracked. The other two are already
part of committed HEAD. Verified by checking them out into the same clean
worktree used above — both existed there, unmodified, with no diff. This
distinction matters for what's "pending a decision" below.

| File | Tracked at HEAD? | Tests | Depends on the uncommitted `base.py` diff? | What it tests |
|---|---|---|---|---|
| `test_round2_real_document_fixes.py` | **Yes, already committed** | 28 | No — imports only pre-existing symbols (`standalone_date_candidate`, which is untouched by the diff) | Five real-document-audit regressions from the "Round 2" findings (R2-01..R2-05): image uploads reaching OCR, a checklist-suppression bug in the missing-field net, `.webp` upload acceptance, bare issuance-block dates, and EXIF-orientation preprocessing. Already landed, already part of history — not a pending decision. |
| `test_real_document_regressions.py` | **Yes, already committed** | 12 | No | General real-document regression pins (classifier, field heuristics, row building, PDF text-meaningfulness). Already landed. |
| `test_p1_layout.py` | **No, untracked** | 18 | No — imports only from the untracked `app/document_intelligence/layout/` package, not from `base.py` | The P1 geometry/structure layer in isolation (columns, sections, header-value row detection) — deliberately asserts *no field value*, per its own docstring, because P2.1's own measurement found this layer changes zero field outcomes on the frozen corpus. This is **P1-phase work that was already measured and decided** (`KEEP_DORMANT`, per `evaluation/p2_1_ocr_diagnosis/final_report.md`), not open/in-flight work — it pins a decision already made, it does not anticipate one. |
| `test_p2_2_issue_date_attribution.py` | **No, untracked** | 18 | **Yes — required**, see §1–2 | Pins both directions of the `base.py` fix: the false negative is fixed, and the pre-existing "a genuine unfulfilled label still suppresses the bare date" guard is not weakened. The filename is explicitly `p2_2`. |

**On the `p2_2` naming specifically:** this session's very first task this
phase sequence continues from opened with an explicit instruction not to
start P2.2, and a later phase repeated that instruction. This file's name,
the `base.py` diff it depends on, and the untracked
`evaluation/p2_2_targeted_improvement/` directory (10 files, all scripts —
`adjudicate_gold.py`, `probe_candidates.py`, `run_experiment.py`,
`run_concurrency_strong.py`, `run_multipage_concurrency.py`,
`probe_dates.py`, `adjudication_crops.py`, `run_workflow_probe.py`, plus
cache — **no final report, no README**, unlike every completed phase
directory in this repo) are consistent with one another: work toward P2.2
appears to have been started in a prior session, producing this specific
fix plus its test, and an exploratory-script scratch directory with no
written-up conclusion. Stated as an observation, not a judgment — the fix
itself (§1–2) reads as a narrow, well-scoped, well-tested correctness fix
on its own merits, independent of which phase it was produced under.

## 4. Backend suite, run twice

**(a) Working tree as-is:**
```
.venv312/bin/python -m pytest -q
→ 386 passed, 0 failed, 16 warnings, 27.3s
```

**(b) Clean worktree of HEAD**, created with
`git worktree add --detach <tmp> 48e3824a...`, outside the repo
(`/tmp/advs_head_worktree.*`), run with the same interpreter
(`apps/api/.venv312/bin/python`, since a worktree does not carry the
gitignored venv), then removed with `git worktree remove --force`. The
main working tree was not touched by this process.
```
→ 350 passed, 0 failed, 16 warnings, 36.1s
```

**Difference: exactly +36**, and it is exactly accounted for:
`test_p1_layout.py` (18 tests) + `test_p2_2_issue_date_attribution.py`
(18 tests) = 36, both untracked-only files, both collected and passing
only in the working tree. The 350 at HEAD already include
`test_round2_real_document_fixes.py` (28) and `test_real_document_regressions.py`
(12) — confirming §3's correction. **No test regressed; the diff is purely
additive to the passing count**, and nothing fails in either state.

## 5. Recommendations

| Item | Recommendation | Reason |
|---|---|---|
| `apps/api/app/document_intelligence/extraction/base.py` (modified) | **Commit** | Narrow, well-scoped fix; empirically shown to add a real regression test (not just assert passing); does not touch the guard it must not weaken (the test file pins both directions); no test anywhere regresses with it in place. |
| `apps/api/tests/test_p2_2_issue_date_attribution.py` | **Commit together with `base.py`** | It cannot be collected without the diff (§1–2) — committing one without the other leaves either an uncovered fix or a broken test file. They are one unit. |
| `apps/api/app/document_intelligence/layout/` | **Commit** | Dormant, but completed, measured (P2.1), decided (`KEEP_DORMANT`), and tested — this is finished P1 work sitting uncommitted, not in-flight work. Leaving it untracked indefinitely risks losing a decision that was already paid for. |
| `apps/api/tests/test_p1_layout.py` | **Commit together with `layout/`** | Same reasoning; it is the test for the module above and asserts nothing beyond what P2.1 already measured. |
| `apps/api/app/document_intelligence/extraction/structural.py` | **Do not commit yet — flag for the user** | Confirmed (again, independently, in this memo) to have zero importers anywhere under `app/` and zero test coverage anywhere in `tests/`. It is genuinely dormant, untested, and — per the prior independent audit (F-014) and P2.1's own `KEEP_DORMANT` verdict — not meant to be on the production path. Committing untested, unreferenced code is a judgment call for the user, not a default "yes." |
| `evaluation/p2_2_targeted_improvement/` (10 files, scripts, no report) | **Flag for the user explicitly — do not commit, do not delete** | This is the clearest sign that P2.2 work was started before this phase sequence's instructions said not to. It is scratch work, not a deliverable (no final report exists, unlike every other completed phase directory in this repo). The user should decide whether to resume it as the deliberate next phase, move it aside, or discard it — not have that decided implicitly by what gets committed now. |
| `evaluation/astra_backend/`, `evaluation/backend_round2/`, `evaluation/p1_layout/`, `evaluation/p2_1_ocr_diagnosis/`, `evaluation/p2_ocr/`, `evaluation/real_backend_validation/`, `evaluation/results/round2_*.csv/json`, `evaluation/system_audit/` | **Commit** (or at minimum: do not discard) | Each is a completed-phase evaluation record with a final report (verified: all contain a `final_report.md` or equivalent except `p2_2_targeted_improvement`, which is the one flagged above). These are exactly the kind of "evaluation-quality, not production-code" artifacts this whole project has been treating as durable history; `evaluation/results/round2_*` are the numeric companions to `evaluation/backend_round2/`. |
| `.venv`, `temp`, `txt.txt` | **No action — not evaluated here** | Out of this memo's scope per the constraint not to delete anything; `temp`/`txt.txt` were already flagged as unexplained, low-severity artifacts in the prior audit (F-017/F-018) and are untracked, so they do not affect any commit decision. |

## Repository state, restated for the record

- HEAD after this memo: unchanged, `48e3824a780e3c051cba2d2eb1838851db1fcf1e`.
- `git status --porcelain`: unchanged from the start of this memo.
- No file under `apps/` or the test suite was edited by this phase.
- No gold file was touched.

**STOPPING HERE per instructions.** Waiting for the user's commit decision
before proceeding to A2.
