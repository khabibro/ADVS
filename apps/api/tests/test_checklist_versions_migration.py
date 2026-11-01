"""Migration 0008 on a database seeded the old way: v1 is published, submissions are pinned."""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

import sqlalchemy as sa

API = Path(__file__).resolve().parents[1]


def alembic(url: str, *args: str) -> None:
    env = {**os.environ, "DATABASE_URL": url, "PYTHONPATH": str(API)}
    subprocess.run(
        [sys.executable, "-m", "alembic", *args], cwd=API, env=env, check=True, capture_output=True
    )


def test_seeded_checklists_become_v1_and_projects_are_pinned(tmp_path) -> None:
    url = f"sqlite:///{tmp_path}/m.db"
    alembic(url, "upgrade", "0007_access_check_date")
    engine = sa.create_engine(url)
    student, custom, owner, project = (uuid.uuid4().hex for _ in range(4))
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO checklists (id, name, is_active) VALUES (:i, '학생 제출서류 점검', 1)"
            ),
            {"i": student},
        )
        connection.execute(
            sa.text(
                "INSERT INTO checklists (id, name, is_active) VALUES (:i, '직접 만든 업무', 1)"
            ),
            {"i": custom},
        )
        connection.execute(
            sa.text("INSERT INTO users (id, email, display_name) VALUES (:i, 'a@b.c', 'x')"),
            {"i": owner},
        )
        connection.execute(
            sa.text(
                "INSERT INTO projects (id, owner_id, checklist_id, name, status, access_token)"
                " VALUES (:i, :o, :c, 'p', 'REVIEW_REQUIRED', 'tok')"
            ),
            {"i": project, "o": owner, "c": student},
        )

    alembic(url, "upgrade", "head")
    with engine.connect() as connection:
        rows = connection.execute(
            sa.text(
                "SELECT c.name, c.key, v.number, v.status FROM checklists c"
                " LEFT JOIN checklist_versions v ON v.checklist_id = c.id ORDER BY c.name"
            )
        ).all()
        assert [tuple(r) for r in rows] == [
            ("직접 만든 업무", None, None, None),  # not a seeded one: stays on its rows
            ("학생 제출서류 점검", "student", 1, "PUBLISHED"),
        ]
        pinned = connection.execute(
            sa.text(
                "SELECT v.number FROM projects p JOIN checklist_versions v"
                " ON v.id = p.checklist_version_id"
            )
        ).scalar_one()
        assert pinned == 1

    alembic(url, "downgrade", "0007_access_check_date")
    assert "checklist_versions" not in sa.inspect(engine).get_table_names()
    alembic(url, "upgrade", "head")  # and forward again
    assert "checklist_versions" in sa.inspect(engine).get_table_names()
