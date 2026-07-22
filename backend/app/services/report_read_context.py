"""Request-scoped guard for immutable Daily Report assembly."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator


_report_read_only: ContextVar[bool] = ContextVar("report_read_only", default=False)


class ReportReadCacheMiss(RuntimeError):
    """A report read may not fetch a missing provider value."""


@contextmanager
def report_snapshot_read() -> Iterator[None]:
    """Allow captured cache/snapshot reads without provider work or refreshes."""
    previous_state = _report_read_only.set(True)
    try:
        yield
    finally:
        _report_read_only.reset(previous_state)


def is_report_snapshot_read() -> bool:
    return _report_read_only.get()
