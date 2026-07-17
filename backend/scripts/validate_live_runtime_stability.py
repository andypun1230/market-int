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
from contextlib import nullcontext
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


os.environ.setdefault("QUOTE_DATA_PROVIDER", "finnhub")
os.environ.setdefault("HISTORY_DATA_PROVIDER", "polygon")
os.environ.setdefault("MARKET_DATA_ALLOW_MOCK_FALLBACK", "false")
os.environ.setdefault("MARKET_DATA_PERSISTENT_CACHE_ENABLED", "true")
os.environ.setdefault("MARKET_DATA_HISTORY_COORDINATOR_CONCURRENCY", "2")

VALIDATOR_TEMP_DIR = tempfile.TemporaryDirectory(prefix="live-runtime-stock-snapshot-")
os.environ.setdefault("STOCK_SNAPSHOT_DB_PATH", str(Path(VALIDATOR_TEMP_DIR.name) / "stock_snapshots.sqlite3"))

from main import app  # noqa: E402
from app.services.history_request_coordinator import reset_history_request_coordinator  # noqa: E402
from app.services.market_data_repository import reset_market_data_repository  # noqa: E402
from app.services.service_cache import invalidate_service_cache  # noqa: E402


AGGREGATE_PATHS = [
    "/home/dashboard",
    "/market/core-snapshot",
    "/market/regime",
    "/market/health",
    "/market/risk",
    "/market/fear-greed",
    "/market/decision-dashboard",
    "/market/details/structure",
    "/market/details/decision",
    "/market/details/institutional",
    "/watchlist/summary",
    "/market/stock-analysis/NVDA",
]

DEFAULT_HISTORY_SYMBOLS = [
    "SPY",
    "QQQ",
    "DIA",
    "RSP",
    "QQQEW",
    "IEF",
    "TLT",
    "GLD",
    "USO",
    "UUP",
    "HYG",
    "SPX",
    "IXIC",
    "RUT",
    "DJI",
]


@dataclass
class RequestResult:
    path: str
    status_code: int
    elapsed_ms: int
    body_excerpt: str


def main() -> int:
    args = parse_args()
    configure(args)
    client_context = nullcontext(None) if args.base_url else TestClient(app)
    with client_context as client:
        if args.cold_cache:
            if args.base_url:
                reset_runtime_url(args.base_url)
            else:
                reset_runtime(client)
        rounds = max(1, args.soak_rounds if args.soak else 1)
        report: dict[str, Any] = {
            "mode": selected_mode(args),
            "config": effective_config(),
            "rounds": [],
        }
        paths = build_paths(args.symbols)
        exit_code = 0
        for index in range(rounds):
            started = time.time()
            if args.base_url:
                results = run_url_round(paths, base_url=args.base_url, max_workers=args.max_workers, timeout_seconds=args.timeout_seconds)
            else:
                results = run_inprocess_round(client, paths)
            status = get_cache_status(args.base_url, client, timeout_seconds=args.timeout_seconds)
            summary = summarize(results, aggregate_paths=AGGREGATE_PATHS)
            summary["elapsed_ms"] = int((time.time() - started) * 1000)
            summary["cache_status"] = status
            report["rounds"].append(summary)
            if summary["http_500_count"] or summary["aggregate_503_count"] or summary["timeout_count"]:
                exit_code = 1
            if args.soak and index + 1 < rounds:
                time.sleep(args.soak_delay)
        output_report(report, args.json_output)
        return exit_code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate live backend cold/warm runtime stability.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--cold-cache", action="store_true", help="Invalidate market-data/service caches before running.")
    mode.add_argument("--warm-cache", action="store_true", help="Run without invalidating caches.")
    mode.add_argument("--soak", action="store_true", help="Run multiple warm rounds.")
    parser.add_argument("--soak-rounds", type=int, default=3)
    parser.add_argument("--soak-delay", type=float, default=2.0)
    parser.add_argument("--max-workers", type=int, default=6)
    parser.add_argument("--base-url", help="Run against an already-started backend URL for true concurrent HTTP validation.")
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--symbols", default=",".join(DEFAULT_HISTORY_SYMBOLS))
    parser.add_argument("--json-output", type=Path)
    return parser.parse_args()


def configure(args: argparse.Namespace) -> None:
    if args.warm_cache or args.soak:
        return
    args.cold_cache = True


def reset_runtime(client: TestClient) -> None:
    invalidate_service_cache()
    client.post("/market-data/cache/invalidate", params={"domain": "daily_history"})
    client.post("/market-data/cache/invalidate", params={"domain": "quotes"})
    reset_history_request_coordinator()
    reset_market_data_repository()


def reset_runtime_url(base_url: str) -> None:
    post_url(base_url, "/market-data/cache/invalidate?domain=daily_history", timeout_seconds=10)
    post_url(base_url, "/market-data/cache/invalidate?domain=quotes", timeout_seconds=10)
    post_url(base_url, "/system/service-cache/clear", timeout_seconds=10)


