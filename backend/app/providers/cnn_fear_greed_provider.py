from __future__ import annotations

import json
import os
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.cache.persistent_cache import get_persistent_value, set_persistent_value
from app.models.market import FearGreedComponent, FearGreedResponse
from app.providers.models import ProviderCapabilities, ProviderHealth

CNN_FEAR_GREED_ENDPOINT = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
CNN_FEAR_GREED_PAGE = "https://www.cnn.com/markets/fear-and-greed"
PARSER_VERSION = "cnn-fear-greed-v1"
OFFICIAL_CACHE_KEY = "cnn-fear-greed:official:v1"
ESTIMATE_CACHE_KEY = "cnn-fear-greed:estimate:v1"
MEMORY_TTL_SECONDS = 5 * 60
PERSISTENT_TTL_SECONDS = 15 * 60
STALE_SECONDS = 24 * 60 * 60

_memory_cache: dict[str, tuple[float, FearGreedResponse]] = {}


class CNNFearGreedError(RuntimeError):
    def __init__(self, message: str, *, category: str) -> None:
        super().__init__(message)
        self.category = category


@dataclass(frozen=True)
class FearGreedThreshold:
    low: int
    high: int
    label: str


CNN_FEAR_GREED_THRESHOLDS = (
    FearGreedThreshold(0, 24, "Extreme Fear"),
    FearGreedThreshold(25, 44, "Fear"),
    FearGreedThreshold(45, 55, "Neutral"),
    FearGreedThreshold(56, 75, "Greed"),
    FearGreedThreshold(76, 100, "Extreme Greed"),
)


CNN_COMPONENT_KEYS = {
    "market_momentum_sp500": ("market_momentum", "Market Momentum"),
    "stock_price_strength": ("stock_price_strength", "Stock Price Strength"),
    "stock_price_breadth": ("stock_price_breadth", "Stock Price Breadth"),
    "put_call_options": ("put_call_options", "Put and Call Options"),
    "market_volatility_vix": ("market_volatility", "Market Volatility"),
    "safe_haven_demand": ("safe_haven_demand", "Safe Haven Demand"),
    "junk_bond_demand": ("junk_bond_demand", "Junk Bond Demand"),
}


class CNNFearGreedProvider:
    def __init__(self, endpoint: str | None = None) -> None:
        self.endpoint = endpoint or os.getenv("CNN_FEAR_GREED_ENDPOINT") or CNN_FEAR_GREED_ENDPOINT
        self.timeout_seconds = float(os.getenv("CNN_FEAR_GREED_TIMEOUT_SECONDS", "4"))
        self.last_error: str | None = None
        self.last_successful_request: str | None = None

    def get_current_index(self, *, allow_stale: bool = True, fetch: bool = True) -> FearGreedResponse | None:
        cached = get_memory_cache(OFFICIAL_CACHE_KEY)
        if cached is not None:
            return cached.model_copy(update={"cache_status": "memory"})

        persistent = get_persistent_index(OFFICIAL_CACHE_KEY, allow_stale=False)
        if persistent is not None:
            set_memory_cache(OFFICIAL_CACHE_KEY, persistent)
            return persistent.model_copy(update={"cache_status": "persistent"})

        if fetch:
            try:
                official = self.fetch_current_index()
                set_memory_cache(OFFICIAL_CACHE_KEY, official)
                persist_index(OFFICIAL_CACHE_KEY, official)
                self.last_successful_request = now_iso()
                self.last_error = None
                return official
            except CNNFearGreedError as exc:
                self.last_error = exc.category

        if allow_stale:
            stale = get_persistent_index(OFFICIAL_CACHE_KEY, allow_stale=True)
            if stale is not None:
                return stale.model_copy(update={"stale": True, "cache_status": "stale"})
        return None

    def fetch_current_index(self) -> FearGreedResponse:
        payload = self.fetch_json()
        return parse_cnn_fear_greed_payload(payload)

    def fetch_json(self) -> dict[str, Any]:
        headers = {
            "Accept": "application/json,text/plain,*/*",
            "Referer": CNN_FEAR_GREED_PAGE,
            "User-Agent": os.getenv(
                "CNN_FEAR_GREED_USER_AGENT",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126 Safari/537.36",
            ),
        }
        request = urllib.request.Request(self.endpoint, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds, context=ssl_context()) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise CNNFearGreedError(f"CNN Fear & Greed source returned HTTP {exc.code}.", category="source_http") from exc
        except urllib.error.URLError as exc:
            raise CNNFearGreedError("CNN Fear & Greed source unavailable.", category="source_unavailable") from exc
        except TimeoutError as exc:
            raise CNNFearGreedError("CNN Fear & Greed source timed out.", category="source_timeout") from exc

        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise CNNFearGreedError("CNN Fear & Greed response was not valid JSON.", category="parser_json") from exc
        if not isinstance(data, dict):
            raise CNNFearGreedError("CNN Fear & Greed response shape changed.", category="parser_shape")
        return data

    def get_provider_health(self) -> ProviderHealth:
        return ProviderHealth(
            provider="cnn",
            enabled=True,
            configured=True,
            reachable=self.last_error is None,
            last_successful_request=self.last_successful_request,
            last_error=self.last_error,
            fallback_active=False,
            status="available" if self.last_error is None else "unavailable",
            capabilities=ProviderCapabilities(quotes=False, daily_history=False, intraday_history=False, adjusted_history=False, volume=False),
            message="CNN Fear & Greed structured dataviz source.",
        )


