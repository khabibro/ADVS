from enum import StrEnum


class DocumentType(StrEnum):
    GRADUATION_CERTIFICATE = "GRADUATION_CERTIFICATE"
    CAREER_CERTIFICATE = "CAREER_CERTIFICATE"
    BUSINESS_REGISTRATION_CERTIFICATE = "BUSINESS_REGISTRATION_CERTIFICATE"
    SME_CONFIRMATION_CERTIFICATE = "SME_CONFIRMATION_CERTIFICATE"
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
        "representative_name",
        "business_registration_number",
        "business_address",
        "business_type",
        "business_item",
        "issue_date",
    ],
    DocumentType.SME_CONFIRMATION_CERTIFICATE: [
        "company_name",
        "representative_name",
        "business_registration_number",
        "certificate_number",
        "issue_date",
        "expiration_date",
        "validity_period",
    ],
    DocumentType.UNKNOWN: [],
}


DOCUMENT_TYPE_DISPLAY_NAMES: dict[DocumentType, str] = {
    DocumentType.GRADUATION_CERTIFICATE: "졸업증명서",
    DocumentType.CAREER_CERTIFICATE: "경력증명서",
    DocumentType.BUSINESS_REGISTRATION_CERTIFICATE: "사업자등록증",
    DocumentType.SME_CONFIRMATION_CERTIFICATE: "중소기업확인서",
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
