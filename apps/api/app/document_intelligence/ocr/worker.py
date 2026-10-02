"""One bounded local OCR worker per API process, with honest timeout semantics.

Python cannot kill a native inference thread. A timeout stops waiting but keeps
the capacity occupied until that job actually exits. No unbounded executor
queue, concurrent access to Paddle engines, or detached late persistence.
"""

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore

from app.core.errors import ProcessingErrorCode
from app.document_intelligence.ocr.models import OCRProviderError

_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="advs-ocr")
_CAPACITY = BoundedSemaphore(1)


async def run_ocr[T](operation: Callable[[], T], timeout: float) -> T:
    if not _CAPACITY.acquire(blocking=False):
        raise OCRProviderError(ProcessingErrorCode.OCR_BUSY)
    try:
        future = _EXECUTOR.submit(operation)
    except BaseException:
        _CAPACITY.release()
        raise
    future.add_done_callback(lambda _: _CAPACITY.release())
    wrapped = asyncio.wrap_future(future)
    wrapped.add_done_callback(lambda result: result.exception() if not result.cancelled() else None)
    try:
        return await asyncio.wait_for(asyncio.shield(wrapped), timeout)
    except TimeoutError as exc:
        raise OCRProviderError(ProcessingErrorCode.OCR_TIMEOUT) from exc
