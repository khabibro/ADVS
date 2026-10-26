"""Layout fixes found on real scanned certificates (synthetic geometry, invented values).

1. Stacked label glyphs fused into one tall box ("학성") with the label tails ("번:...", "명:...") kept
   with their values.
2. A letter-spaced issuer row ("가 나 대 학 교 총 장") detected one glyph per box.
3. A certificate serial number ("제 2026-0000001 호") in the title's band.
"""

from __future__ import annotations

from app.core.domain import DocumentType
from app.document_intelligence.classification.classifier import DocumentClassifier
from app.document_intelligence.classification.title_gate import assess_title
from app.document_intelligence.extraction.registry import ExtractorRegistry
from app.document_intelligence.ocr.layout import split_stacked_label_boxes
from app.document_intelligence.ocr.models import BoundingBox, OCRDocumentResult, OCRLine, OCRPage
from app.document_intelligence.ocr.text_assembly import assemble_page_text, denoised_pages


def _line(text: str, x: float, y: float, w: float, h: float, conf: float = 0.97) -> OCRLine:
    return OCRLine(text, conf, BoundingBox(x, y, w, h))


def _doc(lines: list[OCRLine]) -> OCRDocumentResult:
    page = OCRPage(1, "\n".join(item.text for item in lines), lines, 0.97)
    return OCRDocumentResult(provider="paddle", pages=[page], assembled_text=page.text)


def _fields(document_type: DocumentType, lines: list[OCRLine]) -> dict:
    return {f.field_name: f for f in ExtractorRegistry().extract(document_type, _doc(lines))}


def _header(
    tall_text: str = "학성", tails: tuple[str, str] | None = ("번:20201234", "명:김가나다")
) -> list[OCRLine]:
    lines = [_line(tall_text, 1100, 300, 46, 88)]
    if tails:
        lines += [_line(tails[0], 1210, 301, 280, 45), _line(tails[1], 1210, 342, 380, 44)]
    return lines


def test_fused_stacked_label_is_split_and_yields_both_values() -> None:
    fields = _fields(DocumentType.TRANSCRIPT, _header())
    assert fields["student_id"].normalized_value == "20201234"
    assert fields["student_name"].normalized_value == "김가나다"


def test_split_only_when_every_cell_has_a_label_tail() -> None:
    only_one = _header(tails=("번:20201234", "김가나다"))  # second row has no label tail
    assert [i.text for i in split_stacked_label_boxes(only_one)] == [i.text for i in only_one]


def test_split_requires_a_tall_narrow_glyph_column() -> None:
    wide = [_line("학성", 1100, 300, 300, 88)] + _header(tails=("번:20201234", "명:김가나다"))[1:]
    assert split_stacked_label_boxes(wide)[0].text == "학성"
    no_tails = _header(tails=None)
    assert [i.text for i in split_stacked_label_boxes(no_tails)] == ["학성"]


def test_split_leaves_ordinary_two_syllable_words_alone() -> None:
    lines = [
        _line("학교", 100, 100, 130, 60),
        _line("번:1", 300, 100, 80, 60),
        _line("명:2", 300, 170, 80, 60),
    ]
    assert [i.text for i in split_stacked_label_boxes(lines)] == ["학교", "번:1", "명:2"]


def _issuer_row(glyphs: list[str], y: float = 2400) -> list[OCRLine]:
    return [_line(g, 600 + i * 180, y, 110, 105) for i, g in enumerate(glyphs)]


def test_letter_spaced_issuer_row_names_the_university() -> None:
    lines = _issuer_row(["가", "'나", "대", "학", "교", "총"]) + [
        _line("이", 1700, 2420, 90, 80, 0.2)
    ]
    field = _fields(DocumentType.ENROLLMENT_CERTIFICATE, lines)["university_name"]
    assert field.normalized_value == "가나대학교"
    assert (
        len(field.evidence or []) == 6
    )  # evidence points at the real glyph boxes, not the seal noise


def test_issuer_row_with_boxes_of_several_glyphs() -> None:
    lines = [
        _line("가 나 대", 600, 2400, 600, 120, 0.8),
        _line("학교 총", 1190, 2403, 550, 118, 0.7),
        _line("려니", 1734, 2430, 300, 150, 0.2),
    ]
    assert (
        _fields(DocumentType.TRANSCRIPT, lines)["university_name"].normalized_value == "가나대학교"
    )


def test_sentence_about_a_university_is_not_an_issuer_row() -> None:
    lines = [
        _line("우리", 100, 100, 100, 40),
        _line("대학교", 220, 100, 130, 40),
        _line("총장은", 370, 100, 120, 40),
    ]
    assert (
        _fields(DocumentType.ENROLLMENT_CERTIFICATE, lines)["university_name"].normalized_value
        is None
    )


def test_a_name_held_by_one_box_is_never_overridden_by_the_row_assembly() -> None:
    row = [
        _line("발급", 100, 100, 100, 40),
        _line("가나대학교", 220, 100, 260, 40),
        _line("총장", 500, 100, 100, 40),
    ]
    assert (
        _fields(DocumentType.ENROLLMENT_CERTIFICATE, row)["university_name"].normalized_value
        == "가나대학교"
    )


