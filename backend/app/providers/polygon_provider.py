from __future__ import annotations

import json
import os
import re
import ssl
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

try:
    import certifi
except ImportError:  # pragma: no cover
    certifi = None

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

from app.providers.base import MarketDataProvider
from app.providers.finnhub_provider import ProviderRequestError
from app.providers.models import CandleData, HistoryData, ProviderCapabilities, ProviderHealth, QuoteData
from app.providers.symbols import normalize_market_symbol

BACKEND_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = BACKEND_ROOT / ".env"
if load_dotenv is not None:
    load_dotenv(dotenv_path=ENV_PATH)


class PolygonMarketDataProvider(MarketDataProvider):
    """Polygon/Massive daily OHLCV history provider.

    The provider uses Polygon's current Massive-branded stocks aggregate endpoint,
    while keeping the stable internal provider id as "polygon".
    """

    provider_name = "polygon"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        max_pages: int | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("POLYGON_API_KEY") or os.getenv("HISTORY_DATA_API_KEY")
        self.base_url = (base_url or os.getenv("POLYGON_BASE_URL") or "https://api.polygon.io").rstrip("/")
        self.timeout_seconds = float(timeout_seconds if timeout_seconds is not None else os.getenv("POLYGON_TIMEOUT_SECONDS", "15"))
        self.max_retries = int(max_retries if max_retries is not None else os.getenv("POLYGON_MAX_RETRIES", "2"))
        self.max_pages = int(max_pages if max_pages is not None else os.getenv("POLYGON_MAX_PAGES", "10"))
        self.history_limit = int(os.getenv("POLYGON_HISTORY_LIMIT", "50000"))
        self.adjusted = env_bool("POLYGON_HISTORY_ADJUSTED", True)
        self.debug_provider = env_bool("POLYGON_DEBUG", False)
        self.ssl_context, self.ssl_context_source = build_verified_ssl_context()
        self.last_success_at: str | None = None
        self.last_failure_at: str | None = None
        self.last_error: str | None = None
        self.recent_error_count = 0
        self.last_response_time_ms: float | None = None
        self.rate_limit_state: str | None = None
        self._debug(
            "initialized "
            f"key_loaded={'yes' if self.api_key else 'no'} "
            f"key_length={len(self.api_key or '')} "
            f"configured={bool(self.api_key)} "
            f"base_url={self.base_url} "
            f"adjusted={self.adjusted} "
            f"limit={self.history_limit} "
            f"ssl_context={self.ssl_context_source}"
        )

    def get_quote(self, symbol: str) -> QuoteData:
        raise ProviderRequestError("Polygon quotes are not implemented in Phase 4.3.", category="unsupported_provider")

    def get_history(self, symbol: str, resolution: str = "D", days: int = 240) -> HistoryData:
        normalized = normalize_polygon_symbol(symbol)
        normalized_resolution = normalize_daily_resolution(resolution)
        if normalized_resolution != "D":
            raise ProviderRequestError("Only daily Polygon history is supported in Phase 4.3.", category="unsupported_resolution")

        safe_days = max(1, min(int(days), 1500))
        to_date = datetime.now(timezone.utc).date()
        calendar_days = max(safe_days * 2, safe_days + 35)
        from_date = to_date - timedelta(days=calendar_days)
        path = f"/v2/aggs/ticker/{normalized}/range/1/day/{from_date.isoformat()}/{to_date.isoformat()}"
        params = {
            "adjusted": str(self.adjusted).lower(),
            "sort": "asc",
            "limit": min(max(1, self.history_limit), 50000),
        }
        self._debug(
            "history requested "
            f"symbol={normalized} "
            f"resolution={normalized_resolution} "
            f"from={from_date.isoformat()} "
            f"to={to_date.isoformat()} "
            f"adjusted={self.adjusted} "
            f"url_without_key={self.base_url}{path}?{urlencode(params)}"
        )
        started = time.perf_counter()
        payloads = self._request_paginated_json(path, params)
        duration_ms = (time.perf_counter() - started) * 1000

        bars = normalize_polygon_aggregates(payloads, requested_days=safe_days)
        if not bars:
            self._record_failure(f"No valid Polygon daily history bars for {normalized}.", category="no_data", duration_ms=duration_ms)
            raise ProviderRequestError(f"No valid Polygon daily history bars for {normalized}", category="no_data")
        self._record_success(duration_ms)
        self._debug(
            "history normalized "
            f"symbol={normalized} "
            f"pages={len(payloads)} "
            f"raw_results={sum(len(item.get('results') or []) for item in payloads)} "
            f"normalized_bars={len(bars)} "
            f"first={bars[0].timestamp} "
            f"last={bars[-1].timestamp} "
            f"latency_ms={round(duration_ms, 2)}"
        )
        return HistoryData(
            symbol=normalized,
            candles=bars,
            timeframe="D",
            source=self.provider_name,
            is_live=True,
            is_stale=False,
            fallback_used=False,
            as_of=now_iso(),
            adjusted=bool(payloads[-1].get("adjusted", self.adjusted)),
            requested_days=safe_days,
            returned_candles=len(bars),
            provider=self.provider_name,
            source_state="live",
            fetched_at=now_iso(),
        )

    def get_provider_health(self) -> ProviderHealth:
        configured = bool(self.api_key)
        status = "healthy" if configured and self.recent_error_count == 0 else "degraded" if configured else "not_configured"
        return ProviderHealth(
            provider=self.provider_name,
            enabled=configured,
            configured=configured,
            reachable=configured and self.recent_error_count < 3,
            last_successful_request=self.last_success_at,
            last_error=self.last_error,
            fallback_active=False,
            capabilities=self.get_capabilities(),
            status=status,
            checked_at=now_iso(),
            response_time_ms=self.last_response_time_ms,
            last_success_at=self.last_success_at,
            last_failure_at=self.last_failure_at,
            recent_error_count=self.recent_error_count,
            rate_limit_state=self.rate_limit_state,
            message="Polygon/Massive history API key configured." if configured else "Polygon API key is not configured.",
        )

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            quotes=False,
            daily_history=True,
            intraday_history=False,
            adjusted_history=True,
            volume=True,
        )

    def get_index_snapshots(self) -> dict[str, Any]:
        return {}

    def get_sector_etfs(self) -> dict[str, Any]:
        return {}

    def get_watchlist_symbols(self) -> list[str]:
        return []

    def _request_paginated_json(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        if not self.api_key:
            self._record_failure("Polygon API key is not configured.", category="not_configured")
            raise ProviderRequestError("Polygon API key is not configured.", category="not_configured")

        payloads: list[dict[str, Any]] = []
        next_url: str | None = f"{self.base_url}{path}?{urlencode({**params, 'apiKey': self.api_key})}"
        page = 0
        seen_urls: set[str] = set()
        while next_url:
            page += 1
            if page > max(1, self.max_pages):
                self._debug(f"pagination stopped reason=max_pages max_pages={self.max_pages}")
                break
            safe_url = redact_url(next_url)
            if safe_url in seen_urls:
                self._debug("pagination stopped reason=repeated_next_url")
                break
            seen_urls.add(safe_url)
            payload = self._request_json_url(next_url, safe_url=safe_url, page=page)
            payloads.append(payload)
            raw_next = payload.get("next_url")
            next_url = with_api_key(str(raw_next), self.api_key) if raw_next else None
        return payloads

    def _request_json_url(self, url: str, *, safe_url: str, page: int) -> dict[str, Any]:
        attempt = 0
        while True:
            started = time.perf_counter()
            try:
                self._debug(f"request started page={page} url_without_key={safe_url} attempt={attempt + 1}")
                request = Request(url, headers={"Accept": "application/json", "User-Agent": "market-intelligence-app/phase-4.3"})
                with urlopen(request, timeout=self.timeout_seconds, context=self.ssl_context) as response:
                    body = response.read().decode("utf-8")
                    status_code = response.status
                self._debug(f"response received page={page} status={status_code} body={redact_body(body)}")
                data = json.loads(body)
                if not isinstance(data, dict):
                    raise ProviderRequestError("Polygon returned a non-object JSON payload.", category="invalid_json")
                status = str(data.get("status") or "").upper()
                if data.get("error") or status in {"ERROR", "NOT_AUTHORIZED"}:
                    category = categorize_polygon_payload(data)
                    raise ProviderRequestError("Polygon returned an error payload.", category=category)
                if status in {"DELAYED", "OK"} or "results" in data:
                    return data
                if status in {"NOT_FOUND", "NO_DATA"}:
                    raise ProviderRequestError("Polygon returned no data.", category="no_data")
                return data
            except ProviderRequestError as exc:
                duration_ms = (time.perf_counter() - started) * 1000
                self._record_failure(str(exc), category=exc.category, duration_ms=duration_ms)
                raise
            except HTTPError as exc:
                duration_ms = (time.perf_counter() - started) * 1000
                category = categorize_http_error(exc.code)
                try:
                    error_body = exc.read().decode("utf-8")
                except Exception:
                    error_body = ""
                self._debug(
                    "http error "
                    f"page={page} status={exc.code} category={category} body={redact_body(error_body)} url_without_key={safe_url}"
                )
                if exc.code == 429:
                    self.rate_limit_state = "rate_limited"
                if should_retry_http(exc.code) and attempt < self.max_retries:
                    time.sleep(backoff_seconds(attempt, retry_after=exc.headers.get("Retry-After")))
                    attempt += 1
                    continue
                self._record_failure(f"{category} from Polygon ({exc.code})", category=category, duration_ms=duration_ms)
                raise ProviderRequestError(f"Polygon request failed: {category}", category=category) from exc
            except (TimeoutError, URLError) as exc:
                duration_ms = (time.perf_counter() - started) * 1000
                self._debug(f"network error page={page} type={type(exc).__name__} reason={safe_exception_text(exc)} url_without_key={safe_url}")
                if attempt < self.max_retries:
                    time.sleep(backoff_seconds(attempt))
                    attempt += 1
                    continue
                self._record_failure("Polygon request timed out or network failed.", category="network", duration_ms=duration_ms)
                raise ProviderRequestError("Polygon request timed out or network failed.", category="network") from exc
            except json.JSONDecodeError as exc:
                duration_ms = (time.perf_counter() - started) * 1000
                self._debug(f"json error page={page} reason=invalid_json url_without_key={safe_url}")
                self._record_failure("Polygon returned invalid JSON.", category="invalid_json", duration_ms=duration_ms)
                raise ProviderRequestError("Polygon returned invalid JSON.", category="invalid_json") from exc

    def _debug(self, message: str) -> None:
        if self.debug_provider:
            print(f"[POLYGON DEBUG] {message}")

    def _record_success(self, duration_ms: float) -> None:
        self.last_success_at = now_iso()
        self.last_response_time_ms = round(duration_ms, 2)
        self.last_error = None
        self.recent_error_count = 0
        self.rate_limit_state = None

    def _record_failure(self, message: str, *, category: str, duration_ms: float | None = None) -> None:
        self.last_failure_at = now_iso()
        self.last_error = f"{category}: {redact_body(message, max_length=240)}"
        self.last_response_time_ms = round(duration_ms, 2) if duration_ms is not None else self.last_response_time_ms
        self.recent_error_count += 1
        if category == "rate_limited":
            self.rate_limit_state = "rate_limited"


def normalize_polygon_aggregates(payloads: list[dict[str, Any]], *, requested_days: int) -> list[CandleData]:
    bars: list[CandleData] = []
    seen: set[str] = set()
    for payload in payloads:
        for item in payload.get("results") or []:
            try:
                timestamp = polygon_timestamp(item.get("t"))
                open_price = float(item["o"])
                high = float(item["h"])
                low = float(item["l"])
                close = float(item["c"])
                volume = float(item.get("v") or 0)
                vwap = optional_float(item.get("vw"))
                transactions = optional_int(item.get("n"))
            except (KeyError, TypeError, ValueError, OSError):
                continue
            if min(open_price, high, low, close) <= 0:
                continue
            if volume < 0:
                continue
            if high < max(open_price, low, close) or low > min(open_price, high, close):
                continue
            key = timestamp.isoformat()
            if key in seen:
                continue
            seen.add(key)
            bars.append(CandleData(
                timestamp=key,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
                vwap=vwap,
                transactions=transactions,
            ))
    return sorted(bars, key=lambda item: item.timestamp)[-requested_days:]


def normalize_polygon_symbol(symbol: str) -> str:
    normalized = normalize_market_symbol(symbol, apply_alias=True)
    # Polygon/Massive accepts class-share notation with dots for common U.S. equities.
    return normalized.replace("-", ".")


def normalize_daily_resolution(resolution: str) -> str:
    value = str(resolution or "D").strip().upper()
    if value in {"D", "1D", "DAY", "DAILY"}:
        return "D"
    return value


def polygon_timestamp(value: Any) -> datetime:
    timestamp_ms = int(value)
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)


