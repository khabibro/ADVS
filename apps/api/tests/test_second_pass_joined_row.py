"""The second reading of a value made of several one-character boxes covers the whole line (invented boxes)."""

from app.document_intelligence.evidence import EvidenceRef
from app.document_intelligence.extraction.base import ExtractedValue
from app.document_intelligence.ocr.models import BoundingBox
from app.services.processing import _value_evidence


def piece(text: str, x: float, y: float = 2400, w: float = 110, h: float = 110, page: int = 1) -> EvidenceRef:
    return EvidenceRef(page_number=page, source_text=text, bounding_box=BoundingBox(x, y, w, h), confidence=0.9)


def value(evidence: list[EvidenceRef], normalized: str) -> ExtractedValue:
    return ExtractedValue("university_name", normalized, normalized, 0.9, False, "standalone_university_name", "", evidence)


def test_letter_spaced_pieces_are_read_back_as_one_region() -> None:
    pieces = [piece("가", 700), piece("나", 850), piece("대", 1000), piece("학", 1150), piece("교", 1300)]
    joined = _value_evidence(value(pieces, "가나대학교"))
    assert joined is not None and joined.bounding_box is not None
    box = joined.bounding_box
    assert (box.x, box.y, box.height) == (700, 2400, 110) and box.x + box.width == 1410
    assert joined.source_text == "가나대학교"


def test_a_box_that_holds_the_value_is_still_preferred() -> None:
    whole = piece("가나대학교", 700, w=600)
    assert _value_evidence(value([piece("학교명:", 300), whole], "가나대학교")) is whole


def test_a_name_and_its_title_in_two_boxes_are_joined() -> None:
    boxes = [piece("가나", 700, w=300), piece("대학교", 1050, w=330)]
    joined = _value_evidence(value(boxes, "가나대학교"))
    assert joined is not None and joined.bounding_box is not None
    assert joined.bounding_box.x == 700 and joined.bounding_box.x + joined.bounding_box.width == 1380


def test_a_label_box_is_never_merged_into_the_region() -> None:
    label, other = piece("학교명:", 300, w=300), piece("가나", 650, w=200)
    # the boxes do not spell the value ("학교명:가나" does not contain "가나대학교"): the last box, as before
    assert _value_evidence(value([label, other], "가나대학교")) is other


def test_pieces_on_different_rows_or_pages_are_not_joined() -> None:
    rows = [piece("가", 700, y=2400), piece("나", 850, y=2400), piece("대", 1000, y=2900)]
    assert _value_evidence(value(rows, "가나대")) is rows[-1]
    pages = [piece("가", 700), piece("나", 850), piece("대", 1000, page=2)]
    assert _value_evidence(value(pages, "가나대")) is pages[-1]


def test_pieces_that_do_not_spell_the_value_exactly_are_still_joined_as_a_letter_spaced_line() -> None:
    # the value was normalised after the pieces were read (one character differs): three or more short pieces
    pieces = [piece("가", 700), piece("나", 850), piece("대", 1000), piece("학", 1150), piece("교", 1300)]
    joined = _value_evidence(value(pieces, "가다대학교"))
    assert joined is not None and joined.bounding_box is not None and joined.bounding_box.x == 700
