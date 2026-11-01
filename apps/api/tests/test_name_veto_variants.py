"""The second-pass name veto fires on a different version of the name, not on unrelated text (invented names)."""

from __future__ import annotations

import uuid
from datetime import date

from app.core.domain import DocumentType
from app.document_intelligence.auto_acceptance import (
    FieldInput,
    ProjectContext,
    SecondPassInput,
    Strategy,
    decide,
)

ENR = DocumentType.ENROLLMENT_CERTIFICATE
TRN = DocumentType.TRANSCRIPT
CTX = ProjectContext(reference_date=date(2027, 3, 1))


def verdict(first: str, second: str | None) -> tuple[bool, str | None]:
    d1, d2 = uuid.uuid4(), uuid.uuid4()

    def university(doc: uuid.UUID, doc_type: DocumentType, value: str, re_read: str | None) -> FieldInput:
        return FieldInput(
            document_id=doc, checksum=doc.hex, document_type=doc_type, field_name="university_name", value=value,
            confidence=0.97, ocr=True, needs_review=False, extraction_method="standalone_university_name",
            second_pass=SecondPassInput(re_read, re_read, 0.9) if re_read else None,
        )

    decisions = decide([university(d1, ENR, first, second), university(d2, TRN, first, None)], CTX, Strategy.S8)
    item = decisions[(d1, "university_name")]
    return item.accepted, item.reason


NAME = "가나다대학교"


def test_a_re_read_that_contains_the_name_is_fine() -> None:
    assert verdict(NAME, "가나다대학교 총장") == (True, None)


def test_a_jumble_of_other_words_and_digits_is_not_a_contradiction() -> None:
    assert verdict(NAME, "발 급 일 2030 년 10 월 30 일 총 장") == (True, None)


def test_a_fragment_is_not_a_contradiction() -> None:
    assert verdict(NAME, "학") == (True, None)


def test_a_one_character_variant_of_the_name_vetoes() -> None:
    assert verdict(NAME, "가나라대학교") == (False, "SECOND_PASS_CONTRADICTS_NAME")


def test_a_two_character_variant_vetoes() -> None:
    assert verdict(NAME, "가나다대학원") == (False, "SECOND_PASS_CONTRADICTS_NAME")


def test_an_unrelated_name_is_not_a_misread_and_does_not_veto() -> None:
    assert verdict(NAME, "라마바상업고등") == (True, None)
