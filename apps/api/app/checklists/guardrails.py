"""Warnings shown while editing. ``ACK`` ones must be acknowledged before the version is published.

None of these block a legitimate choice; they make a loosening of the checks visible and logged.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from pydantic import BaseModel

from app.checklists.catalog import GPA_SCALES, document_label, field_label
from app.core.domain import DocumentType
from app.services.requirements import DEFAULT_REQUIRED_FIELDS

LONG_AGE_DAYS = 180
STALE_FIXED_DATE_DAYS = 30


class Warning_(BaseModel):
    key: str
    level: Literal["INFO", "WARN", "ACK"]
    path: str
    message_ko: str


def _decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _index(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {item[key]: item for item in items}


def guardrails(
    document: dict[str, Any], base: dict[str, Any] | None, today: date | None = None
) -> list[Warning_]:
    """Warnings for ``document``; ``base`` is the published document it would replace (if any)."""
    today = today or date.today()
    out: list[Warning_] = []

    def add(code: str, level: str, path: str, message: str) -> None:
        out.append(Warning_(key=f"{code}:{path}", level=level, path=path, message_ko=message))  # type: ignore[arg-type]

    documents = document.get("documents", [])
    if documents and not any(item["requirement"] == "REQUIRED" for item in documents):
        add(
            "NO_REQUIRED_DOCUMENT",
            "ACK",
            "documents",
            "필수 서류가 하나도 없습니다. 아무 서류도 올리지 않아도 점검을 통과할 수 있습니다.",
        )
    for position, item in enumerate(documents):
        label = document_label(item["type"])
        path = f"documents.{position}"
        issue = item.get("issue_date")
        if issue and issue["max_age_days"] > LONG_AGE_DAYS:
            add(
                "LONG_ISSUE_AGE",
                "WARN",
                f"{path}.issue_date",
                f"{label}의 발급일 기준이 {issue['max_age_days']}일로 깁니다. 오래된 서류도 통과합니다.",
            )
        if issue and issue["severity"] == "WARNING":
            add(
                "SOFT_ISSUE_AGE",
                "INFO",
                f"{path}.issue_date",
                f"{label}의 발급일 초과는 '확인 필요'로만 표시되어 제출 가능 여부를 막지 않을 수 있습니다.",
            )
        if item.get("validity") is None and item["requirement"] == "REQUIRED":
            if "valid_until" in DEFAULT_REQUIRED_FIELDS[DocumentType(item["type"])]:
                add(
                    "VALIDITY_ALWAYS_ON",
                    "INFO",
                    f"{path}.validity",
                    f"{label}는 유효기간 확인을 끌 수 없습니다. 만료된 서류는 항상 보완 필요로 처리됩니다.",
                )
    for position, item in enumerate(document.get("comparisons", [])):
        if item["severity"] == "WARNING":
            add(
                "SOFT_COMPARISON",
                "INFO",
                f"comparisons.{position}",
                "이 비교가 맞지 않아도 '확인 필요'로만 표시됩니다.",
            )
    policy = document.get("check_date", {})
    if policy.get("policy") == "FIXED" and policy.get("fixed_date"):
        fixed = date.fromisoformat(str(policy["fixed_date"]))
        if fixed < today - timedelta(days=STALE_FIXED_DATE_DAYS):
            add(
                "STALE_FIXED_DATE",
                "ACK",
                "check_date",
                f"고정 점검 기준일({fixed.isoformat()})이 {STALE_FIXED_DATE_DAYS}일 넘게 지났습니다. "
                "오래전 날짜로 점검하면 만료된 서류도 통과할 수 있습니다.",
            )
    if base is not None:
        out.extend(_loosening(document, base))
    return out


def _loosening(document: dict[str, Any], base: dict[str, Any]) -> list[Warning_]:
    out: list[Warning_] = []

    def add(code: str, path: str, message: str) -> None:
        out.append(Warning_(key=f"{code}:{path}", level="ACK", path=path, message_ko=message))

    old_docs, new_docs = (
        _index(base.get("documents", []), "type"),
        _index(document.get("documents", []), "type"),
    )
    for kind, old in old_docs.items():
        new = new_docs.get(kind)
        label = document_label(kind)
        if new is None:
            add("DOCUMENT_REMOVED", f"documents.{kind}", f"{label}를 점검 대상에서 뺐습니다.")
            continue
        if old["requirement"] == "REQUIRED" and new["requirement"] == "OPTIONAL":
            add(
                "REQUIRED_TO_OPTIONAL",
                f"documents.{kind}",
                f"{label}가 필수에서 선택으로 바뀌었습니다.",
            )
        old_issue, new_issue = old.get("issue_date"), new.get("issue_date")
        if old_issue and not new_issue:
            add(
                "ISSUE_AGE_REMOVED",
                f"documents.{kind}.issue_date",
                f"{label}의 발급일 기준을 없앴습니다.",
            )
        elif old_issue and new_issue:
            if new_issue["max_age_days"] > old_issue["max_age_days"]:
                add(
                    "ISSUE_AGE_RAISED",
                    f"documents.{kind}.issue_date",
                    f"{label}의 발급일 기준을 {old_issue['max_age_days']}일에서 {new_issue['max_age_days']}일로 늘렸습니다.",
                )
            if old_issue["severity"] == "ERROR" and new_issue["severity"] == "WARNING":
                add(
                    "ISSUE_AGE_SOFTENED",
                    f"documents.{kind}.issue_date",
                    f"{label}의 발급일 위반을 보완 필요에서 확인 필요로 낮췄습니다.",
                )
        if old.get("validity") and not new.get("validity"):
            add(
                "VALIDITY_REMOVED",
                f"documents.{kind}.validity",
                f"{label}의 유효기간 확인을 껐습니다.",
            )
        for name in set(old.get("extra_required_fields", [])) - set(
            new.get("extra_required_fields", [])
        ):
            add(
                "REQUIRED_FIELD_REMOVED",
                f"documents.{kind}.extra_required_fields.{name}",
                f"{label}의 필수 항목 '{field_label(name)}'을(를) 뺐습니다.",
            )
    old_cmp, new_cmp = (
        _index(base.get("comparisons", []), "id"),
        _index(document.get("comparisons", []), "id"),
    )
    for slug, old in old_cmp.items():
        new = new_cmp.get(slug)
        left = f"{document_label(old['source']['document'])} {field_label(old['source']['field'])}"
        right = f"{document_label(old['target']['document'])} {field_label(old['target']['field'])}"
        if new is None:
            add(
                "COMPARISON_REMOVED",
                f"comparisons.{slug}",
                f"서류 간 비교를 뺐습니다: {left} = {right}. 다른 사람의 서류가 섞여도 발견하지 못할 수 있습니다.",
            )
        elif old["severity"] == "ERROR" and new["severity"] == "WARNING":
            add(
                "COMPARISON_SOFTENED",
                f"comparisons.{slug}",
                f"비교 위반을 보완 필요에서 확인 필요로 낮췄습니다: {left} = {right}.",
            )
    old_thr, new_thr = (
        _index(base.get("thresholds", []), "id"),
        _index(document.get("thresholds", []), "id"),
    )
    for slug, old in old_thr.items():
        new = new_thr.get(slug)
        if new is None:
            add("THRESHOLD_REMOVED", f"thresholds.{slug}", "기준값을 없앴습니다.")
        elif _threshold_looser(old, new):
            add(
                "THRESHOLD_LOWERED",
                f"thresholds.{slug}",
                f"{document_label(old['document'])}의 {field_label(old['field'])} 기준을 완화했습니다.",
            )
    if document.get("identity_match") != base.get("identity_match"):
        old_i, new_i = base.get("identity_match", {}), document.get("identity_match", {})
        if any(
            old_i.get(k, True) and not new_i.get(k, True)
            for k in ("applicant_name", "company_name")
        ):
            add(
                "IDENTITY_MATCH_OFF",
                "identity_match",
                "제출자가 입력한 이름 또는 회사명을 서류와 비교하지 않도록 바꿨습니다.",
            )
    return out


def _threshold_looser(old: dict[str, Any], new: dict[str, Any]) -> bool:
    """Looser means a lower minimum (GTE) or a higher maximum (LTE), compared per GPA scale."""
    if old["operator"] != new["operator"]:
        return True
    sign = 1 if old["operator"] == "GTE" else -1
    new_values = _values(new)
    # a scale the new rule no longer lists goes to a person, so it is not a loosening
    return any(
        sign * (new_values[key] - old_value) < 0
        for key, old_value in _values(old).items()
        if key in new_values
    )


def _values(threshold: dict[str, Any]) -> dict[str, Decimal]:
    """The limit per GPA scale ("*" for a field without scales). A single value applies to all."""
    scale = threshold.get("scale") or {}
    if scale.get("mode") == "PER_SCALE":
        return {
            k: d
            for k, v in (scale.get("per_scale") or {}).items()
            if (d := _decimal(v)) is not None
        }
    value = _decimal(threshold.get("value"))
    if value is None:
        return {}
    return {s: value for s in GPA_SCALES} if threshold.get("field") == "gpa" else {"*": value}
