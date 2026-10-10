import logging
import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.domain import (
    DOCUMENT_TYPE_DISPLAY_NAMES,
    DocumentType,
    OverallStatus,
    ProcessingStatus,
    normalize_overall_status,
)
from app.core.errors import ApiErrorCode, api_error
from app.db.session import get_db
from app.document_intelligence.evidence_sufficiency import FieldReviewDecision
from app.document_intelligence.extraction.base import ExtractedValue
from app.document_intelligence.results import CanonicalDocumentResult
from app.document_intelligence.validation.engine import ValidationEngine
from app.document_intelligence.validation.submission import RuleConfigurationError
from app.models.entities import (
    AuditLog,
    Checklist,
    Document,
    DocumentRequirement,
    FieldReview,
    Project,
    Submission,
    User,
    ValidationResult,
)
from app.schemas.api import (
    AutoAcceptanceRead,
    ChecklistCreate,
    ChecklistRead,
    DocumentDetail,
    DocumentRead,
    FieldRead,
    FieldReviewCreate,
    FieldReviewRead,
    ProjectCreate,
    ProjectOverviewRead,
    ProjectRead,
    ReviewItemRead,
    RuleEvaluationRead,
    SubmissionVerificationRead,
    ValidationRead,
    VerificationIssueRead,
    VerificationRequest,
    WorkflowDocumentRequirementRead,
    WorkflowRead,
    WorkflowSummary,
)
from app.services.auto_acceptance import decisions_for_project
from app.services.consistency import lock_project
from app.services.document_validation import (
    validate_effective_document,
)
from app.services.overview import ProjectOverviewService
from app.services.processing import _ACTIVE_STATUSES, DocumentProcessingService
from app.services.reviews import FieldReviewService, ReviewValidationError, StaleReviewError
from app.services.storage.local import LocalStorageService, canonical_mime, sanitize_filename
from app.services.verification import (
    StoredSubmissionVerification,
    SubmissionVerificationService,
    invalidate_submission_verification,
)
from app.services.workflows import WorkflowService

router = APIRouter()
workflow_service = WorkflowService()
submission_verification_service = SubmissionVerificationService()
field_review_service = FieldReviewService()
overview_service = ProjectOverviewService()


def demo_user(db: Session) -> User:
    user = db.scalar(select(User).where(User.email == "demo@advs.local"))
    if user:
        return user
    user = User(email="demo@advs.local", display_name="Demo User")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _document_requirement_read(
    requirement: DocumentRequirement,
) -> WorkflowDocumentRequirementRead:
    document_type = DocumentType(requirement.document_type)
    return WorkflowDocumentRequirementRead(
        document_type=document_type.value,
        display_name=DOCUMENT_TYPE_DISPLAY_NAMES[document_type],
        required=requirement.required,
    )


def _workflow_read(checklist: Checklist) -> WorkflowRead:
    return WorkflowRead(
        id=checklist.id,
        name=checklist.name,
        description=checklist.description,
        is_active=checklist.is_active,
        created_at=checklist.created_at,
        document_requirements=[
            _document_requirement_read(requirement) for requirement in checklist.requirements
        ],
    )


def _project_read(project: Project) -> ProjectRead:
    checklist = project.checklist
    return ProjectRead(
        id=project.id,
        name=project.name,
        workflow_id=project.checklist_id,
        workflow=(
            WorkflowSummary(id=checklist.id, name=checklist.name, description=checklist.description)
            if checklist
            else None
        ),
        expected_documents=[
            _document_requirement_read(requirement)
            for requirement in (checklist.requirements if checklist else [])
        ],
        applicant_name=project.applicant_name,
        company_name=project.company_name,
        status=normalize_overall_status(project.status),
        created_at=project.created_at,
    )


