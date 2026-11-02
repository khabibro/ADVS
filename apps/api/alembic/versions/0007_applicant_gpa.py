"""Add the optional applicant-entered GPA and scale to projects (route B confirmation).

Revision ID: 0007_applicant_gpa
Revises: 0006_field_reviews
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_applicant_gpa"
down_revision: str | None = "0006_field_reviews"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table: str, column: str) -> bool:
    return column in {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    for column in ("applicant_gpa", "applicant_gpa_scale"):
        if not _has_column("projects", column):
            op.add_column("projects", sa.Column(column, sa.String(length=8), nullable=True))


def downgrade() -> None:
    for column in ("applicant_gpa_scale", "applicant_gpa"):
        if _has_column("projects", column):
            op.drop_column("projects", column)
