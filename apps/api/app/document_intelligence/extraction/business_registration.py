from app.core.domain import DocumentType
from app.document_intelligence.extraction.base import (
    BaseDocumentExtractor,
    ExtractedValue,
    ExtractionInput,
)


class BusinessRegistrationExtractor(BaseDocumentExtractor):
    document_type = DocumentType.BUSINESS_REGISTRATION_CERTIFICATE

    def extract(self, text: ExtractionInput) -> list[ExtractedValue]:
        return [
            # "법인명칭" is the official label on the legally-annexed form
            # ([별지 제6호서식], law.go.kr) alongside "상호" -- see
            # evaluation/sources/source_registry.json src_business_01.
            self.text_field(text, "company_name", ["법인명(단체명)", "법인명칭", "상호", "상호명"]),
            # "대표자 성명" (compound) must be tried before the plain "대표자"
            # label -- "대표자" alone would match first and incorrectly
            # capture "성명 <name>" as the raw value.
            self.text_field(text, "representative_name", ["대표자 성명", "대표자", "대표자명"]),
            self.business_number_field(
                text, "business_registration_number", ["사업자등록번호", "등록번호"]
            ),
            self.text_field(text, "business_address", ["사업장 소재지", "소재지"]),
            self.text_field(text, "business_type", ["업태"]),
            self.text_field(text, "business_item", ["종목"]),
            # 개업연월일 is a business start date, never an issue date.
            self.date_field(text, "issue_date", ["발급일자", "발급일", "발행일자"]),
        ]
