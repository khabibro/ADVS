import math
import os
import tempfile
import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from functools import cached_property, partial
from importlib.metadata import version
from pathlib import Path
from typing import Any

import fitz
from PIL import Image

from app.core.config import Settings
from app.core.errors import ProcessingErrorCode
from app.document_intelligence.ocr.models import BoundingBox, OCRLine, OCRPage, OCRProviderError
from app.document_intelligence.ocr.text_assembly import assemble_page_text
from app.document_intelligence.ocr.worker import run_ocr
from app.document_intelligence.preprocessing.processor import ImagePreprocessor

# Deterministic synthetic fixtures for mock/dev/test use. Selected by a
# filename hint so integration tests can exercise every document type
# through the real upload -> process API without hitting a paid provider.
# Dict order matters: hint lookup is first-substring-match, so a more
# specific key (e.g. "sme_expired") must be listed before a shorter key it
# contains ("sme").
_MOCK_FIXTURES: dict[str, str] = {
    "graduation": (
        "졸업증명서\n성명 홍길동\n대학교 한국대학교\n학과 컴퓨터공학과\n학위 학사\n"
        "졸업일자 2024-02-20\n발급일자 2026-01-10"
    ),
    "career_partial": "경력증명서\n성명 김철수\n회사명 한국테크",
    "career": (
        "경력증명서\n성명 김철수\n회사명 한국테크\n직위 대리\n담당업무 백엔드 개발\n"
        "입사일 2020-03-02\n퇴사일 2023-08-31\n발급일자 2026-01-15"
    ),
    "business": (
        "사업자등록증\n상호 한국테크\n대표자 이영희\n사업자등록번호 123-45-67890\n"
        "사업장 소재지 서울특별시 강남구\n업태 서비스업\n종목 소프트웨어 개발\n개업연월일 2019-05-01"
    ),
    "sme_expired": (
        "중소기업확인서\n기업명 한국테크\n사업자등록번호 123-45-67890\n확인번호 SME-2020-001\n"
        "유효기간 2019-01-01 ~ 2020-01-01\n발급일자 2019-01-01"
    ),
    "sme": (
        "중소기업확인서\n기업명 한국테크\n사업자등록번호 123-45-67890\n확인번호 SME-2026-001\n"
        "유효기간 2026-01-01 ~ 2027-12-31\n발급일자 2026-01-01"
    ),
    "unknown": "회의록\n일시 2026-01-01\n참석자 홍길동, 김철수\n안건 분기 실적 논의",
    "empty": "",
}
_DEFAULT_MOCK_FIXTURE = "graduation"
# Special filename hint that makes the mock provider raise, simulating an
# upstream OCR failure end-to-end without touching a real provider.
_OCR_FAILURE_HINT = "ocr_failure"
_PROVIDER_CACHE: dict[tuple, object] = {}


class OCRProvider(ABC):
    @abstractmethod
    async def extract_document(
        self, path: Path, mime_type: str, original_filename: str = ""
    ) -> list[OCRPage]:
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        raise NotImplementedError


class MockOCRProvider(OCRProvider):
    """Deterministic double exercising the same OCRProvider interface used
    by real OCR. Fixture text is chosen from `original_filename` (falling back to
    the on-disk path name) so tests can deliberately select
    graduation/career/business/sme/unknown/empty content -- this must be the
    *original* upload filename, since storage renames files on disk to a
    UUID for path-safety and would otherwise erase the hint."""

    async def extract_document(
        self, path: Path, mime_type: str, original_filename: str = ""
    ) -> list[OCRPage]:
        name_hint = (original_filename or path.name).lower()
        if _OCR_FAILURE_HINT in name_hint:
            raise OCRProviderError(
                ProcessingErrorCode.OCR_PROVIDER_ERROR, "Simulated OCR failure for testing."
            )
        if path.suffix == ".txt":
            text = path.read_text(encoding="utf-8", errors="ignore")
        else:
            hint = next((key for key in _MOCK_FIXTURES if key in name_hint), None)
            text = _MOCK_FIXTURES[hint or _DEFAULT_MOCK_FIXTURE]
        lines = [
            OCRLine(
                text=line,
                confidence=0.99,
                bounding_box=BoundingBox(x=10.0, y=float(index * 24), width=500.0, height=20.0),
            )
            for index, line in enumerate(text.splitlines())
            if line
        ]
        return [OCRPage(1, text, lines, 0.99, 1, {"provider": "mock", "mock": True})]

    async def health_check(self) -> bool:
        return True


