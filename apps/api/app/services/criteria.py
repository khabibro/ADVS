"""Check criteria (점검 기준) of a workflow, in a form an administrator can edit.

The verification engine reads persisted `DocumentRequirement` / `ValidationRule` rows. Until now those
rows were written only by `scripts/seed.py`, so every criterion was effectively fixed in code. This module
converts the rows to a small editing model and back:

* required / optional per document                       -> DocumentRequirement.required
* issue-date age ("발급 후 N일 이내")                       -> ISSUE_DATE_MAX_AGE {max_age_days}
* validity check ("유효기간 종료일 >= 점검 기준일")           -> DATE_COMPARISON valid_until ON_OR_AFTER EVALUATION_DATE
* value conditions (e.g. 평점평균 >= 3.0, 발급일 <= 날짜)     -> NUMERIC_COMPARISON / DATE_COMPARISON with expected_value
* extra required fields                                  -> REQUIRED_FIELD {field}
* comparisons between documents ("비교 항목")               -> FIELD_COMPARISON EQUALS

Every save is validated by the verification engine's own configuration check before anything is written,
creates a new version with a full snapshot (who, when, why), and invalidates the stored results of the
projects that use the workflow, so a changed criterion can never silently keep an old READY.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.domain import (
    DOCUMENT_TYPE_DISPLAY_NAMES,
    REVIEWABLE_FIELDS,
    DocumentType,
    RuleOperator,
    RuleType,
    Severity,
    field_display_name,
    field_kind,
)
from app.document_intelligence.validation.submission import (
    RequirementSnapshot,
    RuleConfigurationError,
    SubmissionRule,
    SubmissionVerificationEngine,
)
from app.models.entities import (
    Checklist,
    ChecklistRevision,
    DocumentRequirement,
    Project,
    ValidationRule,
)
from app.services.requirements import DEFAULT_REQUIRED_FIELDS, required_fields
from app.services.verification import invalidate_submission_verification

EVALUATION_DATE = "EVALUATION_DATE"
DATE_OPERATORS = {RuleOperator.ON_OR_BEFORE.value, RuleOperator.ON_OR_AFTER.value}
NUMBER_OPERATORS = {
    RuleOperator.GREATER_THAN_OR_EQUAL.value,
    RuleOperator.LESS_THAN_OR_EQUAL.value,
    RuleOperator.EQUALS.value,
}
VALUE_TYPES = {"string", "identifier", "institution"}
MAX_AGE_LIMIT = 36500


class CriteriaError(ValueError):
    """A criteria change that cannot be saved; `field` points at the offending part of the form."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.field = field


@dataclass
class _ValueRule:
    field: str
    operator: str
    value: str


# --------------------------------------------------------------------------- catalog


def editable_document_types() -> list[DocumentType]:
    return [item for item in DocumentType if item != DocumentType.UNKNOWN]


def catalog() -> dict[str, Any]:
    """Document types and fields an administrator can choose from, with Korean names and value kinds."""
    return {
        "document_types": [
            {
                "document_type": item.value,
                "display_name": DOCUMENT_TYPE_DISPLAY_NAMES[item],
                "supports_issue_date": "issue_date" in REVIEWABLE_FIELDS[item],
                "supports_validity": "valid_until" in REVIEWABLE_FIELDS[item],
                "default_required_fields": list(DEFAULT_REQUIRED_FIELDS[item]),
                "fields": [
                    {
                        "name": name,
                        "display_name": field_display_name(name),
                        "kind": field_kind(name),
                    }
                    for name in REVIEWABLE_FIELDS[item]
                ],
            }
            for item in editable_document_types()
        ]
    }


# --------------------------------------------------------------------------- rows -> criteria


def _is_validity_rule(rule: ValidationRule) -> bool:
    params = rule.params or {}
    if rule.rule_type == RuleType.DATE_NOT_EXPIRED.value:
        return params.get("field", "valid_until") == "valid_until"
    return (
        rule.rule_type == RuleType.DATE_COMPARISON.value
        and params.get("field") == "valid_until"
        and params.get("operator") == RuleOperator.ON_OR_AFTER.value
        and params.get("comparison_source") == EVALUATION_DATE
        and params.get("expected_value") is None
    )


