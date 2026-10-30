# Business documents — real-document test (mentor's files)

Masked report: counts and rates only. No document text, company names, numbers, document dates or images are in this file. Per-file detail is in `data/private_real/business/` (git-ignored).

## 1. Setup

- 14 original files (2 companies; 3 certificate types plus one look-alike type, 지방세) → 268 files (G0 original, G1 scan 200 dpi, G2 scan quality, G3 geometry, G3b known limit 90°/180°, G4 photo style, G5 formats). Gold values confirmed by the owner (2026-10-31). Printed validity dates of the look-alike certificate are recorded as observations, not scored.
- 202 submissions: 19 recipes × valid P1–P4 and negative N1–N6 on the **reduced checklist (b)** (standard checklist without 중소기업확인서); G0 also on the **standard checklist (a)**; 2 multi-page files judged by status only.
- Check date 2026-11-02. Each commit run once: frozen `45f1e30` (`real-docs-freeze-3`) and baseline `1018406` (main), separate worktrees, outputs and caches; OCR once per distinct file (`--memo-ocr`). In addition the 14 G0 originals each alone on both commits (document-type results).
- Company-name normalisation (legal form, parenthesised Latin, spaces) is used **for field scoring only**. Statuses are exactly as the system produced them.

## 2. Frozen vs baseline

**Identical.** Every group, status and field outcome is the same on both commits (compared after removing ids and timings). The fixes between baseline and freeze concern student documents; they neither help nor hurt these business documents. The two runs are one result, not two independent ones. Frozen run time 4855 s.

## 3. Results

### 3.1 G0 original files, digital and scan separately

| group | type correct | fields correct | auto-accepted (correct) | correct, sent to a person | not read |
|---|---|---|---|---|---|
| G0 digital (text layer) | 7/7 (Wilson 64.6–100) | 26/32 = 81.3% (64.7–91.1) | 17/32 | 9/32 | 6/32 |
| G0 scan | 3/4 (30.1–95.4) | 14/16 = 87.5% (64.0–96.5) | 6/16 | 8/16 | 2/16 |

Wrong values: 0 accepted, 0 caught. The README says 8 digital / 6 scan; the files' text layers give 9 / 5 — the groups follow the measured text layers (the table counts the 14 originals in the two groups as scored, look-alike files excluded from fields).

### 3.2 Variants (correlated: 14 sources, 2 companies — intervals indicative only)

| group | type | fields correct | auto-accepted | to a person | not read | wrong caught | wrong accepted |
|---|---|---|---|---|---|---|---|
| G1 scan 200 dpi | 20/22 | 78/96 (81.3%) | 38 | 40 | 18 | 0 | 0 |
| G2 scan quality | 50/55 | 184/240 (76.7%) | 85 | 99 | 54 | 2 | 0 |
| G3 geometry | 40/44 | 146/192 (76.0%) | 60 | 86 | 46 | 0 | 0 |
| G3b 90°/180° (known limit) | 20/22 | 76/96 (79.2%) | 28 | 48 | 20 | 0 | 0 |
| G4 photo style | 40/44 | 141/192 (73.4%) | 67 | 74 | 51 | 0 | 0 |
| G5 formats | 10/11 | 37/48 (77.1%) | 18 | 19 | 11 | 0 | 0 |

All scored fields (G0 + variants): 319 correct auto-accepted, 383 correct sent to a person, 208 not read, 2 wrong caught, 0 wrong accepted. Not read: `issue_date` 152 of 208, business registration number 27, representative 20, workplace name 4, company name 4, valid-until 1. (Observation only; no tuning on business data.)

### 3.3 Safety

- Wrong value auto-accepted: **0 of 319** accepted fields (rule-of-three upper bound 0.9%).
- Wrong 제출 가능 (READY): **0 of 192** submissions (upper bound 1.6%). In fact **no submission was READY at all** (3.5).
- 2 wrong values were caught (sent to a person), both in G2.

### 3.4 Negatives N1–N6 (reduced checklist: 114 submissions; standard: 6)

