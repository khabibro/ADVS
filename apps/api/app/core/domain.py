from enum import StrEnum


class DocumentType(StrEnum):
    GRADUATION_CERTIFICATE = "GRADUATION_CERTIFICATE"
    CAREER_CERTIFICATE = "CAREER_CERTIFICATE"
    BUSINESS_REGISTRATION_CERTIFICATE = "BUSINESS_REGISTRATION_CERTIFICATE"
    SME_CONFIRMATION_CERTIFICATE = "SME_CONFIRMATION_CERTIFICATE"
    NATIONAL_TAX_PAYMENT_CERTIFICATE = "NATIONAL_TAX_PAYMENT_CERTIFICATE"
    SOCIAL_INSURANCE_PAYMENT_CERTIFICATE = "SOCIAL_INSURANCE_PAYMENT_CERTIFICATE"
    ENROLLMENT_CERTIFICATE = "ENROLLMENT_CERTIFICATE"
    TRANSCRIPT = "TRANSCRIPT"
    UNKNOWN = "UNKNOWN"


class ProcessingStatus(StrEnum):
    UPLOADED = "UPLOADED"
    PREPROCESSING = "PREPROCESSING"
    OCR_PENDING = "OCR_PENDING"
    OCR_PROCESSING = "OCR_PROCESSING"
    OCR_COMPLETED = "OCR_COMPLETED"
    CLASSIFYING = "CLASSIFYING"
    EXTRACTING = "EXTRACTING"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class OverallStatus(StrEnum):
    READY = "READY"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NEEDS_CORRECTION = "NEEDS_CORRECTION"


class RuleType(StrEnum):
    REQUIRED_DOCUMENT = "REQUIRED_DOCUMENT"
    REQUIRED_FIELD = "REQUIRED_FIELD"
    DATE_NOT_EXPIRED = "DATE_NOT_EXPIRED"
    ISSUE_DATE_MAX_AGE = "ISSUE_DATE_MAX_AGE"
    APPLICANT_NAME_MATCH = "APPLICANT_NAME_MATCH"
    COMPANY_NAME_MATCH = "COMPANY_NAME_MATCH"
    BUSINESS_REGISTRATION_NUMBER_MATCH = "BUSINESS_REGISTRATION_NUMBER_MATCH"
    DUPLICATE_DOCUMENT = "DUPLICATE_DOCUMENT"
    EXPECTED_DOCUMENT_TYPE = "EXPECTED_DOCUMENT_TYPE"
    CUSTOM_TEXT_RULE = "CUSTOM_TEXT_RULE"
    FIELD_COMPARISON = "FIELD_COMPARISON"
    DATE_COMPARISON = "DATE_COMPARISON"
    NUMERIC_COMPARISON = "NUMERIC_COMPARISON"


class RuleOperator(StrEnum):
    EQUALS = "EQUALS"
    ON_OR_BEFORE = "ON_OR_BEFORE"
    ON_OR_AFTER = "ON_OR_AFTER"
    GREATER_THAN_OR_EQUAL = "GREATER_THAN_OR_EQUAL"
    LESS_THAN_OR_EQUAL = "LESS_THAN_OR_EQUAL"


class RuleOutcome(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNRESOLVED = "UNRESOLVED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOTICE = (
        "NOTICE"  # informational (e.g. a duplicate upload was ignored); never changes the status
    )


class Severity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


EXPECTED_FIELDS: dict[DocumentType, list[str]] = {
    DocumentType.GRADUATION_CERTIFICATE: [
        "applicant_name",
        "university_name",
        "department",
        "degree",
        "graduation_date",
        "issue_date",
    ],
    DocumentType.CAREER_CERTIFICATE: [
        "applicant_name",
        "company_name",
        "position",
        "employment_start_date",
        "employment_end_date",
        "issue_date",
    ],
    DocumentType.BUSINESS_REGISTRATION_CERTIFICATE: [
        "company_name",
        "business_registration_number",
    ],
    DocumentType.SME_CONFIRMATION_CERTIFICATE: [
        "company_name",
        "business_registration_number",
        "valid_from",
        "valid_until",
    ],
    DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE: [
        "company_name",
        "business_registration_number",
        "valid_until",
    ],
    DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE: [
        "workplace_name",
        "business_registration_number",
        "valid_until",
    ],
    DocumentType.ENROLLMENT_CERTIFICATE: [
        "student_name",
        "university_name",
        "department",
        "student_id",
        "birth_date",
        "admission_date",
        "issue_date",
    ],
    DocumentType.TRANSCRIPT: [
        "student_name",
        "university_name",
        "student_id",
        "birth_date",
        "admission_date",
        "issue_date",
        "gpa",
        "gpa_scale",
    ],
    DocumentType.UNKNOWN: [],
}

