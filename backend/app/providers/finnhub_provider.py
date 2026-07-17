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
from urllib.parse import urlencode
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
from app.providers.models import (
    CandleData,
    HistoryData,
    ProviderCapabilities,
    ProviderHealth,
    QuoteData,
)
from app.providers.symbols import normalize_market_symbol

BACKEND_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = BACKEND_ROOT / ".env"
if load_dotenv is not None:
    load_dotenv(dotenv_path=ENV_PATH)


class ProviderRequestError(RuntimeError):
    def __init__(self, message: str, *, category: str = "provider_error") -> None:
        super().__init__(message)
        self.category = category


class FinnhubMarketDataProvider(MarketDataProvider):
    provider_name = "finnhub"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("FINNHUB_API_KEY") or os.getenv("MARKET_DATA_API_KEY")
        self.base_url = (base_url or os.getenv("MARKET_DATA_BASE_URL") or "https://finnhub.io/api/v1").rstrip("/")
        self.timeout_seconds = float(timeout_seconds if timeout_seconds is not None else os.getenv("MARKET_DATA_TIMEOUT_SECONDS", "8"))
        self.max_retries = int(max_retries if max_retries is not None else os.getenv("MARKET_DATA_MAX_RETRIES", "2"))
        self.log_provider_calls = str(os.getenv("MARKET_DATA_LOG_PROVIDER_CALLS", "false")).lower() == "true"
        self.debug_provider = env_bool("MARKET_DATA_DEBUG_PROVIDER", False) or env_bool("FINNHUB_DEBUG", False)
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
            f"ssl_context={self.ssl_context_source}"
        )

    def get_quote(self, symbol: str) -> QuoteData:
        normalized = normalize_market_symbol(symbol, apply_alias=True)
        self._debug(f"quote requested raw_symbol={symbol!r} normalized_symbol={normalized}")
        started = time.perf_counter()
        payload = self._request_json("/quote", {"symbol": normalized})
        duration_ms = (time.perf_counter() - started) * 1000
        self._record_success(duration_ms)

        price = optional_float(payload.get("c"))
        previous_close = optional_float(payload.get("pc"))
        if price is None or price <= 0:
            self._record_failure(f"No quote data available for {normalized}.", category="no_data", duration_ms=duration_ms)
            self._debug(
                "quote rejected "
                f"symbol={normalized} "
                f"reason=no_data "
                f"price={price} "
                f"previous_close={previous_close} "
                f"payload_keys={sorted(payload.keys())}"
            )
            raise ProviderRequestError(f"No quote data available for {normalized}", category="no_data")

        change = optional_float(payload.get("d"))
        if change is None and previous_close:
            change = round(price - previous_close, 4)
        change_percent = optional_float(payload.get("dp"))
        if change_percent is None and previous_close:
            change_percent = round(((price - previous_close) / previous_close) * 100, 4)

        market_timestamp = finnhub_timestamp(payload.get("t"))
        quote = QuoteData(
            symbol=normalized,
            price=price,
            change=change or 0.0,
            change_percent=change_percent or 0.0,
            open=optional_float(payload.get("o")),
            high=optional_float(payload.get("h")),
            low=optional_float(payload.get("l")),
            previous_close=previous_close,
            volume=None,
            timestamp=market_timestamp.isoformat(),
            source=self.provider_name,
            is_live=True,
            is_stale=False,
            fallback_used=False,
            provider=self.provider_name,
            source_state="live",
            fetched_at=now_iso(),
        )
        self._debug(
            "normalized quote "
            f"symbol={quote.symbol} "
            f"price={quote.price} "
            f"change={quote.change} "
            f"change_percent={quote.change_percent} "
            f"timestamp={quote.timestamp} "
            f"source={quote.source}"
        )
        return quote

    def get_history(self, symbol: str, resolution: str = "D", days: int = 240) -> HistoryData:
        normalized = normalize_market_symbol(symbol, apply_alias=True)
        normalized_resolution = "D" if resolution.upper() in {"D", "1D"} else resolution.upper()
        if normalized_resolution != "D":
            self._debug(f"history rejected symbol={normalized} resolution={resolution} reason=unsupported_resolution")
            raise ProviderRequestError("Only daily history is supported in Phase 4.1", category="unsupported_resolution")

        end = datetime.now(timezone.utc)
        # Calendar days exceed trading days, so request extra range for daily bars.
        start = end - timedelta(days=max(days * 2, days + 30))
        request_params = {
            "symbol": normalized,
            "resolution": "D",
            "from": int(start.timestamp()),
            "to": int(end.timestamp()),
        }
        self._debug(
            "history requested "
            f"raw_symbol={symbol!r} "
            f"normalized_symbol={normalized} "
            f"resolution={request_params['resolution']} "
            f"from={request_params['from']} "
            f"to={request_params['to']} "
            f"url_without_key={self.base_url}/stock/candle?{urlencode(request_params)}"
        )
        started = time.perf_counter()
        payload = self._request_json("/stock/candle", request_params)
        duration_ms = (time.perf_counter() - started) * 1000

        status = str(payload.get("s") or "")
        if status != "ok":
            self._record_failure(
                f"Finnhub daily history unavailable for {normalized}: status={status or 'missing'}",
                category="no_data",
                duration_ms=duration_ms,
            )
            self._debug(
                "history rejected "
                f"symbol={normalized} "
                f"reason=no_data "
                f"provider_status={status or 'missing'} "
                f"payload_keys={sorted(payload.keys())}"
            )
            raise ProviderRequestError(f"No daily history available for {normalized}", category="no_data")

        bars = normalize_finnhub_candles(payload, days)
        self._debug(
            "history normalized "
            f"symbol={normalized} "
            f"provider_status={status} "
            f"raw_candles={len(payload.get('t') or [])} "
            f"normalized_candles={len(bars)} "
            f"first={bars[0].timestamp if bars else None} "
            f"last={bars[-1].timestamp if bars else None}"
        )
        if not bars:
            self._record_failure(f"No valid daily history bars for {normalized}.", category="invalid_data", duration_ms=duration_ms)
            raise ProviderRequestError(f"No valid daily history bars for {normalized}", category="invalid_data")
        self._record_success(duration_ms)
        return HistoryData(
            symbol=normalized,
            candles=bars,
            timeframe="D",
            source=self.provider_name,
            is_live=True,
            is_stale=False,
            fallback_used=False,
            as_of=now_iso(),
            adjusted=True,
            requested_days=days,
            returned_candles=len(bars),
            error_message=None,
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
            message="Finnhub API key configured." if configured else "Finnhub API key is not configured.",
        )

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            quotes=True,
            daily_history=True,
            intraday_history=False,
            adjusted_history=False,
            volume=True,
        )

    def get_index_snapshots(self) -> dict[str, Any]:
        return {"indexes": [self.get_quote(symbol).model_dump() for symbol in ["SPY", "QQQ", "IWM", "DIA"]]}

    def get_sector_etfs(self) -> dict[str, Any]:
        symbols = ["XLK", "XLF", "XLV", "XLY", "XLP", "XLE", "XLI", "XLU", "XLC", "XLRE", "XLB"]
        return {"items": [self.get_quote(symbol).model_dump() for symbol in symbols]}

    def get_watchlist_symbols(self) -> list[str]:
        return ["MU", "NVDA", "ARM", "SNDK"]

    def _request_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            self._record_failure("Finnhub API key is not configured.", category="not_configured")
            self._debug("request blocked key_loaded=no key_length=0 reason=not_configured")
            raise ProviderRequestError("Finnhub API key is not configured.", category="not_configured")

        safe_params = {**params, "token": self.api_key}
        url = f"{self.base_url}{path}?{urlencode(safe_params)}"
        safe_url = f"{self.base_url}{path}?{urlencode(params)}"
        attempt = 0
        while True:
            started = time.perf_counter()
            try:
                if self.log_provider_calls:
                    print(f"Provider request started provider=finnhub path={path} symbols={params.get('symbol')}")
                self._debug(f"request started url_without_key={safe_url} attempt={attempt + 1}")
                request = Request(url, headers={"Accept": "application/json", "User-Agent": "market-intelligence-app/phase-4.1"})
                with urlopen(request, timeout=self.timeout_seconds, context=self.ssl_context) as response:
                    body = response.read().decode("utf-8")
                    status_code = response.status
                self._debug(f"response received status={status_code} body={redact_body(body)}")
                data = json.loads(body)
                if isinstance(data, dict) and data.get("error"):
                    self._debug(f"provider error payload reason=provider_error body={redact_body(body)}")
                    raise ProviderRequestError("Provider returned an error payload.", category="provider_error")
                return data if isinstance(data, dict) else {}
            except HTTPError as exc:
                duration_ms = (time.perf_counter() - started) * 1000
                category = categorize_http_error(exc.code)
                try:
                    error_body = exc.read().decode("utf-8")
                except Exception:
                    error_body = ""
                self._debug(
                    "http error "
                    f"status={exc.code} "
                    f"category={category} "
                    f"body={redact_body(error_body)} "
                    f"url_without_key={safe_url}"
                )
                if exc.code == 429:
                    self.rate_limit_state = "rate_limited"
                if should_retry_http(exc.code) and attempt < self.max_retries:
                    time.sleep(backoff_seconds(attempt))
                    attempt += 1
                    continue
                self._record_failure(f"{category} from Finnhub ({exc.code})", category=category, duration_ms=duration_ms)
                raise ProviderRequestError(f"Finnhub request failed: {category}", category=category) from exc
            except (TimeoutError, URLError) as exc:
                duration_ms = (time.perf_counter() - started) * 1000
                self._debug(
                    "network error "
                    f"type={type(exc).__name__} "
                    f"reason={safe_exception_text(exc)} "
                    f"url_without_key={safe_url}"
                )
                if attempt < self.max_retries:
                    time.sleep(backoff_seconds(attempt))
                    attempt += 1
                    continue
                self._record_failure("Finnhub request timed out or network failed.", category="network", duration_ms=duration_ms)
                raise ProviderRequestError("Finnhub request timed out or network failed.", category="network") from exc
            except json.JSONDecodeError as exc:
                duration_ms = (time.perf_counter() - started) * 1000
                self._debug(f"json error reason=invalid_json url_without_key={safe_url}")
                self._record_failure(f"Invalid JSON from Finnhub at {safe_url}", category="invalid_json", duration_ms=duration_ms)
                raise ProviderRequestError("Finnhub returned invalid JSON.", category="invalid_json") from exc

    def _debug(self, message: str) -> None:
        if self.debug_provider:
            print(f"[FINNHUB DEBUG] {message}")

    def _record_success(self, duration_ms: float) -> None:
        self.last_success_at = now_iso()
        self.last_response_time_ms = round(duration_ms, 2)
        self.last_error = None
        self.recent_error_count = 0
        self.rate_limit_state = None

    def _record_failure(self, message: str, *, category: str, duration_ms: float | None = None) -> None:
        self.last_failure_at = now_iso()
        self.last_error = message
        self.last_response_time_ms = round(duration_ms, 2) if duration_ms is not None else self.last_response_time_ms
        self.recent_error_count += 1
        if category == "rate_limited":
            self.rate_limit_state = "rate_limited"


