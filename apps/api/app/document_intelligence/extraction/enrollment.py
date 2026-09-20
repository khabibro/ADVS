from app.core.domain import DocumentType
from app.document_intelligence.extraction.base import BaseDocumentExtractor, ExtractedValue


class EnrollmentCertificateExtractor(BaseDocumentExtractor):
    document_type = DocumentType.ENROLLMENT_CERTIFICATE

    def extract(self, text: str) -> list[ExtractedValue]:
        return [
            self.text_field(text, "student_name", ["학생명", "성명", "이름"]),
            self.text_field(text, "university_name", ["대학교", "대학명", "학교명"]),
            self.text_field(text, "department", ["학과", "전공"]),
            self.text_field(text, "student_id", ["학번"]),
            self.date_field(text, "issue_date", ["발급일자", "발행일자"]),
        ]
