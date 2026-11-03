"""Versioned check criteria: a version number on checklists and a revision history table.

Revision ID: 0008_checklist_revisions
Revises: 0007_applicant_gpa
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008_checklist_revisions"
down_revision: str | None = "0007_applicant_gpa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_column(table: str, column: str) -> bool:
    return column in {item["name"] for item in _inspector().get_columns(table)}


def upgrade() -> None:
    if not _has_column("checklists", "version"):
        op.add_column(
            "checklists",
            sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        )
    if "checklist_revisions" not in _inspector().get_table_names():
        json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
        op.create_table(
            "checklist_revisions",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "checklist_id",
                sa.Uuid(),
                sa.ForeignKey("checklists.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("editor_label", sa.String(length=120), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("snapshot", json_type, nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index(
            "ix_checklist_revisions_checklist_id", "checklist_revisions", ["checklist_id"]
        )
        op.create_index(
            "uq_checklist_revision_version",
            "checklist_revisions",
            ["checklist_id", "version"],
            unique=True,
        )


def downgrade() -> None:
    if "checklist_revisions" in _inspector().get_table_names():
        op.drop_index("uq_checklist_revision_version", table_name="checklist_revisions")
        op.drop_index("ix_checklist_revisions_checklist_id", table_name="checklist_revisions")
        op.drop_table("checklist_revisions")
    if _has_column("checklists", "version"):
        op.drop_column("checklists", "version")
