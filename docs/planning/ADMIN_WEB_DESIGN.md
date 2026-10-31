# ADVS — Admin + Web design (recommended)

Status: design only (2026-10-31), nothing implemented. Decisions and alternatives are in `ADMIN_WEB_ANALYSIS.md`; this file is the recommended design.
Principles kept: the backend decides every status; 0 false 제출 가능 is a hard gate; uncertain → human review; traditional OCR only; frontend is Munira's.

Contents: 1 Scope · 2 Rule schema · 3 Today's behaviour as version 1 · 4 Compilation and engine · 5 Data model and migration · 6 API · 7 Auth · 8 Screens · 9 Applicant UX · 10 Phases and gates.

---

## 1. Scope and non-goals

In scope: editable, versioned checklists (documents, issue-date rule, validity, comparisons, thresholds, check-date policy), staff login with roles, reviewer queue in the admin app, applicant app reduced to status and fixes.
Out of scope: changing extraction, classification, the look-alike title table, the reliability policy (a missing or unconfirmed value is never a failure, always review), the auto-accept policy. These stay code and are shown read-only in the admin.

## 2. Rule schema (`advs.checklist/1`)

Stored as one JSON document per checklist version, validated by a strict pydantic model (`extra="forbid"`, discriminated unions, enums from `core/domain.py`). Field names below are the contract; the pydantic classes are generated from it.

```text
Checklist
  schema                "advs.checklist/1"
  key                   "business" | "student" | …           stable identifier
  name_ko, description_ko
  check_date            { policy: SUBMISSION_DATE | FIXED | STAFF_CHOICE,
                          fixed_date?: "YYYY-MM-DD",           required when FIXED
                          applicant_can_change: false }        always false in v1 (see Analysis N1)
  identity_match        { applicant_name: bool, company_name: bool }   submitter-entered values vs documents (today: always on)
  submission_wide_fields [ "student_id" ]                       required on at least one document; compared only when both print it
  documents[]           DocumentRule
  comparisons[]         Comparison
  thresholds[]          Threshold

DocumentRule
  type                  DocumentType (not UNKNOWN)
  requirement           REQUIRED | OPTIONAL        (CONDITIONAL reserved, not in v1)
  extra_required_fields [ field ]                    added to the built-in defaults; engine always routes a missing one to review
  issue_date?           { field: "issue_date", max_age_days: 1..365, inclusive: true, severity: ERROR | WARNING }
  validity?             { field: "valid_until", mode: PRINTED_VALID_UNTIL, severity: ERROR | WARNING }
  duplicates            "STANDARD"                   read-only in v1: identical re-upload is a notice, different files or conflicting reviews go to review

Comparison                                           same value on two documents
  id                    stable slug
  source / target       { document: DocumentType, field: str }
  match                 IDENTIFIER | TEXT | INSTITUTION     (normalisation is code; company/workplace names always get the legal-form handling, `submission.py:736-738`)
  severity              ERROR | WARNING
  reliability           "BOTH_RELIABLE_ELSE_REVIEW"  read-only constant: an error is raised only when both values are reliable; otherwise review

Threshold                                            numeric condition on one field
  id, document, field
  operator              GTE | LTE | EQ
  value                 decimal as string
  scale                 { field: "gpa_scale", mode: RAW | PER_SCALE,
                          per_scale?: { "4.5": "…", "4.3": "…", "4": "…" },
                          near_margin?: decimal,           values within the margin go to review (reserved for the GPA-scale task)
                          cross_check?: { field: "percent" } }   (reserved; not extracted today)
  severity              ERROR | WARNING
```

Rules of the schema (each is a save-time error):
- a `comparison`/`threshold`/`validity` may only name documents present in `documents[]` and fields that exist for that type (`REVIEWABLE_FIELDS`, `domain.py:164`);
- `severity` ERROR means 보완 필요, WARNING means 확인 필요 (`submission.py:140-146`); neither can turn an unreliable value into a pass or a fail;
- `check_date.policy = FIXED` needs `fixed_date`; `applicant_can_change` must be `false`;
- `max_age_days` must be an integer 1–365 (the engine itself accepts 0–36500; the editor is stricter on purpose);
- a `threshold` on a field that has a scale (`gpa`) needs `scale`; `RAW` reproduces today's behaviour, `PER_SCALE` is the GPA-scale design.

