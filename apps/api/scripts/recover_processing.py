"""Offline recovery of interrupted processing, after all API workers stop.

Run from apps/api: PYTHONPATH=. .venv312/bin/python scripts/recover_processing.py
    --document-id UUID --confirm-workers-stopped

There is intentionally no wall-clock lease reclamation: a hung native OCR
thread can outlive its request. An operator must stop every worker first.
"""

import argparse
import uuid

from sqlalchemy.orm import Session

from app.core.domain import ProcessingStatus
from app.core.errors import ProcessingErrorCode
from app.db.session import SessionLocal
from app.models.entities import AuditLog, Document
from app.services.consistency import lock_document_project
from app.services.processing import _ACTIVE_STATUSES
from app.services.verification import invalidate_document_project_verification


def recover_document(db: Session, document_id: uuid.UUID, *, workers_stopped: bool) -> bool:
    if not workers_stopped:
        raise ValueError("Stop every API/processing worker before recovery")
    document = db.get(Document, document_id)
    if document is None:
        raise LookupError("Document not found")
    project = lock_document_project(db, document)
    db.refresh(document)
    if document.processing_status not in _ACTIVE_STATUSES:
        db.rollback()
        return False
    previous_status = document.processing_status
    document.processing_status = ProcessingStatus.FAILED
    document.error_code = ProcessingErrorCode.PROCESSING_FAILED
    document.error_message = "Interrupted processing recovered offline. Retry processing."
    invalidate_document_project_verification(db, document)
    db.add(
        AuditLog(
            project_id=project.id if project else None,
            document_id=document.id,
            event_name="processing_recovered_offline",
            metadata_json={
                "previous_status": previous_status,
                "processing_version": document.processing_version,
            },
        )
    )
    db.commit()
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--document-id", type=uuid.UUID, required=True)
    parser.add_argument("--confirm-workers-stopped", action="store_true", required=True)
    args = parser.parse_args()
    with SessionLocal() as db:
        changed = recover_document(
            db, args.document_id, workers_stopped=args.confirm_workers_stopped
        )
    print("RECOVERED" if changed else "NOT_ACTIVE")


if __name__ == "__main__":
    main()
