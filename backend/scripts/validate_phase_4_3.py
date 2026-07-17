#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.cache.market_data_cache import LayeredMarketDataCache, SQLiteMarketCache  # noqa: E402
from app.providers.polygon_provider import PolygonMarketDataProvider, normalize_polygon_aggregates, redact_url  # noqa: E402
from app.providers.router import MarketDataProviderRouter  # noqa: E402
from app.services.market_data_repository import MarketDataRepository  # noqa: E402


@dataclass
class CheckResult:
    name: str
    status: str
    evidence: str
    corrective_action: str | None = None


RESULTS: list[CheckResult] = []


def record(name: str, status: str, evidence: str, corrective_action: str | None = None) -> None:
    RESULTS.append(CheckResult(name, status, evidence, corrective_action))
    print(f"{status:4} {name} - {evidence}")
    if corrective_action:
        print(f"     corrective action: {corrective_action}")


def require(condition: bool, name: str, evidence: str, corrective_action: str | None = None) -> None:
    record(name, "PASS" if condition else "FAIL", evidence, None if condition else corrective_action)


class FakeHTTPResponse:
    status = 200

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


class PolygonHTTPStub:
    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self.payloads = list(payloads)
        self.urls: list[str] = []

    def __call__(self, request, timeout=None, context=None):
        self.urls.append(request.full_url)
        if not self.payloads:
            raise RuntimeError("No stub payload remaining")
        return FakeHTTPResponse(self.payloads.pop(0))


def polygon_payload(symbol: str = "SPY", *, next_url: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ticker": symbol,
        "adjusted": True,
        "queryCount": 3,
        "resultsCount": 3,
        "status": "OK",
        "results": [
            {"t": 1704153600000, "o": 100, "h": 102, "l": 99, "c": 101, "v": 1000, "vw": 100.5, "n": 10},
            {"t": 1704240000000, "o": 101, "h": 103, "l": 100, "c": 102, "v": 0},
            {"t": 1704326400000, "o": 102, "h": 104, "l": 101, "c": 103, "v": 1500},
        ],
    }
    if next_url:
        payload["next_url"] = next_url
    return payload


def validate_test_mode() -> None:
    bars = normalize_polygon_aggregates([polygon_payload()], requested_days=10)
    require(len(bars) == 3 and bars[0].timestamp < bars[-1].timestamp, "Polygon normalization", f"bars={len(bars)}")
    require(bars[0].vwap == 100.5 and bars[0].transactions == 10 and bars[1].volume == 0, "Polygon optional fields", "vwap/transactions/zero volume preserved")
    require("secret" not in redact_url("https://api.polygon.io/v2/aggs?apiKey=secret"), "Polygon redaction", "apiKey removed from diagnostic URL")

    second_page = {
        "ticker": "SPY",
        "adjusted": True,
        "status": "OK",
        "results": [
            {"t": 1704412800000, "o": 103, "h": 105, "l": 102, "c": 104, "v": 1500},
            {"t": 1704672000000, "o": 104, "h": 106, "l": 103, "c": 105, "v": 1600},
        ],
    }
    stub = PolygonHTTPStub([polygon_payload("SPY", next_url="https://api.polygon.io/v2/aggs/ticker/SPY/range/1/day/2024-01-01/2024-01-05?cursor=abc"), second_page])
    provider = PolygonMarketDataProvider(api_key="test-key", base_url="https://api.polygon.io", max_retries=0)
    with patch("app.providers.polygon_provider.urlopen", side_effect=stub):
        history = provider.get_history("SPY", days=5)
    require(
        history.provider == "polygon"
        and history.source_state == "live"
        and history.adjusted
        and history.returned_candles == 5
        and len(stub.urls) == 2
        and "apiKey=test-key" in stub.urls[1],
        "Polygon request/pagination",
        f"urls={len(stub.urls)}, bars={history.returned_candles}, adjusted={history.adjusted}",
    )

    with patch.dict(os.environ, {"QUOTE_DATA_PROVIDER": "finnhub", "HISTORY_DATA_PROVIDER": "polygon", "POLYGON_API_KEY": "configured"}, clear=False):
        router = MarketDataProviderRouter()
        require(
            router.get_provider_name_for("quotes") == "finnhub"
            and router.get_provider_name_for("daily_history") == "polygon"
            and router.capability_registry.get_capability("polygon").daily_history_access_state == "available",
            "Provider routing",
            "quotes=finnhub, daily_history=polygon",
        )

    stub = PolygonHTTPStub([polygon_payload("NVDA")])
    provider = PolygonMarketDataProvider(api_key="test-key", base_url="https://api.polygon.io", max_retries=0)
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "market_cache.sqlite3"
        repo = MarketDataRepository(provider=provider, data_provider="polygon", cache=LayeredMarketDataCache(persistent_cache=SQLiteMarketCache(db_path)))
        with patch("app.providers.polygon_provider.urlopen", side_effect=stub):
            first = repo.get_history("NVDA", days=3)
            second = repo.get_history("NVDA", days=3)
        reopened = MarketDataRepository(provider=provider, data_provider="polygon", cache=LayeredMarketDataCache(persistent_cache=SQLiteMarketCache(db_path)))
        persisted = reopened.get_history("NVDA", days=3)
    require(
        first.provider == "polygon"
        and second.source_state == "cached"
        and persisted.persistent_cache_hit
        and len(stub.urls) == 1,
        "Cache integration",
        "first call wrote cache, second memory hit, repository recreation persistent hit",
    )


