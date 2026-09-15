from app.core.domain import DocumentType
from app.document_intelligence.extraction.base import BaseDocumentExtractor, ExtractedValue
from app.document_intelligence.extraction.business_registration import BusinessRegistrationExtractor
from app.document_intelligence.extraction.career import CareerCertificateExtractor
from app.document_intelligence.extraction.graduation import GraduationCertificateExtractor
from app.document_intelligence.extraction.sme_confirmation import SMEConfirmationExtractor

_EXTRACTORS: dict[DocumentType, BaseDocumentExtractor] = {
    DocumentType.GRADUATION_CERTIFICATE: GraduationCertificateExtractor(),
    DocumentType.CAREER_CERTIFICATE: CareerCertificateExtractor(),
    DocumentType.BUSINESS_REGISTRATION_CERTIFICATE: BusinessRegistrationExtractor(),
    DocumentType.SME_CONFIRMATION_CERTIFICATE: SMEConfirmationExtractor(),
}


class ExtractorRegistry:
    """DocumentType.UNKNOWN (and any future type not yet wired in) has no
    extractor -- extract() returns an empty list rather than guessing."""

    def get(self, document_type: DocumentType) -> BaseDocumentExtractor | None:
        return _EXTRACTORS.get(document_type)

    def extract(self, document_type: DocumentType, text: str) -> list[ExtractedValue]:
        extractor = self.get(document_type)
        return extractor.extract(text) if extractor else []
