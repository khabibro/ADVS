"""Phase G / G-2: the university name from the issuer line of a scanned or photographed
재학증명서/성적증명서. The names below are invented and are not in any evaluation data set."""

import pytest

from app.core.domain import DocumentType
from app.document_intelligence.extraction.registry import ExtractorRegistry
from app.document_intelligence.ocr.models import BoundingBox, OCRDocumentResult, OCRLine, OCRPage

H = 44.0


def seg(text: str, x: float, y: float, width: float = 600.0, height: float = H) -> OCRLine:
    return OCRLine(
        text=text,
        confidence=0.97,
        bounding_box=BoundingBox(x=x, y=y, width=width, height=height),
    )


def university(lines: list[OCRLine], kind: DocumentType = DocumentType.TRANSCRIPT) -> str | None:
    page = OCRPage(
        1, "\n".join(line.text for line in lines), lines, 0.97, metadata={"source": "ocr"}
    )
    source = OCRDocumentResult("ocr", [page], page.text)
    values = {v.field_name: v.normalized_value for v in ExtractorRegistry().extract(kind, source)}
    return values.get("university_name")


BODY = [seg("성적증명서", 800, 80, 500, 120), seg("위의 사실을 증명합니다.", 800, 700, 700)]


@pytest.mark.parametrize(
    "printed",
    [
        "새벽바다대학교총장",  # OCR dropped the space before the title
        "새벽바다대학교 총장",
        "새벽바다대학교총창",  # 장 misread as 창
        "새벽바다대학교총",  # title truncated by a seal
        "새벽바다대학교",  # no title at all
        "새 벽 바 다 대 학 교 총 장",  # letter-spaced
        "새 벽 바다 대 학 교 총",  # letter-spaced, mixed token sizes
    ],
)
def test_issuer_line_variants_give_the_same_name(printed: str) -> None:
    assert university([*BODY, seg(printed, 700, 900, 900)]) == "새벽바다대학교"


def test_name_split_by_a_seal_is_rejoined_on_one_row() -> None:
    lines = [*BODY, seg("오로라과학대학", 700, 900, 700), seg("교", 1420, 925, 60, 40)]
    assert university(lines, DocumentType.ENROLLMENT_CERTIFICATE) == "오로라과학대학교"


def test_split_syllable_on_another_row_or_far_away_is_not_joined() -> None:
    below = [*BODY, seg("오로라과학대학", 700, 900, 700), seg("교", 1420, 1100, 60, 40)]
    far = [*BODY, seg("오로라과학대학", 700, 900, 700), seg("교", 2600, 905, 60, 40)]
    assert university(below, DocumentType.ENROLLMENT_CERTIFICATE) is None
    assert university(far, DocumentType.ENROLLMENT_CERTIFICATE) is None


def test_truncated_name_without_the_last_syllable_stays_unresolved() -> None:
    """A name that OCR cut short is left to a person, never completed by guessing."""
    assert university([*BODY, seg("오로라과학대학(", 700, 900, 700)]) is None


def test_two_different_universities_give_no_answer() -> None:
    lines = [
        *BODY,
        seg("새벽바다대학교총장", 700, 900, 900),
        seg("오로라과학대학교총장", 700, 1000, 900),
    ]
    assert university(lines) is None


def test_department_text_is_not_a_university() -> None:
    lines = [
        *BODY,
        seg("소속:공과대학데이터공학과", 100, 300, 800),
        seg("대학글쓰기", 900, 500, 300),
    ]
    assert university(lines) is None
