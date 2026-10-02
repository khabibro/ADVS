import re

from app.core.domain import DocumentType
from app.document_intelligence.extraction.base import (
    BaseDocumentExtractor,
    ExtractedValue,
    ExtractionCandidate,
    ExtractionInput,
    candidate_matching_line,
)
from app.document_intelligence.normalization.field_normalizer import normalize_text_field

_STANDALONE_UNIVERSITY_RE = re.compile(r"[가-힣A-Za-z0-9㈜()· ]{2,40}대학교")


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
        candidate: ExtractionCandidate | None = candidate_matching_line(
            text, _STANDALONE_UNIVERSITY_RE
        )
        raw = candidate.value if candidate else None
        normalized = normalize_text_field(raw)
        if candidate is None or normalized is None:
            return self.missing("university_name")
        assert raw is not None
        return self._value(
            "university_name", raw, normalized, "standalone_university_name", candidate
        )
