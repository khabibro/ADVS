"""Add evidence review persistence and processing version.

Revision ID: 0006_field_reviews
Revises: 0005_submission_verification
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_field_reviews"
down_revision: str | None = "0005_submission_verification"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table: str, column: str) -> bool:
    return column in {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if not _has_column("documents", "processing_version"):
        op.add_column(
            "documents",
            sa.Column("processing_version", sa.Integer(), nullable=False, server_default="0"),
        )
    if not sa.inspect(op.get_bind()).has_table("field_reviews"):
        op.create_table(
            "field_reviews",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("project_id", sa.Uuid(), nullable=False),
            sa.Column("document_id", sa.Uuid(), nullable=False),
            sa.Column("extracted_field_id", sa.Uuid(), nullable=True),
            sa.Column("field_name", sa.String(length=120), nullable=False),
            sa.Column("decision", sa.String(length=30), nullable=False),
            sa.Column("original_raw_value", sa.Text(), nullable=True),
            sa.Column("original_normalized_value", sa.Text(), nullable=True),
            sa.Column("original_evidence_fingerprint", sa.String(length=64), nullable=True),
            sa.Column("reviewed_raw_value", sa.Text(), nullable=True),
            sa.Column("reviewed_normalized_value", sa.Text(), nullable=True),
            sa.Column("reviewer_label", sa.String(length=120), nullable=True),
            sa.Column("note", sa.String(length=500), nullable=True),
            sa.Column("processing_version", sa.Integer(), nullable=False),
            sa.Column("policy_version", sa.String(length=60), nullable=False),
            sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("stale_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
            sa.ForeignKeyConstraint(
                ["extracted_field_id"], ["extracted_fields.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_field_reviews_project_id", "field_reviews", ["project_id"])
        op.create_index("ix_field_reviews_document_id", "field_reviews", ["document_id"])
        op.create_index(
            "ix_field_reviews_extracted_field_id", "field_reviews", ["extracted_field_id"]
        )
        op.create_index("ix_field_reviews_field_name", "field_reviews", ["field_name"])
        op.create_index("ix_field_reviews_decision", "field_reviews", ["decision"])
        op.create_index("ix_field_reviews_is_current", "field_reviews", ["is_current"])
        op.create_index(
            "uq_field_reviews_current_target",
            "field_reviews",
            ["document_id", "field_name"],
            unique=True,
            sqlite_where=sa.text("is_current = 1"),
            postgresql_where=sa.text("is_current = true"),
        )


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("field_reviews"):
        op.drop_table("field_reviews")
    if _has_column("documents", "processing_version"):
        op.drop_column("documents", "processing_version")
