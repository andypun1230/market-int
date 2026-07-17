#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.validation.application_endpoint_inventory import (  # noqa: E402
    DEFAULT_SYMBOLS,
    SECONDARY_SYMBOLS,
    EndpointSpec,
    get_endpoint_inventory,
    inventory_as_dicts,
)
from app.validation.data_quality import (  # noqa: E402
    classify_status,
    find_invalid_numbers,
    find_raw_error_text,
    validate_history,
    validate_quote,
    validate_required_fields,
)
from app.validation.symbol_registry import build_symbol_registry, provider_bound_symbols  # noqa: E402


@dataclass
class HttpResult:
    status_code: int
    content_type: str
    elapsed_ms: int
    payload: Any = None
    text: str = ""
    error: str | None = None


@dataclass
class ValidationRecord:
    name: str
    method: str
    path: str
    screen: str
    status: str
    http_status: int | None
    elapsed_ms: int
    required_failures: list[str] = field(default_factory=list)
    optional_failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    source_state: str | None = None
    provider: str | None = None
    symbol: str | None = None

    def model_dump(self) -> dict[str, object]:
        return {
            "name": self.name,
            "method": self.method,
            "path": self.path,
            "screen": self.screen,
            "status": self.status,
            "http_status": self.http_status,
            "elapsed_ms": self.elapsed_ms,
            "required_failures": self.required_failures,
            "optional_failures": self.optional_failures,
            "warnings": self.warnings,
            "source_state": self.source_state,
            "provider": self.provider,
            "symbol": self.symbol,
        }


class ProviderCallRecorder:
    def __init__(self) -> None:
        self.finnhub_history_calls: list[dict[str, object]] = []
        self.polygon_history_calls: list[dict[str, object]] = []

    @contextmanager
    def install(self):
        try:
            from app.providers.finnhub_provider import FinnhubMarketDataProvider
            from app.providers.polygon_provider import PolygonMarketDataProvider
        except Exception:
            yield self
            return

        original_finnhub = FinnhubMarketDataProvider.get_history
        original_polygon = PolygonMarketDataProvider.get_history
        recorder = self

        def finnhub_wrapper(provider, symbol: str, resolution: str = "D", days: int = 240):
            recorder.finnhub_history_calls.append({
                "symbol": symbol.upper(),
                "resolution": resolution,
                "days": days,
                "provider": "finnhub",
            })
            return original_finnhub(provider, symbol, resolution=resolution, days=days)

        def polygon_wrapper(provider, symbol: str, resolution: str = "D", days: int = 240):
            recorder.polygon_history_calls.append({
                "symbol": symbol.upper(),
                "resolution": resolution,
                "days": days,
                "provider": "polygon",
            })
            return original_polygon(provider, symbol, resolution=resolution, days=days)

        FinnhubMarketDataProvider.get_history = finnhub_wrapper
        PolygonMarketDataProvider.get_history = polygon_wrapper
        try:
            yield self
        finally:
            FinnhubMarketDataProvider.get_history = original_finnhub
            PolygonMarketDataProvider.get_history = original_polygon

    def model_dump(self) -> dict[str, object]:
        return {
            "finnhub_history_call_count": len(self.finnhub_history_calls),
            "polygon_history_call_count": len(self.polygon_history_calls),
            "finnhub_history_calls": self.finnhub_history_calls,
            "polygon_history_calls_sample": self.polygon_history_calls[:100],
        }


class InProcessClient:
    def __init__(self) -> None:
        from fastapi.testclient import TestClient
        from main import app

        self._client_cm = TestClient(app)
        self.client = self._client_cm.__enter__()

    def close(self) -> None:
        self._client_cm.__exit__(None, None, None)

    def get(self, path: str, timeout_seconds: float) -> HttpResult:
        started = time.perf_counter()
        try:
            response = self.client.get(path)
        except Exception as exc:
            return HttpResult(
                status_code=0,
                content_type="",
                elapsed_ms=elapsed_ms(started),
                error=f"{type(exc).__name__}: {exc}",
            )
        return response_to_http_result(response.status_code, response.headers.get("content-type", ""), response.content, started)


class UrlClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def close(self) -> None:
        return None

    def get(self, path: str, timeout_seconds: float) -> HttpResult:
        started = time.perf_counter()
        url = f"{self.base_url}{path}"
        request = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                body = response.read()
                return response_to_http_result(response.status, response.headers.get("content-type", ""), body, started)
        except urllib.error.HTTPError as exc:
            body = exc.read()
            return response_to_http_result(exc.code, exc.headers.get("content-type", ""), body, started)
        except Exception as exc:
            return HttpResult(
                status_code=0,
                content_type="",
                elapsed_ms=elapsed_ms(started),
                error=f"{type(exc).__name__}: {exc}",
            )


def response_to_http_result(status_code: int, content_type: str, body: bytes, started: float) -> HttpResult:
    text = body.decode("utf-8", errors="replace")
    payload: Any = None
    if "application/json" in content_type:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            return HttpResult(status_code, content_type, elapsed_ms(started), text=text[:1200], error=f"Invalid JSON: {exc}")
    return HttpResult(status_code, content_type, elapsed_ms(started), payload=payload, text=text[:1200])


def elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate application data integrity across endpoints and symbols.")
    parser.add_argument("--mode", choices=("test", "live", "mixed"), default="test")
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--json-output", default=None)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--allow-mock-fallback", action="store_true")
    parser.add_argument("--include-report", action="store_true")
    parser.add_argument("--include-copilot", action="store_true")
    parser.add_argument("--frontend-manifest-output", default=None)
    parser.add_argument("--timeout-seconds", type=float, default=12.0)
    parser.add_argument("--max-concurrency", type=int, default=1)
    return parser.parse_args()


def configure_environment(args: argparse.Namespace) -> tempfile.TemporaryDirectory | None:
    temp_dir: tempfile.TemporaryDirectory | None = None
    if args.mode == "test":
        temp_dir = tempfile.TemporaryDirectory(prefix="app-validation-cache-")
        os.environ.update({
            "DATA_PROVIDER": "test",
            "MARKET_DATA_PROVIDER": "test",
            "QUOTE_DATA_PROVIDER": "test",
            "HISTORY_DATA_PROVIDER": "test",
            "MARKET_DATA_ALLOW_MOCK_FALLBACK": "true",
            "BACKGROUND_REFRESH_ENABLED": "false",
            "MARKET_DATA_CACHE_DB_PATH": str(Path(temp_dir.name) / "market_cache.sqlite3"),
            "MARKET_DATA_SQLITE_PATH": str(Path(temp_dir.name) / "market_cache.sqlite3"),
            "STOCK_SNAPSHOT_DB_PATH": str(Path(temp_dir.name) / "stock_snapshots.sqlite3"),
            "MARKET_SNAPSHOT_DB_PATH": str(Path(temp_dir.name) / "market_snapshots.sqlite3"),
        })
    elif args.mode == "live":
        os.environ.update({
            "DATA_PROVIDER": "finnhub",
            "MARKET_DATA_PROVIDER": "finnhub",
            "QUOTE_DATA_PROVIDER": "finnhub",
            "HISTORY_DATA_PROVIDER": "polygon",
            "MARKET_DATA_ALLOW_MOCK_FALLBACK": "true" if args.allow_mock_fallback else "false",
        })
    else:
        os.environ.update({
            "DATA_PROVIDER": os.getenv("DATA_PROVIDER", "finnhub"),
            "QUOTE_DATA_PROVIDER": os.getenv("QUOTE_DATA_PROVIDER", "finnhub"),
            "HISTORY_DATA_PROVIDER": os.getenv("HISTORY_DATA_PROVIDER", "polygon"),
            "MARKET_DATA_ALLOW_MOCK_FALLBACK": "true" if args.allow_mock_fallback else os.getenv("MARKET_DATA_ALLOW_MOCK_FALLBACK", "true"),
        })
    return temp_dir


