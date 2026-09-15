"""p1 pipeline metadata

Additive columns supporting classification evidence and extraction
provenance (P1). No existing column is renamed or dropped.

Revision ID: 0002_p1_pipeline_metadata
Revises: 0001_initial
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_p1_pipeline_metadata"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _has_column("documents", "classification_meta"):
        op.add_column("documents", sa.Column("classification_meta", _JSON_TYPE, nullable=True))
    if not _has_column("extracted_fields", "extraction_method"):
        op.add_column(
            "extracted_fields", sa.Column("extraction_method", sa.String(length=60), nullable=True)
        )
    if not _has_column("extracted_fields", "source_text"):
        op.add_column("extracted_fields", sa.Column("source_text", sa.Text(), nullable=True))


def downgrade() -> None:
    if _has_column("extracted_fields", "source_text"):
        op.drop_column("extracted_fields", "source_text")
    if _has_column("extracted_fields", "extraction_method"):
        op.drop_column("extracted_fields", "extraction_method")
    if _has_column("documents", "classification_meta"):
        op.drop_column("documents", "classification_meta")
