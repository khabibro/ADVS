"""status semantics ready review required

Revision ID: 0003_status_semantics
Revises: 0002_p1_pipeline_metadata
Create Date: 2026-09-15
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_status_semantics"
down_revision: str | None = "0002_p1_pipeline_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _rewrite_status(table_name: str, old: str, new: str) -> None:
    op.execute(
        sa.text(f"UPDATE {table_name} SET status = :new WHERE status = :old").bindparams(
            old=old, new=new
        )
    )


def upgrade() -> None:
    for table_name in ("projects", "submissions"):
        _rewrite_status(table_name, "PASS", "READY")
        _rewrite_status(table_name, "REVIEW", "REVIEW_REQUIRED")


def downgrade() -> None:
    for table_name in ("projects", "submissions"):
        _rewrite_status(table_name, "READY", "PASS")
        _rewrite_status(table_name, "REVIEW_REQUIRED", "REVIEW")
