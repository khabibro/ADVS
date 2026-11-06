"""A read below the confidence floor that the other document confirms by an exact match (S11 variant b) takes
effect: the effective value is usable. Any other below-policy read stays open. Invented values."""

from __future__ import annotations

import uuid

from app.document_intelligence.auto_acceptance import AutoDecision
from app.document_intelligence.evidence_sufficiency import (
    EffectiveValueSource,
    EvidenceAssessmentState,
)
from app.models.entities import ExtractedField
from app.services.reviews import EffectiveFieldResolver


def _field(confidence: float) -> ExtractedField:
    return ExtractedField(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        field_name="student_name",
        raw_value="김가나",
        normalized_value="김가나",
        confidence=confidence,
        needs_review=False,
        extraction_method="label_match",
        evidence=[{"source_kind": "ocr", "confidence": confidence, "page": 1}],
    )


def _auto(rule_id: str) -> AutoDecision:
    return AutoDecision(True, "S11", rule_id=rule_id, sources=("documents",))


def test_below_floor_pair_confirmation_makes_the_value_usable() -> None:
    effective = EffectiveFieldResolver().resolve(
        _field(0.80), None, 1, _auto("PERSON:DOCUMENTS_BELOW_FLOOR")
    )
    assert effective.assessment.state == EvidenceAssessmentState.SUFFICIENT
    assert effective.source == EffectiveValueSource.MACHINE
    assert effective.normalized_value == "김가나"


def test_a_low_read_without_that_confirmation_stays_open() -> None:
    effective = EffectiveFieldResolver().resolve(_field(0.80), None, 1, _auto("PERSON:DOCUMENTS"))
    assert effective.assessment.state == EvidenceAssessmentState.REVIEW_REQUIRED
    assert effective.normalized_value is None
    effective = EffectiveFieldResolver().resolve(_field(0.80), None, 1, None)
    assert effective.assessment.state == EvidenceAssessmentState.REVIEW_REQUIRED


def _gpa_field(confidence: float) -> ExtractedField:
    field = _field(confidence)
    field.field_name, field.raw_value, field.normalized_value = "gpa", "3.40/4.3", "3.4"
    return field


def test_applicant_entered_gpa_confirms_a_read_below_the_policy_floor() -> None:
    # B2: a typed GPA that equals the read confirms it whatever the read's own confidence
    effective = EffectiveFieldResolver().resolve(
        _gpa_field(0.889), None, 1, _auto("GPA:APPLICANT_ENTERED")
    )
    assert effective.assessment.state == EvidenceAssessmentState.SUFFICIENT
    assert effective.normalized_value == "3.4"


def test_a_typed_gpa_that_differs_confirms_nothing() -> None:
    from app.core.domain import DocumentType
    from app.document_intelligence.auto_acceptance import (
        FieldInput,
        ProjectContext,
        Strategy,
        decide,
    )

    doc = uuid.uuid4()
    items = [
        FieldInput(doc, "x", DocumentType.TRANSCRIPT, name, value, 0.889, True, False)
        for name, value in (("gpa", "3.40"), ("gpa_scale", "4.3"))
    ]
    got = decide(
        items, ProjectContext(applicant_gpa="3.04", applicant_gpa_scale="4.3"), Strategy.S21
    )
    assert got[(doc, "gpa")].accepted is False
    assert got[(doc, "gpa")].reason == "CONFLICTS_WITH_APPLICANT_GPA"
    effective = EffectiveFieldResolver().resolve(_gpa_field(0.889), None, 1, got[(doc, "gpa")])
    assert effective.assessment.state == EvidenceAssessmentState.REVIEW_REQUIRED
