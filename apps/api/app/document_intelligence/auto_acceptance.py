"""Auto-acceptance of OCR values: decide which OCR-read fields still need a human.

Today's evidence policy sends every OCR-read field to a person. This module lets an OCR
value stand **only when something independent confirms it**. It never edits machine
evidence and never replaces human review: it only decides whether a field still needs
one. The decision is computed on the fly from the project's current documents, so
re-processing a document invalidates it automatically.

Strategies (one switch, `Settings.auto_accept_strategy`)
-------------------------------------------------------
S0  none (every OCR field goes to a human; the previous behaviour)
S1  confidence >= floor only                        (unsafe: shown to prove why)
S2  S1 + format validators
S3  S2 + corroboration by another document
S4  S3, or a second OCR pass of the field's region that agrees (fields with no corroborator)
S5  S4 + the application's own values (project company name / applicant name) as an
    independent source, and a veto when they disagree
S6  S5 + a disagreeing second pass vetoes any acceptance of a numeric field
S8  S7 + internal confirmations from the document's own content (GPA arithmetic, date-pair
    consistency, a date printed twice) -- see confirmations.py
S9  S8 + decision-robust acceptance of a lone decision-driving value (every plausible misreading
    leads to the same verification outcome)
S7  S6 + a second pass that does not contain a name's value vetoes the acceptance of that name
    (a second pass never *accepts* a name -- rule 4 -- it can only contradict it)

Mandatory rules (all corroborating strategies)
----------------------------------------------
1. Exact equality only, after field-specific canonicalisation (no similarity, no edit distance).
2. Independence: a corroborating value comes from a different document (different file hash)
   or from a second OCR pass with different preprocessing. A value never corroborates itself.
3. No majority voting: a disagreement from any other document means no acceptance by corroboration.
4. Person and company names are accepted only through corroboration (documents or the
   application), never through a second pass of the same image.
5. Mismatch handling stays with the existing rules: a value that is not accepted is simply
   left to a human; this module never produces a NEEDS_CORRECTION by itself.
"""

from __future__ import annotations

import logging
import re
import unicodedata
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from enum import StrEnum
from typing import Any

from app.core.domain import DocumentType
from app.document_intelligence.candidate_repair import PROVENANCE, propose_repair
from app.document_intelligence.company_names import (
    alias_pool,
    company_aliases,
    company_key,
    company_names_agree,
    typed_name_matches,
)
from app.document_intelligence.confirmations import (
    VALIDITY_PROFILES,
    business_number_copy,
    business_number_type_plausible,
    date_pair,
    gpa_arithmetic,
    gpa_percent_relation,
    issue_date_box_for,
    parse_iso,
    printed_twice,
    scale_confirmation,
)
from app.document_intelligence.decision_robust import RuleSpec, is_decision_robust
from app.document_intelligence.internal_evidence import DocFacts
from app.document_intelligence.normalization.field_normalizer import (
    DATE_RE,
    LEGAL_ENTITY_MARKERS,
    canonicalize_numeric_text,
    is_valid_business_number,
    normalize_business_number,
    normalize_date,
)
from app.document_intelligence.ocr_confusions import CONFUSION_TABLE_VERSION
from app.document_intelligence.validation.submission import institution_key

_LOG = logging.getLogger("advs.auto_acceptance")

AUTO_ACCEPT_POLICY_VERSION = "auto-accept-v1"

#: A value accepted only because every plausible misreading gives the same verdict is never presented as
#: confirmed. Staff-facing copy, English and Korean; the UI shows it next to the value.
DECISION_ROBUST_LABEL = "decision-robust (value not individually confirmed)"
DECISION_ROBUST_LABEL_KO = "판정상 안전 (값 미확정)"


class Strategy(StrEnum):
    S0 = "S0"
    S1 = "S1"
    S2 = "S2"
    S3 = "S3"
    S4 = "S4"
    S5 = "S5"
    S6 = "S6"
    S7 = "S7"
    S8 = "S8"
    S9 = "S9"
    S10 = "S10"  # S9 + the student pair: cross-document confirmation, both reads above the floor
    S11 = "S11"  # S10 + a below-floor read confirmed by an exact match with the other document
    S12 = "S12"  # S11 + the same-person verdict is decision-robust when both names read the same
    S13 = "S13"  # S11 + business pair: second copy of the business number, below-floor exact confirmations
    S14 = "S14"  # S15 + the second-pass name veto is lifted for a jumbled re-read when another document reads back
    S15 = "S15"  # S13 + company identity by numbers: names that agree but cannot be confirmed no longer block
    S16 = "S16"  # S14 + route A: the total GPA confirmed by the page's own GPA-to-백분율 conversion
    S17 = "S17"  # S14 + route B: the applicant-entered GPA and scale
    S18 = "S18"  # S14 + routes A and B
    S19 = "S19"  # S16 + a narrow boundary margin for GPA values the page itself confirms (report-only option)
    S20 = "S20"  # S18 + the same narrow margin (report-only option)
    S21 = "S21"  # S17 + the live-strictness fixes (company aliases, typed-name/GPA exact confirmation, ...)


@dataclass(frozen=True)
class Features:
    validators: bool = False
    corroboration: bool = False
    second_pass: bool = False
    application: bool = False
    second_pass_veto: bool = False
    name_veto: bool = False
    internal: bool = False  # D3-1..D3-4: confirmation from the document's own content
    robust: bool = False  # D3-5: acceptance for the decision when every plausible misreading agrees
    # Student pair (enrolment certificate primary, transcript confirming): the other document counts only
    # with a read above the floor, issue dates are confirmed across the two documents, institution names
    # are compared by their name part.
    student_pair: bool = False
    pair_below_floor: bool = (
        False  # a below-floor read is confirmed by an exact match of a reliable one
    )
    # Both student documents read the same name exactly (any confidence) and the date of birth is confirmed on
    # both: the same-person verdict does not depend on which characters the name really has. The name value
    # stays unconfirmed.
    name_pair_robust: bool = False
    # Business certificates (사업자등록증, 국세 납세증명서, 4대보험 완납증명서): the business number is confirmed by
    # its second copy on the same page, and a below-floor business number or validity end is confirmed by an exact
    # independent relation (equal reliable read on another document; issue date plus the legal period).
    business_pair: bool = False
    # A jumbled second-pass re-read (it neither shows the name nor looks like a misread of it) does not veto a
    # name that another document carries identically and whose own re-read shows it.
    veto_lift: bool = False
    # Company identity by numbers: when the business number is confirmed on at least two documents and equal on
    # every document that prints it, a company or workplace name that agrees with every other name read but is
    # held by the floor or the second-pass veto no longer blocks; it stays unconfirmed and is labelled so.
    company_identity: bool = False
    # Route A: the total GPA is confirmed when its (GPA, 백분율) pair lies on the conversion that the legend and the
    # semester lines of the same page fit (never fitted from the total line itself).
    gpa_relation: bool = False
    # Route B: a GPA and scale typed by the applicant confirm the read value and scale only by exact equality.
    applicant_gpa: bool = False
    # A GPA the page itself confirms (arithmetic, conversion) is pinned to the printed truncation (0.01), so the
    # distance to the threshold that blocks it can be this small instead of the policy margin. None = policy margin.
    confirmed_gpa_margin: float | None = None
    # Every name form a certificate prints (the Korean name, the Latin name in brackets) is an alias: a typed
    # company name conflicts only when it equals none of the aliases printed on the documents of that business.
    company_alias: bool = False
    # A same-image re-read may not veto a first read that passes the floor and that the other document (or the typed
    # name) reads exactly the same, unless the re-read is itself a plausible, different value.
    veto_exact_lift: bool = False
    # The applicant-typed name equals a below-floor read exactly: two independent sources confirm it (like route B).
    applicant_name_confirm: bool = False
    # Certificate end dates: the fixed 10-day margin around the check date is replaced by the digit-confusion
    # check (decision_robust.py): an unconfirmed end date passes only when every likely misreading gives the same
    # verdict at the check date.
    robust_end_dates: bool = False


