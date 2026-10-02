"""One bounded local OCR worker per API process, with honest timeout semantics.

Python cannot kill a native inference thread. A timeout stops waiting but keeps
the capacity occupied until that job actually exits. Normal contention waits
for that bounded slot instead of turning a valid document into a terminal
OCR_BUSY failure.
"""

import asyncio
import weakref
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from app.core.errors import ProcessingErrorCode
from app.document_intelligence.ocr.models import OCRProviderError

_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="advs-ocr")
_LOCKS: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Lock] = (
    weakref.WeakKeyDictionary()
)


def _capacity_lock() -> asyncio.Lock:
    loop = asyncio.get_running_loop()
    lock = _LOCKS.get(loop)
    if lock is None:
        lock = asyncio.Lock()
        _LOCKS[loop] = lock
    return lock


def _release_lock(lock: asyncio.Lock) -> None:
    if lock.locked():
        lock.release()


async def run_ocr[T](operation: Callable[[], T], timeout: float) -> T:
    lock = _capacity_lock()
    await lock.acquire()
    loop = asyncio.get_running_loop()
    try:
        future = _EXECUTOR.submit(operation)
    except BaseException:
        _release_lock(lock)
        raise
    future.add_done_callback(lambda _: loop.call_soon_threadsafe(_release_lock, lock))
    wrapped = asyncio.wrap_future(future)
    wrapped.add_done_callback(lambda result: result.exception() if not result.cancelled() else None)
    try:
        return await asyncio.wait_for(asyncio.shield(wrapped), timeout)
    except TimeoutError as exc:
        raise OCRProviderError(ProcessingErrorCode.OCR_TIMEOUT) from exc
