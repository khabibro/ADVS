"""What an applicant is told about a problem, and what to do about it.

Only decision facts are named: the document, and the validity date for an expired document. Read
values (names, numbers, grades) are never shown to the applicant. Everything not listed here is
"담당자 확인 중" with no action expected from the applicant.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.core.domain import DocumentType

DOCUMENT_LABELS: dict[str, str] = {
    DocumentType.GRADUATION_CERTIFICATE.value: "졸업증명서",
    DocumentType.CAREER_CERTIFICATE.value: "경력증명서",
    DocumentType.BUSINESS_REGISTRATION_CERTIFICATE.value: "사업자등록증",
    DocumentType.SME_CONFIRMATION_CERTIFICATE.value: "중소기업(소상공인)확인서",
    DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE.value: "국세 납세증명서",
    DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE.value: "4대보험 완납증명서",
    DocumentType.ENROLLMENT_CERTIFICATE.value: "재학증명서",
    DocumentType.TRANSCRIPT.value: "성적증명서",
}
FALLBACK_LABEL = "서류"

#: kind of problem -> who has to act
ACTION_APPLICANT = "APPLICANT"
ACTION_STAFF = "STAFF"


@dataclass(frozen=True)
class ApplicantMessage:
    message: str
    action: str  # ACTION_APPLICANT: the applicant can fix it; ACTION_STAFF: wait for a reviewer


def document_label(document_type: str | None) -> str:
    return DOCUMENT_LABELS.get(document_type or "", FALLBACK_LABEL)


def applicant_message(
    code: str,
    document_type: str | None,
    *,
    valid_until: date | None = None,
    evaluation_date: date | None = None,
) -> ApplicantMessage:
    label = document_label(document_type)
    if code == "MISSING_REQUIRED_DOCUMENT":
        return ApplicantMessage(
            f"{label}이(가) 아직 제출되지 않았습니다. 해당 서류를 올려 주세요.", ACTION_APPLICANT
        )
    if code == "EXPIRED_DOCUMENT":
        if valid_until and evaluation_date:
            return ApplicantMessage(
                f"{label}의 유효기간({valid_until:%Y-%m-%d})이 점검 기준일({evaluation_date:%Y-%m-%d})"
                "보다 먼저 끝났습니다. 유효한 서류를 새로 발급받아 올려 주세요.",
                ACTION_APPLICANT,
            )
        return ApplicantMessage(
            f"{label}의 유효기간이 지났습니다. 유효한 서류를 새로 발급받아 올려 주세요.",
            ACTION_APPLICANT,
        )
    if code == "ISSUE_DATE_TOO_OLD":
        return ApplicantMessage(
            f"{label}의 발급일이 너무 오래되었습니다. 최근에 발급받은 서류를 올려 주세요.",
            ACTION_APPLICANT,
        )
    if code == "WRONG_DOCUMENT_TYPE":
        return ApplicantMessage(
            f"올리신 파일이 요청한 {label}이(가) 아닙니다. 비슷하지만 다른 서류일 수 있으니 "
            "올바른 서류를 올려 주세요.",
            ACTION_APPLICANT,
        )
    if code == "COMPANY_NAME_MISMATCH":
        return ApplicantMessage(
            f"{label}의 회사명이 신청서의 회사명과 다릅니다. 회사명이 같은 서류인지 확인해 주세요.",
            ACTION_APPLICANT,
        )
    if code == "APPLICANT_NAME_MISMATCH":
        return ApplicantMessage(
            f"{label}의 이름이 신청서의 이름과 다릅니다. 본인 서류인지 확인해 주세요.",
            ACTION_APPLICANT,
        )
    if code in {"DUPLICATE_UPLOAD", "DUPLICATE_UPLOAD_IGNORED", "DUPLICATE_RESULTS_CONFLICT"}:
        return ApplicantMessage(
            "같은 파일이 두 번 올라왔습니다. 한 번만 사용하니 다른 서류를 올려 주세요.",
            ACTION_APPLICANT,
        )
    if code == "MULTIPLE_DOCUMENTS_IN_FILE":
        return ApplicantMessage(
            "한 파일에 서로 다른 서류가 들어 있습니다. 서류별로 나누어 올려 주세요.",
            ACTION_APPLICANT,
        )
    return ApplicantMessage("담당자가 확인 중입니다. 따로 하실 일은 없습니다.", ACTION_STAFF)