STRATEGY_FEATURES: dict[Strategy, Features] = {
    Strategy.S0: Features(),
    Strategy.S1: Features(),
    Strategy.S2: Features(validators=True),
    Strategy.S3: Features(validators=True, corroboration=True),
    Strategy.S4: Features(validators=True, corroboration=True, second_pass=True),
    Strategy.S5: Features(validators=True, corroboration=True, second_pass=True, application=True),
    Strategy.S6: Features(
        validators=True,
        corroboration=True,
        second_pass=True,
        application=True,
        second_pass_veto=True,
    ),
    Strategy.S7: Features(
        validators=True,
        corroboration=True,
        second_pass=True,
        application=True,
        second_pass_veto=True,
        name_veto=True,
    ),
    Strategy.S8: Features(
        validators=True,
        corroboration=True,
        second_pass=True,
        application=True,
        second_pass_veto=True,
        name_veto=True,
        internal=True,
    ),
    Strategy.S9: Features(
        validators=True,
        corroboration=True,
        second_pass=True,
        application=True,
        second_pass_veto=True,
        name_veto=True,
        internal=True,
        robust=True,
    ),
    Strategy.S10: Features(
        validators=True,
        corroboration=True,
        second_pass=True,
        application=True,
        second_pass_veto=True,
        name_veto=True,
        internal=True,
        robust=True,
        student_pair=True,
    ),
    Strategy.S11: Features(
        validators=True,
        corroboration=True,
        second_pass=True,
        application=True,
        second_pass_veto=True,
        name_veto=True,
        internal=True,
        robust=True,
        student_pair=True,
        pair_below_floor=True,
    ),
    Strategy.S12: Features(
        validators=True,
        corroboration=True,
        second_pass=True,
        application=True,
        second_pass_veto=True,
        name_veto=True,
        internal=True,
        robust=True,
        student_pair=True,
        pair_below_floor=True,
        name_pair_robust=True,
    ),
    Strategy.S13: Features(
        validators=True,
        corroboration=True,
        second_pass=True,
        application=True,
        second_pass_veto=True,
        name_veto=True,
        internal=True,
        robust=True,
        student_pair=True,
        pair_below_floor=True,
        business_pair=True,
    ),
    Strategy.S15: Features(
        validators=True,
        corroboration=True,
        second_pass=True,
        application=True,
        second_pass_veto=True,
        name_veto=True,
        internal=True,
        robust=True,
        student_pair=True,
        pair_below_floor=True,
        business_pair=True,
        company_identity=True,
    ),
    Strategy.S14: Features(
        validators=True,
        corroboration=True,
        second_pass=True,
        application=True,
        second_pass_veto=True,
        name_veto=True,
        internal=True,
        robust=True,
        student_pair=True,
        pair_below_floor=True,
        business_pair=True,
        company_identity=True,
        veto_lift=True,
    ),
}
# Routes A and B stack on the default (S14).
STRATEGY_FEATURES[Strategy.S16] = replace(STRATEGY_FEATURES[Strategy.S14], gpa_relation=True)
STRATEGY_FEATURES[Strategy.S17] = replace(STRATEGY_FEATURES[Strategy.S14], applicant_gpa=True)
STRATEGY_FEATURES[Strategy.S18] = replace(
    STRATEGY_FEATURES[Strategy.S14], gpa_relation=True, applicant_gpa=True
)
STRATEGY_FEATURES[Strategy.S21] = replace(
    STRATEGY_FEATURES[Strategy.S17],
    company_alias=True,
    veto_exact_lift=True,
    applicant_name_confirm=True,
    robust_end_dates=True,
)
STRATEGY_FEATURES[Strategy.S19] = replace(
    STRATEGY_FEATURES[Strategy.S16], confirmed_gpa_margin=0.05
)
STRATEGY_FEATURES[Strategy.S20] = replace(
    STRATEGY_FEATURES[Strategy.S18], confirmed_gpa_margin=0.05
)

STUDENT_PAIR_TYPES = frozenset({DocumentType.ENROLLMENT_CERTIFICATE, DocumentType.TRANSCRIPT})
BUSINESS_PAIR_TYPES = frozenset(
    {
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE,
        DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE,
    }
)
#: Business fields a below-floor read may be confirmed for.
BUSINESS_BELOW_FLOOR_FIELDS = frozenset({"business_registration_number", "valid_until"})
#: Marks a decision that rests on the same value on the other student document (an inferred issue date was
#: accepted).
CROSS_DOCUMENT_SOURCE = "cross_document"


def parse_strategy(value: str | None) -> Strategy:
    try:
        return Strategy((value or "S0").strip().upper())
    except ValueError:
        return Strategy.S0


# ---------------------------------------------------------------------------
# Per-field rule table (the one place that says what each field may rely on)
# ---------------------------------------------------------------------------

#: Minimum OCR confidence. Confidence is a floor, never a reason to accept on its own:
#: calibration on the development set found no usable separation between correct and
#: wrong values (see evaluation/phase_d/calibration.md), and the injection suite shows
#: high-confidence errors. The floor equals the evidence policy's existing 0.90.
CONFIDENCE_FLOOR = 0.90


@dataclass(frozen=True)
class FieldRule:
    rule_id: str
    group: str | None  # identity attribute shared across documents (corroboration)
    second_pass: bool  # a second pass of the region may confirm it
    application: str | None = None  # project attribute it can be compared with
    floor: float = CONFIDENCE_FLOOR
    name_veto: bool = False  # a second pass may contradict (never confirm) this value
    # May a second pass of the same image confirm this value on its own? Owner decision after
    # Phase D2: no for the decision-driving fields (a misread repeated by both passes could flip
    # a decision); they need another document or the application value. The second pass is still
    # read for them and still vetoes (S6/S7).
    confirm_by_second_pass: bool = True


FIELD_RULES: dict[str, FieldRule] = {
    "business_registration_number": FieldRule("BRN", "business_number", True),
    "company_name": FieldRule("COMPANY", "company", False, "company_name", name_veto=True),
    "workplace_name": FieldRule("COMPANY", "company", False, "company_name", name_veto=True),
    "student_name": FieldRule("PERSON", "person", False, "applicant_name", name_veto=True),
    "student_id": FieldRule("STUDENT_ID", "student_id", True, confirm_by_second_pass=False),
    "university_name": FieldRule("UNIVERSITY", "university", False, name_veto=True),
    "issue_date": FieldRule("DATE", None, True, confirm_by_second_pass=False),
    "birth_date": FieldRule("DATE", "birth_date", True, confirm_by_second_pass=False),
    "admission_date": FieldRule("DATE", "admission_date", True, confirm_by_second_pass=False),
    "valid_from": FieldRule("DATE", None, True, confirm_by_second_pass=False),
    "valid_until": FieldRule("DATE", None, True, confirm_by_second_pass=False),
    "gpa": FieldRule("GPA", None, True, confirm_by_second_pass=False),
    "gpa_scale": FieldRule("GPA", None, True, confirm_by_second_pass=False),
}

# Decision-boundary margins (Phase D2). A value confirmed *only* by a second pass of the same
# image is not auto-accepted when it lies this close to a decision boundary of the workflow:
#   date_days -- valid_until / valid_from within N days of the reference date, and issue_date within
#                N days of the age limit (reference date - max age);
#   gpa       -- within X of the configured GPA threshold.
# Chosen from the injection analysis (evaluation/phase_d2/margins.md): E11 moves dates 0-7 days
# across the boundary (N = 10 keeps a margin over the largest tested shift, and the largest
# shift a day-digit confusion can cause is 8 days); E12 moves a GPA to 3.00-3.10 (X = 0.5 covers
# the first-decimal confusions 0.1-0.5). Larger margins were rejected because 납세증명서 and
# 완납증명원 normally expire 20-30 days after issue, so N >= 31 would send every such date to a
# human and remove the scanned all-valid READY.
BOUNDARY_MARGINS: dict[str, float] = {"date_days": 10, "gpa": 0.5}
# A certificate is valid for a bounded span; a validity end far beyond the issue date (or the
# start) is the signature of a year/month digit misread. Policy constant, days.
MAX_VALIDITY_SPAN_DAYS = 400

# Fields whose value a second pass can re-read and compare as a number/date.
SECOND_PASS_FIELDS = frozenset(
    name for name, rule in FIELD_RULES.items() if rule.second_pass or rule.name_veto
)
KNOWN_GPA_SCALES = frozenset({"4", "4.3", "4.5"})
STUDENT_ID_RE = re.compile(r"^\d{8,10}$")
_GPA_PAIR_RE = re.compile(r"(\d(?:\.\d{1,3})?)\s*/\s*(\d(?:\.\d{1,3})?)")


