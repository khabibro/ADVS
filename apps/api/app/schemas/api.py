import uuid
from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.domain import (
    DOCUMENT_TYPE_DISPLAY_NAMES,
    DocumentType,
    OverallStatus,
    RuleOutcome,
    RuleType,
)
from app.document_intelligence.evidence_sufficiency import (
    EffectiveValueSource,
    EvidenceAssessmentReason,
    EvidenceAssessmentState,
    FieldReviewDecision,
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
    processing_version: int
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
    polygon: list[tuple[float, float]] | None = None
    detection_confidence: float | None = None
    transform: dict | None = None


class FieldRead(BaseModel):
    id: uuid.UUID | None = None
    field_name: str
    raw_value: str | None
    normalized_value: str | None
    confidence: float | None
    needs_review: bool
    extraction_method: str | None = None
    source_text: str | None = None
    evidence: list[EvidenceRead] | None = None
    evidence_assessment: EvidenceAssessmentState | None = None
    assessment_reasons: list[EvidenceAssessmentReason] = []
    policy_version: str | None = None
    effective_normalized_value: str | None = None
    effective_source: EffectiveValueSource | None = None
    current_review_decision: FieldReviewDecision | None = None
    model_config = ConfigDict(from_attributes=True)


class FieldReviewCreate(BaseModel):
    expected_processing_version: int = Field(ge=0)
    decision: FieldReviewDecision
    corrected_value: str | None = None
    reviewer_label: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_decision_value(self) -> Self:
        if self.decision == FieldReviewDecision.CORRECTED and not self.corrected_value:
            raise ValueError("CORRECTED requires corrected_value")
        if self.decision != FieldReviewDecision.CORRECTED and self.corrected_value is not None:
            raise ValueError(f"{self.decision.value} does not accept corrected_value")
        return self


class FieldReviewRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    document_id: uuid.UUID
    extracted_field_id: uuid.UUID | None
    field_name: str
    decision: FieldReviewDecision
    original_raw_value: str | None
    original_normalized_value: str | None
    original_evidence_fingerprint: str | None
    reviewed_raw_value: str | None
    reviewed_normalized_value: str | None
    reviewer_label: str | None
    note: str | None
    processing_version: int
    policy_version: str
    is_current: bool
    reviewed_at: datetime
    stale_at: datetime | None
    superseded_at: datetime | None
    model_config = ConfigDict(from_attributes=True)


class ReviewItemRead(BaseModel):
    document_id: uuid.UUID
    processing_version: int
    document_type: DocumentType
    field_id: uuid.UUID | None
    field_name: str
    machine_raw_value: str | None
    machine_normalized_value: str | None
    confidence: float | None
    evidence: list[EvidenceRead] | None
    assessment_state: EvidenceAssessmentState
    assessment_reasons: list[EvidenceAssessmentReason]
    policy_version: str
    issue_code: str
    affects_verification: bool
    queue_status: str
    current_review_id: uuid.UUID | None
    current_review_decision: FieldReviewDecision | None
    effective_value: str | None
    effective_source: EffectiveValueSource


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
