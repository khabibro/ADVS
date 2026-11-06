"""B1: every name form printed on the documents is an alias of the company; a typed name matches if it equals any
alias. Invented names."""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.core.domain import DocumentType, OverallStatus
from app.document_intelligence.company_names import alias_pool, company_aliases, typed_name_matches
from app.document_intelligence.evidence_sufficiency import EvidenceAssessmentState
from app.document_intelligence.validation.submission import (
    DocumentSnapshot,
    FieldSnapshot,
    ProcessingStatus,
    RequirementSnapshot,
    SubmissionVerificationEngine,
    VerificationContext,
)

BRC_NAME = "(주)가나다상사 (Ganada 21)"
NTAX_NAME = "(주)가나다상사 (Ganada 21)"
INS_NAME = "(주)가나다상사"
POOL = alias_pool([BRC_NAME, NTAX_NAME, INS_NAME])


@pytest.mark.parametrize(
    "typed",
    [
        "가나다상사",
        "(주)가나다상사",
        "㈜가나다상사",
        "주식회사 가나다상사",
        "주식회사가나다상사",
        "가나다상사 주식회사",
        "가나다 상사",
        "Ganada21",
        "Ganada 21",
        "GANADA 21",
        "ganada-21",
        "(주)가나다상사(Ganada 21)",
        "Ganada 21 Co., Ltd.",
        "Ｇａｎａｄａ２１",  # full width
    ],
)
def test_every_printed_name_form_is_an_alias(typed: str) -> None:
    assert typed_name_matches(typed, POOL)


@pytest.mark.parametrize(
    "typed",
    [
        "가나다상사코리아",
        "가나라상사",
        "Ganada 22",
        "Ganada",
        "상사",
        "",
        "(주)",
        "다른회사",
        "가나다",
    ],
)
def test_a_different_name_is_not_an_alias(typed: str) -> None:
    assert not typed_name_matches(typed, POOL)


def test_no_transliteration_is_attempted() -> None:
    assert not typed_name_matches("가나다이십일", POOL)
    assert company_aliases("(주)가나다상사 (Ganada 21)") == {
        "가나다상사",
        "ganada21",
        "가나다상사ganada21",
    }


def _field(name: str, value: str | None) -> FieldSnapshot:
    return FieldSnapshot(
        uuid.uuid4(), name, value, False, value is not None, EvidenceAssessmentState.SUFFICIENT
    )


def _doc(document_type: DocumentType, **values: str) -> DocumentSnapshot:
    return DocumentSnapshot(
        uuid.uuid4(),
        document_type,
        ProcessingStatus.COMPLETED,
        uuid.uuid4().hex,
        {name: _field(name, value) for name, value in values.items()},
    )


def _verify(typed: str | None, brn_ins: str = "1234567891") -> tuple[OverallStatus, list[str]]:
    docs = [
        _doc(
            DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
            company_name=BRC_NAME,
            business_registration_number="1234567891",
        ),
        _doc(
            DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE,
            workplace_name=INS_NAME,
            business_registration_number=brn_ins,
        ),
    ]
    requirements = [
        RequirementSnapshot(uuid.uuid4(), DocumentType.BUSINESS_REGISTRATION_CERTIFICATE, True, ()),
        RequirementSnapshot(
            uuid.uuid4(), DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE, True, ()
        ),
    ]
    result = SubmissionVerificationEngine().verify(
        project_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        requirements=requirements,
        documents=docs,
        context=VerificationContext(date(2026, 11, 6), company_name=typed),
    )
    return result.status, [i.code for i in result.issues]


@pytest.mark.parametrize(
    "typed", ["가나다상사", "Ganada21", "(주)가나다상사(Ganada 21)", "주식회사 가나다상사"]
)
def test_any_alias_typed_gives_no_company_issue(typed: str) -> None:
    status, codes = _verify(typed)
    assert "COMPANY_NAME_MISMATCH" not in codes and "COMPANY_NAME_INPUT_NOT_FOUND" not in codes


def test_unknown_name_with_agreeing_documents_is_review_never_correction() -> None:
    status, codes = _verify("다른이름")
    assert codes.count("COMPANY_NAME_INPUT_NOT_FOUND") == 1  # reported once, not once per document
    assert "COMPANY_NAME_MISMATCH" not in codes
    assert status == OverallStatus.REVIEW_REQUIRED


def test_empty_typed_name_skips_the_check() -> None:
    assert "COMPANY_NAME_INPUT_NOT_FOUND" not in _verify(None)[1]