def normalize_finnhub_candles(payload: dict[str, Any], days: int) -> list[CandleData]:
    timestamps = payload.get("t") or []
    opens = payload.get("o") or []
    highs = payload.get("h") or []
    lows = payload.get("l") or []
    closes = payload.get("c") or []
    volumes = payload.get("v") or []
    bars: list[CandleData] = []
    seen: set[str] = set()
    for index, timestamp in enumerate(timestamps):
        try:
            bar_time = finnhub_timestamp(timestamp)
            open_price = float(opens[index])
            high = float(highs[index])
            low = float(lows[index])
            close = float(closes[index])
            volume = float(volumes[index]) if index < len(volumes) and volumes[index] is not None else 0.0
        except (IndexError, TypeError, ValueError):
            continue
        if min(open_price, high, low, close) <= 0 or high < max(open_price, low, close) or low > min(open_price, high, close):
            continue
        key = bar_time.isoformat()
        if key in seen:
            continue
        seen.add(key)
        bars.append(CandleData(timestamp=key, open=open_price, high=high, low=low, close=close, volume=volume))
    return sorted(bars, key=lambda item: item.timestamp)[-days:]


def optional_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        number = float(value)
        return number if number == number else None
    except (TypeError, ValueError):
        return None


def finnhub_timestamp(value: Any) -> datetime:
    try:
        timestamp = int(value)
        if timestamp > 0:
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        pass
    return datetime.now(timezone.utc)


def should_retry_http(status_code: int) -> bool:
    return status_code == 429 or 500 <= status_code <= 599


def categorize_http_error(status_code: int) -> str:
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


def backoff_seconds(attempt: int) -> float:
    return min(1.5, 0.2 * (2 ** attempt))


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def redact_body(body: str, max_length: int = 1200) -> str:
    redacted = re.sub(
        r'(?i)("?(?:token|api_key|apikey|access_key|finnhub_api_key|market_data_api_key)"?\s*[:=]\s*")([^"]+)(")',
        r"\1REDACTED\3",
        body,
    )
    if len(redacted) > max_length:
        return f"{redacted[:max_length]}...<truncated>"
    return redacted


def safe_exception_text(exc: BaseException, max_length: int = 300) -> str:
    text = str(getattr(exc, "reason", exc))
    text = redact_body(text, max_length=max_length)
    return text.replace("\n", " ")


def build_verified_ssl_context() -> tuple[ssl.SSLContext | None, str]:
    if certifi is not None:
        try:
            return ssl.create_default_context(cafile=certifi.where()), "certifi"
        except Exception:
            pass
    return None, "system-default"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
