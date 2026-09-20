from app.core.domain import DocumentType
from app.document_intelligence.extraction.base import (
    BaseDocumentExtractor,
    ExtractedValue,
    ExtractionInput,
)


class GraduationCertificateExtractor(BaseDocumentExtractor):
    document_type = DocumentType.GRADUATION_CERTIFICATE

    def extract(self, text: ExtractionInput) -> list[ExtractedValue]:
        return [
            self.text_field(text, "applicant_name", ["성명", "이름", "신청인"]),
            self.text_field(text, "university_name", ["대학교", "대학명", "학교명"]),
            self.text_field(text, "department", ["학과", "전공"]),
            self.text_field(text, "degree", ["학위"]),
            self.date_field(text, "graduation_date", ["졸업일자", "졸업 연월일"]),
            self.date_field(text, "issue_date", ["발급일자", "발행일자"]),
        ]
