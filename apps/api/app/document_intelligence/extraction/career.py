from dataclasses import replace

from app.core.domain import DocumentType
from app.document_intelligence.extraction.base import (
    BaseDocumentExtractor,
    ExtractedValue,
    after_label,
    split_range,
)
from app.document_intelligence.normalization.field_normalizer import normalize_date

_START_LABELS = ["입사일", "근무 시작일"]
_END_LABELS = ["퇴사일", "근무 종료일"]
_RANGE_LABELS = ["재직기간", "재직 기간", "근무기간", "근무 기간"]


class CareerCertificateExtractor(BaseDocumentExtractor):
    """MVP limitation: extracts a single employment period only. A document
    listing multiple non-contiguous employment periods will only surface
    the first one found (either explicit start/end labels, or the first
    '재직기간/근무기간' range) -- it does not attempt to enumerate all of
    them, and does not silently merge conflicting periods.

    When more than one such label is present, the dates are still returned
    (best-effort, first occurrence) but flagged `needs_review=True`, per the
    P1.5 requirement that an unsupported multi-period structure must not be
    silently presented as a confident result (evaluation/reports/
    baseline_2026-09-09.md, UNSUPPORTED_LAYOUT category)."""

    document_type = DocumentType.CAREER_CERTIFICATE

    def extract(self, text: str) -> list[ExtractedValue]:
        start = self.date_field(text, "employment_start_date", _START_LABELS)
        end = self.date_field(text, "employment_end_date", _END_LABELS)
        if start.normalized_value is None and end.normalized_value is None:
            start, end = self._from_range(text)
            multi_period = any(text.count(label) > 1 for label in _RANGE_LABELS)
        else:
            multi_period = any(text.count(label) > 1 for label in _START_LABELS + _END_LABELS)
        if multi_period:
            start = _flag_for_review(start)
            end = _flag_for_review(end)
        return [
            self.text_field(text, "applicant_name", ["성명", "이름", "신청인"]),
            self.text_field(text, "company_name", ["회사명", "상호", "기업명", "업체명"]),
            self.text_field(text, "position", ["직위", "직급"]),
            start,
            end,
            self.date_field(text, "issue_date", ["발급일자", "발행일자"]),
        ]

    def _from_range(self, text: str) -> tuple[ExtractedValue, ExtractedValue]:
        raw_range = after_label(text, _RANGE_LABELS)
        start_raw, end_raw = split_range(raw_range)
        return (
            self._date_from_raw("employment_start_date", start_raw),
            self._date_from_raw("employment_end_date", end_raw),
        )

    def _date_from_raw(self, field_name: str, raw: str | None) -> ExtractedValue:
        normalized = normalize_date(raw)
        if normalized is None:
            return self.missing(field_name)
        return ExtractedValue(field_name, raw, normalized, 0.5, False, "regex_date_range", raw)


def _flag_for_review(value: ExtractedValue) -> ExtractedValue:
    if value.normalized_value is None:
        return value
    return replace(value, needs_review=True)
