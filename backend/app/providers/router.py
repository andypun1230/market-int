from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

from app.providers.base import MarketDataProvider
from app.providers.finnhub_provider import ProviderRequestError

BACKEND_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = BACKEND_ROOT / ".env"
if load_dotenv is not None:
    load_dotenv(dotenv_path=ENV_PATH)

ProviderDomain = Literal["quotes", "daily_history"]
AccessState = Literal["available", "restricted", "unavailable", "unknown"]


@dataclass
class DomainCapability:
    provider: str
    supports_quotes: bool
    supports_batch_quotes: bool
    supports_daily_history: bool
    supports_intraday_history: bool
    supports_macro: bool = False
    supports_economic_calendar: bool = False
    quote_access_state: AccessState = "unknown"
    daily_history_access_state: AccessState = "unknown"
    notes: list[str] = field(default_factory=list)
    last_restricted_at: str | None = None
    restriction_reason: str | None = None

    def model_dump(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "supports_quotes": self.supports_quotes,
            "supports_batch_quotes": self.supports_batch_quotes,
            "supports_daily_history": self.supports_daily_history,
            "supports_intraday_history": self.supports_intraday_history,
            "supports_macro": self.supports_macro,
            "supports_economic_calendar": self.supports_economic_calendar,
            "quote_access_state": self.quote_access_state,
            "daily_history_access_state": self.daily_history_access_state,
            "notes": self.notes,
            "last_restricted_at": self.last_restricted_at,
            "restriction_reason": self.restriction_reason,
        }


class ProviderCapabilityRegistry:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._restrictions: dict[tuple[str, ProviderDomain], tuple[float, str]] = {}
        self.restriction_ttl_seconds = env_int("MARKET_DATA_CAPABILITY_RESTRICTION_TTL_SECONDS", 3600)

    def get_capability(self, provider_name: str) -> DomainCapability:
        name = normalize_provider_name(provider_name)
        if name in {"test", "generated_test_data"}:
            return DomainCapability(
                provider="generated_test_data",
                supports_quotes=True,
                supports_batch_quotes=True,
                supports_daily_history=True,
                supports_intraday_history=False,
                quote_access_state="available",
                daily_history_access_state="available",
                notes=["Generated deterministic test data."],
            )
        if name == "mock":
            return DomainCapability(
                provider="mock",
                supports_quotes=True,
                supports_batch_quotes=True,
                supports_daily_history=True,
                supports_intraday_history=False,
                quote_access_state="available",
                daily_history_access_state="available",
                notes=["Deterministic mock data."],
            )
        if name in {"finnhub", "live", "auto"}:
            history_override = os.getenv("FINNHUB_DAILY_HISTORY_ACCESS_STATE")
            history_state: AccessState = "restricted"
            notes = ["Finnhub quote access is available.", "Daily candles returned HTTP 403 under the configured plan."]
            if history_override in {"available", "restricted", "unavailable", "unknown"}:
                history_state = history_override  # type: ignore[assignment]
                notes = ["Finnhub capability overridden by FINNHUB_DAILY_HISTORY_ACCESS_STATE."]
            restriction = self._get_restriction("finnhub", "daily_history")
            if restriction:
                history_state = "restricted"
                notes.append(restriction)
            return DomainCapability(
                provider="finnhub",
                supports_quotes=True,
                supports_batch_quotes=False,
                supports_daily_history=history_state == "available",
                supports_intraday_history=False,
                quote_access_state="available",
                daily_history_access_state=history_state,
                notes=notes,
                restriction_reason=restriction,
            )
        if name in {"polygon", "massive"}:
            configured = bool(os.getenv("POLYGON_API_KEY") or os.getenv("HISTORY_DATA_API_KEY"))
            history_override = os.getenv("POLYGON_DAILY_HISTORY_ACCESS_STATE")
            history_state: AccessState = "available" if configured else "unavailable"
            notes = [
                "Polygon/Massive daily stock aggregate history provider.",
                "Internal provider id remains polygon.",
            ]
            if history_override in {"available", "restricted", "unavailable", "unknown"}:
                history_state = history_override  # type: ignore[assignment]
                notes.append("Capability overridden by POLYGON_DAILY_HISTORY_ACCESS_STATE.")
            restriction = self._get_restriction("polygon", "daily_history")
            if restriction:
                history_state = "restricted"
                notes.append(restriction)
            return DomainCapability(
                provider="polygon",
                supports_quotes=False,
                supports_batch_quotes=False,
                supports_daily_history=history_state == "available",
                supports_intraday_history=False,
                quote_access_state="unavailable",
                daily_history_access_state=history_state,
                notes=notes,
                restriction_reason=restriction,
            )
        return DomainCapability(
            provider=name,
            supports_quotes=False,
            supports_batch_quotes=False,
            supports_daily_history=False,
            supports_intraday_history=False,
            quote_access_state="unknown",
            daily_history_access_state="unknown",
            notes=["Provider is not implemented."],
        )

    def mark_restricted(self, provider_name: str, domain: ProviderDomain, reason: str) -> None:
        with self._lock:
            self._restrictions[(normalize_provider_name(provider_name), domain)] = (time.time(), reason)

    def _get_restriction(self, provider_name: str, domain: ProviderDomain) -> str | None:
        with self._lock:
            item = self._restrictions.get((normalize_provider_name(provider_name), domain))
            if not item:
                return None
            created_at, reason = item
            if time.time() - created_at > self.restriction_ttl_seconds:
                self._restrictions.pop((normalize_provider_name(provider_name), domain), None)
                return None
            return reason

    def status(self, providers: list[str]) -> dict[str, object]:
        return {normalize_provider_name(provider): self.get_capability(provider).model_dump() for provider in providers}