def criteria_from_checklist(checklist: Checklist) -> dict[str, Any]:
    """The editing model of a workflow's persisted requirements and rules."""
    documents: dict[str, dict[str, Any]] = {}
    for requirement in checklist.requirements:
        documents[requirement.document_type] = {
            "document_type": requirement.document_type,
            "required": bool(requirement.required),
            "issue_date_max_age_days": None,
            "check_validity": False,
            "value_rules": [],
            "required_fields": [],
        }
    comparisons: list[dict[str, Any]] = []
    for requirement in checklist.requirements:
        own = documents[requirement.document_type]
        for rule in requirement.rules:
            params = rule.params or {}
            if rule.rule_type == RuleType.ISSUE_DATE_MAX_AGE.value:
                own["issue_date_max_age_days"] = int(params.get("max_age_days", 90))
            elif _is_validity_rule(rule):
                target = documents.get(params.get("document_type", requirement.document_type), own)
                target["check_validity"] = True
            elif rule.rule_type in (
                RuleType.DATE_COMPARISON.value,
                RuleType.NUMERIC_COMPARISON.value,
            ):
                target = documents.get(params.get("document_type", requirement.document_type), own)
                target["value_rules"].append(
                    {
                        "field": params.get("field"),
                        "operator": params.get("operator"),
                        "value": str(params.get("expected_value")),
                    }
                )
            elif rule.rule_type == RuleType.FIELD_COMPARISON.value:
                comparisons.append(
                    {
                        "source_document_type": params.get("source_document_type"),
                        "source_field": params.get("source_field"),
                        "target_document_type": params.get("target_document_type"),
                        "target_field": params.get("target_field"),
                        "value_type": params.get("value_type", "string"),
                    }
                )
            elif rule.rule_type == RuleType.REQUIRED_FIELD.value and params.get("field"):
                own["required_fields"].append(params["field"])
    return {"documents": list(documents.values()), "comparisons": comparisons}


# --------------------------------------------------------------------------- criteria -> rows


def _check_documents(criteria: dict[str, Any]) -> list[dict[str, Any]]:
    documents = criteria.get("documents") or []
    if not documents:
        raise CriteriaError("제출 서류를 1개 이상 추가해 주세요.", "documents")
    seen: set[str] = set()
    for index, item in enumerate(documents):
        where = f"documents.{index}"
        try:
            document_type = DocumentType(item.get("document_type"))
        except ValueError as exc:
            raise CriteriaError("알 수 없는 서류 종류입니다.", where) from exc
        if document_type == DocumentType.UNKNOWN:
            raise CriteriaError("알 수 없는 서류 종류입니다.", where)
        if document_type.value in seen:
            raise CriteriaError(
                f"{DOCUMENT_TYPE_DISPLAY_NAMES[document_type]}이(가) 두 번 들어 있습니다.", where
            )
        seen.add(document_type.value)
        fields = REVIEWABLE_FIELDS[document_type]
        age = item.get("issue_date_max_age_days")
        if age is not None:
            if "issue_date" not in fields:
                raise CriteriaError(
                    "이 서류에는 발급일 기준을 설정할 수 없습니다.",
                    f"{where}.issue_date_max_age_days",
                )
            if type(age) is not int or not 1 <= age <= MAX_AGE_LIMIT:
                raise CriteriaError(
                    "발급일 기준은 1일부터 36500일 사이의 정수로 입력해 주세요.",
                    f"{where}.issue_date_max_age_days",
                )
        if item.get("check_validity") and "valid_until" not in fields:
            raise CriteriaError("이 서류에는 유효기간이 없습니다.", f"{where}.check_validity")
        for field_name in item.get("required_fields") or []:
            if field_name not in fields:
                raise CriteriaError("이 서류에 없는 항목입니다.", f"{where}.required_fields")
        for rule_index, rule in enumerate(item.get("value_rules") or []):
            rule_where = f"{where}.value_rules.{rule_index}"
            name = rule.get("field")
            if name not in fields:
                raise CriteriaError("이 서류에 없는 항목입니다.", rule_where)
            kind = field_kind(name)
            operator = rule.get("operator")
            value = str(rule.get("value", "")).strip()
            if kind == "date":
                if operator not in DATE_OPERATORS:
                    raise CriteriaError(
                        "날짜 항목에는 '이전' 또는 '이후'만 쓸 수 있습니다.", rule_where
                    )
                try:
                    date.fromisoformat(value)
                except ValueError as exc:
                    raise CriteriaError(
                        "날짜를 YYYY-MM-DD 형식으로 입력해 주세요.", rule_where
                    ) from exc
            elif kind == "number":
                if operator not in NUMBER_OPERATORS:
                    raise CriteriaError("숫자 항목의 비교 방식이 올바르지 않습니다.", rule_where)
                try:
                    number = Decimal(value)
                except InvalidOperation as exc:
                    raise CriteriaError("숫자를 입력해 주세요.", rule_where) from exc
                if not number.is_finite():
                    raise CriteriaError("숫자를 입력해 주세요.", rule_where)
            else:
                raise CriteriaError(
                    "날짜나 숫자 항목에만 값 조건을 설정할 수 있습니다.", rule_where
                )
    if not any(item.get("required") for item in documents):
        raise CriteriaError("필수 서류를 1개 이상 지정해 주세요.", "documents")
    return documents


