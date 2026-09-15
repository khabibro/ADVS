# Development

Use pnpm for TypeScript workspaces and Python tooling directly for the API.

- Web: `make dev-web`
- Admin: `make dev-admin`
- API: `make dev-api`
- Docker stack: `make docker-up`

The API remains a Python project under `apps/api`; it is intentionally not modeled as a fake npm package.

Use Python `>=3.12,<3.13` for the API environment. Install backend dependencies with `pip install -e ".[dev,paddle]"` so the local runtime matches the PaddleOCR production path.