The catalogue the editor shows (document types, fields with Korean labels, allowed comparison pairs, match kinds, severities, scales) is served by the API (`GET /admin/catalog`), so the frontend contains no domain constants.

## 3. Today's behaviour as version 1

These two documents reproduce today's seeded checklists. Items marked **code** are not in the document because the engine applies them regardless.

### 3.1 Business (`seed.py:122-183`, defaults from `requirements.py:17-37`)

```json
{
  "schema": "advs.checklist/1",
  "key": "business",
  "name_ko": "기업 제출서류 점검",
  "description_ko": "기업 제출에 필요한 문서 종류를 확인하는 사전 점검 업무입니다.",
  "check_date": { "policy": "SUBMISSION_DATE", "applicant_can_change": false },
  "identity_match": { "applicant_name": true, "company_name": true },
  "submission_wide_fields": [],
  "documents": [
    { "type": "BUSINESS_REGISTRATION_CERTIFICATE", "requirement": "REQUIRED", "extra_required_fields": [], "duplicates": "STANDARD" },
    { "type": "SME_CONFIRMATION_CERTIFICATE", "requirement": "REQUIRED", "extra_required_fields": [], "duplicates": "STANDARD",
      "validity": { "field": "valid_until", "mode": "PRINTED_VALID_UNTIL", "severity": "ERROR" } },
    { "type": "NATIONAL_TAX_PAYMENT_CERTIFICATE", "requirement": "REQUIRED", "extra_required_fields": [], "duplicates": "STANDARD",
      "validity": { "field": "valid_until", "mode": "PRINTED_VALID_UNTIL", "severity": "ERROR" } },
    { "type": "SOCIAL_INSURANCE_PAYMENT_CERTIFICATE", "requirement": "REQUIRED", "extra_required_fields": [], "duplicates": "STANDARD",
      "validity": { "field": "valid_until", "mode": "PRINTED_VALID_UNTIL", "severity": "ERROR" } }
  ],
  "comparisons": [
    { "id": "sme-brn",   "source": {"document": "BUSINESS_REGISTRATION_CERTIFICATE", "field": "business_registration_number"},
      "target": {"document": "SME_CONFIRMATION_CERTIFICATE", "field": "business_registration_number"}, "match": "IDENTIFIER", "severity": "ERROR" },
    { "id": "sme-name",  "source": {"document": "BUSINESS_REGISTRATION_CERTIFICATE", "field": "company_name"},
      "target": {"document": "SME_CONFIRMATION_CERTIFICATE", "field": "company_name"}, "match": "TEXT", "severity": "ERROR" },
    { "id": "tax-brn",   "source": {"document": "BUSINESS_REGISTRATION_CERTIFICATE", "field": "business_registration_number"},
      "target": {"document": "NATIONAL_TAX_PAYMENT_CERTIFICATE", "field": "business_registration_number"}, "match": "IDENTIFIER", "severity": "ERROR" },
    { "id": "tax-name",  "source": {"document": "BUSINESS_REGISTRATION_CERTIFICATE", "field": "company_name"},
      "target": {"document": "NATIONAL_TAX_PAYMENT_CERTIFICATE", "field": "company_name"}, "match": "TEXT", "severity": "ERROR" },
    { "id": "ins-brn",   "source": {"document": "BUSINESS_REGISTRATION_CERTIFICATE", "field": "business_registration_number"},
      "target": {"document": "SOCIAL_INSURANCE_PAYMENT_CERTIFICATE", "field": "business_registration_number"}, "match": "IDENTIFIER", "severity": "ERROR" },
    { "id": "ins-name",  "source": {"document": "BUSINESS_REGISTRATION_CERTIFICATE", "field": "company_name"},
      "target": {"document": "SOCIAL_INSURANCE_PAYMENT_CERTIFICATE", "field": "workplace_name"}, "match": "TEXT", "severity": "ERROR" }
  ],
  "thresholds": []
}
```

Notes: the cross-document company-name comparison already strips legal-form markers (주식회사 / (주) / ㈜) because the engine applies that to any `company_name` or `workplace_name` field (`submission.py:736-738`); `match: TEXT` therefore reproduces today's behaviour exactly and no separate company-name kind is needed.
**Code (not in the document):** the implicit `valid_until` ≥ check date for required documents (`submission.py:632-660`); default required fields (`requirements.py:17-37`); look-alike titles (지방세납세증명서 → UNKNOWN → review); uncertain classification, multiple documents in one file, hidden text → review; duplicate policy.

