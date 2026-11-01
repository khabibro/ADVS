"""Phone photos (iPhone HDR = MPO with a gain map, GPS-tagged, EXIF-rotated, large) are accepted,
stored without location/device metadata, and read upright. All inputs are synthetic."""

import io
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from PIL import Image, ImageChops, ImageOps
from sqlalchemy import select
from starlette.datastructures import Headers, UploadFile

from app.core.config import Settings
from app.document_intelligence.preprocessing.processor import ImagePreprocessor
from app.models.entities import Checklist
from app.services import pages
from app.services.storage.local import LocalStorageService, canonical_mime
from app.services.storage.sanitize import ImageSanitizeError, strip_jpeg_metadata

SEED = Path(__file__).resolve().parents[3] / "scripts" / "seed.py"
LAT, LON = (37.0, 33.0, 12.0), (127.0, 1.0, 30.0)


def _picture(width: int = 300, height: int = 200) -> Image.Image:
    """A page-like synthetic picture with an asymmetric marker so orientation is checkable."""
    image = Image.new("RGB", (width, height), "white")
    for x in range(width):
        for y in range(0, height, 7):
            image.putpixel((x, y), (x % 256, 40, 90))
    for x in range(20):
        for y in range(10):
            image.putpixel((x, y), (255, 0, 0))  # red block at the top-left
    return image


def _exif(orientation: int = 1, *, gps: bool = True) -> Image.Exif:
    exif = Image.Exif()
    exif[274] = orientation
    exif[271] = "SyntheticPhone"
    exif[272] = "Model-X"
    exif[306] = "2026:10:30 21:31:12"
    if gps:
        ifd = exif.get_ifd(0x8825)
        ifd[1], ifd[2], ifd[3], ifd[4] = "N", LAT, "E", LON
    return exif


def _jpeg(image: Image.Image, **kwargs) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90, **kwargs)
    return buffer.getvalue()


