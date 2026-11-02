# UCWIT 2026 paper summary

Source for the next midterm deck: `ADVS_UCWIT2026_EN_final_v2.pdf` and matching DOCX in this folder. Counts below are transcribed from the paper without recomputation. The tagged final-results ledger is `evaluation/paper/FINAL_RESULTS_2026-11-03.md` at commit `431aaf1`; it is not present in the `real-docs-v6` tag tree itself. Where it does not report a paper metric, that limitation is stated.

## Title, authors, venue

**Safe Automation of Administrative Document Pre-Checks through Cross-Document Verification**

Munira Olimjonova, Khabibillo Gulomov, Hyunji Lee, and Dongkyun Kim. Venue: UCWIT 2026.

## Abstract summary

ADVS checks Korean administrative documents with OCR, fixed workflow rules, and evidence from other sources. It accepts values automatically only when a separate source supports them, and sends uncertain values to staff. On the paper’s real-document sample, OCR found most correct text but field extraction remained the main source of error. Cross-document checks reduced review burden and enabled automatic decisions for many business submissions, while a student GPA still required confirmation unless entered by the applicant. The evaluation observed no wrong Ready decision on real documents or across the reported synthetic injection cases.

## Three contributions

1. A pre-check design that accepts a value only when an independent source supports it, including cross-document agreement.
2. An evaluation that separates OCR-stage performance from field extraction on real documents and compares the gap with synthetic results.
3. Real-document automation results reported separately for student and business development and validation sets.

## Pipeline and evidence policy

Digital PDFs use their text layer unless it is invisible or disagrees with the rendered page; scans and photos use Korean PP-OCRv5. Poorly read pages are checked in four orientations. Rules classify the document, extract fields by label and position, and check the submission against a versioned workflow checklist.

A high OCR confidence alone does not establish a value. Automatic acceptance requires a separate supporting source, or a decision-robust value for which plausible OCR alternatives would not change the result. If a required value remains unconfirmed, the submission cannot be Ready. Cross-document agreement supports consistency, not authenticity.

The three statuses are **Ready** (no blocking issue in the configured pre-check; not official approval), **Needs correction**, and **Needs review**.

## Dataset (Table 2)

| | Students | Business |
|---|---:|---:|
| Originals | 2 scans and 3 phone photos | 14 files from 2 companies |
| Conditions | 27 per source | 19 |
| Valid submissions | 27 + 27 + 54 = 108 | 19 × 4 + 2 = 78 |
| Development / validation | 81 / 27 | 38 / 38 |
| Never Ready | 14 | 95 |

Student variants use two scanned originals and three fresh phone photos. Business variants use 14 original files. The condition families are scan quality, geometry, photo effects, and file format. The business count includes two multi-page PDFs. Duplicates are excluded from the never-Ready negative count. Variants from a small number of originals are correlated, not independent observations.

The final-results ledger confirms the business valid count and split but does not independently report the paper’s 95 business never-Ready total; keep that number attributed to Table 2.

## Results and locations in the paper

### OCR and extraction

- **Table 3, §5.1:** synthetic development 99.7%; synthetic held-out 1 99.2%.
- **Table 3, §5.1:** real documents, 1,972 fields total: OCR stage 95.8% (95% CI 94.8–96.6%); extraction 79.9% (95% CI 78.1–81.7%).
- **Table 3:** student photo 300 fields (89.7% OCR; 74.3% extraction); student scan 760 (93.7%; 85.4%); business photo 232 (100%; 75.4%); business scan 672 (99.4%; 78.0%). The real total also includes 8 fields not shown in those four rows.
- **§5.1:** business OCR text contained more than 99% of values, while extraction was 75–78%.

The final-results ledger does not reproduce these stage metrics or their row definitions. Keep them attributed to the paper’s Table 3; independent reconciliation against the final-results ledger remains unverified.

### Review causes

- **§5.2:** 2,615 fields were not accepted automatically before the improvements.
- Causes, in paper order: field mapping 38.7%; OCR 26.8%; cross-document comparison 23.2%; safety policy 9.3%; classification 2.0%.

The final-results ledger reports a separate review-category table for valid real submissions by version, not the 2,615-field pre-improvement denominator. It does not independently verify these percentages.

### Automation

- **Abstract, §5.3, Table 4:** business fully automatic 56/78 (71.8%, 95% CI 61.0–80.6%) at the realistic check date; strict expiry-date case 20/78 (25.6%).
- **§5.3, Table 4:** business at most one confirmation 66/78 (84.6%). Each company had 28/38 single-file submissions fully automatic at the realistic check date; the other 2 submissions were multi-page and never Ready. Open items fell 6.9 → 0.63 per submission, averaged over 76 single-file submissions.
- **Abstract, §5.3, Table 4:** student open items fell 8.19 → 3.50; 19/108 (17.6%) needed at most one confirmation, split 17 development and 2 validation.
- **§5.3, Table 4:** typed-GPA upper-bound simulation produced 17/108 (15.7%) fully automatic submissions, split 15 development and 2 validation. A one-digit GPA typo always went to review.
- **§5.3:** with no GPA requirement, 19 submissions became fully automatic. Replayed thresholds from 2.0 to 3.5 did not change the result.

### Safety

- **Abstract, §5.4:** real documents: 0 wrong values accepted and 0 wrong Ready decisions.
- **§5.4:** the rule-of-three upper bound for 0 wrong decisions among 56 automatic business decisions is 5.4%.
- **Evaluation method §4; §5.4:** 6,815 injection cases produced 1 wrong accepted value and 0 wrong Ready decisions.
- **§5.4:** 148 misread values were treated as “safe for the decision”; all decisions were correct, and values stayed unconfirmed.
- **Evaluation method §4; §5.4:** 237 files per PDF manipulation type; no hidden text was read. The paper gives a 1.3% upper bound in §5.4.

## Limitations and future work

The real sample covers one university and two companies, and variants come from a few original documents. Results do not establish performance on other institutions’ layouts. The fresh photos were compressed images; phone captures in the application may behave differently. Applicant-entered GPA results are a simulation using gold values, and GPA thresholds were replayed on development data. Cached OCR was reused in the final stretch. A consistently forged set can share the same error across documents and requires issuer verification.

The paper proposes testing GPA entry with real applicants, accepting electronic certificates, studying issuer verification, comparing ADVS with commercial and learned extractors on shared data, measuring staff time saved, and testing more schools and companies.

## 한국어 요약

ADVS는 OCR, 규칙, 문서 간 근거를 사용해 행정 서류를 사전 점검합니다.
별도 근거가 없는 값은 자동 승인하지 않고 담당자 확인으로 보냅니다.
실제 서류에서는 OCR보다 필드 추출이 더 큰 오류 원인이었습니다.
기업 제출은 78건 중 56건이 자동 처리됐고, 학생의 GPA는 마지막 확인 항목이었습니다.
평가는 소수 원본의 변형에 기반하므로 더 많은 기관과 실제 이용자 검증이 필요합니다.