class PaddleOCRProvider(OCRProvider):
    """PaddleOCR adapter.

    Paddle-specific result shapes stay in this class; callers receive the
    same normalized OCRPage/OCRLine structures as the mock provider.
    """

    provider_name = "paddle"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.device = settings.paddle_ocr_device
        self.lang = settings.paddle_ocr_lang
        self.rec_model_name = settings.paddle_ocr_rec_model_name
        self.det_model_name = settings.paddle_ocr_det_model_name
        self.cache_dir = settings.paddle_ocr_cache_dir or None
        self.render_scale = self._render_scale(settings.paddle_ocr_render_dpi)
        self.doc_orientation = settings.paddle_ocr_doc_orientation

    @staticmethod
    def _render_scale(render_dpi: int) -> float:
        """PDF user space is 72 DPI, so a PDF point grid scaled by N renders
        at 72*N DPI. Clamped to a sane band: below ~150 DPI small Hangul
        glyphs and business-number digits degrade badly, and beyond ~400 DPI
        the cost grows quadratically for no measured gain."""
        return max(1.5, min(float(render_dpi) / 72.0, 6.0))

    @cached_property
    def _engine(self) -> Any:
        return self._build_engine(orientation=False)

    @cached_property
    def _orientation_engine(self) -> Any:
        return self._build_engine(orientation=True)

    def _build_engine(self, *, orientation: bool) -> Any:
        if self.cache_dir:
            cache_path = Path(self.cache_dir)
            cache_path.mkdir(parents=True, exist_ok=True)
            os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(cache_path.resolve()))
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise OCRProviderError(
                ProcessingErrorCode.OCR_INITIALIZATION_ERROR,
                "PaddleOCR is not installed. Install the backend paddle extra to use OCR_PROVIDER=paddle.",
            ) from exc

        rec_model_dir = self._cached_model_dir(self.rec_model_name)
        det_model_dir = self._cached_model_dir(self.det_model_name)
        kwargs: dict[str, Any] = {
            "lang": self.lang,
            "device": self.device,
            "text_recognition_model_name": self.rec_model_name,
            "text_recognition_model_dir": rec_model_dir,
            "text_detection_model_name": self.det_model_name,
            "text_detection_model_dir": det_model_dir,
            "use_doc_orientation_classify": orientation,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
        }
        try:
            return PaddleOCR(**kwargs)
        except TypeError:
            # PaddleOCR 2.x/early-3.x compatibility. We still set Korean
            # language explicitly; tests assert the PP-OCRv5 names in the
            # primary path without importing the real dependency.
            legacy_kwargs = {
                "lang": self.lang,
                "use_gpu": self.device.lower().startswith("gpu"),
                "rec_model_name": self.rec_model_name,
                "det_model_name": self.det_model_name,
            }
            return PaddleOCR(**legacy_kwargs)
        except Exception as exc:
            raise OCRProviderError(ProcessingErrorCode.OCR_INITIALIZATION_ERROR) from exc

    def _cached_model_dir(self, model_name: str) -> str | None:
        if not self.cache_dir:
            return None
        model_dir = Path(self.cache_dir) / "official_models" / model_name
        return str(model_dir.resolve()) if model_dir.exists() else None

    # A first pass that finds very little text, or text it is not confident
    # about, is the observable signature of a rotated / sideways capture.
    _RETRY_MIN_MEAN_CONFIDENCE = 0.80
    _RETRY_MIN_CHARS_PER_PAGE = 120

    def _looks_orientation_broken(self, pages: list[OCRPage]) -> bool:
        confidences = [
            line.confidence
            for page in pages
            for line in page.lines
            if line.confidence is not None and line.text.strip()
        ]
        if not confidences:
            return True
        if sum(confidences) / len(confidences) < self._RETRY_MIN_MEAN_CONFIDENCE:
            return True
        total_chars = sum(len(page.text.strip()) for page in pages)
        return total_chars < self._RETRY_MIN_CHARS_PER_PAGE * max(1, len(pages))

    def _retry_with_orientation(
        self, pages: list[OCRPage], image_paths: list[Path]
    ) -> list[OCRPage]:
        """Re-run pages once with PaddleOCR's orientation classifier enabled.

        This is deliberately a *conditional retry* rather than an always-on
        setting. Measured on a real upright 재학증명서, enabling the
        orientation classifier unconditionally dropped mean line confidence
        from 0.933 to 0.717 and re-broke the document title. On a 90-degree
        rotated copy of the same page it improved recognized characters from
        243 to 367. Always-on therefore trades a large regression on the
        common case for a partial gain on the rare one; a retry only pays
        the cost when the first pass already looks orientation-damaged.

        Upright documents never reach this path, so they keep the good
        first-pass result. Rotation is still only *partially* supported --
        see the limitations section of the audit report.
        """
        if not self.doc_orientation or not image_paths:
            return pages
        if not any(self._looks_orientation_broken([page]) for page in pages):
            return pages
        try:
            retried = [
                self._normalize_page(
                    raw=self._predict(image_path, orientation=True), page_number=idx, duration_ms=0
                )
                for idx, image_path in enumerate(image_paths, start=1)
            ]
        except Exception:
            # A retry must never turn a usable result into a failure.
            return pages
        if self._recognition_quality(retried) > self._recognition_quality(pages):
            return retried
        return pages

    @staticmethod
    def _recognition_quality(pages: list[OCRPage]) -> float:
        """A single comparable number: recognized characters weighted by how
        confident the recognizer was about them."""
        total = 0.0
        for page in pages:
            for line in page.lines:
                if not line.text.strip():
                    continue
                weight = line.confidence if line.confidence is not None else 0.5
                total += len(line.text) * weight
        return total

    def _predict(self, image_path: Path, orientation: bool = False) -> Any:
        engine = self._orientation_engine if orientation else self._engine
        if hasattr(engine, "predict"):
            return engine.predict(str(image_path))
        if hasattr(engine, "ocr"):
            return engine.ocr(str(image_path), cls=True)
        raise OCRProviderError(ProcessingErrorCode.OCR_INVALID_RESPONSE)

    async def extract_document(
        self, path: Path, mime_type: str, original_filename: str = ""
    ) -> list[OCRPage]:
        return await self._extract_document(path, mime_type)

    async def _extract_document(self, path: Path, mime_type: str) -> list[OCRPage]:
        started = time.perf_counter()
        pages: list[OCRPage] = []
        try:
            for idx, image_path, transform in self._input_images(path, mime_type):
                page_start = time.perf_counter()
                raw = await run_ocr(
                    partial(self._predict, image_path),
                    self.settings.ocr_timeout_seconds,
                )
                page = self._normalize_page(raw=raw, page_number=idx, duration_ms=0)
                page = await self._retry_page_with_orientation(page, image_path)
                page.page_number = idx
                page.duration_ms = int((time.perf_counter() - page_start) * 1000)
                page.metadata["transform"] = {**transform, **page.metadata.get("transform", {})}
                # A page can render below the configured DPI (budget fit to the
                # page's own raster); report what was actually used.
                if "effective_render_dpi" in transform:
                    page.metadata["render_dpi"] = transform["effective_render_dpi"]
                pages.append(page)
        except OCRProviderError:
            raise
        except Exception as exc:
            raise OCRProviderError(ProcessingErrorCode.OCR_PROCESSING_ERROR) from exc
        duration_ms = int((time.perf_counter() - started) * 1000)
        for page in pages:
            page.metadata["document_duration_ms"] = duration_ms
        if not pages or not any(page.text.strip() for page in pages):
            raise OCRProviderError(ProcessingErrorCode.OCR_EMPTY_RESULT)
        return pages

    async def _retry_page_with_orientation(self, page: OCRPage, image_path: Path) -> OCRPage:
        if not self.doc_orientation or not self._looks_orientation_broken([page]):
            return page
        try:
            raw = await run_ocr(
                partial(self._predict, image_path, orientation=True),
                self.settings.ocr_timeout_seconds,
            )
            retried = self._normalize_page(raw=raw, page_number=page.page_number, duration_ms=0)
        except Exception:
            # A retry must never turn a usable result into a failure.
            return page
        if self._recognition_quality([retried]) > self._recognition_quality([page]):
            return retried
        return page

    def _input_images(self, path: Path, mime_type: str) -> Iterator[tuple[int, Path, dict]]:
        if mime_type != "application/pdf":
            # An image carries its own EXIF orientation, which the OCR loader
            # ignores, and may be in a codec the OCR engine cannot open at
            # all. Fix both before the detector sees the pixels, and only when
            # something is actually wrong, so a normal JPEG or PNG takes
            # exactly the same path as before.
            with Image.open(path) as image:
                self._check_pixels(*image.size)
                transform = {
                    "exif_orientation": image.getexif().get(274, 1),
                    "source_width": image.width,
                    "source_height": image.height,
                    "coordinate_reference": "prepared_image",
                }
            preprocessor = ImagePreprocessor()
            if preprocessor.needs_preparation(path):
                with tempfile.TemporaryDirectory(prefix="advs_paddle_") as directory:
                    prepared = preprocessor.prepare(path, Path(directory))
                    if prepared is None:
                        raise OCRProviderError(ProcessingErrorCode.CORRUPT_DOCUMENT)
                    self._check_temp(prepared)
                    yield 1, prepared, transform
            else:
                yield 1, path, transform
            return
        try:
            with (
                fitz.open(path) as doc,
                tempfile.TemporaryDirectory(prefix="advs_paddle_") as directory,
            ):
                if (
                    doc.needs_pass
                    or not doc.page_count
                    or doc.page_count > self.settings.max_pdf_pages
                ):
                    raise OCRProviderError(ProcessingErrorCode.RESOURCE_LIMIT)
                total = 0
                for idx, page in enumerate(doc, start=1):
                    scale, scale_reason = self._page_render_scale(page)
                    width, height = (
                        math.ceil(page.rect.width * scale),
                        math.ceil(page.rect.height * scale),
                    )
                    self._check_pixels(width, height)
                    total += width * height
                    if total > self.settings.max_pdf_render_pixels:
                        raise OCRProviderError(ProcessingErrorCode.RESOURCE_LIMIT)
                    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                    image_path = Path(directory) / "page.png"
                    pix.save(image_path)
                    del pix
                    self._check_temp(image_path)
                    try:
                        yield (
                            idx,
                            image_path,
                            {
                                "pdf_rotation_degrees": page.rotation,
                                "render_scale": scale,
                                "render_scale_reason": scale_reason,
                                "effective_render_dpi": int(72 * scale),
                                "coordinate_reference": "rendered_image",
                            },
                        )
                    finally:
                        image_path.unlink(missing_ok=True)
        except OCRProviderError:
            raise
        except Exception as exc:
            raise OCRProviderError(ProcessingErrorCode.PDF_RENDER_ERROR) from exc

    def _check_pixels(self, width: int, height: int) -> None:
        if (
            min(width, height) < 1
            or max(width, height) > self.settings.max_image_dimension
            or width * height > self.settings.max_image_pixels
        ):
            raise OCRProviderError(ProcessingErrorCode.RESOURCE_LIMIT)

    _MIN_RENDER_SCALE = 1.5

    def _page_render_scale(self, page: Any) -> tuple[float, str]:
        """Scale to render one PDF page at, and the reason for it.

        The pixel budget is a statement about decode cost, not about document
        validity. A page box routinely overstates the resolution of the raster
        it wraps: scanners and print-to-PDF pipelines emit page boxes far
        larger than the image inside them, so projecting the configured render
        DPI onto the box multiplies memory and OCR time by the oversampling
        factor while producing no additional evidence.

        So the budget is applied against the resolution the page actually
        carries. When the configured DPI would push a page past the budget,
        the scale drops to that page's own resolution -- never below it, so no
        detail is lost. A page that fits the budget renders exactly as before,
        and a vector page with no embedded raster is never downscaled.
        """
        scale = self.render_scale
        if not self._exceeds_page_budget(page, scale):
            return scale, "configured_render_dpi"
        source_scale = self._source_raster_scale(page)
        if source_scale is None or source_scale >= scale:
            return scale, "configured_render_dpi"
        return max(self._MIN_RENDER_SCALE, source_scale), "source_resolution_fit"

    def _exceeds_page_budget(self, page: Any, scale: float) -> bool:
        width = math.ceil(page.rect.width * scale)
        height = math.ceil(page.rect.height * scale)
        return (
            max(width, height) > self.settings.max_image_dimension
            or width * height > self.settings.max_image_pixels
        )

    def _source_raster_scale(self, page: Any) -> float | None:
        """Scale at which the page's embedded raster is reproduced 1:1.

        Returns None for a vector page, where the render DPI is the only
        resolution in play and must not be reduced.
        """
        try:
            infos = page.get_image_info(xrefs=True)
        except Exception:
            return None
        rotation = int(getattr(page, "rotation", 0)) % 180
        scale: float | None = None
        for info in infos or []:
            bbox = info.get("bbox")
            width_px = info.get("width")
            height_px = info.get("height")
            if not bbox or not width_px or not height_px:
                continue
            placed_w = float(bbox[2]) - float(bbox[0])
            placed_h = float(bbox[3]) - float(bbox[1])
            if placed_w <= 0 or placed_h <= 0:
                continue
            if rotation:
                placed_w, placed_h = placed_h, placed_w
            # Never render below the finest content on the page.
            candidate = min(float(width_px) / placed_w, float(height_px) / placed_h)
            scale = candidate if scale is None else max(scale, candidate)
        return scale

    def _check_temp(self, path: Path) -> None:
        if path.stat().st_size > self.settings.max_ocr_temp_bytes:
            raise OCRProviderError(ProcessingErrorCode.RESOURCE_LIMIT)

    def _normalize_page(self, raw: Any, page_number: int, duration_ms: int) -> OCRPage:
        if not isinstance(raw, (list, dict)):
            raw = list(raw)
        lines = self._extract_lines(raw)
        text = assemble_page_text(lines)
        confidences = [line.confidence for line in lines if line.confidence is not None]
        return OCRPage(
            page_number=page_number,
            text=text,
            lines=lines,
            confidence=sum(confidences) / len(confidences) if confidences else None,
            duration_ms=duration_ms,
            metadata={
                "provider": self.provider_name,
                "lang": self.lang,
                "rec_model_name": self.rec_model_name,
                "det_model_name": self.det_model_name,
                "device": self.device,
                "render_dpi": int(72 * self.render_scale),
                "doc_orientation": self.doc_orientation,
                "provider_version": version("paddleocr"),
                "source": "ocr",
                "coordinate_space": "pixel",
                "transform": self._transform_metadata(raw),
            },
        )

    @staticmethod
    def _transform_metadata(raw: Any) -> dict:
        item = raw[0] if isinstance(raw, list) and raw else raw
        if not isinstance(item, dict):
            return {}
        preprocessor = item.get("doc_preprocessor_res")
        if not isinstance(preprocessor, dict):
            return {}
        return {
            "orientation_degrees": preprocessor.get("angle"),
            "coordinate_reference": "provider_preprocessed_image",
        }

    def _extract_lines(self, raw: Any) -> list[OCRLine]:
        items = self._flatten_result(raw)
        lines: list[OCRLine] = []
        for item in items:
            line = self._item_to_line(item)
            if line and line.text.strip():
                lines.append(line)
        return lines

    def _flatten_result(self, raw: Any) -> list[Any]:
        if isinstance(raw, list) and len(raw) == 1 and isinstance(raw[0], list):
            return list(raw[0])
        if isinstance(raw, list):
            if raw and all(isinstance(item, dict) for item in raw):
                expanded: list[Any] = []
                for item in raw:
                    if "rec_texts" in item:
                        texts = self._present(item, "rec_texts", default=[])
                        scores = self._present(item, "rec_scores", default=[])
                        boxes = self._present(item, "rec_polys", "rec_boxes", default=[])
                        # Missing quality or geometry must not silently drop
                        # observations through a truncating zip().
                        for index, text in enumerate(texts):
                            expanded.append(
                                {
                                    "text": text,
                                    "confidence": scores[index] if index < len(scores) else None,
                                    "poly": boxes[index] if index < len(boxes) else None,
                                }
                            )
                    else:
                        expanded.append(item)
                return expanded
            return raw
        if isinstance(raw, dict):
            return self._flatten_result([raw])
        raise OCRProviderError(ProcessingErrorCode.OCR_INVALID_RESPONSE)

    @staticmethod
    def _present(item: dict, *keys: str, default: Any = None) -> Any:
        return next((item[key] for key in keys if item.get(key) is not None), default)

    def _item_to_line(self, item: Any) -> OCRLine | None:
        if isinstance(item, dict):
            text = self._present(item, "text", "rec_text", "transcription")
            confidence = self._present(item, "confidence", "score", "rec_score")
            box = self._present(item, "box", "poly", "points", "dt_poly")
            if text is None:
                return None
            return OCRLine(
                str(text),
                self._confidence(confidence),
                self._bbox(box),
                polygon=self._polygon(box),
                detection_confidence=self._confidence(item.get("detection_confidence")),
            )

        if isinstance(item, (list, tuple)) and len(item) >= 2:
            box = item[0]
            text_part = item[1]
            if isinstance(text_part, (list, tuple)) and text_part:
                text = text_part[0]
                confidence = text_part[1] if len(text_part) > 1 else None
            else:
                text = text_part
                confidence = item[2] if len(item) > 2 else None
            return OCRLine(
                str(text), self._confidence(confidence), self._bbox(box), polygon=self._polygon(box)
            )
        return None

    def _confidence(self, value: Any) -> float | None:
        try:
            number = float(value) if value is not None else None
            return (
                number
                if number is not None and math.isfinite(number) and 0 <= number <= 1
                else None
            )
        except (TypeError, ValueError):
            return None

    def _polygon(self, value: Any) -> tuple[tuple[float, float], ...] | None:
        if isinstance(value, dict):
            value = self._present(value, "points", "vertices")
        if hasattr(value, "tolist"):
            value = value.tolist()
        if not isinstance(value, (list, tuple)) or len(value) < 3:
            return None
        try:
            polygon = tuple((float(point[0]), float(point[1])) for point in value)
        except (TypeError, ValueError, IndexError):
            return None
        return polygon if all(math.isfinite(v) for point in polygon for v in point) else None

    def _bbox(self, value: Any) -> BoundingBox | None:
        if value is None:
            return None
        points = value.tolist() if hasattr(value, "tolist") else value
        if isinstance(value, dict):
            points = self._present(value, "points", "vertices")
        try:
            if len(points) == 4 and all(isinstance(v, (int, float)) for v in points):
                x1, y1, x2, y2 = [float(v) for v in points]
                return BoundingBox(x=x1, y=y1, width=x2 - x1, height=y2 - y1)
            xs = [float(point[0]) for point in points]
            ys = [float(point[1]) for point in points]
        except (TypeError, ValueError, IndexError):
            return None
        if not xs or not ys or not all(math.isfinite(v) for v in [*xs, *ys]):
            return None
        return BoundingBox(x=min(xs), y=min(ys), width=max(xs) - min(xs), height=max(ys) - min(ys))

    async def health_check(self) -> bool:
        try:
            await run_ocr(lambda: self._engine, self.settings.ocr_timeout_seconds)
            return True
        except OCRProviderError:
            return False


