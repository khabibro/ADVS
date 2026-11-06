"""Check-date policy on a checklist version: the day of the check, or a fixed date.

Revision ID: 0010_checklist_date_policy
Revises: 0009_uuid_text_affinity
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_checklist_date_policy"
down_revision: str | None = "0009_uuid_text_affinity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns() -> set[str]:
    return {item["name"] for item in sa.inspect(op.get_bind()).get_columns("checklists")}


def upgrade() -> None:
    existing = _columns()
    if "evaluation_date_mode" not in existing:
        op.add_column(
            "checklists",
            sa.Column(
                "evaluation_date_mode",
                sa.String(10),
                nullable=False,
                server_default=sa.text("'TODAY'"),
            ),
        )
    if "evaluation_date_fixed" not in existing:
        op.add_column("checklists", sa.Column("evaluation_date_fixed", sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("checklists") as batch:
        batch.drop_column("evaluation_date_fixed")
        batch.drop_column("evaluation_date_mode")
