"""Phase D2: digital extraction depends on positions, not on the order text is stored in the PDF.
Made-up values only."""

from __future__ import annotations

import random
import tempfile
from pathlib import Path

import fitz
import pytest

from app.core.domain import DocumentType
from app.document_intelligence.classification.classifier import DocumentClassifier
from app.document_intelligence.extraction.registry import ExtractorRegistry
from app.document_intelligence.ocr.models import OCRDocumentResult
from app.document_intelligence.ocr.text_assembly import assemble_document_text
from app.document_intelligence.preprocessing.processor import PdfProcessor

# (text, x, y) -- label cells, separate ":" cells and value cells, as on real certificates
SME_BOXES: list[tuple[str, float, float]] = [
    ("중 소 기 업 확 인 서", 200, 60),
    ("기    업    명", 60, 120),
    (":", 215, 120),
    ("주식회사 가온정밀", 230, 120),
    ("사업자등록번호", 60, 150),
    (":", 215, 150),
    ("123-45-67891", 230, 150),
    ("대 표 자 명", 60, 180),
    (":", 215, 180),
    ("류하늘", 230, 180),
    ("유 효 기 간", 60, 210),
    (":", 215, 210),
    ("2027-01-01 ~ 2027-12-31", 230, 210),
    ("위 기업은 중소기업임을 확인합니다.", 60, 400),
    ("2027년 01월 05일", 220, 430),
    ("중소벤처기업부장관", 190, 470),
]


def _pdf(boxes: list[tuple[str, float, float]], jitter: float = 0.0, seed: int = 0) -> Path:
    rng = random.Random(seed)
    document = fitz.open()
    page = document.new_page()
    for text, x, y in boxes:
        shift = rng.uniform(-jitter, jitter) if jitter else 0.0
        page.insert_text((x, y + shift), text, fontsize=12, fontname="korea")
    path = Path(tempfile.mkdtemp()) / "doc.pdf"
    document.save(path)
    document.close()
    return path


def _extract(path: Path) -> tuple[DocumentType, dict[str, str | None]]:
    pages = PdfProcessor().extract_text(path).pages
    source = OCRDocumentResult("direct_pdf_text", pages, assemble_document_text(pages))
    classification = DocumentClassifier().classify(source.assembled_text)
    values = ExtractorRegistry().extract(classification.predicted_type, source)
    return classification.predicted_type, {v.field_name: v.normalized_value for v in values}


def test_extraction_reads_the_certificate() -> None:
    kind, fields = _extract(_pdf(SME_BOXES))
    assert kind == DocumentType.SME_CONFIRMATION_CERTIFICATE
    assert fields["company_name"] == "주식회사 가온정밀"
    assert fields["business_registration_number"] == "1234567891"
    assert fields["valid_from"] == "2027-01-01"
    assert fields["valid_until"] == "2027-12-31"
    assert fields["issue_date"] == "2027-01-05"


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_shuffled_text_order_gives_identical_fields(seed: int) -> None:
    expected = _extract(_pdf(SME_BOXES))
    shuffled = list(SME_BOXES)
    random.Random(seed).shuffle(shuffled)
    assert _extract(_pdf(shuffled)) == expected


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_vertical_jitter_within_tolerance_gives_identical_fields(seed: int) -> None:
    expected = _extract(_pdf(SME_BOXES))
    shuffled = list(SME_BOXES)
    random.Random(seed).shuffle(shuffled)
    assert _extract(_pdf(shuffled, jitter=2.0, seed=seed)) == expected


def test_seal_mark_printed_beside_the_issue_date_does_not_hide_it() -> None:
    boxes = [(t, x, y) for t, x, y in SME_BOXES if t != "2027년 01월 05일"]
    boxes += [("2027년 01월 05일", 220, 430), ("TEST", 400, 426), ("견본", 405, 440)]
    _, fields = _extract(_pdf(boxes))
    assert fields["issue_date"] == "2027-01-05"


def test_a_labelled_date_beside_its_label_is_not_mistaken_for_the_issue_date() -> None:
    boxes = [(t, x, y) for t, x, y in SME_BOXES if t != "2027년 01월 05일"]
    boxes += [("생 년 월 일:", 60, 300), ("1999년 03월 04일", 230, 300)]
    _, fields = _extract(_pdf(boxes))
    assert fields["issue_date"] is None  # no unlabelled date in an issuer block
