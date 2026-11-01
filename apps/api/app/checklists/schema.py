"""Rule document ``advs.checklist/1``: strict pydantic model plus the save-time rules.

The document is data only. Extraction, classification, the look-alike title table, the
reliability policy (an unreliable value is never a failure, always a review) and the
auto-acceptance policy stay code; the document shows two of them read-only.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.checklists.catalog import (
    GPA_SCALES,
    NUMERIC_FIELDS,
    SCALE_FIELD_OF,
    document_label,
    field_label,
)
from app.core.domain import REVIEWABLE_FIELDS, DocumentType

SCHEMA_ID = "advs.checklist/1"
MAX_AGE_DAYS = (1, 365)
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")

Severity = Literal["ERROR", "WARNING"]
SelectableDocument = Literal[
    "GRADUATION_CERTIFICATE",
    "CAREER_CERTIFICATE",
    "BUSINESS_REGISTRATION_CERTIFICATE",
    "SME_CONFIRMATION_CERTIFICATE",
    "NATIONAL_TAX_PAYMENT_CERTIFICATE",
    "SOCIAL_INSURANCE_PAYMENT_CERTIFICATE",
    "ENROLLMENT_CERTIFICATE",
    "TRANSCRIPT",
]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CheckDate(_Strict):
    policy: Literal["SUBMISSION_DATE", "FIXED", "STAFF_CHOICE"] = "SUBMISSION_DATE"
    fixed_date: date | None = None
    applicant_can_change: Literal[False] = False


class IdentityMatch(_Strict):
    """Whether the name / company the submitter typed is compared with the documents."""

    applicant_name: bool = True
    company_name: bool = True


class IssueDateRule(_Strict):
    field: Literal["issue_date"] = "issue_date"
    max_age_days: int
    severity: Severity = "ERROR"


class ValidityRule(_Strict):
    field: Literal["valid_until"] = "valid_until"
    mode: Literal["PRINTED_VALID_UNTIL"] = "PRINTED_VALID_UNTIL"
    severity: Severity = "ERROR"


class DocumentRule(_Strict):
    type: SelectableDocument
    requirement: Literal["REQUIRED", "OPTIONAL"]
    extra_required_fields: list[str] = Field(default_factory=list)
    issue_date: IssueDateRule | None = None
    validity: ValidityRule | None = None
    # Fixed by the system, shown read-only in the editor.
    duplicates: Literal["STANDARD"] = "STANDARD"
    lookalike: Literal["STANDARD"] = "STANDARD"


class FieldRef(_Strict):
    document: SelectableDocument
    field: str


class Normalise(_Strict):
    """Per-comparison switches; the defaults are the engine's behaviour before checklists existed."""

    legal_form: bool = True
    spaces: bool = True
    parenthesised_latin: bool = False

    def is_default(self) -> bool:
        return self == Normalise()


class Comparison(_Strict):
    id: str
    source: FieldRef
    target: FieldRef
    match: Literal["IDENTIFIER", "TEXT", "INSTITUTION"]
    severity: Severity = "ERROR"
    normalise: Normalise = Field(default_factory=Normalise)
    # Fixed: an error is raised only when both values are reliable; otherwise a person reviews.
    reliability: Literal["BOTH_RELIABLE_ELSE_REVIEW"] = "BOTH_RELIABLE_ELSE_REVIEW"


class ScaleSetting(_Strict):
    field: Literal["gpa_scale"] = "gpa_scale"
    mode: Literal["RAW", "PER_SCALE"] = "RAW"
    per_scale: dict[str, str] | None = None


class Threshold(_Strict):
    id: str
    document: SelectableDocument
    field: str
    operator: Literal["GTE", "LTE", "EQ"] = "GTE"
    value: str | None = None
    scale: ScaleSetting | None = None
    severity: Severity = "ERROR"


