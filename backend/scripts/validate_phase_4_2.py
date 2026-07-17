#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.cache.market_data_cache import (  # noqa: E402
    CachePolicy,
    CachePolicyRegistry,
    LayeredMarketDataCache,
    SQLiteMarketCache,
    build_history_cache_key,
    build_quote_cache_key,
)
from app.providers.finnhub_provider import ProviderRequestError  # noqa: E402
from app.providers.models import CandleData, HistoryData, ProviderCapabilities, ProviderHealth, QuoteData  # noqa: E402
from app.providers.router import MarketDataProviderRouter, ProviderCapabilityRegistry  # noqa: E402
from app.services.market_data_repository import MarketDataRepository, reset_market_data_repository  # noqa: E402


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


def make_history(symbol: str = "SPY", source: str = "fake", live: bool = True, days: int = 10) -> HistoryData:
    candles = [
        CandleData(
            timestamp=f"2026-01-{index + 1:02d}T00:00:00+00:00",
            open=100 + index,
            high=101 + index,
            low=99 + index,
            close=100.5 + index,
            volume=1000 + index,
        )
        for index in range(days)
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


def provider_health(provider: str = "fake", reachable: bool = True) -> ProviderHealth:
    return ProviderHealth(
        provider=provider,
        enabled=True,
        configured=True,
        reachable=reachable,
        last_successful_request=None,
        last_error=None if reachable else "provider unavailable",
        fallback_active=False,
        capabilities=ProviderCapabilities(
            quotes=True,
            daily_history=True,
            intraday_history=False,
            adjusted_history=True,
            volume=True,
        ),
    )


class CountingProvider:
    def __init__(self, provider: str = "fake", fail_quote: bool = False, fail_history: bool = False, delay: float = 0.0) -> None:
        self.provider = provider
        self.fail_quote = fail_quote
        self.fail_history = fail_history
        self.delay = delay
        self.quote_calls = 0
        self.history_calls = 0

    def get_quote(self, symbol: str) -> QuoteData:
        self.quote_calls += 1
        if self.delay:
            time.sleep(self.delay)
        if self.fail_quote:
            raise RuntimeError("quote provider unavailable")
        return make_quote(symbol, self.provider)

    def get_quotes(self, symbols: list[str]) -> list[QuoteData]:
        return [self.get_quote(symbol) for symbol in symbols]

    def get_history(self, symbol: str, resolution: str = "D", days: int = 240) -> HistoryData:
        self.history_calls += 1
        if self.delay:
            time.sleep(self.delay)
        if self.fail_history:
            raise RuntimeError("history provider unavailable")
        return make_history(symbol, self.provider, days=min(days, 30))

    def get_provider_health(self) -> ProviderHealth:
        return provider_health(self.provider, reachable=not (self.fail_quote or self.fail_history))

    def get_capabilities(self) -> ProviderCapabilities:
        return provider_health(self.provider).capabilities

    def get_index_snapshots(self) -> dict[str, Any]:
        return {}

    def get_sector_etfs(self) -> dict[str, Any]:
        return {}

    def get_watchlist_symbols(self) -> list[str]:
        return []


class TinyPolicyRegistry(CachePolicyRegistry):
    def for_domain(self, domain: str) -> CachePolicy:
        if domain in {"quotes", "daily_history", "technical_history"}:
            return CachePolicy(
                memory_ttl_seconds=1,
                persistent_ttl_seconds=1,
                stale_while_revalidate_seconds=60,
                allow_stale_on_error=True,
                persist=True,
                negative_ttl_seconds=1,
                max_entries=None,
                schema_version=1,
            )
        return super().for_domain(domain)


def make_cache(db_path: Path, policy_registry: CachePolicyRegistry | None = None) -> LayeredMarketDataCache:
    return LayeredMarketDataCache(
        persistent_cache=SQLiteMarketCache(db_path),
        policy_registry=policy_registry or CachePolicyRegistry(),
    )


def validate_sqlite_schema(tmp: Path) -> None:
    db_path = tmp / "schema.sqlite3"
    SQLiteMarketCache(db_path).initialize()
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute("PRAGMA table_info(market_data_cache)").fetchall()
    columns = {row[1] for row in rows}
    required = {
        "key",
        "domain",
        "provider",
        "source_state",
        "payload_json",
        "fetched_at",
        "market_timestamp",
        "expires_at",
        "stale_until",
        "created_at",
        "updated_at",
        "schema_version",
        "payload_hash",
        "size_bytes",
        "access_count",
        "last_accessed_at",
    }
    require(required <= columns, "SQLite schema", f"{len(columns)} columns present", "Create all Phase 4.2 cache columns.")


def validate_persistent_read_write(tmp: Path) -> None:
    db_path = tmp / "read-write.sqlite3"
    cache = make_cache(db_path)
    key = build_quote_cache_key("fake", "SPY")
    cache.set(key, make_quote(), domain="quotes", provider="fake", source_state="live")
    reopened = make_cache(db_path)
    cached, _age = reopened.get(key)
    require(isinstance(cached, QuoteData) and cached.symbol == "SPY", "persistent read/write", "quote survived cache recreation")


def validate_restart_persistence(tmp: Path) -> None:
    db_path = tmp / "restart.sqlite3"
    provider = CountingProvider()
    first = MarketDataRepository(provider=provider, data_provider="fake", cache=make_cache(db_path))
    first.get_history("SPY", days=10)
    second = MarketDataRepository(provider=provider, data_provider="fake", cache=make_cache(db_path))
    cached = second.get_history("SPY", days=10)
    require(provider.history_calls == 1 and cached.persistent_cache_hit, "restart persistence", "history loaded from persistent cache after repository recreation")


def validate_layered_order(tmp: Path) -> None:
    db_path = tmp / "layered.sqlite3"
    cache = make_cache(db_path)
    key = build_quote_cache_key("fake", "QQQ")
    cache.set(key, make_quote("QQQ"), domain="quotes", provider="fake", source_state="live")
    first, _ = make_cache(db_path).get(key)
    same_cache = make_cache(db_path)
    persistent_hit, _ = same_cache.get(key)
    memory_hit, _ = same_cache.get(key)
    require(
        isinstance(first, QuoteData)
        and isinstance(persistent_hit, QuoteData)
        and persistent_hit.persistent_cache_hit
        and isinstance(memory_hit, QuoteData)
        and memory_hit.memory_cache_hit,
        "layered cache order",
        "persistent hit warms memory, then memory serves next read",
    )


def validate_cache_policies() -> None:
    registry = CachePolicyRegistry()
    quote_policy = registry.for_domain("quotes")
    history_policy = registry.for_domain("daily_history")
    technical_policy = registry.for_domain("technical_history")
    require(
        quote_policy.persistent_ttl_seconds > 0
        and history_policy.stale_while_revalidate_seconds >= history_policy.persistent_ttl_seconds
        and technical_policy.persist,
        "cache policies",
        "quotes/history/technical history have persistent policies and stale windows",
    )


def validate_stale_while_revalidate(tmp: Path) -> None:
    db_path = tmp / "swr.sqlite3"
    cache = make_cache(db_path, TinyPolicyRegistry())
    key = build_history_cache_key("fake", "SPY", "D", 10)
    cache.set(key, make_history(days=10), domain="daily_history", provider="fake", source_state="live")
    time.sleep(1.1)
    provider = CountingProvider(delay=0.1)
    repo = MarketDataRepository(provider=provider, data_provider="fake", cache=cache)
    first = repo.get_history("SPY", days=10)
    time.sleep(0.2)
    require(
        first.source_state == "stale" and first.background_refresh_started and provider.history_calls == 1 and repo.background_refresh_count == 1,
        "stale-while-revalidate",
        "stale history returned immediately and one background refresh completed",
    )


def validate_background_deduplication(tmp: Path) -> None:
    db_path = tmp / "dedupe.sqlite3"
    cache = make_cache(db_path, TinyPolicyRegistry())
    key = build_history_cache_key("fake", "SPY", "D", 10)
    cache.set(key, make_history(days=10), domain="daily_history", provider="fake", source_state="live")
    time.sleep(1.1)
    provider = CountingProvider(delay=0.25)
    repo = MarketDataRepository(provider=provider, data_provider="fake", cache=cache)
    results: list[HistoryData] = []

    def read_history() -> None:
        results.append(repo.get_history("SPY", days=10))

    threads = [threading.Thread(target=read_history), threading.Thread(target=read_history)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    time.sleep(0.35)
    require(
        len(results) == 2 and all(item.source_state == "stale" for item in results) and provider.history_calls == 1,
        "background refresh deduplication",
        f"{provider.history_calls} provider refresh call(s) for two stale readers",
    )


def validate_failed_refresh_behavior(tmp: Path) -> None:
    db_path = tmp / "failed-refresh.sqlite3"
    cache = make_cache(db_path, TinyPolicyRegistry())
    key = build_history_cache_key("fake", "SPY", "D", 10)
    cache.set(key, make_history(days=10), domain="daily_history", provider="fake", source_state="live")
    time.sleep(1.1)
    repo = MarketDataRepository(provider=CountingProvider(fail_history=True), data_provider="fake", cache=cache)
    stale = repo.get_history("SPY", days=10)
    time.sleep(0.2)
    require(
        stale.source_state == "stale" and repo.background_refresh_failure_count == 1,
        "failed refresh behavior",
        "failed refresh kept last-known stale value",
    )


def validate_provider_capabilities() -> None:
    registry = ProviderCapabilityRegistry()
    finnhub = registry.get_capability("finnhub")
    test = registry.get_capability("test")
    require(
        finnhub.supports_quotes
        and finnhub.daily_history_access_state in {"restricted", "available", "unavailable", "unknown"}
        and test.supports_daily_history,
        "provider capabilities",
        f"finnhub history={finnhub.daily_history_access_state}; test history available",
    )


def validate_provider_routing() -> None:
    with patch.dict(os.environ, {"QUOTE_DATA_PROVIDER": "finnhub", "HISTORY_DATA_PROVIDER": "mock"}, clear=False):
        router = MarketDataProviderRouter()
        route_ok = router.get_provider_name_for("quotes") == "finnhub" and router.get_provider_name_for("daily_history") == "mock"
    with patch.dict(os.environ, {"HISTORY_DATA_PROVIDER": "finnhub"}, clear=False):
        restricted = False
        try:
            MarketDataProviderRouter().get_provider_for("daily_history")
        except ProviderRequestError as exc:
            restricted = exc.category == "permission"
    with patch.dict(os.environ, {"QUOTE_DATA_PROVIDER": "unknown_provider"}, clear=False):
        unsupported = False
        try:
            MarketDataProviderRouter().get_provider_for("quotes")
        except ProviderRequestError as exc:
            unsupported = exc.category == "unsupported_provider"
    require(route_ok and restricted and unsupported, "provider routing", "quotes/history route independently and unsupported providers are rejected")


def validate_source_metadata(tmp: Path) -> None:
    db_path = tmp / "source.sqlite3"
    provider = CountingProvider()
    repo = MarketDataRepository(provider=provider, data_provider="fake", cache=make_cache(db_path, TinyPolicyRegistry()))
    live = repo.get_quote("SPY")
    cached = repo.get_quote("SPY")

    stale_provider = CountingProvider(fail_history=True)
    stale_repo = MarketDataRepository(provider=stale_provider, data_provider="fake", cache=make_cache(db_path, TinyPolicyRegistry()))
    key = build_history_cache_key("fake", "SPY", "D", 10)
    stale_repo.cache.set(key, make_history(days=10), domain="daily_history", provider="fake", source_state="live")
    time.sleep(1.1)
    stale = stale_repo.get_history("SPY", days=10)
    repeated_stale = stale_repo.get_history("SPY", days=10)
    require(
        live.source_state == "live"
        and cached.source_state == "cached"
        and stale.source_state == "stale"
        and repeated_stale.source_state == "stale",
        "source-state metadata",
        "live, cached, and repeated stale reads keep explicit source_state",
    )


def validate_invalidation_cleanup(tmp: Path) -> None:
    db_path = tmp / "invalidate.sqlite3"
    cache = make_cache(db_path)
    quote_key = build_quote_cache_key("fake", "SPY")
    history_key = build_history_cache_key("fake", "SPY", "D", 10)
    cache.set(quote_key, make_quote(), domain="quotes", provider="fake", source_state="live")
    cache.set(history_key, make_history(days=10), domain="daily_history", provider="fake", source_state="live")
    deleted = cache.invalidate("history:fake")
    remaining, _ = cache.get(quote_key)
    cleanup = cache.cleanup()
    require(deleted >= 1 and isinstance(remaining, QuoteData) and "deleted" in cleanup, "invalidation and cleanup", f"deleted={deleted}; cleanup keys={sorted(cleanup.keys())}")


def validate_cache_diagnostics_endpoints(tmp: Path) -> None:
    from fastapi.testclient import TestClient
    from main import app

    db_path = tmp / "endpoint.sqlite3"
    env = {
        "DATA_PROVIDER": "test",
        "MARKET_DATA_PROVIDER": "test",
        "QUOTE_DATA_PROVIDER": "test",
        "HISTORY_DATA_PROVIDER": "test",
        "MARKET_DATA_CACHE_DB_PATH": str(db_path),
        "BACKGROUND_REFRESH_ENABLED": "false",
    }
    with patch.dict(os.environ, env, clear=False):
        reset_market_data_repository()
        with TestClient(app) as client:
            status = client.get("/market-data/cache/status")
            cleanup = client.post("/market-data/cache/cleanup")
            invalidate = client.post("/market-data/cache/invalidate", params={"prefix": "history:test"})
        reset_market_data_repository()
    status_json = status.json()
    require(
        status.status_code == 200
        and cleanup.status_code == 200
        and invalidate.status_code == 200
        and "persistent" in status_json
        and "market_cache.sqlite3" not in json.dumps(status_json),
        "cache diagnostics endpoints",
        "status/cleanup/invalidate respond without exposing cache path",
    )


def validate_technical_history_migration(tmp: Path) -> None:
    from app.services import candle_data

    db_path = tmp / "technical.sqlite3"
    repo = MarketDataRepository(provider=CountingProvider(), data_provider="fake", cache=make_cache(db_path))
    with patch("app.services.candle_data.get_market_data_provider", return_value=repo):
        candles = candle_data.get_ohlcv("SPY", days=10)
        metadata = candle_data.get_history_metadata("SPY", days=10)
    require(
        len(candles) > 0
        and metadata.get("provider") == "fake"
        and metadata.get("source_state") in {"live", "cached"}
        and "history_quality_score" in metadata,
        "technical-history migration",
        f"{len(candles)} candles with provider metadata",
    )


def validate_offline_and_corrupt_cache(tmp: Path) -> None:
    db_path = tmp / "offline.sqlite3"
    cache = make_cache(db_path, TinyPolicyRegistry())
    key = build_history_cache_key("fake", "SPY", "D", 10)
    cache.set(key, make_history(days=10), domain="daily_history", provider="fake", source_state="live")
    time.sleep(1.1)
    repo = MarketDataRepository(provider=CountingProvider(fail_history=True), data_provider="fake", cache=cache)
    stale = repo.get_history("SPY", days=10)
    corrupt_key = build_quote_cache_key("fake", "BAD")
    persistent = SQLiteMarketCache(db_path)
    persistent.initialize()
    with sqlite3.connect(db_path) as connection:
        now = datetime.now(timezone.utc)
        now_text = now.isoformat()
        future_text = datetime.fromtimestamp(time.time() + 60, tz=timezone.utc).isoformat()
        connection.execute(
            """
            INSERT OR REPLACE INTO market_data_cache (
                key, domain, provider, source_state, payload_json, fetched_at, market_timestamp,
                expires_at, stale_until, created_at, updated_at, schema_version, payload_hash, size_bytes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (corrupt_key, "quotes", "fake", "live", "{bad json", now_text, None, future_text, future_text, now_text, now_text, 1, None, 9),
        )
        connection.commit()
    corrupt = persistent.get(corrupt_key)
    require(
        stale.source_state == "stale" and corrupt.value is None and persistent.corrupt_entries >= 1,
        "offline/corrupt cache behavior",
        "offline provider returned stale cache and corrupt payload was discarded",
    )


def validate_security() -> None:
    gitignore = (PROJECT_ROOT / ".gitignore").read_text()
    env_example = (PROJECT_ROOT / ".env.example").read_text()
    data_ignored = "data/*.sqlite3" in gitignore and ".env" in gitignore
    no_example_secret = "FINNHUB_API_KEY=" in env_example and "sk-" not in env_example
    require(data_ignored and no_example_secret, "security", ".env and SQLite cache files are ignored; .env.example has placeholders")


def validate_frontend_static_contracts() -> None:
    data_usage = (REPO_ROOT / "frontend/src/app/data-usage.tsx").read_text()
    data_sources = (REPO_ROOT / "frontend/src/app/data-sources.tsx").read_text()
    api = (REPO_ROOT / "frontend/src/services/api.ts").read_text()
    types = (REPO_ROOT / "frontend/src/types/market.ts").read_text()
    require(
        "getMarketDataCacheStatus" in api
        and "ProviderCacheStatus" in types
        and "cache" in data_usage.lower()
        and "source" in data_sources.lower(),
        "frontend data usage/sources static contract",
        "frontend exposes cache/source diagnostics helpers",
    )


def validate_optional_live_quote(allow_live: bool) -> None:
    if not allow_live:
        record("optional live quote smoke", "SKIP", "disabled by default; rerun with --allow-live-quotes")
        return
    try:
        repo = MarketDataRepository(data_provider="finnhub")
        quote = repo.get_quote("SPY")
        require(quote.source_state in {"live", "delayed", "cached"} and quote.price > 0, "optional live quote smoke", f"source_state={quote.source_state}")
    except Exception as exc:
        record("optional live quote smoke", "FAIL", f"{type(exc).__name__}: {exc}", "Check FINNHUB_API_KEY and provider status.")


def run_validation(args: argparse.Namespace) -> int:
    RESULTS.clear()
    with tempfile.TemporaryDirectory(prefix="phase42-validator-") as tmp_dir:
        tmp = Path(tmp_dir)
        validate_sqlite_schema(tmp)
        validate_persistent_read_write(tmp)
        validate_restart_persistence(tmp)
        validate_layered_order(tmp)
        validate_cache_policies()
        validate_stale_while_revalidate(tmp)
        validate_background_deduplication(tmp)
        validate_failed_refresh_behavior(tmp)
        validate_provider_capabilities()
        validate_provider_routing()
        validate_source_metadata(tmp)
        validate_invalidation_cleanup(tmp)
        validate_cache_diagnostics_endpoints(tmp)
        validate_technical_history_migration(tmp)
        validate_offline_and_corrupt_cache(tmp)
        validate_security()
        validate_frontend_static_contracts()
        validate_optional_live_quote(args.allow_live_quotes)

        if args.keep_temp_db:
            keep_dir = PROJECT_ROOT / "tmp" / f"phase42-validator-{int(time.time())}"
            keep_dir.mkdir(parents=True, exist_ok=True)
            for path in tmp.glob("*.sqlite3*"):
                path.replace(keep_dir / path.name)
            record("temporary cache artifacts", "PASS", f"kept at {keep_dir}")

    summary = {
        "pass": sum(1 for result in RESULTS if result.status == "PASS"),
        "fail": sum(1 for result in RESULTS if result.status == "FAIL"),
        "skip": sum(1 for result in RESULTS if result.status == "SKIP"),
        "results": [asdict(result) for result in RESULTS],
    }
    if args.json_output:
        Path(args.json_output).write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(f"\nSUMMARY pass={summary['pass']} fail={summary['fail']} skip={summary['skip']}")
    return 1 if summary["fail"] else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Phase 4.2 market-data cache and routing behavior.")
    parser.add_argument("--mode", choices=["test", "ci"], default="test")
    parser.add_argument("--json-output")
    parser.add_argument("--keep-temp-db", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Reserved for future external smoke checks.")
    parser.add_argument("--allow-live-quotes", action="store_true", help="Opt into a real live quote smoke check.")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run_validation(parse_args()))
