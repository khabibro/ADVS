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