def get_cache_status(base_url: str | None, client: TestClient | None, *, timeout_seconds: float) -> dict[str, Any]:
    if base_url:
        return get_json_url(base_url, "/market-data/cache/status", timeout_seconds=timeout_seconds)
    if client is None:
        return {"status_error": "No client available"}
    return client.get("/market-data/cache/status").json()


def build_paths(symbols_csv: str) -> list[str]:
    symbols = [symbol.strip().upper() for symbol in symbols_csv.split(",") if symbol.strip()]
    history_paths = [f"/market/live/history/{symbol}?days=240" for symbol in symbols]
    smaller_paths = [f"/market/live/history/{symbol}?days=60" for symbol in symbols[:6]]
    return [*AGGREGATE_PATHS, *history_paths, *smaller_paths]


def run_inprocess_round(client: TestClient, paths: list[str]) -> list[RequestResult]:
    return [fetch_path_inprocess(client, path) for path in paths]


def run_url_round(paths: list[str], *, base_url: str, max_workers: int, timeout_seconds: float) -> list[RequestResult]:
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(fetch_path_url, base_url.rstrip("/"), path, timeout_seconds) for path in paths]
        return [future.result() for future in as_completed(futures)]


def fetch_path_inprocess(client: TestClient, path: str) -> RequestResult:
    started = time.time()
    response = client.get(path)
    elapsed_ms = int((time.time() - started) * 1000)
    return RequestResult(path=path, status_code=response.status_code, elapsed_ms=elapsed_ms, body_excerpt=response.text[:240])


def fetch_path_url(base_url: str, path: str, timeout_seconds: float) -> RequestResult:
    return get_url(base_url, path, timeout_seconds=timeout_seconds)


def get_url(base_url: str, path: str, timeout_seconds: float) -> RequestResult:
    started = time.time()
    url = f"{base_url}{path}"
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="replace")
            return RequestResult(path=path, status_code=response.status, elapsed_ms=int((time.time() - started) * 1000), body_excerpt=body[:240])
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return RequestResult(path=path, status_code=exc.code, elapsed_ms=int((time.time() - started) * 1000), body_excerpt=body[:240])
    except Exception as exc:
        return RequestResult(
            path=path,
            status_code=599,
            elapsed_ms=int((time.time() - started) * 1000),
            body_excerpt=f"{type(exc).__name__}: {exc}",
        )


def post_url(base_url: str, path: str, timeout_seconds: float) -> RequestResult:
    started = time.time()
    url = f"{base_url.rstrip('/')}{path}"
    request = urllib.request.Request(url, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="replace")
            return RequestResult(path=path, status_code=response.status, elapsed_ms=int((time.time() - started) * 1000), body_excerpt=body[:240])
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return RequestResult(path=path, status_code=exc.code, elapsed_ms=int((time.time() - started) * 1000), body_excerpt=body[:240])
    except Exception as exc:
        return RequestResult(
            path=path,
            status_code=599,
            elapsed_ms=int((time.time() - started) * 1000),
            body_excerpt=f"{type(exc).__name__}: {exc}",
        )


def get_json_url(base_url: str, path: str, timeout_seconds: float) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="replace")
            payload = json.loads(body)
            if isinstance(payload, dict):
                return payload
            return {"payload": payload, "http_status": response.status}
    except Exception as exc:
        return {"status_error": f"{type(exc).__name__}: {exc}"}


def summarize(results: list[RequestResult], *, aggregate_paths: list[str]) -> dict[str, Any]:
    aggregate_set = set(aggregate_paths)
    failures = [result for result in results if result.status_code >= 500]
    aggregate_503 = [result for result in results if result.path in aggregate_set and result.status_code == 503]
    return {
        "request_count": len(results),
        "http_500_count": len([result for result in results if 500 <= result.status_code < 599]),
        "http_503_count": len([result for result in results if result.status_code == 503]),
        "timeout_count": len([result for result in results if result.status_code == 599]),
        "aggregate_503_count": len(aggregate_503),
        "max_elapsed_ms": max((result.elapsed_ms for result in results), default=0),
        "failures": [result.__dict__ for result in failures],
        "statuses": {result.path: result.status_code for result in sorted(results, key=lambda item: item.path)},
    }


def effective_config() -> dict[str, str | None]:
    names = [
        "QUOTE_DATA_PROVIDER",
        "HISTORY_DATA_PROVIDER",
        "MARKET_DATA_ALLOW_MOCK_FALLBACK",
        "MARKET_DATA_PERSISTENT_CACHE_ENABLED",
        "MARKET_DATA_HISTORY_COORDINATOR_CONCURRENCY",
    ]
    return {name: os.getenv(name) for name in names}


def selected_mode(args: argparse.Namespace) -> str:
    if args.soak:
        return "soak"
    if args.warm_cache:
        return "warm-cache"
    return "cold-cache"


def output_report(report: dict[str, Any], json_output: Path | None) -> None:
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if json_output is not None:
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
