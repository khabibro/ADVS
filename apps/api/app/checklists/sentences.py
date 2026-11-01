"""One plain Korean sentence per rule, generated from the rule document (never typed by hand)."""

from __future__ import annotations

from typing import Any

from app.checklists.catalog import (
    MATCH_KINDS_KO,
    NORMALISE_KO,
    SEVERITIES_KO,
    document_label,
    field_label,
)
from app.document_intelligence.validation.submission import NORMALISE_DEFAULTS

_DIGITS_WITH_FINAL = "013678"  # 영 일 삼 육 칠 팔 end in a consonant


def josa(word: str, with_final: str, without_final: str) -> str:
    """Attach a particle pair (은/는, 이/가, 을/를, 과/와) by the last sound of ``word``."""
    for char in reversed(word):
        if "가" <= char <= "힣":
            return word + (with_final if (ord(char) - ord("가")) % 28 else without_final)
        if char.isdigit():
            return word + (with_final if char in _DIGITS_WITH_FINAL else without_final)
        if char.isalpha():
            return word + without_final
    return word + without_final


def _topic(word: str) -> str:
    return josa(word, "은", "는")


def _object(word: str) -> str:
    return josa(word, "을", "를")


def _subject(word: str) -> str:
    return josa(word, "이", "가")


def _severity(value: str) -> str:
    return SEVERITIES_KO[value]


def check_date_sentence(item: dict[str, Any]) -> str:
    policy = item.get("policy", "SUBMISSION_DATE")
    if policy == "FIXED":
        return (
            f"점검 기준일은 {item.get('fixed_date', '')}로 고정됩니다. 제출자는 바꿀 수 없습니다."
        )
    if policy == "STAFF_CHOICE":
        return "점검 기준일은 담당자가 정합니다. 정하기 전에는 제출한 날을 씁니다. 제출자는 바꿀 수 없습니다."
    return "점검 기준일은 제출한 날(서버 날짜)입니다. 제출자는 바꿀 수 없습니다."


def document_sentences(item: dict[str, Any]) -> list[dict[str, str]]:
    label = document_label(item["type"])
    out: list[dict[str, str]] = []
    if item["requirement"] == "REQUIRED":
        out.append(
            {
                "rule": "requirement",
                "text": f"{_topic(label)} 필수 서류입니다. 없으면 보완이 필요합니다.",
            }
        )
    else:
        out.append(
            {
                "rule": "requirement",
                "text": f"{_topic(label)} 선택 서류입니다. 올리지 않아도 제출할 수 있고, 올리면 점검에 포함합니다.",
            }
        )
    for name in item.get("extra_required_fields", []):
        out.append(
            {
                "rule": f"required:{name}",
                "text": f"{label}에서 {_object(field_label(name))} 반드시 읽을 수 있어야 합니다. 읽지 못하면 담당자가 확인합니다.",
            }
        )
    issue = item.get("issue_date")
    if issue:
        out.append(
            {
                "rule": "issue_date",
                "text": f"{_topic(label)} 점검 기준일 기준 {issue['max_age_days']}일 이내에 발급되어야 합니다"
                f"(당일 포함). 어기면 '{_severity(issue['severity'])}'입니다.",
            }
        )
    validity = item.get("validity")
    if validity:
        out.append(
            {
                "rule": "validity",
                "text": f"{label}의 유효기간 만료일이 점검 기준일보다 앞서면 '{_severity(validity['severity'])}'입니다.",
            }
        )
    return out


def comparison_label(item: dict[str, Any]) -> str:
    source, target = item["source"], item["target"]
    return (
        f"{document_label(source['document'])} {field_label(source['field'])}"
        f" = {document_label(target['document'])} {field_label(target['field'])}"
    )


def threshold_label(item: dict[str, Any]) -> str:
    return f"{document_label(item['document'])} {field_label(item['field'])}"


def comparison_sentence(item: dict[str, Any]) -> str:
    source, target = item["source"], item["target"]
    left = f"{document_label(source['document'])}의 {field_label(source['field'])}"
    right = f"{document_label(target['document'])}의 {field_label(target['field'])}"
    options = {**NORMALISE_DEFAULTS, **item.get("normalise", {})}
    names = {source["field"], target["field"]}
    applicable = ["spaces"] if item["match"] != "IDENTIFIER" else []
    if names & {"company_name", "workplace_name"}:
        applicable = ["legal_form", *applicable, "parenthesised_latin", "workplace_name"]
    ignored = [NORMALISE_KO[key] for key in applicable if options[key]]
    kind = MATCH_KINDS_KO[item["match"]].split(" (")[0]
    sentence = (
        f"{_topic(left)} {josa(right, '과', '와')} 같아야 합니다({kind} 비교)."
        f" 다르면 '{_severity(item['severity'])}'입니다."
    )
    if ignored:
        sentence += f" 비교할 때 무시하는 것: {', '.join(ignored)}."
    return sentence + " 한쪽 값이 불확실하면 오류가 아니라 담당자 확인입니다."


def threshold_sentence(item: dict[str, Any]) -> str:
    label = f"{document_label(item['document'])}의 {field_label(item['field'])}"
    word = {"GTE": "이상", "LTE": "이하", "EQ": "과(와) 같음"}[item["operator"]]
    scale = item.get("scale") or {}
    if scale.get("mode") == "PER_SCALE":
        parts = ", ".join(
            f"{key}점 만점 {value}{word if word != '과(와) 같음' else ''}"
            for key, value in sorted(
                scale.get("per_scale", {}).items(), key=lambda pair: -float(pair[0])
            )
        )
        return (
            f"{_topic(label)} 만점별로 {parts}이어야 합니다. 만점을 읽지 못했거나 목록에 없으면 담당자가 확인합니다."
            f" 못 미치면 '{_severity(item['severity'])}'입니다."
        )
    extra = " 만점 구분 없이 숫자만 비교합니다." if scale else ""
    return f"{_topic(label)} {item['value']} {word}이어야 합니다.{extra} 못 미치면 '{_severity(item['severity'])}'입니다."


def identity_sentence(item: dict[str, Any]) -> str:
    parts = []
    if item.get("applicant_name", True):
        parts.append("이름")
    if item.get("company_name", True):
        parts.append("회사명")
    if not parts:
        return "제출자가 입력한 이름·회사명은 서류와 비교하지 않습니다."
    return f"제출자가 입력한 {'과 '.join(parts) if len(parts) == 2 else parts[0]}{'이' if parts[-1] == '이름' else '이'} 서류와 같은지 확인합니다."


def describe(document: dict[str, Any]) -> dict[str, Any]:
    """Every rule of the document with its sentence, in the order the editor shows them."""
    return {
        "check_date": check_date_sentence(document.get("check_date", {})),
        "identity": identity_sentence(document.get("identity_match", {})),
        "documents": {
            item["type"]: document_sentences(item) for item in document.get("documents", [])
        },
        "comparisons": {
            item["id"]: comparison_sentence(item) for item in document.get("comparisons", [])
        },
        "thresholds": {
            item["id"]: threshold_sentence(item) for item in document.get("thresholds", [])
        },
    }
