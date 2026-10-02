import asyncio
import io
import threading
from pathlib import Path

import fitz
import pytest
from fastapi import HTTPException
from PIL import Image
from starlette.datastructures import Headers, UploadFile

from app.core.config import Settings
from app.core.errors import ProcessingErrorCode
from app.document_intelligence.ocr.models import OCRProviderError
from app.document_intelligence.ocr.providers import PaddleOCRProvider
from app.document_intelligence.ocr.worker import run_ocr
from app.services.storage.local import LocalStorageService, canonical_mime, detected_mime


def upload(data, filename, mime):
    return UploadFile(
        file=io.BytesIO(data), filename=filename, headers=Headers({"content-type": mime})
    )


def png(size=(10, 10)):
    buffer = io.BytesIO()
    Image.new("RGB", size, "white").save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_server_type_overrides_incorrect_client_mime(tmp_path):
    storage = LocalStorageService(Settings(storage_path=tmp_path))
    with fitz.open() as pdf:
        pdf.new_page()
        content = pdf.tobytes()
    key, _, _ = await storage.save_upload(upload(content, "sample.pdf", "image/png"))
    assert detected_mime(storage.path_for(key)) == "application/pdf"
    assert canonical_mime(key) == "application/pdf"
    key, _, _ = await storage.save_upload(upload(png(), "sample.png", "application/octet-stream"))
    assert detected_mime(storage.path_for(key)) == "image/png"


@pytest.mark.asyncio
async def test_renamed_image_and_over_budget_image_leave_no_orphans(tmp_path):
    storage = LocalStorageService(Settings(storage_path=tmp_path, max_image_pixels=99))
    for name, code in [
        ("sample.pdf", "INVALID_FILE_TYPE"),
        ("sample.png", "PIXEL_BUDGET_EXCEEDED"),
    ]:
        with pytest.raises(HTTPException) as failure:
            await storage.save_upload(upload(png(), name, "application/pdf"))
        assert failure.value.detail["code"] == code
        assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_pdf_upload_validation_is_independent_from_ocr_render_budget(tmp_path):
    storage = LocalStorageService(Settings(storage_path=tmp_path, max_pdf_render_pixels=100))
    with fitz.open() as pdf:
        pdf.new_page()
        content = pdf.tobytes()
        encrypted = pdf.tobytes(
            encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="synthetic", user_pw="synthetic"
        )
    key, _, _ = await storage.save_upload(upload(content, "sample.pdf", "application/pdf"))
    assert storage.path_for(key).exists()
    with pytest.raises(HTTPException) as failure:
        await storage.save_upload(upload(encrypted, "sample.pdf", "application/pdf"))
    assert failure.value.detail["code"] == "CORRUPT_DOCUMENT"


@pytest.mark.asyncio
async def test_interrupted_upload_cleans_partial_file(tmp_path):
    storage = LocalStorageService(Settings(storage_path=tmp_path))

    class Interrupted:
        filename = "sample.png"
        content_type = "image/png"
        reads = 0

        async def read(self, _):
            self.reads += 1
            if self.reads == 1:
                return png()
            raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await storage.save_upload(Interrupted())
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_pdf_streams_single_temporary_page_and_cleans_on_error(tmp_path):
    source = tmp_path / "multi.pdf"
    with fitz.open() as pdf:
        for _ in range(3):
            pdf.new_page(width=50, height=50)
        pdf.save(source)
    provider = PaddleOCRProvider(Settings(paddle_ocr_doc_orientation=False))
    observed = []

    class Engine:
        def predict(self, filename):
            page = Path(filename)
            assert len(list(page.parent.iterdir())) == 1
            observed.append(page)
            if len(observed) == 2:
                raise RuntimeError("synthetic engine failure")
            return [
                {
                    "text": "synthetic",
                    "confidence": 0.0,
                    "poly": [[0, 0], [40, 1], [39, 20], [1, 19]],
                }
            ]

    provider.__dict__["_engine"] = Engine()
    with pytest.raises(OCRProviderError):
        await provider.extract_document(source, "application/pdf")
    assert len(observed) == 2
    assert all(not page.parent.exists() for page in observed)


def test_provider_retains_zero_confidence_polygon_and_missing_metadata():
    provider = PaddleOCRProvider(Settings())
    polygon = [[0, 0], [40, 1], [39, 20], [1, 19]]
    page = provider._normalize_page(
        [{"text": "synthetic", "confidence": 0.0, "poly": polygon}], 1, 0
    )
    assert page.lines[0].confidence == 0.0
    assert page.lines[0].polygon == tuple(tuple(point) for point in polygon)
    # Absence of a provider score must not erase otherwise observable text.
    page = provider._normalize_page({"rec_texts": ["synthetic"]}, 1, 0)
    assert page.text == "synthetic"
    assert page.lines[0].confidence is None
    assert page.lines[0].polygon is None


@pytest.mark.asyncio
async def test_timeout_waits_for_worker_recovery_without_terminal_busy():
    entered, release, exited = threading.Event(), threading.Event(), threading.Event()

    def slow():
        entered.set()
        try:
            release.wait(3)
        finally:
            exited.set()

    task = asyncio.create_task(run_ocr(slow, 0.05))
    try:
        assert await asyncio.to_thread(entered.wait, 1)
        # This coroutine runs while native OCR is still blocked.
        assert not task.done()
        with pytest.raises(OCRProviderError) as timeout:
            await task
        assert timeout.value.code == ProcessingErrorCode.OCR_TIMEOUT
        second = asyncio.create_task(run_ocr(lambda: "after", 1))
        await asyncio.sleep(0)
        assert not second.done()
        release.set()
        assert await asyncio.to_thread(exited.wait, 1)
        assert await second == "after"
    finally:
        release.set()


@pytest.mark.asyncio
async def test_provider_cache_respects_render_configuration():
    from app.document_intelligence.ocr.providers import get_ocr_provider

    first = get_ocr_provider(Settings(ocr_provider="paddle", paddle_ocr_render_dpi=180))
    second = get_ocr_provider(Settings(ocr_provider="paddle", paddle_ocr_render_dpi=288))
    assert first.render_scale != second.render_scale
