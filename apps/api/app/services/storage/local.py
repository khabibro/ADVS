import hashlib
import math
import re
import unicodedata
import uuid
import warnings
from pathlib import Path

import fitz
from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import Settings
from app.core.errors import ApiErrorCode, api_error

ALLOWED_MIME = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    # WebP is what browsers produce for screenshots and what most Android
    # capture/share flows emit. Rejecting it means a user holding a perfectly
    # ordinary certificate file cannot upload it at all, so the allowlist has
    # to cover the formats users actually have.
    "image/webp",
}
ALLOWED_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
CANONICAL_MIME = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def canonical_mime(storage_key: str) -> str:
    """Only call for a storage key whose signature and decoder were validated."""
    return CANONICAL_MIME[Path(storage_key).suffix.lower()]


def detected_mime(path: Path) -> str:
    """Server byte detection, including older rows with client MIME metadata."""
    with path.open("rb") as stream:
        header = stream.read(12)
    for extension, mime in CANONICAL_MIME.items():
        if _matches_signature(header, extension):
            return mime
    raise api_error(ApiErrorCode.INVALID_FILE_TYPE, "Unrecognized file signature.")


# File signature (magic bytes) per extension. Client-supplied extension and
# Content-Type are hints only; the bytes on disk are what we trust.
_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF-",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    # WebP is a RIFF container: "RIFF" .... "WEBP". The four size bytes in
    # between are the only variable part, so the check needs both markers.
    ".webp": (b"RIFF",),
}
_MAX_SIGNATURE_BYTES = 12


def sanitize_filename(name: str) -> str:
    stem = unicodedata.normalize("NFC", Path(name).name)
    # Storage uses a generated UUID. This value is only the safe display name,
    # so retain Korean and other Unicode letters while stripping controls and
    # filesystem-hostile punctuation.
    stem = "".join(character for character in stem if unicodedata.category(character)[0] != "C")
    return re.sub(r'[\\/:*?"<>|]', "_", stem).strip(". ")[:160] or "upload"


def _matches_signature(header: bytes, ext: str) -> bool:
    if ext == ".webp":
        # RIFF is shared with WAV/AVI, so the "WEBP" form tag is what makes the
        # container an image we can decode.
        return header.startswith(b"RIFF") and header[8:12] == b"WEBP"
    signatures = _SIGNATURES.get(ext, ())
    return any(header.startswith(sig) for sig in signatures)


class LocalStorageService:
    def __init__(self, settings: Settings):
        self.root = settings.storage_path
        self.max_size = settings.max_upload_size_bytes
        self.max_pdf_pages = settings.max_pdf_pages
        self.settings = settings
        self.root.mkdir(parents=True, exist_ok=True)

    async def save_upload(self, file: UploadFile) -> tuple[str, int, str]:
        original = sanitize_filename(file.filename or "upload")
        ext = Path(original).suffix.lower()
        if ext not in ALLOWED_EXT:
            raise api_error(
                ApiErrorCode.INVALID_FILE_TYPE, "PDF, PNG, JPG, JPEG and WebP files are supported."
            )
        storage_key = f"{uuid.uuid4()}{ext}"
        path = self.root / storage_key
        digest = hashlib.sha256()
        size = 0
        header = b""
        try:
            with path.open("wb") as out:
                while chunk := await file.read(1024 * 1024):
                    header = (header + chunk)[:_MAX_SIGNATURE_BYTES]
                    size += len(chunk)
                    if size > self.max_size:
                        raise api_error(
                            ApiErrorCode.FILE_TOO_LARGE, "Uploaded file exceeds size limit."
                        )
                    digest.update(chunk)
                    out.write(chunk)
            if size == 0:
                raise api_error(ApiErrorCode.EMPTY_FILE, "Uploaded file is empty.")
            if not _matches_signature(header, ext):
                raise api_error(
                    ApiErrorCode.INVALID_FILE_TYPE, "File content does not match its extension."
                )
            self._validate_decodable(path, ext)
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        return storage_key, size, digest.hexdigest()

    def _validate_decodable(self, path: Path, ext: str) -> None:
        """Confirm the file actually opens as the format it claims to be,
        rejecting corrupt/truncated uploads before they reach the pipeline."""
        try:
            if ext == ".pdf":
                with fitz.open(path) as doc:
                    page_count = doc.page_count
                    if doc.needs_pass or page_count < 1:
                        raise ValueError("Encrypted or empty PDF")
                    for page in doc:
                        width, height = math.ceil(page.rect.width), math.ceil(page.rect.height)
                        if (
                            width < 1
                            or height < 1
                            or max(width, height) > self.settings.max_image_dimension
                        ):
                            raise api_error(
                                ApiErrorCode.PIXEL_BUDGET_EXCEEDED,
                                "PDF page exceeds upload dimension budget.",
                            )
                    if page_count > self.max_pdf_pages:
                        raise api_error(
                            ApiErrorCode.TOO_MANY_PAGES,
                            f"PDF exceeds the maximum of {self.max_pdf_pages} pages.",
                        )
            else:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", Image.DecompressionBombWarning)
                    with Image.open(path) as img:
                        self._validate_dimensions(*img.size)
                        if (
                            img.format
                            != {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP"}[
                                ext
                            ]
                        ):
                            raise ValueError("Decoder format mismatch")
                        if getattr(img, "n_frames", 1) != 1:
                            raise ValueError("Multi-frame image unsupported")
                        img.verify()
                    # verify() checks container integrity; load() additionally
                    # proves the compressed pixel stream can be decoded.
                    with Image.open(path) as img:
                        img.load()
                page_count = 1
        except (
            fitz.FileDataError,
            RuntimeError,
            UnidentifiedImageError,
            OSError,
            ValueError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ) as exc:
            path.unlink(missing_ok=True)
            raise api_error(
                ApiErrorCode.CORRUPT_DOCUMENT, "File could not be opened; it may be corrupt."
            ) from exc
        if ext != ".pdf" and page_count > self.max_pdf_pages:
            path.unlink(missing_ok=True)
            raise api_error(
                ApiErrorCode.TOO_MANY_PAGES,
                f"PDF exceeds the maximum of {self.max_pdf_pages} pages.",
            )

    def _validate_dimensions(self, width: int, height: int) -> None:
        if (
            width < 1
            or height < 1
            or max(width, height) > self.settings.max_image_dimension
            or width * height > self.settings.max_image_pixels
        ):
            raise api_error(
                ApiErrorCode.PIXEL_BUDGET_EXCEEDED, "Page exceeds image dimension/pixel budget."
            )

    def path_for(self, storage_key: str) -> Path:
        path = (self.root / Path(storage_key).name).resolve()
        if self.root.resolve() not in path.parents and path != self.root.resolve():
            raise api_error(ApiErrorCode.INVALID_FILE_TYPE, "Invalid storage key.")
        return path
