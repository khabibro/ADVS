# ADVS

AI-Based Administrative Document Analysis and Automated Verification System.

CURRENT PHASE (on `main`): Phase 2 mentor-defined document domain, plus P0
backend stabilization and P1/P2.x OCR/extraction hardening. Four additional
safety fixes and a from-scratch reproducible baseline exist on unmerged
branches (`phase-b/safety-fixes`, `p2.2/issue-date-label-gate`) pending
review. See `docs/ARCHITECTURE.md` §11 and `evaluation/README.md`'s phase
history for the full picture.

ADVS is a workflow-centric modular monorepo for uploading Korean administrative documents, extracting text through direct PDF text or OCR, classifying the document, extracting structured fields, and validating results against workflow-scoped checklist rules. A document is required only when the selected workflow requires it.

Canonical pre-check results are `READY` (제출 가능), `REVIEW_REQUIRED` (확인 필요), and `NEEDS_CORRECTION` (보완 필요). `READY` means only that the configured ADVS checks found no issue; it does not mean official approval or guaranteed acceptance by an institution.

MENTOR-DEFINED MVP DOCUMENT DOMAIN:
- Business Registration Certificate / 사업자등록증
- SME Confirmation Certificate / 중소기업확인서
- National Tax Payment Certificate / 국세 납세증명서
- Social Insurance Payment Certificate / 4대 사회보험료 완납증명서
- Enrollment Certificate / 재학증명서
- Transcript / 성적증명서

Existing Graduation Certificate / 졸업증명서 and Career Certificate / 경력증명서 support is
preserved. Phase 2 defines structured facts; it does not yet perform cross-document identity
matching, generalized validity decisions, or GPA threshold evaluation.

This is not production-ready OCR/extraction. PaddleOCR is the only real OCR provider; mock OCR remains available for tests and local pipeline development.

## Monorepo Structure

- `apps/web`: Next.js user-facing application
- `apps/admin`: separate Next.js admin application shell
- `apps/api`: FastAPI backend, SQLAlchemy models, Alembic migrations, document pipeline
- `packages/ui`: shared UI primitives used by web and admin
- `packages/contracts`: generated TypeScript contracts from FastAPI OpenAPI
- `docs`: architecture, domain, operations, security, and planning documentation
- `scripts`: environment validation and security audit automation
- `tests/e2e`: reserved for end-to-end smoke tests

## Tech Stack

Frontend/admin: Next.js, TypeScript, App Router, Tailwind CSS, shadcn-style UI primitives, React Hook Form, Zod, TanStack Query where useful.

Backend: FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, PostgreSQL, PyMuPDF, Pillow, PaddleOCR.

Infrastructure: Docker Compose, pnpm workspace, Turborepo for TypeScript tasks, GitHub Actions.

## Setup

```bash
pnpm install
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,paddle]"
alembic upgrade head
cd ../..
make seed
```

Copy `.env.example` to `.env` for local overrides. Do not commit `.env`.

## Development

```bash
make dev-web
make dev-admin
make dev-api
```

Default ports:
- Web: http://localhost:3000
- Admin: http://localhost:3002
- API: http://localhost:8000
- API docs: http://localhost:8000/docs

## OCR

PaddleOCR is the default real OCR engine. Digital PDFs with a usable text layer are extracted directly with PyMuPDF; scanned PDFs and images go through PaddleOCR.

```bash
OCR_PROVIDER=paddle
PADDLE_OCR_DEVICE=cpu
PADDLE_OCR_LANG=korean
PADDLE_OCR_REC_MODEL_NAME=korean_PP-OCRv5_mobile_rec
PADDLE_OCR_DET_MODEL_NAME=PP-OCRv5_mobile_det
```

Use `OCR_PROVIDER=mock` only for tests and deterministic local pipeline checks.

The backend runtime is Python `>=3.12,<3.13` because the pinned `paddlepaddle==3.1.1` runtime must have a compatible wheel. Python 3.14 can run the stubbed tests in an already-created venv, but it cannot complete real PaddleOCR inference with the pinned runtime.

## Quality Gates

Normal gate:
```bash
make check
```

Heavier gate:
```bash
make check-all
```

Focused commands:
```bash
make api-lint
make api-typecheck
make api-test
pnpm lint
pnpm typecheck
pnpm build
pnpm contracts:generate
make docker-check
```

## Contracts

FastAPI schemas are the server source of truth. Generate frontend-consumable TypeScript contracts with:

```bash
pnpm contracts:generate
```

This exports `apps/api/openapi.json` and writes generated types to `packages/contracts/src/openapi.ts`.

## Docker

```bash
docker compose up --build
```

Services:
- `web`: localhost:3000
- `admin`: localhost:3002
- `api`: localhost:8000
- `db`: PostgreSQL

## Documentation

Start with `docs/DOCUMENTATION_INDEX.md`, or go directly to
`docs/ARCHITECTURE.md` (system overview), `docs/GLOSSARY.md` (terms), or
`docs/RECOMMENDATIONS.md` (proposed next steps, not implemented).

## OCR Evaluation

Run `make eval-paddle` to process renderable benchmark samples through PaddleOCR and score the downstream classifier, extractors, and validator. Text-only evaluation (`make eval`) is useful for deterministic rule regression, but it is not OCR accuracy evidence.

## Security and Privacy

Administrative documents may contain personal and corporate information. The MVP validates uploads, avoids logging full OCR text, keeps runtime configuration in environment variables, and does not expose raw filesystem paths. Production use still requires authentication, RBAC, retention/deletion policy, encryption, and formal privacy review.

## Known Limitations

- Admin app is a structural shell, not a complete admin product.
- Extraction rules are initial deterministic heuristics.
- No authentication/RBAC yet.
- No async queue or object storage.
- PaddleOCR model downloads and real OCR inference are not used in normal unit tests.
- Docker build depends on a running Docker daemon.
