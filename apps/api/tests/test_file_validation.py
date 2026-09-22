import io

import pytest
from fastapi import HTTPException
from starlette.datastructures import Headers, UploadFile

from app.core.config import Settings
from app.document_intelligence.preprocessing.processor import is_meaningful_text
from app.services.storage.local import LocalStorageService, sanitize_filename


def test_sanitize_filename_removes_path() -> None:
    assert sanitize_filename("../../secret.pdf") == "secret.pdf"


def _upload(name: str, content: bytes, content_type: str) -> UploadFile:
    return UploadFile(
        file=io.BytesIO(content),
        filename=name,
        headers=Headers({"content-type": content_type}),
    )


def _service(tmp_path) -> LocalStorageService:
    return LocalStorageService(Settings(storage_path=tmp_path / "storage"))


_VALID_PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>"


@pytest.mark.asyncio
async def test_rejects_content_type_extension_mismatch(tmp_path) -> None:
    service = _service(tmp_path)
    upload = _upload("scan.exe", b"MZ\x90\x00", "application/pdf")
    with pytest.raises(HTTPException) as exc_info:
        await service.save_upload(upload)
    assert exc_info.value.detail["code"] == "INVALID_FILE_TYPE"


@pytest.mark.asyncio
async def test_rejects_magic_byte_mismatch(tmp_path) -> None:
    service = _service(tmp_path)
    # Extension/Content-Type claim PDF, bytes are actually a PNG.
    upload = _upload("fake.pdf", b"\x89PNG\r\n\x1a\nrest", "application/pdf")
    with pytest.raises(HTTPException) as exc_info:
        await service.save_upload(upload)
    assert exc_info.value.detail["code"] == "INVALID_FILE_TYPE"


@pytest.mark.asyncio
async def test_rejects_corrupt_pdf(tmp_path) -> None:
    service = _service(tmp_path)
    upload = _upload("broken.pdf", b"%PDF-1.4\ntruncated garbage", "application/pdf")
    with pytest.raises(HTTPException) as exc_info:
        await service.save_upload(upload)
    assert exc_info.value.detail["code"] == "CORRUPT_DOCUMENT"


@pytest.mark.asyncio
async def test_rejects_empty_file(tmp_path) -> None:
    service = _service(tmp_path)
    upload = _upload("empty.pdf", b"", "application/pdf")
    with pytest.raises(HTTPException) as exc_info:
        await service.save_upload(upload)
    assert exc_info.value.detail["code"] == "EMPTY_FILE"


@pytest.mark.asyncio
async def test_accepts_valid_pdf(tmp_path) -> None:
    service = _service(tmp_path)
    upload = _upload("real.pdf", _VALID_PDF, "application/pdf")
    storage_key, size, checksum = await service.save_upload(upload)
    assert storage_key.endswith(".pdf")
    assert size == len(_VALID_PDF)
    assert len(checksum) == 64


@pytest.mark.asyncio
async def test_rejects_pdf_exceeding_page_limit(tmp_path) -> None:
    settings = Settings(storage_path=tmp_path / "storage", max_pdf_pages=1)
    service = LocalStorageService(settings)
    import fitz

    doc = fitz.open()
    doc.new_page()
    doc.new_page()
    two_page_pdf = doc.tobytes()
    doc.close()
    upload = _upload("two_pages.pdf", two_page_pdf, "application/pdf")
    with pytest.raises(HTTPException) as exc_info:
        await service.save_upload(upload)
    assert exc_info.value.detail["code"] == "TOO_MANY_PAGES"


def test_pdf_text_heuristic_rejects_long_nonsemantic_artifacts() -> None:
    assert not is_meaningful_text("!@#$%^&*()_+{}[]<>?/|~`" * 3)
    assert is_meaningful_text("사업자등록증 상호 한국테크 사업자등록번호 123-45-67890")
