import os
import shutil
import tempfile
import time
from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
from typing import Any

import fitz

from app.core.config import Settings
from app.core.errors import ProcessingErrorCode
from app.document_intelligence.ocr.models import BoundingBox, OCRLine, OCRPage, OCRProviderError
from app.document_intelligence.ocr.text_assembly import assemble_page_text

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
_PROVIDER_CACHE: dict[tuple[str, str, str, str, str, str], object] = {}


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
        started = time.perf_counter()
        try:
            image_paths = self._input_images(path, mime_type)
            pages = [
                self._normalize_page(raw=self._predict(image_path), page_number=idx, duration_ms=0)
                for idx, image_path in enumerate(image_paths, start=1)
            ]
            pages = self._retry_with_orientation(pages, image_paths)
        except OCRProviderError:
            raise
        except Exception as exc:
            raise OCRProviderError(ProcessingErrorCode.OCR_PROCESSING_ERROR) from exc
        finally:
            if mime_type == "application/pdf":
                rendered_pages = locals().get("image_paths", [])
                if rendered_pages:
                    rendered_dir = rendered_pages[0].parent
                    if rendered_dir.name.startswith("advs_paddle_"):
                        shutil.rmtree(rendered_dir, ignore_errors=True)

        duration_ms = int((time.perf_counter() - started) * 1000)
        for page in pages:
            page.duration_ms = duration_ms
        if not pages or not any(page.text.strip() for page in pages):
            raise OCRProviderError(ProcessingErrorCode.OCR_EMPTY_RESULT)
        return pages

    def _input_images(self, path: Path, mime_type: str) -> list[Path]:
        if mime_type != "application/pdf":
            return [path]

        output_dir = Path(tempfile.mkdtemp(prefix="advs_paddle_"))
        rendered: list[Path] = []
        try:
            with fitz.open(path) as doc:
                for idx, page in enumerate(doc, start=1):
                    pix = page.get_pixmap(
                        matrix=fitz.Matrix(self.render_scale, self.render_scale), alpha=False
                    )
                    image_path = output_dir / f"page_{idx}.png"
                    pix.save(image_path)
                    rendered.append(image_path)
        except Exception as exc:
            shutil.rmtree(output_dir, ignore_errors=True)
            raise OCRProviderError(ProcessingErrorCode.PDF_RENDER_ERROR) from exc
        return rendered

    def _normalize_page(self, raw: Any, page_number: int, duration_ms: int) -> OCRPage:
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
            },
        )

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
                        texts = item.get("rec_texts") or []
                        scores = item.get("rec_scores") or []
                        boxes = (
                            item.get("rec_polys")
                            or item.get("dt_polys")
                            or item.get("rec_boxes")
                            or []
                        )
                        expanded.extend(zip(boxes, texts, scores, strict=False))
                    else:
                        expanded.append(item)
                return expanded
            return raw
        if isinstance(raw, dict):
            return self._flatten_result([raw])
        raise OCRProviderError(ProcessingErrorCode.OCR_INVALID_RESPONSE)

    def _item_to_line(self, item: Any) -> OCRLine | None:
        if isinstance(item, dict):
            text = item.get("text") or item.get("rec_text") or item.get("transcription")
            confidence = item.get("confidence") or item.get("score") or item.get("rec_score")
            box = item.get("box") or item.get("poly") or item.get("points") or item.get("dt_poly")
            if text is None:
                return None
            return OCRLine(str(text), self._confidence(confidence), self._bbox(box))

        if isinstance(item, (list, tuple)) and len(item) >= 2:
            box = item[0]
            text_part = item[1]
            if isinstance(text_part, (list, tuple)) and text_part:
                text = text_part[0]
                confidence = text_part[1] if len(text_part) > 1 else None
            else:
                text = text_part
                confidence = item[2] if len(item) > 2 else None
            return OCRLine(str(text), self._confidence(confidence), self._bbox(box))
        return None

    def _confidence(self, value: Any) -> float | None:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _bbox(self, value: Any) -> BoundingBox | None:
        if value is None:
            return None
        points = value
        if isinstance(value, dict):
            points = value.get("points") or value.get("vertices")
        try:
            if len(points) == 4 and all(isinstance(v, (int, float)) for v in points):
                x1, y1, x2, y2 = [float(v) for v in points]
                return BoundingBox(x=x1, y=y1, width=x2 - x1, height=y2 - y1)
            xs = [float(point[0]) for point in points]
            ys = [float(point[1]) for point in points]
        except (TypeError, ValueError, IndexError):
            return None
        return BoundingBox(x=min(xs), y=min(ys), width=max(xs) - min(xs), height=max(ys) - min(ys))

    async def health_check(self) -> bool:
        try:
            _ = self._engine
            return True
        except OCRProviderError:
            return False


def get_ocr_provider(settings: Settings) -> OCRProvider:
    provider = settings.ocr_provider.lower().strip()
    if provider == "mock":
        key = ("mock", "", "", "", "", "")
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
        )
        if key not in _PROVIDER_CACHE:
            _PROVIDER_CACHE[key] = PaddleOCRProvider(settings)
        return _PROVIDER_CACHE[key]  # type: ignore[return-value]
    raise ValueError(
        f"Unsupported OCR_PROVIDER '{settings.ocr_provider}'. Expected mock or paddle."
    )
