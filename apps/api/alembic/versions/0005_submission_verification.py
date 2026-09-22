"""Persist structured submission-verification rule results.

Revision ID: 0005_submission_verification
Revises: 0004_field_evidence
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005_submission_verification"
down_revision: str | None = "0004_field_evidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def _has_column(table: str, column: str) -> bool:
    return column in {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if not _has_column("validation_results", "scope"):
        op.add_column("validation_results", sa.Column("scope", sa.String(length=30), nullable=True))
        op.create_index(
            "ix_validation_results_scope", "validation_results", ["scope"], unique=False
        )
    if not _has_column("validation_results", "outcome"):
        op.add_column(
            "validation_results", sa.Column("outcome", sa.String(length=30), nullable=True)
        )
    if not _has_column("validation_results", "details"):
        op.add_column("validation_results", sa.Column("details", _JSON_TYPE, nullable=True))


def downgrade() -> None:
    if _has_column("validation_results", "details"):
        op.drop_column("validation_results", "details")
    if _has_column("validation_results", "outcome"):
        op.drop_column("validation_results", "outcome")
    if _has_column("validation_results", "scope"):
        op.drop_index("ix_validation_results_scope", table_name="validation_results")
        op.drop_column("validation_results", "scope")