def optional_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        number = float(value)
        return number if number == number else None
    except (TypeError, ValueError):
        return None


def optional_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def categorize_http_error(status_code: int) -> str:
    if status_code == 400:
        return "bad_request"
    if status_code == 401:
        return "authentication"
    if status_code == 403:
        return "permission"
    if status_code == 404:
        return "invalid_symbol"
    if status_code == 429:
        return "rate_limited"
    if 500 <= status_code <= 599:
        return "transient"
    return "http_error"


def categorize_polygon_payload(payload: dict[str, Any]) -> str:
    text = " ".join(str(payload.get(key, "")) for key in ("status", "error", "message")).lower()
    if "not authorized" in text or "api key" in text:
        return "authentication"
    if "permission" in text or "access" in text or "plan" in text:
        return "permission"
    if "not found" in text or "ticker" in text:
        return "invalid_symbol"
    if "rate" in text:
        return "rate_limited"
    return "provider_error"


def should_retry_http(status_code: int) -> bool:
    return status_code == 429 or 500 <= status_code <= 599


def backoff_seconds(attempt: int, retry_after: str | None = None) -> float:
    if retry_after:
        try:
            return min(float(retry_after), 2.0)
        except ValueError:
            pass
    return min(2.0, 0.25 * (2 ** attempt))


