import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_evidence_migration_preserves_historical_rows_and_downgrades(monkeypatch) -> None:
    path = Path(__file__).parents[1] / "alembic/versions/0004_field_evidence.py"
    spec = importlib.util.spec_from_file_location("field_evidence_migration", path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    table = sa.Table(
        "extracted_fields",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("field_name", sa.String(120), nullable=False),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(table.insert(), {"field_name": "company_name"})
        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))
        migration.upgrade()
        assert "evidence" in {
            item["name"] for item in sa.inspect(connection).get_columns(table.name)
        }
        row = connection.execute(sa.text("SELECT field_name, evidence FROM extracted_fields")).one()
        assert row._mapping == {"field_name": "company_name", "evidence": None}
        migration.downgrade()
        assert "evidence" not in {
            item["name"] for item in sa.inspect(connection).get_columns(table.name)
        }