def _check_comparisons(criteria: dict[str, Any], types: set[str]) -> list[dict[str, Any]]:
    comparisons = criteria.get("comparisons") or []
    seen: set[tuple[str, str, str, str]] = set()
    for index, item in enumerate(comparisons):
        where = f"comparisons.{index}"
        source, target = item.get("source_document_type"), item.get("target_document_type")
        if source not in types or target not in types:
            raise CriteriaError("비교하는 서류가 제출 서류 목록에 있어야 합니다.", where)
        source_field, target_field = item.get("source_field"), item.get("target_field")
        if (
            source_field not in REVIEWABLE_FIELDS[DocumentType(source)]
            or target_field not in REVIEWABLE_FIELDS[DocumentType(target)]
        ):
            raise CriteriaError("비교 항목을 선택해 주세요.", where)
        if source == target and source_field == target_field:
            raise CriteriaError("같은 서류의 같은 항목끼리는 비교할 수 없습니다.", where)
        if item.get("value_type", "string") not in VALUE_TYPES:
            raise CriteriaError("비교 방식이 올바르지 않습니다.", where)
        key = (source, source_field, target, target_field)
        if key in seen or (target, target_field, source, source_field) in seen:
            raise CriteriaError("같은 비교 항목이 두 번 들어 있습니다.", where)
        seen.add(key)
    return comparisons


def _build_requirements(criteria: dict[str, Any]) -> list[DocumentRequirement]:
    documents = _check_documents(criteria)
    types = {item["document_type"] for item in documents}
    comparisons = _check_comparisons(criteria, types)
    by_type: dict[str, DocumentRequirement] = {}
    ordered: list[DocumentRequirement] = []
    for item in documents:
        document_type = item["document_type"]
        requirement = DocumentRequirement(
            document_type=document_type, required=bool(item.get("required"))
        )
        rules: list[ValidationRule] = []
        if item.get("issue_date_max_age_days") is not None:
            rules.append(
                ValidationRule(
                    rule_type=RuleType.ISSUE_DATE_MAX_AGE.value,
                    severity=Severity.ERROR.value,
                    params={"max_age_days": int(item["issue_date_max_age_days"])},
                )
            )
        if item.get("check_validity"):
            rules.append(
                ValidationRule(
                    rule_type=RuleType.DATE_COMPARISON.value,
                    severity=Severity.ERROR.value,
                    params={
                        "document_type": document_type,
                        "field": "valid_until",
                        "operator": RuleOperator.ON_OR_AFTER.value,
                        "comparison_source": EVALUATION_DATE,
                    },
                )
            )
        for rule in item.get("value_rules") or []:
            kind = field_kind(rule["field"])
            rules.append(
                ValidationRule(
                    rule_type=(
                        RuleType.DATE_COMPARISON.value
                        if kind == "date"
                        else RuleType.NUMERIC_COMPARISON.value
                    ),
                    severity=Severity.ERROR.value,
                    params={
                        "document_type": document_type,
                        "field": rule["field"],
                        "operator": rule["operator"],
                        "expected_value": str(rule["value"]).strip(),
                    },
                )
            )
        for field_name in sorted(set(item.get("required_fields") or [])):
            rules.append(
                ValidationRule(
                    rule_type=RuleType.REQUIRED_FIELD.value,
                    severity=Severity.ERROR.value,
                    params={"field": field_name},
                )
            )
        requirement.rules = rules
        by_type[document_type] = requirement
        ordered.append(requirement)
    for item in comparisons:
        # A comparison belongs to the document that is checked against the other one (as in the seed).
        by_type[item["target_document_type"]].rules.append(
            ValidationRule(
                rule_type=RuleType.FIELD_COMPARISON.value,
                severity=Severity.ERROR.value,
                params={
                    "source_document_type": item["source_document_type"],
                    "source_field": item["source_field"],
                    "target_document_type": item["target_document_type"],
                    "target_field": item["target_field"],
                    "operator": RuleOperator.EQUALS.value,
                    "value_type": item.get("value_type", "string"),
                },
            )
        )
    _validate_with_engine(ordered)
    return ordered


