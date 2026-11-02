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
#: The rounding bound only, never widened: the credit-weighted mean of values printed to 2 decimals is itself
#: rounded to 2 decimals and compared with the printed total, which may differ by one unit in the last place
#: (a mean of 87.4985 rounds to 87.50 against a printed 87.51).
ROUNDING_BOUND = 0.010
_EPSILON = 1e-9


def _gpa_within_truncation(mean: float, printed: float) -> bool:
    """The university truncates (floors) GPAs to 2 decimals. With M the credit-weighted mean of the printed
    semester GPAs, each of which is floored, the true mean lies in [M, M + 0.01) and the floored total P in
    (M - 0.01, M + 0.01): the exact bound, open at both ends."""
    return mean - 0.01 < printed < mean + 0.01


def _agrees(mean: float, printed: float) -> bool:
    """The mean, rounded to 2 decimals, equals the printed 2-decimal value within one last-place unit."""
    return abs(round(mean, 2) - printed) <= ROUNDING_BOUND + _EPSILON
POINTS_TOLERANCE = 0.006  # total points / total credits, printed exactly


def gpa_arithmetic(facts: DocFacts | None, gpa: float) -> Verdict:
    """Confirm the cumulative GPA by recomputing it from other boxes of the same page.

    Independent because the semester GPAs, the credits and the printed totals are separate OCR boxes
    in different regions from the cumulative GPA box (the cumulative GPA line is excluded from the
    semester pairs); a misread of the cumulative value does not change them.

    Three outcomes. CONFIRMED: the table reproduces the page and the total within the rounding bound.
    MISMATCH: the table is sound (the credits add up to the printed total and, where printed, the 백분율
    average reproduces the printed 백분율) and the GPA still disagrees: the numbers truly disagree.
    NONE ("could not check"): anything else -- too few semesters, credits that do not add up, a 백분율 that
    does not reproduce -- is a reading or parsing problem, never a mismatch.
    """
    g = facts.gpa if facts else None
    if g is None:
        return NONE
    results: list[tuple[str, bool]] = []
    credits = sum(c for c, _ in g.pairs)
    if (
        len(g.pairs) >= MIN_SEMESTERS
        and credits > 0
        and g.total_credits is not None  # a table is known to be complete only if its credits add up
        and credits == g.total_credits
    ):
        if g.percent_pairs and g.total_percent is not None and len(g.percent_pairs) == len(g.pairs):
            percent = sum(c * x for c, x in g.percent_pairs) / sum(c for c, _ in g.percent_pairs)
            if not _agrees(percent, g.total_percent):
                return NONE  # the table does not reproduce the printed 백분율: not a table to judge by
            results.append(("weighted_percent", True))
        average = sum(c * x for c, x in g.pairs) / credits
        results.append(("weighted_average", _gpa_within_truncation(average, gpa)))
    if g.total_points is not None and g.total_credits:
        results.append(
            ("total_points", abs(g.total_points / g.total_credits - gpa) <= POINTS_TOLERANCE)
        )
    if not [name for name, _ in results if name != "weighted_percent"]:
        return NONE
    if all(ok for _, ok in results):
        return Verdict("CONFIRMED", "arithmetic", "+".join(name for name, _ in results))
    return Verdict(
        "MISMATCH",
        "arithmetic",
        "the printed semesters reproduce their credits (and 백분율) but their credit-weighted GPA mean "
        "differs from the printed total by more than the floor bound; a retake, a pass/fail course or "
        "transfer credits can do this on a genuine certificate, a misread digit can too",
    )


#: The university truncates GPAs and 백분율 to 2 decimals, so a printed value p stands for [p, p + 0.01). A line
#: (g, p) on a relation p = a*g + b may therefore be off by 0.01*|a| (the GPA) plus 0.01 (the 백분율) and no more.
MIN_RELATION_PAIRS = 3
_TRUNCATION = 0.01


def _relation_bound(slope: float) -> float:
    return _TRUNCATION * abs(slope) + _TRUNCATION


def percent_relation_fit(facts: DocFacts | None) -> tuple[float, float] | None:
    """The relation 백분율 = a * GPA + b of the page, fitted from the grading legend and the semester lines only,
    never from the cumulative line. It exists only if at least three pairs fit and every one of them lies within
    the truncation bound of the fitted line. The top grade of the legend is left out: its range ends at the
    ceiling of 100, which is not a measured upper bound."""
    g = facts.gpa if facts else None
    if g is None:
        return None
    pairs = [pair for pair in g.legend_pairs if pair[1] < 100] + list(g.semester_percent_pairs)
    if g.total_pair is not None:  # a semester line identical to the cumulative line must not stand in for it
        pairs = [pair for pair in pairs if pair != g.total_pair]
    if len(pairs) < MIN_RELATION_PAIRS or len({gp for gp, _ in pairs}) < 2:
        return None
    n = len(pairs)
    mean_g = sum(gp for gp, _ in pairs) / n
    mean_p = sum(pp for _, pp in pairs) / n
    spread = sum((gp - mean_g) ** 2 for gp, _ in pairs)
    if spread == 0:
        return None
    slope = sum((gp - mean_g) * (pp - mean_p) for gp, pp in pairs) / spread
    intercept = mean_p - slope * mean_g
    bound = _relation_bound(slope)
    if any(abs(pp - (slope * gp + intercept)) > bound + 1e-9 for gp, pp in pairs):
        return None
    return slope, intercept