def _verification_read(
    project: Project, stored: StoredSubmissionVerification
) -> SubmissionVerificationRead:
    result = stored.result
    return SubmissionVerificationRead(
        project_id=project.id,
        workflow_id=project.checklist_id,
        status=result.status if result else normalize_overall_status(project.status),
        evaluation_date=result.evaluation_date if result else None,
        evaluated_at=stored.evaluated_at,
        is_current=stored.is_current,
        issues=[
            VerificationIssueRead.model_validate(issue, from_attributes=True)
            for issue in (result.issues if result else ())
        ],
        notices=[
            VerificationIssueRead.model_validate(issue, from_attributes=True)
            for issue in (result.notices if result else ())
        ],
        rule_results=[
            RuleEvaluationRead.model_validate(item, from_attributes=True)
            for item in (result.rule_results if result else ())
        ],
        disclaimer=(
            "현재 설정된 점검 기준에서 확인된 문제가 없습니다."
            if result and result.status == OverallStatus.READY
            else "현재 설정된 점검 기준에 따른 사전 점검 결과입니다."
        ),
    )


def _require_active_workflow(workflow_id: uuid.UUID, db: Session) -> Checklist:
    workflow = workflow_service.get(db, workflow_id)
    if workflow is None:
        raise api_error(ApiErrorCode.RESOURCE_NOT_FOUND, "Workflow not found", 404)
    if not workflow.is_active:
        raise api_error(ApiErrorCode.VALIDATION_FAILED, "Workflow is not available", 400)
    return workflow


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/projects", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)):
    projects = db.scalars(
        select(Project)
        .options(selectinload(Project.checklist).selectinload(Checklist.requirements))
        .order_by(Project.created_at.desc())
    ).all()
    for project in sorted(projects, key=lambda item: str(item.id)):
        if project.status == OverallStatus.READY:
            submission_verification_service.get_latest(db, project.id)
    return [_project_read(project) for project in projects]


@router.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    user = demo_user(db)
    workflow = _require_active_workflow(payload.workflow_id, db)
    project = Project(
        owner_id=user.id,
        checklist_id=workflow.id,
        name=payload.name,
        applicant_name=payload.applicant_name,
        company_name=payload.company_name,
    )
    db.add(project)
    db.flush()
    db.add(Submission(project_id=project.id))
    db.commit()
    db.refresh(project)
    project.checklist = workflow
    return _project_read(project)


@router.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: uuid.UUID, db: Session = Depends(get_db)):
    project = db.scalar(
        select(Project)
        .options(selectinload(Project.checklist).selectinload(Checklist.requirements))
        .where(Project.id == project_id)
    )
    if not project:
        raise api_error(ApiErrorCode.RESOURCE_NOT_FOUND, "Project not found", 404)
    if project.status == OverallStatus.READY:
        submission_verification_service.get_latest(db, project.id)
    return _project_read(project)


@router.patch("/projects/{project_id}", response_model=ProjectRead)
def update_project(project_id: uuid.UUID, payload: ProjectCreate, db: Session = Depends(get_db)):
    lock_project(db, project_id)
    project = db.scalar(
        select(Project)
        .options(selectinload(Project.checklist).selectinload(Checklist.requirements))
        .where(Project.id == project_id)
    )
    if not project:
        raise api_error(ApiErrorCode.RESOURCE_NOT_FOUND, "Project not found", 404)
    workflow = _require_active_workflow(payload.workflow_id, db)
    project.checklist_id = workflow.id
    project.name = payload.name
    project.applicant_name = payload.applicant_name
    project.company_name = payload.company_name
    invalidate_submission_verification(db, project.id)
    db.commit()
    db.refresh(project)
    project.checklist = workflow
    return _project_read(project)


@router.get("/workflows", response_model=list[WorkflowRead])
def list_workflows(db: Session = Depends(get_db)):
    return [_workflow_read(workflow) for workflow in workflow_service.list_available(db)]


