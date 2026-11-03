"""Privacy clean-up of an uploaded image before ADVS keeps it.

A phone photo carries a GPS position, a timestamp, the device model and often a
thumbnail of the same picture inside its metadata. None of that is needed to
read a certificate, so the copy ADVS stores has none of it. Two more phone
specifics are handled here:

* an iPhone HDR photo is an MPO file: the picture followed by a second embedded
  image (the gain map). Only the first image is the photograph; the rest is
  dropped;
* EXIF orientation is applied to the pixels first, so a portrait photo stored
  sideways is stored upright and carries no orientation tag afterwards.

The pixels are never changed when no rotation is needed: a JPEG is cleaned by
removing metadata segments, not by decoding and encoding it again. A rotated
photo is stored losslessly as PNG, so there is no second compression
generation. Downscaling for OCR happens later, on a temporary copy only.

The upload checksum is computed by the caller on the bytes as received, so
duplicate detection is unaffected.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

_SOI = b"\xff\xd8"
_EOI = 0xD9
_SOS = 0xDA
#: Segments that carry pixels or what is needed to decode them are kept; metadata is dropped.
_APP1, _APP2, _APP14, _COM = 0xE1, 0xE2, 0xEE, 0xFE
_APP_RANGE = range(0xE0, 0xF0)
_ICC = b"ICC_PROFILE\x00"
_ADOBE = b"Adobe"

_PNG_BENIGN_INFO = {
    "dpi",
    "gamma",
    "icc_profile",
    "srgb",
    "transparency",
    "aspect",
    "chromaticity",
    "interlace",
}


class ImageSanitizeError(ValueError):
    """The bytes are not a JPEG stream this module can walk (treated as corrupt)."""


def strip_jpeg_metadata(data: bytes) -> bytes:
    """Return the first image of a JPEG/MPO stream without EXIF, XMP, GPS, comments,
    multi-picture data or trailing bytes. ICC colour profile, JFIF and Adobe markers
    (which the decoder needs for some colour spaces) are kept. Pixel data is copied
    byte for byte."""
    if not data.startswith(_SOI):
        raise ImageSanitizeError("not a JPEG")
    out = bytearray(_SOI)
    pos = 2
    size = len(data)
    while pos < size:
        if data[pos] != 0xFF:
            raise ImageSanitizeError("marker expected")
        while pos < size and data[pos] == 0xFF:  # fill bytes before a marker
            pos += 1
        if pos >= size:
            break
        marker = data[pos]
        pos += 1
        if marker == _EOI:
            out += b"\xff\xd9"
            return bytes(out)
        if marker == 0x01 or 0xD0 <= marker <= 0xD7:  # standalone markers, no length
            out += bytes((0xFF, marker))
            continue
        if pos + 2 > size:
            raise ImageSanitizeError("truncated segment length")
        length = int.from_bytes(data[pos : pos + 2], "big")
        end = pos + length
        if length < 2 or end > size:
            raise ImageSanitizeError("truncated segment")
        payload = data[pos + 2 : end]
        keep = True
        if marker in _APP_RANGE:
            keep = (
                marker == 0xE0
                or (marker == _APP2 and payload.startswith(_ICC))
                or (marker == _APP14 and payload.startswith(_ADOBE))
            )
        elif marker == _COM:
            keep = False
        if keep:
            out += bytes((0xFF, marker)) + data[pos:end]
        pos = end
        if marker == _SOS:
            # Entropy-coded data runs until the next marker that is not a stuffed
            # 0xFF00 or a restart marker; copy it unchanged.
            start = pos
            while pos < size - 1:
                if (
                    data[pos] == 0xFF
                    and data[pos + 1] != 0x00
                    and not (0xD0 <= data[pos + 1] <= 0xD7)
                ):
                    if data[pos + 1] == 0xFF:  # fill byte
                        pos += 1
                        continue
                    break
                pos += 1
            else:
                pos = size
            out += data[start:pos]
    raise ImageSanitizeError("no end-of-image marker")


def _icc(image: Image.Image) -> bytes | None:
    profile = image.info.get("icc_profile")
    return profile if isinstance(profile, bytes) and profile else None


def _orientation(image: Image.Image) -> int:
    try:
        return int(image.getexif().get(274, 1) or 1)
    except (TypeError, ValueError):
        return 1


def sanitize_stored_image(path: Path, *, extension: str) -> Path:
    """Clean the stored file at `path` in place and return its final path.

    The returned path differs from `path` only when a rotated photo is re-stored as
    PNG (the old file is removed). Raises ImageSanitizeError or OSError for a file
    that cannot be processed (the caller reports it as corrupt)."""
    if extension in (".jpg", ".jpeg"):
        with Image.open(path) as image:
            orientation = _orientation(image)
            if orientation != 1:
                upright = ImageOps.exif_transpose(image).convert("RGB")
                profile = _icc(image)
                target = path.with_suffix(".png")
                upright.save(target, format="PNG", icc_profile=profile)
                path.unlink(missing_ok=True)
                return target
        path.write_bytes(strip_jpeg_metadata(path.read_bytes()))
        return path
    with Image.open(path) as image:
        orientation = _orientation(image)
        carries_metadata = (
            bool(image.getexif())
            or "xmp" in image.info
            or any(key not in _PNG_BENIGN_INFO for key in image.info if extension == ".png")
            or (extension == ".webp" and ("exif" in image.info or "xmp" in image.info))
        )
        if orientation != 1:
            upright = ImageOps.exif_transpose(image)
            target = path.with_suffix(".png")
            upright.save(target, format="PNG", icc_profile=_icc(image))
            if target != path:
                path.unlink(missing_ok=True)
            return target
        if not carries_metadata:
            return path
        image.load()
        profile = _icc(image)
        transparency = image.info.get("transparency")
        clean = image.copy()
    if extension == ".png":
        extra = {"transparency": transparency} if transparency is not None else {}
        clean.save(path, format="PNG", icc_profile=profile, **extra)
    else:
        clean.save(path, format="WEBP", lossless=True, icc_profile=profile)
    return path
