"""Company-name notation across certificates: parenthesised Latin text and a shorter workplace name.

All names and numbers are invented."""

from __future__ import annotations

import uuid
from datetime import date

from app.core.domain import DocumentType
from app.document_intelligence.auto_acceptance import (
    FieldInput,
    ProjectContext,
    Strategy,
    canonical_key,
    decide,
)

BR = DocumentType.BUSINESS_REGISTRATION_CERTIFICATE
TAX = DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE
INS = DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE
BRN = "1234567891"  # valid check digit
OTHER_BRN = "2148655302"  # valid check digit
CTX = ProjectContext(reference_date=date(2027, 3, 1))


def field(doc: uuid.UUID, name: str, value: str, doc_type: DocumentType) -> FieldInput:
    return FieldInput(
        document_id=doc,
        checksum=doc.hex,
        document_type=doc_type,
        field_name=name,
        value=value,
        confidence=0.97,
        ocr=True,
        needs_review=False,
        extraction_method="label_match",
    )


def accepted(decisions: dict, doc: uuid.UUID, name: str) -> bool:
    item = decisions.get((doc, name))
    return bool(item and item.accepted)


def submission(br_name: str, tax_name: str, ins_name: str, ins_brn: str = BRN):
    d1, d2, d3 = (uuid.uuid4() for _ in range(3))
    fields = [
        field(d1, "company_name", br_name, BR),
        field(d1, "business_registration_number", BRN, BR),
        field(d2, "company_name", tax_name, TAX),
        field(d2, "business_registration_number", BRN, TAX),
        field(d3, "workplace_name", ins_name, INS),
        field(d3, "business_registration_number", ins_brn, INS),
    ]
    return (d1, d2, d3), decide(fields, CTX, Strategy.S8)


def test_parenthesised_latin_text_is_not_part_of_the_name() -> None:
    assert canonical_key("company", "(주)가나다상사(Kanada Trading 2)") == canonical_key("company", "가나다상사")


def test_parenthesised_hangul_is_kept() -> None:
    assert canonical_key("company", "가나다(구)상사") != canonical_key("company", "가나다상사")


def test_shorter_workplace_name_is_accepted_when_both_documents_share_the_business_number() -> None:
    (d1, d2, d3), decisions = submission("(주)가나다상사(Kanada Trading)", "(주)가나다상사", "(주)가나다상")
    assert accepted(decisions, d1, "company_name")
    assert accepted(decisions, d2, "company_name")
    assert accepted(decisions, d3, "workplace_name")


def test_a_shorter_name_is_not_accepted_when_the_business_numbers_differ() -> None:
    (d1, _d2, d3), decisions = submission("(주)가나다상사", "(주)가나다상사", "(주)가나다상", ins_brn=OTHER_BRN)
    assert not accepted(decisions, d3, "workplace_name")
    assert decisions[(d3, "workplace_name")].reason == "DISAGREES_WITH_OTHER_DOCUMENT"
    assert not accepted(decisions, d1, "company_name")


def test_a_name_that_is_not_a_prefix_stays_a_disagreement() -> None:
    (d1, _d2, d3), decisions = submission("(주)가나다상사", "(주)가나다상사", "(주)라마바상사")
    assert not accepted(decisions, d3, "workplace_name")
    assert not accepted(decisions, d1, "company_name")


def test_a_very_short_prefix_is_not_enough() -> None:
    (_d1, _d2, d3), decisions = submission("(주)가나다상사", "(주)가나다상사", "(주)가나")
    assert not accepted(decisions, d3, "workplace_name")