def _mpo(image: Image.Image, exif: Image.Exif) -> bytes:
    gain_map = Image.new("L", (image.width // 4, image.height // 4), 128)
    buffer = io.BytesIO()
    image.save(buffer, format="MPO", save_all=True, append_images=[gain_map], exif=exif, quality=90)
    return buffer.getvalue()


def _upload(name: str, content: bytes) -> UploadFile:
    return UploadFile(
        file=io.BytesIO(content), filename=name, headers=Headers({"content-type": "image/jpeg"})
    )


def _service(tmp_path, **overrides) -> LocalStorageService:
    return LocalStorageService(Settings(storage_path=tmp_path / "storage", **overrides))


def _has_private_metadata(path) -> bool:
    raw = path.read_bytes()
    with Image.open(path) as image:
        exif = image.getexif()
        return (
            bool(exif) or "xmp" in image.info or b"Exif\x00\x00" in raw or b"SyntheticPhone" in raw
        )


def test_fixture_is_really_an_mpo_with_two_frames() -> None:
    data = _mpo(_picture(), _exif())
    with Image.open(io.BytesIO(data)) as image:
        assert image.format == "MPO"
        assert image.n_frames == 2


@pytest.mark.asyncio
async def test_mpo_with_gain_map_is_accepted_and_only_the_primary_frame_is_kept(tmp_path) -> None:
    service = _service(tmp_path)
    original = _picture()
    key, size, checksum = await service.save_upload(_upload("IMG_1.jpg", _mpo(original, _exif())))
    stored = service.path_for(key)
    assert key.endswith(".jpg") and canonical_mime(key) == "image/jpeg"
    assert size == stored.stat().st_size
    assert len(checksum) == 64
    with Image.open(stored) as image:
        assert image.format == "JPEG"  # no longer an MPO
        assert getattr(image, "n_frames", 1) == 1
        assert image.size == original.size
        assert image.getexif().get(274, 1) == 1
    assert b"\xff\xd8" in stored.read_bytes()[:2]
    assert stored.read_bytes().count(b"\xff\xd9") >= 1


@pytest.mark.asyncio
async def test_gps_and_device_metadata_are_removed_from_the_stored_copy(tmp_path) -> None:
    service = _service(tmp_path)
    upload_bytes = _jpeg(_picture(), exif=_exif())
    with Image.open(io.BytesIO(upload_bytes)) as received:
        assert received.getexif().get_ifd(0x8825)  # the synthetic upload does carry GPS
    key, _, _ = await service.save_upload(_upload("gps.jpg", upload_bytes))
    stored = service.path_for(key)
    assert not _has_private_metadata(stored)
    with Image.open(stored) as image:
        assert not image.getexif().get_ifd(0x8825)
        assert image.info.get("exif") is None


@pytest.mark.asyncio
async def test_unrotated_jpeg_pixels_are_not_recompressed(tmp_path) -> None:
    service = _service(tmp_path)
    data = _jpeg(_picture(), exif=_exif())
    key, _, _ = await service.save_upload(_upload("plain.jpg", data))
    with Image.open(io.BytesIO(data)) as before, Image.open(service.path_for(key)) as after:
        assert ImageChops.difference(before.convert("RGB"), after.convert("RGB")).getbbox() is None


@pytest.mark.asyncio
async def test_large_photo_is_stored_at_full_size_not_downscaled(tmp_path) -> None:
    service = _service(tmp_path)
    large = Image.new("RGB", (5000, 4000), (230, 230, 230))  # 20 MP, inside the 25 MP budget
    key, _, _ = await service.save_upload(_upload("big.jpg", _jpeg(large, exif=_exif())))
    with Image.open(service.path_for(key)) as stored:
        assert stored.size == (5000, 4000)


@pytest.mark.asyncio
async def test_photo_over_the_pixel_budget_is_still_refused(tmp_path) -> None:
    service = _service(tmp_path, max_image_pixels=10_000)
    with pytest.raises(HTTPException) as failure:
        await service.save_upload(_upload("big.jpg", _jpeg(_picture(300, 200))))
    assert failure.value.detail["code"] == "PIXEL_BUDGET_EXCEEDED"
    assert not list((tmp_path / "storage").iterdir())


@pytest.mark.asyncio
@pytest.mark.parametrize("orientation", [3, 6, 8])
async def test_exif_rotated_jpeg_is_stored_upright_without_orientation_or_metadata(
    tmp_path, orientation
) -> None:
    service = _service(tmp_path)
    data = _jpeg(_picture(), exif=_exif(orientation))
    key, _, _ = await service.save_upload(_upload("rot.jpg", data))
    stored = service.path_for(key)
    assert key.endswith(".png") and canonical_mime(key) == "image/png"
    with Image.open(io.BytesIO(data)) as source:
        expected = ImageOps.exif_transpose(source).convert("RGB")
    with Image.open(stored) as image:
        assert image.size == expected.size
        assert ImageChops.difference(image.convert("RGB"), expected).getbbox() is None
        assert not image.getexif()
    assert not _has_private_metadata(stored)
    assert [p.name for p in (tmp_path / "storage").iterdir()] == [key]  # the sideways file is gone


@pytest.mark.asyncio
async def test_derived_images_carry_no_location_data(tmp_path, monkeypatch) -> None:
    service = _service(tmp_path)
    key, _, _ = await service.save_upload(_upload("rot.jpg", _jpeg(_picture(), exif=_exif(6))))
    stored = service.path_for(key)
    document = SimpleNamespace(storage_key=key, mime_type=canonical_mime(key))
    monkeypatch.setattr(pages, "_path", lambda _document: stored)
    rendered = pages.render_page_png(document, 1)
    assert rendered is not None
    with Image.open(io.BytesIO(rendered)) as image:
        assert not image.getexif() and b"SyntheticPhone" not in rendered
    # the OCR copy made from a raw, still-tagged phone file is clean too
    raw = tmp_path / "raw.jpg"
    raw.write_bytes(_jpeg(_picture(), exif=_exif(6)))
    prepared = ImagePreprocessor().prepare(raw, tmp_path / "prepared")
    assert prepared is not None and not _has_private_metadata(prepared)


@pytest.mark.asyncio
async def test_truncated_jpeg_is_reported_as_corrupt(tmp_path) -> None:
    service = _service(tmp_path)
    data = _jpeg(_picture(), exif=_exif())
    with pytest.raises(HTTPException) as failure:
        await service.save_upload(_upload("cut.jpg", data[: len(data) // 2]))
    assert failure.value.detail["code"] == "CORRUPT_DOCUMENT"
    with pytest.raises(HTTPException) as failure:
        await service.save_upload(_upload("junk.jpg", b"\xff\xd8\xff" + b"not an image" * 20))
    assert failure.value.detail["code"] == "CORRUPT_DOCUMENT"
    assert not list((tmp_path / "storage").iterdir())


@pytest.mark.asyncio
async def test_unsupported_formats_get_their_own_codes(tmp_path) -> None:
    service = _service(tmp_path)
    heic = b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic" + b"\x00" * 40
    cases = [
        ("IMG_1.HEIC", heic, "HEIC_NOT_SUPPORTED"),
        ("renamed.jpg", heic, "HEIC_NOT_SUPPORTED"),
        ("anim.gif", b"GIF89a" + b"\x00" * 30, "INVALID_FILE_TYPE"),
        ("renamed.jpg", b"GIF89a" + b"\x00" * 30, "INVALID_FILE_TYPE"),
        ("scan.tiff", b"II*\x00" + b"\x00" * 30, "INVALID_FILE_TYPE"),
    ]
    for name, content, code in cases:
        with pytest.raises(HTTPException) as failure:
            await service.save_upload(_upload(name, content))
        assert failure.value.detail["code"] == code, name
    assert not list((tmp_path / "storage").iterdir())


@pytest.mark.asyncio
async def test_png_with_text_metadata_is_cleaned_and_keeps_its_pixels(tmp_path) -> None:
    from PIL.PngImagePlugin import PngInfo

    service = _service(tmp_path)
    info = PngInfo()
    info.add_text("Location", "37.5,127.0")
    buffer = io.BytesIO()
    _picture().save(buffer, format="PNG", pnginfo=info)
    key, _, _ = await service.save_upload(
        UploadFile(file=io.BytesIO(buffer.getvalue()), filename="a.png", headers=Headers({}))
    )
    stored = service.path_for(key)
    assert b"37.5,127.0" not in stored.read_bytes()
    with Image.open(stored) as after, Image.open(io.BytesIO(buffer.getvalue())) as before:
        assert ImageChops.difference(before.convert("RGB"), after.convert("RGB")).getbbox() is None


def test_strip_keeps_progressive_scans_and_the_icc_profile() -> None:
    profile = b"\x00" * 128
    buffer = io.BytesIO()
    _picture().save(buffer, format="JPEG", progressive=True, icc_profile=profile, exif=_exif())
    cleaned = strip_jpeg_metadata(buffer.getvalue())
    with Image.open(io.BytesIO(cleaned)) as image:
        image.load()
        assert image.info.get("icc_profile") == profile
        assert not image.getexif()
    with Image.open(io.BytesIO(buffer.getvalue())) as a, Image.open(io.BytesIO(cleaned)) as b:
        assert ImageChops.difference(a.convert("RGB"), b.convert("RGB")).getbbox() is None


def test_strip_rejects_non_jpeg_and_truncated_streams() -> None:
    with pytest.raises(ImageSanitizeError):
        strip_jpeg_metadata(b"\x89PNG\r\n")
    with pytest.raises(ImageSanitizeError):
        strip_jpeg_metadata(_jpeg(_picture())[:50])


def test_api_upload_of_an_mpo_photo_is_accepted(client, db_session) -> None:
    runpy.run_path(str(SEED))["main"]()
    workflow = db_session.scalar(select(Checklist).where(Checklist.name == "학생 제출서류 점검"))
    project = client.post(
        "/api/v1/projects", json={"name": "phone", "workflow_id": str(workflow.id)}
    ).json()
    response = client.post(
        f"/api/v1/projects/{project['id']}/documents",
        files={"file": ("IMG_4196.jpg", _mpo(_picture(), _exif()), "image/jpeg")},
    )
    assert response.status_code == 201, response.text
    heic = client.post(
        f"/api/v1/projects/{project['id']}/documents",
        files={"file": ("IMG_1.HEIC", b"\x00\x00\x00\x18ftypheic" + b"\x00" * 40, "image/heic")},
    )
    assert heic.status_code == 400 and heic.json()["detail"]["code"] == "HEIC_NOT_SUPPORTED"
