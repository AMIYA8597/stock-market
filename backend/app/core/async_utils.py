"""Helpers for calling coroutines from synchronous code."""

from __future__ import annotations

import asyncio
import concurrent.futures
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

T = TypeVar("T")

_RAISE = object()


def run_coroutine_sync(  # noqa: UP047 - PEP 695 generics need Python 3.12
    factory: Callable[[], Awaitable[T]],
    *,
    timeout: float,
    default: Any = _RAISE,
    on_error: Callable[[Exception], T] | None = None,
) -> T:
    """Run the coroutine produced by ``factory`` from a synchronous caller.

    When an event loop is already running in the current thread the coroutine is
    executed on a dedicated worker thread and awaited for at most ``timeout``
    seconds. Failures are re-raised unless ``default`` or ``on_error`` is given.
    """
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, factory()).result(timeout=timeout)
        return asyncio.run(factory())
    except Exception as exc:
        if on_error is not None:
            return on_error(exc)
        if default is _RAISE:
            raise
        return default
