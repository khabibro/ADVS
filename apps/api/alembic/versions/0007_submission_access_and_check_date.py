"""Per-submission access token and the stored check date.

Revision ID: 0007_access_check_date
Revises: 0006_field_reviews
"""

import secrets
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_access_check_date"
down_revision: str | None = "0006_field_reviews"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table: str, column: str) -> bool:
    return column in {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if not _has_column("projects", "access_token"):
        op.add_column("projects", sa.Column("access_token", sa.String(64), nullable=True))
        bind = op.get_bind()
        for (project_id,) in bind.execute(sa.text("SELECT id FROM projects")).fetchall():
            bind.execute(
                sa.text("UPDATE projects SET access_token = :t WHERE id = :i"),
                {"t": secrets.token_urlsafe(24), "i": project_id},
            )
        with op.batch_alter_table("projects") as batch:
            batch.alter_column("access_token", existing_type=sa.String(64), nullable=False)
        op.create_index("ix_projects_access_token", "projects", ["access_token"])
    if not _has_column("projects", "check_date"):
        op.add_column("projects", sa.Column("check_date", sa.Date(), nullable=True))
    if not _has_column("projects", "check_date_source"):
        op.add_column("projects", sa.Column("check_date_source", sa.String(40), nullable=True))
    if not _has_column("projects", "finalised_at"):
        op.add_column("projects", sa.Column("finalised_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_index("ix_projects_access_token", table_name="projects")
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("finalised_at")
        batch.drop_column("check_date_source")
        batch.drop_column("check_date")
        batch.drop_column("access_token")