@router.get("/workflows/{workflow_id}", response_model=WorkflowRead)
def get_workflow(workflow_id: uuid.UUID, db: Session = Depends(get_db)):
    workflow = _require_active_workflow(workflow_id, db)
    return _workflow_read(workflow)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: uuid.UUID, db: Session = Depends(get_db)):
    project = lock_project(db, project_id)
    if project is None:
        raise api_error(ApiErrorCode.RESOURCE_NOT_FOUND, "Project not found", 404)
    documents = db.scalars(
        select(Document).join(Submission).where(Submission.project_id == project_id)
    ).all()
    if any(document.processing_status in _ACTIVE_STATUSES for document in documents):
        db.rollback()
        raise api_error(
            "PROCESSING_IN_PROGRESS",
            "Wait for document processing before deleting the project",
            409,
        )
    keys = [document.storage_key for document in documents]
    document_ids = [document.id for document in documents]
    db.execute(delete(FieldReview).where(FieldReview.project_id == project_id))
    db.execute(delete(ValidationResult).where(ValidationResult.project_id == project_id))
    db.execute(update(AuditLog).where(AuditLog.project_id == project_id).values(project_id=None))
    if document_ids:
        db.execute(
            update(AuditLog).where(AuditLog.document_id.in_(document_ids)).values(document_id=None)
        )
    db.delete(project)
    db.commit()
    storage = LocalStorageService(get_settings())
    for key in keys:
        try:
            storage.path_for(key).unlink(missing_ok=True)
        except OSError:
            logging.getLogger(__name__).error(
                "stored_file_cleanup_failed", extra={"project_id": str(project_id)}
            )


@router.get("/checklists", response_model=list[ChecklistRead])
def list_checklists(db: Session = Depends(get_db)):
    return db.scalars(select(Checklist).order_by(Checklist.created_at.desc())).all()


@router.post("/checklists", response_model=ChecklistRead, status_code=status.HTTP_201_CREATED)
def create_checklist(payload: ChecklistCreate, db: Session = Depends(get_db)):
    checklist = Checklist(**payload.model_dump())
    db.add(checklist)
    db.commit()
    db.refresh(checklist)
    return checklist


@router.get("/checklists/{checklist_id}", response_model=ChecklistRead)
def get_checklist(checklist_id: uuid.UUID, db: Session = Depends(get_db)):
    checklist = db.get(Checklist, checklist_id)
    if not checklist:
        raise api_error(ApiErrorCode.RESOURCE_NOT_FOUND, "Checklist not found", 404)
    return checklist


@router.patch("/checklists/{checklist_id}", response_model=ChecklistRead)
def update_checklist(
    checklist_id: uuid.UUID, payload: ChecklistCreate, db: Session = Depends(get_db)
):
    checklist = db.get(Checklist, checklist_id)
    if not checklist:
        raise api_error(ApiErrorCode.RESOURCE_NOT_FOUND, "Checklist not found", 404)
    checklist.name = payload.name
    checklist.description = payload.description
    db.commit()
    db.refresh(checklist)
    return checklist


@router.post(
    "/projects/{project_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    project_id: uuid.UUID, file: UploadFile = File(...), db: Session = Depends(get_db)
):
    lock_project(db, project_id)
    project = db.scalar(
        select(Project).options(selectinload(Project.submissions)).where(Project.id == project_id)
    )
    if not project:
        raise api_error(ApiErrorCode.RESOURCE_NOT_FOUND, "Project not found", 404)
    submission = (
        project.submissions[0] if project.submissions else Submission(project_id=project.id)
    )
    if not project.submissions:
        db.add(submission)
        db.flush()
    storage_key, size, checksum = await LocalStorageService(get_settings()).save_upload(file)
    doc = Document(
        submission_id=submission.id,
        original_filename=sanitize_filename(file.filename or "upload"),
        storage_key=storage_key,
        mime_type=canonical_mime(storage_key),
        size_bytes=size,
        checksum_sha256=checksum,
    )
    try:
        db.add(doc)
        invalidate_submission_verification(db, project.id)
        db.commit()
    except BaseException:
        db.rollback()
        LocalStorageService(get_settings()).path_for(storage_key).unlink(missing_ok=True)
        raise
    db.refresh(doc)
    return doc


