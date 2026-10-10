import uuid
from datetime import date, datetime
from enum import StrEnum
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


class AutoAcceptanceRead(BaseModel):
    """Why an OCR value does (or does not) still need a human check."""

    accepted: bool
    strategy: str
    policy_version: str
    rule_id: str | None = None
    sources: list[str] = []
    corroborating_document_ids: list[uuid.UUID] = []
    second_pass_value: str | None = None
    reason: str | None = None


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
    auto_acceptance: AutoAcceptanceRead | None = None
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
    auto_acceptance: AutoAcceptanceRead | None = None


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
    # Informational items that never change the status (e.g. DUPLICATE_UPLOAD_IGNORED).
    notices: list[VerificationIssueRead] = []
    rule_results: list[RuleEvaluationRead]
    disclaimer: str


# --- Project overview (read model for the web app; aggregates stored decisions, decides nothing) ---


class UploadRulesRead(BaseModel):
    """What the upload endpoint accepts, so clients never keep their own allow-list."""

    extensions: list[str]
    mime_types: list[str]
    max_size_mb: int
    max_pages: int


class CheckState(StrEnum):
    CURRENT = "CURRENT"  # a stored check exists and still matches the documents and reviews
    NOT_CURRENT = "NOT_CURRENT"  # never run, or inputs changed since


class RequirementState(StrEnum):
    MISSING = "MISSING"
    PROCESSING = "PROCESSING"
    FAILED = "FAILED"
    NOT_CHECKED = "NOT_CHECKED"
    OK = "OK"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NEEDS_CORRECTION = "NEEDS_CORRECTION"


class NextStep(StrEnum):
    UPLOAD_DOCUMENTS = "UPLOAD_DOCUMENTS"
    WAIT_PROCESSING = "WAIT_PROCESSING"
    REVIEW_FIELDS = "REVIEW_FIELDS"
    RUN_CHECK = "RUN_CHECK"
    FIX_ISSUES = "FIX_ISSUES"
    DONE = "DONE"


class OverviewDocumentRef(BaseModel):
    id: uuid.UUID
    original_filename: str
    processing_status: str
    document_type: DocumentType
    error_message: str | None = None


class RequirementOverview(BaseModel):
    document_type: DocumentType
    display_name: str
    required: bool
    state: RequirementState
    documents: list[OverviewDocumentRef]
    issue_codes: list[str]


class OtherDocumentOverview(BaseModel):
    document: OverviewDocumentRef
    reason: str  # UNKNOWN_TYPE | NOT_IN_WORKFLOW


class OverviewIssue(VerificationIssueRead):
    # Values behind the finding, so the UI quotes them instead of looking them up.
    value: str | None = None
    related_value: str | None = None
    reference_date: date | None = None
    expected_value: str | None = None
    max_age_days: int | None = None


class OverviewCounts(BaseModel):
    requirements_total: int
    required_total: int
    required_ok: int
    required_missing: int
    issues_needs_correction: int
    issues_review_required: int
    review_open: int
    review_done: int
    documents_total: int
    documents_processing: int
    documents_failed: int


class ProjectOverviewRead(BaseModel):
    project_id: uuid.UUID
    check_state: CheckState
    status: OverallStatus | None  # the stored decision; None unless check_state is CURRENT
    evaluation_date: date | None
    evaluated_at: datetime | None
    suggested_evaluation_date: date
    status_item_count: int | None
    next_step: NextStep
    counts: OverviewCounts
    requirements: list[RequirementOverview]
    other_documents: list[OtherDocumentOverview]
    issues: list[OverviewIssue]
    notices: list[VerificationIssueRead]