def build_symbols(raw_symbols: str) -> list[str]:
    seen: set[str] = set()
    symbols: list[str] = []
    seeded_symbols = [*raw_symbols.split(","), *DEFAULT_SYMBOLS, *SECONDARY_SYMBOLS]
    for symbol in provider_bound_symbols(seeded_symbols):
        normalized = symbol.strip().upper()
        if normalized and normalized not in seen:
            seen.add(normalized)
            symbols.append(normalized)
    return symbols


def expand_specs(specs: list[EndpointSpec], symbols: list[str]) -> list[tuple[EndpointSpec, str, str | None]]:
    targets: list[tuple[EndpointSpec, str, str | None]] = []
    for spec in specs:
        if "{symbol}" in spec.path:
            for symbol in symbols:
                targets.append((spec, spec.path.replace("{symbol}", symbol), symbol))
        else:
            targets.append((spec, spec.path, None))
    return targets


def validate_endpoint(spec: EndpointSpec, path: str, symbol: str | None, result: HttpResult) -> ValidationRecord:
    required_failures: list[str] = []
    optional_failures: list[str] = []
    warnings: list[str] = []
    payload = result.payload

    if result.error:
        required_failures.append(result.error)
    elif result.status_code >= 500:
        if is_controlled_unavailable_response(payload):
            required_failures.append(controlled_http_failure(result.status_code, payload))
        else:
            required_failures.append(f"unexpected HTTP {result.status_code}")
    elif result.status_code == 0:
        required_failures.append("request did not complete")
    elif result.status_code >= 400:
        if is_controlled_unavailable_response(payload):
            required_failures.append(controlled_http_failure(result.status_code, payload))
        else:
            required_failures.append(f"HTTP {result.status_code}")
    elif spec.response_model == "application/pdf":
        if "application/pdf" not in result.content_type:
            required_failures.append(f"expected PDF content type, got {result.content_type}")
    elif payload is None:
        required_failures.append("expected JSON payload")
    else:
        missing_required = validate_required_fields(payload, spec.required_fields)
        if missing_required and spec.partial_supported and is_controlled_partial_response(payload):
            optional_failures.extend([f"controlled partial required field: {field}" for field in missing_required])
        else:
            required_failures.extend([f"missing required field: {field}" for field in missing_required])
        optional_failures.extend([f"missing optional field: {field}" for field in spec.optional_fields if field and not field_exists_or_null(payload, field)])
        number_issues = find_invalid_numbers(payload)
        if number_issues:
            required_failures.extend([f"invalid number at {issue}" for issue in number_issues[:10]])
        raw_errors = find_raw_error_text(payload)
        if raw_errors:
            required_failures.extend([f"raw error text at {issue}" for issue in raw_errors[:10]])
        if spec.response_model == "QuoteData" and isinstance(payload, dict):
            required_failures.extend(validate_quote(payload))
        if spec.response_model == "HistoryData" and isinstance(payload, dict):
            minimum = 20 if "days=60" in path else 60 if "days=260" in path else 1
            required_failures.extend(validate_history(payload, minimum_bars=minimum))
        if spec.response_model == "StockAnalysisAggregate" and isinstance(payload, dict):
            required_failures.extend(validate_stock_analysis_payload(payload))
        source_state = extract_source_state(payload)
        if source_state and source_state not in spec.allowed_source_states:
            required_failures.append(f"unexpected source state: {source_state}")

    if result.elapsed_ms > int(spec.timeout_seconds * 1000):
        warnings.append(f"slow response: {result.elapsed_ms}ms > {int(spec.timeout_seconds * 1000)}ms")

    status = classify_status(required_failures, optional_failures)
    return ValidationRecord(
        name=spec.response_model,
        method=spec.method,
        path=path,
        screen=spec.screen,
        status=status,
        http_status=result.status_code,
        elapsed_ms=result.elapsed_ms,
        required_failures=required_failures,
        optional_failures=optional_failures,
        warnings=warnings,
        source_state=extract_source_state(payload),
        provider=extract_provider(payload),
        symbol=symbol,
    )


