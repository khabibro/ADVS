"""Applicants are told what to fix, in specific words; read values are not shown."""

from __future__ import annotations

from datetime import date

import pytest

from app.services.applicant_messages import (
    ACTION_APPLICANT,
    ACTION_STAFF,
    applicant_message,
)


def test_expired_names_the_validity_date_and_check_date() -> None:
    message = applicant_message(
        "EXPIRED_DOCUMENT",
        "NATIONAL_TAX_PAYMENT_CERTIFICATE",
        valid_until=date(2026, 9, 30),
        evaluation_date=date(2026, 10, 5),
    )
    assert "2026-09-30" in message.message and "2026-10-05" in message.message
    assert "국세 납세증명서" in message.message
    assert message.action == ACTION_APPLICANT


def test_expired_without_a_known_date_does_not_invent_one() -> None:
    message = applicant_message("EXPIRED_DOCUMENT", "NATIONAL_TAX_PAYMENT_CERTIFICATE")
    assert "20" not in message.message
    assert message.action == ACTION_APPLICANT


@pytest.mark.parametrize(
    ("code", "document_type"),
    [
        ("MISSING_REQUIRED_DOCUMENT", "BUSINESS_REGISTRATION_CERTIFICATE"),
        ("WRONG_DOCUMENT_TYPE", "NATIONAL_TAX_PAYMENT_CERTIFICATE"),
        ("COMPANY_NAME_MISMATCH", "BUSINESS_REGISTRATION_CERTIFICATE"),
        ("APPLICANT_NAME_MISMATCH", "ENROLLMENT_CERTIFICATE"),
        ("ISSUE_DATE_TOO_OLD", "TRANSCRIPT"),
        ("DUPLICATE_UPLOAD", "TRANSCRIPT"),
        ("MULTIPLE_DOCUMENTS_IN_FILE", None),
    ],
)
def test_fixable_problems_have_their_own_message(code: str, document_type: str | None) -> None:
    message = applicant_message(code, document_type)
    assert message.action == ACTION_APPLICANT
    assert "담당자가 확인 중" not in message.message


@pytest.mark.parametrize("code", ["OCR_UNCERTAIN", "REQUIRED_FIELD_UNRESOLVED", "SOMETHING_NEW"])
def test_everything_else_waits_for_staff_and_shows_no_values(code: str) -> None:
    message = applicant_message(code, "TRANSCRIPT")
    assert message.action == ACTION_STAFF
    assert "담당자가 확인 중" in message.message
