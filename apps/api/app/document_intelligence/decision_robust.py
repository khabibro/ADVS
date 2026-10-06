"""Decision-robust acceptance (D3-5).

A lone decision-driving value may be accepted *for the decision* when every plausible misreading of
it leads to the same verification outcome. The set of plausible misreadings comes from the explicit
confusion table (`ocr_confusions.py`); alternatives that are not valid values (an impossible date, a
GPA above the scale) or that contradict a confirmed date profile are discarded.

Safety argument: for an error inside the table (a single substitution, one adjacent transposition,
one dropped or added digit) the outcome of every active rule on that field is identical for the read
value and for each alternative, so whichever of them is the truth the decision is the same. Errors
outside the table are not covered by this argument and are measured with the injection suites. The
value itself stays unconfirmed: it is shown labelled "decision-robust, not individually confirmed".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.core.domain import DocumentType
from app.document_intelligence.confirmations import VALIDITY_PROFILES, date_pair, parse_iso
from app.document_intelligence.normalization.field_normalizer import normalize_date
from app.document_intelligence.ocr_confusions import alternative_readings


@dataclass(frozen=True)
class RuleSpec:
    """One active workflow rule on a field. kind: on_or_after_ref | on_or_before | on_or_after |
    max_age | at_least | at_most."""

    document_type: DocumentType
    field: str
    kind: str
    bound_date: date | None = None
    bound_number: float | None = None
    days: int | None = None


def outcomes(
    specs: list[RuleSpec],
    reference: date | None,
    field: str,
    document_type: DocumentType,
    value: str,
) -> tuple[bool, ...] | None:
    """The tuple of rule outcomes for `value`, or None if it cannot be evaluated."""
    result: list[bool] = []
    for spec in specs:
        if spec.field != field or spec.document_type != document_type:
            continue
        if spec.kind in ("on_or_after_ref", "on_or_before", "on_or_after", "max_age"):
            parsed = parse_iso(value)
            if parsed is None:
                return None
            if spec.kind == "on_or_after_ref":
                if reference is None:
                    return None
                result.append(parsed >= reference)
            elif spec.kind == "on_or_before" and spec.bound_date is not None:
                result.append(parsed <= spec.bound_date)
            elif spec.kind == "on_or_after" and spec.bound_date is not None:
                result.append(parsed >= spec.bound_date)
            elif spec.kind == "max_age" and spec.days is not None:
                if reference is None:
                    return None
                result.append(reference - parsed <= timedelta(days=spec.days))
        else:
            try:
                number = float(value)
            except ValueError:
                return None
            if spec.bound_number is None:
                return None
            result.append(
                number >= spec.bound_number
                if spec.kind == "at_least"
                else number <= spec.bound_number
            )
    return tuple(result)


def _alternative_values(field: str, value: str, scale: float | None) -> list[str]:
    valid: list[str] = []
    for text in alternative_readings(value):
        if field in ("issue_date", "valid_from", "valid_until"):
            iso = normalize_date(text)
            if iso is not None and 1990 <= int(iso[:4]) <= 2100:
                valid.append(iso)
        elif field == "gpa":
            try:
                number = float(text)
            except ValueError:
                continue
            if 0 <= number <= (scale or 4.5) and text.count(".") <= 1:
                valid.append(text)
    return sorted(set(valid) - {value})


def is_decision_robust(
    specs: list[RuleSpec],
    reference: date | None,
    field: str,
    document_type: DocumentType,
    value: str,
    *,
    scale: float | None = None,
    siblings: dict[str, date | None] | None = None,
) -> bool:
    """True when the read value and every valid alternative reading give identical rule outcomes."""
    base = outcomes(specs, reference, field, document_type, value)
    if not base:  # no rule uses the value, or it cannot be evaluated: nothing to be robust about
        return False
    profile_applies = False
    if (
        siblings
        and field in ("issue_date", "valid_from", "valid_until")
        and VALIDITY_PROFILES.get(document_type)
    ):
        read = {**siblings, field: parse_iso(value)}
        profile_applies = (
            date_pair(
                document_type,
                read.get("issue_date"),
                read.get("valid_from"),
                read.get("valid_until"),
            ).state
            == "CONFIRMED"
        )
    for alternative in _alternative_values(field, value, scale):
        if profile_applies:
            merged = {**(siblings or {}), field: parse_iso(alternative)}
            pair = date_pair(
                document_type,
                merged.get("issue_date"),
                merged.get("valid_from"),
                merged.get("valid_until"),
            )
            if pair.state == "MISMATCH":
                continue  # the date profile the read values satisfy rules this reading out
        if outcomes(specs, reference, field, document_type, alternative) != base:
            return False
    return True
