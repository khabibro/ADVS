import re
from dataclasses import replace

from app.core.domain import DocumentType
from app.document_intelligence.extraction.base import (
    BaseDocumentExtractor,
    ExtractedValue,
    ExtractionInput,
)

_GLUED_COLLEGE_RE = re.compile(r"(.{2,8}?대학)(?![원교])\s*(.{2,}(?:학과|학부|전공))")


def department_without_college(value: ExtractedValue) -> ExtractedValue:
    """소속 prints "단과대학 학과" ("공과대학 기계공학과"); the department is the
    part after the college. Only a leading token ending in 대학 is dropped."""
    normalized = value.normalized_value
    if normalized is None:
        return value
    glued = _GLUED_COLLEGE_RE.fullmatch(normalized)
    if glued:
        # OCR often drops the space inside one recognised box: "공과대학기계공학과".
        return replace(value, normalized_value=glued.group(2))
    tokens = normalized.split()
    if len(tokens) > 1 and tokens[0].endswith("대학") and not tokens[0].endswith("대학교"):
        return replace(value, normalized_value=" ".join(tokens[1:]))
    return value


class EnrollmentCertificateExtractor(BaseDocumentExtractor):
    document_type = DocumentType.ENROLLMENT_CERTIFICATE

    def extract(self, text: ExtractionInput) -> list[ExtractedValue]:
        return [
            self.text_field(text, "student_name", ["학생명", "성명", "이름"]),
            self._university_name(text),
            self._department(text),
            self.text_field(text, "student_id", ["학번"]),
            self.issue_date_field(text, ["발급일", "발급일자", "발행일자"]),
        ]

    def _university_name(self, text: ExtractionInput) -> ExtractedValue:
        labeled = self.text_field(text, "university_name", ["대학교", "대학명", "학교명", "대학"])
        if labeled.normalized_value is not None:
            return labeled
        return self.issuer_university_field(text)

    def _department(self, text: ExtractionInput) -> ExtractedValue:
        # 학과/소속 name the student's department; 전공 can be a different
        # (second or minor) major, so it is only a fallback.
        primary = self.text_field(text, "department", ["학과", "소속"])
        if primary.normalized_value is not None:
            return department_without_college(primary)
        return department_without_college(self.text_field(text, "department", ["전공"]))
