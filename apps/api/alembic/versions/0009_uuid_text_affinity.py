"""Store UUID columns as TEXT on SQLite.

Revision ID: 0009_uuid_text_affinity
Revises: 0008_checklist_revisions

A column declared "UUID" gets NUMERIC affinity in SQLite: a hex id made of digits and one "e" was turned into a float
(even infinity) and the row became unreadable. The columns are rebuilt as CHAR(32) (TEXT affinity); the stored hex
strings are copied unchanged. Other databases are not touched.
"""

import warnings
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_uuid_text_affinity"
down_revision: str | None = "0008_checklist_revisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        return
    tables = [
        row[0]
        for row in bind.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "AND name != 'alembic_version'"
        )
    ]
    for table in tables:
        uuid_columns = [
            row[1]
            for row in bind.exec_driver_sql(f'PRAGMA table_info("{table}")')
            if str(row[2]).upper() == "UUID"
        ]
        if not uuid_columns:
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with op.batch_alter_table(table, recreate="always") as batch:
                for column in uuid_columns:
                    batch.alter_column(column, type_=sa.CHAR(32))


def downgrade() -> None:
    pass
