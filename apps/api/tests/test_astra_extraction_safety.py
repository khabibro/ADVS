"""Synthetic adversarial fixtures only; no transcribed document identities."""

import pytest

from app.core.domain import DocumentType
from app.document_intelligence.classification.classifier import DocumentClassifier
from app.document_intelligence.extraction.registry import ExtractorRegistry
from app.document_intelligence.normalization.field_normalizer import (
    normalize_date,
    normalize_gpa,
    normalize_text_field,
)
from app.document_intelligence.ocr.models import BoundingBox, OCRDocumentResult, OCRLine, OCRPage


def extract(kind, text):
    return {f.field_name: f for f in ExtractorRegistry().extract(kind, text)}


@pytest.mark.parametrize("separator", ["~", "-", "–", "—", "부터", "에서", "∼"])
@pytest.mark.parametrize(
    "dates",
    [
        ("2021.04.01", "2022.03.31"),
        ("2021년 4월 1일", "2022년 3월 31일"),
        ("2021–04–01", "2022–03–31"),
    ],
)
def test_range_endpoints_remain_distinct(separator, dates):
    raw = f"{dates[0]} {separator} {dates[1]}"
    fields = extract(DocumentType.SME_CONFIRMATION_CERTIFICATE, f"유효기간: {raw}")
    assert fields["valid_from"].normalized_value == "2021-04-01"
    assert fields["valid_until"].normalized_value == "2022-03-31"
    assert normalize_date(raw) is None


@pytest.mark.parametrize(
    "raw",
    [
        "2021.04.01 및 2022.03.31",
        "2022.03.31 ~ 2021.04.01",
        "2021.02.30 ~ 2022.03.31",
        "2021.04.01 ~ 알 수 없음",
    ],
)
def test_invalid_or_ambiguous_range_never_becomes_single_expiry(raw):
    fields = extract(DocumentType.SME_CONFIRMATION_CERTIFICATE, f"유효기간: {raw}")
    assert fields["valid_from"].normalized_value is None
    assert fields["valid_until"].normalized_value is None


def test_issue_date_does_not_supply_graduation_or_employment_or_validity():
    text = "2026.09.01\n가상대학교 총장"
    for kind, names in [
        (DocumentType.GRADUATION_CERTIFICATE, ["graduation_date"]),
        (DocumentType.CAREER_CERTIFICATE, ["employment_start_date", "employment_end_date"]),
        (DocumentType.SME_CONFIRMATION_CERTIFICATE, ["valid_from", "valid_until"]),
    ]:
        fields = extract(kind, text)
        assert fields["issue_date"].normalized_value == "2026-09-01"
        assert fields["issue_date"].needs_review
        assert fields["issue_date"].extraction_method == "document_semantic_issue_date"
        assert all(fields[name].normalized_value is None for name in names)


def test_issue_date_does_not_shadow_employment_range():
    fields = extract(
        DocumentType.CAREER_CERTIFICATE,
        "근무기간: 2021.04.01 — 2022.03.31\n2026.09.01\n가상기관 기관장",
    )
    assert fields["employment_start_date"].normalized_value == "2021-04-01"
    assert fields["employment_end_date"].normalized_value == "2022-03-31"


@pytest.mark.parametrize(
    "text",
    [
        "졸업일자\n2026.09.01\n가상대학교 총장",
        "입사일\n2026.09.01\n가상기관 기관장",
        "2026.08.01\n본문\n본문\n본문\n2026.09.01\n가상대학교 총장",
        "발급일자: 읽을 수 없음\n2026.09.01\n가상대학교 총장",
    ],
)
def test_issue_inference_abstains_when_labelled_elsewhere_or_ambiguous(text):
    assert extract(DocumentType.ENROLLMENT_CERTIFICATE, text)["issue_date"].normalized_value is None


def test_labelled_semantic_dates_remain_supported():
    fields = extract(
        DocumentType.GRADUATION_CERTIFICATE, "졸업일자: 2024.02.20\n발급일자: 2026.09.01"
    )
    assert fields["graduation_date"].normalized_value == "2024-02-20"
    assert fields["issue_date"].normalized_value == "2026-09-01"
    assert not fields["issue_date"].needs_review


def test_identifier_dash_cleanup_preserves_organization_and_raw_evidence():
    fields = extract(
        DocumentType.BUSINESS_REGISTRATION_CERTIFICATE,
        "상호: 가상—연구소\n사업자등록번호: 123–45–67890",
    )
    assert fields["company_name"].normalized_value == "가상—연구소"
    assert fields["business_registration_number"].normalized_value == "1234567890"
    assert fields["business_registration_number"].raw_value == "123–45–67890"
    assert normalize_text_field("가상—연구소") == "가상—연구소"
    assert normalize_gpa("-3.5") is None


def test_mixed_source_provenance_is_per_evidence_page():
    pages = [
        OCRPage(
            1,
            "성명: 김가상",
            [OCRLine("성명: 김가상", None, BoundingBox(1, 2, 30, 10))],
            metadata={"source": "direct_pdf_text"},
        ),
        OCRPage(
            2,
            "학번: 202600001",
            [OCRLine("학번: 202600001", 0.0, BoundingBox(5, 6, 90, 20))],
            metadata={"source": "ocr"},
        ),
    ]
    fields = extract(
        DocumentType.ENROLLMENT_CERTIFICATE,
        OCRDocumentResult("paddle", pages, "\n".join(p.text for p in pages)),
    )
    name, student_id = fields["student_name"], fields["student_id"]
    assert name.evidence[0].source_kind == "embedded_pdf_text"
    assert name.evidence[0].coordinate_space == "pdf_point"
    assert student_id.evidence[0].source_kind == "ocr"
    assert student_id.evidence[0].coordinate_space == "pixel"
    assert student_id.confidence == 0.0


def test_colon_pairing_rejects_distant_column():
    page = OCRPage(
        1,
        "",
        [
            OCRLine("성명:", 0.99, BoundingBox(0, 0, 30, 10)),
            OCRLine("김가상", 0.99, BoundingBox(1000, 0, 50, 10)),
        ],
    )
    fields = extract(DocumentType.ENROLLMENT_CERTIFICATE, OCRDocumentResult("paddle", [page], ""))
    assert fields["student_name"].normalized_value is None


def test_conflicting_candidates_abstain_and_classification_tie_is_unknown():
    assert (
        extract(DocumentType.ENROLLMENT_CERTIFICATE, "성명: 김가상\n성명: 이가상")[
            "student_name"
        ].normalized_value
        is None
    )
    result = DocumentClassifier().classify("재학증명서 성적증명서 학번")
    assert result.predicted_type == DocumentType.UNKNOWN
    assert result.needs_review
    assert ExtractorRegistry().extract(result.predicted_type, "성명: 김가상") == []