@router.get("/projects/{project_id}/documents", response_model=list[DocumentRead])
def list_documents(project_id: uuid.UUID, db: Session = Depends(get_db)):
    if db.get(Project, project_id) is None:
        raise api_error(ApiErrorCode.RESOURCE_NOT_FOUND, "Project not found", 404)
    return db.scalars(
        select(Document)
        .join(Submission)
        .where(Submission.project_id == project_id)
        .order_by(Document.created_at.desc())
    ).all()


@router.get("/documents/{document_id}", response_model=DocumentDetail)
def get_document(document_id: uuid.UUID, db: Session = Depends(get_db)):
    document = db.scalar(
        select(Document)
        .options(
            selectinload(Document.extracted_fields),
            selectinload(Document.validation_results),
            selectinload(Document.field_reviews),
        )
        .where(Document.id == document_id)
    )
    if not document:
        raise api_error(ApiErrorCode.RESOURCE_NOT_FOUND, "Document not found", 404)
    detail = DocumentDetail.model_validate(document)
    canonical = CanonicalDocumentResult.from_persisted(
        document,
        verification_status=detail.overall_status,
        issues=[row.code for row in document.validation_results if not row.passed],
    )
    detail.missing_expected_fields = canonical.missing_expected_fields
    current_reviews = {
        item.field_name: item
        for item in document.field_reviews
        if item.is_current and item.processing_version == document.processing_version
    }
    detail.extracted_fields = []
    submission = db.get(Submission, document.submission_id)
    project = db.get(Project, submission.project_id) if submission else None
    decisions = decisions_for_project(db, project)
    by_name = {item.field_name: item for item in document.extracted_fields}
    for name in sorted(set(by_name) | set(current_reviews)):
        item = by_name.get(name)
        decision = decisions.get((document.id, name))
        effective = field_review_service.resolver.resolve(
            item, current_reviews.get(name), document.processing_version, decision
        )
        field_read = (
            FieldRead.model_validate(item)
            if item
            else FieldRead(
                field_name=name,
                raw_value=None,
                normalized_value=None,
                confidence=None,
                needs_review=True,
            )
        )
        field_read.evidence_assessment = effective.assessment.state
        field_read.assessment_reasons = list(effective.assessment.reasons)
        field_read.policy_version = effective.assessment.policy_version
        field_read.effective_normalized_value = effective.normalized_value
        field_read.effective_source = effective.source
        field_read.current_review_decision = (
            FieldReviewDecision(effective.review.decision) if effective.review else None
        )
        field_read.auto_acceptance = (
            AutoAcceptanceRead(**decision.to_dict()) if decision is not None else None
        )
        detail.extracted_fields.append(field_read)
    detail.missing_expected_fields = [
        name
        for name in detail.missing_expected_fields
        if not any(
            field.field_name == name and field.effective_normalized_value is not None
            for field in detail.extracted_fields
        )
    ]
    effective_fields = [
        ExtractedValue(
            field.field_name,
            field.raw_value,
            field.effective_normalized_value,
            field.confidence,
            field.effective_normalized_value is None,
        )
        for field in detail.extracted_fields
    ]
    issues, _ = validate_effective_document(
        db, document, DocumentType(document.document_type), effective_fields
    )
    detail.validation_results = [
        ValidationRead.model_validate(issue, from_attributes=True) for issue in issues
    ]
    detail.overall_status = (
        ValidationEngine().overall_status(issues)
        if document.processing_status == ProcessingStatus.COMPLETED
        and document.document_type != DocumentType.UNKNOWN
        and not (document.classification_meta or {}).get("needs_review")
        else OverallStatus.REVIEW_REQUIRED
    )
    return detail


