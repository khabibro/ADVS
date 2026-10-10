import asyncio

from app.core.config import Settings
from app.document_intelligence.ocr.warmup import warm_up_ocr


def test_warmup_is_a_noop_for_the_mock_provider() -> None:
    assert asyncio.run(warm_up_ocr(Settings(ocr_provider="mock"))) is True
