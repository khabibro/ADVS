"""Admin endpoints: manage workflows and their check criteria (점검 기준).

All routes live under /api/v1/admin. When `ADMIN_API_TOKEN` is configured they require the
`X-ADVS-Admin-Token` header; the admin console adds it from its own server.
"""

import hmac
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.errors import ApiErrorCode, api_error
from app.db.session import get_db
from app.models.entities import Checklist, DocumentRequirement
from app.schemas.api import (
    AdminRevisionRead,
    AdminWorkflowCreate,
    AdminWorkflowDetail,
    AdminWorkflowSummary,
    AdminWorkflowUpdate,
    Criteria,
    CriteriaCatalog,
    CriteriaSave,
    RevisionRestore,
)
from app.services import criteria as service


def require_admin(x_advs_admin_token: str | None = Header(default=None)) -> None:
    expected = get_settings().admin_api_token
    if expected and not (x_advs_admin_token and hmac.compare_digest(x_advs_admin_token, expected)):
        raise api_error(
            "ADMIN_TOKEN_REQUIRED", "Admin token required", status.HTTP_401_UNAUTHORIZED
        )


admin_router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _criteria_error(exc: service.CriteriaError) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={"code": ApiErrorCode.VALIDATION_FAILED, "message": exc.message, "field": exc.field},
    )


def _summary(db: Session, checklist: Checklist) -> dict:
    return {
        "id": checklist.id,
        "name": checklist.name,
        "description": checklist.description,
        "is_active": checklist.is_active,
        "version": checklist.version or 1,
        "document_count": len(checklist.requirements),
        "required_document_count": sum(1 for item in checklist.requirements if item.required),
        "project_count": service.project_count(db, checklist.id),
        "created_at": checklist.created_at,
        "updated_at": checklist.updated_at,
    }


def _detail(db: Session, checklist: Checklist) -> AdminWorkflowDetail:
    return AdminWorkflowDetail(
        **_summary(db, checklist), criteria=Criteria(**service.criteria_from_checklist(checklist))
    )


def _get(db: Session, workflow_id: uuid.UUID) -> Checklist:
    checklist = service.load_checklist(db, workflow_id)
    if checklist is None:
        raise api_error(ApiErrorCode.RESOURCE_NOT_FOUND, "Workflow not found", 404)
    return checklist


@admin_router.get("/catalog", response_model=CriteriaCatalog)
def get_catalog():
    return service.catalog()


@admin_router.get("/workflows", response_model=list[AdminWorkflowSummary])
def list_workflows(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Checklist)
        .options(selectinload(Checklist.requirements).selectinload(DocumentRequirement.rules))
        .order_by(Checklist.is_active.desc(), Checklist.created_at.asc())
    ).all()
    return [_summary(db, row) for row in rows]


@admin_router.post(
    "/workflows", response_model=AdminWorkflowDetail, status_code=status.HTTP_201_CREATED
)
def create_workflow(payload: AdminWorkflowCreate, db: Session = Depends(get_db)):
    source = _get(db, payload.copy_from_id) if payload.copy_from_id else None
    try:
        checklist = service.create_workflow(
            db,
            name=payload.name,
            description=payload.description,
            copy_from=source,
            criteria=payload.criteria.model_dump(mode="json") if payload.criteria else None,
            editor=payload.editor,
        )
    except service.CriteriaError as exc:
        db.rollback()
        raise _criteria_error(exc) from exc
    return _detail(db, checklist)


@admin_router.get("/workflows/{workflow_id}", response_model=AdminWorkflowDetail)
def get_workflow(workflow_id: uuid.UUID, db: Session = Depends(get_db)):
    return _detail(db, _get(db, workflow_id))


@admin_router.patch("/workflows/{workflow_id}", response_model=AdminWorkflowDetail)
def update_workflow(
    workflow_id: uuid.UUID, payload: AdminWorkflowUpdate, db: Session = Depends(get_db)
):
    checklist = _get(db, workflow_id)
    try:
        checklist = service.update_details(
            db,
            checklist,
            name=payload.name,
            description=payload.description,
            is_active=payload.is_active,
        )
    except service.CriteriaError as exc:
        db.rollback()
        raise _criteria_error(exc) from exc
    return _detail(db, checklist)


@admin_router.put("/workflows/{workflow_id}/criteria", response_model=AdminWorkflowDetail)
def save_criteria(workflow_id: uuid.UUID, payload: CriteriaSave, db: Session = Depends(get_db)):
    checklist = _get(db, workflow_id)
    try:
        checklist = service.save_criteria(
            db,
            checklist,
            payload.criteria.model_dump(mode="json"),
            editor=payload.editor,
            note=payload.note,
            expected_version=payload.expected_version,
        )
    except service.CriteriaError as exc:
        db.rollback()
        if exc.field == "version":
            raise api_error("VERSION_CONFLICT", exc.message, status.HTTP_409_CONFLICT) from exc
        raise _criteria_error(exc) from exc
    return _detail(db, checklist)


@admin_router.get("/workflows/{workflow_id}/revisions", response_model=list[AdminRevisionRead])
def list_revisions(workflow_id: uuid.UUID, db: Session = Depends(get_db)):
    _get(db, workflow_id)
    return [
        AdminRevisionRead(
            version=row.version,
            editor_label=row.editor_label,
            note=row.note,
            created_at=row.created_at,
            criteria=Criteria(**((row.snapshot or {}).get("criteria") or {})),
        )
        for row in service.revisions(db, workflow_id)
    ]


@admin_router.post(
    "/workflows/{workflow_id}/revisions/{version}/restore", response_model=AdminWorkflowDetail
)
def restore_revision(
    workflow_id: uuid.UUID, version: int, payload: RevisionRestore, db: Session = Depends(get_db)
):
    checklist = _get(db, workflow_id)
    try:
        checklist = service.restore_revision(db, checklist, version, editor=payload.editor)
    except service.CriteriaError as exc:
        db.rollback()
        raise _criteria_error(exc) from exc
    return _detail(db, checklist)