def validate_live_mode(symbols: list[str], json_records: list[dict[str, Any]]) -> None:
    if not (os.getenv("POLYGON_API_KEY") or os.getenv("HISTORY_DATA_API_KEY")):
        record("Polygon live key", "FAIL", "POLYGON_API_KEY is not configured", "Set POLYGON_API_KEY in backend/.env for live validation.")
        return

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "phase43-live.sqlite3"
        provider = PolygonMarketDataProvider()
        repo = MarketDataRepository(provider=provider, data_provider="polygon", cache=LayeredMarketDataCache(persistent_cache=SQLiteMarketCache(db_path)))
        for symbol in symbols:
            before_calls = provider.last_success_at
            history = repo.get_history(symbol, days=370 if symbol.upper() == "SPY" else 190)
            cached = repo.get_history(symbol, days=370 if symbol.upper() == "SPY" else 190)
            reopened = MarketDataRepository(provider=provider, data_provider="polygon", cache=LayeredMarketDataCache(persistent_cache=SQLiteMarketCache(db_path)))
            persisted = reopened.get_history(symbol, days=370 if symbol.upper() == "SPY" else 190)
            candles = history.candles
            valid = bool(candles) and candles == sorted(candles, key=lambda item: item.timestamp)
            valid = valid and all(item.high >= max(item.open, item.low, item.close) and item.low <= min(item.open, item.high, item.close) and item.volume >= 0 for item in candles)
            require(
                valid and history.provider == "polygon" and cached.cache_hit and persisted.persistent_cache_hit,
                f"Live Polygon history {symbol.upper()}",
                f"bars={len(candles)}, first={candles[0].timestamp if candles else None}, last={candles[-1].timestamp if candles else None}, cached={cached.source_state}",
            )
            json_records.append({
                "provider": history.provider,
                "symbol": symbol.upper(),
                "requested_days": history.requested_days,
                "normalized_count": len(candles),
                "first_date": candles[0].timestamp if candles else None,
                "last_date": candles[-1].timestamp if candles else None,
                "adjusted": history.adjusted,
                "cache_source": cached.source_state,
                "persistent_cache_hit": persisted.persistent_cache_hit,
                "last_success_before": before_calls,
                "last_success_after": provider.last_success_at,
            })


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Phase 4.3 Polygon/Massive daily history integration.")
    parser.add_argument("--mode", choices=["test", "live"], default="test")
    parser.add_argument("--symbols", default="SPY,AAPL,NVDA")
    parser.add_argument("--json-output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    json_records: list[dict[str, Any]] = []
    if args.mode == "test":
        validate_test_mode()
    else:
        symbols = [symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip()]
        validate_live_mode(symbols, json_records)

    summary = {
        "pass": sum(1 for item in RESULTS if item.status == "PASS"),
        "fail": sum(1 for item in RESULTS if item.status == "FAIL"),
        "skip": sum(1 for item in RESULTS if item.status == "SKIP"),
        "records": json_records,
        "results": [asdict(item) for item in RESULTS],
    }
    if args.json_output:
        Path(args.json_output).write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(f"\nSUMMARY pass={summary['pass']} fail={summary['fail']} skip={summary['skip']}")
    return 1 if summary["fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
