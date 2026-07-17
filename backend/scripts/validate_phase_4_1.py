#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.providers.finnhub_provider import (  # noqa: E402
    FinnhubMarketDataProvider,
    ProviderRequestError,
    categorize_http_error,
    normalize_finnhub_candles,
    should_retry_http,
)
from app.providers.models import (  # noqa: E402
    CandleData,
    HistoryData,
    NormalizedOHLCVBar,
    NormalizedPriceHistory,
    NormalizedQuote,
    ProviderCapabilities,
    ProviderHealth,
    QuoteData,
)
from app.providers.symbols import normalize_market_symbol  # noqa: E402
from app.services.market_data_repository import (  # noqa: E402
    MarketDataRepository,
    MemoryMarketDataCache,
    aggregate_source_state,
)


@dataclass
class CheckResult:
    name: str
    status: str
    evidence: str
    corrective_action: str | None = None


@dataclass(frozen=True)
class SecretScanIssue:
    path: str
    variable: str
    reason: str


RESULTS: list[CheckResult] = []


def record(name: str, status: str, evidence: str, corrective_action: str | None = None) -> None:
    RESULTS.append(CheckResult(name, status, evidence, corrective_action))
    print(f"{status:4} {name} - {evidence}")
    if corrective_action:
        print(f"     corrective action: {corrective_action}")


def require(condition: bool, name: str, evidence: str, corrective_action: str | None = None) -> None:
    record(name, "PASS" if condition else "FAIL", evidence, corrective_action if not condition else None)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_quote(symbol: str = "SPY", source: str = "fake", live: bool = True) -> QuoteData:
    return QuoteData(
        symbol=symbol,
        price=100.0,
        change=1.0,
        change_percent=1.0,
        open=99.0,
        high=101.0,
        low=98.0,
        previous_close=99.0,
        volume=1000,
        timestamp=now_iso(),
        source=source,
        is_live=live,
        is_stale=False,
        fallback_used=False,
    )


def make_history(symbol: str = "SPY", source: str = "fake", live: bool = True, days: int = 5) -> HistoryData:
    candles = [
        CandleData(
            timestamp=f"2026-01-{day:02d}T00:00:00+00:00",
            open=100 + day,
            high=101 + day,
            low=99 + day,
            close=100.5 + day,
            volume=1000,
        )
        for day in range(1, days + 1)
    ]
    return HistoryData(
        symbol=symbol,
        candles=candles,
        timeframe="D",
        source=source,
        is_live=live,
        is_stale=False,
        fallback_used=False,
        as_of=now_iso(),
        requested_days=days,
        returned_candles=days,
    )


class FakeProvider:
    def __init__(self, fail: bool = False, delay: float = 0.0, provider: str = "fake") -> None:
        self.fail = fail
        self.delay = delay
        self.provider = provider
        self.quote_calls = 0
        self.history_calls = 0

    def get_quote(self, symbol: str) -> QuoteData:
        self.quote_calls += 1
        if self.delay:
            time.sleep(self.delay)
        if self.fail:
            raise RuntimeError("provider down")
        return make_quote(symbol, self.provider)

    def get_quotes(self, symbols: list[str]) -> list[QuoteData]:
        return [self.get_quote(symbol) for symbol in symbols]

    def get_history(self, symbol: str, resolution: str = "D", days: int = 240) -> HistoryData:
        self.history_calls += 1
        if self.delay:
            time.sleep(self.delay)
        if self.fail:
            raise RuntimeError("provider down")
        return make_history(symbol, self.provider, days=min(days, 5))

    def get_provider_health(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.provider,
            enabled=True,
            configured=True,
            reachable=not self.fail,
            last_successful_request=None,
            last_error="provider down" if self.fail else None,
            fallback_active=False,
            capabilities=self.get_capabilities(),
        )

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(quotes=True, daily_history=True, intraday_history=False, adjusted_history=True, volume=True)

    def get_index_snapshots(self) -> dict[str, Any]:
        return {}

    def get_sector_etfs(self) -> dict[str, Any]:
        return {}

    def get_watchlist_symbols(self) -> list[str]:
        return []