# ---------------------------------------------------------------------------
# Canonical keys
# ---------------------------------------------------------------------------


def _squash(text: str) -> str:
    return "".join(unicodedata.normalize("NFKC", text).split())


def canonical_key(group: str, value: str, *, tolerant: bool = False) -> str:
    """Comparison key of a value within its group. `tolerant` compares an institution by its name part
    (generic affixes and the issuer title dropped), because a stamp may cover the last characters of the
    issuer line."""
    if group in ("business_number", "student_id"):
        return "".join(ch for ch in value if ch.isdigit())
    if group == "company":
        return company_key(value)
    if group == "university" and tolerant:
        return institution_key(value)
    return _squash(value)


def _business_number_of(item: FieldInput, index: _Index) -> str | None:
    number = index.sibling(item.document_id, "business_registration_number")
    return number.value if number is not None else None


def _company_alias_pool(
    item: FieldInput, fields: Sequence[FieldInput], index: _Index
) -> frozenset[str]:
    """Every name form printed on the documents of the item's business (same valid business number)."""
    number = "".join(ch for ch in (_business_number_of(item, index) or "") if ch.isdigit())
    values: list[str | None] = [item.value]
    for other in fields:
        rule = FIELD_RULES.get(other.field_name)
        if (
            other.document_id == item.document_id
            or rule is None
            or rule.group != "company"
            or other.value is None
        ):
            continue
        theirs = "".join(ch for ch in (_business_number_of(other, index) or "") if ch.isdigit())
        if number and theirs == number and is_valid_business_number(number):
            values.append(other.value)
    return alias_pool(values)


def parse_second_pass(field_name: str, text: str | None) -> str | None:
    """Normalise a second-pass reading of a region the same way the first pass is."""
    if not text:
        return None
    rule = FIELD_RULES.get(field_name)
    if rule is not None and rule.name_veto:
        return _squash(text)  # names: the whole reading, compared by containment (veto only)
    folded = canonicalize_numeric_text(text)
    if field_name == "business_registration_number":
        return normalize_business_number(folded)
    if field_name == "student_id":
        runs = re.findall(r"(?<!\d)\d{8,10}(?!\d)", folded)
        return runs[0] if len(set(runs)) == 1 else None
    if field_name in ("issue_date", "valid_from", "valid_until", "birth_date", "admission_date"):
        found = [normalize_date(match.group(0)) for match in DATE_RE.finditer(folded)]
        if not found or any(item is None for item in found):
            return None
        if len(found) == 1:
            return found[0]
        if len(found) == 2 and field_name in ("valid_from", "valid_until"):
            # a validity range printed in one box: start, then end
            return found[0] if field_name == "valid_from" else found[1]
        return None
    if field_name in ("gpa", "gpa_scale"):
        tail = folded.split("평점평균", 1)[-1]
        match = _GPA_PAIR_RE.search(tail)
        if not match:
            return None
        text_value = match.group(1) if field_name == "gpa" else match.group(2)
        try:
            from decimal import Decimal

            return format(Decimal(text_value).normalize(), "f")
        except Exception:
            return None
    return None


# ---------------------------------------------------------------------------
# Inputs / outputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SecondPassInput:
    text: str | None
    normalized: str | None
    confidence: float | None
    preprocess: str = ""


@dataclass(frozen=True)
class FieldInput:
    document_id: uuid.UUID
    checksum: str
    document_type: DocumentType
    field_name: str
    value: str | None  # machine normalized value
    confidence: float | None
    ocr: bool  # the value was read by OCR (not embedded text)
    needs_review: bool
    extraction_method: str | None = None
    second_pass: SecondPassInput | None = None
    has_current_review: bool = False
    # Other values of the same kind printed on the same document (a transcript's per-semester
    # GPAs): a cumulative value must lie among them.
    peer_values: tuple[float, ...] = ()
    facts: DocFacts | None = None  # what the document's own boxes say (internal_evidence.py)


@dataclass(frozen=True)
class ProjectContext:
    company_name: str | None = None
    applicant_name: str | None = None
    reference_date: date | None = None
    issue_max_age_days: int | None = None  # the workflow's ISSUE_DATE_MAX_AGE, if configured
    gpa_threshold: float | None = None  # the workflow's GPA threshold, if configured
    applicant_gpa: str | None = None  # route B: the GPA the applicant typed (e.g. "3.40")
    applicant_gpa_scale: str | None = None  # route B: the scale the applicant typed (e.g. "4.3")
    rules: tuple[RuleSpec, ...] = ()  # the workflow's active rules on decision-driving fields


@dataclass(frozen=True)
class AutoDecision:
    accepted: bool
    strategy: str
    policy_version: str = AUTO_ACCEPT_POLICY_VERSION
    rule_id: str | None = None
    sources: tuple[str, ...] = ()
    corroborating_document_ids: tuple[uuid.UUID, ...] = ()
    second_pass_value: str | None = None
    reason: str | None = None  # why it was NOT accepted
    robust: bool = False  # accepted for the decision only (every plausible misreading agrees)
    repair_candidate: str | None = (
        None  # D3-9: a proposed repair of a failed checksum (never applied)
    )
    lifted_veto: str | None = None  # the same-image re-read that did not veto this value (logged)

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "strategy": self.strategy,
            "policy_version": self.policy_version,
            "rule_id": self.rule_id,
            "sources": list(self.sources),
            "corroborating_document_ids": [str(item) for item in self.corroborating_document_ids],
            "second_pass_value": self.second_pass_value,
            "reason": self.reason,
            "robust": self.robust,
            "repair_candidate": self.repair_candidate,
            "lifted_veto": self.lifted_veto,
            "repair_provenance": PROVENANCE if self.repair_candidate else None,
            "confusion_table_version": CONFUSION_TABLE_VERSION
            if self.robust or self.repair_candidate
            else None,
            "confirmation": (
                "DECISION_ROBUST"
                if self.robust
                else "INDEPENDENT_SOURCE"
                if self.accepted
                else None
            ),
            "label": DECISION_ROBUST_LABEL if self.robust else None,
            "label_ko": DECISION_ROBUST_LABEL_KO if self.robust else None,
        }


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


@dataclass
class _Index:
    by_doc: dict[uuid.UUID, dict[str, FieldInput]] = field(default_factory=dict)

    def sibling(self, document_id: uuid.UUID, name: str) -> FieldInput | None:
        return self.by_doc.get(document_id, {}).get(name)


