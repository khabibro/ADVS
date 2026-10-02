import uuid
from datetime import date

from app.core.domain import (
    DocumentType,
    OverallStatus,
    ProcessingStatus,
    RuleOperator,
    RuleType,
    Severity,
)
from app.document_intelligence.evidence_sufficiency import (
    EvidenceAssessmentReason,
    EvidenceAssessmentState,
    EvidenceSufficiencyPolicy,
)
from app.document_intelligence.validation.submission import (
    DocumentSnapshot,
    FieldSnapshot,
    RequirementSnapshot,
    SubmissionRule,
    SubmissionVerificationEngine,
    VerificationContext,
)


def test_evidence_policy_distinguishes_sufficient_uncertain_and_unavailable() -> None:
    policy = EvidenceSufficiencyPolicy()
    high = policy.assess(
        normalized_value="1234567890",
        needs_review=False,
        evidence=[{"source_kind": "ocr", "confidence": 0.95}],
        field_confidence=0.95,
    )
    low = policy.assess(
        normalized_value="1234567890",
        needs_review=False,
        evidence=[{"source_kind": "ocr", "confidence": 0.89}],
        field_confidence=0.89,
    )
    missing = policy.assess(
        normalized_value=None, needs_review=True, evidence=None, field_confidence=None
    )

    assert high.state == EvidenceAssessmentState.REVIEW_REQUIRED
    assert high.reasons == (EvidenceAssessmentReason.OCR_REQUIRES_CONFIRMATION,)
    assert low.state == EvidenceAssessmentState.REVIEW_REQUIRED
    assert low.reasons == (
        EvidenceAssessmentReason.OCR_REQUIRES_CONFIRMATION,
        EvidenceAssessmentReason.OCR_CONFIDENCE_BELOW_POLICY,
    )
    assert missing.state == EvidenceAssessmentState.UNAVAILABLE
    assert missing.reasons == (EvidenceAssessmentReason.FIELD_MISSING,)


def test_needs_review_and_missing_provenance_prevent_automatic_trust() -> None:
    policy = EvidenceSufficiencyPolicy()
    marked = policy.assess(
        normalized_value="value",
        needs_review=True,
        evidence=[{"source_kind": "ocr", "confidence": 0.99}],
        field_confidence=0.99,
    )
    no_evidence = policy.assess(
        normalized_value="value", needs_review=False, evidence=None, field_confidence=0.99
    )

    assert marked.state == EvidenceAssessmentState.REVIEW_REQUIRED
    assert EvidenceAssessmentReason.EXTRACTION_MARKED_FOR_REVIEW in marked.reasons
    assert no_evidence.reasons == (EvidenceAssessmentReason.EVIDENCE_MISSING,)


def test_embedded_pdf_null_confidence_is_sufficient() -> None:
    result = EvidenceSufficiencyPolicy().assess(
        normalized_value="value",
        needs_review=False,
        evidence=[{"source_kind": "embedded_pdf_text", "confidence": None}],
        field_confidence=None,
    )
    assert result.state == EvidenceAssessmentState.SUFFICIENT


def _field(name: str, value: str, state: EvidenceAssessmentState) -> FieldSnapshot:
    return FieldSnapshot(
        id=uuid.uuid4(),
        field_name=name,
        normalized_value=value,
        needs_review=state != EvidenceAssessmentState.SUFFICIENT,
        evidence_available=True,
        assessment_state=state,
    )


def test_only_rule_dependent_low_confidence_field_blocks_verification() -> None:
    document = DocumentSnapshot(
        id=uuid.uuid4(),
        document_type=DocumentType.TRANSCRIPT,
        processing_status=ProcessingStatus.COMPLETED,
        checksum_sha256="a" * 64,
        fields={
            "gpa": _field("gpa", "3.85", EvidenceAssessmentState.SUFFICIENT),
            "student_name": _field("student_name", "학생", EvidenceAssessmentState.REVIEW_REQUIRED),
        },
    )
    rule = SubmissionRule(
        id=uuid.uuid4(),
        rule_type=RuleType.NUMERIC_COMPARISON,
        severity=Severity.ERROR,
        params={
            "document_type": DocumentType.TRANSCRIPT.value,
            "field": "gpa",
            "operator": RuleOperator.GREATER_THAN_OR_EQUAL.value,
            "expected_value": "3.0",
        },
    )
    result = SubmissionVerificationEngine().verify(
        project_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        requirements=[
            RequirementSnapshot(uuid.uuid4(), DocumentType.TRANSCRIPT, True, rules=(rule,))
        ],
        documents=[document],
        context=VerificationContext(date(2026, 9, 22)),
    )

    assert result.status == OverallStatus.READY

    document.fields["gpa"] = _field("gpa", "3.85", EvidenceAssessmentState.REVIEW_REQUIRED)
    result = SubmissionVerificationEngine().verify(
        project_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        requirements=[
            RequirementSnapshot(uuid.uuid4(), DocumentType.TRANSCRIPT, True, rules=(rule,))
        ],
        documents=[document],
        context=VerificationContext(date(2026, 9, 22)),
    )
    assert result.status == OverallStatus.REVIEW_REQUIRED
    assert {issue.code for issue in result.issues} == {"OCR_UNCERTAIN"}
