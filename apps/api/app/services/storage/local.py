import hashlib
import re
import uuid
from pathlib import Path

import fitz
from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import Settings
from app.core.errors import ApiErrorCode, api_error

ALLOWED_MIME = {"application/pdf", "image/png", "image/jpeg"}
ALLOWED_EXT = {".pdf", ".png", ".jpg", ".jpeg"}

# File signature (magic bytes) per extension. Client-supplied extension and
# Content-Type are hints only; the bytes on disk are what we trust.
_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF-",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
}
_MAX_SIGNATURE_BYTES = 8


def sanitize_filename(name: str) -> str:
    stem = Path(name).name
    return re.sub(r"[^A-Za-z0-9._-]", "_", stem)[:160] or "upload"


def _matches_signature(header: bytes, ext: str) -> bool:
    signatures = _SIGNATURES.get(ext, ())
    return any(header.startswith(sig) for sig in signatures)


class LocalStorageService:
    def __init__(self, settings: Settings):
        self.root = settings.storage_path
        self.max_size = settings.max_upload_size_bytes
        self.max_pdf_pages = settings.max_pdf_pages
        self.root.mkdir(parents=True, exist_ok=True)

    async def save_upload(self, file: UploadFile) -> tuple[str, int, str]:
        original = sanitize_filename(file.filename or "upload")
        ext = Path(original).suffix.lower()
        if ext not in ALLOWED_EXT or file.content_type not in ALLOWED_MIME:
            raise api_error(
                ApiErrorCode.INVALID_FILE_TYPE, "PDF, PNG, JPG, JPEG files are supported."
            )
        storage_key = f"{uuid.uuid4()}{ext}"
        path = self.root / storage_key
        digest = hashlib.sha256()
        size = 0
        header = b""
        with path.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                if not header:
                    header = chunk[:_MAX_SIGNATURE_BYTES]
                size += len(chunk)
                if size > self.max_size:
                    path.unlink(missing_ok=True)
                    raise api_error(
                        ApiErrorCode.FILE_TOO_LARGE, "Uploaded file exceeds size limit."
                    )
                digest.update(chunk)
                out.write(chunk)
        if size == 0:
            path.unlink(missing_ok=True)
            raise api_error(ApiErrorCode.EMPTY_FILE, "Uploaded file is empty.")
        if not _matches_signature(header, ext):
            path.unlink(missing_ok=True)
            raise api_error(
                ApiErrorCode.INVALID_FILE_TYPE, "File content does not match its extension."
            )
        self._validate_decodable(path, ext)
        return storage_key, size, digest.hexdigest()

    def _validate_decodable(self, path: Path, ext: str) -> None:
        """Confirm the file actually opens as the format it claims to be,
        rejecting corrupt/truncated uploads before they reach the pipeline."""
        try:
            if ext == ".pdf":
                with fitz.open(path) as doc:
                    page_count = doc.page_count
            else:
                with Image.open(path) as img:
                    img.verify()
                page_count = 1
        except (fitz.FileDataError, RuntimeError, UnidentifiedImageError, OSError) as exc:
            path.unlink(missing_ok=True)
            raise api_error(
                ApiErrorCode.CORRUPT_DOCUMENT, "File could not be opened; it may be corrupt."
            ) from exc
        if page_count > self.max_pdf_pages:
            path.unlink(missing_ok=True)
            raise api_error(
                ApiErrorCode.TOO_MANY_PAGES,
                f"PDF exceeds the maximum of {self.max_pdf_pages} pages.",
            )

    def path_for(self, storage_key: str) -> Path:
        path = (self.root / Path(storage_key).name).resolve()
        if self.root.resolve() not in path.parents and path != self.root.resolve():
            raise api_error(ApiErrorCode.INVALID_FILE_TYPE, "Invalid storage key.")
        return path
