import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_status_migration_upgrade_and_downgrade(monkeypatch) -> None:
    migration_path = (
        Path(__file__).parents[1]
        / "alembic/versions/0003_status_semantics_ready_review_required.py"
    )
    spec = importlib.util.spec_from_file_location("status_semantics_migration", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    for table_name in ("projects", "submissions"):
        sa.Table(
            table_name,
            metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("status", sa.String(40), nullable=False),
        )
    metadata.create_all(engine)

    with engine.begin() as connection:
        for table_name in ("projects", "submissions"):
            connection.execute(
                metadata.tables[table_name].insert(),
                [{"status": "PASS"}, {"status": "REVIEW"}, {"status": "NEEDS_CORRECTION"}],
            )
        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))

        migration.upgrade()
        for table_name in ("projects", "submissions"):
            statuses = connection.scalars(
                sa.select(metadata.tables[table_name].c.status).order_by(
                    metadata.tables[table_name].c.id
                )
            ).all()
            assert statuses == ["READY", "REVIEW_REQUIRED", "NEEDS_CORRECTION"]

        migration.downgrade()
        for table_name in ("projects", "submissions"):
            statuses = connection.scalars(
                sa.select(metadata.tables[table_name].c.status).order_by(
                    metadata.tables[table_name].c.id
                )
            ).all()
            assert statuses == ["PASS", "REVIEW", "NEEDS_CORRECTION"]
