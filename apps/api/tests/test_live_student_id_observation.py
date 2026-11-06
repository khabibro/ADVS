"""The student number is an observation: identity is name + date of birth. It is never queued for a person and never
blocks, unless a checklist lists it as a required field. Invented values."""

from __future__ import annotations

import uuid
from datetime import date

from app.core.domain import DocumentType, OverallStatus, RuleOperator, RuleType, Severity
from app.document_intelligence.evidence_sufficiency import EvidenceAssessmentState
from app.document_intelligence.validation.submission import (
    DocumentSnapshot,
    FieldSnapshot,
    ProcessingStatus,
    RequirementSnapshot,
    SubmissionRule,
    SubmissionVerificationEngine,
    VerificationContext,
)
from app.models.entities import Checklist, DocumentRequirement, Project, ValidationRule
from app.services.reviews import FieldReviewService


def _comparison(required: tuple[str, ...]) -> Project:
    rule = ValidationRule(
        rule_type=RuleType.FIELD_COMPARISON.value,
        severity=Severity.ERROR.value,
        params={
            "source_document_type": DocumentType.ENROLLMENT_CERTIFICATE.value,
            "source_field": "student_id",
            "target_document_type": DocumentType.TRANSCRIPT.value,
            "target_field": "student_id",
            "operator": RuleOperator.EQUALS.value,
            "value_type": "identifier",
        },
    )
    enrolment = DocumentRequirement(
        document_type=DocumentType.ENROLLMENT_CERTIFICATE.value, required=True, rules=[rule]
    )
    for name in required:
        enrolment.rules.append(
            ValidationRule(
                rule_type=RuleType.REQUIRED_FIELD.value,
                severity=Severity.ERROR.value,
                params={"field": name},
            )
        )
    transcript = DocumentRequirement(
        document_type=DocumentType.TRANSCRIPT.value, required=False, rules=[]
    )
    return Project(checklist=Checklist(name="x", requirements=[enrolment, transcript]))


def test_student_id_is_not_queued_by_default() -> None:
    deps = FieldReviewService().review_dependencies(_comparison(()))
    assert (DocumentType.TRANSCRIPT, "student_id") not in deps
    assert (DocumentType.ENROLLMENT_CERTIFICATE, "student_id") not in deps


def test_student_id_is_queued_when_the_checklist_requires_it() -> None:
    deps = FieldReviewService().review_dependencies(_comparison(("student_id",)))
    assert (DocumentType.ENROLLMENT_CERTIFICATE, "student_id") in deps


def _doc(kind: DocumentType, sid: str, state: EvidenceAssessmentState) -> DocumentSnapshot:
    field = FieldSnapshot(uuid.uuid4(), "student_id", sid, False, True, state)
    return DocumentSnapshot(
        uuid.uuid4(), kind, ProcessingStatus.COMPLETED, uuid.uuid4().hex, {"student_id": field}
    )


def test_an_unreliable_student_id_does_not_block_the_comparison() -> None:
    rule = SubmissionRule(
        uuid.uuid4(),
        RuleType.FIELD_COMPARISON,
        Severity.ERROR,
        {
            "source_document_type": DocumentType.ENROLLMENT_CERTIFICATE.value,
            "source_field": "student_id",
            "target_document_type": DocumentType.TRANSCRIPT.value,
            "target_field": "student_id",
            "operator": RuleOperator.EQUALS.value,
            "value_type": "identifier",
        },
    )
    requirements = [
        RequirementSnapshot(uuid.uuid4(), DocumentType.ENROLLMENT_CERTIFICATE, True, (rule,)),
        RequirementSnapshot(uuid.uuid4(), DocumentType.TRANSCRIPT, False, ()),
    ]
    docs = [
        _doc(DocumentType.ENROLLMENT_CERTIFICATE, "2023111111", EvidenceAssessmentState.SUFFICIENT),
        _doc(DocumentType.TRANSCRIPT, "2023111111", EvidenceAssessmentState.REVIEW_REQUIRED),
    ]
    result = SubmissionVerificationEngine().verify(
        project_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        requirements=requirements,
        documents=docs,
        context=VerificationContext(date(2026, 11, 6)),
    )
    assert result.status == OverallStatus.READY and not result.issues


def _birth_date_comparison() -> Project:
    rule = ValidationRule(
        rule_type=RuleType.FIELD_COMPARISON.value,
        severity=Severity.ERROR.value,
        params={
            "source_document_type": DocumentType.ENROLLMENT_CERTIFICATE.value,
            "source_field": "birth_date",
            "target_document_type": DocumentType.TRANSCRIPT.value,
            "target_field": "birth_date",
            "operator": RuleOperator.EQUALS.value,
            "value_type": "identifier",
        },
    )
    enrolment = DocumentRequirement(
        document_type=DocumentType.ENROLLMENT_CERTIFICATE.value, required=True, rules=[rule]
    )
    transcript = DocumentRequirement(
        document_type=DocumentType.TRANSCRIPT.value, required=False, rules=[]
    )
    return Project(checklist=Checklist(name="x", requirements=[enrolment, transcript]))


def test_a_comparison_only_field_is_queued_only_when_both_documents_are_there() -> None:
    service = FieldReviewService()
    project = _birth_date_comparison()
    alone = service.review_dependencies(project, {DocumentType.ENROLLMENT_CERTIFICATE})
    both = service.review_dependencies(
        project, {DocumentType.ENROLLMENT_CERTIFICATE, DocumentType.TRANSCRIPT}
    )
    assert (DocumentType.ENROLLMENT_CERTIFICATE, "birth_date") not in alone
    assert (DocumentType.ENROLLMENT_CERTIFICATE, "birth_date") in both
    assert (DocumentType.TRANSCRIPT, "birth_date") in both