class ChecklistDocument(_Strict):
    schema_id: Literal["advs.checklist/1"] = Field(default="advs.checklist/1", alias="schema")
    key: str
    name_ko: str = Field(min_length=1, max_length=200)
    description_ko: str = Field(default="", max_length=2000)
    check_date: CheckDate = Field(default_factory=CheckDate)
    identity_match: IdentityMatch = Field(default_factory=IdentityMatch)
    documents: list[DocumentRule]
    comparisons: list[Comparison] = Field(default_factory=list)
    thresholds: list[Threshold] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    def to_json(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


class Problem(BaseModel):
    path: str
    code: str
    message_ko: str


def canonical_json(document: dict[str, Any]) -> str:
    return json.dumps(document, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def document_sha256(document: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(document).encode()).hexdigest()


_STRUCTURAL_MESSAGES = {
    "missing": "필수 항목이 비어 있습니다.",
    "extra_forbidden": "허용되지 않는 항목입니다.",
    "literal_error": "허용되지 않는 값입니다.",
    "enum": "허용되지 않는 값입니다.",
    "string_too_short": "비워 둘 수 없습니다.",
    "string_too_long": "너무 깁니다.",
}


def _path(location: tuple[Any, ...]) -> str:
    return ".".join(str(part) for part in location)


def parse_document(raw: object) -> tuple[ChecklistDocument | None, list[Problem]]:
    """Structure first; the semantic rules only run on a well-formed document."""
    try:
        document = ChecklistDocument.model_validate(raw)
    except ValidationError as exc:
        return None, [
            Problem(
                path=_path(error["loc"]),
                code=error["type"].upper(),
                message_ko=_STRUCTURAL_MESSAGES.get(error["type"], "값이 올바르지 않습니다."),
            )
            for error in exc.errors()
        ]
    return document, semantic_problems(document)


def _decimal(value: str | None) -> Decimal | None:
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        return None
    return result if result.is_finite() else None


def semantic_problems(document: ChecklistDocument) -> list[Problem]:
    problems: list[Problem] = []

    def add(path: str, code: str, message: str) -> None:
        problems.append(Problem(path=path, code=code, message_ko=message))

    if not SLUG_RE.fullmatch(document.key):
        add("key", "KEY_INVALID", "업무 식별자는 영문 소문자·숫자·하이픈만 쓸 수 있습니다.")
    types = [item.type for item in document.documents]
    for position, item in enumerate(document.documents):
        base = f"documents.{position}"
        if types.count(item.type) > 1:
            add(base, "DOCUMENT_DUPLICATED", f"{document_label(item.type)}가 두 번 들어 있습니다.")
        fields = REVIEWABLE_FIELDS[DocumentType(item.type)]
        for name in item.extra_required_fields:
            if name not in fields:
                add(
                    f"{base}.extra_required_fields",
                    "FIELD_UNKNOWN",
                    f"{document_label(item.type)}에 없는 항목입니다: {name}",
                )
        if item.issue_date is not None:
            low, high = MAX_AGE_DAYS
            if "issue_date" not in fields:
                add(f"{base}.issue_date", "FIELD_UNKNOWN", "이 서류에는 발급일 항목이 없습니다.")
            if not low <= item.issue_date.max_age_days <= high:
                add(
                    f"{base}.issue_date.max_age_days",
                    "MAX_AGE_RANGE",
                    f"발급일 기준은 {low}일 이상 {high}일 이하로 정해 주세요.",
                )
        if item.validity is not None and "valid_until" not in fields:
            add(f"{base}.validity", "FIELD_UNKNOWN", "이 서류에는 유효기간 항목이 없습니다.")

    comparison_ids: set[str] = set()
    for position, comparison in enumerate(document.comparisons):
        base = f"comparisons.{position}"
        if not SLUG_RE.fullmatch(comparison.id) or comparison.id in comparison_ids:
            add(f"{base}.id", "ID_INVALID", "비교 식별자가 올바르지 않거나 중복됩니다.")
        comparison_ids.add(comparison.id)
        for side, ref in (("source", comparison.source), ("target", comparison.target)):
            if ref.document not in types:
                add(f"{base}.{side}", "DOCUMENT_NOT_IN_CHECKLIST", "이 업무에 없는 서류입니다.")
            elif ref.field not in REVIEWABLE_FIELDS[DocumentType(ref.document)]:
                add(
                    f"{base}.{side}.field",
                    "FIELD_UNKNOWN",
                    f"{document_label(ref.document)}에 없는 항목입니다: {ref.field}",
                )
        if comparison.source == comparison.target:
            add(base, "COMPARISON_SELF", "같은 서류의 같은 항목끼리는 비교할 수 없습니다.")

    threshold_ids: set[str] = set()
    for position, threshold in enumerate(document.thresholds):
        base = f"thresholds.{position}"
        if not SLUG_RE.fullmatch(threshold.id) or threshold.id in threshold_ids:
            add(f"{base}.id", "ID_INVALID", "기준값 식별자가 올바르지 않거나 중복됩니다.")
        threshold_ids.add(threshold.id)
        if threshold.document not in types:
            add(f"{base}.document", "DOCUMENT_NOT_IN_CHECKLIST", "이 업무에 없는 서류입니다.")
            continue
        if threshold.field not in REVIEWABLE_FIELDS[DocumentType(threshold.document)]:
            add(f"{base}.field", "FIELD_UNKNOWN", f"없는 항목입니다: {threshold.field}")
            continue
        if threshold.field not in NUMERIC_FIELDS:
            add(f"{base}.field", "FIELD_NOT_NUMERIC", "숫자로 비교할 수 없는 항목입니다.")
            continue
        scale_field = SCALE_FIELD_OF.get(threshold.field)
        scale = threshold.scale
        if scale_field is not None and scale is None:
            add(f"{base}.scale", "SCALE_REQUIRED", "평점은 만점 기준 방식을 정해야 합니다.")
        if scale is None or scale.mode == "RAW":
            if _decimal(threshold.value) is None:
                add(f"{base}.value", "VALUE_INVALID", "기준값은 숫자여야 합니다.")
            if scale is not None and scale.per_scale:
                add(
                    f"{base}.scale.per_scale",
                    "PER_SCALE_UNUSED",
                    "척도 구분 없음에서는 쓰지 않습니다.",
                )
        else:
            if threshold.value is not None:
                add(
                    f"{base}.value",
                    "VALUE_UNUSED",
                    "척도별 기준에서는 단일 기준값을 쓰지 않습니다.",
                )
            values = scale.per_scale or {}
            if not values:
                add(
                    f"{base}.scale.per_scale",
                    "PER_SCALE_REQUIRED",
                    "만점별 기준값을 입력해 주세요.",
                )
            for key, limit in values.items():
                if key not in GPA_SCALES:
                    add(
                        f"{base}.scale.per_scale.{key}",
                        "SCALE_UNKNOWN",
                        f"지원하지 않는 만점입니다: {key} (4.5 / 4.3 / 4)",
                    )
                value = _decimal(limit)
                if value is None or value < 0 or value > Decimal(key if _decimal(key) else "10"):
                    add(
                        f"{base}.scale.per_scale.{key}",
                        "VALUE_INVALID",
                        "기준값은 0 이상, 해당 만점 이하의 숫자여야 합니다.",
                    )

    policy = document.check_date
    if policy.policy == "FIXED" and policy.fixed_date is None:
        add("check_date.fixed_date", "FIXED_DATE_REQUIRED", "고정 날짜를 입력해 주세요.")
    if policy.policy != "FIXED" and policy.fixed_date is not None:
        add(
            "check_date.fixed_date",
            "FIXED_DATE_UNUSED",
            "고정 날짜는 '고정 날짜'를 고른 경우에만 씁니다.",
        )
    return problems


def describe_field(document_type: str, field: str) -> str:
    return f"{document_label(document_type)}의 {field_label(field)}"
