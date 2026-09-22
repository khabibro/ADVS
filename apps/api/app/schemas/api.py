import uuid
from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from app.core.domain import (
    DOCUMENT_TYPE_DISPLAY_NAMES,
    DocumentType,
    OverallStatus,
    RuleOutcome,
    RuleType,
)


class ProjectCreate(BaseModel):
    name: str
    workflow_id: uuid.UUID
    applicant_name: str | None = None
    company_name: str | None = None


class WorkflowDocumentRequirementRead(BaseModel):
    document_type: DocumentType
    display_name: str
    required: bool


class WorkflowRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    is_active: bool
    document_requirements: list[WorkflowDocumentRequirementRead]
    created_at: datetime


class WorkflowSummary(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None


class ProjectRead(BaseModel):
    id: uuid.UUID
    name: str
    workflow_id: uuid.UUID | None
    workflow: WorkflowSummary | None = None
    expected_documents: list[WorkflowDocumentRequirementRead]
    applicant_name: str | None = None
    company_name: str | None = None
    status: OverallStatus
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ChecklistCreate(BaseModel):
    name: str
    description: str | None = None


class ChecklistRead(ChecklistCreate):
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DocumentRead(BaseModel):
    id: uuid.UUID
    original_filename: str
    mime_type: str
    size_bytes: int
    processing_status: str
    document_type: DocumentType
    document_type_display_name: str = ""
    classification_confidence: float | None
    classification_meta: dict | None = None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def populate_document_type_display_name(self) -> Self:
        self.document_type_display_name = DOCUMENT_TYPE_DISPLAY_NAMES[self.document_type]
        return self


class BoundingBoxRead(BaseModel):
    x: float
    y: float
    width: float
    height: float


class EvidenceRead(BaseModel):
    page_number: int
    source_text: str
    bounding_box: BoundingBoxRead | None = None
    confidence: float | None = None
    source_kind: str
    coordinate_space: str


class FieldRead(BaseModel):
    field_name: str
    raw_value: str | None
    normalized_value: str | None
    confidence: float | None
    needs_review: bool
    extraction_method: str | None = None
    source_text: str | None = None
    evidence: list[EvidenceRead] | None = None
    model_config = ConfigDict(from_attributes=True)


class ValidationRead(BaseModel):
    rule_type: str
    passed: bool
    severity: str
    expected_value: str | None
    actual_value: str | None
    message: str
    code: str
    model_config = ConfigDict(from_attributes=True)


class DocumentDetail(DocumentRead):
    extracted_fields: list[FieldRead] = []
    missing_expected_fields: list[str] = []
    validation_results: list[ValidationRead] = []
    # Computed at read time from validation_results
    # (READY/REVIEW_REQUIRED/NEEDS_CORRECTION);
    # not a stored column.
    overall_status: OverallStatus = OverallStatus.REVIEW_REQUIRED


class VerificationRequest(BaseModel):
    evaluation_date: date


class VerificationIssueRead(BaseModel):
    code: str
    status_effect: OverallStatus
    message: str
    document_id: uuid.UUID | None = None
    document_type: DocumentType | None = None
    field_name: str | None = None
    related_document_id: uuid.UUID | None = None
    related_document_type: DocumentType | None = None
    related_field_name: str | None = None
    rule_id: uuid.UUID | None = None
    field_id: uuid.UUID | None = None
    related_field_id: uuid.UUID | None = None


class RuleEvaluationRead(BaseModel):
    rule_id: uuid.UUID | None = None
    rule_type: RuleType
    outcome: RuleOutcome
    document_id: uuid.UUID | None = None
    document_type: DocumentType | None = None
    field_name: str | None = None
    related_document_id: uuid.UUID | None = None
    related_document_type: DocumentType | None = None
    related_field_name: str | None = None


class SubmissionVerificationRead(BaseModel):
    project_id: uuid.UUID
    workflow_id: uuid.UUID | None
    status: OverallStatus
    evaluation_date: date | None
    evaluated_at: datetime | None
    is_current: bool
    issues: list[VerificationIssueRead]
    rule_results: list[RuleEvaluationRead]
    disclaimer: str