def parse_cnn_fear_greed_payload(payload: dict[str, Any]) -> FearGreedResponse:
    current = payload.get("fear_and_greed")
    if not isinstance(current, dict):
        raise CNNFearGreedError("CNN Fear & Greed current object missing.", category="parser_shape")
    score = normalize_score(current.get("score"))
    source_status = normalize_cnn_rating(current.get("rating")) or classify_fear_greed(score)
    source_timestamp = parse_timestamp(current.get("timestamp"))
    components = parse_components(payload)
    return FearGreedResponse(
        score=score,
        status=source_status,
        components=components,
        summary="Official CNN Fear & Greed Index value retrieved from CNN's structured dataviz source.",
        title="CNN Fear & Greed Index",
        subtitle=None,
        source="CNN",
        source_type="official",
        fetched_at=now_iso(),
        source_timestamp=source_timestamp,
        previous_close=optional_score(current.get("previous_close")),
        one_week_ago=optional_score(current.get("previous_1_week")),
        one_month_ago=optional_score(current.get("previous_1_month")),
        one_year_ago=optional_score(current.get("previous_1_year")),
        stale=False,
        confidence=100,
        parser_version=PARSER_VERSION,
        cache_status="fresh",
        partial=False,
        coverage_percent=100.0,
        coverage_components=7,
        required_components=7,
        overall_mode="official",
        dependencies_requested=1,
        dependencies_available=1,
        dependencies_missing=[],
        degraded_reasons=[],
    )


def parse_components(payload: dict[str, Any]) -> list[FearGreedComponent]:
    components: list[FearGreedComponent] = []
    for raw_key, (key, label) in CNN_COMPONENT_KEYS.items():
        raw = payload.get(raw_key)
        if not isinstance(raw, dict):
            components.append(missing_component(key, label, f"CNN component `{raw_key}` missing."))
            continue
        score = optional_score(raw.get("score"))
        if score is None:
            components.append(missing_component(key, label, f"CNN component `{raw_key}` has no score."))
            continue
        components.append(
            FearGreedComponent(
                key=key,
                label=label,
                score=score,
                status=normalize_cnn_rating(raw.get("rating")) or classify_fear_greed(score),
                explanation=f"{label} component as published in CNN's Fear & Greed dataviz payload.",
                source="CNN",
                source_timestamp=parse_timestamp(raw.get("timestamp")),
                data_state="official",
                confidence=100,
                missing=False,
                warnings=[],
            )
        )
    return components


def missing_component(key: str, label: str, warning: str) -> FearGreedComponent:
    return FearGreedComponent(
        key=key,
        label=label,
        score=0,
        status="Unavailable",
        explanation=warning,
        source="CNN",
        source_timestamp=None,
        data_state="missing",
        confidence=0,
        missing=True,
        warnings=[warning],
    )


def classify_fear_greed(score: int | None) -> str:
    if score is None:
        return "Unavailable"
    bounded = max(0, min(100, int(score)))
    for threshold in CNN_FEAR_GREED_THRESHOLDS:
        if threshold.low <= bounded <= threshold.high:
            return threshold.label
    return "Unavailable"


def normalize_cnn_rating(value: Any) -> str | None:
    text = str(value or "").replace("_", " ").strip().lower()
    mapping = {
        "extreme fear": "Extreme Fear",
        "fear": "Fear",
        "neutral": "Neutral",
        "greed": "Greed",
        "extreme greed": "Extreme Greed",
    }
    return mapping.get(text)


def normalize_score(value: Any) -> int:
    score = optional_score(value)
    if score is None:
        raise CNNFearGreedError("CNN Fear & Greed score missing.", category="parser_score")
    return score


def optional_score(value: Any) -> int | None:
    try:
        return max(0, min(100, round(float(value))))
    except (TypeError, ValueError):
        return None


def parse_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        raw = float(value)
        if raw > 10_000_000_000:
            raw = raw / 1000
        return datetime.fromtimestamp(raw, timezone.utc).isoformat()
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.isoformat()


def get_memory_cache(key: str) -> FearGreedResponse | None:
    cached = _memory_cache.get(key)
    if cached is None:
        return None
    expires_at, value = cached
    if expires_at <= time.time():
        _memory_cache.pop(key, None)
        return None
    return value.model_copy(deep=True)


def set_memory_cache(key: str, value: FearGreedResponse) -> None:
    _memory_cache[key] = (time.time() + MEMORY_TTL_SECONDS, value.model_copy(deep=True))


def clear_fear_greed_cache() -> None:
    _memory_cache.clear()


def get_persistent_index(key: str, *, allow_stale: bool) -> FearGreedResponse | None:
    result = get_persistent_value(key, allow_stale=allow_stale)
    if result is None:
        return None
    try:
        response = FearGreedResponse.model_validate(result.value)
    except Exception:
        return None
    return response.model_copy(update={"stale": bool(result.stale), "cache_status": "stale" if result.stale else "persistent"})


def persist_index(key: str, value: FearGreedResponse) -> None:
    set_persistent_value(
        key,
        value.model_dump(),
        ttl_seconds=PERSISTENT_TTL_SECONDS,
        stale_seconds=STALE_SECONDS,
        data_source=value.source,
        metadata={
            "source_type": value.source_type,
            "parser_version": PARSER_VERSION,
            "cache_key": key,
        },
    )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ssl_context() -> ssl.SSLContext | None:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()
