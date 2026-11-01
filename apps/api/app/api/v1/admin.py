"""Checklist administration: catalogue, drafts, publishing, history, rollback and the change log.

Every route is off (404) unless ADMIN_ENABLED, like the other admin endpoints, and stays so until
staff accounts exist. The actor recorded in the change log is therefore a placeholder.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.checklists.catalog import build_catalog
from app.checklists.diff import diff_documents
from app.checklists.guardrails import guardrails
from app.checklists.schema import parse_document
from app.checklists.sentences import describe
from app.checklists.service import ACTOR_NO_LOGIN, ChecklistError, ChecklistService
from app.core.access import require_admin
from app.core.errors import ApiErrorCode, api_error
from app.db.session import get_db
from app.models.entities import AuditLog, Checklist, ChecklistVersion, Project
from app.schemas.admin import (
    AdminWorkflowRead,
    AdminWorkflowSummary,
    AuditRead,
    ChecklistCheckRead,
    DiffRead,
    DocumentCheck,
    DraftSave,
    DraftSaved,
    PreviewRead,
    ProblemRead,
    PublishRequest,
    RollbackRequest,
    VersionRead,
    VersionSummary,
    WarningRead,
)

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])
service = ChecklistService()


def _raise(error: ChecklistError) -> HTTPException:
    return HTTPException(
        status_code=error.status,
        detail={
            "code": error.code,
            "message": error.message_ko,
            "problems": [p.model_dump() for p in error.problems],
        },
    )


def _checklist(db: Session, workflow_id: uuid.UUID) -> Checklist:
    checklist = db.get(Checklist, workflow_id)
    if checklist is None or checklist.key is None:
        raise api_error(ApiErrorCode.RESOURCE_NOT_FOUND, "Workflow not found", 404)
    return checklist


def _summary(version: ChecklistVersion) -> dict:
    return {
        "number": version.number,
        "status": version.status,
        "revision": version.revision,
        "change_note": version.change_note,
        "created_by": version.created_by,
        "published_by": version.published_by,
        "published_at": version.published_at,
        "rolled_back_to_number": version.rolled_back_to_number,
        "document_sha256": version.document_sha256,
    }


def _version_read(
    db: Session, version: ChecklistVersion, base: ChecklistVersion | None = None
) -> VersionRead:
    base_document = base.document if base is not None and base.id != version.id else None
    warnings = guardrails(version.document, base_document) if version.document else []
    return VersionRead(
        **_summary(version),
        id=version.id,
        document=version.document,
        sentences=describe(version.document) if version.document else {},
        warnings=[WarningRead(**w.model_dump()) for w in warnings],
    )


@router.get("/catalog")
def catalog() -> dict:
    return build_catalog()


@router.get("/workflows", response_model=list[AdminWorkflowSummary])
def list_workflows(db: Session = Depends(get_db)):
    out = []
    for checklist in db.scalars(
        select(Checklist).where(Checklist.key.is_not(None)).order_by(Checklist.created_at)
    ).all():
        published = service.published(db, checklist.id)
        draft = service.draft(db, checklist.id)
        last = [v.published_at for v in service.history(db, checklist.id) if v.published_at]
        out.append(
            AdminWorkflowSummary(
                id=checklist.id,
                key=checklist.key,
                name=checklist.name,
                published_number=published.number if published else None,
                has_draft=draft is not None,
                projects=db.scalar(
                    select(func.count())
                    .select_from(Project)
                    .where(Project.checklist_id == checklist.id)
                )
                or 0,
                last_changed_at=max(last) if last else None,
            )
        )
    return out


@router.get("/workflows/{workflow_id}", response_model=AdminWorkflowRead)
def get_workflow(workflow_id: uuid.UUID, db: Session = Depends(get_db)):
    checklist = _checklist(db, workflow_id)
    published = service.published(db, checklist.id)
    draft = service.draft(db, checklist.id)
    return AdminWorkflowRead(
        id=checklist.id,
        key=checklist.key,
        name=checklist.name,
        published=_version_read(db, published) if published else None,
        draft=_version_read(db, draft, published) if draft else None,
    )


@router.get("/workflows/{workflow_id}/versions", response_model=list[VersionSummary])
def list_versions(workflow_id: uuid.UUID, db: Session = Depends(get_db)):
    checklist = _checklist(db, workflow_id)
    return [VersionSummary(**_summary(v)) for v in service.history(db, checklist.id)]


@router.get("/workflows/{workflow_id}/versions/{number}", response_model=VersionRead)
def get_version(workflow_id: uuid.UUID, number: int, db: Session = Depends(get_db)):
    checklist = _checklist(db, workflow_id)
    try:
        return _version_read(db, service.version(db, checklist.id, number))
    except ChecklistError as error:
        raise _raise(error) from error


@router.put("/workflows/{workflow_id}/draft", response_model=DraftSaved)
def save_draft(workflow_id: uuid.UUID, payload: DraftSave, db: Session = Depends(get_db)):
    checklist = _checklist(db, workflow_id)
    try:
        result = service.save_draft(
            db, checklist, payload.document, payload.expected_revision, ACTOR_NO_LOGIN
        )
    except ChecklistError as error:
        raise _raise(error) from error
    if result.problems:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "CHECKLIST_INVALID",
                "message": "고쳐야 할 항목이 있습니다.",
                "problems": [p.model_dump() for p in result.problems],
            },
        )
    return DraftSaved(
        saved=True, draft=_version_read(db, result.version, service.published(db, checklist.id))
    )


@router.post("/workflows/{workflow_id}/validate", response_model=ChecklistCheckRead)
def validate(workflow_id: uuid.UUID, payload: DocumentCheck, db: Session = Depends(get_db)):
    """Stateless check of an unsaved edit: what is wrong, the rule sentences and the warnings."""
    checklist = _checklist(db, workflow_id)
    document, problems = parse_document(payload.document)
    if document is None or problems:
        return ChecklistCheckRead(problems=[ProblemRead(**p.model_dump()) for p in problems])
    content = document.to_json()
    base = service.published(db, checklist.id)
    return ChecklistCheckRead(
        problems=[],
        sentences=describe(content),
        warnings=[
            WarningRead(**w.model_dump())
            for w in guardrails(content, base.document if base else None)
        ],
    )


@router.post("/workflows/{workflow_id}/draft/preview", response_model=PreviewRead)
def preview(workflow_id: uuid.UUID, db: Session = Depends(get_db)):
    checklist = _checklist(db, workflow_id)
    try:
        results = service.preview(db, checklist)
    except ChecklistError as error:
        raise _raise(error) from error
    return PreviewRead(
        corpora=[r.to_json() for r in results["corpora"]],
        scenarios=results["scenarios"].to_json(),
        submissions=results["submissions"].to_json(),
    )


@router.delete("/workflows/{workflow_id}/draft", status_code=status.HTTP_204_NO_CONTENT)
def discard_draft(workflow_id: uuid.UUID, db: Session = Depends(get_db)):
    checklist = _checklist(db, workflow_id)
    try:
        service.discard_draft(db, checklist, ACTOR_NO_LOGIN)
    except ChecklistError as error:
        raise _raise(error) from error


@router.post("/workflows/{workflow_id}/publish", response_model=VersionRead)
def publish(workflow_id: uuid.UUID, payload: PublishRequest, db: Session = Depends(get_db)):
    checklist = _checklist(db, workflow_id)
    try:
        version = service.publish(
            db,
            checklist,
            payload.change_note,
            payload.acknowledged_warnings,
            ACTOR_NO_LOGIN,
            payload.expected_revision,
        )
    except ChecklistError as error:
        raise _raise(error) from error
    return _version_read(db, version)


@router.post("/workflows/{workflow_id}/rollback", response_model=VersionRead)
def rollback(workflow_id: uuid.UUID, payload: RollbackRequest, db: Session = Depends(get_db)):
    checklist = _checklist(db, workflow_id)
    try:
        version = service.rollback(
            db, checklist, payload.to_version, payload.change_note, ACTOR_NO_LOGIN
        )
    except ChecklistError as error:
        raise _raise(error) from error
    return _version_read(db, version)


@router.get("/workflows/{workflow_id}/diff", response_model=DiffRead)
def diff(
    workflow_id: uuid.UUID,
    from_: int | None = Query(default=None, alias="from"),
    to: int | None = None,
    db: Session = Depends(get_db),
):
    """Changes from version ``from`` to ``to``; ``to`` omitted means the draft, ``from`` omitted
    means the published version."""
    checklist = _checklist(db, workflow_id)
    try:
        old = (
            service.version(db, checklist.id, from_)
            if from_ is not None
            else service.published(db, checklist.id)
        )
        new = (
            service.version(db, checklist.id, to)
            if to is not None
            else service.draft(db, checklist.id)
        )
    except ChecklistError as error:
        raise _raise(error) from error
    if old is None or new is None:
        raise api_error(ApiErrorCode.RESOURCE_NOT_FOUND, "Nothing to compare", 404)
    return DiffRead(
        from_number=old.number,
        to_number=new.number,
        changes=diff_documents(old.document, new.document),
    )


@router.get("/audit", response_model=list[AuditRead])
def audit(limit: int = 100, checklist_id: uuid.UUID | None = None, db: Session = Depends(get_db)):
    query = (
        select(AuditLog)
        .where(AuditLog.checklist_id.is_not(None))
        .order_by(AuditLog.created_at.desc())
        .limit(min(max(limit, 1), 500))
    )
    if checklist_id is not None:
        query = query.where(AuditLog.checklist_id == checklist_id)
    out = []
    for row in db.scalars(query).all():
        checklist = db.get(Checklist, row.checklist_id) if row.checklist_id else None
        version = db.get(ChecklistVersion, row.version_id) if row.version_id else None
        metadata = dict(row.metadata_json or {})
        out.append(
            AuditRead(
                id=row.id,
                at=row.created_at,
                event=row.event_name,
                actor=metadata.pop("actor", None),
                checklist_id=row.checklist_id,
                checklist_name=checklist.name if checklist else None,
                version_number=version.number if version else None,
                detail=metadata,
            )
        )
    return out
