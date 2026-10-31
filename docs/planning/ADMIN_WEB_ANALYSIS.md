# ADVS — Admin + Web analysis and design decisions

Status: analysis only (2026-10-31). No code was changed. Written in a read-only worktree of `main` (`1018406`); nothing is committed.
Evidence is cited as `file:line` on `main` unless it says `research/real-docs`. The owner's real-document test was running while this was written and was not touched.

Contents: 1 Summary · 2 Current state · 3 Decisions A–I · 4 Risks · 5 Open questions.

---

## 1. Summary

1. **The rules are already stored in the database, but they cannot be edited safely.** `Checklist → DocumentRequirement → ValidationRule(rule_type, severity, params JSON)` exists (`models/entities.py:54-86`), and the engine validates the params (`submission.py:241-286`). What is missing is: any API to edit requirements or rules (only `POST/PATCH /checklists` for name and description, `routes.py:311-340`), versioning, and an admin UI. Today the only way to change a rule is to edit `scripts/seed.py` and re-run it, and that **rewrites the rules in place and invalidates every project's result** (`seed.py:38-55`).
2. **Roughly half of "what is checked" is not data.** Default required fields (`services/requirements.py:17-53`), the expected-field lists (`core/domain.py:75-128`), the match of the submitter's own name/company (`submission.py:576-630`), the implicit `valid_until` check (`submission.py:632-660`), the duplicate policy (`submission.py:430-500`), the look-alike title table (`classifier.py:162-166`), the GPA scale list (`auto_acceptance.py:211`) and the student-number "on at least one document" rule (`research/real-docs` `fe569a2`) are code. Some of these must stay code (safety invariants); some should become configuration.
3. **There is no authentication anywhere.** Every endpoint is open, including `DELETE /projects/{id}`, `POST /documents/{id}/process`, field review, and `GET /projects` (lists everyone's submissions). Rule editing must not go live before login and roles.
4. **Two existing defects matter for the design, not only for the UI:**
   - the **applicant can change the 점검 기준일** to any date (`StatusBanner.tsx:96-121`, `VerificationRequest` has no bound, `schemas/api.py:244`), so an applicant can make an expired 납세증명서 pass → a path to a false 제출 가능;
   - **applicants confirm their own OCR values** in the applicant app (`ReviewPanel.tsx`), and doing so can turn the status into 제출 가능 (`evaluation/phase_e2/UX_AUDIT.md` UX-1). The "human review" is the applicant.
5. **Latent bug in the seed:** both student workflows contain `issue_date ON_OR_BEFORE 2026-12-31` (`seed.py:196-201, 221-224`). From 2027-01-01 every student submission fails. It is redundant with `ISSUE_DATE_MAX_AGE`, whose upper bound is the check date (`submission.py:676-690`).
6. **The admin app is a placeholder** (five stub pages, no API client, no tests; `apps/admin/src/app/*/page.tsx`).

**Recommendations in one line each** (details in §3):

| | Recommendation |
|---|---|
| A | Keep two apps (web + admin); extract an API client, Korean copy and more UI components into shared packages. The security boundary is the backend, not the app split. |
| B | Hybrid rule model: a **versioned, immutable JSON checklist document** validated by a strict pydantic schema, compiled into the engine's existing `RequirementSnapshot`s; relational shell for workflow/version/status. Today's behaviour becomes version 1. |
| C | Draft → publish; every project **pins** a checklist version; publish never touches old results; re-check is an explicit action. Impact preview by **replaying stored field snapshots** (no OCR), feasible in seconds. Audit = immutable versions + AuditLog events; rollback = publish an old version as a new one. |
| D | Seeded staff accounts (reviewer, admin), argon2 password hashes, HttpOnly session cookie + CSRF header, role checks on every non-applicant endpoint. Applicants get an unguessable per-submission link (no accounts yet). **Must exist before rule editing.** |
| E | Eight admin screens, plain-Korean rule sentences rendered by the backend. |
| F | Applicant app shows only checklist, fixable problems and overall status; OCR values, confidence and confirm buttons move to the admin reviewer screen; check date set by the server. |
| G | Grow `packages/ui` (tokens preset + table, form, dialog, tabs, diff); no new UI framework. |
| H | Phase plan to 11/19 (auth, schema+versioning, editor) and 12/10 (queue, preview, audit, applicant trim). |
| I | Real-document plan in `REAL_DOCUMENT_TEST_PLAN.md` (Korean, for the mentor). |

---

## 2. Current state

### 2.1 Backend rules

**Where checklists are defined.** Only in `scripts/seed.py`: `upsert_workflow` (`:24-55`), `comparison_rule` (`:58`), `student_identity_rule` (`:79`), `validity_rule` (`:97`), and `main()` (`:112-259`). Two workflows: 기업 제출서류 점검 and 학생 제출서류 점검. On `research/real-docs` the student workflow additionally compares `university_name` (`a9ff8c7`, `value_type: institution`); that branch is not merged.

**Rule types.** `core/domain.py:35-48` lists 13; the submission engine supports four (`services/verification.py:203-209`): `FIELD_COMPARISON`, `DATE_COMPARISON`, `NUMERIC_COMPARISON`, `ISSUE_DATE_MAX_AGE`. `DATE_NOT_EXPIRED` is rewritten to a `DATE_COMPARISON` against the check date (`:223-231`). `REQUIRED_FIELD` adds to defaults (`requirements.py:56-68`). Any other persisted rule type raises `RuleConfigurationError` instead of silently passing (`verification.py:250-257`) — a good property to keep.

| What | Where | Data or code? |
|---|---|---|
| Document required/optional | `DocumentRequirement.required` (`entities.py:70`) | **data** |
| Field comparison (EQUALS, `string`/`identifier`; `institution` on research branch) | rule row, `submission.py:296-306`, `:692-780` | **data** (value types are code) |
| Date comparison vs fixed date or check date | rule row, `submission.py:308-336` | **data** |
| Issue-date max age (default 90, 0–36500) | rule row, `submission.py:270-282, 674-690` | **data** |
| Numeric threshold (GPA ≥ 3.0) | rule row, `submission.py:854-918`, `seed.py:225-234` | **data**; **no scale handling**: the rule compares the raw GPA, so 3.4/4.3 and 3.62/4.5 are both compared with 3.0 |
| Severity → status (ERROR → 보완 필요, other → 확인 필요) | `submission.py:140-146` | code |
| Reliability policy (a missing/unconfirmed value is UNRESOLVED → review, never a failure) | `_unresolved_field`, `submission.py:920-` | **code, must stay** |
| Default required fields per type | `requirements.py:17-53` | code |
| Expected / reviewable fields per type | `domain.py:75-164` | code |
| Submitter name/company match (entered by the applicant on the project) | `submission.py:576-630` | code, always on |
| Implicit `valid_until` ≥ check date for required docs | `submission.py:632-660` | code, always on |
| Duplicate policy (identical → notice; different → review; conflicting reviews → review) | `submission.py:430-500` | code |
| Uncertain classification / multi-document file / hidden-text mismatch → review | `submission.py:380-410` | code, must stay |
| Look-alike titles (지방세납세증명서, 휴학증명서, 졸업예정증명서 → UNKNOWN + review) | `classifier.py:162-166` | code, must stay |
| GPA scales 4 / 4.3 / 4.5; GPA ≤ scale check | `auto_acceptance.py:211, 410-420` | code |
| Student number required on one document of the submission | `research/real-docs` `fe569a2` (`SUBMISSION_WIDE_FIELDS`) | code |
| Auto-accept policy (confidence floor 0.90, evidence sufficiency) | `auto_acceptance.py:72, 159, 177`; `evidence_sufficiency.py:7` | code, versioned strings |

**Workflow ↔ submission.** `Project.checklist_id` is a mutable foreign key (`entities.py:43`). There is no version. `seed.py:46` does `workflow.requirements.clear()` and recreates the rows, so rule ids change and `ValidationResult.details.rule_id` (`verification.py:395`) dangles; then `invalidate_submission_verification` runs for every project of the workflow (`seed.py:40-44`). **"Publishing silently changes past results" is today's behaviour.** The stored input snapshot is a hash (`verification.py:347-371`), which does detect staleness but cannot say which rules were used.

**Statuses.** The backend computes everything: `aggregate_status` (`submission.py:148-153`) → NEEDS_CORRECTION > REVIEW_REQUIRED > READY. The web only lays out API values (`ProjectWorkspacePage.tsx` header comment; E2E "every screen shows exactly what the API decided").

### 2.2 Data model and API

Tables (`entities.py`): `users` (email, display_name; **no password, no role**), `projects`, `checklists`, `document_requirements`, `validation_rules`, `submissions`, `documents`, `ocr_results`, `extracted_fields`, `field_reviews` (reviewer_label is free text, `:172`), `validation_results`, `audit_logs` (event_name, actor_id, metadata). SQLite by default (`config.py:11`), PostgreSQL JSONB variant already in the types (`entities.py:22`), Alembic present (`apps/api/alembic`).

Endpoints (`api/v1/routes.py`): health; projects CRUD; workflows read; checklists create/read/update-name; upload; document read/process/pages; `verify`, `verification`, `verification-history`; `review-items`, `overview`, `project-summaries`; `upload-rules`; field `review`. OpenAPI types are generated into `packages/contracts/src/openapi.ts` (2,021 lines) and the web already derives its types from it (`apps/web/src/types/api.ts:1-9`).

### 2.3 Apps

- **`apps/web`** (applicant, :3000): Next 15, React 19, TanStack Query, react-hook-form + zod, Tailwind; ~8,300 lines including tests. Screens: projects list, new project, workspace (banner, requirement checklist, issues, review panel, upload), document detail with evidence. 109 unit tests and 15 Playwright tests including axe (`PHASE_E2_REPORT.md:43-45`: 0 serious/critical violations on 7 screens at desktop width and 3 at 390 px).
- **`apps/admin`** (:3002): placeholder. Dashboard with five links; `checklists`, `rules`, `document-types`, `projects`, `history` pages are a heading and one sentence. Depends only on `@advs/ui`; no data fetching, no tests (`package.json` "test" echoes a message).
- **Shared:** `packages/ui` has three components (`button`, `card`, `status-badge`); `packages/contracts` is the generated OpenAPI types; `packages/eslint-config`. The web app keeps its own `components/` (`page-state`, `status-chip`, `app-header`), `lib/copy.ts` (350 lines of Korean issue/fix text), `lib/presentation.ts` (480 lines of labels), `lib/api-client.ts` and `queries.ts`. **None of this can be reused by the admin app today.**
- **Review screen** lives in the applicant app (`features/reviews/ReviewPanel.tsx`, 288 lines; `DocumentDetailPage.tsx`, 372 lines).
- **Reference material on the Desktop:** `ADVS_fresh_real_2026-10-30` (owner's fresh set: 80 files, seed 20261030), `ADVS_mentor_business_real_PRIVATE` (mentor's 14 documents + 268-file variant set, seed 20261031), `실제서류` (the 14 mentor files as received). All three are private real documents; only their README/manifest structure was read, no values were copied here. `khabibillo` is the owner's separate portfolio project (a NestJS admin plane); it is not ADVS and was not used.
  One fact from the mentor set's README matters for this feature: *"No 중소기업확인서 is included: with the standard business checklist every submission is 보완 필요 for that reason — also run with a checklist without it, if configurable."* That is the mentor's requirement #1 in practice.

### 2.4 Security

- No authentication or authorization in the API (`grep` for `Depends` shows only `get_db`; `docs/domains/admin.md` says "must be resolved before production use").
- Open today: `GET /projects`, `/project-summaries` (everyone's names and companies), `DELETE /projects/{id}` (`routes.py:270`), `POST /checklists` and `PATCH /checklists/{id}` (`:311, :328`), `POST …/review` with a free-text `reviewer_label` (`:651`), `POST /verify` with any date (`:518`).
- CORS allows `localhost:3000` and `:3002` (`config.py:25`); no credentials flow exists yet.
- **Risk of adding rule editing without auth:** anyone who can reach the API could disable comparisons or the issue-date rule and obtain 제출 가능 for any submission. This breaks the 0-false-제출-가능gate outright. It is a **blocker**, not a hardening item.
- Real documents are now processed; `GET /projects` listing all submitters is a privacy exposure even before rule editing.

### 2.5 UX audit (applicant and review)

Existing audit: `evaluation/phase_e2/UX_AUDIT.md` (21 findings; 17 fixed in Part A; UX-19/20/21 — admin app, reviewer queue, history — were deferred to "Part B"). What works: status banner with one sentence and next step, issues grouped once with "what / where / how to fix / 근거 보기", progress "3 / 7 완료", keyboard review (Enter/Esc), per-row upload, cause-specific upload errors, no raw enums, no overflow at 390 px.

What still confuses or is risky (new findings, with evidence):

| # | Finding | Evidence |
|---|---|---|
| N1 | **Applicant can change the check date** to any date and re-check | `StatusBanner.tsx:96-121`; no bound in `schemas/api.py:244` |
| N2 | **Applicant confirms their own values**; this can produce 제출 가능 | `ReviewPanel.tsx`; `UX_AUDIT` UX-1/E2E D6 |
| N3 | Applicant sees OCR values, confidence, evidence crops, auto-accept reasons (`autoAcceptReasonLabel`, `formatPercent`) — internal detail | `ReviewPanel.tsx:3-20`, `DocumentDetailPage.tsx` |
| N4 | iPhone photos are rejected as "corrupt": Pillow reports MPO, the upload check requires `format == "JPEG"` and one frame | `storage/local.py:154-163`; reproduced on a real photo; message `copy.ts:341` tells the user the file is damaged |
| N5 | "Unsupported format" and "corrupt file" use two codes in the API but the web copy cannot tell a supported-but-unreadable photo apart | `copy.ts:335-342` |
| N6 | `.heic` is not in the allow-list; iOS usually converts to JPEG on upload from the picker but a file picked from Files may stay HEIC | `UploadRulesRead`, `routes.py:602`; untested |
| N7 | Applicant must type 제출자 이름 and 회사명 on project creation; these then act as a ground truth the documents are compared against (`APPLICANT_NAME_MATCH`) — a typo by the applicant yields 보완 필요 on a correct document | `NewProjectPage.tsx:25-26`, `submission.py:576-630` |
| N8 | The disclaimer is good but the status word 확인 필요 conflates "your action needed" and "staff will look"; the applicant cannot tell which | `StatusBanner.tsx`, `copy.ts` |

Accessibility: axe shows 0 serious/critical on the applicant screens; the admin app has never been measured. Korean wording is plain and consistent in the applicant app; the admin copy consists of English-flavoured jargon in stubs ("결정적 규칙", "Phase 1B").

---

## 3. Decisions

For each: options → pros/cons → recommendation → why.

### A. App structure

| Option | Pros | Cons |
|---|---|---|
| **A1. Two apps + shared packages** (today's layout, filled in) | Admin can be deployed internal-only and never ships to applicants; separate bundles; separate session cookie scope; already scaffolded (`apps/admin`, ports 3000/3002, `Dockerfile` for each); clear ownership of screens | Needs extraction work: API client, copy, UI components currently live in `apps/web`; two deploys |
| **A2. One app, role-based routes** | One build, zero duplication, single login page | Admin code is served to everyone (not a vulnerability if the API enforces roles, but a larger public surface and leaks the rule schema); one deployment cannot be made internal-only; applicant and staff share cookie scope on the same origin; one failing admin screen can break the applicant build |
| A3. Admin as a Next.js BFF (server-side session, API token never in the browser) | Strongest browser-side security | More moving parts than a one-developer frontend should carry now |

**Recommend A1.** The decisive point is that the real boundary is the API's role check either way; given that, the split buys an internal-only deployment and a smaller applicant bundle at the price of extraction work that is needed anyway (the reviewer screen must be moved). Extract in this order: `packages/api-client` (fetch wrapper + error mapping from `lib/api-client.ts`, `api-error.ts`), `packages/copy` (issue/fix text, field and document labels), then UI components. A2 would be the right answer if the team were adding no staff-only deployment requirement; A3 is a later hardening if the admin goes on the public internet.

### B. Rule model

| Option | Pros | Cons |
|---|---|---|
| **B1. JSON rule document per checklist version, strict pydantic schema** | Whole checklist is one immutable value: trivial to version, diff, hash, export, replay and roll back; schema is the single source for validation and for the admin form; the same JSON works on SQLite and PostgreSQL (JSONB already used) | No per-rule SQL queries (rarely needed); schema evolution needs explicit migrations of stored documents |
| B2. Relational tables per rule type | Queryable; DB-level constraints | Many tables for 4–6 rule types; versioning means copying many rows; diff is awkward; each new rule type = a migration; today's `validation_rules.params` already shows the pressure to put typed data in JSON |
| **B3. Hybrid: relational shell + JSON version document** | Keeps FK integrity where it matters (workflow, version, project pin, audit) and immutability where it pays (the document) | Two things to keep consistent (shell vs document) |
| B4. Keep today's rows, add `version` column | Smallest change | Row-level versioning of a rule tree is error-prone; diffs must be reconstructed; nothing enforces that a published tree is complete |

**Recommend B3** (JSON document, relational shell). Evidence for the choice: the engine already consumes an in-memory tree (`RequirementSnapshot`/`SubmissionRule`, `submission.py:83-99`) and the loader is the only place that touches rows (`verification.py:202-264`) — so the document can be **compiled to the same snapshots** and the engine stays untouched. The engine already validates configuration (`validate_configuration`, `submission.py:241`), but only at verify time (errors are raised on `/verify`, `verification.py:107-112`); with a schema the same errors are caught at **save** time. "Keep what we have" (B4) is weighed fairly: it works for one frozen version but gives no atomic publish, no pin and no diff, which are the points of the mentor's request.

What stays in code on purpose (not editable): reliability policy, look-alike table, classification review, multi-document handling, extraction and auto-accept policy. The editor chooses *what must hold* and *how severe a failure is*; it cannot change *when a value is trustworthy enough to be judged*. This is what keeps the 0-false-제출-가능 gate meaningful.

### C. Versioning, guardrails, preview, audit

**C1. Draft → publish and pinning.** A workflow has at most one **draft** and one **published** version; publishing creates version *n+1* (immutable). A project records `checklist_version_id` at creation and every verification records the version it used. Options for existing projects when a version is published: (i) keep pinned, re-check explicitly ("현재 기준으로 다시 점검") — **recommended**; (ii) auto-migrate — rejected: silently changes past results, the property the owner ruled out. Cost: UI must show "점검 기준 버전 3 (최신: 4)".

**C2. Guardrails** (enforced in the schema or warned in the editor; each error is a save-time 400, each warning needs an explicit tick-box before publish):

| Guardrail | Level |
|---|---|
| Max age < 1 or > 365 days (0 allowed by the engine today: `submission.py:278`) | block (<1), warn (>180), block (>365) |
| Required document with no field comparison and no validity or issue-date rule | warn |
| All identity comparisons removed (student: name, 학번; business: BRN, company name) | **block** |
| Comparison severity set to a level below ERROR for BRN or 학번 | warn |
| Required document removed that has comparisons depending on it | block (engine already rejects, `submission.py:287-292`) |
| `fixed date` check-date policy | warn (creates stale-by-design checks) |
| A threshold without a scale when the document type carries a scale | block |
| Anything that would make the published version's **impact preview** show a new 제출 가능 on a corpus case that expects not-ready | **block** until acknowledged by an admin with a reason |

**C3. Impact preview.** Feasible and fast, because the verification engine is a pure function over persisted canonical fields ("The engine never reads files or OCR text", `submission.py:182-190`) and the stored snapshot already contains the full `documents` input (`verification.py:347-362`, minus PII). Design: keep a **replay corpus** of field snapshots (JSON), produced once per extractor version by the existing evaluation harnesses (the fictional sets E1–E18 and holdouts are non-private; real-document snapshots stay under `data/private_real/` and are only usable on the owner's machine). The preview runs `engine.verify` for each case with the draft and the published rules and lists cases whose **status** or **issue codes** change, with the corpus' expected outcome beside them. Cost: pure-Python per case; I estimate well under a second per 1,000 cases but have **not measured it** (no OCR or heavy runs were allowed); measure in phase P2. Limits, stated in the UI: it covers rule changes only, not extractor or auto-accept changes, and a real-document corpus is not available in a deployed server.

**C4. Audit and rollback.** Versions are immutable and carry author, timestamp and a mandatory change note; a diff is computed from two JSON documents. Publish, rollback, login, failed login and review actions are written to the existing `audit_logs` table (needs a `workflow_id` column or `metadata_json`). Rollback = publish an older document as a new version (history stays linear).

### D. Roles and authentication (minimum safe)

| Option | Pros | Cons |
|---|---|---|
| **D1. Seeded staff accounts, argon2 hash, server-side session in an HttpOnly cookie, CSRF header, roles `reviewer`/`admin`** | Standard, revocable, no token in JS; small: add `password_hash`, `role`, `is_active` to `users` | Cookies are shared across ports on `localhost` (use distinct cookie names, e.g. `advs_staff`); needs same-site deployment or proper CORS-with-credentials |
| D2. JWT bearer kept in memory/localStorage | Simple for SPAs | Hard to revoke; XSS exposure if stored; refresh logic |
| D3. Reverse-proxy authentication (basic auth / SSO / IP allow-list) in front of the admin app and `/admin/*` API paths | Zero app code | Not auditable per user; no roles inside the app; easy to misconfigure; does not protect the API if reachable directly |
| D4. Applicant accounts too | Proper ownership | Much more scope; not required for the pre-check scenario |

**Recommend D1 for staff plus unguessable per-submission links for applicants.** Applicants today need no account; what they need is that nobody else can list or open their submission. Replace `GET /projects` for applicants by a capability URL (random 128-bit token stored hashed on the project); the list endpoints become staff-only. This is the smallest change that closes the privacy hole without inventing accounts.

**Must exist before rule editing goes live:** (1) login with hashed passwords and lockout/rate-limit; (2) role checks on every write and every staff read, including the currently open `/checklists` writes and `DELETE /projects`; (3) check-date control moved to staff (N1); (4) AuditLog entries with the actor for publish/rollback/review; (5) CORS limited to the known origins with credentials; (6) HTTPS and `Secure` cookies in any shared deployment. Review decisions use the authenticated user instead of the free-text `reviewer_label`.

### E. Admin information architecture and UX

Screens (wireframes in `ADMIN_WEB_DESIGN.md` §7): 로그인; 업무(워크플로) 목록; 업무 편집 (tabs 서류 / 문서 간 비교 / 기준값 / 점검 기준일); 버전 이력과 비교; 변경 영향 미리보기; 검토 대기열; 검토 화면; 변경 기록. Rules are shown as **sentences generated by the backend** from the schema (single source; the UI does not interpret rule semantics, matching the project principle that the UI never decides): e.g. "국세 납세증명서는 점검 기준일에 유효기간이 지나지 않아야 합니다 (위반 시 보완 필요)". Options considered for rule editing: (1) form per rule kind with plain-Korean labels — **recommended**; (2) raw JSON editor — rejected for ordinary admins, but kept as a read-only "JSON 보기" for diffs; (3) rule-builder canvas — over-built for 5 rule kinds.

### F. Applicant web UX

Applicants should see: the checklist (제출됨 / 미제출 per slot), problems they can fix with the reason and how, an overall status (제출 가능 / 보완 필요 / 담당자 확인 중), then the final result. Remove OCR values, confidences, evidence crops, auto-accept reasons and the confirm buttons from the applicant app (N2, N3); the applicant's check date becomes server-set (N1).

Two real options for *who confirms an uncertain value* — an owner decision:

| Option | Pros | Cons |
|---|---|---|
| F1. Keep applicant self-confirmation (today) | Fast, no staff needed; works as a pre-check tool | The interested party certifies their own document values; can reach 제출 가능 without any independent look (N2) |
| **F2. Staff-only confirmation; applicant sees 담당자 확인 중** | Matches "uncertain → human review" and the 0-false gate; removes the OCR detail from the applicant UI | Needs reviewers; turnaround; every real scan today ends REVIEW_REQUIRED (seed B: 34/34), so the queue would receive every submission |
| F3. F2 plus **applicant-declared values** (학번; GPA with an explicit scale) used as *independent evidence of the reading* | Catches the real failure mode (an OCR digit error) with a second channel; reduces staff load when applicant value = OCR value; also answers the scale ambiguity (4.3 vs 4.5) by asking | The declaration is not proof of authenticity (state it in the UI and policy); changes the evidence policy (`evidence-policy-v3`) and needs the real-document test again |

**Recommend F2 now, F3 as a later phase after the policy change is tested.** Reason: today's measured behaviour on real scans is "safe by abstaining" (0 wrong auto-accepts, 0 false READY, 100% REVIEW_REQUIRED on both seeds), so the reviewer queue is not an edge case, it is the main path — and it belongs in the admin app. F1 stays valid for the demo/pre-check positioning if the owner prefers; it must then at least stop showing confidence figures and be labelled "내가 확인함".

Upload fixes (all N4–N6): accept MPO and use the primary frame, strip GPS/EXIF from stored and derived images, separate "지원하지 않는 형식" from "파일이 손상됨" (detailed in the separate task `fix/phone-photo-upload`). HEIC: decide after testing the iOS picker (open question 7). The per-slot upload button bug is already fixed on main (`1018406`).

### G. Design system

| Option | Pros | Cons |
|---|---|---|
| G1. Keep as is (web owns its components; admin copies) | No work now | Divergence; the admin cannot reuse tested components |
| **G2. Grow `packages/ui`: tokens as a Tailwind preset, move `page-state`, `status-chip`, add `data-table`, `form-field`, `dialog`, `tabs`, `diff-view`** | One look; shared tests; one frontend developer maintains one set | Moves code Munira owns; needs a migration pass on the web app |
| G3. Adopt a component framework (shadcn/Radix, MUI) | Faster tables/dialogs, accessible primitives | New dependency surface and visual change right before a midterm |

**Recommend G2**, adding Radix primitives only for dialog/tabs/select if hand-rolled versions fail axe (decision at implementation time). Accessibility targets: axe 0 serious/critical on every admin screen (the web already meets this), full keyboard operation of the editor and review queue, contrast ≥ AA on every status colour (including dark text on amber), a visible focus ring (the web already uses `focus-visible:ring-2`), forms with associated labels and errors announced (`role="alert"`).

### H. Phasing

See `ADMIN_WEB_DESIGN.md` §9: P0 finish tests + upload fix (owner); P1 auth and lock-down; P2 schema + versioning + compile + v1 equivalence; P3 admin shell + editor + publish; P4 reviewer queue move, impact preview, audit/rollback; P5 applicant trim and optional declared values. Target for the **11/19 midterm**: P1–P3 minimal (edit and publish the issue-date age, required/optional, comparison on/off and severity, GPA threshold; new project uses the new version, old one is untouched). Target for **12/10**: P4 and P5 plus the real-document verification of every rule change.

### I. Real-document test plan

`REAL_DOCUMENT_TEST_PLAN.md` (Korean, for the mentor). The checklist feature is tested against both sets: each rule change is replayed on the fictional corpus (preview) and the owner's/mentor's real sets (locally), and a final one-time run on frozen code is repeated for any change that touches evidence policy.

---

## 4. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Rule editing shipped before auth | Anyone can weaken checks → false 제출 가능 | Phase gate: no editor endpoint without roles (D) |
| Admin edits weaken a safety property | False 제출 가능 | Guardrails (C2), preview with expected outcomes, reliability policy in code only |
| Equivalence of v1 with today's behaviour | Silent behaviour change | Golden test: compiled v1 == rows loaded by `_requirements()`; fictional sets v2/v3 and real pair field-level diff 0 |
| Schema drift (research branch adds `institution` value type and a code rule for 학번) | v1 defined on the wrong base | Define v1 on the merged `research/real-docs` head, after the owner's merge OK |
| Frontend capacity (one developer) | Midterm slips | Cut P4 preview/audit UI to December; ship editor with a text diff |
| Session cookies across localhost ports | Dev confusion, accidental session sharing | Distinct cookie names; document in `development.md` |
| Time bomb `2026-12-31` | All student checks fail from 2027-01-01 | Remove with v1 (redundant with `ISSUE_DATE_MAX_AGE`); needs the owner's OK because it changes seed behaviour |
| Evidence-policy change (F3) | Alters auto-accept behaviour | Separate approval, new policy version, full real-doc re-test, never combined with the editor release |
| Real corpora cannot run on a shared server | Preview shows fictional only | State it in the UI; real replay is a local script |

## 5. Open questions

**Owner (backend):**
1. Remove the `2026-12-31` issue-date rule in v1? (Recommended: yes.)
2. Staff-only confirmation (F2) or keep applicant self-confirmation (F1)? Affects the demo narrative.
3. Per-submission capability link for applicants acceptable instead of accounts (D)? Where will the admin be hosted (internal-only)?
4. Should GPA thresholds be per scale in v1 or wait for the GPA-scale task? (Recommended: the schema supports per-scale from v1; values decided in that task.)
5. Should the student-number "one document is enough" rule become configurable (`submission_wide_fields`) or stay code?
6. Merge `research/real-docs` first so v1 is defined on it? (Recommended: yes, after your OK.)

**Munira (frontend):**
7. Appetite for moving `copy.ts`/`presentation.ts`/`page-state` into shared packages and for removing the review panel from the web app (and the e2e tests that cover it).
8. Admin component list for P3 (table, form, dialog, tabs, diff) — build or adopt primitives?
9. HEIC: test the iOS picker and the Files picker on a real iPhone.

**Mentor:**
10. Which parameters must be editable first? (issue-date age, required/optional, validity, comparisons are assumed.)
11. Is 중소기업확인서 required for every applicant, or conditional? (Conditional "required if…" needs a new rule kind; optional/required toggle is enough for the demo.)
12. Who reviews uncertain items at the institution and how fast? That decides F1 vs F2.
