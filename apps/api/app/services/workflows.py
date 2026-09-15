import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.entities import Checklist


class WorkflowService:
    """Read-only workflow access over the existing Checklist persistence model."""

    def list_available(self, db: Session) -> list[Checklist]:
        return list(
            db.scalars(
                select(Checklist)
                .options(selectinload(Checklist.requirements))
                .where(Checklist.is_active.is_(True))
                .order_by(Checklist.created_at.desc())
            ).all()
        )

    def get(self, db: Session, workflow_id: uuid.UUID) -> Checklist | None:
        return db.scalar(
            select(Checklist)
            .options(selectinload(Checklist.requirements))
            .where(Checklist.id == workflow_id)
        )