def with_api_key(url: str, api_key: str) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["apiKey"] = api_key
    return urlunparse(parsed._replace(query=urlencode(query)))


def redact_url(url: str) -> str:
    parsed = urlparse(url)
    query = [(key, "REDACTED" if key.lower() in {"apikey", "api_key", "token"} else value) for key, value in parse_qsl(parsed.query, keep_blank_values=True)]
    return urlunparse(parsed._replace(query=urlencode(query)))


def redact_body(body: str, max_length: int = 1200) -> str:
    redacted = re.sub(
        r'(?i)("?(?:token|api_key|apikey|access_key|polygon_api_key|history_data_api_key)"?\s*[:=]\s*")([^"]+)(")',
        r"\1REDACTED\3",
        body,
    )
    redacted = re.sub(r"(?i)(apiKey=)[^&\\s]+", r"\1REDACTED", redacted)
    if len(redacted) > max_length:
        return f"{redacted[:max_length]}...<truncated>"
    return redacted


def safe_exception_text(exc: BaseException, max_length: int = 300) -> str:
    text = str(getattr(exc, "reason", exc))
    return redact_body(text, max_length=max_length).replace("\n", " ")


def build_verified_ssl_context() -> tuple[ssl.SSLContext | None, str]:
    if certifi is not None:
        try:
            return ssl.create_default_context(cafile=certifi.where()), "certifi"
        except Exception:
            pass
    return None, "system-default"


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