def validate_stock_analysis_payload(payload: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if payload.get("snapshot_status") == "initializing":
        return failures
    required_sections = (
        "supportResistance",
        "trendline",
        "volumeAnalysis",
        "riskPlan",
        "relativeStrength",
        "stockRating",
        "multiTimeframeSignals",
    )
    for section in required_sections:
        if payload.get(section) is None:
            failures.append(f"stock analysis section unavailable: {section}")
    errors = payload.get("errors")
    if isinstance(errors, dict):
        for section in required_sections:
            if section in errors:
                failures.append(f"stock analysis required section error: {section}: {errors[section]}")
    return failures


def is_controlled_partial_response(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("partial") is True:
        return True
    if payload.get("bootstrap") is True and payload.get("refreshing") is True:
        return True
    if payload.get("cache_status") in {"miss", "stale", "initializing"} and payload.get("refreshing") is True:
        return True
    if extract_source_state(payload) in {"partial", "unavailable", "initializing"}:
        return True
    return False


def is_controlled_unavailable_response(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    return (
        payload.get("status") == "unavailable"
        and payload.get("source_state") == "unavailable"
        and isinstance(payload.get("category"), str)
        and isinstance(payload.get("message"), str)
    )


def controlled_http_failure(status_code: int, payload: Any) -> str:
    if not isinstance(payload, dict):
        return f"controlled HTTP {status_code}"
    return f"controlled HTTP {status_code}: {payload.get('category', 'unavailable')}"


def field_exists_or_null(payload: Any, path: str) -> bool:
    current = payload
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return False
    return True


def extract_source_state(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("source_state", "overall_mode", "dataStatus", "overallDataStatus"):
        value = payload.get(key)
        if isinstance(value, str):
            return normalize_source_state(value)
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        for key in ("source_state", "overall_mode", "source"):
            value = metadata.get(key)
            if isinstance(value, str):
                return normalize_source_state(value)
    return None


def normalize_source_state(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"generated_test_data", "test", "fixture", "mock-fallback"}:
        return "mock"
    return normalized


def extract_provider(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("provider", "source", "history_provider", "configured_history_provider"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return None


def fetch_provider_status(client: Any) -> dict[str, Any]:
    result = client.get("/system/provider-status", 10)
    return result.payload if isinstance(result.payload, dict) else {}


def summarize(records: list[ValidationRecord], provider_calls: dict[str, object], provider_status: dict[str, Any], symbols: list[str]) -> dict[str, Any]:
    counts = {status: sum(1 for record in records if record.status == status) for status in ("PASS", "PARTIAL", "FAIL", "SKIP")}
    http_500_count = sum(1 for record in records if record.http_status and record.http_status >= 500)
    symbol_failures: dict[str, list[str]] = {}
    for record in records:
        if record.symbol and record.status == "FAIL":
            symbol_failures.setdefault(record.symbol, []).append(record.path)
    overall = "PASS"
    if counts["FAIL"] or http_500_count:
        overall = "FAIL"
    elif counts["PARTIAL"]:
        overall = "PASS WITH CONDITIONS"
    finnhub_history_count = int(provider_calls.get("finnhub_history_call_count") or 0)
    if finnhub_history_count:
        overall = "FAIL"
    return {
        "overall_result": overall,
        "endpoint_count": len(records),
        "symbol_count": len(symbols),
        "counts": counts,
        "http_500_count": http_500_count,
        "symbol_failures": symbol_failures,
        "provider_status": provider_status,
        "provider_routing_evidence": provider_calls,
        "failed_records": [record.model_dump() for record in records if record.status == "FAIL"],
        "partial_records": [record.model_dump() for record in records if record.status == "PARTIAL"],
        "slow_records": [record.model_dump() for record in records if record.warnings],
    }


def write_json(path: str | Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def build_frontend_manifest(records: list[ValidationRecord], inventory: list[dict[str, object]], summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": current_iso(),
        "overall_result": summary["overall_result"],
        "screen_matrix": group_records_by_screen(records),
        "inventory": inventory,
        "failure_strings_to_check": [
            "Setup summary unavailable",
            "Chart unavailable",
            "Signal summary unavailable",
            "History unavailable",
            "Fetch request has been cancelled",
            "HTTP 500",
            "Internal Server Error",
            "ProviderRequestError",
            "undefined",
            "NaN",
        ],
        "manual_required": [
            "Simulator visual rendering",
            "Rapid tab-switch cancellation behavior",
            "Screenshot capture on native UI failures",
        ],
    }


def group_records_by_screen(records: list[ValidationRecord]) -> dict[str, dict[str, int]]:
    grouped: dict[str, dict[str, int]] = {}
    for record in records:
        bucket = grouped.setdefault(record.screen, {"PASS": 0, "PARTIAL": 0, "FAIL": 0, "SKIP": 0})
        bucket[record.status] += 1
    return grouped


def current_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def print_summary(summary: dict[str, Any], records: list[ValidationRecord], verbose: bool) -> None:
    print(f"Overall: {summary['overall_result']}")
    print(f"Endpoints tested: {summary['endpoint_count']}")
    print(f"Symbols tested: {summary['symbol_count']}")
    print(f"Counts: {summary['counts']}")
    print(f"HTTP 500 count: {summary['http_500_count']}")
    routing = summary["provider_routing_evidence"]
    print(f"Finnhub history calls: {routing.get('finnhub_history_call_count', 'unavailable')}")
    print(f"Polygon history calls: {routing.get('polygon_history_call_count', 'unavailable')}")
    if summary["failed_records"]:
        print("\nFailures:")
        for record in records:
            if record.status == "FAIL":
                print(f"- {record.method} {record.path} [{record.screen}]")
                for issue in record.required_failures[:6]:
                    print(f"  - {issue}")
    if verbose and summary["partial_records"]:
        print("\nPartial:")
        for record in records:
            if record.status == "PARTIAL":
                print(f"- {record.method} {record.path}: {record.optional_failures}")


def main() -> int:
    args = parse_args()
    temp_dir = configure_environment(args)
    symbols = build_symbols(args.symbols)
    specs = get_endpoint_inventory(include_report=args.include_report, include_copilot=args.include_copilot)
    inventory = inventory_as_dicts(include_report=args.include_report, include_copilot=args.include_copilot)
    targets = expand_specs(specs, symbols)
    client = UrlClient(args.base_url) if args.base_url else InProcessClient()
    recorder = ProviderCallRecorder()
    records: list[ValidationRecord] = []

    try:
        with recorder.install():
            provider_status = fetch_provider_status(client)
            for spec, path, symbol in targets:
                result = client.get(path, min(args.timeout_seconds, spec.timeout_seconds))
                record = validate_endpoint(spec, path, symbol, result)
                records.append(record)
                if args.verbose:
                    print(f"{record.status:7} {record.elapsed_ms:5}ms {record.method} {record.path}")
                if args.fail_fast and record.status == "FAIL":
                    break
    finally:
        client.close()
        if temp_dir is not None:
            temp_dir.cleanup()

    provider_calls = recorder.model_dump() if not args.base_url else {
        "finnhub_history_call_count": "unavailable_with_base_url",
        "polygon_history_call_count": "unavailable_with_base_url",
    }
    summary = summarize(records, provider_calls, provider_status, symbols)
    report = {
        "generated_at": current_iso(),
        "mode": args.mode,
        "base_url": args.base_url,
        "symbols": symbols,
        "symbol_registry": [entry.model_dump() for entry in build_symbol_registry(symbols)],
        "inventory": inventory,
        "summary": summary,
        "records": [record.model_dump() for record in records],
    }
    json_output = args.json_output or str(PROJECT_ROOT / "docs" / "application-data-integrity-validation.json")
    write_json(json_output, report)
    manifest_output = args.frontend_manifest_output or str(PROJECT_ROOT / "docs" / "application-data-ui-manifest.json")
    write_json(manifest_output, build_frontend_manifest(records, inventory, summary))
    print_summary(summary, records, args.verbose)
    print(f"JSON report: {json_output}")
    print(f"Frontend manifest: {manifest_output}")
    return 0 if summary["overall_result"] in {"PASS", "PASS WITH CONDITIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