### 3.2 Student (`seed.py:184-238`; on `research/real-docs` also `a9ff8c7` and `fe569a2`)

```json
{
  "schema": "advs.checklist/1",
  "key": "student",
  "name_ko": "학생 제출서류 점검",
  "description_ko": "학생 제출 문서의 구조화 정보 기반을 확인하는 사전 점검 업무입니다.",
  "check_date": { "policy": "SUBMISSION_DATE", "applicant_can_change": false },
  "identity_match": { "applicant_name": true, "company_name": false },
  "submission_wide_fields": ["student_id"],
  "documents": [
    { "type": "ENROLLMENT_CERTIFICATE", "requirement": "REQUIRED", "extra_required_fields": ["student_id"], "duplicates": "STANDARD",
      "issue_date": { "field": "issue_date", "max_age_days": 90, "inclusive": true, "severity": "ERROR" } },
    { "type": "TRANSCRIPT", "requirement": "OPTIONAL", "extra_required_fields": [], "duplicates": "STANDARD" }
  ],
  "comparisons": [
    { "id": "stu-id",   "source": {"document": "ENROLLMENT_CERTIFICATE", "field": "student_id"},
      "target": {"document": "TRANSCRIPT", "field": "student_id"}, "match": "IDENTIFIER", "severity": "ERROR" },
    { "id": "stu-name", "source": {"document": "ENROLLMENT_CERTIFICATE", "field": "student_name"},
      "target": {"document": "TRANSCRIPT", "field": "student_name"}, "match": "TEXT", "severity": "ERROR" },
    { "id": "stu-univ", "source": {"document": "ENROLLMENT_CERTIFICATE", "field": "university_name"},
      "target": {"document": "TRANSCRIPT", "field": "university_name"}, "match": "INSTITUTION", "severity": "ERROR" }
  ],
  "thresholds": [
    { "id": "gpa-min", "document": "TRANSCRIPT", "field": "gpa", "operator": "GTE", "value": "3.0",
      "scale": { "field": "gpa_scale", "mode": "RAW" }, "severity": "ERROR" }
  ]
}
```

Notes:
- The transcript's `issue_date` is not age-checked today (only the enrolment certificate has `ISSUE_DATE_MAX_AGE`); v1 keeps that. The question whether the transcript should have a 90-day rule is a v2 content decision for the owner/mentor.
- **Removed on purpose:** the two `issue_date ON_OR_BEFORE 2026-12-31` rows (`seed.py:196-201, 221-224`). They are redundant with the age rule's upper bound (`submission.py:676-690`) and stop every student check on 2027-01-01. Needs the owner's OK; an equivalence test must show that no corpus case changes.
- `university_name` comparison and the "student number on at least one document" behaviour exist only on `research/real-docs`. v1 must be built on that branch after the merge OK.
- `GPA RAW` reproduces today's scale-blind comparison on purpose; `PER_SCALE` thresholds are decided in the GPA-scale task.

## 4. Compilation and engine

The published document is compiled to the engine's existing inputs; the engine (`SubmissionVerificationEngine`) is not changed in P2.

| Document element | Compiles to |
|---|---|
| `documents[].requirement` | `RequirementSnapshot.required` |
| `extra_required_fields` | `RequirementSnapshot.required_fields` (same additive rule as `required_fields()`, `requirements.py:56-68`) |
| `issue_date` | `ISSUE_DATE_MAX_AGE {max_age_days, field}` with the given severity |
| `validity` | `DATE_COMPARISON ON_OR_AFTER EVALUATION_DATE` on `valid_until` |
| `comparisons[]` | `FIELD_COMPARISON EQUALS` with `value_type` from `match` (`string` / `identifier` / `institution`) |
| `thresholds[]` RAW | `NUMERIC_COMPARISON` |
| `thresholds[]` PER_SCALE | **new** engine rule `NUMERIC_COMPARISON_BY_SCALE` (P3+, with the GPA-scale task) |
| `check_date`, `identity_match`, `submission_wide_fields` | `VerificationContext` / engine flags (today hard-wired; become parameters) |

Equivalence gate for P2: for each workflow, `compile(v1) == SubmissionVerificationService._requirements(checklist)` (rules sorted, params equal), plus the full fictional corpora (dev, hold-out 1/2/3, v2 and v3 views) give 0 field-level and 0 status differences, the real pair stays 11/11, and `test_submission_verification*.py`, `test_b1…b4_*`, `test_phase_d2_student_workflow.py` pass unchanged.