def test_serial_number_in_the_title_band_does_not_unsettle_the_title() -> None:
    page = OCRPage(
        1,
        "",
        [_line("제2026-0000001호", 270, 260, 360, 42), _line("성 적 증 명 서", 820, 178, 926, 128)],
        0.99,
    )
    assert assess_title([page], DocumentType.TRANSCRIPT, []).established


def test_other_hangul_before_the_title_still_blocks_it() -> None:
    page = OCRPage(
        1,
        "",
        [
            _line("제2026-0000001호", 270, 260, 360, 42),
            _line("사본", 700, 250, 100, 60),
            _line("성 적 증 명 서", 820, 178, 926, 128),
        ],
        0.99,
    )
    assert not assess_title([page], DocumentType.TRANSCRIPT, []).established


def _title_page(extra: list[OCRLine], source: str = "ocr") -> OCRPage:
    glyphs = [_line(g, 480 + i * 170, 335, 70, 69, 0.99) for i, g in enumerate("재학증명서")]
    lines = glyphs + extra + [_line("성", 400, 660, 40, 47), _line("명:김가나", 630, 660, 410, 44)]
    return OCRPage(1, assemble_page_text(lines), lines, 0.97, metadata={"source": source})


def _classify(page: OCRPage):
    return DocumentClassifier().classify(denoised_pages([page])[0].text).predicted_type


def test_stray_marks_inside_a_letter_spaced_title_do_not_break_classification() -> None:
    assert _classify(_title_page([])) == DocumentType.ENROLLMENT_CERTIFICATE
    for stray in (_line("\u2212", 745, 359, 21, 25, 0.37), _line("그", 915, 360, 7, 12, 0.12)):
        page = _title_page([stray])
        assert (
            DocumentClassifier().classify(page.text).predicted_type == DocumentType.UNKNOWN
        )  # before
        assert _classify(page) == DocumentType.ENROLLMENT_CERTIFICATE  # after


def test_quote_mark_glued_to_a_title_glyph_is_trimmed() -> None:
    glyphs = [
        _line(g, 480 + i * 170, 335, 70, 69, 0.99)
        for i, g in enumerate(["재", "학", "'증", "명", "서"])
    ]
    page = OCRPage(1, assemble_page_text(glyphs), glyphs, 0.97, metadata={"source": "ocr"})
    assert _classify(page) == DocumentType.ENROLLMENT_CERTIFICATE


def test_a_missing_title_glyph_is_not_invented() -> None:
    glyphs = [
        _line(g, 480 + i * 170, 335, 70, 69, 0.99) for i, g in enumerate(["재", "학", "명", "서"])
    ]
    page = OCRPage(1, assemble_page_text(glyphs), glyphs, 0.97, metadata={"source": "ocr"})
    assert _classify(page) == DocumentType.UNKNOWN


def test_confident_or_large_or_lettered_boxes_are_kept() -> None:
    keep = [
        _line("가", 100, 100, 60, 60, 0.3),
        _line("5", 100, 200, 6, 10, 0.9),
        _line("나", 100, 300, 6, 10, 0.9),
    ]
    kept = denoised_pages(
        [OCRPage(1, "", keep + [_line("본문", 300, 100, 80, 60)], 0.9, metadata={"source": "ocr"})]
    )[0].lines
    assert [item.text for item in kept][:3] == ["가", "5", "나"]


def test_embedded_pdf_text_is_never_denoised() -> None:
    page = _title_page([_line("\u2212", 1171, 359, 21, 25, 0.37)], source="direct_pdf_text")
    assert denoised_pages([page])[0] is page


def test_stray_ascii_specks_on_issuer_glyph_boxes_are_ignored() -> None:
    lines = [
        _line("가", 600, 2400, 110, 105),
        _line("1나", 780, 2400, 150, 105, 0.6),
        _line("대", 1000, 2400, 110, 105),
        _line("학", 1180, 2400, 110, 105),
        _line("교", 1360, 2400, 110, 105),
        _line("5총", 1540, 2400, 150, 105, 0.6),
    ]
    assert (
        _fields(DocumentType.ENROLLMENT_CERTIFICATE, lines)["university_name"].normalized_value
        == "가나대학교"
    )
    ascii_name = [
        _line("KAIST", 600, 2400, 300, 105),
        _line("대학교", 940, 2400, 300, 105),
        _line("총장", 1300, 2400, 200, 105),
    ]
    assert _fields(DocumentType.ENROLLMENT_CERTIFICATE, ascii_name)[
        "university_name"
    ].normalized_value in ("KAIST대학교", None)


def test_overlapping_boxes_that_read_the_same_glyph_twice_do_not_repeat_it() -> None:
    lines = [
        _line("가 나 대", 600, 2400, 600, 120),
        _line("대학교 총", 900, 2403, 600, 118),
    ]  # boxes overlap by 300 px
    assert (
        _fields(DocumentType.TRANSCRIPT, lines)["university_name"].normalized_value == "가나대학교"
    )
    apart = [
        _line("가 나 대", 600, 2400, 400, 120),
        _line("대학교 총", 1100, 2403, 600, 118),
    ]  # a real gap: nothing dropped
    # no overlap: the text is kept as read (a repeated glyph there is not an overlap artefact)
    assert (
        _fields(DocumentType.TRANSCRIPT, apart)["university_name"].normalized_value
        == "가나대대학교"
    )
