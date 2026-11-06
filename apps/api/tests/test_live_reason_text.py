"""Item 7: every open item says which field of which document, why and what to do (plain Korean)."""

from __future__ import annotations

import pytest

from app.core.domain import DocumentType
from app.services.reason_text import explain, pick_reason


@pytest.mark.parametrize(
    "code",
    [
        "CONFLICTS_WITH_APPLICATION_VALUE",
        "CONFLICTS_WITH_APPLICANT_GPA",
        "SECOND_PASS_CONTRADICTS_NAME",
        "NEAR_DECISION_BOUNDARY",
        "NO_INDEPENDENT_CONFIRMATION",
        "CONFIDENCE_BELOW_FLOOR",
        "DISAGREES_WITH_OTHER_DOCUMENT",
        "FIELD_MISSING",
        "SEMANTIC_INFERENCE",
        "OCR_REQUIRES_CONFIRMATION",
        "FORMAT_GPA_PAIR_MISSING",
        "SOMETHING_NEW",
    ],
)
def test_every_reason_names_the_field_the_document_and_an_action(code: str) -> None:
    text = explain(code, DocumentType.TRANSCRIPT, "university_name")
    assert text is not None and text.code == code
    assert "성적증명서" in text.explanation or "입력" in text.explanation
    assert text.action
    assert "일부 정보를 확인할 수 없어" not in text.explanation + text.action


def test_the_most_specific_reason_wins() -> None:
    assert (
        pick_reason("NEAR_DECISION_BOUNDARY", ["OCR_REQUIRES_CONFIRMATION"], False)
        == "NEAR_DECISION_BOUNDARY"
    )
    assert (
        pick_reason(None, ["OCR_REQUIRES_CONFIRMATION", "OCR_CONFIDENCE_BELOW_POLICY"], False)
        == "OCR_CONFIDENCE_BELOW_POLICY"
    )
    assert pick_reason("CONFIDENCE_BELOW_FLOOR", [], True) == "FIELD_MISSING"
    assert explain(None, None, None) is None
