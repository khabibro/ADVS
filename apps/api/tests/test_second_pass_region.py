"""The second-pass region of a value assembled from several boxes is their union (invented text)."""

from app.document_intelligence.evidence import EvidenceRef
from app.document_intelligence.extraction.base import ExtractedValue
from app.document_intelligence.ocr.models import BoundingBox
from app.services.processing import value_region


def box(text: str, x: float, y: float = 100, w: float = 40, h: float = 30, page: int = 1) -> EvidenceRef:
    return EvidenceRef(page_number=page, source_text=text, bounding_box=BoundingBox(x, y, w, h), source_kind="ocr")


def value(name: str, evidence: list[EvidenceRef]) -> ExtractedValue:
    return ExtractedValue("university_name", name, name, 0.97, False, "standalone_university_name", None, evidence)


def test_a_value_in_one_box_uses_that_box() -> None:
    region = value_region(value("가나다대학교", [box("학생증", 0), box("가나다대학교", 100, w=200)]))
    assert region is not None and region[1].x == 100 and region[1].width == 200


def test_a_letter_spaced_name_uses_the_union_of_its_boxes() -> None:
    boxes = [box("가", 100), box("나", 150), box("다", 200), box("대", 250), box("학", 300), box("교", 350)]
    page, region = value_region(value("가나다대학교", boxes))
    assert (page, region.x, region.width) == (1, 100, 290)


def test_unrelated_boxes_before_the_name_are_not_included() -> None:
    boxes = [box("발급", 0), box("가나다", 100, w=100), box("대학교", 210, w=90)]
    _, region = value_region(value("가나다대학교", boxes))
    assert (region.x, region.width) == (100, 200)


def test_without_a_matching_run_it_falls_back_to_the_last_box() -> None:
    page, region = value_region(value("라마바대학교", [box("가", 100), box("나", 150)]))
    assert region.x == 150