def get_ocr_provider(settings: Settings) -> OCRProvider:
    provider = settings.ocr_provider.lower().strip()
    if provider == "mock":
        key: tuple = ("mock", "", "", "", "", "")
        if key not in _PROVIDER_CACHE:
            _PROVIDER_CACHE[key] = MockOCRProvider()
        return _PROVIDER_CACHE[key]  # type: ignore[return-value]
    if provider == "paddle":
        key = (
            "paddle",
            settings.paddle_ocr_device,
            settings.paddle_ocr_lang,
            settings.paddle_ocr_rec_model_name,
            settings.paddle_ocr_det_model_name,
            settings.paddle_ocr_cache_dir,
            settings.paddle_ocr_render_dpi,
            settings.paddle_ocr_doc_orientation,
            settings.max_image_dimension,
            settings.max_image_pixels,
            settings.max_pdf_render_pixels,
            settings.max_pdf_pages,
            settings.max_ocr_temp_bytes,
            settings.ocr_timeout_seconds,
        )
        if key not in _PROVIDER_CACHE:
            _PROVIDER_CACHE[key] = PaddleOCRProvider(settings)
        return _PROVIDER_CACHE[key]  # type: ignore[return-value]
    raise ValueError(
        f"Unsupported OCR_PROVIDER '{settings.ocr_provider}'. Expected mock or paddle."
    )
