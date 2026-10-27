"""Cross-document university comparison (invented names only; no real institution appears here).

* same school with spacing / ownership prefix / issuer-title variants -> pass
* different schools, both values reliable -> NEEDS_CORRECTION
* one side missing, unconfirmed or low-confidence -> review, never an error
* a one-character recognition near miss -> review, not an error
"""

from __future__ import annotations

import uuid
from datetime import date

import pytest

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
    institution_key,
)

ENROL, TRANS = DocumentType.ENROLLMENT_CERTIFICATE, DocumentType.TRANSCRIPT


def _field(value: str | None, state: EvidenceAssessmentState | None = None) -> FieldSnapshot:
    if value is not None and state is None:
        return FieldSnapshot(
            uuid.uuid4(), "university_name", value, False, True, EvidenceAssessmentState.SUFFICIENT
        )
    return FieldSnapshot(
        uuid.uuid4(),
        "university_name",
        None,
        value is not None,
        value is not None,
        state or EvidenceAssessmentState.UNAVAILABLE,
    )


def _doc(document_type: DocumentType, field: FieldSnapshot | None) -> DocumentSnapshot:
    fields = {} if field is None else {"university_name": field}
    return DocumentSnapshot(
        uuid.uuid4(), document_type, ProcessingStatus.COMPLETED, uuid.uuid4().hex, fields
    )


def _verify(enrol: FieldSnapshot | None, trans: FieldSnapshot | None):
    rule = SubmissionRule(
        uuid.uuid4(),
        RuleType.FIELD_COMPARISON,
        Severity.ERROR,
        {
            "source_document_type": ENROL.value,
            "source_field": "university_name",
            "target_document_type": TRANS.value,
            "target_field": "university_name",
            "operator": RuleOperator.EQUALS.value,
            "value_type": "institution",
        },
    )
    return SubmissionVerificationEngine().verify(
        project_id=uuid.UUID(int=1),
        workflow_id=uuid.UUID(int=2),
        requirements=[
            RequirementSnapshot(uuid.uuid4(), ENROL, True, ()),
            RequirementSnapshot(uuid.uuid4(), TRANS, False, (rule,)),
        ],
        documents=[_doc(ENROL, enrol), _doc(TRANS, trans)],
        context=VerificationContext(date(2026, 9, 22)),
    )


@pytest.mark.parametrize(
    "variant",
    [
        "가나대학교",
        "가 나 대 학 교",
        "국립가나대학교",
        "(국립)가나대학교",
        "가나대학교 총장",
        "가나대학교총장",
        "사립 가나대학교",
    ],
)
def test_same_school_with_spacing_and_generic_affix_variants_passes(variant: str) -> None:
    result = _verify(_field("가나대학교"), _field(variant))
    assert result.issues == ()
    assert result.status == OverallStatus.READY


def test_institution_key_only_drops_generic_parts() -> None:
    assert institution_key("국립 가 나 대 학 교 총 장") == "가나대학교"
    assert institution_key("가나대학교") != institution_key("다라대학교")
    assert institution_key("대학교") == "대학교"  # nothing left to drop but the name itself


def test_different_schools_with_reliable_values_is_an_error() -> None:
    result = _verify(_field("가나대학교"), _field("다라마바대학교"))
    assert [i.code for i in result.issues] == ["INFORMATION_MISMATCH"]
    assert result.status == OverallStatus.NEEDS_CORRECTION


@pytest.mark.parametrize(
    "other",
    [None, _field(None), _field("가나대학교", EvidenceAssessmentState.REVIEW_REQUIRED)],
    ids=["field missing", "nothing read", "read but unconfirmed"],
)
def test_one_side_missing_or_unconfirmed_is_review_never_error(other: FieldSnapshot | None) -> None:
    for first, second in ((_field("가나대학교"), other), (other, _field("가나대학교"))):
        result = _verify(first, second)
        assert result.status == OverallStatus.REVIEW_REQUIRED
        assert all(i.code != "INFORMATION_MISMATCH" for i in result.issues)


def test_a_different_value_that_is_unconfirmed_is_review_not_error() -> None:
    result = _verify(
        _field("가나대학교"), _field("다라마바대학교", EvidenceAssessmentState.REVIEW_REQUIRED)
    )
    assert result.status == OverallStatus.REVIEW_REQUIRED
    assert all(i.code != "INFORMATION_MISMATCH" for i in result.issues)


@pytest.mark.parametrize("near", ["가나대학고", "가나대학", "가나대대학교", "가라대학교"])
def test_a_one_character_near_miss_is_review_not_error(near: str) -> None:
    result = _verify(_field("가나대학교"), _field(near))
    assert result.status == OverallStatus.REVIEW_REQUIRED
    assert [i.code for i in result.issues] == ["OCR_UNCERTAIN"]


def test_two_character_difference_is_a_real_mismatch() -> None:
    result = _verify(_field("가나대학교"), _field("가라마대학교"))
    assert result.status == OverallStatus.NEEDS_CORRECTION
