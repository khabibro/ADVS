"""A decision-robust value is labelled as not individually confirmed, and its robustness follows the check date
(all values invented)."""

from __future__ import annotations

import uuid
from datetime import date

from app.core.domain import DocumentType
from app.document_intelligence.auto_acceptance import (
    DECISION_ROBUST_LABEL,
    FieldInput,
    ProjectContext,
    Strategy,
    decide,
)
from app.document_intelligence.decision_robust import RuleSpec
from app.document_intelligence.internal_evidence import DateBox, DocFacts

TAX = DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE
RULES = (RuleSpec(TAX, "valid_until", "on_or_after_ref"),)
DOC = uuid.uuid4()
FACTS = DocFacts(dates=(DateBox("2030-07-11", 1, 100, 100, 300, 40, True), DateBox("2030-07-31", 1, 100, 200, 300, 40, True)))


def verdict(reference: date):
    item = FieldInput(
        document_id=DOC,
        checksum=DOC.hex,
        document_type=TAX,
        field_name="valid_until",
        value="2030-07-31",
        confidence=0.97,
        ocr=True,
        needs_review=False,
        extraction_method="regex_date",
        facts=FACTS,
    )
    context = ProjectContext(reference_date=reference, rules=RULES)
    return decide([item], context, Strategy.S9)[(DOC, "valid_until")]


def test_robust_acceptance_is_labelled_not_confirmed() -> None:
    decision = verdict(date(2030, 6, 10))
    assert decision.accepted and decision.robust
    data = decision.to_dict()
    assert data["confirmation"] == "DECISION_ROBUST"
    assert data["label"] == DECISION_ROBUST_LABEL
    assert "값 미확정" in data["label_ko"]


def test_the_same_value_is_not_robust_once_the_check_date_moves_next_to_it() -> None:
    assert verdict(date(2030, 6, 10)).accepted
    near = verdict(date(2030, 7, 29))  # a day-digit misreading could now cross the check date
    assert not near.accepted