def _valid_format(item: FieldInput, index: _Index, context: ProjectContext) -> str | None:
    """None when the value passes its format validator, else the reason."""
    value = item.value or ""
    name = item.field_name
    if name == "business_registration_number":
        if not (len(value) == 10 and is_valid_business_number(value)):
            return "FORMAT_BRN_CHECKSUM"
        if (
            item.facts is not None
            and business_number_type_plausible(value, item.facts.entity_type) is False
        ):
            return "BRN_TYPE_CODE_IMPLAUSIBLE"
        return None
    if name == "admission_date":
        try:
            admitted = date.fromisoformat(value)
        except ValueError:
            return "FORMAT_DATE_INVALID"
        if not (1990 <= admitted.year <= 2100) or (
            context.reference_date and admitted > context.reference_date
        ):
            return "FORMAT_ADMISSION_DATE_IMPLAUSIBLE"
        return None
    if name == "birth_date":
        try:
            born = date.fromisoformat(value)
        except ValueError:
            return "FORMAT_DATE_INVALID"
        today = context.reference_date or date.today()
        if not (MIN_STUDENT_AGE_YEARS <= (today - born).days / 365.25 <= MAX_STUDENT_AGE_YEARS):
            return "FORMAT_BIRTH_DATE_IMPLAUSIBLE"
        return None
    if name in ("issue_date", "valid_from", "valid_until"):
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            return "FORMAT_DATE_INVALID"
        if not (1990 <= parsed.year <= 2100):
            return "FORMAT_DATE_RANGE"
        if name == "issue_date" and context.reference_date and parsed > context.reference_date:
            return "FORMAT_ISSUE_DATE_AFTER_SUBMISSION"
        if name == "valid_until":
            issued = index.sibling(item.document_id, "issue_date")
            if issued and issued.value:
                try:
                    issue_date = date.fromisoformat(issued.value)
                except ValueError:
                    issue_date = None
                if issue_date is not None:
                    span = (parsed - issue_date).days
                    if span < 0:
                        return "FORMAT_VALIDITY_BEFORE_ISSUE"
                    if span > MAX_VALIDITY_SPAN_DAYS:
                        return "FORMAT_VALIDITY_TOO_LONG"
        if name in ("valid_from", "valid_until"):
            other_name = "valid_until" if name == "valid_from" else "valid_from"
            other = index.sibling(item.document_id, other_name)
            if other and other.value:
                try:
                    other_date = date.fromisoformat(other.value)
                except ValueError:
                    return "FORMAT_DATE_INVALID"
                start, end = (parsed, other_date) if name == "valid_from" else (other_date, parsed)
                if start > end:
                    return "FORMAT_VALIDITY_ORDER"
                if (end - start).days > MAX_VALIDITY_SPAN_DAYS:
                    return "FORMAT_VALIDITY_TOO_LONG"
        return None
    if name in ("gpa", "gpa_scale"):
        scale = index.sibling(item.document_id, "gpa_scale")
        score = index.sibling(item.document_id, "gpa")
        if not (scale and scale.value and score and score.value):
            return "FORMAT_GPA_PAIR_MISSING"
        if scale.value not in KNOWN_GPA_SCALES:
            return "FORMAT_GPA_SCALE_UNKNOWN"
        try:
            if float(score.value) > float(scale.value) or float(score.value) < 0:
                return "FORMAT_GPA_ABOVE_SCALE"
            # a cumulative GPA is an average of the semester GPAs, so it cannot lie outside them
            others = [v for v in score.peer_values if abs(v - float(score.value)) > 1e-6]
            if len(others) >= 2 and not (
                min(others) - 0.01 <= float(score.value) <= max(others) + 0.01
            ):
                return "FORMAT_GPA_OUTSIDE_SEMESTER_RANGE"
        except ValueError:
            return "FORMAT_GPA_INVALID"
        return None
    if name == "student_id":
        return None if STUDENT_ID_RE.match(value) else "FORMAT_STUDENT_ID"
    return None  # names / university: no format validator (corroboration only)


MIN_STUDENT_AGE_YEARS = 14
MAX_STUDENT_AGE_YEARS = 80


def _printed_bare_dates(item: FieldInput) -> tuple[date, ...]:
    """Bare dates printed elsewhere on the page (not the box that holds the value itself)."""
    if item.facts is None:
        return ()
    found = []
    for box in item.facts.dates:
        parsed = parse_iso(box.iso)
        if box.bare and parsed is not None and box.iso != item.value:
            found.append(parsed)
    return tuple(sorted(set(found)))


#: Marks a decision that rests on the certificate-number year (an inferred issue date was accepted).
YEAR_ANCHOR_SOURCE = "year_anchor"

#: Another bare date this close (in box heights) to the issue date shares its block.
ISSUANCE_BLOCK_BOXES = 4


def _anchored_issue_date_robust(item: FieldInput, index: _Index, context: ProjectContext) -> bool:
    """An inferred (unlabelled) issue date, decision-robust with the certificate number as year anchor.

    All must hold: the page prints exactly one document-number year and the date carries it; the date
    stands alone in its box and is the only date box of its block (no other bare date within a few
    box heights, so a birth or admission date nearby keeps it in review); it is not near the age
    limit; and every OCR digit-confusion reading with that year gives the same rule outcomes."""
    facts = item.facts
    if (
        item.field_name != "issue_date"
        or facts is None
        or len(facts.number_years) != 1
        or item.value is None
        or _near_decision_boundary(item, context)
    ):
        return False
    boxes = [box for box in facts.dates if box.iso == item.value and box.bare]
    if len(boxes) != 1:
        return False
    own = boxes[0]
    for other in facts.dates:
        if other is own or not other.bare or other.page != own.page:
            continue
        if abs(other.y - own.y) <= ISSUANCE_BLOCK_BOXES * max(own.height, other.height):
            return False
    return is_decision_robust(
        list(context.rules),
        context.reference_date,
        item.field_name,
        item.document_type,
        item.value,
        year_anchor=facts.number_years[0],
    )


def _decision_robust_item(item: FieldInput, index: _Index, context: ProjectContext) -> bool:
    """Every plausible misreading of the value (digit-confusion table) gives the same rule outcomes."""
    assert item.value is not None
    scale_item = index.sibling(item.document_id, "gpa_scale")
    siblings = {
        name: parse_iso(other.value)
        for name in ("issue_date", "valid_from", "valid_until")
        if (other := index.sibling(item.document_id, name)) is not None
    }
    return is_decision_robust(
        list(context.rules),
        context.reference_date,
        item.field_name,
        item.document_type,
        item.value,
        scale=float(scale_item.value) if scale_item and scale_item.value else None,
        siblings=siblings,
        window_dates=_printed_bare_dates(item),
    )


def _exact_legal_relation(verdict, item: FieldInput, features: Features) -> bool:  # type: ignore[no-untyped-def]
    """The end date equals the legal period after the issue date exactly (national tax certificate, 30 days,
    tolerance 0): another source, so no margin or misreading check is needed."""
    if not features.robust_end_dates or verdict.source != "date_pair":
        return False
    profile = VALIDITY_PROFILES.get(item.document_type)
    return (
        profile is not None
        and profile.tolerance_days == 0
        and item.field_name in ("valid_until", "valid_from", "issue_date")
    )


def _boundary_blocks(
    item: FieldInput,
    index: _Index,
    context: ProjectContext,
    features: Features,
    gpa_margin: float | None = None,
) -> bool:
    """A value that is only tolerance-confirmed (or confirmed by a re-read of the same image) must not sit where a
    misreading could flip the decision. Certificate end dates: decided by the digit-confusion check; everything
    else keeps the policy margin."""
    if features.robust_end_dates and item.field_name in ("valid_until", "valid_from"):
        if item.value is None or context.reference_date is None:
            return False
        return not _decision_robust_item(item, index, context)
    return _near_decision_boundary(item, context, gpa_margin)


def _near_decision_boundary(
    item: FieldInput, context: ProjectContext, gpa_margin: float | None = None
) -> bool:
    """True when `item` lies within the policy margin of a decision boundary of the workflow."""
    margin_days = BOUNDARY_MARGINS["date_days"]
    reference = context.reference_date
    if item.value is None:
        return False
    try:
        if item.field_name in ("valid_until", "valid_from") and reference is not None:
            return abs((date.fromisoformat(item.value) - reference).days) <= margin_days
        if item.field_name == "issue_date" and reference is not None and context.issue_max_age_days:
            limit = reference - timedelta(days=context.issue_max_age_days)
            return abs((date.fromisoformat(item.value) - limit).days) <= margin_days
        if item.field_name == "gpa" and context.gpa_threshold is not None:
            return abs(float(item.value) - context.gpa_threshold) <= (
                BOUNDARY_MARGINS["gpa"] if gpa_margin is None else gpa_margin
            )
    except ValueError:
        return False
    return False


ROBUST_FIELDS = frozenset({"gpa", "valid_from", "valid_until", "issue_date"})
INTERNAL_FIELDS = frozenset({"gpa", "gpa_scale", "issue_date", "valid_from", "valid_until"})


def _internal_verdict(  # type: ignore[no-untyped-def]
    item: FieldInput, index: _Index, context: ProjectContext, features: Features | None = None
):
    """Confirmation from the document's own content (D3-1..D3-3); None when no rule applies."""
    if item.field_name == "gpa":
        arithmetic = gpa_arithmetic(item.facts, float(item.value or 0))
        if arithmetic.state != "NONE" or features is None or not features.gpa_relation:
            return arithmetic
        return gpa_percent_relation(item.facts, float(item.value or 0))
    if item.field_name == "gpa_scale":
        return scale_confirmation(item.facts, item.value or "")

    def sibling(name: str):  # type: ignore[no-untyped-def]
        other = index.sibling(item.document_id, name)
        return parse_iso(other.value) if other is not None else None

    issue, start, end = sibling("issue_date"), sibling("valid_from"), sibling("valid_until")
    if item.field_name in ("valid_from", "valid_until", "issue_date"):
        pair = date_pair(item.document_type, issue, start, end)
        if pair.state != "NONE":
            return pair
        if item.field_name == "valid_until" and end is not None and issue is None:
            boxed = issue_date_box_for(item.document_type, item.facts, end)
            if boxed.state != "NONE":
                return boxed
    if item.field_name == "issue_date":
        return printed_twice(item.facts, item.value or "")
    return None


