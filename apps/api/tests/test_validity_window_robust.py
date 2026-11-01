"""A validity end is decision-robust when the page's other printed dates bound its plausible readings
(all dates invented)."""

from datetime import date

from app.core.domain import DocumentType
from app.document_intelligence.decision_robust import RuleSpec, is_decision_robust

TAX = DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE
RULE = [RuleSpec(TAX, "valid_until", "on_or_after_ref")]
REFERENCE = date(2030, 6, 10)


def robust(value: str, window: tuple[date, ...]) -> bool:
    return is_decision_robust(RULE, REFERENCE, "valid_until", TAX, value, window_dates=window)


def test_without_a_printed_date_the_year_digit_makes_it_not_robust() -> None:
    assert robust("2030-07-31", ()) is False


def test_an_issue_date_just_before_the_end_makes_the_decision_robust() -> None:
    assert robust("2030-07-31", (date(2030, 7, 30),)) is True


def test_an_issue_date_a_month_before_the_end_is_also_robust() -> None:
    assert robust("2030-07-31", (date(2030, 7, 1),)) is True


def test_a_value_near_the_reference_stays_not_robust_even_with_a_window() -> None:
    # a day-digit misreading (06-13 -> 06-03 or 06-18) flips the outcome, and both stay inside the window
    assert robust("2030-06-13", (date(2030, 6, 1),)) is False


def test_the_read_value_must_lie_after_the_printed_date() -> None:
    assert robust("2030-07-31", (date(2030, 9, 1),)) is False


def test_a_printed_date_more_than_the_window_before_does_not_bound_it() -> None:
    assert robust("2030-07-31", (date(2028, 1, 1),)) is False
