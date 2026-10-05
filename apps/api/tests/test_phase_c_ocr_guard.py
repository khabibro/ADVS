"""Phase C: per-page render DPI metadata (F-005) and the production guard
against the mock OCR provider (F-006). Hold-out values only."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import fitz
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.document_intelligence.ocr.providers import PaddleOCRProvider

# ------------------------------------------------------------ C-4 / F-005


def _pdf_with_page_box_and_raster(
    directory: Path, page_points: tuple[float, float], raster_px: tuple[int, int]
) -> Path:
    path = directory / "scan.pdf"
    document = fitz.open()
    page = document.new_page(width=page_points[0], height=page_points[1])
    image = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, *raster_px), False)
    image.set_rect(image.irect, (255, 255, 255))
    page.insert_image(page.rect, pixmap=image)
    document.save(path)
    document.close()
    return path


def test_downscaled_page_reports_its_real_render_dpi() -> None:
    settings = Settings(ocr_provider="paddle")
    provider = PaddleOCRProvider(settings)
    provider._predict = lambda image_path, orientation=False: [  # type: ignore[method-assign]
        {"text": "확인", "confidence": 0.99, "poly": [[0, 0], [10, 0], [10, 10], [0, 10]]}
    ]

    with tempfile.TemporaryDirectory() as directory:
        # A 3x-A4 page box wrapping a 72 DPI raster: rendered at its own 72 DPI,
        # not at the configured 288.
        path = _pdf_with_page_box_and_raster(Path(directory), (1117.0, 1408.0), (1117, 1408))
        pages = asyncio.run(provider._extract_document(path, "application/pdf"))

    meta = pages[0].metadata
    assert meta["transform"]["render_scale_reason"] == "source_resolution_fit"
    assert meta["render_dpi"] == meta["transform"]["effective_render_dpi"]
    assert meta["render_dpi"] < settings.paddle_ocr_render_dpi


def test_page_at_configured_dpi_reports_configured_dpi() -> None:
    settings = Settings(ocr_provider="paddle")
    provider = PaddleOCRProvider(settings)
    provider._predict = lambda image_path, orientation=False: [  # type: ignore[method-assign]
        {"text": "확인", "confidence": 0.99, "poly": [[0, 0], [10, 0], [10, 10], [0, 10]]}
    ]
    with tempfile.TemporaryDirectory() as directory:
        path = _pdf_with_page_box_and_raster(Path(directory), (595.0, 842.0), (1653, 2338))
        pages = asyncio.run(provider._extract_document(path, "application/pdf"))
    assert pages[0].metadata["render_dpi"] == int(72 * provider.render_scale)


# ------------------------------------------------------------ C-5 / F-006


@pytest.mark.parametrize("env", ["production", "Production", "prod", " PRODUCTION "])
def test_mock_ocr_is_refused_in_production(env: str) -> None:
    with pytest.raises(ValidationError, match="mock"):
        Settings(app_env=env, ocr_provider="mock")


@pytest.mark.parametrize(
    ("env", "provider"),
    [
        ("production", "paddle"),
        ("development", "mock"),
        ("test", "mock"),
        ("staging", "mock"),
        ("development", "paddle"),
    ],
)
def test_other_environment_provider_combinations_are_allowed(env: str, provider: str) -> None:
    assert Settings(app_env=env, ocr_provider=provider).ocr_provider == provider
