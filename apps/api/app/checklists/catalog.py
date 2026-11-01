"""What the editor may offer, served by the API so the frontend holds no domain constants."""

from __future__ import annotations

from app.core.domain import DOCUMENT_TYPE_DISPLAY_NAMES, REVIEWABLE_FIELDS, DocumentType
from app.services.requirements import DEFAULT_REQUIRED_FIELDS

FIELD_LABELS_KO: dict[str, str] = {
    "applicant_name": "신청인 이름",
    "student_name": "이름",
    "birth_date": "생년월일",
    "student_id": "학번",
    "university_name": "대학",
    "department": "학과",
    "degree": "학위",
    "graduation_date": "졸업일",
    "issue_date": "발급일",
    "company_name": "상호",
    "workplace_name": "사업장명",
    "business_registration_number": "사업자등록번호",
    "representative_name": "대표자",
    "business_address": "사업장 주소",
    "business_type": "업태",
    "business_item": "종목",
    "certificate_number": "확인서 번호",
    "valid_from": "유효기간 시작",
    "valid_until": "유효기간 만료",
    "position": "직위",
    "employment_start_date": "재직 시작일",
    "employment_end_date": "재직 종료일",
    "gpa": "평점",
    "gpa_scale": "평점 만점",
}

NUMERIC_FIELDS = frozenset({"gpa"})
SCALE_FIELD_OF: dict[str, str] = {"gpa": "gpa_scale"}
GPA_SCALES = ("4.5", "4.3", "4")

# Comparison kinds, in plain Korean. Normalisation is applied by the engine; only the switches in
# ``Normalise`` are editable.
MATCH_KINDS_KO = {
    "IDENTIFIER": "번호 (숫자·문자만 비교)",
    "TEXT": "글자 (띄어쓰기 무시)",
    "INSTITUTION": "학교명 (학교법인·괄호 무시)",
}
SEVERITIES_KO = {"ERROR": "보완 필요", "WARNING": "확인 필요"}
# Noun phrases: the editor shows "<phrase> 차이를 무시", the sentence lists what is ignored.
NORMALISE_KO = {
    "legal_form": "주식회사·(주)·㈜ 표기",
    "spaces": "띄어쓰기",
    "parenthesised_latin": "괄호 안 영문 표기",
    "workplace_name": "같은 사업자번호일 때 더 짧은 사업장명",
}
FIXED_POLICIES_KO = [
    "유사 서류(휴학증명서·지방세납세증명서 등)는 다른 서류로 보고 담당자 확인을 요청합니다.",
    "같은 파일을 다시 올리면 안내만 하고, 서로 다른 파일이 충돌하면 담당자 확인으로 넘깁니다.",
    "읽은 값이 불확실하거나 확인되지 않았으면 오류로 처리하지 않고 담당자 확인으로 넘깁니다.",
    "점검 기준일은 제출자가 바꿀 수 없습니다.",
]


def document_label(document_type: DocumentType | str) -> str:
    return DOCUMENT_TYPE_DISPLAY_NAMES[DocumentType(document_type)]


def field_label(field: str) -> str:
    return FIELD_LABELS_KO.get(field, field)


def build_catalog() -> dict:
    documents = []
    for document_type in DocumentType:
        if document_type == DocumentType.UNKNOWN:
            continue
        fields = REVIEWABLE_FIELDS[document_type]
        documents.append(
            {
                "type": document_type.value,
                "label_ko": document_label(document_type),
                "fields": [{"name": name, "label_ko": field_label(name)} for name in fields],
                "default_required": list(DEFAULT_REQUIRED_FIELDS[document_type]),
                "has_valid_until": "valid_until" in fields,
                "has_issue_date": "issue_date" in fields,
                "numeric_fields": [name for name in fields if name in NUMERIC_FIELDS],
            }
        )
    return {
        "documents": documents,
        "match_kinds": [{"value": k, "label_ko": v} for k, v in MATCH_KINDS_KO.items()],
        "severities": [{"value": k, "label_ko": v} for k, v in SEVERITIES_KO.items()],
        "normalise": [{"name": k, "label_ko": v} for k, v in NORMALISE_KO.items()],
        # the legal-form, Latin-in-parentheses and workplace-name switches only matter when one side is a
        # company / workplace name
        "company_name_fields": ["company_name", "workplace_name"],
        "gpa_scales": list(GPA_SCALES),
        "check_date_policies": [
            {"value": "SUBMISSION_DATE", "label_ko": "제출한 날(서버 날짜)"},
            {"value": "FIXED", "label_ko": "고정 날짜"},
            {"value": "STAFF_CHOICE", "label_ko": "담당자가 정함"},
        ],
        "fixed_policies_ko": FIXED_POLICIES_KO,
        "limits": {"max_age_days": {"min": 1, "max": 365}},
    }
