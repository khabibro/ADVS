"""Versioned checklists: version table, pinned submissions, audit columns.

Revision ID: 0008_checklist_versions
Revises: 0007_access_check_date

Data step: the two seeded checklists (matched by name) get their v1 template as published version 1
and every submission of them is pinned to it. Other checklists keep running on their old rows (no
key, no version) until they are recreated.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "0008_checklist_versions"
down_revision: str | None = "0007_access_check_date"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEEDED = {"기업 제출서류 점검": "business", "학생 제출서류 점검": "student"}


def _has_column(table: str, column: str) -> bool:
    return column in {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("checklist_versions"):
        op.create_table(
            "checklist_versions",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("checklist_id", sa.Uuid(), sa.ForeignKey("checklists.id"), nullable=False),
            sa.Column("number", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("document", sa.JSON(), nullable=False),
            sa.Column("document_sha256", sa.String(64), nullable=False),
            sa.Column("schema_version", sa.String(40), nullable=False),
            sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("change_note", sa.String(500), nullable=True),
            sa.Column("created_by", sa.String(120), nullable=True),
            sa.Column("published_by", sa.String(120), nullable=True),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "parent_version_id",
                sa.Uuid(),
                sa.ForeignKey("checklist_versions.id"),
                nullable=True,
            ),
            sa.Column("rolled_back_to_number", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index(
            "ix_checklist_versions_checklist_id", "checklist_versions", ["checklist_id"]
        )
        op.create_index("ix_checklist_versions_status", "checklist_versions", ["status"])
        op.create_index(
            "uq_checklist_versions_number",
            "checklist_versions",
            ["checklist_id", "number"],
            unique=True,
        )
        for name, status in (
            ("uq_checklist_versions_one_draft", "DRAFT"),
            ("uq_checklist_versions_one_published", "PUBLISHED"),
        ):
            op.create_index(
                name,
                "checklist_versions",
                ["checklist_id"],
                unique=True,
                sqlite_where=sa.text(f"status = '{status}'"),
                postgresql_where=sa.text(f"status = '{status}'"),
            )
    if not _has_column("checklists", "key"):
        with op.batch_alter_table("checklists") as batch:
            batch.add_column(sa.Column("key", sa.String(40), nullable=True))
            batch.create_unique_constraint("uq_checklists_key", ["key"])
    for column in ("checklist_version_id", "verified_version_id"):
        if not _has_column("projects", column):
            with op.batch_alter_table("projects") as batch:
                batch.add_column(sa.Column(column, sa.Uuid(), nullable=True))
                batch.create_foreign_key(
                    f"fk_projects_{column}", "checklist_versions", [column], ["id"]
                )
    if "ix_projects_checklist_version_id" not in {
        i["name"] for i in sa.inspect(bind).get_indexes("projects")
    }:
        op.create_index("ix_projects_checklist_version_id", "projects", ["checklist_version_id"])
    if not _has_column("audit_logs", "checklist_id"):
        with op.batch_alter_table("audit_logs") as batch:
            batch.add_column(sa.Column("checklist_id", sa.Uuid(), nullable=True))
            batch.add_column(sa.Column("version_id", sa.Uuid(), nullable=True))
            batch.create_foreign_key(
                "fk_audit_logs_checklist_id", "checklists", ["checklist_id"], ["id"]
            )
            batch.create_foreign_key(
                "fk_audit_logs_version_id", "checklist_versions", ["version_id"], ["id"]
            )
        op.create_index("ix_audit_logs_checklist_id", "audit_logs", ["checklist_id"])
    _backfill(bind)


def _backfill(bind) -> None:
    from app.checklists.schema import document_sha256, parse_document
    from app.checklists.service import TEMPLATE_FILES, load_template

    checklists = sa.table(
        "checklists",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("key", sa.String()),
    )
    versions = sa.table(
        "checklist_versions",
        sa.column("id", sa.Uuid()),
        sa.column("checklist_id", sa.Uuid()),
        sa.column("number", sa.Integer()),
        sa.column("status", sa.String()),
        sa.column("document", sa.JSON()),
        sa.column("document_sha256", sa.String()),
        sa.column("schema_version", sa.String()),
        sa.column("revision", sa.Integer()),
        sa.column("change_note", sa.String()),
        sa.column("created_by", sa.String()),
        sa.column("published_by", sa.String()),
        sa.column("published_at", sa.DateTime(timezone=True)),
    )
    projects = sa.table(
        "projects",
        sa.column("checklist_id", sa.Uuid()),
        sa.column("checklist_version_id", sa.Uuid()),
    )
    for row in bind.execute(sa.select(checklists.c.id, checklists.c.name, checklists.c.key)).all():
        key = SEEDED.get(row.name)
        if key is None or key not in TEMPLATE_FILES or row.key is not None:
            continue
        if bind.execute(sa.select(versions.c.id).where(versions.c.checklist_id == row.id)).first():
            continue
        document, problems = parse_document(load_template(key))
        assert document is not None and not problems
        content = document.to_json()
        version_id = uuid.uuid4()
        bind.execute(
            versions.insert().values(
                id=version_id,
                checklist_id=row.id,
                number=1,
                status="PUBLISHED",
                document=content,
                document_sha256=document_sha256(content),
                schema_version=content["schema"],
                revision=1,
                change_note="기존 점검 기준을 1번째 버전으로 등록",
                created_by="migration",
                published_by="migration",
                published_at=datetime.now(UTC),
            )
        )
        bind.execute(checklists.update().where(checklists.c.id == row.id).values(key=key))
        bind.execute(
            projects.update()
            .where(projects.c.checklist_id == row.id)
            .values(checklist_version_id=version_id)
        )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_checklist_id", table_name="audit_logs")
    with op.batch_alter_table("audit_logs") as batch:
        batch.drop_column("version_id")
        batch.drop_column("checklist_id")
    op.drop_index("ix_projects_checklist_version_id", table_name="projects")
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("verified_version_id")
        batch.drop_column("checklist_version_id")
    with op.batch_alter_table("checklists") as batch:
        batch.drop_column("key")
    op.drop_table("checklist_versions")
