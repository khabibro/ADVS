# Frozen P1 baseline

## Repository

| Field | Value |
|---|---|
| Branch | `main` |
| Starting HEAD | `48e3824a780e3c051cba2d2eb1838851db1fcf1e` |
| Remote | `git@github-khabibro:khabibro/ADVS.git` |
| Local author | `KHABIBILLO <khabibillionaire@gmail.com>` |
| Push authentication | `khabibro` |
| Relationship to `origin/main` | in sync at freeze; no divergence |
| Tracked worktree at freeze | clean, `git diff` empty |
| Untracked at freeze | pre-existing evidence directories, an unrelated Mach-O binary, the task brief |

History was not rewritten, reset, restored, stashed, rebased or amended. No
branch was created.

## P0 baseline, re-measured from `48e3824`

Re-measured in a separate worktree at the exact P0 tip with the frozen gold and
the frozen runner, so the P1 comparison is not against a remembered number.

| Metric | P0 baseline |
|---|---|
| Documents | 7 |
| Upload rejected | 0 |
| Processed to completion | 7 |
| Pages | 7 |
| OCR characters | 6326 |
| Classification correct | 7 |
| Fields `CORRECT` | 16 |
| Fields `INCORRECT_NON_NULL` | 1 |
| Fields `UNRESOLVED` | 17 |
| Fields `NOT_EVALUATED` | 7 |
| Field precision | 0.941 |
| Field recall | 0.471 |
| False READY | 0 |
| Wrong non-null | 1 |
| Negative-assertion violations | 0 |

## Frozen hashes

| Artefact | SHA-256 |
|---|---|
| Gold `evaluation/backend_round2/work/ground_truth.json` | `ff4b226c946b78d79ee320c3e30fd349ca715a7db18c403159088e9b05e53893` |
| Runner `evaluation/backend_round2/run_round2.py` | `de667f011d196c8cdbc292bd2a198a82d7b752c899957492fb165b9a15db8f64` |
| Summariser `evaluation/backend_round2/summarise.py` | `4d44a504c89eab8a636f5067879164473f7ac0daf2f1e3b9b6155d13aaa1a8fc` |
| `dataset_inventory.py` | `e1bffc4d1e26ae093dce508cceab9b1c29665da2a2d841e23f89f8e91dea72e0` |
| `observation_cache.py` | `101397bc1f610003bcfcb69312775c516db88e798331f9797a6339dba4f3f972` |
| `structural_probe.py` | `0e8e1abee63827fb3983b9de2daa8542c732b4a608b7b70856569b6c7f8ec603` |
| `field_diagnosis.py` | `88b8b48420d54005c63623808e43d01fd25f5956347690cab17b39f2c801a879` |

No evaluator was edited during P1, so the scorer version is unchanged and P0 to
P1 results are directly comparable.

## Denominator

| Item | Value |
|---|---|
| Files | 7 |
| Unique SHA-256 | 7 |
| Pages | 7 |
| Evaluated fields | 34 |
| All scanned, no embedded text | yes |
| Document types present | 4 of 8 supported |

Frozen before any P1 model output was inspected, and unchanged afterwards.

## Environment

| Item | Value |
|---|---|
| Python | 3.12.14 |
| OS / arch | macOS 26.6.2, arm64 |
| PaddleOCR | 3.2.0 |
| PaddlePaddle | 3.1.1 |
| PaddleX | 3.2.1 |
| PyMuPDF | 1.28.2 |
| Device | CPU only, no GPU |
| OCR models | `PP-OCRv5_mobile_det`, `korean_PP-OCRv5_mobile_rec` |
| Layout model probed | `PP-DocLayout-S` |

Cached models served every OCR run; no model was downloaded during the corpus
runs. `PP-DocLayout-S` was fetched once, for the Architecture C probe only.

## Private dataset integrity

SHA-256, byte size, modification time and permission bits were recorded before
any P1 work and re-verified after. All seven files are unchanged. No file was
renamed, moved, copied into the repository or modified. Every read used
`pathlib` in read mode.
