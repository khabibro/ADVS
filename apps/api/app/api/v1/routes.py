import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.domain import (
    DOCUMENT_TYPE_DISPLAY_NAMES,
    EXPECTED_FIELDS,
    DocumentType,
    OverallStatus,
    ProcessingStatus,
    normalize_overall_status,
)
from app.core.errors import ApiErrorCode, api_error
from app.db.session import get_db
from app.document_intelligence.validation.engine import ValidationEngine
from app.models.entities import (
    Checklist,
    Document,
    DocumentRequirement,
    Project,
    Submission,
    User,
)
from app.schemas.api import (
    ChecklistCreate,
    ChecklistRead,
    DocumentDetail,
    DocumentRead,
    ProjectCreate,
    ProjectRead,
    WorkflowDocumentRequirementRead,
    WorkflowRead,
    WorkflowSummary,
)
from app.services.processing import DocumentProcessingService
from app.services.storage.local import LocalStorageService, sanitize_filename
from app.services.workflows import WorkflowService

router = APIRouter()
workflow_service = WorkflowService()


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
    return _project_read(project)


@router.patch("/projects/{project_id}", response_model=ProjectRead)
def update_project(project_id: uuid.UUID, payload: ProjectCreate, db: Session = Depends(get_db)):
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
    project = db.get(Project, project_id)
    if project:
        db.delete(project)
        db.commit()


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
        mime_type=file.content_type or "",
        size_bytes=size,
        checksum_sha256=checksum,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/projects/{project_id}/documents", response_model=list[DocumentRead])
def list_documents(project_id: uuid.UUID, db: Session = Depends(get_db)):
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
        .options(selectinload(Document.extracted_fields), selectinload(Document.validation_results))
        .where(Document.id == document_id)
    )
    if not document:
        raise api_error(ApiErrorCode.RESOURCE_NOT_FOUND, "Document not found", 404)
    detail = DocumentDetail.model_validate(document)
    expected = EXPECTED_FIELDS[DocumentType(document.document_type)]
    extracted = {
        field.field_name
        for field in document.extracted_fields
        if field.normalized_value is not None
    }
    detail.missing_expected_fields = [name for name in expected if name not in extracted]
    detail.overall_status = ValidationEngine().overall_status(document.validation_results)
    return detail


@router.post("/documents/{document_id}/process", response_model=DocumentRead)
async def process_document(document_id: uuid.UUID, db: Session = Depends(get_db)):
    return await DocumentProcessingService().process(db, document_id)


@router.get("/documents/{document_id}/processing-status")
def processing_status(document_id: uuid.UUID, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise api_error(ApiErrorCode.RESOURCE_NOT_FOUND, "Document not found", 404)
    return {"document_id": str(document.id), "status": document.processing_status}


@router.post("/projects/{project_id}/verify")
def verify_project(project_id: uuid.UUID, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise api_error(ApiErrorCode.RESOURCE_NOT_FOUND, "Project not found", 404)
    docs = list_documents(project_id, db)
    engine = ValidationEngine()

    if not docs:
        status_value = OverallStatus.NEEDS_CORRECTION
    elif any(doc.processing_status == ProcessingStatus.FAILED for doc in docs):
        status_value = OverallStatus.NEEDS_CORRECTION
    else:
        statuses = [engine.overall_status(doc.validation_results) for doc in docs]
        if project.checklist_id:
            requirements = db.scalars(
                select(DocumentRequirement).where(
                    DocumentRequirement.checklist_id == project.checklist_id,
                    DocumentRequirement.required.is_(True),
                )
            ).all()
            required_types = [DocumentType(r.document_type) for r in requirements]
            present_types = {
                DocumentType(d.document_type)
                for d in docs
                if d.processing_status == ProcessingStatus.COMPLETED
            }
            missing_issues = engine.validate_required_documents(required_types, present_types)
            if missing_issues:
                statuses.append(engine.overall_status(missing_issues))
        if OverallStatus.NEEDS_CORRECTION in statuses:
            status_value = OverallStatus.NEEDS_CORRECTION
        elif OverallStatus.REVIEW_REQUIRED in statuses:
            status_value = OverallStatus.REVIEW_REQUIRED
        else:
            status_value = OverallStatus.READY

    project.status = str(status_value)
    db.commit()
    return {
        "project_id": str(project_id),
        "status": str(status_value),
        "document_count": len(docs),
    }


@router.get("/projects/{project_id}/verification")
@router.get("/projects/{project_id}/verification-history")
def verification(project_id: uuid.UUID, db: Session = Depends(get_db)):
    project = db.scalar(
        select(Project)
        .options(selectinload(Project.checklist).selectinload(Checklist.requirements))
        .where(Project.id == project_id)
    )
    if not project:
        raise api_error(ApiErrorCode.RESOURCE_NOT_FOUND, "Project not found", 404)
    docs = list_documents(project_id, db)
    return {"project": _project_read(project), "documents": docs}
