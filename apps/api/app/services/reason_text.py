"""Plain-Korean reasons for items that wait for a person: which field of which document, why, and what to do.

The code is the machine reason (auto-acceptance reason or evidence-assessment reason); the explanation says what is
wrong, the action says what the applicant can do. Staff see the code next to the explanation."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.domain import DOCUMENT_TYPE_DISPLAY_NAMES, DocumentType, field_display_name


@dataclass(frozen=True)
class ReasonText:
    code: str
    explanation: str
    action: str


_REVIEW = "직원이 서류 원본으로 확인합니다."

# code -> (explanation template, action). {doc} = document name, {field} = field name.
_TEMPLATES: dict[str, tuple[str, str]] = {
    "CONFLICTS_WITH_APPLICATION_VALUE": (
        "입력하신 {field}{i} {doc}에 인쇄된 값과 다릅니다.",
        "서류에 인쇄된 값 그대로 다시 입력해 주세요. 맞게 입력했다면 " + _REVIEW,
    ),
    "CONFLICTS_WITH_APPLICANT_GPA": (
        "입력하신 평점이 {doc}에서 읽은 평점과 다릅니다.",
        "성적증명서에 인쇄된 평점을 다시 확인해 입력해 주세요. 맞게 입력했다면 " + _REVIEW,
    ),
    "SECOND_PASS_CONTRADICTS_NAME": (
        "{doc}의 {field}{eul} 한 번 더 읽은 결과가 첫 번째 결과와 달라 자동으로 확정하지 못했습니다.",
        _REVIEW + " 더 선명한 사진이나 스캔을 올리면 자동으로 확인될 수 있습니다.",
    ),
    "NEAR_DECISION_BOUNDARY": (
        "{doc}의 {field}{eun} 한 글자만 잘못 읽혀도 판정이 달라질 수 있어 자동으로 확정하지 못했습니다.",
        "직원이 날짜를 서류 원본으로 확인합니다.",
    ),
    "NO_INDEPENDENT_CONFIRMATION": (
        "{doc}의 {field}{eul} 확인해 줄 다른 서류나 입력값이 없어 자동으로 확정하지 못했습니다.",
        _REVIEW,
    ),
    "CONFIDENCE_BELOW_FLOOR": (
        "{doc}의 {field}{eul} 선명하게 읽지 못했습니다(인식 신뢰도 부족).",
        "더 선명한 파일을 올리거나 " + _REVIEW,
    ),
    "OCR_CONFIDENCE_BELOW_POLICY": (
        "{doc}의 {field}{eul} 선명하게 읽지 못했습니다(인식 신뢰도 부족).",
        "더 선명한 파일을 올리거나 " + _REVIEW,
    ),
    "DISAGREES_WITH_OTHER_DOCUMENT": (
        "{doc}의 {field}{i} 함께 제출한 다른 서류의 값과 다릅니다.",
        "어느 서류가 맞는지 확인하고 잘못된 서류를 다시 올려 주세요.",
    ),
    "FIELD_MISSING": (
        "{doc}에서 {field}{eul} 찾지 못했습니다.",
        "서류 전체가 잘 보이도록 다시 촬영하거나 스캔해 올려 주세요.",
    ),
    "EXTRACTION_MARKED_FOR_REVIEW": (
        "{doc}의 {field}{eun} 문장에서 추정한 값이라 자동으로 확정하지 못했습니다.",
        _REVIEW,
    ),
    "SEMANTIC_INFERENCE": (
        "{doc}의 {field}{eun} 문장에서 추정한 값이라 자동으로 확정하지 못했습니다.",
        _REVIEW,
    ),
    "OCR_REQUIRES_CONFIRMATION": (
        "{doc}의 {field}{eun} 글자 인식 결과라 다른 근거로 확인되지 않았습니다.",
        _REVIEW,
    ),
    "EVIDENCE_MISSING": ("{doc}의 {field}의 근거 위치를 찾지 못했습니다.", _REVIEW),
    "REQUIRED_FIELD_UNRESOLVED": (
        "{doc}의 {field}{eun} 필수 항목인데 읽지 못했습니다.",
        "서류 전체가 잘 보이도록 다시 올리거나 " + _REVIEW,
    ),
    "COMPANY_NAME_INPUT_NOT_FOUND": (
        "입력하신 회사명이 서류에 인쇄된 상호와 일치하지 않습니다.",
        "서류에 인쇄된 상호(한글 또는 괄호 안 영문)로 다시 입력해 주세요.",
    ),
}
_FORMAT_PREFIX = "FORMAT_"


def _josa(word: str, with_final: str, without_final: str) -> str:
    """The particle that follows `word` (은/는, 이/가, 을/를): 받침 decides."""
    last = word.rstrip()[-1:] if word.strip() else ""
    if last and "\uac00" <= last <= "\ud7a3":
        return with_final if (ord(last) - 0xAC00) % 28 else without_final
    return without_final


def explain(
    code: str | None, document_type: DocumentType | str | None, field_name: str | None
) -> ReasonText | None:
    if not code:
        return None
    doc = ""
    if document_type is not None:
        try:
            doc = DOCUMENT_TYPE_DISPLAY_NAMES[DocumentType(document_type)]
        except (KeyError, ValueError):
            doc = "서류"
    field = field_display_name(field_name) if field_name else "항목"
    if code in _TEMPLATES:
        template, action = _TEMPLATES[code]
    elif code.startswith(_FORMAT_PREFIX):
        template = "{doc}의 {field}{i} 올바른 형식이 아니라 자동으로 확정하지 못했습니다."
        action = _REVIEW
    else:
        template = "{doc}의 {field}{eul} 자동으로 확정하지 못했습니다."
        action = _REVIEW
    return ReasonText(
        code,
        template.format(
            doc=doc or "서류",
            field=field,
            eun=_josa(field, "은", "는"),
            i=_josa(field, "이", "가"),
            eul=_josa(field, "을", "를"),
        ),
        action,
    )


#: Assessment reasons in the order a person would care about them.
_ASSESSMENT_PRIORITY = (
    "FIELD_MISSING",
    "OCR_CONFIDENCE_BELOW_POLICY",
    "EXTRACTION_MARKED_FOR_REVIEW",
    "SEMANTIC_INFERENCE",
    "EVIDENCE_MISSING",
    "OCR_REQUIRES_CONFIRMATION",
)


def pick_reason(
    auto_reason: str | None, assessment_reasons: list[str], value_missing: bool
) -> str | None:
    """The most specific reason code for one open item."""
    if value_missing:
        return "FIELD_MISSING"
    if auto_reason and auto_reason not in ("EXTRACTION_MARKED_FOR_REVIEW",):
        return auto_reason
    names = [str(getattr(item, "value", item)) for item in assessment_reasons]
    for candidate in _ASSESSMENT_PRIORITY:
        if candidate in names:
            return candidate
    return auto_reason or (names[0] if names else None)
