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

import re
import unicodedata
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import StrEnum
from typing import Any

from app.core.domain import DocumentType
from app.document_intelligence.confirmations import (
    business_number_type_plausible,
    date_pair,
    gpa_arithmetic,
    issue_date_box_for,
    parse_iso,
    printed_twice,
    scale_confirmation,
)
from app.document_intelligence.decision_robust import RuleSpec, is_decision_robust
from app.document_intelligence.internal_evidence import DocFacts
from app.document_intelligence.normalization.field_normalizer import (
    DATE_RE,
    canonicalize_numeric_text,
    is_valid_business_number,
    normalize_business_number,
    normalize_date,
    strip_legal_entity_markers,
)
from app.document_intelligence.ocr_confusions import CONFUSION_TABLE_VERSION

AUTO_ACCEPT_POLICY_VERSION = "auto-accept-v1"


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
}


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


def canonical_key(group: str, value: str) -> str:
    if group in ("business_number", "student_id"):
        return "".join(ch for ch in value if ch.isdigit())
    if group == "company":
        core = strip_legal_entity_markers(unicodedata.normalize("NFKC", value))
        return _squash(core)
    return _squash(value)


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
    if field_name in ("issue_date", "valid_from", "valid_until"):
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
            "confusion_table_version": CONFUSION_TABLE_VERSION if self.robust else None,
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


def _near_decision_boundary(item: FieldInput, context: ProjectContext) -> bool:
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
            return abs(float(item.value) - context.gpa_threshold) <= BOUNDARY_MARGINS["gpa"]
    except ValueError:
        return False
    return False


ROBUST_FIELDS = frozenset({"gpa", "valid_from", "valid_until", "issue_date"})
INTERNAL_FIELDS = frozenset({"gpa", "gpa_scale", "issue_date", "valid_from", "valid_until"})


def _internal_verdict(item: FieldInput, index: _Index, context: ProjectContext):  # type: ignore[no-untyped-def]
    """Confirmation from the document's own content (D3-1..D3-3); None when no rule applies."""
    if item.field_name == "gpa":
        return gpa_arithmetic(item.facts, float(item.value or 0))
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
        if item.confidence is None or item.confidence < rule.floor:
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
                decisions[key] = _no(strategy, problem, rule.rule_id)
                continue

        if features.internal and item.field_name in INTERNAL_FIELDS:
            verdict = _internal_verdict(item, index, context)
            if (
                verdict is not None
                and verdict.state == "CONFIRMED"
                and _near_decision_boundary(item, context)
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
    return decisions


def _group_values(
    item: FieldInput,
    rule: FieldRule,
    fields: Sequence[FieldInput],
    index: _Index,
    context: ProjectContext,
    features: Features,
) -> tuple[list[FieldInput], list[FieldInput]]:
    """(agreeing, disagreeing) valid values of the same attribute on *other* documents."""
    assert rule.group is not None and item.value is not None
    mine = canonical_key(rule.group, item.value)
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
        if (
            other.field_name in HAS_VALIDATOR
            and features.validators
            and _valid_format(other, index, context)
        ):
            continue  # an unreadable/invalid value from another document is noise, not evidence
        if canonical_key(rule.group, other.value) == mine:
            agreeing.append(other)
        else:
            disagreeing.append(other)
    return agreeing, disagreeing


def _decide_corroborated(
    item: FieldInput,
    rule: FieldRule,
    fields: Sequence[FieldInput],
    index: _Index,
    context: ProjectContext,
    strategy: Strategy,
    features: Features,
) -> AutoDecision:
    assert item.value is not None
    # ---- application value (independent source, S5+) ---------------------------------------
    reference = None
    if features.application and rule.application:
        reference = (
            context.company_name if rule.application == "company_name" else context.applicant_name
        )
    if reference and rule.group:
        if canonical_key(rule.group, reference) != canonical_key(rule.group, item.value):
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
        if canonical_key(rule.group, item.value) not in second.normalized:
            return _no(strategy, "SECOND_PASS_CONTRADICTS_NAME", rule.rule_id)

    sources: list[str] = []
    corroborators: list[uuid.UUID] = []
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
    if sources:
        return AutoDecision(
            True,
            strategy.value,
            rule_id=f"{rule.rule_id}:{'+'.join(s.upper() for s in sources)}",
            sources=tuple(sources),
            corroborating_document_ids=tuple(corroborators),
        )

    # ---- second-pass consensus, only where nothing else can confirm it (S4+)
    if (
        features.second_pass
        and rule.second_pass
        and second_value is not None
        and second_value == item.value
        and _near_decision_boundary(item, context)
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
    if features.robust and item.field_name in ROBUST_FIELDS and not item.needs_review:
        scale_item = index.sibling(item.document_id, "gpa_scale")
        siblings = {
            name: parse_iso(other.value)
            for name in ("issue_date", "valid_from", "valid_until")
            if (other := index.sibling(item.document_id, name)) is not None
        }
        if is_decision_robust(
            list(context.rules),
            context.reference_date,
            item.field_name,
            item.document_type,
            item.value,
            scale=float(scale_item.value) if scale_item and scale_item.value else None,
            siblings=siblings,
        ):
            return AutoDecision(
                True,
                strategy.value,
                rule_id=f"{rule.rule_id}:DECISION_ROBUST",
                sources=("decision_robust",),
                robust=True,
            )
    return _no(strategy, "NO_INDEPENDENT_CONFIRMATION", rule.rule_id)
