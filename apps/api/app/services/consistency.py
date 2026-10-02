"""Transaction lock shared by every project-input writer and verification.

PostgreSQL serializes on the project row. SQLite (local/test deployment) takes
its write lock with a no-op UPDATE; SELECT FOR UPDATE alone is ignored there.
The lock is released only when the caller commits or rolls back. Acquire it
before loading mutable verification inputs, in project -> document order.
"""

import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.entities import Document, Project, Submission


def acquire_project_lock(db: Session, project_id: uuid.UUID) -> None:
    with db.no_autoflush:
        if db.get_bind().dialect.name == "sqlite":
            db.execute(
                update(Project)
                .where(Project.id == project_id)
                .values(status=Project.status)
                .execution_options(synchronize_session=False)
            )
        else:
            db.execute(select(Project.id).where(Project.id == project_id).with_for_update())


def lock_project(db: Session, project_id: uuid.UUID) -> Project | None:
    acquire_project_lock(db, project_id)
    with db.no_autoflush:
        return db.scalar(
            select(Project)
            .where(Project.id == project_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )


def lock_document_project(db: Session, document: Document) -> Project | None:
    project_id = db.scalar(
        select(Submission.project_id).where(Submission.id == document.submission_id)
    )
    return lock_project(db, project_id) if project_id is not None else None
