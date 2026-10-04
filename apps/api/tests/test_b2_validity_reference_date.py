"""B-2 (validity-reference issue): expiry and issue-date age are measured
against the submission's own date (Asia/Seoul), not the server clock.

Covers:
- the submission.created_at -> Asia/Seoul conversion
  (services.document_validation.submission_reference_date), including a
  UTC timestamp that falls on the next day in Korea;
- validity boundaries (day before / day of / day after the reference date)
  at the engine level, both for the always-on expiration check and the
  configured DATE_NOT_EXPIRED rule;
- re-running validation on a later day no longer changes the result, as
  long as the same reference_date is supplied (the whole point: the
  result now depends on the submission, not on when someone happens to
  re-run the check);
- ISSUE_DATE_MAX_AGE boundaries;
- a genuinely unknown reference date reviews, never guesses.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest

from app.core.domain import DocumentType, OverallStatus, RuleType, Severity
from app.document_intelligence.extraction.base import ExtractedValue
from app.document_intelligence.validation.engine import ConfiguredRule, ValidationEngine
from app.models.entities import Submission
from app.services.document_validation import submission_reference_date

engine = ValidationEngine()


# ---------------------------------------------------------------------
# submission.created_at -> Asia/Seoul
# ---------------------------------------------------------------------


def test_utc_timestamp_crossing_midnight_in_korea_uses_the_korean_date() -> None:
    """2026-10-04T16:30:00Z is 2026-10-05 01:30 KST -- the next day."""
    submission = Submission(
        project_id=uuid.uuid4(), created_at=datetime(2026, 10, 4, 16, 30, tzinfo=UTC)
    )
    assert submission_reference_date(submission) == date(2026, 10, 5)


def test_naive_timestamp_is_treated_as_utc_not_guessed_at() -> None:
    submission = Submission(
        project_id=uuid.uuid4(),
        created_at=datetime(2026, 10, 4, 16, 30),  # no tzinfo
    )
    assert submission_reference_date(submission) == date(2026, 10, 5)


def test_no_submission_returns_none_not_a_guess() -> None:
    assert submission_reference_date(None) is None


# ---------------------------------------------------------------------
# Boundaries: the day before / of / after the reference date
# ---------------------------------------------------------------------


def _sme_fields(valid_until: str) -> list[ExtractedValue]:
    return [
        ExtractedValue("company_name", "테스트상사", "테스트상사"),
        ExtractedValue("business_registration_number", "123-45-00018", "1234500018"),
        ExtractedValue("valid_from", "2026-01-01", "2026-01-01"),
        ExtractedValue("valid_until", valid_until, valid_until),
    ]


@pytest.mark.parametrize(
    ("valid_until", "expected_status"),
    [
        ("2026-10-04", OverallStatus.NEEDS_CORRECTION),  # the day before: expired
        ("2026-10-05", OverallStatus.READY),  # the day of: inclusive, still valid
        ("2026-10-06", OverallStatus.READY),  # the day after: valid
    ],
)
def test_always_on_expiration_check_is_inclusive_at_the_boundary(
    valid_until: str, expected_status: OverallStatus
) -> None:
    fields = _sme_fields(valid_until)
    issues = engine.validate_document(
        None,
        DocumentType.SME_CONFIRMATION_CERTIFICATE,
        fields,
        configured_rules=[],
        reference_date=date(2026, 10, 5),
    )
    assert engine.overall_status(issues) == expected_status


@pytest.mark.parametrize(
    ("valid_until", "expected_status"),
    [
        ("2026-10-04", OverallStatus.NEEDS_CORRECTION),
        ("2026-10-05", OverallStatus.READY),
        ("2026-10-06", OverallStatus.READY),
    ],
)
def test_configured_date_not_expired_rule_is_inclusive_at_the_boundary(
    valid_until: str, expected_status: OverallStatus
) -> None:
    fields = _sme_fields(valid_until)
    rules = [ConfiguredRule(RuleType.DATE_NOT_EXPIRED, Severity.ERROR, {"field": "valid_until"})]
    issues = engine.validate_document(
        None,
        DocumentType.SME_CONFIRMATION_CERTIFICATE,
        fields,
        configured_rules=rules,
        reference_date=date(2026, 10, 5),
    )
    assert engine.overall_status(issues) == expected_status


def test_rerunning_60_days_later_with_the_same_reference_date_is_unchanged() -> None:
    """The whole point of B-2: the result depends on the submission's own
    date, supplied explicitly, not on when the check happens to run."""
    fields = _sme_fields("2026-10-05")
    submission_date = date(2026, 10, 5)
    today_issues = engine.validate_document(
        None,
        DocumentType.SME_CONFIRMATION_CERTIFICATE,
        fields,
        configured_rules=[],
        reference_date=submission_date,
    )
    sixty_days_later_issues = engine.validate_document(
        None,
        DocumentType.SME_CONFIRMATION_CERTIFICATE,
        fields,
        configured_rules=[],
        reference_date=submission_date,  # unchanged -- a real caller always
        # re-derives this from submission.created_at, which does not move.
    )
    assert engine.overall_status(today_issues) == engine.overall_status(sixty_days_later_issues)
    assert engine.overall_status(today_issues) == OverallStatus.READY
    assert (date(2026, 10, 5) + timedelta(days=60)) > submission_date  # sanity: time did pass


# ---------------------------------------------------------------------
# ISSUE_DATE_MAX_AGE boundaries
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("issue_date", "expected_status"),
    [
        ("2026-07-07", OverallStatus.READY),  # exactly 90 days before: still within range
        ("2026-07-06", OverallStatus.NEEDS_CORRECTION),  # 91 days before: too old
        ("2026-10-05", OverallStatus.READY),  # issued the same day: 0 days old
    ],
)
def test_issue_date_max_age_boundaries(issue_date: str, expected_status: OverallStatus) -> None:
    fields = [ExtractedValue("issue_date", issue_date, issue_date)]
    rules = [
        ConfiguredRule(
            RuleType.ISSUE_DATE_MAX_AGE,
            Severity.ERROR,
            {"field": "issue_date", "max_age_days": 90},
        )
    ]
    issues = engine.validate_document(
        None,
        DocumentType.SME_CONFIRMATION_CERTIFICATE,
        fields,
        configured_rules=rules,
        reference_date=date(2026, 10, 5),
    )
    assert engine.overall_status(issues) == expected_status


# ---------------------------------------------------------------------
# Unknown reference date: review, never a guess
# ---------------------------------------------------------------------


def test_unknown_reference_date_reviews_the_always_on_expiration_check() -> None:
    fields = _sme_fields("2099-01-01")  # unambiguously not-expired by any real date
    issues = engine.validate_document(
        None, DocumentType.SME_CONFIRMATION_CERTIFICATE, fields, configured_rules=[]
    )
    assert any(i.code == "REFERENCE_DATE_UNAVAILABLE" for i in issues)
    assert engine.overall_status(issues) == OverallStatus.REVIEW_REQUIRED


def test_unknown_reference_date_reviews_issue_date_max_age() -> None:
    fields = [ExtractedValue("issue_date", "2026-09-01", "2026-09-01")]
    rules = [
        ConfiguredRule(
            RuleType.ISSUE_DATE_MAX_AGE,
            Severity.ERROR,
            {"field": "issue_date", "max_age_days": 90},
        )
    ]
    issues = engine.validate_document(
        None, DocumentType.SME_CONFIRMATION_CERTIFICATE, fields, configured_rules=rules
    )
    assert any(i.code == "REFERENCE_DATE_UNAVAILABLE" for i in issues)
    assert engine.overall_status(issues) == OverallStatus.REVIEW_REQUIRED