def _validate_with_engine(requirements: list[DocumentRequirement]) -> None:
    """Run the verification engine's own configuration check on the unsaved rows."""
    snapshots = []
    for requirement in requirements:
        rules = []
        for row in requirement.rules:
            rule_type = RuleType(row.rule_type)
            params = dict(row.params or {})
            if rule_type == RuleType.ISSUE_DATE_MAX_AGE:
                params = {
                    **params,
                    "document_type": requirement.document_type,
                    "field": "issue_date",
                }
            if rule_type == RuleType.REQUIRED_FIELD:
                continue
            rules.append(
                SubmissionRule(
                    id=uuid.uuid4(),
                    rule_type=rule_type,
                    severity=Severity(row.severity),
                    params=params,
                )
            )
        try:
            fields = required_fields(requirement)
        except RuleConfigurationError as exc:
            raise CriteriaError(f"설정을 저장할 수 없습니다: {exc}") from exc
        snapshots.append(
            RequirementSnapshot(
                id=uuid.uuid4(),
                document_type=DocumentType(requirement.document_type),
                required=requirement.required,
                rules=tuple(rules),
                required_fields=fields,
            )
        )
    try:
        SubmissionVerificationEngine().validate_configuration(snapshots)
    except RuleConfigurationError as exc:
        raise CriteriaError(f"설정을 저장할 수 없습니다: {exc}") from exc


# --------------------------------------------------------------------------- persistence


def load_checklist(db: Session, checklist_id: uuid.UUID) -> Checklist | None:
    return db.scalar(
        select(Checklist)
        .options(selectinload(Checklist.requirements).selectinload(DocumentRequirement.rules))
        .where(Checklist.id == checklist_id)
        .execution_options(populate_existing=True)
    )


def project_count(db: Session, checklist_id: uuid.UUID) -> int:
    return int(
        db.scalar(select(func.count(Project.id)).where(Project.checklist_id == checklist_id)) or 0
    )


def snapshot_of(checklist: Checklist) -> dict[str, Any]:
    return {
        "name": checklist.name,
        "description": checklist.description,
        "criteria": criteria_from_checklist(checklist),
    }


def _record_revision(
    db: Session, checklist: Checklist, editor: str | None, note: str | None
) -> ChecklistRevision:
    revision = ChecklistRevision(
        checklist_id=checklist.id,
        version=checklist.version,
        editor_label=(editor or "").strip()[:120] or None,
        note=(note or "").strip() or None,
        snapshot=snapshot_of(checklist),
    )
    db.add(revision)
    return revision


def _has_revisions(db: Session, checklist_id: uuid.UUID) -> bool:
    return bool(
        db.scalar(
            select(func.count(ChecklistRevision.id)).where(
                ChecklistRevision.checklist_id == checklist_id
            )
        )
    )


def _invalidate_projects(db: Session, checklist_id: uuid.UUID) -> None:
    ids = db.scalars(select(Project.id).where(Project.checklist_id == checklist_id)).all()
    for project_id in sorted(ids, key=str):
        invalidate_submission_verification(db, project_id)


def save_criteria(
    db: Session,
    checklist: Checklist,
    criteria: dict[str, Any],
    *,
    editor: str | None = None,
    note: str | None = None,
    expected_version: int | None = None,
) -> Checklist:
    """Replace a workflow's criteria as a new version. Raises CriteriaError without writing anything."""
    if expected_version is not None and expected_version != checklist.version:
        raise CriteriaError(
            "다른 사람이 먼저 이 기준을 저장했습니다. 화면을 새로 고친 뒤 다시 수정해 주세요.",
            "version",
        )
    requirements = _build_requirements(criteria)
    if not _has_revisions(db, checklist.id):
        _record_revision(db, checklist, "시스템", "최초 기준 (변경 전 상태)")
    checklist.requirements.clear()
    db.flush()
    checklist.requirements.extend(requirements)
    checklist.version = (checklist.version or 1) + 1
    db.flush()
    _record_revision(db, checklist, editor, note)
    _invalidate_projects(db, checklist.id)
    db.commit()
    return load_checklist(db, checklist.id)  # type: ignore[return-value]


