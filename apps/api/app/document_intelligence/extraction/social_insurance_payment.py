from app.core.domain import DocumentType
from app.document_intelligence.extraction.base import (
    BaseDocumentExtractor,
    ExtractedValue,
    ExtractionInput,
)


class SocialInsurancePaymentCertificateExtractor(BaseDocumentExtractor):
    document_type = DocumentType.SOCIAL_INSURANCE_PAYMENT_CERTIFICATE

    def extract(self, text: ExtractionInput) -> list[ExtractedValue]:
        return [
            self.text_field(text, "workplace_name", ["사업장명", "사업장 명칭"]),
            self.business_number_field(
                text, "business_registration_number", ["사업자등록번호", "등록번호"]
            ),
            self.date_field(text, "issue_date", ["발급일", "발급일자", "발행일자"]),
            self.valid_until_field(text, ["유효기한", "유효기간"]),
        ]