HAS_VALIDATOR = frozenset(
    {
        "business_registration_number",
        "issue_date",
        "valid_from",
        "valid_until",
        "gpa",
        "gpa_scale",
        "student_id",
        "birth_date",
        "admission_date",
    }
)


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------


def _no(strategy: Strategy, reason: str, rule_id: str | None = None) -> AutoDecision:
    return AutoDecision(False, strategy.value, rule_id=rule_id, reason=reason)


def decide(
    fields: Sequence[FieldInput],
    context: ProjectContext,
    strategy: Strategy,
) -> dict[tuple[uuid.UUID, str], AutoDecision]:
    """Decision for every OCR field of the project. Fields that are not OCR-read, have no
    value, were marked for review by the extractor, or have a human review are not decided."""
    features = STRATEGY_FEATURES[strategy]
    index = _Index()
    for item in fields:
        index.by_doc.setdefault(item.document_id, {})[item.field_name] = item
    decisions: dict[tuple[uuid.UUID, str], AutoDecision] = {}
    if strategy == Strategy.S0:
        return decisions

    for item in fields:
        if not item.ocr or item.value is None or item.has_current_review:
            continue
        key = (item.document_id, item.field_name)
        rule = FIELD_RULES.get(item.field_name)
        if rule is None:
            decisions[key] = _no(strategy, "NO_RULE_FOR_FIELD")
            continue
        semantic = bool(item.extraction_method and "semantic" in item.extraction_method)
        # An unlabelled issue date is an inference; only the document's own content may confirm it.
        internal_only = features.internal and semantic and item.field_name in INTERNAL_FIELDS
        if item.needs_review and not internal_only:
            decisions[key] = _no(strategy, "EXTRACTION_MARKED_FOR_REVIEW", rule.rule_id)
            continue
        if semantic and not internal_only:
            decisions[key] = _no(strategy, "SEMANTIC_INFERENCE", rule.rule_id)
            continue
        if (
            features.applicant_gpa
            and item.field_name in ("gpa", "gpa_scale")
            and (context.applicant_gpa if item.field_name == "gpa" else context.applicant_gpa_scale)
            and item.document_type == DocumentType.TRANSCRIPT
        ):
            decisions[key] = _decide_applicant_gpa(item, rule, index, context, strategy, features)
            continue
        if (item.confidence is None or item.confidence < rule.floor) and (
            features.applicant_name_confirm
            and rule.application
            and (typed_decision := _decide_applicant_name(item, rule, context, strategy))
        ):
            decisions[key] = typed_decision
            continue
        if item.confidence is None or item.confidence < rule.floor:
            if _below_floor_pair_allowed(item, features):
                decisions[key] = _decide_below_floor(
                    item, rule, fields, index, context, strategy, features
                )
            else:
                decisions[key] = _no(strategy, "CONFIDENCE_BELOW_FLOOR", rule.rule_id)
            continue

        # S1: confidence only (shown to be unsafe by the injection suite)
        if strategy == Strategy.S1:
            decisions[key] = AutoDecision(
                True, strategy.value, rule_id=f"{rule.rule_id}:CONFIDENCE"
            )
            continue

        if features.validators and item.field_name in HAS_VALIDATOR:
            problem = _valid_format(item, index, context)
            if problem:
                decision = _no(strategy, problem, rule.rule_id)
                if problem == "FORMAT_BRN_CHECKSUM" and features.internal:
                    proposal = propose_repair(
                        item.value,
                        is_valid_business_number,
                        (
                            other.value
                            for document_id, named in index.by_doc.items()
                            if document_id != item.document_id
                            for other in [named.get("business_registration_number")]
                            if other is not None and other.value
                        ),
                    )
                    if proposal is not None:
                        decision = replace(decision, repair_candidate=proposal.value)
                decisions[key] = decision
                continue

        if (
            features.business_pair
            and item.field_name == "business_registration_number"
            and item.document_type in BUSINESS_PAIR_TYPES
            and business_number_copy(item.facts, item.value, rule.floor).state == "CONFIRMED"
        ):
            decisions[key] = AutoDecision(
                True,
                strategy.value,
                rule_id=f"{rule.rule_id}:SECOND_COPY",
                sources=("second_copy",),
            )
            continue

        if features.internal and item.field_name in INTERNAL_FIELDS:
            verdict = _internal_verdict(item, index, context, features)
            if (
                verdict is not None
                and verdict.state == "CONFIRMED"
                and not _exact_legal_relation(verdict, item, features)
                and _boundary_blocks(
                    item,
                    index,
                    context,
                    features,
                    features.confirmed_gpa_margin
                    if verdict.source in ("arithmetic", "percent_relation")
                    else None,
                )
            ):
                # internal confirmations are tolerance-based (a one-day shift still fits a
                # profile), so they cannot pin a value that sits next to a decision boundary
                decisions[key] = _no(strategy, "NEAR_DECISION_BOUNDARY", rule.rule_id)
                continue
            if verdict is not None and verdict.state == "CONFIRMED":
                decisions[key] = AutoDecision(
                    True,
                    strategy.value,
                    rule_id=f"{rule.rule_id}:{verdict.source.upper()}",
                    sources=(verdict.source,),
                )
                continue
            if verdict is not None and verdict.state == "MISMATCH":
                decisions[key] = _no(strategy, f"{verdict.source.upper()}_MISMATCH", rule.rule_id)
                continue
            if internal_only:
                pair = _issue_date_pair(item, fields, index, context, features)
                if pair:
                    decisions[key] = _pair_decision(strategy, rule, pair)
                    continue
                if features.robust and _anchored_issue_date_robust(item, index, context):
                    decisions[key] = AutoDecision(
                        True,
                        strategy.value,
                        rule_id=f"{rule.rule_id}:DECISION_ROBUST",
                        sources=("decision_robust", YEAR_ANCHOR_SOURCE),
                        robust=True,
                    )
                    continue
                decisions[key] = _no(strategy, "SEMANTIC_INFERENCE", rule.rule_id)
                continue

        if not features.corroboration:
            # S2: confidence + format only, for the fields that have a validator
            if item.field_name in HAS_VALIDATOR:
                decisions[key] = AutoDecision(
                    True, strategy.value, rule_id=f"{rule.rule_id}:FORMAT"
                )
            else:
                decisions[key] = _no(strategy, "NO_FORMAT_VALIDATOR", rule.rule_id)
            continue

        decisions[key] = _decide_corroborated(
            item, rule, fields, index, context, strategy, features
        )
    if features.name_pair_robust:
        _name_pair_robust_pass(fields, decisions, strategy, features)
    if features.company_identity:
        _company_identity_pass(fields, decisions, strategy, features, index, context)
    return decisions


def _unreliable_partner(
    item: FieldInput, other: FieldInput, other_rule: FieldRule, features: Features
) -> bool:
    """Student pair: a read of the other student document below its confidence floor says nothing."""
    return (
        features.student_pair
        and item.document_type in STUDENT_PAIR_TYPES
        and other.document_type in STUDENT_PAIR_TYPES
        and (other.confidence is None or other.confidence < other_rule.floor)
    )


