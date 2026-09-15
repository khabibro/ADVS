import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str
    workflow_id: uuid.UUID
    applicant_name: str | None = None
    company_name: str | None = None


class WorkflowDocumentRequirementRead(BaseModel):
    document_type: str
    display_name: str
    required: bool


class WorkflowRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    is_active: bool
    document_requirements: list[WorkflowDocumentRequirementRead] = Field(default_factory=list)
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
    expected_documents: list[WorkflowDocumentRequirementRead] = Field(default_factory=list)
    applicant_name: str | None = None
    company_name: str | None = None
    status: str
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
    document_type: str
    classification_confidence: float | None
    classification_meta: dict | None = None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class FieldRead(BaseModel):
    field_name: str
    raw_value: str | None
    normalized_value: str | None
    confidence: float | None
    needs_review: bool
    extraction_method: str | None = None
    source_text: str | None = None
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
    validation_results: list[ValidationRead] = []
    # Computed at read time from validation_results
    # (READY/REVIEW_REQUIRED/NEEDS_CORRECTION);
    # not a stored column.
    overall_status: str = "REVIEW_REQUIRED"