@router.post("/documents/{document_id}/process", response_model=DocumentRead)
async def process_document(document_id: uuid.UUID, db: Session = Depends(get_db)):
    if db.get(Document, document_id) is None:
        raise api_error(ApiErrorCode.RESOURCE_NOT_FOUND, "Document not found", 404)
    return await DocumentProcessingService().process(db, document_id)


@router.get("/documents/{document_id}/processing-status")
def processing_status(document_id: uuid.UUID, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise api_error(ApiErrorCode.RESOURCE_NOT_FOUND, "Document not found", 404)
    return {"document_id": str(document.id), "status": document.processing_status}


@router.post("/projects/{project_id}/verify", response_model=SubmissionVerificationRead)
def verify_project(
    project_id: uuid.UUID,
    payload: VerificationRequest,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise api_error(ApiErrorCode.RESOURCE_NOT_FOUND, "Project not found", 404)
    try:
        stored = submission_verification_service.verify(db, project_id, payload.evaluation_date)
    except (RuleConfigurationError, ValueError) as exc:
        db.rollback()
        raise api_error(ApiErrorCode.VALIDATION_FAILED, str(exc), 400) from exc
    db.refresh(project)
    return _verification_read(project, stored)


@router.get("/projects/{project_id}/verification", response_model=SubmissionVerificationRead)
@router.get(
    "/projects/{project_id}/verification-history", response_model=SubmissionVerificationRead
)
def verification(project_id: uuid.UUID, db: Session = Depends(get_db)):
    project = db.scalar(
        select(Project)
        .options(selectinload(Project.checklist).selectinload(Checklist.requirements))
        .where(Project.id == project_id)
    )
    if not project:
        raise api_error(ApiErrorCode.RESOURCE_NOT_FOUND, "Project not found", 404)
    stored = submission_verification_service.get_latest(db, project_id)
    return _verification_read(project, stored)


@router.get("/projects/{project_id}/review-items", response_model=list[ReviewItemRead])
def review_items(project_id: uuid.UUID, db: Session = Depends(get_db)):
    items = field_review_service.review_items(db, project_id)
    if items is None:
        raise api_error(ApiErrorCode.RESOURCE_NOT_FOUND, "Project not found", 404)
    return items


@router.get("/projects/{project_id}/overview", response_model=ProjectOverviewRead)
def project_overview(project_id: uuid.UUID, db: Session = Depends(get_db)):
    overview = overview_service.build(db, project_id)
    if overview is None:
        raise api_error(ApiErrorCode.RESOURCE_NOT_FOUND, "Project not found", 404)
    return overview


@router.get("/projects/{project_id}/reviews", response_model=list[FieldReviewRead])
def list_reviews(
    project_id: uuid.UUID,
    include_history: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    if db.get(Project, project_id) is None:
        raise api_error(ApiErrorCode.RESOURCE_NOT_FOUND, "Project not found", 404)
    return field_review_service.list_reviews(db, project_id, include_history=include_history)


@router.post(
    "/projects/{project_id}/documents/{document_id}/fields/{field_name}/review",
    response_model=FieldReviewRead,
    status_code=status.HTTP_201_CREATED,
)
def review_field(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    field_name: str,
    payload: FieldReviewCreate,
    db: Session = Depends(get_db),
):
    try:
        target = field_review_service.target(db, project_id, document_id, field_name)
        if target is None:
            raise api_error(ApiErrorCode.RESOURCE_NOT_FOUND, "Review target not found", 404)
        return field_review_service.submit(
            db,
            target,
            decision=payload.decision,
            corrected_value=payload.corrected_value,
            reviewer_label=payload.reviewer_label,
            note=payload.note,
            expected_processing_version=payload.expected_processing_version,
        )
    except StaleReviewError as exc:
        db.rollback()
        raise api_error("STALE_PROCESSING_VERSION", str(exc), 409) from exc
    except ReviewValidationError as exc:
        db.rollback()
        raise api_error(ApiErrorCode.VALIDATION_FAILED, str(exc), 400) from exc