def _group_values(
    item: FieldInput,
    rule: FieldRule,
    fields: Sequence[FieldInput],
    index: _Index,
    context: ProjectContext,
    features: Features,
    *,
    reliable_partner_only: bool = False,
) -> tuple[list[FieldInput], list[FieldInput]]:
    """(agreeing, disagreeing) valid values of the same attribute on *other* documents."""
    assert rule.group is not None and item.value is not None
    tolerant = features.student_pair
    mine = canonical_key(rule.group, item.value, tolerant=tolerant)
    agreeing: list[FieldInput] = []
    disagreeing: list[FieldInput] = []
    for other in fields:
        other_rule = FIELD_RULES.get(other.field_name)
        if (
            other.document_id == item.document_id
            or other.checksum == item.checksum
            or other_rule is None
            or other_rule.group != rule.group
            or other.value is None
        ):
            continue
        if reliable_partner_only and (
            other.confidence is None or other.confidence < other_rule.floor
        ):
            continue  # a below-floor read is confirmed only by a reliable read of another document
        weak_partner = _unreliable_partner(item, other, other_rule, features)
        if weak_partner and not features.pair_below_floor:
            continue  # student pair: the other document counts only with a read above its floor
        if (
            other.field_name in HAS_VALIDATOR
            and features.validators
            and _valid_format(other, index, context)
        ):
            continue  # an unreadable/invalid value from another document is noise, not evidence
        theirs = canonical_key(rule.group, other.value, tolerant=tolerant)
        if weak_partner and (
            theirs != mine or item.confidence is None or item.confidence < rule.floor
        ):
            continue  # a below-floor partner supports a reliable read only by an exact match
        if theirs == mine or (
            rule.group == "company"
            and company_names_agree(
                mine, theirs, _business_number_of(item, index), _business_number_of(other, index)
            )
        ):
            agreeing.append(other)
        else:
            disagreeing.append(other)
    return agreeing, disagreeing


#: Student fields a below-floor read may be confirmed for, by an exact match with a reliable read of the other
#: student document.
BELOW_FLOOR_PAIR_FIELDS = frozenset(
    {"student_name", "university_name", "birth_date", "admission_date", "issue_date"}
)


#: Reasons for which a name stays open although nothing contradicts it; only these may be settled for the decision.
_NAME_OPEN_REASONS = frozenset({"CONFIDENCE_BELOW_FLOOR", "NO_INDEPENDENT_CONFIRMATION"})


def _name_pair_robust_pass(
    fields: Sequence[FieldInput],
    decisions: dict[tuple[uuid.UUID, str], AutoDecision],
    strategy: Strategy,
    features: Features,
) -> None:
    """Both student documents read the same name exactly (whatever the confidence) and the date of birth is
    accepted and equal on both: the same-person verdict is then decision-robust. The name value is not
    confirmed and is labelled so. A differing, missing or vetoed name, or a birth date that is not accepted on
    both documents, settles nothing."""
    names = [
        item
        for item in fields
        if item.field_name == "student_name"
        and item.document_type in STUDENT_PAIR_TYPES
        and item.ocr
        and item.value is not None
        and not item.has_current_review
    ]
    births = {
        item.document_id: item
        for item in fields
        if item.field_name == "birth_date" and item.document_type in STUDENT_PAIR_TYPES
    }
    for item in names:
        key = (item.document_id, "student_name")
        current = decisions.get(key)
        if current is None or current.accepted or current.reason not in _NAME_OPEN_REASONS:
            continue
        partners = [
            other
            for other in names
            if other.document_id != item.document_id
            and other.document_type != item.document_type
            and other.checksum != item.checksum
        ]
        if len(partners) != 1 or _squash(partners[0].value or "") != _squash(item.value or ""):
            continue
        partner = partners[0]
        mine, theirs = births.get(item.document_id), births.get(partner.document_id)
        if (
            mine is None
            or theirs is None
            or mine.value is None
            or mine.value != theirs.value
            or not _accepted(decisions, mine)
            or not _accepted(decisions, theirs)
        ):
            continue
        decisions[key] = AutoDecision(
            True,
            strategy.value,
            rule_id="PERSON:DECISION_ROBUST_PAIR",
            sources=("decision_robust", "pair_name"),
            corroborating_document_ids=(partner.document_id,),
            robust=True,
        )


#: Reasons for which a business name stays open without being contradicted by another document's name.
_COMPANY_OPEN_REASONS = frozenset(
    {"SECOND_PASS_CONTRADICTS_NAME", "CONFIDENCE_BELOW_FLOOR", "NO_INDEPENDENT_CONFIRMATION"}
)


def _company_identity_pass(
    fields: Sequence[FieldInput],
    decisions: dict[tuple[uuid.UUID, str], AutoDecision],
    strategy: Strategy,
    features: Features,
    index: _Index,
    context: ProjectContext,
) -> None:
    """The same company by its numbers: the business number is accepted (valid check digit, read on at least
    two documents) and equal on every business document that prints it. A company or workplace name of a
    document that prints that number, which agrees with every other name read and is open only because of
    the confidence floor, the second-pass veto or a missing second source, no longer blocks. A name that is
    readable and different from another document's stays in review, as does a document with no number or a
    different one. The name value is not confirmed and is labelled so."""
    numbers = [
        item
        for item in fields
        if item.field_name == "business_registration_number"
        and item.document_type in BUSINESS_PAIR_TYPES
        and item.value is not None
    ]
    digits = {canonical_key("business_number", item.value or "") for item in numbers}
    if (
        len(digits) != 1
        or len({item.document_id for item in numbers}) < 2
        or not is_valid_business_number(next(iter(digits)))
        or not all(_accepted(decisions, item) for item in numbers)
    ):
        return
    with_number = {item.document_id for item in numbers}
    for item in fields:
        key = (item.document_id, item.field_name)
        rule = FIELD_RULES.get(item.field_name)
        current = decisions.get(key)
        if (
            item.field_name not in ("company_name", "workplace_name")
            or rule is None
            or rule.group != "company"
            or item.document_type not in BUSINESS_PAIR_TYPES
            or item.document_id not in with_number
            or item.value is None
            or current is None
            or current.accepted
            or current.reason not in _COMPANY_OPEN_REASONS
        ):
            continue
        _, disagreeing = _group_values(
            item, rule, fields, index, context, features, reliable_partner_only=True
        )
        readable_different = [
            other
            for other in disagreeing
            if getattr(decisions.get((other.document_id, other.field_name)), "reason", None)
            != "SECOND_PASS_CONTRADICTS_NAME"
        ]
        if readable_different:
            continue  # a name read reliably and different from this one: a person decides, as now
        decisions[key] = AutoDecision(
            True,
            strategy.value,
            rule_id="COMPANY:IDENTITY_BY_NUMBERS",
            sources=("decision_robust", "identity_numbers"),
            corroborating_document_ids=tuple(
                sorted(
                    {
                        other.document_id
                        for other in numbers
                        if other.document_id != item.document_id
                    },
                    key=str,
                )
            ),
            robust=True,
        )


def _accepted(decisions: dict[tuple[uuid.UUID, str], AutoDecision], item: FieldInput) -> bool:
    decision = decisions.get((item.document_id, item.field_name))
    return bool(decision and decision.accepted)


def _same_number(left: str | None, right: str | None) -> bool:
    try:
        return left is not None and right is not None and abs(float(left) - float(right)) < 1e-9
    except ValueError:
        return False


def _decide_applicant_gpa(
    item: FieldInput,
    rule: FieldRule,
    index: _Index,
    context: ProjectContext,
    strategy: Strategy,
    features: Features,
) -> AutoDecision:
    """Route B: the GPA (or its scale) the applicant typed confirms the OCR read only by exact equality, whatever
    the read's confidence (two independent sources, one of them a person). Any difference, a typo as well as a
    misread, goes to a person. The value's format must still be valid."""
    assert item.value is not None
    if features.validators and item.field_name in HAS_VALIDATOR:
        problem = _valid_format(item, index, context)
        if problem:
            return _no(strategy, problem, rule.rule_id)
    typed = context.applicant_gpa if item.field_name == "gpa" else context.applicant_gpa_scale
    if typed is None:
        return _no(strategy, "NO_INDEPENDENT_CONFIRMATION", rule.rule_id)
    if not _same_number(item.value, typed):
        return _no(strategy, "CONFLICTS_WITH_APPLICANT_GPA", rule.rule_id)
    return AutoDecision(
        True,
        strategy.value,
        rule_id=f"{rule.rule_id}:APPLICANT_ENTERED",
        sources=("application",),
    )


def _below_floor_pair_allowed(item: FieldInput, features: Features) -> bool:
    if item.confidence is None:
        return False
    if features.business_pair and item.document_type in BUSINESS_PAIR_TYPES:
        return item.field_name in BUSINESS_BELOW_FLOOR_FIELDS
    return (
        features.pair_below_floor
        and item.document_type in STUDENT_PAIR_TYPES
        and item.field_name in BELOW_FLOOR_PAIR_FIELDS
    )


