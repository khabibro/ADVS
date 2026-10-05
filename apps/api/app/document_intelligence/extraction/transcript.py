from app.core.domain import DocumentType
from app.document_intelligence.extraction.base import (
    BaseDocumentExtractor,
    ExtractedValue,
    ExtractionInput,
)


class TranscriptExtractor(BaseDocumentExtractor):
    document_type = DocumentType.TRANSCRIPT

    def extract(self, text: ExtractionInput) -> list[ExtractedValue]:
        gpa_labels = ["GPA", "총평점", "평점평균", "평점"]
        return [
            self.text_field(
                text,
                "student_name",
                ["학생명", "성명", "이름"],
                allow_spatial_right=True,
            ),
            self._university_name(text),
            self.text_field(text, "student_id", ["학번"]),
            self.issue_date_field(text, ["발급일", "발급일자", "발행일자"]),
            self.gpa_field(text, "gpa", gpa_labels),
            self.gpa_scale_field(text, "gpa_scale", gpa_labels),
        ]

    def _university_name(self, text: ExtractionInput) -> ExtractedValue:
        labeled = self.text_field(text, "university_name", ["대학교", "대학명", "학교명", "대학"])
        if labeled.normalized_value is not None:
            return labeled
        return self.issuer_university_field(text)