def gpa_percent_relation(facts: DocFacts | None, gpa: float) -> Verdict:
    """The total GPA confirmed by the page's own GPA-to-백분율 conversion: the cumulative line's (GPA, 백분율)
    pair lies on the relation fitted from the legend and the semester lines, within the truncation bound. No
    relation (too few pairs, or pairs that do not agree): nothing is said. A relation that the total does not fit
    is a disagreement."""
    g = facts.gpa if facts else None
    fit = percent_relation_fit(facts)
    if g is None or fit is None or g.total_pair is None or abs(g.total_pair[0] - gpa) > 1e-9:
        return NONE
    slope, intercept = fit
    if abs(g.total_pair[1] - (slope * g.total_pair[0] + intercept)) <= _relation_bound(slope) + 1e-9:
        return Verdict("CONFIRMED", "percent_relation")
    return Verdict(
        "MISMATCH",
        "percent_relation",
        "the page's own GPA-to-백분율 conversion does not give the printed total 백분율 for the printed total GPA",
    )


def business_number_copy(facts: DocFacts | None, digits: str, floor: float) -> Verdict:
    """The business number printed a second time on the same page (the 11-digit management number, whose first
    ten digits are the business number). Two reads of separate boxes that agree, with a valid check digit,
    confirm it; the copy must itself be read above the floor. A differing copy confirms nothing."""
    from app.document_intelligence.normalization.field_normalizer import is_valid_business_number

    if facts is None or not is_valid_business_number(digits):
        return NONE
    agreeing = [
        confidence
        for prefix, confidence in facts.management_numbers
        if prefix == digits and confidence is not None and confidence >= floor
    ]
    return Verdict("CONFIRMED", "second_copy") if agreeing else NONE


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
    # a validity shorter than the period (down to the issue date) is lawful but never a confirmation
    shorter_is_consistent: bool = False
    # False: the profile is a consistency check only. A range that does not fit is flagged; one that fits
    # confirms nothing (the printed validity end is never taken from, or confirmed by, an assumed period).
    confirms: bool = True


#: Only relations that rest on a legal period or on measured real certificates may confirm a date.
#: * 국세 납세증명서: 국세징수법 시행령 제96조 제1항: valid for 30 days from issue; shortened (to a payment
#:   deadline, with the reason and period printed) only when a tax is due sooner. Exactly +30 confirms; a shorter
#:   validity is consistent, not confirmed; a longer one or one before the issue date is inconsistent.
#: * 4대보험 완납증명서: no legal period; real certificates are valid 7-28 days after their issue (measured), so
#:   there is no profile: its validity end is the printed one, confirmed by other evidence or by a person.
#: * 중소기업확인서: no real sample; the one-year validity is set by the fiscal year, not by the issue date, and a
#:   certificate may be issued at any time during it (the "issue within a month of the start" relation was a property
#:   of the fictional data and is out). The one-year span is a consistency check only: its validity end is the printed
#:   one, never confirmed or taken from the profile.
VALIDITY_PROFILES: dict[DocumentType, ValidityProfile] = {
    DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE: ValidityProfile(
        until_after_issue_days=(30, 30), tolerance_days=0, shorter_is_consistent=True
    ),
    DocumentType.SME_CONFIRMATION_CERTIFICATE: ValidityProfile(span_days=(364, 365), confirms=False),
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
        days = (valid_until - issue).days
        if profile.shorter_is_consistent and 0 <= days < profile.until_after_issue_days[0]:
            return NONE  # shortened by law (reason printed): consistent, not confirmed
        checks.append(_within(days, profile.until_after_issue_days, profile.tolerance_days))
    if profile.span_days is not None or profile.issue_after_start_days is not None:
        if valid_from is None or valid_until is None:
            return NONE
        if profile.issue_after_start_days is not None and issue is None:
            return NONE
        if profile.span_days is not None:
            checks.append(
                _within((valid_until - valid_from).days, profile.span_days, profile.tolerance_days)
            )
        if profile.issue_after_start_days is not None and issue is not None:
            checks.append(
                _within(
                    (issue - valid_from).days,
                    profile.issue_after_start_days,
                    profile.tolerance_days,
                )
            )
    if not checks:
        return NONE
    if not all(checks):
        return Verdict("MISMATCH", "date_pair", "dates do not fit the validity profile")
    return Verdict("CONFIRMED", "date_pair") if profile.confirms else NONE


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


# Business registration number type code (digits 4-5 of the ten digits). Configurable expectation,
# not a legal rule: it is commonly published that 01-79 are individual taxpayers, 81/84/85/86/87/88
# are for-profit corporations, 82 non-profit corporations, 89 other bodies, 90-99 tax-exempt
# individuals. Validation only: a plausible code never confirms a number; an implausible one
# (a form that states "corporate" with an individual code) sends it to a human.
BUSINESS_TYPE_CODES: dict[str, tuple[tuple[int, int], ...]] = {
    "individual": ((1, 79), (90, 99)),
    "corporate": ((81, 89),),
}


def business_number_type_plausible(number: str, entity_type: str | None) -> bool | None:
    """True/False when the form states its entity type and the number has a type code; else None."""
    if entity_type not in BUSINESS_TYPE_CODES or len(number) != 10 or not number.isdigit():
        return None
    code = int(number[3:5])
    return any(low <= code <= high for low, high in BUSINESS_TYPE_CODES[entity_type])
