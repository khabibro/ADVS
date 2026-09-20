from app.core.domain import DocumentType
from app.document_intelligence.extraction.base import (
    BaseDocumentExtractor,
    ExtractedValue,
    ExtractionCandidate,
    ExtractionInput,
    candidate_after_label,
    split_range,
)
from app.document_intelligence.normalization.field_normalizer import (
    normalize_date,
)


class SMEConfirmationExtractor(BaseDocumentExtractor):
    document_type = DocumentType.SME_CONFIRMATION_CERTIFICATE

    def extract(self, text: ExtractionInput) -> list[ExtractedValue]:
        validity_candidate = candidate_after_label(text, ["유효기간"])
        return [
            self.text_field(text, "company_name", ["기업명", "회사명", "상호"]),
            self.text_field(text, "representative_name", ["대표자", "대표자명"]),
            self.business_number_field(
                text, "business_registration_number", ["사업자등록번호", "등록번호"]
            ),
            self.text_field(
                text, "certificate_number", ["발급번호", "확인번호", "증명서번호", "일련번호"]
            ),
            self.date_field(text, "issue_date", ["발급일", "발급일자", "발행일자"]),
            self._validity_date_field(validity_candidate, "valid_from", 0),
            self._validity_date_field(validity_candidate, "valid_until", 1),
        ]

    def _validity_date_field(
        self, source: ExtractionCandidate | None, field_name: str, range_index: int
    ) -> ExtractedValue:
        raw = source.value if source else None
        start_raw, end_raw = split_range(raw)
        candidate = (start_raw, end_raw)[range_index]
        if candidate is None and field_name == "valid_until":
            candidate = raw
        normalized = normalize_date(candidate)
        if normalized is None or source is None:
            return self.missing(field_name)
        assert candidate is not None
        return self._value(field_name, candidate, normalized, "regex_date", source)
