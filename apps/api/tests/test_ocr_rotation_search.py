"""Rotation by OCR evidence: pure scoring and the provider's search on synthetic pages."""

import pytest
from PIL import Image, ImageDraw

from app.document_intelligence.ocr import orientation as rotation_scoring
from app.document_intelligence.ocr.models import OCRLine
from app.document_intelligence.ocr.providers import PaddleOCRProvider
from tests.test_ocr_provider import make_settings

_GOOD = [
    ([[0, 0], [100, 0], [100, 20], [0, 20]], ("재학증명서", 0.97)),
    ([[0, 30], [100, 30], [100, 50], [0, 50]], ("성명 홍길동 학번 12345", 0.95)),
    ([[0, 60], [100, 60], [100, 80], [0, 80]], ("위의 사실을 증명합니다", 0.96)),
    (
        [[0, 90], [100, 90], [100, 110], [0, 110]],
        ("소속 컴퓨터학부 발급일 2026년 10월 30일 " * 4, 0.95),
    ),
]
_GARBAGE = [
    ([[0, 0], [100, 0], [100, 20], [0, 20]], ("Il1|", 0.41)),
    ([[0, 30], [100, 30], [100, 50], [0, 50]], ("뮈귀됴", 0.52)),
]


def _lines(*items: tuple[str, float]) -> list[OCRLine]:
    return [OCRLine(text=text, confidence=conf) for text, conf in items]


def test_evidence_counts_form_words_and_hangul() -> None:
    evidence = rotation_scoring.evidence_for(_lines(("재학증명서", 0.9), ("성명 학번", 0.9)))
    assert evidence.label_hits >= 3
    assert evidence.hangul_ratio == pytest.approx(1.0)
    assert rotation_scoring.evidence_for([]).label_hits == 0


def test_pick_rotation_prefers_the_rotation_that_reads_words() -> None:
    good = rotation_scoring.evidence_for(_lines(("재학증명서", 0.95), ("성명 학번 발급", 0.95)))
    junk = rotation_scoring.evidence_for(_lines(("뮈귀됴", 0.5)))
    assert rotation_scoring.pick_rotation({0: junk, 90: junk, 180: good, 270: junk}) == 180


def test_pick_rotation_tie_returns_none() -> None:
    same = rotation_scoring.evidence_for(_lines(("재학증명서", 0.95), ("성명", 0.95)))
    assert rotation_scoring.pick_rotation({0: same, 90: same, 180: same, 270: same}) is None
    assert rotation_scoring.pick_rotation({0: rotation_scoring.evidence_for([])}) is None


def test_upright_wins_a_close_call_only_by_default_ordering() -> None:
    upright = rotation_scoring.evidence_for(_lines(("재학증명서", 0.95), ("성명 학번", 0.95)))
    almost = rotation_scoring.evidence_for(_lines(("재학증명서", 0.95), ("성명 학번", 0.94)))
    assert rotation_scoring.pick_rotation({0: upright, 90: almost}) is None


class _MarkerEngine:
    """Reads the page only when the black corner marker is at the top left (i.e. upright)."""

    def __init__(self) -> None:
        self.calls = 0

    def predict(self, path: str) -> object:
        self.calls += 1
        with Image.open(path) as image:
            upright = image.convert("L").getpixel((4, 4)) < 50
        return [_GOOD if upright else _GARBAGE]


def _page(tmp_path, transpose) -> object:
    image = Image.new("RGB", (240, 320), "white")
    ImageDraw.Draw(image).rectangle((0, 0, 12, 12), fill="black")
    if transpose is not None:
        image = image.transpose(transpose)
    path = tmp_path / "page.png"
    image.save(path)
    return path


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("transpose", "expected"),
    [
        (Image.Transpose.ROTATE_270, 90),
        (Image.Transpose.ROTATE_180, 180),
        (Image.Transpose.ROTATE_90, 270),
    ],
)
async def test_rotated_page_is_read_upright(tmp_path, transpose, expected) -> None:
    provider = PaddleOCRProvider(make_settings())
    engine = _MarkerEngine()
    provider.__dict__["_engine"] = engine
    provider.__dict__["_orientation_engine"] = engine
    pages = await provider.extract_document(_page(tmp_path, transpose), "image/png")
    assert "재학증명서" in pages[0].text
    search = pages[0].metadata["transform"]["rotation_search"]
    assert search["chosen"] == expected
    assert pages[0].metadata["transform"]["orientation_degrees"] == expected
    assert search["evidence"][str(expected)]["label_hits"] > search["evidence"]["0"]["label_hits"]