OPTIONAL_SUPPORTED_FIELDS: dict[DocumentType, list[str]] = {
    DocumentType.GRADUATION_CERTIFICATE: [],
    DocumentType.CAREER_CERTIFICATE: [],
    DocumentType.BUSINESS_REGISTRATION_CERTIFICATE: [
        "representative_name",
        "business_address",
        "business_type",
        "business_item",
        "issue_date",
    ],
    DocumentType.SME_CONFIRMATION_CERTIFICATE: [
        "representative_name",
        "certificate_number",
        "issue_date",
    ],
    DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE: ["issue_date"],
    DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE: ["issue_date"],
    DocumentType.ENROLLMENT_CERTIFICATE: [],
    DocumentType.TRANSCRIPT: [],
    DocumentType.UNKNOWN: [],
}


def _field_union(required: list[str], optional: list[str]) -> list[str]:
    result = list(required)
    result.extend(field for field in optional if field not in result)
    return result


SUPPORTED_FIELDS: dict[DocumentType, list[str]] = {
    document_type: _field_union(fields, OPTIONAL_SUPPORTED_FIELDS[document_type])
    for document_type, fields in EXPECTED_FIELDS.items()
}

REVIEWABLE_FIELDS: dict[DocumentType, list[str]] = SUPPORTED_FIELDS


DOCUMENT_TYPE_DISPLAY_NAMES: dict[DocumentType, str] = {
    DocumentType.GRADUATION_CERTIFICATE: "졸업증명서",
    DocumentType.CAREER_CERTIFICATE: "경력증명서",
    DocumentType.BUSINESS_REGISTRATION_CERTIFICATE: "사업자등록증",
    DocumentType.SME_CONFIRMATION_CERTIFICATE: "중소기업확인서",
    DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE: "국세 납세증명서",
    DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE: "4대 사회보험료 완납증명서",
    DocumentType.ENROLLMENT_CERTIFICATE: "재학증명서",
    DocumentType.TRANSCRIPT: "성적증명서",
    DocumentType.UNKNOWN: "알 수 없는 문서",
}


LEGACY_OVERALL_STATUS_MAP: dict[str, OverallStatus] = {
    "PASS": OverallStatus.READY,
    "REVIEW": OverallStatus.REVIEW_REQUIRED,
    OverallStatus.READY.value: OverallStatus.READY,
    OverallStatus.REVIEW_REQUIRED.value: OverallStatus.REVIEW_REQUIRED,
    OverallStatus.NEEDS_CORRECTION.value: OverallStatus.NEEDS_CORRECTION,
}


def normalize_overall_status(value: str | OverallStatus) -> OverallStatus:
    if isinstance(value, OverallStatus):
        return value
    try:
        return LEGACY_OVERALL_STATUS_MAP[value]
    except KeyError as exc:
        raise ValueError(f"Unsupported overall status: {value}") from exc


#: Korean display names of canonical fields (shared with the admin console through the API).
FIELD_DISPLAY_NAMES: dict[str, str] = {
    "company_name": "기업명",
    "workplace_name": "사업장명",
    "representative_name": "대표자명",
    "business_registration_number": "사업자등록번호",
    "business_address": "사업장 소재지",
    "business_type": "업태",
    "business_item": "종목",
    "certificate_number": "확인서 번호",
    "valid_from": "유효기간 시작일",
    "valid_until": "유효기간 종료일",
    "student_name": "성명",
    "applicant_name": "신청인 이름",
    "university_name": "학교",
    "department": "학과",
    "degree": "학위",
    "student_id": "학번",
    "birth_date": "생년월일",
    "admission_date": "입학일자",
    "issue_date": "발급일",
    "graduation_date": "졸업일",
    "employment_start_date": "근무 시작일",
    "employment_end_date": "근무 종료일",
    "position": "직위",
    "gpa": "평점평균",
    "gpa_scale": "평점 만점",
}

#: Value kind of each canonical field: decides which checks an administrator can configure on it.
FIELD_KINDS: dict[str, str] = {
    **{
        name: "date"
        for name in (
            "valid_from",
            "valid_until",
            "birth_date",
            "admission_date",
            "issue_date",
            "graduation_date",
            "employment_start_date",
            "employment_end_date",
        )
    },
    **{name: "number" for name in ("gpa", "gpa_scale")},
    **{
        name: "identifier"
        for name in ("business_registration_number", "student_id", "certificate_number")
    },
}


def field_display_name(name: str) -> str:
    return FIELD_DISPLAY_NAMES.get(name, name)


def field_kind(name: str) -> str:
    return FIELD_KINDS.get(name, "text")