## 5. Data model and migration

New / changed tables (SQLAlchemy models; Alembic revision; JSON uses the existing `JSONType`, JSONB on PostgreSQL):

```text
checklists                (existing = "workflow")
  + key                    unique, stable
  + published_version_id   FK checklist_versions.id, nullable until migrated
checklist_versions        NEW
  id, checklist_id FK, number int, status DRAFT|PUBLISHED|SUPERSEDED,
  document JSON, document_sha256 (canonical JSON, sorted keys), schema_version,
  change_note, created_by FK users, created_at, published_by, published_at, parent_version_id
  unique(checklist_id, number); partial unique index: at most one DRAFT per checklist
projects
  + checklist_version_id   FK, pinned at creation (NOT NULL after backfill)
  + verified_version_id    FK, the version used by the latest verification
  + access_token_hash      applicant capability link (see §7)
validation_results
  details JSON gains checklist_version_id and rule ids from the document (stable slugs, not row ids)
users
  + password_hash, role (REVIEWER|ADMIN), is_active, failed_logins, locked_until
staff_sessions            NEW   id_hash, user_id, created_at, expires_at, last_seen_at, csrf_hash
audit_logs
  + checklist_id, version_id; actor_id required for staff events
document_requirements, validation_rules
  unchanged and unused after the switch; dropped in a later revision once v1 equivalence has held for one release
```

Migration steps:
1. Revision A: add the tables and nullable columns.
2. Data step: for each existing checklist, `export_rows_to_document()` (a generic converter from rows, not hard-coded to the two seeds) → version 1, `PUBLISHED`; backfill `projects.checklist_version_id`.
3. Equivalence test (§4) runs in CI against a database built from `seed.py`.
4. Switch `SubmissionVerificationService._requirements()` to compile from the pinned version; keep the old loader behind a test-only flag for one release.
5. Revision B (later): drop the unused rule tables.

`seed.py` stops owning rules: it creates users and imports the two JSON templates as version 1 when a database is empty. It no longer clears requirements or invalidates projects. SQLite vs PostgreSQL: partial unique indexes use the existing `sqlite_where`/`postgresql_where` pattern (`entities.py:182-191`); JSON is canonicalised before hashing so both backends give the same hash.

## 6. API

All under `/api/v1`. "Staff" = valid session; role in parentheses. Applicant endpoints take the project's access token (`X-Project-Token` header or `?t=` once, then stored in the page).

| Method and path | Who | Purpose |
|---|---|---|
| `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` | staff | session cookie, CSRF token, current user and role |
| `GET /admin/catalog` | admin | document types, fields with Korean labels, comparable pairs, match kinds, severities, scales |
| `GET /admin/workflows`, `GET /admin/workflows/{id}` | admin, reviewer(read) | list; published and draft summaries |
| `GET /admin/workflows/{id}/versions`, `…/versions/{n}` | admin, reviewer(read) | history; one version with generated Korean sentences |
| `PUT /admin/workflows/{id}/draft` | admin | save the draft; 422 returns `[ {path, code, message_ko} ]`; response includes generated sentences and guardrail warnings |
| `POST /admin/workflows/{id}/draft/preview` | admin | impact preview on a named replay corpus (`fictional-v3`, optional local `real`); returns changed cases |
| `GET /admin/workflows/{id}/diff?from=&to=` | admin | structural diff of two versions |
| `POST /admin/workflows/{id}/publish` | admin | `{change_note, acknowledged_warnings[]}`; creates version n+1, supersedes the old one, audit entry |
| `POST /admin/workflows/{id}/rollback` | admin | `{to_version, change_note}`; publishes an old document as a new version |
| `POST /admin/projects/{id}/recheck` | staff | `{use: "pinned" \| "latest"}`: explicit re-check; never automatic |
| `GET /staff/review-queue` | reviewer | filters: status, document type, age, workflow; counts |
| `GET /staff/projects/{id}` | reviewer | full detail with OCR values, evidence, confidence |
| `POST /staff/projects/{pid}/documents/{did}/fields/{name}/review` | reviewer | existing review call, now with the authenticated user as the actor (`reviewer_label` removed) |
| `GET /staff/audit` | admin | change log: who, what, when, diff link |
| `POST /projects` | public | creates a submission; returns the access link once |
| `GET /projects/{id}/status` | applicant (token) | **applicant view**: checklist, fixable problems, overall status; no OCR values, confidences or evidence |
| `POST /projects/{id}/documents`, `POST /documents/{id}/process` | applicant (token) | upload and process |
| `DELETE /projects/{id}` | admin | the only delete |
| `POST/PATCH /checklists`, `GET /projects` (list), `GET /project-summaries` | **removed or staff-only** | closes the open endpoints (Analysis §2.4) |

