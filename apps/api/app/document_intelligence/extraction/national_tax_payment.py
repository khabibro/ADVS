from app.core.domain import DocumentType
from app.document_intelligence.extraction.base import BaseDocumentExtractor, ExtractedValue


class NationalTaxPaymentCertificateExtractor(BaseDocumentExtractor):
    document_type = DocumentType.NATIONAL_TAX_PAYMENT_CERTIFICATE

    def extract(self, text: str) -> list[ExtractedValue]:
        return [
            self.text_field(text, "company_name", ["기업명", "법인명", "상호", "납세자명"]),
            self.business_number_field(
                text, "business_registration_number", ["사업자등록번호", "등록번호"]
            ),
            self.date_field(text, "issue_date", ["발급일자", "발행일자"]),
            self.valid_until_field(text, ["유효기한", "유효기간"]),
        ]