def _issue_date_pair(
    item: FieldInput,
    fields: Sequence[FieldInput],
    index: _Index,
    context: ProjectContext,
    features: Features,
) -> list[FieldInput]:
    """The same issue date on the other student document (both read above the floor, both of a valid
    format). Issued on different days, or any disagreeing reading: nothing is confirmed."""
    if (
        not features.student_pair
        or item.field_name != "issue_date"
        or item.document_type not in STUDENT_PAIR_TYPES
        or item.value is None
    ):
        return []
    floor = FIELD_RULES["issue_date"].floor
    equal: list[FieldInput] = []
    for other in fields:
        if (
            other.field_name != "issue_date"
            or other.document_id == item.document_id
            or other.checksum == item.checksum
            or other.document_type not in STUDENT_PAIR_TYPES
            or other.document_type == item.document_type
            or other.value is None
        ):
            continue
        if other.confidence is None or other.confidence < floor:
            # a below-floor partner supports a reliable read by an exact match only (variant b)
            if not (
                features.pair_below_floor
                and other.value == item.value
                and item.confidence is not None
                and item.confidence >= floor
            ):
                continue
        elif other.value != item.value:
            return []
        if features.validators and _valid_format(other, index, context):
            continue
        equal.append(other)
    return equal


def _pair_decision(strategy: Strategy, rule: FieldRule, partners: list[FieldInput]) -> AutoDecision:
    return AutoDecision(
        True,
        strategy.value,
        rule_id=f"{rule.rule_id}:CROSS_DOCUMENT",
        sources=("documents", CROSS_DOCUMENT_SOURCE),
        corroborating_document_ids=tuple(
            sorted({other.document_id for other in partners}, key=str)
        ),
    )


def _validity_end_by_legal_period(
    item: FieldInput, rule: FieldRule, index: _Index, strategy: Strategy
) -> AutoDecision:
    """A validity end read below the floor, confirmed by the certificate's own issue date (read above the floor
    on the same page, another box): the end falls exactly the legal period after the issue date. Only the
    national tax certificate has one (국세징수법 시행령 제96조: 30 days from issue; a shorter validity, to a payment
    deadline, is printed with its reason and is consistent but not confirmed). The 4대보험 완납증명서 has no
    legal period and the measured offsets on real certificates differ, so it is never confirmed this way.
    Shorter, longer or earlier: nothing is confirmed."""
    if item.document_type != DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE:
        return _no(strategy, "CONFIDENCE_BELOW_FLOOR", rule.rule_id)
    profile = VALIDITY_PROFILES.get(item.document_type)
    issue = index.sibling(item.document_id, "issue_date")
    if (
        profile is None
        or profile.until_after_issue_days is None
        or issue is None
        or issue.value is None
        or issue.confidence is None
        or issue.confidence < FIELD_RULES["issue_date"].floor
    ):
        return _no(strategy, "CONFIDENCE_BELOW_FLOOR", rule.rule_id)
    issued, end = parse_iso(issue.value), parse_iso(item.value or "")
    low, high = profile.until_after_issue_days
    if issued is None or end is None or not low <= (end - issued).days <= high:
        return _no(strategy, "CONFIDENCE_BELOW_FLOOR", rule.rule_id)
    return AutoDecision(
        True,
        strategy.value,
        rule_id=f"{rule.rule_id}:LEGAL_PERIOD_BELOW_FLOOR",
        sources=("date_pair",),
    )


def _decide_below_floor(
    item: FieldInput,
    rule: FieldRule,
    fields: Sequence[FieldInput],
    index: _Index,
    context: ProjectContext,
    strategy: Strategy,
    features: Features,
) -> AutoDecision:
    """A read below the floor is confirmed only by an exact match with a reliable read of the other student
    document; no other evidence (second pass, internal, decision-robust) can lift it."""
    assert item.value is not None
    if features.validators and item.field_name in HAS_VALIDATOR:
        problem = _valid_format(item, index, context)
        if problem:
            return _no(strategy, problem, rule.rule_id)
    if item.field_name == "issue_date":
        pair = _issue_date_pair(item, fields, index, context, features)
        return (
            _pair_decision(strategy, rule, pair)
            if pair
            else _no(strategy, "CONFIDENCE_BELOW_FLOOR", rule.rule_id)
        )
    if features.business_pair and item.document_type in BUSINESS_PAIR_TYPES:
        if item.field_name == "valid_until":
            return _validity_end_by_legal_period(item, rule, index, strategy)
        if item.field_name == "business_registration_number":
            copy = business_number_copy(
                item.facts, item.value, FIELD_RULES["business_registration_number"].floor
            )
            if copy.state == "CONFIRMED":
                return AutoDecision(
                    True,
                    strategy.value,
                    rule_id=f"{rule.rule_id}:SECOND_COPY_BELOW_FLOOR",
                    sources=("second_copy",),
                )
    return _decide_corroborated(
        item, rule, fields, index, context, strategy, features, below_floor=True
    )


NAME_MISREAD_MIN_SIMILARITY = 0.6


def _reads_like_a_misread(key: str, reading: str) -> bool:
    """The re-read contains a stretch of about the name's length that agrees with it at 60% of the positions or
    more without being the name: the shape of a misread (a character or two different). A fragment, or text of
    other words and digits, is no information about the name."""
    squashed = "".join(unicodedata.normalize("NFKC", reading).split())
    if not key or key in squashed:
        return False
    for width in {len(key) - 1, len(key), len(key) + 1}:
        if width < 2 or len(squashed) < width:
            continue
        for start in range(len(squashed) - width + 1):
            window = squashed[start : start + width]
            same = sum(a == b for a, b in zip(window, key, strict=False))
            if same / len(key) >= NAME_MISREAD_MIN_SIMILARITY:
                return True
    return False


def _letter_runs(text: str) -> list[str]:
    """Maximal runs of Hangul syllables or of Latin letters; digits, marks, jamo and a change of script end a run."""
    runs: list[str] = []
    current = ""
    current_kind = ""
    for ch in unicodedata.normalize("NFKC", text):
        kind = "H" if "\uac00" <= ch <= "\ud7a3" else "L" if ch.isascii() and ch.isalpha() else ""
        if kind and kind == current_kind:
            current += ch
            continue
        if len(current) >= 2:
            runs.append(current)
        current, current_kind = (ch, kind) if kind else ("", "")
    if len(current) >= 2:
        runs.append(current)
    return runs


_GARBLED_NOISE_RATIO = 0.25
_HARMLESS_MARKS = ":：.,-()·'"


def _noise_ratio(reading: str, hangul: bool) -> float:
    """Share of the re-read's characters that cannot belong to a name written in the key's script (a label word in
    Hangul around a Latin name is harmless)."""
    chars = [ch for ch in unicodedata.normalize("NFKC", reading) if not ch.isspace()]
    if not chars:
        return 1.0
    noise = 0
    for ch in chars:
        if "\uac00" <= ch <= "\ud7a3" or ch in _HARMLESS_MARKS:
            continue
        if ch.isascii() and ch.isalpha() and not hangul:
            continue
        noise += 1
    return noise / len(chars)


def _plausible_different_value(key: str, reading: str, *, company: bool = False) -> bool:
    """The re-read contains a run of letters that is itself a plausible, *different* value: about the name's length,
    no stuttered syllable that the name does not have, and neither a fragment of the name nor containing it. Label
    words and marks around it ("성명:") do not matter. A garbled string (repeated syllables, digits, symbols, jamo,
    mixed scripts) or a truncation says nothing against the first read."""
    if not key:
        return False
    if company:  # a legal form beside the name ("주식회사", "(주)") is not part of the name
        for marker in LEGAL_ENTITY_MARKERS:
            reading = reading.replace(marker, " ")
    key_doubled = {a for a, b in zip(key, key[1:], strict=False) if a == b}
    key_hangul = any("\uac00" <= ch <= "\ud7a3" for ch in key)
    if _noise_ratio(reading, key_hangul) > _GARBLED_NOISE_RATIO:
        return False  # digits, symbols, jamo and letters of another script all over it: garbled, not another name
    for run in _letter_runs(reading):
        if run in key or key in run:
            continue
        if ("\uac00" <= run[0] <= "\ud7a3") != key_hangul:
            continue  # another script is not another spelling of this name
        if abs(len(run) - len(key)) > 2:
            continue
        if {a for a, b in zip(run, run[1:], strict=False) if a == b} - key_doubled:
            continue
        return True
    return False