Verification: `POST /projects/{id}/verify` no longer accepts a client-chosen date for applicants; the server uses `check_date.policy`. Staff may pass a date only when the policy is `STAFF_CHOICE`. The OpenAPI contract is regenerated (`pnpm contracts:generate`) and both apps consume the generated types.

## 7. Authentication and authorisation (minimum safe)

- **Accounts:** seeded by a CLI (`scripts/create_staff.py --email --role`), no default password in the repository; argon2id hashes; roles `REVIEWER`, `ADMIN`.
- **Session:** random 256-bit id in an HttpOnly cookie named `advs_staff` (`SameSite=Strict`, `Secure` outside localhost), server-side row with expiry (8 h absolute, 30 min idle). Distinct name so the applicant app never shares it (cookies are shared across ports on `localhost`).
- **CSRF:** every state-changing staff request needs `X-CSRF-Token` (value from `/auth/me`); `Origin` is checked against the configured origins.
- **CORS:** only the web and admin origins, credentials allowed for the admin origin only.
- **Login hygiene:** generic error message, 5 failures → 15 min lockout per account and per IP, every login and failure in `audit_logs`.
- **Role matrix:**

| | applicant (token) | reviewer | admin |
|---|---|---|---|
| upload, see own status | yes | – | – |
| list or open any submission, see OCR values | – | yes | yes |
| confirm / correct / mark undecidable | – | yes | yes |
| edit draft, preview, publish, rollback | – | read only | yes |
| delete submission, manage users | – | – | yes |
| change a check date | – | yes (when policy allows) | yes |

- **Applicant access:** a random 128-bit token stored hashed on the project; the link is shown once on creation; no account in v1. Lost link → staff can issue a new token.
- **Before the editor goes live (gate):** all of the above, plus tests that every staff and admin route returns 401 without a session and 403 with the wrong role (generated from the route table so a new route cannot be forgotten).

## 8. Screens (low fidelity)

The admin app is Korean-only, desktop-first, usable at 1280 px and keyboard-only. All strings are plain Korean; rule sentences come from the backend.

