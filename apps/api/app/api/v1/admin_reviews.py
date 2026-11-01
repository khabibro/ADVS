"""Reviewer queue for staff: open items across submissions, one item with its evidence, the log.

Off (404) unless ADMIN_ENABLED, like the other admin routes. Decisions are made through the
existing review endpoint; this module only reads.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.checklists.catalog import document_label, field_label
from app.core.access import require_admin
from app.core.errors import ApiErrorCode, api_error
from app.db.session import get_db
from app.models.entities import Document, Project
from app.schemas.admin_reviews import (
    QueueRead,
    ReviewDetailRead,
    ReviewLogRead,
)
from app.services.pages import EvidenceBoxNormalizer, page_infos
from app.services.review_queue import SORTS, STATUS_FILTERS, QueueFilter, ReviewQueueService
from app.services.reviews import FieldReviewService

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])
queue = ReviewQueueService()
reviews = FieldReviewService()


@router.get("/review-queue", response_model=QueueRead)
def review_queue(
    status: str = Query(default="OPEN"),
    workflow: str | None = None,
    document_type: str | None = None,
    field_name: str | None = None,
    q: str | None = Query(default=None, max_length=100),
    sort: str = Query(default="OLDEST"),
    include_drafts: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    if status not in STATUS_FILTERS or sort not in SORTS:
        raise api_error(ApiErrorCode.VALIDATION_FAILED, "Unknown status or sort", 400)
    rows, facets = queue.rows(
        db, QueueFilter(status, workflow, document_type, field_name, q, sort, include_drafts)
    )
    return QueueRead(total=len(rows), items=rows[offset : offset + limit], facets=facets)


@router.get(
    "/review-queue/{project_id}/{document_id}/{field_name}", response_model=ReviewDetailRead
)
def review_detail(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    field_name: str,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    document = db.get(Document, document_id)
    items = reviews.review_items(db, project_id)
    if project is None or document is None or items is None:
        raise api_error(ApiErrorCode.RESOURCE_NOT_FOUND, "Review item not found", 404)
    item = next(
        (i for i in items if i["document_id"] == document_id and i["field_name"] == field_name),
        None,
    )
    if item is None:
        # Already decided and now sufficient, or never needed review: say so instead of 404.
        return ReviewDetailRead(
            project_id=project_id,
            project_name=project.name,
            applicant_name=project.applicant_name,
            company_name=project.company_name,
            document_id=document_id,
            document_label=document_label(document.document_type),
            field_name=field_name,
            field_label=field_label(field_name),
            open=False,
            item=None,
            pages=[],
            siblings=[],
            history=_history(db, project_id, document_id, field_name),
        )
    normalizer = EvidenceBoxNormalizer(document)
    for evidence in item.get("evidence") or []:
        box = normalizer.normalize(evidence)
        evidence["normalized_box"] = box.model_dump() if box else None
    try:
        pages = page_infos(document)
    except (OSError, RuntimeError, ValueError):
        pages = []
    siblings = [
        {
            "document_id": i["document_id"],
            "document_label": document_label(i["document_type"]),
            "field_name": i["field_name"],
            "field_label": field_label(i["field_name"]),
            "queue_status": i["queue_status"],
        }
        for i in items
        if not (i["document_id"] == document_id and i["field_name"] == field_name)
    ]
    return ReviewDetailRead(
        project_id=project_id,
        project_name=project.name,
        applicant_name=project.applicant_name,
        company_name=project.company_name,
        document_id=document_id,
        document_label=document_label(document.document_type),
        field_name=field_name,
        field_label=field_label(field_name),
        open=True,
        item=item,
        pages=pages,
        siblings=siblings,
        history=_history(db, project_id, document_id, field_name),
    )


def _history(db: Session, project_id: uuid.UUID, document_id: uuid.UUID, field_name: str):
    return [
        r
        for r in reviews.list_reviews(db, project_id, include_history=True)
        if r.document_id == document_id and r.field_name == field_name
    ]


@router.get("/review-log", response_model=ReviewLogRead)
def review_log(
    decision: str | None = Query(
        default=None, pattern="^(CONFIRMED|CORRECTED|REJECTED|CANNOT_DETERMINE)$"
    ),
    project_id: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    total, items = queue.log(
        db, decision=decision, project_id=project_id, limit=limit, offset=offset
    )
    return ReviewLogRead(total=total, items=items)