def validate_models() -> None:
    quote = NormalizedQuote(
        symbol="SPY",
        price=100,
        open=99,
        high=101,
        low=98,
        previous_close=None,
        change=None,
        change_percent=None,
        volume=None,
        market_timestamp=datetime.now(timezone.utc),
        provider="fake",
        source_state="live",
        fetched_at=datetime.now(timezone.utc),
    )
    require(quote.previous_close is None and quote.volume is None, "normalized quote preserves null optionals", "previous_close and volume remain null")
    try:
        NormalizedQuote(
            symbol="BAD",
            price=-1,
            open=1,
            high=1,
            low=1,
            previous_close=None,
            change=None,
            change_percent=None,
            volume=0,
            market_timestamp=None,
            provider="fake",
            source_state="live",
            fetched_at=datetime.now(timezone.utc),
        )
        require(False, "normalized quote rejects negative price", "negative price accepted")
    except ValueError:
        record("normalized quote rejects negative price", "PASS", "negative price rejected")

    bars = [
        NormalizedOHLCVBar(timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc), open=11, high=12, low=10, close=11.5, volume=0),
        NormalizedOHLCVBar(timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc), open=10, high=11, low=9, close=10.5, volume=None),
        NormalizedOHLCVBar(timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc), open=10, high=11, low=9, close=10.5, volume=None),
    ]
    history = NormalizedPriceHistory(symbol="SPY", bars=bars, provider="fake", source_state="live", fetched_at=datetime.now(timezone.utc))
    require(len(history.bars) == 2 and history.bars[0].timestamp < history.bars[1].timestamp, "normalized history sorts/deduplicates bars", "2 unique ascending bars")
    try:
        NormalizedOHLCVBar(timestamp=datetime.now(timezone.utc), open=10, high=9, low=8, close=10, volume=0)
        require(False, "normalized history rejects invalid high", "invalid high accepted")
    except ValueError:
        record("normalized history rejects invalid high", "PASS", "high below close rejected")


