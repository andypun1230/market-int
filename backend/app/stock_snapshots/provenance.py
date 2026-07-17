from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.providers.models import HistoryData, QuoteData

SNAPSHOT_SCHEMA_VERSION = 2
ALGORITHM_VERSION = "stock-analysis-snapshot-v2"


@dataclass(frozen=True)
class RuntimeProvenance:
    data_mode: str
    quote_provider: str
    history_provider: str
    test_data: bool
    mock_data: bool
    configuration_signature: str
    snapshot_schema_version: int = SNAPSHOT_SCHEMA_VERSION
    algorithm_version: str = ALGORITHM_VERSION


def current_runtime_provenance() -> RuntimeProvenance:
    data_mode = current_data_mode()
    quote_provider = normalized_provider(os.getenv("QUOTE_DATA_PROVIDER") or os.getenv("QUOTE_PROVIDER") or os.getenv("DATA_PROVIDER") or os.getenv("MARKET_DATA_PROVIDER") or "test")
    history_provider = normalized_provider(os.getenv("HISTORY_DATA_PROVIDER") or os.getenv("HISTORY_PROVIDER") or os.getenv("DATA_PROVIDER") or os.getenv("MARKET_DATA_PROVIDER") or "test")
    payload = {
        "data_mode": data_mode,
        "quote_provider": quote_provider,
        "history_provider": history_provider,
        "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
        "algorithm_version": ALGORITHM_VERSION,
        "history_adjusted": env_bool("MARKET_DATA_HISTORY_ADJUSTED", True),
    }
    signature = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:20]
    return RuntimeProvenance(
        data_mode=data_mode,
        quote_provider=quote_provider,
        history_provider=history_provider,
        test_data=data_mode == "test",
        mock_data=data_mode == "mock",
        configuration_signature=signature,
    )


def current_data_mode() -> str:
    values = {
        normalized_provider(os.getenv("DATA_PROVIDER") or os.getenv("MARKET_DATA_PROVIDER") or "test"),
        normalized_provider(os.getenv("QUOTE_DATA_PROVIDER") or os.getenv("QUOTE_PROVIDER") or ""),
        normalized_provider(os.getenv("HISTORY_DATA_PROVIDER") or os.getenv("HISTORY_PROVIDER") or ""),
    }
    if values & {"test", "generated_test_data"}:
        return "test"
    if "mock" in values:
        return "mock"
    return "live"


def snapshot_namespace(symbol: str, provenance: RuntimeProvenance | None = None) -> str:
    runtime = provenance or current_runtime_provenance()
    return f"{runtime.data_mode}:{runtime.quote_provider}:{runtime.history_provider}:{runtime.configuration_signature}:{symbol.upper()}"


def is_snapshot_compatible(snapshot: Any, provenance: RuntimeProvenance | None = None) -> tuple[bool, str | None]:
    runtime = provenance or current_runtime_provenance()
    metadata = snapshot_metadata(snapshot)
    if runtime.data_mode == "live":
        if not metadata:
            return False, "missing_provenance"
        if metadata.get("snapshot_schema_version") != SNAPSHOT_SCHEMA_VERSION:
            return False, "schema_version"
        if metadata.get("data_mode") in {"test", "mock"}:
            return False, "data_mode"
        if metadata.get("test_data") is True:
            return False, "test_data"
        if metadata.get("mock_data") is True:
            return False, "mock_data"
        if normalized_provider(metadata.get("history_provider")) != runtime.history_provider:
            return False, "history_provider"
        if normalized_provider(metadata.get("quote_provider")) != runtime.quote_provider:
            return False, "quote_provider"
        if metadata.get("configuration_signature") != runtime.configuration_signature:
            return False, "configuration_signature"
    else:
        if metadata.get("configuration_signature") and metadata.get("configuration_signature") != runtime.configuration_signature:
            return False, "configuration_signature"
        if metadata.get("data_mode") and metadata.get("data_mode") != runtime.data_mode:
            return False, "data_mode"
    return True, None


def snapshot_metadata(snapshot: Any) -> dict[str, Any]:
    metadata = getattr(snapshot, "metadata", None)
    return metadata if isinstance(metadata, dict) else {}


def build_snapshot_metadata(
    *,
    quote: QuoteData | None,
    history: HistoryData,
    source_state: str,
    latest_history_timestamp: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime = current_runtime_provenance()
    history_provider = normalized_provider(history.provider or history.source or runtime.history_provider)
    quote_provider = normalized_provider((quote.provider or quote.source) if quote else runtime.quote_provider)
    source_values = {
        normalized_provider(source_state),
        normalized_provider(history.source),
        normalized_provider(history.provider),
        normalized_provider(getattr(history, "source_state", None)),
        normalized_provider(quote.source if quote else None),
        normalized_provider(quote.provider if quote else None),
    }
    test_data = runtime.test_data or bool(source_values & {"test", "generated_test_data"})
    mock_data = runtime.mock_data or "mock" in source_values or bool(getattr(history, "fallback_used", False)) or bool(getattr(quote, "fallback_used", False) if quote else False)
    data_mode = "test" if test_data else "mock" if mock_data else "live"
    metadata = {
        "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
        "algorithm_version": ALGORITHM_VERSION,
        "data_mode": data_mode,
        "test_data": test_data,
        "mock_data": mock_data,
        "configuration_signature": runtime.configuration_signature,
        "runtime_quote_provider": runtime.quote_provider,
        "runtime_history_provider": runtime.history_provider,
        "quote_provider": quote_provider,
        "history_provider": history_provider,
        "source_state": source_state,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "latest_history_timestamp": latest_history_timestamp,
    }
    metadata.update(extra or {})
    return metadata


def normalized_provider(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text == "massive":
        return "polygon"
    if text == "live":
        return "finnhub"
    return text


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}
