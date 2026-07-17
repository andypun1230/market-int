from datetime import datetime, timezone

from app.providers.intelligence_models import (
    MarketSentimentData,
    SentimentComponentData,
    SourceMetadata,
)
from app.providers.models import ProviderCapabilities, ProviderHealth
from app.providers.sentiment_base import SentimentProvider
from app.services.basket_data import calculate_history_return
from app.services.breadth import calculate_market_breadth
from app.services.candle_data import get_symbol_history
from app.services.regime import build_market_regime


class MarketProxySentimentProvider(SentimentProvider):
    """Live-aware sentiment proxy built from allowed market data inputs.

    This is APInvest Market Sentiment, not the official CNN Fear & Greed Index.
    Put/call remains a fallback component unless a compliant source is configured.
    """

    def get_put_call_statistics(self) -> dict[str, object]:
        return {
            "total_put_call_ratio": 0.78,
            "equity_put_call_ratio": 0.71,
            "index_put_call_ratio": 0.96,
            "as_of": now_iso(),
            "metadata": mock_metadata(["Put/call ratio is deterministic fallback; no compliant live source configured."]),
        }

    def get_volatility_inputs(self) -> dict[str, object]:
        regime = build_market_regime()
        return {
            "vix": regime.volatility.vix,
            "status": regime.volatility.status,
            "metadata": mixed_metadata(["VIX remains a provider-independent proxy value in this phase."]),
        }

    def get_sentiment_health(self) -> ProviderHealth:
        return ProviderHealth(
            provider="market_proxy",
            enabled=True,
            configured=True,
            reachable=True,
            last_successful_request=now_iso(),
            last_error=None,
            fallback_active=False,
            capabilities=ProviderCapabilities(
                quotes=False,
                daily_history=True,
                intraday_history=False,
                adjusted_history=True,
                volume=True,
            ),
        )

    def get_market_sentiment(self) -> MarketSentimentData:
        components = [
            self.build_momentum_component(),
            self.build_price_strength_component(),
            self.build_breadth_component(),
            self.build_put_call_component(),
            self.build_volatility_component(),
            self.build_safe_haven_component(),
            self.build_junk_bond_component(),
        ]
        score = round(sum(component.score for component in components) / len(components), 2)
        live_components = [component for component in components if component.metadata.is_live]
        fallback_components = [component for component in components if component.metadata.fallback_used]
        metadata = SourceMetadata(
            source="market_proxy" if live_components else "mock",
            is_live=bool(live_components) and not fallback_components,
            is_stale=False,
            fallback_used=bool(fallback_components),
            as_of=now_iso(),
            quality_score=round(sum(component.metadata.quality_score or 60 for component in components) / len(components), 2),
            warnings=[
                "APInvest Market Sentiment uses market-derived proxy inputs.",
                "Put/call ratio is fallback unless a compliant live source is configured.",
            ],
        )
        return MarketSentimentData(
            score=score,
            status=classify_sentiment(score),
            confidence=metadata.quality_score or 70,
            components=components,
            summary=f"APInvest Market Sentiment is {classify_sentiment(score)} with live-aware market momentum and breadth inputs.",
            metadata=metadata,
        )

    def build_momentum_component(self) -> SentimentComponentData:
        history, validation = get_symbol_history("SPY", days=180, minimum_candles=60)
        value = calculate_history_return(history, "1m") or 0.0
        score = normalize(value, -8, 8)
        return component(
            "market_momentum",
            "Market Momentum",
            score,
            value,
            "rising" if value > 0 else "falling",
            "SPY one-month momentum is used as a live-aware risk appetite proxy.",
            history.source,
            history.is_live,
            history.fallback_used,
            validation.get("quality_score", 70),
        )

    def build_price_strength_component(self) -> SentimentComponentData:
        breadth = calculate_market_breadth()
        value = breadth.percent_above_200ema
        return component(
            "stock_price_strength",
            "Stock Price Strength",
            value,
            value,
            "healthy" if value >= 55 else "weakening",
            "Percent above 200EMA in the core liquid-stock universe proxies price strength.",
            breadth.overall_mode or "mock",
            breadth.overall_mode == "live",
            bool(breadth.fallback_used),
            breadth.history_quality_score or 70,
        )

    def build_breadth_component(self) -> SentimentComponentData:
        breadth = calculate_market_breadth()
        value = breadth.percent_above_50ema
        return component(
            "stock_price_breadth",
            "Stock Price Breadth",
            value,
            value,
            "healthy" if value >= 60 else "mixed",
            "Core liquid-stock breadth is used; this is not full exchange breadth.",
            breadth.overall_mode or "mock",
            breadth.overall_mode == "live",
            bool(breadth.fallback_used),
            breadth.history_quality_score or 70,
        )

    def build_put_call_component(self) -> SentimentComponentData:
        stats = self.get_put_call_statistics()
        ratio = float(stats["total_put_call_ratio"])
        return SentimentComponentData(
            key="put_call_ratio",
            label="Put/Call Ratio",
            score=normalize(1.15 - ratio, 0.0, 0.7),
            status="Neutral" if ratio < 1 else "Hedging Elevated",
            value=ratio,
            previous_value=None,
            trend="fallback",
            explanation="Put/call ratio uses deterministic fallback until a compliant live source is enabled.",
            metadata=stats["metadata"],
        )

    def build_volatility_component(self) -> SentimentComponentData:
        inputs = self.get_volatility_inputs()
        vix = float(inputs["vix"])
        score = 85 if vix < 22 else 55 if vix < 28 else 25
        return SentimentComponentData(
            key="market_volatility",
            label="Market Volatility",
            score=score,
            status=str(inputs["status"]),
            value=vix,
            previous_value=None,
            trend="stable",
            explanation="Lower volatility supports sentiment; elevated volatility reduces confidence.",
            metadata=inputs["metadata"],
        )

    def build_safe_haven_component(self) -> SentimentComponentData:
        value = relative_proxy_return("SPY", "GLD")
        score = normalize(value, -6, 6)
        return component(
            "safe_haven_demand",
            "Safe-Haven Demand",
            score,
            value,
            "risk-on" if value > 0 else "defensive",
            "SPY versus GLD acts as a safe-haven demand proxy.",
            "market_proxy",
            False,
            False,
            65,
        )

    def build_junk_bond_component(self) -> SentimentComponentData:
        value = relative_proxy_return("HYG", "IEF")
        score = normalize(value, -4, 4)
        return component(
            "junk_bond_demand",
            "Junk-Bond Demand",
            score,
            value,
            "risk-on" if value > 0 else "defensive",
            "HYG versus IEF acts as a credit appetite proxy.",
            "market_proxy",
            False,
            False,
            65,
        )


