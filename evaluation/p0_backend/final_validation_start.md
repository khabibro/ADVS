# P0 final validation — frozen starting state

Sanitized snapshot taken before any validation work. No sample contents.

## Repository

| Field | Value |
|---|---|
| Branch | `main` |
| Starting HEAD | `f641fee2031641f3da0983d57d27460607c7f89e` |
| Remote | `git@github-khabibro:khabibro/ADVS.git` (fetch and push) |
| `git config --local user.name` | `KHABIBILLO` |
| `git config --local user.email` | `khabibillionaire@gmail.com` |
| `ssh -T git@github-khabibro` | `Hi khabibro! You've successfully authenticated` |
| Tracking | `main...origin/main`, up to date with `origin/main` |

Push authentication resolves to `khabibro`, as required.

## Recent history (`git log --date=iso -30`)

```
f641fee | 2026-10-02 22:52:36 +0900 | KHABIBILLO  | Update document review contracts and UI integration
2326ed1 | 2026-10-02 22:52:24 +0900 | KHABIBILLO  | Strengthen extraction and verification safety
fa38ef8 | 2026-10-02 22:52:05 +0900 | KHABIBILLO  | Harden OCR ingestion and processing reliability
721cc9d | 2026-09-29 09:37:36 +0900 | Munira     | Improve real-document processing and extraction
2228b75 | 2026-09-29 00:37:34 +0900 | Munira     | Rebuild frontend document workflow and review experience
6a73d37 | 2026-09-28 22:10:21 +0900 | KHABIBILLO  | Add evidence-aware human review workflow
95820f8 | 2026-09-22 17:21:58 +0900 | KHABIBILLO  | Add null-safe submission verification engine
d22ce4e | 2026-09-22 10:12:44 +0900 | KHABIBILLO  | Harden document classification and field extraction
2638c51 | 2026-09-22 09:37:06 +0900 | KHABIBILLO  | Integrate end-to-end document processing pipeline
237404b | 2026-09-20 19:53:52 +0900 | KHABIBILLO  | Add canonical document evidence and provenance
5270935 | 2026-09-20 16:11:46 +0900 | KHABIBILLO  | Complete document domains
88f227a | 2026-09-20 14:09:53 +0900 | KHABIBILLO  | Complete status semantics
ddfdc2c | 2026-09-15 23:11:01 +0900 | KHABIBILLO  | Fix web image build without public assets
eabc744 | 2026-09-15 22:59:39 +0900 | KHABIBILLO  | Fix CI storage tracking and ADVS workflow config
aff7872 | 2026-09-15 22:50:47 +0900 | KHABIBILLO  | Add current ADVS implementation
1ba16d1 | 2026-09-05 15:18:43 +0900 | KHABIBILLO  | first commit
```

## Worktree at freeze (unstaged production/test changes)

```
 M apps/api/app/core/domain.py
 M apps/api/app/core/logging.py
 M apps/api/app/document_intelligence/extraction/base.py
 M apps/api/app/document_intelligence/ocr/providers.py
 M apps/api/app/document_intelligence/ocr/worker.py
 M apps/api/app/document_intelligence/validation/submission.py
 M apps/api/app/services/requirements.py
 M apps/api/app/services/reviews.py
 M apps/api/app/services/storage/local.py
 M apps/api/tests/test_astra_ingestion.py
```

`git diff --stat`: 10 files, 206 insertions, 51 deletions.
`git diff --check`: clean.

## Untracked at freeze

`apps/api/tests/test_p0_backend_stabilization.py`, the `evaluation/` evidence
directories from earlier sessions, `evaluation/results/round2_*`, an unrelated
Mach-O binary at `temp`, and `txt.txt`.

## Private-material handling established at freeze

`.gitignore` gained a generic rule for `evaluation/private_runtime/`, and the
rule was verified before any private ground truth or machine output was written:

```
$ git check-ignore -v evaluation/private_runtime/probe.json
.gitignore:55:evaluation/private_runtime/    evaluation/private_runtime/probe.json
```

The pre-existing rule for `evaluation/backend_round2/work/` (which holds the
real ground truth) was also re-verified:

```
$ git check-ignore -v evaluation/backend_round2/work/ground_truth.json
.gitignore:51:evaluation/backend_round2/work/    evaluation/backend_round2/work/ground_truth.json
```

## Evaluator hashes used to define the frozen denominator

Recorded before any model output was inspected.

| Artefact | SHA-256 |
|---|---|
| ground truth (`evaluation/backend_round2/work/ground_truth.json`) | `ff4b226c946b78d79ee320c3e30fd349ca715a7db18c403159088e9b05e53893` |
| runner (`evaluation/backend_round2/run_round2.py`, post path fix) | recorded in `desktop_samples_results.md` |
| summariser (`evaluation/backend_round2/summarise.py`) | `4d44a504c89eab8a636f5067879164473f7ac0daf2f1e3b9b6155d13aaa1a8fc` |
| diagnoser (`evaluation/backend_round2/diagnose_rows.py`) | `1560db809bbebe347741d5699277e4255bfd1b4d9a91f5c39721703c78c4a673` |

The denominator was frozen at 7 files / 34 evaluable fields and was not changed
after seeing any model output.