| case | meaning | reduced (b) | standard (a) |
|---|---|---|---|
| N1 | national-tax certificate on its last valid day (check date 2026-11-02) | 19/19 REVIEW_REQUIRED | NEEDS_CORRECTION |
| N2 | old social-insurance certificate | 19/19 REVIEW_REQUIRED, no expiry code | NEEDS_CORRECTION |
| N3 | company / number mismatch | 19/19 REVIEW_REQUIRED | NEEDS_CORRECTION |
| N4 | 지방세 in place of 국세 | 19/19 REVIEW_REQUIRED (classification-review code on every one) | NEEDS_CORRECTION |
| N5 | duplicate upload | 19/19 REVIEW_REQUIRED, no duplicate indication in the verification output | NEEDS_CORRECTION |
| N6 | national-tax certificate long expired | 16/19 NEEDS_CORRECTION with the expiry code; 3 REVIEW_REQUIRED | NEEDS_CORRECTION |

Never READY: 0/114 (upper bound 2.6%). But N1–N5 are **not distinguishable from valid submissions**, which end in the same status (3.5). Only N6 (clear expiry) is reported specifically.

Look-alike (지방세): in the submissions it was typed as 국세 in 19/19 files; the N4 submissions still reach review through a classification-review code. In the single-file run 2 of 4 look-alike originals were flagged for review and **2 of 4 were typed as national-tax certificate without any review flag.** Nothing reached READY, but the classifier alone does not separate these two document types. Finding for the paper and the admin checklist.

### 3.5 Checklist (b) vs (a); valid submissions

| | valid P1–P4 (G0) | negatives (G0) |
|---|---|---|
| (a) standard | 4/4 NEEDS_CORRECTION (missing 중소기업확인서, expected) | 6/6 NEEDS_CORRECTION |
| (b) without 중소기업확인서 | 4/4 REVIEW_REQUIRED | 5 REVIEW_REQUIRED, 1 NEEDS_CORRECTION |

All 76 valid variant submissions on (b): **0 READY, 76 REVIEW_REQUIRED.** Removing the 중소기업확인서 item made the status honest (a person reviews instead of "missing document") but did not enable automation; the blockers are in the documents (not-read `issue_date`, company-name notation, no independent confirmation).

### 3.6 Single files (document type, each original alone, both commits)

10/10 of the 국세 / 4대보험 / 사업자등록증 originals typed correctly. Look-alike originals: see 3.4. Every single-file submission ends NEEDS_CORRECTION (other required documents missing), as expected.

## 4. Company-name notation findings (for the admin checklist editor)

47 of 192 submissions contain cross-document company-name comparisons (company name, and workplace name on the insurance certificate) that went to review or stayed unresolved: 82 as OCR-uncertain, 5 as required-field-unresolved (G0: 8 items). All end in REVIEW_REQUIRED, none worse.

Notation patterns in the files (from masked lengths and the owner's examples): a legal-form prefix with or without a space; a long name with parenthesised Latin text on one certificate and a short transliteration on another; the insurance certificate's workplace name being a shorter form of the registration name. Normalisation settings worth offering in the editor: strip legal form (주식회사 / (주)), ignore spaces, ignore parenthesised Latin, optional alias list per applicant.

Caveat: the system does not state why an item went to review and I did not investigate (business results stay out of the accuracy work), so notation is a likely, not proven, cause.

## 5. For the paper

- Safety held on the mentor's real business documents: 0 wrong auto-accepted of 319, 0 false READY of 192, 0 of 114 negatives READY (2 companies, 14 originals; variants correlated).
- Business documents are **not automated yet**: 0/76 valid submissions READY. Causes: unread `issue_date`, company-name notation, and the policy that an unconfirmed value goes to a person.
- Negative detection is coarse: only clear expiry (N6) is reported specifically; mismatch, duplicate, old insurance certificate and look-alike end in the same status as a valid submission.
- The accuracy fixes made on student documents have no effect, positive or negative, on this set (identical on both commits). This set has not influenced the fixes.
- Limits: 2 companies, one issuer format per type, variants derived from 14 files, one check date, N1 sits on a boundary day.

## 6. Not done

- No business result was used for code changes. The generalisation run (accuracy fixes frozen, run once more) waits for the owner's signal. Nothing merged or pushed.
