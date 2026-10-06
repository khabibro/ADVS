"""Internal confirmation rules (Phase D3): what a document's own content can confirm.

Each rule returns a `Verdict`: CONFIRMED (independent evidence agrees), MISMATCH (it disagrees: the
value must go to a human, nothing is ever failed automatically) or NONE (no evidence available).
Every rule states why its evidence is independent of the value it confirms.

The expected-validity profiles and tolerances below are *configurable expectations* about how these
certificates are normally issued, taken from the development data as an example; they are not legal
rules and need confirming with the issuing bodies / the mentor before real use.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from app.core.domain import DocumentType
from app.document_intelligence.internal_evidence import DocFacts

State = Literal["CONFIRMED", "MISMATCH", "NONE"]


@dataclass(frozen=True)
class Verdict:
    state: State
    source: str = ""
    detail: str = ""


NONE = Verdict("NONE")


# ----------------------------------------------------------------------------- GPA


MIN_SEMESTERS = 3
WEIGHTED_AVERAGE_TOLERANCE = 0.015  # semester GPAs are printed to 2 decimals
POINTS_TOLERANCE = 0.006  # total points / total credits, printed exactly


def gpa_arithmetic(facts: DocFacts | None, gpa: float) -> Verdict:
    """Confirm the cumulative GPA by recomputing it from other boxes of the same page.

    Independent because the semester GPAs, the credits and the printed totals are separate OCR boxes
    in different regions from the cumulative GPA box (the cumulative GPA line is excluded from the
    semester pairs); a misread of the cumulative value does not change them. A mismatch blocks.
    """
    g = facts.gpa if facts else None
    if g is None:
        return NONE
    results: list[tuple[str, bool]] = []
    credits = sum(c for c, _ in g.pairs)
    if (
        len(g.pairs) >= MIN_SEMESTERS
        and credits > 0
        and (g.total_credits is None or credits == g.total_credits)
    ):
        average = sum(c * x for c, x in g.pairs) / credits
        results.append(("weighted_average", abs(average - gpa) <= WEIGHTED_AVERAGE_TOLERANCE))
    if g.total_points is not None and g.total_credits:
        results.append(
            ("total_points", abs(g.total_points / g.total_credits - gpa) <= POINTS_TOLERANCE)
        )
    if not results:
        return NONE
    if all(ok for _, ok in results):
        return Verdict("CONFIRMED", "arithmetic", "+".join(name for name, _ in results))
    return Verdict("MISMATCH", "arithmetic", "cumulative GPA does not match the recomputation")


def scale_confirmation(facts: DocFacts | None, scale: str) -> Verdict:
    """The scale printed in the grading legend (top grade value) and beside the semester GPAs.
    Independent: the legend and the per-semester scales are other boxes than the cumulative one."""
    g = facts.gpa if facts else None
    if g is None:
        return NONE
    printed = {item for item in g.semester_scales}
    evidence = []
    if g.legend_max is not None:
        evidence.append(float(g.legend_max) == float(scale))
    if len(g.semester_scales) >= 3:
        evidence.append(len(printed) == 1 and float(next(iter(printed))) == float(scale))
    if not evidence:
        return NONE
    return (
        Verdict("CONFIRMED", "grading_scale")
        if all(evidence)
        else Verdict("MISMATCH", "grading_scale")
    )


# ----------------------------------------------------------------------------- dates


@dataclass(frozen=True)
class ValidityProfile:
    """How a certificate type normally dates itself (configurable expectation)."""

    until_after_issue_days: tuple[int, int] | None = None  # valid_until - issue_date
    span_days: tuple[int, int] | None = None  # valid_until - valid_from
    issue_after_start_days: tuple[int, int] | None = None  # issue_date - valid_from
    tolerance_days: int = 1


VALIDITY_PROFILES: dict[DocumentType, ValidityProfile] = {
    DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE: ValidityProfile(until_after_issue_days=(30, 30)),
    DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE: ValidityProfile(
        until_after_issue_days=(30, 30)
    ),
    DocumentType.SME_CONFIRMATION_CERTIFICATE: ValidityProfile(
        span_days=(364, 365), issue_after_start_days=(0, 31)
    ),
}


def _within(value: int, bounds: tuple[int, int], tolerance: int) -> bool:
    return bounds[0] - tolerance <= value <= bounds[1] + tolerance


def date_pair(
    document_type: DocumentType,
    issue: date | None,
    valid_from: date | None,
    valid_until: date | None,
    profiles: dict[DocumentType, ValidityProfile] | None = None,
) -> Verdict:
    """The dates of one certificate confirm each other when they fit the type's validity profile.

    Independent because the issue date and the validity end are printed in different regions (the
    issuance block, the validity row); the SME validity range sits in one box, so it is only
    confirmed *jointly with the separately printed issue date*. A date that is absent is never
    inferred from the profile, and a pair that does not fit blocks."""
    profile = (profiles or VALIDITY_PROFILES).get(document_type)
    if profile is None:
        return NONE
    checks: list[bool] = []
    if profile.until_after_issue_days is not None:
        if issue is None or valid_until is None:
            return NONE
        checks.append(
            _within(
                (valid_until - issue).days, profile.until_after_issue_days, profile.tolerance_days
            )
        )
    if profile.span_days is not None or profile.issue_after_start_days is not None:
        if issue is None or valid_from is None or valid_until is None:
            return NONE
        if profile.span_days is not None:
            checks.append(
                _within((valid_until - valid_from).days, profile.span_days, profile.tolerance_days)
            )
        if profile.issue_after_start_days is not None:
            checks.append(
                _within(
                    (issue - valid_from).days,
                    profile.issue_after_start_days,
                    profile.tolerance_days,
                )
            )
    if not checks:
        return NONE
    return (
        Verdict("CONFIRMED", "date_pair")
        if all(checks)
        else Verdict("MISMATCH", "date_pair", "dates do not fit the validity profile")
    )


def issue_date_box_for(
    document_type: DocumentType,
    facts: DocFacts | None,
    valid_until: date,
    profiles: dict[DocumentType, ValidityProfile] | None = None,
) -> Verdict:
    """When the issue date itself was not extracted (it is printed unlabelled, e.g. beside a receipt
    number), look at the separately printed dates of the page: a bare date box exactly one profile
    period before `valid_until` supports it. Independent: that box is not the validity-end box; the
    issue date is never invented -- a box must be printed there."""
    profile = (profiles or VALIDITY_PROFILES).get(document_type)
    if facts is None or profile is None or profile.until_after_issue_days is None:
        return NONE
    low, high = profile.until_after_issue_days
    own = [box for box in facts.dates if box.iso == valid_until.isoformat()]
    if not own:
        return NONE
    for box in facts.dates:
        parsed = parse_iso(box.iso)
        if (
            parsed is None
            or not box.bare
            or any(box.iso == o.iso and box.x == o.x and box.y == o.y for o in own)
        ):
            continue
        if _within((valid_until - parsed).days, (low, high), profile.tolerance_days):
            return Verdict(
                "CONFIRMED", "date_pair", "a separately printed date one validity period earlier"
            )
    return NONE


MIN_SEPARATION_HEIGHTS = 1.5


def printed_twice(facts: DocFacts | None, iso: str) -> Verdict:
    """The same date printed in two separate boxes (e.g. the issuer-block date and the date beside
    "재학중"), each a bare date. Independent: different boxes at least 1.5 text heights apart; two
    mentions inside one box never count, and a missing second occurrence is never borrowed."""
    if facts is None:
        return NONE
    boxes = [item for item in facts.dates if item.iso == iso and item.bare]
    for index, first in enumerate(boxes):
        for second in boxes[index + 1 :]:
            if first.page != second.page or abs(first.y - second.y) >= MIN_SEPARATION_HEIGHTS * max(
                first.height, second.height
            ):
                return Verdict("CONFIRMED", "printed_twice")
    return NONE


def parse_iso(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


__all__ = [
    "Verdict",
    "NONE",
    "ValidityProfile",
    "VALIDITY_PROFILES",
    "gpa_arithmetic",
    "scale_confirmation",
    "date_pair",
    "printed_twice",
    "parse_iso",
    "timedelta",
]
