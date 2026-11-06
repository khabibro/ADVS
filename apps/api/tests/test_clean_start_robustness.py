"""Clean-start robustness: UUID columns are TEXT on SQLite, a locked database is retried, and documents left "in
progress" by a stopped process are recovered at startup."""

from __future__ import annotations

import contextlib
import os
import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError

from app.core.domain import ProcessingStatus
from app.models.entities import AuditLog, Checklist, Document
from app.services import consistency
from app.services.startup_recovery import recover_interrupted_documents

API = Path(__file__).resolve().parents[1]
RISKY = uuid.UUID(
    "1e000000-0000-0000-0000-000000000001"
)  # digits and one "e": a float to a NUMERIC column


def test_uuid_columns_are_text_on_sqlite(db_session) -> None:
    kinds = {row[1]: row[2] for row in db_session.execute(text("PRAGMA table_info(checklists)"))}
    assert kinds["id"].upper() == "CHAR(32)"


def test_a_digits_and_e_id_survives_a_round_trip(db_session) -> None:
    db_session.add(Checklist(id=RISKY, name=f"uuid probe {uuid.uuid4().hex[:6]}"))
    db_session.commit()
    raw = db_session.execute(
        text("SELECT typeof(id), id FROM checklists WHERE name LIKE 'uuid probe%'")
    ).first()
    assert raw[0] == "text" and raw[1] == RISKY.hex
    assert db_session.get(Checklist, RISKY).id == RISKY
    db_session.delete(db_session.get(Checklist, RISKY))
    db_session.commit()


def test_the_migration_rebuilds_old_uuid_columns(tmp_path) -> None:
    database = tmp_path / "old.db"
    with contextlib.closing(sqlite3.connect(database)) as raw:
        raw.execute(
            "CREATE TABLE users (id UUID NOT NULL PRIMARY KEY, email VARCHAR(255) NOT NULL)"
        )
        raw.execute("INSERT INTO users VALUES ('aaaaaaaabbbbccccddddeeeeeeeeeeee', 'a@b.c')")
        raw.commit()
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{database}", "PYTHONPATH": str(API)}
    for args in (["stamp", "0008_checklist_revisions"], ["upgrade", "0009_uuid_text_affinity"]):
        subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=API,
            env=env,
            check=True,
            capture_output=True,
        )
    with contextlib.closing(sqlite3.connect(database)) as raw:
        kinds = {row[1]: row[2] for row in raw.execute("PRAGMA table_info(users)")}
        assert kinds["id"].upper() == "CHAR(32)"
        assert (
            raw.execute("SELECT id FROM users").fetchone()[0] == "aaaaaaaabbbbccccddddeeeeeeeeeeee"
        )


def _pdf() -> bytes:
    import fitz

    document = fitz.open()
    document.new_page().insert_text((60, 60), "sample", fontsize=12)
    return document.tobytes()


class _FlakySession:
    """Fails with 'database is locked' a number of times, then works."""

    def __init__(self, failures: int) -> None:
        self.failures, self.calls, self.rollbacks = failures, 0, 0

    def get_bind(self):
        return type("Bind", (), {"dialect": type("Dialect", (), {"name": "sqlite"})()})()

    @property
    def no_autoflush(self):
        return contextlib.nullcontext()

    def execute(self, *_args, **_kwargs) -> None:
        self.calls += 1
        if self.calls <= self.failures:
            raise OperationalError("UPDATE", {}, Exception("database is locked"))

    def rollback(self) -> None:
        self.rollbacks += 1


def test_a_locked_database_is_retried(monkeypatch) -> None:
    monkeypatch.setattr(consistency.time, "sleep", lambda _s: None)
    session = _FlakySession(failures=2)
    consistency.acquire_project_lock(session, uuid.uuid4())  # type: ignore[arg-type]
    assert session.calls == 3 and session.rollbacks == 2


def test_another_error_is_not_swallowed(monkeypatch) -> None:
    monkeypatch.setattr(consistency.time, "sleep", lambda _s: None)

    class Broken(_FlakySession):
        def execute(self, *_a, **_k) -> None:
            raise OperationalError("UPDATE", {}, Exception("no such table"))

    with pytest.raises(OperationalError):
        consistency.acquire_project_lock(Broken(0), uuid.uuid4())  # type: ignore[arg-type]


def test_interrupted_documents_are_recovered_at_startup(client, db_session) -> None:
    checklist = db_session.scalar(select(Checklist).limit(1))
    if checklist is None:
        import runpy

        runpy.run_path(str(API.parents[1] / "scripts" / "seed.py"))["main"]()
        checklist = db_session.scalar(select(Checklist).limit(1))
    project = client.post(
        "/api/v1/projects", json={"name": "stuck", "workflow_id": str(checklist.id)}
    ).json()
    upload = client.post(
        f"/api/v1/projects/{project['id']}/documents",
        files={"file": ("a.pdf", _pdf(), "application/pdf")},
    ).json()
    db_session.execute(
        text("UPDATE documents SET processing_status='OCR_PROCESSING' WHERE id=:i"),
        {"i": uuid.UUID(upload["id"]).hex},
    )
    db_session.commit()
    assert recover_interrupted_documents() >= 1
    db_session.expire_all()
    document = db_session.get(Document, uuid.UUID(upload["id"]))
    assert document.processing_status == ProcessingStatus.FAILED
    assert db_session.scalar(
        select(AuditLog).where(
            AuditLog.document_id == document.id,
            AuditLog.event_name == "processing_recovered_at_startup",
        )
    )
