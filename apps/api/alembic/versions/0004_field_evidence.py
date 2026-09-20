"""Persist provider-independent field evidence.

Revision ID: 0004_field_evidence
Revises: 0003_status_semantics
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_field_evidence"
down_revision: str | None = "0003_status_semantics"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def _has_column(table: str, column: str) -> bool:
    return column in {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if not _has_column("extracted_fields", "evidence"):
        op.add_column("extracted_fields", sa.Column("evidence", _JSON_TYPE, nullable=True))


def downgrade() -> None:
    if _has_column("extracted_fields", "evidence"):
        op.drop_column("extracted_fields", "evidence")
