from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Iterator

_lock = threading.RLock()
_active_interactive_requests = 0
_active_background_jobs = 0
_queued_background_jobs = 0


@contextmanager
def interactive_request() -> Iterator[None]:
    global _active_interactive_requests
    with _lock:
        _active_interactive_requests += 1
    try:
        yield
    finally:
        with _lock:
            _active_interactive_requests = max(0, _active_interactive_requests - 1)


@contextmanager
def background_job() -> Iterator[None]:
    global _active_background_jobs
    with _lock:
        _active_background_jobs += 1
    try:
        yield
    finally:
        with _lock:
            _active_background_jobs = max(0, _active_background_jobs - 1)


def mark_background_queued(delta: int) -> None:
    global _queued_background_jobs
    with _lock:
        _queued_background_jobs = max(0, _queued_background_jobs + delta)


def has_interactive_demand() -> bool:
    with _lock:
        return _active_interactive_requests > 0


def get_workload_status() -> dict[str, int]:
    with _lock:
        return {
            "active_interactive_requests": _active_interactive_requests,
            "active_background_jobs": _active_background_jobs,
            "queued_background_jobs": _queued_background_jobs,
        }
