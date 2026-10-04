# Roadmap

> **Archived 2026-10-04.** Pre-dates the actual Phase 2 mentor-defined
> document domain, P0 backend validation, P1 layout, P2.x OCR/extraction
> work, and this session's Phase A/B safety work. The phase numbering here
> (1A-1D, 2, 3) does not match how the project actually proceeded; kept for
> historical reference only, not as a current plan. See
> `docs/DOCUMENTATION_INDEX.md` for current docs.

## PHASE 1A - Codebase Bootstrap
Monorepo, frontend, backend, DB, migrations, Docker, file upload, mock OCR, PaddleOCR interface, classifier framework, extractor framework, validation framework, dashboard skeleton, tests, docs.

## PHASE 1B - Functional MVP
Collect sample documents, verify PaddleOCR in the deployment image, test Korean OCR, implement real extraction rules, tune classification, confirm fields/rules, connect all pages, test end-to-end.

## PHASE 1C - Accuracy Improvement
Build labeled dataset, measure OCR/classification/extraction accuracy, test scan qualities/templates, improve regex/label extraction, add confidence thresholds and manual review, consider optional LLM extraction.

## PHASE 1D - Evaluation and Delivery
Run final test set, record metrics, compare document formats, document failures, fix critical bugs, polish UI, deploy demo, prepare reports and final presentation.

## PHASE 2 - Document Expansion
Contracts, employment certificates, qualification certificates, other confirmation documents, better layout/template robustness.

## PHASE 3 - Production Hardening
Authentication, RBAC, queues, object storage, encryption, retention, observability, audit controls, CI/CD, scaling, OCR fallback, backup/recovery, security review.

## Questions to Confirm with Flash21
1. Are these four MVP document types final?
2. Can sample documents be provided?
3. Which fields are mandatory for each document type?
4. What exactly constitutes a valid document?
5. Maximum allowed issue-date age?
6. Which certificates have expiration requirements?
7. How should names be matched?
8. How should company names be matched?
9. What should happen when OCR confidence is low?
10. Should users be able to manually correct extracted fields?
11. What retention and access policy is required for uploaded documents containing personal information?
12. Are files allowed to be stored after verification?
13. If yes, for how long?
14. Is authentication required for the demo?
15. Is an admin interface required in the first MVP?
16. Is checklist export required, and in what format?
17. What deployment environment will be used?
18. Is Korean-only UI sufficient?
19. Is English UI also required?
20. What accuracy threshold is considered acceptable?
