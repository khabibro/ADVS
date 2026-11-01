"""One bounded local OCR worker per API process, with honest timeout semantics.

Python cannot kill a native inference thread. A timeout stops waiting but keeps
the capacity occupied until that job actually exits. Normal contention waits
for that slot, but only for a bounded time: if the slot is still held when the
wait ends, the worker is considered wedged, is recycled (a fresh executor, and
the registered engines are dropped so they are rebuilt), and the waiting call
fails with OCR_BUSY. The failure is a processing error, never a verdict, and
the next call runs on the fresh worker.
"""

import asyncio
import weakref
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from app.core.errors import ProcessingErrorCode
from app.document_intelligence.ocr.models import OCRProviderError

_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="advs-ocr")
_RECYCLE_HOOKS: list[weakref.WeakMethod] = []
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


def on_recycle(hook: Callable[[], None]) -> None:
    """Register a bound method that drops engines tied to the worker being replaced."""
    _RECYCLE_HOOKS.append(weakref.WeakMethod(hook))  # type: ignore[arg-type]


def _recycle() -> None:
    global _EXECUTOR
    stale = _EXECUTOR
    _EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="advs-ocr")
    stale.shutdown(wait=False, cancel_futures=True)
    _LOCKS.pop(asyncio.get_running_loop(), None)
    for ref in list(_RECYCLE_HOOKS):
        hook = ref()
        if hook is None:
            _RECYCLE_HOOKS.remove(ref)
        else:
            hook()


def _release_lock(lock: asyncio.Lock) -> None:
    if lock.locked():
        lock.release()


async def run_ocr[T](
    operation: Callable[[], T], timeout: float, slot_wait: float | None = None
) -> T:
    lock = _capacity_lock()
    try:
        await asyncio.wait_for(lock.acquire(), timeout if slot_wait is None else slot_wait)
    except TimeoutError as exc:
        if _LOCKS.get(asyncio.get_running_loop()) is lock:  # first waiter recycles; others retry
            _recycle()
        raise OCRProviderError(ProcessingErrorCode.OCR_BUSY) from exc
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
