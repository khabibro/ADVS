"""D3-7: stamp-aware reading helper (red ink detection)."""

from PIL import Image, ImageDraw

from app.document_intelligence.ocr.providers import has_red_ink


def test_red_stamp_detected_and_black_text_not() -> None:
    plain = Image.new("RGB", (200, 40), "white")
    ImageDraw.Draw(plain).rectangle((10, 10, 120, 28), fill="black")
    assert has_red_ink(plain) is False

    stamped = plain.copy()
    ImageDraw.Draw(stamped).ellipse((100, 2, 160, 38), outline=(200, 30, 30), width=4)
    assert has_red_ink(stamped) is True


def test_red_channel_hides_stamp_but_keeps_text() -> None:
    image = Image.new("RGB", (60, 20), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((5, 5, 20, 15), fill="black")
    draw.rectangle((30, 5, 50, 15), fill=(210, 30, 30))
    red = image.getchannel("R")
    assert red.getpixel((10, 10)) < 60  # black text stays dark
    assert red.getpixel((40, 10)) > 150  # red ink becomes bright


def test_company_name_after_label_whose_bracket_overlaps_value_cell() -> None:
    """D3-8: the closing bracket of "법인명(단체명)" is read into the value cell, whose box then
    overlaps the label box."""
    from app.document_intelligence.extraction.business_registration import (
        BusinessRegistrationExtractor,
    )
    from app.document_intelligence.ocr.models import (
        BoundingBox,
        OCRDocumentResult,
        OCRLine,
        OCRPage,
    )

    lines = [
        OCRLine("법인명(단체명)", 0.99, BoundingBox(245, 761, 361, 63)),
        OCRLine("):주식회사온누리샘플", 0.97, BoundingBox(572, 762, 515, 65)),
    ]
    page = OCRPage(page_number=1, text="", lines=lines, metadata={})
    values = {
        v.field_name: v
        for v in BusinessRegistrationExtractor().extract(OCRDocumentResult("x", [page], ""))
    }
    assert values["company_name"].normalized_value == "주식회사온누리샘플"