@pytest.mark.asyncio
async def test_upright_page_is_read_once(tmp_path) -> None:
    provider = PaddleOCRProvider(make_settings())
    engine = _MarkerEngine()
    provider.__dict__["_engine"] = engine
    provider.__dict__["_orientation_engine"] = engine
    pages = await provider.extract_document(_page(tmp_path, None), "image/png")
    assert engine.calls == 1
    assert "rotation_search" not in pages[0].metadata["transform"]


@pytest.mark.asyncio
async def test_search_can_be_disabled(tmp_path) -> None:
    provider = PaddleOCRProvider(make_settings(paddle_ocr_rotation_search=False))
    engine = _MarkerEngine()
    provider.__dict__["_engine"] = engine
    provider.__dict__["_orientation_engine"] = engine
    pages = await provider.extract_document(
        _page(tmp_path, Image.Transpose.ROTATE_180), "image/png"
    )
    assert "rotation_search" not in pages[0].metadata["transform"]


@pytest.mark.asyncio
async def test_unreadable_page_keeps_the_first_pass(tmp_path) -> None:
    class Blind:
        def predict(self, path: str) -> object:
            return [_GARBAGE]

    provider = PaddleOCRProvider(make_settings())
    provider.__dict__["_engine"] = Blind()
    provider.__dict__["_orientation_engine"] = Blind()
    pages = await provider.extract_document(
        _page(tmp_path, Image.Transpose.ROTATE_180), "image/png"
    )
    assert pages[0].metadata["transform"]["rotation_search"]["chosen"] is None
    assert pages[0].metadata["transform"].get("orientation_degrees") != 180


class _QuadrantEngine:
    """Reads the page only when the dark marker lies in the upper-left quarter (i.e. upright)."""

    def __init__(self) -> None:
        self.calls = 0

    def predict(self, path: str) -> object:
        self.calls += 1
        with Image.open(path) as image:
            gray = image.convert("L")
            width, height = gray.size
            quarter = gray.crop((0, 0, width // 2, height // 2))
            upright = quarter.getextrema()[0] < 50
        return [_GOOD if upright else _GARBAGE]


def _marked_page(tmp_path, transpose) -> object:
    image = Image.new("RGB", (400, 600), "white")
    ImageDraw.Draw(image).rectangle(
        (100, 150, 130, 180), fill="black"
    )  # inside the centre sample, upper left
    if transpose is not None:
        image = image.transpose(transpose)
    path = tmp_path / "marked.png"
    image.save(path)
    return path


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("transpose", "expected"),
    [
        (Image.Transpose.ROTATE_270, 90),
        (Image.Transpose.ROTATE_180, 180),
        (Image.Transpose.ROTATE_90, 270),
    ],
)
async def test_centre_probe_reaches_the_same_rotation_with_one_full_read(
    tmp_path, transpose, expected
) -> None:
    provider = PaddleOCRProvider(make_settings(paddle_ocr_rotation_probe_fraction=0.6))
    engine = _QuadrantEngine()
    provider.__dict__["_engine"] = engine
    provider.__dict__["_orientation_engine"] = engine
    pages = await provider.extract_document(_marked_page(tmp_path, transpose), "image/png")
    search = pages[0].metadata["transform"]["rotation_search"]
    assert search["chosen"] == expected
    assert search["probe_fraction"] == 0.6
    assert "재학증명서" in pages[0].text
    assert engine.calls == 1 + 4 + 1  # first pass, four samples, full read of the winner


@pytest.mark.asyncio
async def test_centre_probe_keeps_the_first_pass_when_upright_wins(tmp_path) -> None:
    # An upright page that merely looks unread (short text) is probed, found upright and not read again.
    provider = PaddleOCRProvider(make_settings(paddle_ocr_rotation_probe_fraction=0.6, paddle_ocr_doc_orientation=False))
    engine = _QuadrantEngine()
    provider.__dict__["_engine"] = engine
    provider.__dict__["_orientation_engine"] = engine
    short = [([[0, 0], [100, 0], [100, 20], [0, 20]], ("재학증명서", 0.97))]

    class Short(_QuadrantEngine):
        def predict(self, path: str) -> object:
            self.calls += 1
            with Image.open(path) as image:
                gray = image.convert("L")
                quarter = gray.crop((0, 0, gray.size[0] // 2, gray.size[1] // 2))
                return [short if quarter.getextrema()[0] < 50 else _GARBAGE]

    probe_engine = Short()
    provider.__dict__["_engine"] = probe_engine
    provider.__dict__["_orientation_engine"] = probe_engine
    pages = await provider.extract_document(_marked_page(tmp_path, None), "image/png")
    assert pages[0].metadata["transform"]["rotation_search"]["chosen"] == 0
    assert probe_engine.calls == 1 + 4  # no full re-read
