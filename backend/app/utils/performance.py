import logging
import os
import time
from contextlib import contextmanager
from functools import wraps
from typing import Callable, Iterator, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable)


def is_performance_debug_enabled() -> bool:
    return os.getenv("PERFORMANCE_DEBUG", "false").lower() == "true"


def get_slow_threshold_ms() -> int:
    try:
        return int(os.getenv("SLOW_REQUEST_THRESHOLD_MS", "1000"))
    except ValueError:
        return 1000


def monotonic_ms() -> float:
    return time.monotonic() * 1000


def log_duration(label: str, started_ms: float) -> None:
    elapsed_ms = monotonic_ms() - started_ms
    if is_performance_debug_enabled() or elapsed_ms >= get_slow_threshold_ms():
        logger.warning("Slow service: %s took %.0fms", label, elapsed_ms)


@contextmanager
def measure_service(label: str) -> Iterator[None]:
    started_ms = monotonic_ms()
    try:
        yield
    finally:
        log_duration(label, started_ms)


def timed_service(label: str | None = None) -> Callable[[F], F]:
    def decorator(fn: F) -> F:
        service_label = label or getattr(fn, "__name__", "service")

        @wraps(fn)
        def wrapper(*args, **kwargs):
            with measure_service(service_label):
                return fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
