"""Student identity across the two certificates (invented values).

* The student is identified by name AND date of birth, both printed on both documents.
* The student number is an observation: compared only when both documents print it, never required.
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


def _comparison(field: str, value_type: str = "string") -> SubmissionRule:
    return SubmissionRule(
        uuid.uuid4(),
        RuleType.FIELD_COMPARISON,
        Severity.ERROR,
        {
            "source_document_type": ENROL.value,
            "source_field": field,
            "target_document_type": TRANS.value,
            "target_field": field,
            "operator": RuleOperator.EQUALS.value,
            "value_type": value_type,
        },
    )


def _requirements() -> list[RequirementSnapshot]:
    rules = (
        _comparison("student_id", "identifier"),
        _comparison("student_name"),
        _comparison("birth_date", "identifier"),
        _comparison("admission_date", "identifier"),
    )
    return [
        RequirementSnapshot(uuid.uuid4(), ENROL, True, (), ()),
        RequirementSnapshot(uuid.uuid4(), TRANS, False, rules),
    ]


def _verify(documents: list[DocumentSnapshot]):
    return SubmissionVerificationEngine().verify(
        project_id=uuid.UUID(int=1),
        workflow_id=uuid.UUID(int=2),
        requirements=_requirements(),
        documents=documents,
        context=VerificationContext(date(2026, 9, 22)),
    )


def _issues(result, field: str) -> list[str]:
    return [i.code for i in result.issues if i.field_name == field]


WAITING = EvidenceAssessmentState.REVIEW_REQUIRED


def test_value_helpers() -> None:
    assert value_exists(_field("student_id", "20201234"))
    assert field_absent(None) and field_absent(_field("student_id", None))
    waiting = FieldSnapshot(uuid.uuid4(), "student_id", None, True, True, WAITING)
    assert value_exists(waiting) and not field_absent(waiting)


def test_same_name_and_same_birth_date_match() -> None:
    result = _verify(
        [
            _doc(ENROL, student_name="김가나", birth_date="2002-05-17"),
            _doc(TRANS, student_name="김가나", birth_date="2002-05-17"),
        ]
    )
    assert list(result.issues) == []


def test_same_name_different_birth_date_needs_correction() -> None:
    result = _verify(
        [
            _doc(ENROL, student_name="김가나", birth_date="2002-05-17"),
            _doc(TRANS, student_name="김가나", birth_date="2002-05-18"),
        ]
    )
    assert "INFORMATION_MISMATCH" in _issues(result, "birth_date")
    assert result.status == OverallStatus.NEEDS_CORRECTION


def test_same_name_different_birth_date_with_an_unreliable_side_goes_to_review() -> None:
    result = _verify(
        [
            _doc(ENROL, student_name="김가나", birth_date="2002-05-17"),
            _doc(TRANS, student_name="김가나", birth_date=("2002-05-18", WAITING)),
        ]
    )
    assert result.status == OverallStatus.REVIEW_REQUIRED


def test_birth_date_on_one_side_only_is_review_never_ready() -> None:
    result = _verify(
        [
            _doc(ENROL, student_name="김가나", birth_date="2002-05-17"),
            _doc(TRANS, student_name="김가나"),
        ]
    )
    assert result.status == OverallStatus.REVIEW_REQUIRED


def test_name_on_one_side_only_is_review_never_ready() -> None:
    result = _verify(
        [
            _doc(ENROL, birth_date="2002-05-17"),
            _doc(TRANS, student_name="김가나", birth_date="2002-05-17"),
        ]
    )
    assert result.status == OverallStatus.REVIEW_REQUIRED


def test_a_different_name_with_the_same_birth_date_is_not_ready() -> None:
    result = _verify(
        [
            _doc(ENROL, student_name="김가나", birth_date="2002-05-17"),
            _doc(TRANS, student_name="박다라", birth_date="2002-05-17"),
        ]
    )
    assert result.status == OverallStatus.NEEDS_CORRECTION


def _identity(**extra) -> dict:
    return {"student_name": "김가나", "birth_date": "2002-05-17", **extra}


def test_student_number_is_not_required() -> None:
    result = _verify([_doc(ENROL, **_identity()), _doc(TRANS, **_identity())])
    assert _issues(result, "student_id") == []
    assert result.status == OverallStatus.READY


def test_a_student_number_on_one_document_is_only_an_observation() -> None:
    for value in ("20201234", ("20201234", WAITING)):
        result = _verify([_doc(ENROL, **_identity()), _doc(TRANS, **_identity(student_id=value))])
        assert _issues(result, "student_id") == []
        assert result.status == OverallStatus.READY


def test_both_documents_printing_a_student_number_are_compared() -> None:
    same = _verify(
        [_doc(ENROL, **_identity(student_id="20201234")), _doc(TRANS, **_identity(student_id="20201234"))]
    )
    assert same.status == OverallStatus.READY
    different = _verify(
        [_doc(ENROL, **_identity(student_id="20201234")), _doc(TRANS, **_identity(student_id="20209999"))]
    )
    assert "INFORMATION_MISMATCH" in _issues(different, "student_id")
    assert different.status == OverallStatus.NEEDS_CORRECTION


def test_two_different_certificates_of_one_type_go_to_review_and_none_is_picked() -> None:
    # same type, same person, different issue dates (so different documents): never silently chosen
    first = _doc(TRANS, **_identity(issue_date="2026-08-01"))
    second = _doc(TRANS, **_identity(issue_date="2026-09-02"))
    result = _verify([_doc(ENROL, **_identity()), first, second])
    assert "MULTIPLE_DOCUMENTS_REQUIRE_REVIEW" in {i.code for i in result.issues}
    assert result.status == OverallStatus.REVIEW_REQUIRED


def test_an_identical_upload_twice_is_ignored_with_a_notice() -> None:
    document = _doc(TRANS, **_identity())
    copy = DocumentSnapshot(
        uuid.uuid4(), TRANS, ProcessingStatus.COMPLETED, document.checksum_sha256, document.fields
    )
    result = _verify([_doc(ENROL, **_identity()), document, copy])
    assert result.status == OverallStatus.READY
    assert "DUPLICATE_UPLOAD_IGNORED" in {n.code for n in result.notices}


def _admission_pair(left, right):
    return _verify(
        [
            _doc(ENROL, **_identity(admission_date=left)),
            _doc(TRANS, **_identity(admission_date=right)),
        ]
    )


def test_admission_date_is_compared_only_when_both_reads_are_reliable() -> None:
    assert _admission_pair("2022-03-02", "2022-03-02").status == OverallStatus.READY
    differ = _admission_pair("2022-03-02", "2022-03-07")
    assert differ.status == OverallStatus.NEEDS_CORRECTION  # two reliable reads that differ
    # an unreliable read is an observation no decision depends on: nothing is acted on
    assert _admission_pair("2022-03-02", ("2022-03-07", WAITING)).status == OverallStatus.READY
    only_one_prints = _verify(
        [_doc(ENROL, **_identity(admission_date="2022-03-02")), _doc(TRANS, **_identity())]
    )
    assert only_one_prints.status == OverallStatus.READY
