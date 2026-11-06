"""Item 5: the fixed 10-day margin around the check date is replaced by the digit-confusion check. A certificate end
date that is not individually confirmed passes only when every likely misreading gives the same verdict. Invented
dates."""

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
from app.document_intelligence.decision_robust import RuleSpec

D = DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE
DOC = uuid.uuid4()
SPEC = (RuleSpec(D, "valid_until", "on_or_after_ref"),)


def _fields(end: str, issue: str = "2026-10-14") -> list[FieldInput]:
    second = SecondPassInput(end, end, 0.9)
    return [
        FieldInput(DOC, "c", D, "valid_until", end, 0.95, True, False, second_pass=second),
        FieldInput(DOC, "c", D, "issue_date", issue, 0.97, True, False),
    ]


def _decide(end: str, reference: date, strategy: Strategy):
    context = ProjectContext(reference_date=reference, rules=SPEC)
    return decide(_fields(end), context, strategy)[(DOC, "valid_until")]


def test_expired_by_one_day_is_robust_and_no_longer_waits_for_a_person() -> None:
    # 30 days after issue (the national-tax profile), one day before the check date: every misreading that the
    # profile allows is also expired
    old = _decide("2026-11-13", date(2026, 11, 14), Strategy.S17)
    new = _decide("2026-11-13", date(2026, 11, 14), Strategy.S21)
    assert not old.accepted and old.reason == "NEAR_DECISION_BOUNDARY"
    assert new.accepted  # the exact 30-day relation to the issue date is another source


def test_an_end_date_without_an_exact_relation_that_a_misreading_can_flip_waits_for_a_person() -> (
    None
):
    # a 5-day validity (shortened by law: consistent, never confirmed), checked 3 days before its end: one digit
    # (2 -> 7, 0 -> 1 ...) moves the end across the check date
    second = SecondPassInput("2026-11-02", "2026-11-02", 0.9)
    fields = [
        FieldInput(DOC, "c", D, "valid_until", "2026-11-02", 0.95, True, False, second_pass=second),
        FieldInput(DOC, "c", D, "issue_date", "2026-10-28", 0.97, True, False),
    ]
    for reference in (date(2026, 10, 30), date(2026, 11, 2), date(2026, 11, 6)):
        got = decide(fields, ProjectContext(reference_date=reference, rules=SPEC), Strategy.S21)
        assert not got[(DOC, "valid_until")].accepted, reference


def test_far_from_the_check_date_with_a_confirmed_profile_is_robust() -> None:
    got = _decide("2026-11-13", date(2026, 10, 20), Strategy.S21)
    assert got.accepted


def test_without_another_date_on_the_page_the_policy_margin_stays() -> None:
    # injection E11: an expired end date misread as "the day after the check date" cannot be told from a true one
    second = SecondPassInput("2026-10-06", "2026-10-06", 0.9)
    only_end = [
        FieldInput(DOC, "c", D, "valid_until", "2026-10-06", 0.95, True, False, second_pass=second)
    ]
    unread_issue = [*only_end, FieldInput(DOC, "c", D, "issue_date", None, None, True, False)]
    for fields in (only_end, unread_issue):
        got = decide(
            fields, ProjectContext(reference_date=date(2026, 10, 5), rules=SPEC), Strategy.S21
        )
        assert not got[(DOC, "valid_until")].accepted
        assert got[(DOC, "valid_until")].reason == "NEAR_DECISION_BOUNDARY"


def test_an_end_date_that_breaks_the_legal_period_is_never_accepted_as_robust() -> None:
    second = SecondPassInput("2026-10-06", "2026-10-06", 0.9)
    fields = [
        FieldInput(DOC, "c", D, "valid_until", "2026-10-06", 0.95, True, False, second_pass=second),
        FieldInput(DOC, "c", D, "issue_date", "2026-08-01", 0.97, True, False),
    ]
    got = decide(fields, ProjectContext(reference_date=date(2026, 10, 5), rules=SPEC), Strategy.S21)
    assert not got[(DOC, "valid_until")].accepted
