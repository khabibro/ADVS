"""Recovery of documents that were left "in progress" by a stopped or crashed API process."""

from __future__ import annotations

import logging

from sqlalchemy import select, update

from app.core.domain import ProcessingStatus
from app.core.errors import ProcessingErrorCode
from app.db.session import SessionLocal
from app.models.entities import AuditLog, Document
from app.services.processing import _ACTIVE_STATUSES

logger = logging.getLogger(__name__)
RECOVERY_MESSAGE = "처리가 중단되어 다시 처리해야 합니다. 다시 시도해 주세요."


def recover_interrupted_documents() -> int:
    """Mark every document still in an active processing state as FAILED (retryable).

    Run once at API start, before any request is served: this deployment processes inside the API request, so a
    document that is "in progress" while no request is running is a leftover of an earlier process."""
    with SessionLocal() as db:
        stuck = db.execute(
            select(Document.id, Document.processing_status, Document.processing_version).where(
                Document.processing_status.in_([status.value for status in _ACTIVE_STATUSES])
            )
        ).all()
        for document_id, status, version in stuck:
            db.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(
                    processing_status=ProcessingStatus.FAILED,
                    error_code=ProcessingErrorCode.PROCESSING_FAILED,
                    error_message=RECOVERY_MESSAGE,
                )
            )
            db.add(
                AuditLog(
                    document_id=document_id,
                    event_name="processing_recovered_at_startup",
                    metadata_json={"previous_status": str(status), "processing_version": version},
                )
            )
        db.commit()
    if stuck:
        logger.warning("recovered %d interrupted documents at startup", len(stuck))
    return len(stuck)