class MarketDataProviderRouter:
    def __init__(self, *, capability_registry: ProviderCapabilityRegistry | None = None) -> None:
        self.capability_registry = capability_registry or ProviderCapabilityRegistry()
        self._providers: dict[str, MarketDataProvider] = {}
        self.quote_provider_name = normalize_provider_name(
            os.getenv("QUOTE_DATA_PROVIDER") or os.getenv("QUOTE_PROVIDER") or os.getenv("DATA_PROVIDER") or os.getenv("MARKET_DATA_PROVIDER") or "test"
        )
        self.history_provider_name = normalize_provider_name(
            os.getenv("HISTORY_DATA_PROVIDER") or os.getenv("HISTORY_PROVIDER") or os.getenv("DATA_PROVIDER") or os.getenv("MARKET_DATA_PROVIDER") or "test"
        )

    def get_provider_for(self, domain: ProviderDomain) -> MarketDataProvider:
        provider_name = self.get_provider_name_for(domain)
        capability = self.capability_registry.get_capability(provider_name)
        if domain == "daily_history":
            if capability.daily_history_access_state == "restricted":
                raise ProviderRequestError(f"{provider_name} daily history is restricted by provider capability.", category="permission")
            if capability.daily_history_access_state != "available" or not capability.supports_daily_history:
                raise ProviderRequestError(f"{provider_name} daily history is unavailable.", category="unsupported_provider")
        if domain == "quotes":
            if capability.quote_access_state == "restricted":
                raise ProviderRequestError(f"{provider_name} quotes are restricted by provider capability.", category="permission")
            if capability.quote_access_state != "available" or not capability.supports_quotes:
                raise ProviderRequestError(f"{provider_name} quotes are unavailable.", category="unsupported_provider")
        return self._get_provider(provider_name)

    def get_provider_name_for(self, domain: ProviderDomain) -> str:
        return self.quote_provider_name if domain == "quotes" else self.history_provider_name

    def get_configured_provider_name_for(self, domain: ProviderDomain) -> str:
        return self.get_provider_name_for(domain)

    def mark_restricted(self, provider_name: str, domain: ProviderDomain, reason: str) -> None:
        self.capability_registry.mark_restricted(provider_name, domain, reason)

    def status(self) -> dict[str, object]:
        providers = sorted({self.quote_provider_name, self.history_provider_name, "finnhub", "polygon", "mock", "generated_test_data"})
        return {
            "configured_quote_provider": self.quote_provider_name,
            "configured_history_provider": self.history_provider_name,
            "capabilities": self.capability_registry.status(providers),
        }

    def _get_provider(self, provider_name: str) -> MarketDataProvider:
        name = normalize_provider_name(provider_name)
        if name not in self._providers:
            from app.providers.selector import build_provider

            self._providers[name] = build_provider(name)
        return self._providers[name]


def normalize_provider_name(provider_name: str | None) -> str:
    value = (provider_name or "test").strip().lower()
    if value == "generated_test_data":
        return value
    if value == "live":
        return "finnhub"
    if value == "massive":
        return "polygon"
    return value


def is_stable_permission_error(error: BaseException) -> bool:
    if isinstance(error, ProviderRequestError) and error.category == "permission":
        return True
    cause = getattr(error, "__cause__", None)
    return isinstance(cause, ProviderRequestError) and cause.category == "permission"


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default