**8.1 업무 목록**
```text
┌ ADVS 관리 ─ 업무 · 검토 대기열 · 변경 기록 ───────────── 김관리 (관리자) ▾ ┐
│ 점검 업무                                                                    │
│ ┌──────────────────────┬──────────┬──────────────┬───────────┬──────────┐ │
│ │ 업무                 │ 게시 버전 │ 초안         │ 진행 중 제출 │ 최근 변경 │ │
│ │ 기업 제출서류 점검    │ v3       │ 없음         │ 12        │ 10/28    │ │
│ │ 학생 제출서류 점검    │ v2       │ 편집 중 ●    │ 4         │ 10/29    │ │
│ └──────────────────────┴──────────┴──────────────┴───────────┴──────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

**8.2 업무 편집** (tabs: 서류 · 서류 간 비교 · 기준값 · 점검 기준일)
```text
┌ 학생 제출서류 점검 · 초안 (v2 기준) ──────────  [저장] [변경 영향 보기] [게시…] ┐
│ 서류 │ 서류 간 비교 │ 기준값 │ 점검 기준일                                    │
│ ┌ 재학증명서 ─────────────────────────────────────────────── 필수 ◉ 선택 ○ ┐ │
│ │ 발급일 기준   ☑ 사용   발급 후 [ 90 ]일 이내 (당일 포함)   위반 시 [보완 필요 ▾] │ │
│ │ 유효기간 확인 ☐ 사용                                                       │ │
│ │ 추가 필수 항목  [학번 ✕] [+ 항목 추가]                                       │ │
│ │ 이 규칙의 뜻: “재학증명서는 점검 기준일 기준 90일 이내에 발급되어야 합니다.”      │ │
│ │ 고정(수정 불가): 유사 서류(휴학증명서 등)는 다른 서류로 보고 확인 요청            │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
│ ┌ 성적증명서 ─────────────────────────────────────────────── 필수 ○ 선택 ◉ ┐ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
│ ⚠ 경고 1건: 발급 후 365일 초과는 허용되지 않습니다.                              │
└──────────────────────────────────────────────────────────────────────────┘
```

**8.3 서류 간 비교 · 기준값**
```text
│ 비교 항목                            방식        위반 시        │
│ 재학증명서.학번 = 성적증명서.학번      식별번호    보완 필요 ▾  🗑 │
│ 재학증명서.이름 = 성적증명서.이름      글자        보완 필요 ▾  🗑 │
│ 재학증명서.대학 = 성적증명서.대학      학교명      보완 필요 ▾  🗑 │
│ [+ 비교 추가]   ⓘ 한쪽 값이 불확실하면 오류가 아니라 담당자 확인으로 넘어갑니다(고정). │
│ 기준값: 성적증명서 평점 ≥ [3.0]  척도 방식 [척도 구분 없이 ▾]  위반 시 [보완 필요 ▾]  │
```

**8.4 점검 기준일**
```text
│ ◉ 제출한 날(서버 날짜)   ○ 고정 날짜 [____]   ○ 담당자가 정함                      │
│ ⓘ 제출자는 점검 기준일을 바꿀 수 없습니다.                                       │
```

**8.5 버전 이력과 비교**
```text
│ v3 게시 10/29 김관리  “발급 90→60일”   [보기] [비교] [이 버전으로 되돌리기]            │
│ v2 게시 10/22 김관리  “대학 비교 추가”                                            │
│ 비교 v2 → v3:   재학증명서.발급일 기준   - 90일 이내   + 60일 이내                  │
```

**8.6 변경 영향 미리보기** (before publishing)
```text
│ 기준: 가상 서류 모음 v3 (1,527건 · 약 1초)         실제 서류 모음: 이 서버에서 사용 불가 │
│ 상태가 바뀌는 건   보완 필요 → 확인 필요: 0   확인 필요 → 보완 필요: 14   ★ 제출 가능으로 바뀜: 0 │
│ ┌ 건 ──────────── 기대 결과 ───── 현재 ───── 초안 ───────────────┐                │
│ │ S07 변형 12 ·    보완 필요     보완 필요    보완 필요 …            │                │
│ └──────────────────────────────────────────────────────────────────┘                │
│ ☐ 새로 “제출 가능”이 되는 건이 있어도 게시합니다 (사유: ______)  ← 새 제출 가능이 있을 때만 표시 │
```

**8.7 검토 대기열 · 검토 화면** (moved from the applicant app)
```text
┌ 검토 대기열 ── 필터: 업무 ▾ 서류 ▾ 경과일 ▾ ─────────────────────────────────┐
│ 제출 건            업무       확인 항목  경과    상태                           │
│ 홍*동 · 학생 …    학생       5건       2일     대기 ●                           │
└──────────────────────────────────────────────────────────────────────────────┘
┌ 홍*동 · 재학증명서 ─ 3 / 7 완료 ──────────────────────────┬ 서류 이미지(강조) ┐
│ 학번   인식값 2023****78   신뢰도 0.93   이유: 독립 확인 없음 │  [페이지 이미지]   │
│ [확인 Enter] [값 수정] [판단 불가]                          │                    │
└─────────────────────────────────────────────────────────┴────────────────────┘
```

**8.8 변경 기록**
```text
│ 시각          사용자     행동        대상          상세                           │
│ 10/29 14:02  김관리     게시        학생 v2→v3   [비교 보기]                       │
│ 10/29 13:50  이검토     값 확인     제출 #381    학번                              │
```

States to design for each screen (Munira): loading, empty, error with next step, save conflict ("다른 관리자가 초안을 수정했습니다"), session expired.

## 9. Applicant web UX changes

Applicant sees only: (1) checklist per document, 제출됨 / 미제출, with the upload button for each; (2) problems they can fix: what is wrong, which document, how to fix; (3) overall status 제출 가능 / 보완 필요 / 담당자 확인 중, one sentence, next step; (4) the result.

```text
┌ 학생 제출서류 점검 ───────────────────────────────────────────────┐
│ 현재 상태   담당자 확인 중   서류는 정상입니다. 담당자가 확인하면 알려드립니다. │
│ 점검 기준일  2026-11-02 (제출일 기준)                              │
│ 필요한 서류   재학증명서 ✔ 제출됨 [교체]    성적증명서 ○ 미제출 [업로드]    │
│ 보완할 항목   재학증명서: 발급일이 90일을 넘었습니다 → 최근 발급본으로 다시 올려 주세요 │
└──────────────────────────────────────────────────────────────────┘
```

Changes and owners:

| Change | Why | Owner |
|---|---|---|
| Remove `ReviewPanel`, OCR values, confidence, auto-accept reasons, evidence crops, and the detail page's value table from the applicant app; add 담당자 확인 중 wording | trust model (Analysis N2/N3); less private data on the applicant's screen | Munira (reviews), backend adds the applicant DTO |
| Remove the date picker ("날짜를 바꿔 다시 점검하기"); show the server's check date | N1 | Munira + backend |
| `GET /projects/{id}/status` with access token; list page replaced by a link | privacy | backend + Munira |
| Upload: accept MPO; strip GPS/EXIF; separate "unsupported" and "corrupt" | N4–N6 (task `fix/phone-photo-upload`) | backend; Munira reviews `copy.ts` |
| Optional later: applicant enters 학번 and GPA with an explicit scale as independent evidence of the reading | catches OCR digit errors; resolves 4.3/4.5 | backend (evidence policy v3) after the real-document test; Munira for the form |
| Project creation: explain that the entered name/company are compared with the documents | N7 | Munira |

## 10. Phases and gates

Calendar: today 2026-10-31; second midterm **11/19**; final **12/10**. Gates marked **G** are always run on the phase's final commit: backend tests + ruff + format + mypy; `pnpm check` (web and admin, uncached once per phase); Playwright + axe (0 serious/critical on every screen of both apps); `make demo-rehearsal` ×3 consecutive; manipulated-PDF suite 711/711; fictional sets v2/v3 field-level diff 0; real pair 11/11; privacy scan.

| Phase | Dates | Content | Owner | Extra gate |
|---|---|---|---|---|
| P0 | 11/1–11/5 | finish the fresh-capture test and report; merge `research/real-docs` (owner OK); `fix/phone-photo-upload` | owner; Munira reviews upload copy | owner's approvals |
| P1 | 11/3–11/8 | auth, roles, sessions, CSRF, tokens for applicants; lock down open endpoints; applicant DTO; server check date; admin login page | owner (API); Munira (login, token flow) | every route 401/403 test generated from the route table; no applicant endpoint returns OCR values |
| P2 | 11/5–11/11 | schema + pydantic, `checklist_versions`, compile, v1 export/import, equivalence test, read-only admin API, catalogue | owner | **G**; compile(v1) == current loader; 0 diff on all corpora |
| P3 | 11/9–11/17 | admin shell; workflow list; editor (documents, issue-date, validity, comparisons, GPA RAW threshold, check-date); draft/publish; version list with text diff; `packages/api-client`, `packages/copy`, UI components | Munira (UI) + owner (draft/publish API) | **G**; Playwright admin: edit → publish → new submission pinned to vN → old submission still on vN-1 |
| demo | 11/18 | rehearsal, freeze, demo script update | both | `make demo-rehearsal` ×3 |
| P4 | 11/20–12/1 | reviewer queue and review screen moved to admin; impact preview; structural diff; audit log; rollback | owner (preview, audit) + Munira (screens) | **G**; preview matches a full corpus run on 3 sampled edits; rollback test |
| P5 | 12/2–12/8 | applicant app trimmed; real-document verification of each rule kind; optional applicant-declared values (separate approval) | Munira + owner | **G**; real-document run per `REAL_DOCUMENT_TEST_PLAN.md` |
| final | 12/10 | report, deck, demo | both | – |

Cut line if time is short: P4 preview UI and audit screens move to December; the midterm demo shows editing → publishing → the pinned-version behaviour and the guardrails. P5's applicant-declared values are optional and need a separate evidence-policy approval and a new real-document test; they are never bundled with the editor release.

Per-phase review by Munira: any change under `apps/web`, `apps/admin`, `packages/ui`, `packages/copy`, `packages/api-client`; Korean strings in `copy.ts`; accessibility fixes found by axe. Commits: backend and docs as KHABIBILLO via `github-khabibro`; frontend as Munira via `github-munira`.