def validate_repository() -> None:
    provider = FakeProvider()
    repo = MarketDataRepository(provider=provider, data_provider="fake", cache=MemoryMarketDataCache())
    first = repo.get_quote("spy")
    second = repo.get_quote(" SPY ")
    require(first.symbol == "SPY" and second.cache_hit and provider.quote_calls == 1, "quote cache and symbol normalization", f"calls={provider.quote_calls}, second_state={second.source_state}")

    provider_h = FakeProvider()
    repo_h = MarketDataRepository(provider=provider_h, data_provider="fake", cache=MemoryMarketDataCache())
    repo_h.get_history("SPY", days=5)
    history_cached = repo_h.get_history("SPY", days=5)
    require(history_cached.cache_hit and provider_h.history_calls == 1, "history cache hit", f"calls={provider_h.history_calls}, age={history_cached.cache_age_seconds}")

    provider_ttl = FakeProvider()
    repo_ttl = MarketDataRepository(provider=provider_ttl, data_provider="fake", cache=MemoryMarketDataCache())
    repo_ttl.quote_ttl_seconds = 1
    repo_ttl.get_quote("SPY")
    time.sleep(1.05)
    repo_ttl.get_quote("SPY")
    require(provider_ttl.quote_calls == 2, "quote TTL expiry refetches", f"calls={provider_ttl.quote_calls}")

    slow = FakeProvider(delay=0.05)
    repo_slow = MarketDataRepository(provider=slow, data_provider="fake", cache=MemoryMarketDataCache())
    results: list[QuoteData] = []
    threads = [threading.Thread(target=lambda: results.append(repo_slow.get_quote("SPY"))) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    require(slow.quote_calls == 1 and len(results) == 5, "in-flight quote deduplication", f"calls={slow.quote_calls}, results={len(results)}")

    slow_history = FakeProvider(delay=0.05)
    repo_slow_history = MarketDataRepository(provider=slow_history, data_provider="fake", cache=MemoryMarketDataCache())
    history_results: list[HistoryData] = []
    threads = [threading.Thread(target=lambda: history_results.append(repo_slow_history.get_history("SPY", days=5))) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    require(slow_history.history_calls == 1 and len(history_results) == 5, "in-flight history deduplication", f"calls={slow_history.history_calls}, results={len(history_results)}")

    failing = FakeProvider(fail=True, provider="finnhub")
    repo_fallback = MarketDataRepository(provider=failing, data_provider="finnhub", cache=MemoryMarketDataCache())
    repo_fallback.allow_mock_fallback = True
    fallback_quote = repo_fallback.get_quote("SPY")
    require(fallback_quote.source == "mock-fallback" and fallback_quote.source_state == "mock" and fallback_quote.fallback_used, "mock fallback is explicit", f"source={fallback_quote.source}, reason={fallback_quote.fallback_reason}")

    failing_disabled = FakeProvider(fail=True, provider="finnhub")
    repo_disabled = MarketDataRepository(provider=failing_disabled, data_provider="finnhub", cache=MemoryMarketDataCache())
    repo_disabled.allow_mock_fallback = False
    try:
        repo_disabled.get_quote("SPY")
        require(False, "fallback disabled returns controlled error", "no error raised")
    except ProviderRequestError:
        record("fallback disabled returns controlled error", "PASS", "ProviderRequestError raised")

    batch = repo.get_batch_quotes(["spy", "SPY", " qqq ", "QQQ", "INVALID"])
    symbols = [item.symbol for item in batch.quotes]
    require(symbols == ["SPY", "QQQ"] and "INVALID" in batch.unavailable_symbols, "batch dedup and partial invalid handling", f"symbols={symbols}, unavailable={batch.unavailable_symbols}")

    require(aggregate_source_state(["live", "cached"]) == "mixed", "source aggregation live+cached is mixed", "live+cached -> mixed")
    require(aggregate_source_state(["mock", "mock"]) == "mock", "source aggregation all mock", "mock+mock -> mock")
    require(aggregate_source_state(["unavailable", "live"]) == "mixed", "source aggregation unavailable+live not live", "unavailable+live -> mixed")


def validate_finnhub_helpers() -> None:
    require(should_retry_http(500) and should_retry_http(429), "retry policy retries transient/rate-limit", "500 and 429 retry")
    require(not should_retry_http(401) and categorize_http_error(401) == "authentication", "retry policy does not retry auth failure", "401 -> authentication")
    payload = {
        "s": "ok",
        "t": [1_704_153_600, 1_704_067_200, 1_704_067_200],
        "o": [11, 10, 10],
        "h": [13, 12, 12],
        "l": [10, 9, 9],
        "c": [12, 11, 11],
        "v": [200, 100, 100],
    }
    bars = normalize_finnhub_candles(payload, 10)
    require(len(bars) == 2 and bars[0].timestamp < bars[1].timestamp, "Finnhub candle normalization", f"bars={len(bars)}")


def validate_endpoints(mode: str) -> None:
    os.environ["DATA_PROVIDER"] = mode
    os.environ["MARKET_DATA_PROVIDER"] = mode
    os.environ["QUOTE_PROVIDER"] = mode
    os.environ["HISTORY_PROVIDER"] = mode
    os.environ["QUOTE_DATA_PROVIDER"] = mode
    os.environ["HISTORY_DATA_PROVIDER"] = mode
    os.environ["MARKET_DATA_ALLOW_MOCK_FALLBACK"] = "true"
    from app.services.market_data_repository import reset_market_data_repository

    reset_market_data_repository()
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)
    status = client.get("/market-data/status")
    require(status.status_code == 200, f"{mode} provider status endpoint", f"status={status.status_code}")
    status_json = status.json()
    require("FINNHUB_API_KEY" not in json.dumps(status_json) and "MARKET_DATA_API_KEY" not in json.dumps(status_json), f"{mode} status hides key names", "no provider key names in status payload")

    quote = client.get("/market/live/quote/%20spy%20")
    require(quote.status_code == 200 and quote.json().get("symbol") == "SPY", f"{mode} quote endpoint trims symbol", f"status={quote.status_code}, symbol={quote.json().get('symbol') if quote.status_code == 200 else None}")
    if quote.status_code == 200:
        payload = quote.json()
        require(payload.get("source_state") in {"mock", "cached", "live", "delayed", "stale"} and payload.get("fetched_at"), f"{mode} quote metadata", f"source={payload.get('source')}, state={payload.get('source_state')}")

    history = client.get("/market/live/history/SPY?days=20")
    ok_history = history.status_code == 200 and len(history.json().get("candles", [])) > 0
    require(ok_history, f"{mode} history endpoint non-empty", f"status={history.status_code}, candles={len(history.json().get('candles', [])) if history.status_code == 200 else 0}")
    if ok_history:
        candles = history.json()["candles"]
        timestamps = [item["timestamp"] for item in candles]
        valid_ohlc = all(item["high"] >= max(item["open"], item["low"], item["close"]) and item["low"] <= min(item["open"], item["high"], item["close"]) for item in candles)
        require(timestamps == sorted(set(timestamps)) and valid_ohlc, f"{mode} history timestamps/OHLC valid", f"unique={len(set(timestamps))}, valid_ohlc={valid_ohlc}")

    batch = client.post("/market/live/quotes", json={"symbols": ["SPY", "QQQ", "IWM", "INVALID"]})
    require(batch.status_code == 200, f"{mode} POST batch endpoint", f"status={batch.status_code}")
    if batch.status_code == 200:
        data = batch.json()
        require(len(data.get("items", [])) >= 3 and "INVALID" in data.get("unavailable_symbols", []), f"{mode} POST batch partial results", f"items={len(data.get('items', []))}, unavailable={data.get('unavailable_symbols')}")

    dedup = client.post("/market/live/quotes", json={"symbols": ["spy", "SPY", " qqq ", "QQQ"]})
    if dedup.status_code == 200:
        symbols = [item["symbol"] for item in dedup.json().get("items", [])]
        require(symbols == ["SPY", "QQQ"], f"{mode} POST batch deduplicates symbols", f"symbols={symbols}")
    else:
        require(False, f"{mode} POST batch deduplicates symbols", f"status={dedup.status_code}")

    indexes = client.get("/market/indexes")
    require(indexes.status_code == 200 and len(indexes.json().get("indexes", [])) == 4, f"{mode} index endpoint compatibility", f"status={indexes.status_code}")
    index_history = client.get("/market/indexes/SPY/history")
    require(index_history.status_code == 200 and len(index_history.json().get("closes", [])) > 0, f"{mode} index history compatibility", f"status={index_history.status_code}")


SECRET_ASSIGNMENT_RE = re.compile(
    r"(?P<variable>\b(?:FINNHUB_API_KEY|MARKET_DATA_API_KEY|POLYGON_API_KEY|TWELVE_DATA_API_KEY|FMP_API_KEY|token))"
    r"[ \t]*=[ \t]*"
    r"(?P<quote>['\"]?)"
    r"(?P<value><[^>]*>|[^'\"\s`#]*)",
    re.IGNORECASE,
)
PLACEHOLDER_SECRET_VALUES = {
    "",
    "<real key>",
    "<real-key>",
    "<your key>",
    "<your-key>",
    "<key>",
    "<api key>",
    "<api-key>",
    "<token>",
    "your_key_here",
    "your-api-key",
    "your_api_key",
    "your_finnhub_key",
    "redacted",
    "changeme",
    "placeholder",
    "example",
}


def is_ignored_env_path(path: Path) -> bool:
    name = path.name
    if name == ".env.example":
        return False
    return name == ".env" or name.endswith(".env") or ".env." in name


def is_placeholder_secret_value(value: str) -> bool:
    normalized = value.strip().strip("'\"").strip()
    if normalized.lower() in PLACEHOLDER_SECRET_VALUES:
        return True
    if normalized.startswith("<") and normalized.endswith(">"):
        return True
    return False


def secret_issue_reason(variable: str, value: str, path: Path) -> str | None:
    if is_placeholder_secret_value(value):
        return None
    if path.name == ".env.example":
        return f"{variable} in .env.example has a non-placeholder value"
    return f"{variable} has an assigned non-placeholder value"


def scan_secret_files(roots: list[Path], report_base: Path) -> list[SecretScanIssue]:
    issues: list[SecretScanIssue] = []
    for root in roots:
        if not root.exists():
            continue
        files = [root] if root.is_file() else [path for path in root.rglob("*") if path.is_file() and "__pycache__" not in str(path)]
        for path in files:
            if is_ignored_env_path(path):
                continue
            try:
                text = path.read_text(errors="ignore")
            except OSError:
                continue
            for match in SECRET_ASSIGNMENT_RE.finditer(text):
                variable = match.group("variable")
                value = match.group("value") or ""
                reason = secret_issue_reason(variable, value, path)
                if not reason:
                    continue
                try:
                    issue_path = str(path.relative_to(report_base))
                except ValueError:
                    issue_path = str(path)
                issues.append(SecretScanIssue(path=issue_path, variable=variable, reason=reason))
    return issues


def validate_security_scan() -> None:
    roots = [PROJECT_ROOT / "app", PROJECT_ROOT / "tests", PROJECT_ROOT / ".env.example", PROJECT_ROOT.parent / "frontend" / "src", PROJECT_ROOT.parent / "docs"]
    issues = scan_secret_files(roots, PROJECT_ROOT.parent)
    for issue in issues:
        print(f"     secret issue: file={issue.path} variable={issue.variable} reason={issue.reason}")
    corrective_action = "; ".join(f"{issue.path} ({issue.variable}: {issue.reason})" for issue in issues[:5])
    require(not issues, "secret scan app/frontend/docs/tests", f"issues={len(issues)}", corrective_action if issues else None)


def validate_live_if_enabled(allow_live: bool) -> None:
    key_present = bool(os.getenv("FINNHUB_API_KEY") or os.getenv("MARKET_DATA_API_KEY"))
    if not allow_live or not key_present:
        record("genuine Finnhub smoke test", "SKIP", "real Finnhub key not configured or --allow-live not supplied")
        return
    repo = MarketDataRepository(data_provider="finnhub")
    try:
        quote = repo.get_quote("SPY")
        history = repo.get_history("SPY", days=30)
        require(quote.source == "finnhub" and quote.source_state in {"live", "cached", "delayed"}, "genuine Finnhub quote", f"source={quote.source}, state={quote.source_state}")
        require(history.source == "finnhub" and len(history.candles) > 0, "genuine Finnhub history", f"source={history.source}, candles={len(history.candles)}")
    except Exception as exc:
        record("genuine Finnhub smoke test", "FAIL", f"{type(exc).__name__}: sanitized provider validation failed", "Check API key, account candle permissions, and network connectivity.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 4.1 market-data provider foundation.")
    parser.add_argument("--mode", choices=["mock", "test", "finnhub"], default="test")
    parser.add_argument("--base-url", default=None, help="Reserved for future running-backend validation. TestClient is used when omitted.")
    parser.add_argument("--allow-live", action="store_true", help="Allow genuine Finnhub network smoke tests when a key is configured.")
    parser.add_argument("--json-output", default=None)
    args = parser.parse_args()

    validate_models()
    validate_repository()
    validate_finnhub_helpers()
    validate_endpoints(args.mode)
    if args.mode != "mock":
        validate_endpoints("mock")
    if args.mode != "test":
        validate_endpoints("test")
    validate_security_scan()
    validate_live_if_enabled(args.allow_live)

    if args.json_output:
        Path(args.json_output).write_text(json.dumps([asdict(item) for item in RESULTS], indent=2))

    failed = [item for item in RESULTS if item.status == "FAIL"]
    print("")
    print(f"Phase 4.1 validation complete: {len([item for item in RESULTS if item.status == 'PASS'])} PASS, {len(failed)} FAIL, {len([item for item in RESULTS if item.status == 'SKIP'])} SKIP")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
