"""The student number is required on at least ONE document of a submission (invented values).

* an enrolment certificate that prints no 학번 is satisfied by a transcript that does;
* the two documents are compared only when both print it;
* a single document's value that still needs a person stays flagged;
* with no 학번 anywhere the requirement still fails.
"""

from __future__ import annotations

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
from app.document_intelligence.evidence_sufficiency import EvidenceAssessmentState
from app.document_intelligence.validation.submission import (
    DocumentSnapshot,
    FieldSnapshot,
    RequirementSnapshot,
    SubmissionRule,
    SubmissionVerificationEngine,
    VerificationContext,
    field_absent,
    value_exists,
)

ENROL, TRANS = DocumentType.ENROLLMENT_CERTIFICATE, DocumentType.TRANSCRIPT


def _field(
    name: str, value: str | None, state: EvidenceAssessmentState | None = None
) -> FieldSnapshot:
    sufficient = value is not None and state is None
    return FieldSnapshot(
        uuid.uuid4(),
        name,
        value,
        needs_review=not sufficient and value is not None,
        evidence_available=value is not None,
        assessment_state=EvidenceAssessmentState.SUFFICIENT
        if sufficient
        else state
        if state is not None
        else EvidenceAssessmentState.UNAVAILABLE,
    )


def _doc(
    document_type: DocumentType,
    **fields: tuple[str | None, EvidenceAssessmentState | None] | str | None,
) -> DocumentSnapshot:
    built = {}
    for name, spec in fields.items():
        value, state = spec if isinstance(spec, tuple) else (spec, None)
        built[name] = _field(name, value, state)
    return DocumentSnapshot(
        uuid.uuid4(), document_type, ProcessingStatus.COMPLETED, uuid.uuid4().hex, built
    )


def _requirements() -> list[RequirementSnapshot]:
    comparison = SubmissionRule(
        uuid.uuid4(),
        RuleType.FIELD_COMPARISON,
        Severity.ERROR,
        {
            "source_document_type": ENROL.value,
            "source_field": "student_id",
            "target_document_type": TRANS.value,
            "target_field": "student_id",
            "operator": RuleOperator.EQUALS.value,
            "value_type": "identifier",
        },
    )
    return [
        RequirementSnapshot(uuid.uuid4(), ENROL, True, (), ("student_id",)),
        RequirementSnapshot(uuid.uuid4(), TRANS, False, (comparison,)),
    ]


def _verify(documents: list[DocumentSnapshot]):
    return SubmissionVerificationEngine().verify(
        project_id=uuid.UUID(int=1),
        workflow_id=uuid.UUID(int=2),
        requirements=_requirements(),
        documents=documents,
        context=VerificationContext(date(2026, 9, 22)),
    )


def _student_id_issues(result) -> list[str]:
    return [i.code for i in result.issues if i.field_name == "student_id"]


def test_value_helpers() -> None:
    assert value_exists(_field("student_id", "20201234"))
    assert field_absent(None) and field_absent(_field("student_id", None))
    waiting = FieldSnapshot(
        uuid.uuid4(), "student_id", None, True, True, EvidenceAssessmentState.REVIEW_REQUIRED
    )
    assert value_exists(waiting) and not field_absent(waiting)


def test_a_student_number_on_one_document_satisfies_the_requirement() -> None:
    result = _verify([_doc(ENROL, student_name="김가나"), _doc(TRANS, student_id="20201234")])
    assert _student_id_issues(result) == []


def test_no_student_number_anywhere_still_fails() -> None:
    result = _verify([_doc(ENROL, student_name="김가나"), _doc(TRANS, student_name="김가나")])
    assert _student_id_issues(result)
    assert result.status == OverallStatus.REVIEW_REQUIRED


def test_both_documents_printing_it_are_compared() -> None:
    same = _verify([_doc(ENROL, student_id="20201234"), _doc(TRANS, student_id="20201234")])
    assert _student_id_issues(same) == []
    different = _verify([_doc(ENROL, student_id="20201234"), _doc(TRANS, student_id="20209999")])
    assert "INFORMATION_MISMATCH" in _student_id_issues(different)
    assert different.status == OverallStatus.NEEDS_CORRECTION


def test_a_single_documents_value_that_needs_a_person_stays_flagged() -> None:
    waiting = ("20201234", EvidenceAssessmentState.REVIEW_REQUIRED)
    result = _verify([_doc(ENROL, student_name="김가나"), _doc(TRANS, student_id=waiting)])
    assert _student_id_issues(result) == ["OCR_UNCERTAIN"]
    assert result.status == OverallStatus.REVIEW_REQUIRED


def test_the_value_on_the_enrolment_certificate_alone_is_flagged_when_unconfirmed() -> None:
    waiting = ("20201234", EvidenceAssessmentState.REVIEW_REQUIRED)
    result = _verify([_doc(ENROL, student_id=waiting), _doc(TRANS, student_name="김가나")])
    assert "OCR_UNCERTAIN" in _student_id_issues(result)
