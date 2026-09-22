import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_submission_verification_migration_preserves_rows_and_downgrades(monkeypatch) -> None:
    path = Path(__file__).parents[1] / "alembic/versions/0005_submission_verification.py"
    spec = importlib.util.spec_from_file_location("submission_verification_migration", path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    table = sa.Table(
        "validation_results",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(100), nullable=False),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(table.insert(), {"code": "HISTORICAL_RESULT"})
        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))
        migration.upgrade()
        columns = {item["name"] for item in sa.inspect(connection).get_columns(table.name)}
        assert {"scope", "outcome", "details"}.issubset(columns)
        row = connection.execute(
            sa.text("SELECT code, scope, outcome, details FROM validation_results")
        ).one()
        assert row._mapping == {
            "code": "HISTORICAL_RESULT",
            "scope": None,
            "outcome": None,
            "details": None,
        }

        migration.downgrade()
        columns = {item["name"] for item in sa.inspect(connection).get_columns(table.name)}
        assert "scope" not in columns
        assert "outcome" not in columns
        assert "details" not in columns
