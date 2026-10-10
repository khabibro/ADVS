"""Optional OCR warm-up at API start so the first real upload does not pay model load time."""

import logging
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw

from app.core.config import Settings
from app.document_intelligence.ocr.providers import PaddleOCRProvider, get_ocr_provider
from app.document_intelligence.ocr.worker import run_ocr

logger = logging.getLogger(__name__)


async def warm_up_ocr(settings: Settings) -> bool:
    """Load the OCR engines and run one tiny inference. Returns True when ready."""
    provider = get_ocr_provider(settings)
    if not isinstance(provider, PaddleOCRProvider):
        logger.info("OCR warm-up skipped (provider=%s)", settings.ocr_provider)
        return True
    started = time.perf_counter()
    logger.info("OCR warm-up started")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "warmup.png"
            image = Image.new("RGB", (480, 120), "white")
            ImageDraw.Draw(image).text((20, 40), "ADVS 2026-10-14", fill="black")
            image.save(image_path)
            await run_ocr(lambda: provider._predict(image_path), settings.ocr_timeout_seconds)
    except Exception:
        logger.exception("OCR warm-up failed; the first upload will load the model instead")
        return False
    logger.info("OCR model ready (warm-up %.1fs)", time.perf_counter() - started)
    return True