def update_details(
    db: Session,
    checklist: Checklist,
    *,
    name: str | None = None,
    description: str | None = None,
    is_active: bool | None = None,
) -> Checklist:
    if name is not None:
        cleaned = name.strip()
        if not cleaned:
            raise CriteriaError("업무 이름을 입력해 주세요.", "name")
        clash = db.scalar(
            select(Checklist.id).where(Checklist.name == cleaned, Checklist.id != checklist.id)
        )
        if clash is not None:
            raise CriteriaError("같은 이름의 업무가 이미 있습니다.", "name")
        checklist.name = cleaned[:200]
    if description is not None:
        checklist.description = description.strip() or None
    if is_active is not None:
        checklist.is_active = is_active
    db.commit()
    return load_checklist(db, checklist.id)  # type: ignore[return-value]


def create_workflow(
    db: Session,
    *,
    name: str,
    description: str | None,
    copy_from: Checklist | None,
    criteria: dict[str, Any] | None,
    editor: str | None,
) -> Checklist:
    cleaned = (name or "").strip()
    if not cleaned:
        raise CriteriaError("업무 이름을 입력해 주세요.", "name")
    if db.scalar(select(Checklist.id).where(Checklist.name == cleaned)) is not None:
        raise CriteriaError("같은 이름의 업무가 이미 있습니다.", "name")
    source = criteria_from_checklist(copy_from) if copy_from is not None else criteria
    if source is None:
        raise CriteriaError("제출 서류를 1개 이상 추가해 주세요.", "documents")
    requirements = _build_requirements(source)
    checklist = Checklist(
        name=cleaned[:200], description=(description or "").strip() or None, is_active=True
    )
    checklist.version = 1
    db.add(checklist)
    db.flush()
    checklist.requirements.extend(requirements)
    db.flush()
    note = (
        f"'{copy_from.name}' 기준을 복사해 새로 만듦" if copy_from is not None else "새 업무 생성"
    )
    _record_revision(db, checklist, editor, note)
    db.commit()
    return load_checklist(db, checklist.id)  # type: ignore[return-value]


def revisions(db: Session, checklist_id: uuid.UUID) -> list[ChecklistRevision]:
    return list(
        db.scalars(
            select(ChecklistRevision)
            .where(ChecklistRevision.checklist_id == checklist_id)
            .order_by(ChecklistRevision.version.desc())
        ).all()
    )


def restore_revision(
    db: Session, checklist: Checklist, version: int, *, editor: str | None = None
) -> Checklist:
    revision = db.scalar(
        select(ChecklistRevision).where(
            ChecklistRevision.checklist_id == checklist.id, ChecklistRevision.version == version
        )
    )
    if revision is None:
        raise CriteriaError("해당 버전을 찾을 수 없습니다.", "version")
    criteria = (revision.snapshot or {}).get("criteria") or {}
    return save_criteria(
        db, checklist, criteria, editor=editor, note=f"버전 {version}의 기준으로 되돌림"
    )


def requirement_hints(requirement: DocumentRequirement) -> list[str]:
    """Short Korean descriptions of a document's checks, shown to applicants before they upload."""
    hints: list[str] = []
    for rule in requirement.rules:
        params = rule.params or {}
        if rule.rule_type == RuleType.ISSUE_DATE_MAX_AGE.value:
            hints.append(f"발급일로부터 {int(params.get('max_age_days', 90))}일 이내")
        elif _is_validity_rule(rule):
            hints.append("유효기간이 남아 있어야 함")
        elif rule.rule_type == RuleType.NUMERIC_COMPARISON.value:
            symbol = {
                "GREATER_THAN_OR_EQUAL": "이상",
                "LESS_THAN_OR_EQUAL": "이하",
                "EQUALS": "과 같음",
            }.get(params.get("operator", ""), "")
            hints.append(
                f"{field_display_name(params.get('field', ''))} {params.get('expected_value')} {symbol}".strip()
            )
        elif rule.rule_type == RuleType.DATE_COMPARISON.value and params.get("expected_value"):
            word = "이전" if params.get("operator") == RuleOperator.ON_OR_BEFORE.value else "이후"
            hints.append(
                f"{field_display_name(params.get('field', ''))} {params.get('expected_value')} {word}"
            )
    return hints
