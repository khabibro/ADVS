"""The second-pass name veto: a re-read that is only a piece of the name is not a contradiction (invented names)."""

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


def university(doc: uuid.UUID, doc_type: DocumentType, value: str, second: str | None) -> FieldInput:
    return FieldInput(
        document_id=doc,
        checksum=doc.hex,
        document_type=doc_type,
        field_name="university_name",
        value=value,
        confidence=0.97,
        ocr=True,
        needs_review=False,
        extraction_method="standalone_university_name",
        second_pass=SecondPassInput(second, second, 0.9) if second else None,
    )


def verdict(second: str | None) -> tuple[bool, str | None]:
    d1, d2 = uuid.uuid4(), uuid.uuid4()
    decisions = decide(
        [university(d1, ENR, "가나다대학교", second), university(d2, TRN, "가나다대학교", None)],
        CTX,
        Strategy.S8,
    )
    item = decisions[(d1, "university_name")]
    return item.accepted, item.reason


def test_a_fragment_of_the_name_does_not_veto() -> None:
    assert verdict("학교") == (True, None)


def test_a_complete_re_read_does_not_veto() -> None:
    assert verdict("가나다대학교총장") == (True, None)


def test_a_fragment_that_is_not_part_of_the_name_vetoes() -> None:
    assert verdict("라마") == (False, "SECOND_PASS_CONTRADICTS_NAME")


def test_a_longer_reading_without_the_name_vetoes() -> None:
    assert verdict("라마바대학교총장") == (False, "SECOND_PASS_CONTRADICTS_NAME")