def _matched_exactly_elsewhere(
    item: FieldInput,
    rule: FieldRule,
    fields: Sequence[FieldInput],
    index: _Index,
    context: ProjectContext,
    features: Features,
    reference: str | None,
) -> bool:
    """The first read equals the other document's read (or the typed name) after normalisation, and nothing
    disagrees."""
    assert rule.group is not None and item.value is not None
    agreeing, disagreeing = _group_values(item, rule, fields, index, context, features)
    if disagreeing:
        return False
    if agreeing:
        return True
    if reference is None:
        return False
    if rule.group == "company":
        return typed_name_matches(reference, company_aliases(item.value))
    return canonical_key(rule.group, reference) == canonical_key(rule.group, item.value)


def _decide_applicant_name(
    item: FieldInput, rule: FieldRule, context: ProjectContext, strategy: Strategy
) -> AutoDecision | None:
    """The typed name equals a below-floor read exactly: accepted like route B (two independent sources). A
    reliable read is never overridden: this only runs for a read below the floor, and a plausible different re-read
    of the same image still stops it."""
    typed = context.company_name if rule.application == "company_name" else context.applicant_name
    if not typed or item.value is None or not rule.group:
        return None
    if rule.group == "company":
        same = typed_name_matches(typed, company_aliases(item.value))
    else:
        same = canonical_key(rule.group, typed) == canonical_key(rule.group, item.value)
    if not same:
        return None
    second = item.second_pass
    if second is not None and second.normalized:
        key = canonical_key(rule.group, item.value)
        if key not in second.normalized and _plausible_different_value(
            key, second.normalized, company=rule.group == "company"
        ):
            return None
    return AutoDecision(
        True,
        strategy.value,
        rule_id=f"{rule.rule_id}:APPLICANT_ENTERED",
        sources=("application",),
    )


def _read_back_by_another_document(
    item: FieldInput,
    rule: FieldRule,
    fields: Sequence[FieldInput],
    index: _Index,
    context: ProjectContext,
    features: Features,
) -> bool:
    """A jumbled re-read lifts the veto only when another document carries the same value, no document
    disagrees, and that document's own re-read shows the name: two documents repeating one misread cannot
    clear each other."""
    assert rule.group is not None and item.value is not None
    agreeing, disagreeing = _group_values(item, rule, fields, index, context, features)
    if disagreeing:
        return False
    key = canonical_key(rule.group, item.value)
    return any(
        other.second_pass is not None
        and other.second_pass.normalized is not None
        and key in other.second_pass.normalized
        for other in agreeing
    )


def _decide_corroborated(
    item: FieldInput,
    rule: FieldRule,
    fields: Sequence[FieldInput],
    index: _Index,
    context: ProjectContext,
    strategy: Strategy,
    features: Features,
    *,
    below_floor: bool = False,
) -> AutoDecision:
    assert item.value is not None
    lifted_veto: str | None = None
    # ---- application value (independent source, S5+) ---------------------------------------
    reference = None
    if features.application and rule.application:
        reference = (
            context.company_name if rule.application == "company_name" else context.applicant_name
        )
    if reference and rule.group:
        if features.company_alias and rule.group == "company":
            if not typed_name_matches(reference, _company_alias_pool(item, fields, index)):
                return _no(strategy, "CONFLICTS_WITH_APPLICATION_VALUE", rule.rule_id)
        elif canonical_key(rule.group, reference) != canonical_key(rule.group, item.value):
            return _no(strategy, "CONFLICTS_WITH_APPLICATION_VALUE", rule.rule_id)

    # ---- second-pass veto (S6) ----------------------------------------------------------------
    second = item.second_pass
    # Two independent reads that produce the identical value are the evidence; the second read's
    # confidence is not used (crop-edge noise drags it down and it tells nothing extra).
    second_value = second.normalized if second else None
    if (
        features.second_pass_veto
        and rule.second_pass
        and second
        and second.normalized
        and second_value != item.value
    ):
        return _no(strategy, "SECOND_PASS_DISAGREES", rule.rule_id)

    if features.name_veto and rule.name_veto and rule.group and second and second.normalized:
        key = canonical_key(rule.group, item.value)
        if (
            key not in second.normalized
            and features.veto_exact_lift
            and not below_floor
            and not _plausible_different_value(
                key, second.normalized, company=rule.group == "company"
            )
            and _matched_exactly_elsewhere(item, rule, fields, index, context, features, reference)
        ):
            lifted_veto = second.normalized
            _LOG.info(
                "second-pass veto lifted: field=%s document=%s reread_length=%d",
                item.field_name,
                item.document_id,
                len(second.normalized),
            )
        elif key not in second.normalized and (
            not features.veto_lift
            or _reads_like_a_misread(key, second.normalized)
            or not _read_back_by_another_document(item, rule, fields, index, context, features)
        ):
            return replace(
                _no(strategy, "SECOND_PASS_CONTRADICTS_NAME", rule.rule_id),
                second_pass_value=second.normalized,
            )

    sources: list[str] = []
    corroborators: list[uuid.UUID] = []
    if below_floor:
        # only the other document can confirm a read below the floor
        agreeing, disagreeing = (
            _group_values(item, rule, fields, index, context, features, reliable_partner_only=True)
            if rule.group
            else ([], [])
        )
        if agreeing and not disagreeing:
            return AutoDecision(
                True,
                strategy.value,
                rule_id=f"{rule.rule_id}:DOCUMENTS_BELOW_FLOOR",
                sources=("documents",),
                corroborating_document_ids=tuple(
                    sorted({other.document_id for other in agreeing}, key=str)
                ),
            )
        return _no(strategy, "CONFIDENCE_BELOW_FLOOR", rule.rule_id)
    if rule.group:
        agreeing, disagreeing = _group_values(item, rule, fields, index, context, features)
        if reference:
            # The application's own value is an independent source: an exact match accepts the
            # value even if some other document disagrees (that document is what gets reviewed).
            sources.append("application")
            if agreeing and not disagreeing:
                sources.append("documents")
                corroborators = sorted({other.document_id for other in agreeing}, key=str)
        else:
            if disagreeing:
                return _no(strategy, "DISAGREES_WITH_OTHER_DOCUMENT", rule.rule_id)
            if agreeing:
                sources.append("documents")
                corroborators = sorted({other.document_id for other in agreeing}, key=str)
    if not sources:
        pair = _issue_date_pair(item, fields, index, context, features)
        if pair:
            return _pair_decision(strategy, rule, pair)
    if sources:
        return AutoDecision(
            True,
            strategy.value,
            rule_id=f"{rule.rule_id}:{'+'.join(s.upper() for s in sources)}",
            sources=tuple(sources),
            corroborating_document_ids=tuple(corroborators),
            lifted_veto=lifted_veto,
        )

    # ---- second-pass consensus, only where nothing else can confirm it (S4+)
    if (
        features.second_pass
        and rule.second_pass
        and second_value is not None
        and second_value == item.value
        and _boundary_blocks(item, index, context, features)
    ):
        return _no(strategy, "NEAR_DECISION_BOUNDARY", rule.rule_id)
    if (
        features.second_pass
        and rule.second_pass
        and rule.confirm_by_second_pass
        and second_value is not None
        and second_value == item.value
    ):
        return AutoDecision(
            True,
            strategy.value,
            rule_id=f"{rule.rule_id}:SECOND_PASS",
            sources=("second_pass",),
            second_pass_value=second_value,
        )
    if (
        features.robust
        and item.field_name in ROBUST_FIELDS
        and not item.needs_review
        and _decision_robust_item(item, index, context)
    ):
        return AutoDecision(
            True,
            strategy.value,
            rule_id=f"{rule.rule_id}:DECISION_ROBUST",
            sources=("decision_robust",),
            robust=True,
        )
    return _no(strategy, "NO_INDEPENDENT_CONFIRMATION", rule.rule_id)