def relative_proxy_return(symbol: str, benchmark: str) -> float:
    try:
        history, _ = get_symbol_history(symbol, days=80, minimum_candles=40)
        benchmark_history, _ = get_symbol_history(benchmark, days=80, minimum_candles=40)
        return round(
            (calculate_history_return(history, "1m") or 0.0)
            - (calculate_history_return(benchmark_history, "1m") or 0.0),
            2,
        )
    except Exception:
        return 0.0


def component(
    key: str,
    label: str,
    score: float,
    value: float | None,
    trend: str,
    explanation: str,
    source: str,
    is_live: bool,
    fallback_used: bool,
    quality_score: float | None,
) -> SentimentComponentData:
    return SentimentComponentData(
        key=key,
        label=label,
        score=round(score, 2),
        status=classify_sentiment(score),
        value=value,
        previous_value=None,
        trend=trend,
        explanation=explanation,
        metadata=SourceMetadata(
            source=source,
            is_live=is_live,
            is_stale=False,
            fallback_used=fallback_used,
            as_of=now_iso(),
            quality_score=quality_score,
            warnings=[],
        ),
    )


def normalize(value: float, low: float, high: float) -> float:
    if high == low:
        return 50.0
    return max(0.0, min(100.0, round(((value - low) / (high - low)) * 100, 2)))


def classify_sentiment(score: float) -> str:
    if score >= 80:
        return "Constructive"
    if score >= 65:
        return "Positive but Selective"
    if score >= 50:
        return "Mixed"
    return "Defensive"


def mock_metadata(warnings: list[str]) -> SourceMetadata:
    return SourceMetadata(
        source="mock-fallback",
        is_live=False,
        is_stale=False,
        fallback_used=True,
        as_of=now_iso(),
        quality_score=55,
        warnings=warnings,
    )


def mixed_metadata(warnings: list[str]) -> SourceMetadata:
    return SourceMetadata(
        source="market_proxy",
        is_live=False,
        is_stale=False,
        fallback_used=False,
        as_of=now_iso(),
        quality_score=65,
        warnings=warnings,
    )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
