from app.core.domain import DocumentType
from app.document_intelligence.extraction.base import (
    BaseDocumentExtractor,
    ExtractedValue,
    after_label,
    split_range,
)
from app.document_intelligence.normalization.field_normalizer import (
    normalize_date,
    normalize_text_field,
)


class SMEConfirmationExtractor(BaseDocumentExtractor):
    document_type = DocumentType.SME_CONFIRMATION_CERTIFICATE

    def extract(self, text: str) -> list[ExtractedValue]:
        validity_raw = after_label(text, ["유효기간"])
        return [
            self.text_field(text, "company_name", ["기업명", "회사명", "상호"]),
            self.text_field(text, "representative_name", ["대표자", "대표자명"]),
            self.business_number_field(
                text, "business_registration_number", ["사업자등록번호", "등록번호"]
            ),
            self.text_field(text, "certificate_number", ["확인번호", "증명서번호", "일련번호"]),
            self.date_field(text, "issue_date", ["발급일자", "발행일자"]),
            self._expiration_field(validity_raw),
            self._validity_period_field(validity_raw),
        ]

    def _validity_period_field(self, raw: str | None) -> ExtractedValue:
        start_raw, end_raw = split_range(raw)
        start = normalize_date(start_raw)
        end = normalize_date(end_raw)
        normalized = f"{start} ~ {end}" if start and end else normalize_text_field(raw)
        if normalized is None:
            return self.missing("validity_period")
        return ExtractedValue("validity_period", raw, normalized, 0.6, False, "label_match", raw)

    def _expiration_field(self, raw: str | None) -> ExtractedValue:
        if not raw:
            return self.missing("expiration_date")
        _, end_raw = split_range(raw)
        candidate = end_raw or raw
        normalized = normalize_date(candidate)
        if normalized is None:
            return self.missing("expiration_date")
        return ExtractedValue(
            "expiration_date", candidate, normalized, 0.55, False, "regex_date", candidate
        )
