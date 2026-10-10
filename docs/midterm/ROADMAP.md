# ADVS — roadmap after the midterm

Status today: working pipeline and review flow on fictional documents; safety measured (see `RESULTS.md`). Not yet real-world ready.

## By the November presentation
- **Finish D3 (internal-consistency automation).** The branch `phase-d3/internal-automation` cuts the decision-blocking review burden on scans (dev: 5.41 → 2.68 fields per scan) but its extended injection suite shows one false 제출 가능 (case E3c-both, hold-out-2 data). It is merged only when its acceptance table passes with 0 false 제출 가능.
- **Reviewer experience.** A fast review screen: all open fields of a submission on one page, original crop beside the value, keyboard confirm, automatic re-check after the last confirmation (today the reviewer clicks 자동 점검 실행 once).
- **Real-document pilot (read-only, counts only).** Run ADVS on a small set of real documents provided by the mentor and report only counts (classified, extracted, needs-human); no content copied into the repository or reports. Closes the "fictional documents" limit.
- **PostgreSQL and concurrency tests.** Run the backend suite and the demo rehearsal against PostgreSQL (Docker Compose); test simultaneous uploads and reviews on one submission.
- Mentor confirmation of the GPA threshold and the student 90-day rule value.

## By December (full working system)
- **Authentication and per-project access** (users see only their own submissions; reviewer and admin roles).
- **Privacy:** no personal data in logs; file retention period and deletion on request.
- **Audit log:** who confirmed or corrected which value, and when.
- **Optional external checks, if the mentor agrees:** National Tax Service business-registration status API; issuance-number verification links for certificates.
- **Admin app:** replace the empty shell with checklist/rule editing and a submissions overview.
- **Full end-to-end scenarios** (browser tests for business and student workflows, scan and digital) in CI.
- **Deployment instructions** (Docker Compose on a server, environment configuration, backup).
