# Dataset / scorer v3 change log

Date: 2026-10-28. Decided by the owner after the real-document findings (student number; cross-document university).
The v2 files (`manifest.json`, `score_v2.py`, `score_d2.py`) are **unchanged**; v3 is added next to them and every
gate is reported under both.

## Changes
| id | scope | change |
|---|---|---|
| v3-1 | all corpora, set S09, **digital** | expected `REVIEW_REQUIRED` + `MISSING_REQUIRED_FIELD (student_id)` -> **`READY`**. Reason: the student-number rule was corrected after the real-document finding: a 재학증명서 that prints no 학번 is satisfied by a 성적증명서 that does (required on at least one document; compared only when both print it; a value on a single document stays unconfirmed unless other evidence exists). S09 scanned and photo expectations are unchanged (`REVIEW_REQUIRED`). The v2 note "must not be borrowed silently" is superseded. |
| v3-2 | dev only, new set **S11** | enrolment (university A) + transcript (university B), same student name and number. Digital: `NEEDS_CORRECTION` (`INFORMATION_MISMATCH` on `university_name`). Scans and photos: `NEEDS_CORRECTION` or `REVIEW_REQUIRED`, never `READY`. Derived from S01 by `_generator/gen_v3_additions.py` (v2 files untouched). Hold-out manifests get no new sets. |
| v3-3 | workflow | the student workflow compares `university_name` between 재학증명서 and 성적증명서 (`value_type = institution`). Generic affixes, letter-spacing and the issuer title are ignored; a one-character difference is routed to review; an error needs both values reliable. **Department is not compared**: the transcript has no `department` field (it prints college, department and major in one line). |

## Files and hashes (sha256)
| corpus | manifest.json (v2) | manifest_v3.json |
|---|---|---|
| test_variants | `e650a96d2b4d441bb3b1647e08afaf04840ebc26dc5d0333ca8c8477aef35f67` | `b386b657d31a890ae908de59f2f1fa56976c597837701c597f37aeac54d3b2fe` |
| holdout | `be0978e25bc26938721c1772809c0158c9d5d86feaccd51ab1a7da47306b5e35` | `ad4b81b1aee1c8dac6138f62fdf121e1ab09df616553ea4385a0538f187407c7` |
| holdout2 | `13f5c9d4da32d8683e74afda6c50b6c0607fbf0cf6162a98d83b48780ca398b0` | `3ba1f594a424bee57f9b273881d2df15ad10346ca464f97b8c46805b101ba96f` |
| holdout3 | `8ca71d5e6d152dc7f15e4c39024aa43d3e73da16935f024232ab387c1b939a6d` | `f875323ce8f3dd2e5005656ce7fad05d4bd8fd75b5812967c664b3585cdb662d` |

Scorer v3 = `evaluation/harness/score_d3_v3.py` (sha256 `f730c5b5f1322c0323f388c8fc745a3ea74a1a7e8f5e5232db9ad796b27f9737`): `score_v2.py` (sha256 `49674a9c03e464310cda0278782062e1a4b996e334ff8d8cbdc78d10b5ad2594`, unchanged) with the v3 manifests.
Metrics and equality rules are identical; only the expectations differ.

## Not changed
Injection suites E1-E18 run on the v2 manifests (S11 is not part of them). Scoring of the real-document and variant runs does not use these manifests.
