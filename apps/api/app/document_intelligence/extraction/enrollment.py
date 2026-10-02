from app.core.domain import DocumentType
from app.document_intelligence.extraction.base import (
    BaseDocumentExtractor,
    ExtractedValue,
    ExtractionInput,
)


class EnrollmentCertificateExtractor(BaseDocumentExtractor):
    document_type = DocumentType.ENROLLMENT_CERTIFICATE

    def extract(self, text: ExtractionInput) -> list[ExtractedValue]:
        return [
            self.text_field(text, "student_name", ["학생명", "성명", "이름"]),
            self.text_field(text, "university_name", ["대학교", "대학명", "학교명", "대학"]),
            self.text_field(text, "department", ["학과", "전공"]),
            self.text_field(text, "student_id", ["학번"]),
            self.issue_date_field(text, ["발급일", "발급일자", "발행일자"]),
        ]
