# Privacy Scan Before Commit

Run immediately before Commit A/B of the Phase A baseline work, gating
whether anything is committed. Contains no private values — categorical
results and file paths only.

## 1. `git check-ignore -v`

| Path | Ignored? |
|---|---|
| `evaluation/backend_round2/work/` | **YES** — `.gitignore:51` |
| `evaluation/private_runtime/` | **YES** — `.gitignore:55` |
| `evaluation/astra_backend/`, `evaluation/backend_round2/` (itself), `evaluation/p1_layout/`, `evaluation/p2_1_ocr_diagnosis/`, `evaluation/p2_2_targeted_improvement/`, `evaluation/p2_ocr/`, `evaluation/phase_a_baseline/`, `evaluation/real_backend_validation/`, `evaluation/system_audit/`, `evaluation/results/round2_*.{csv,json}` | **NO** |

## 2. Classification of every untracked, not-ignored file under `evaluation/`

Scope: `git ls-files --others --exclude-standard evaluation/` → **132 files**.
Zero are images or PDFs (verified with `file` on every path — all report as
text/JSON, none as PNG/JPEG/PDF/binary).

**Method, applied to all 132 files, not a sample:**
- Resident-registration-number pattern `\d{6}-?[1-4]\d{6}` — 12 files
  matched; every match individually inspected. All 12 are false positives:
  long decimal fractions in precision/recall/confidence metric values
  (e.g. a 16-digit repeating decimal like `0.91659992933273...`) that
  happen to contain a 13-digit substring of the right shape. None is an
  actual resident-registration-number-shaped standalone value. **No real
  match.**
- Business-registration-number pattern `\d{3}-\d{2}-\d{5}` — 1 file
  matched (`evaluation/backend_round2/remaining_failures.md`); inspected:
  the well-documented synthetic placeholder number already recorded
  elsewhere in this project as belonging to the fictional `샘플 주식회사`
  fixture. **Safe.**
- Blanket Hangul-presence scan — 40 of 132 files contain any Korean text
  at all; every one individually read. All Korean content is one of: field
  *label* names (the same alias-list vocabulary that exists in production
  code, e.g. "사업자등록번호"), Korean document-type names (e.g.
  "재학증명서" = "enrollment certificate" — a category name, not personal
  data), checklist/UI config names, generic/obviously-fictional test
  fixture strings (e.g. a placeholder "sample corporation" name used in
  this session's own synthetic probes), or category-level discussion in
  narrative reports that explicitly avoids quoting a transcribed value
  (one file's own text states this directly: "the private value is
  intentionally not copied into this tracked record"). **One exception,
  below.**
- Absolute local filesystem paths — 2 files reference
  `/Users/admin/Documents/ADVS/...`. `admin` is the generic macOS account
  name on this machine, not a real person's name, and the path reveals
  only this project's own directory structure, not any document subject's
  identity. Not a document-privacy issue; noted as a portability/hygiene
  note only, not a blocker.
- Original filenames carried through several JSON reports
  (`nfc_filename` fields): all seven distinct values are generic
  document-type names ("성적증명서.jpeg", "사업자등록증.png", etc.) with no
  personal name in any of them.

**Result: 131 of 132 files SAFE. 1 file CONTAINS_PRIVATE. 0 UNSURE.**

| File | Classification | Reason (no value quoted) |
|---|---|---|
| `evaluation/p2_2_targeted_improvement/adjudicate_gold.py` | **CONTAINS_PRIVATE** | Hardcodes real transcribed values (a specific real transcript's GPA figures and components; a department/major string) as Python string literals in its `DECISIONS` list. One of the two source documents involved is the corpus's one `REAL_PERSONAL` transcript. This directory is **not** gitignored, unlike the `private_runtime`/`backend_round2/work` locations where the script's own *output* correctly lands. |
| All other 131 files under `evaluation/astra_backend/`, `evaluation/backend_round2/` (excluding `work/`), `evaluation/p1_layout/`, `evaluation/p2_1_ocr_diagnosis/`, `evaluation/p2_ocr/`, `evaluation/phase_a_baseline/`, `evaluation/real_backend_validation/`, `evaluation/system_audit/`, `evaluation/results/round2_*` | **SAFE** | See method above; individually verified, not sampled. |

Per instruction, `evaluation/p2_2_targeted_improvement/` is excluded from
the commit **in its entirety** (not just the one flagged file), consistent
with it also being out-of-scope scratch work per the A1 decision memo.

## 3. `structural.py` / `base.py` / `test_p2_2_issue_date_attribution.py`

Excluded from Commit B per instruction regardless of privacy status — not
a privacy finding, a scope/phase-sequencing one (`base.py` and its test are
Commit D's concern; `structural.py` is dormant/unreviewed code, held per
the A1 memo).

## 4. `layout/` package reachability (re-confirmed)

```
grep -rn "document_intelligence.layout\|from .layout\|from ..layout" apps/api/app
```
Only match: `apps/api/app/document_intelligence/extraction/structural.py`,
which itself has no importers anywhere under `apps/api/app/`. Nothing in
the production call path imports `layout/`. Safe to commit without
changing production behavior.

## Gate result

**PASS.** Proceeding to Commit A and Commit B, the latter excluding the one
CONTAINS_PRIVATE file and its containing directory in full.
