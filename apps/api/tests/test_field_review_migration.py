import importlib.util
import uuid
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_field_review_migration_preserves_phase6_rows_and_round_trips(monkeypatch) -> None:
    path = Path(__file__).parents[1] / "alembic/versions/0006_field_reviews.py"
    spec = importlib.util.spec_from_file_location("field_review_migration", path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    projects = sa.Table("projects", metadata, sa.Column("id", sa.Uuid(), primary_key=True))
    documents = sa.Table(
        "documents",
        metadata,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_marker", sa.String()),
    )
    sa.Table(
        "extracted_fields",
        metadata,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id")),
    )
    validation = sa.Table(
        "validation_results",
        metadata,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(100), nullable=False),
    )
    metadata.create_all(engine)
    project_id = uuid.uuid4()
    document_id = uuid.uuid4()
    validation_id = uuid.uuid4()

    with engine.begin() as connection:
        connection.execute(projects.insert(), {"id": project_id})
        connection.execute(documents.insert(), {"id": document_id, "project_marker": "historical"})
        connection.execute(validation.insert(), {"id": validation_id, "code": "RULE_PASSED"})
        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))
        migration.upgrade()
        assert "processing_version" in {
            item["name"] for item in sa.inspect(connection).get_columns("documents")
        }
        assert sa.inspect(connection).has_table("field_reviews")
        historical = connection.execute(
            sa.text("SELECT project_marker, processing_version FROM documents")
        ).one()
        assert historical._mapping == {
            "project_marker": "historical",
            "processing_version": 0,
        }
        assert (
            connection.execute(
                sa.text("SELECT code FROM validation_results WHERE id = :id"),
                {"id": validation_id.hex},
            ).scalar_one()
            == "RULE_PASSED"
        )

        migration.downgrade()
        assert not sa.inspect(connection).has_table("field_reviews")
        assert "processing_version" not in {
            item["name"] for item in sa.inspect(connection).get_columns("documents")
        }

        migration.upgrade()
        assert sa.inspect(connection).has_table("field_reviews")
        assert (
            connection.execute(sa.text("SELECT code FROM validation_results")).scalar_one()
            == "RULE_PASSED"
        )
