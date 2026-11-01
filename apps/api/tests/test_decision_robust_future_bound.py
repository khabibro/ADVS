"""The decision-robust model must evaluate the issue-date rule like the engine: a date after the check date fails it."""

from datetime import date

from app.core.domain import DocumentType
from app.document_intelligence.decision_robust import RuleSpec, is_decision_robust, outcomes

DOC = DocumentType.ENROLLMENT_CERTIFICATE
SPEC = [RuleSpec(DOC, "issue_date", "max_age", days=90)]


def test_a_future_date_fails_the_age_rule_like_in_the_engine() -> None:
    reference = date(2031, 3, 10)
    assert outcomes(SPEC, reference, "issue_date", DOC, "2031-03-09") == (True,)
    assert outcomes(SPEC, reference, "issue_date", DOC, "2031-03-10") == (
        True,
    )  # the check date itself passes
    assert outcomes(SPEC, reference, "issue_date", DOC, "2031-03-11") == (
        False,
    )  # one day ahead fails
    assert outcomes(SPEC, reference, "issue_date", DOC, "2030-12-10") == (
        True,
    )  # exactly 90 days: inclusive
    assert outcomes(SPEC, reference, "issue_date", DOC, "2030-12-09") == (False,)


def test_a_date_whose_misreading_could_be_in_the_future_is_not_robust_to_pass() -> None:
    # "2031-03-05" read one digit wrong can be "2037-03-05" (1 and 7 are confusable): in the future, which fails.
    assert not is_decision_robust(SPEC, date(2031, 3, 10), "issue_date", DOC, "2031-03-05")


def test_every_plausible_reading_expired_is_robust_to_fail() -> None:
    # check date far after the issue date: the read value and each valid alternative reading all fail
    assert is_decision_robust(SPEC, date(2033, 6, 1), "issue_date", DOC, "2031-03-05")
