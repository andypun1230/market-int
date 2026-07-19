from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.providers.models import HistoryData
from app.services.candle_data import get_symbol_history
from app.services.service_cache import get_or_compute, get_service_ttl


# These ETF proxies intentionally match the documented Macro tab inputs. They
# are price proxies, not direct observations of Treasury yields or commodities.
MACRO_PROXIES = (
    ("SPY", "Equities", "equities"),
    ("IEF", "10Y Treasury bond proxy", "treasury_10y"),
    ("TLT", "30Y Treasury bond proxy", "treasury_30y"),
    ("GLD", "Gold", "gold"),
    ("USO", "Oil", "oil"),
    ("UUP", "US Dollar", "dollar"),
    ("HYG", "High-yield credit", "credit"),
)
MACRO_SESSIONS = 66


def build_macro_state(days: int = 110) -> dict[str, Any]:
    """Return one cache-backed, transparent macro read for UI, report, and AI.

    The provider is only consulted when the existing history cache has no
    usable input. Consumers receive an unavailable state instead of invented
    mock values when cross-asset coverage is incomplete.
    """
    return get_or_compute(
        f"macro-state:v3:{days}",
        get_service_ttl("SERVICE_CACHE_MACRO_TTL_SECONDS", 300),
        lambda: _build_macro_state_uncached(days),
    )


def _build_macro_state_uncached(days: int) -> dict[str, Any]:
    histories = {symbol: get_live_macro_history(symbol, days) for symbol, _, _ in MACRO_PROXIES}
    state = build_macro_state_from_histories(histories)
    # The Macro screen needs the same provider-backed candles for its selected
    # horizon charts. Returning them from this cache-backed read prevents each
    # screen navigation from issuing seven independent history requests.
    state["histories"] = {
        symbol: history.model_dump(mode="json")
        for symbol, history in histories.items()
        if is_eligible_live_history(history)
    }
    return state


def get_live_macro_history(symbol: str, days: int) -> HistoryData:
    """Reject a legacy mock cache entry before it can affect live macro state."""
    history, _ = get_symbol_history(symbol, days=days)
    if is_eligible_live_history(history):
        return history
    # A provider-keyed cache can contain a pre-live mock entry from an older
    # development run. This targeted invalidation is only for that proven
    # provenance conflict; normal warm reads use the service cache above.
    from app.services.market_data_repository import get_market_data_repository

    repository = get_market_data_repository()
    repository.invalidate_history(symbol)
    refreshed, _ = get_symbol_history(symbol, days=days)
    return refreshed


def build_macro_state_from_histories(histories: dict[str, HistoryData]) -> dict[str, Any]:
    assets: list[dict[str, Any]] = []
    for symbol, label, asset_class in MACRO_PROXIES:
        history = histories.get(symbol)
        period_return = calculate_period_return(history)
        if period_return is None or not is_eligible_live_history(history):
            continue
        assets.append({
            "symbol": symbol,
            "label": label,
            "asset_class": asset_class,
            "return": period_return,
            "source_state": history.source_state if history else "unavailable",
            "provider": history.provider if history else "unavailable",
            "as_of": history.as_of if history else None,
            "is_live": bool(history and history.is_live and not history.fallback_used),
        })

    returns = {item["asset_class"]: item["return"] for item in assets}
    score, supporting, current_risks = calculate_risk_appetite(returns)
    available = len(assets)
    state = classify_state(score) if score is not None else "unavailable"
    ranked = sorted(assets, key=lambda item: item["return"], reverse=True)
    source_kind = source_kind_for_assets(assets)
    as_of = max((item["as_of"] for item in assets if item.get("as_of")), default=None)
    leading = [item["label"] for item in ranked[:2]]
    lagging = [item["label"] for item in reversed(ranked[-2:])]
    return {
        "state": state,
        "state_label": format_state(state),
        "score": score,
        "confidence": confidence_for_asset_count(available),
        "supporting_evidence": supporting,
        "current_risks": current_risks,
        "key_risk": current_risks[0] if current_risks else "No dominant current macro risk is identified.",
        "invalidation_conditions": (
            "A renewed rise in defensive assets or destabilizing yields would weaken this risk-appetite read."
            if score is not None
            else "Cross-asset coverage must be restored before an invalidation condition can be assessed."
        ),
        "summary": build_summary(state, leading, lagging, supporting, current_risks),
        "leading": leading,
        "lagging": lagging,
        "assets": ranked,
        "available_assets": available,
        "expected_assets": len(MACRO_PROXIES),
        "source_state": source_kind,
        "source_label": {
            "live": "Live proxy data",
            "cached": "Cached proxy data",
            "mixed": "Mixed proxy sources",
        }.get(source_kind, "Unavailable"),
        "as_of": as_of or datetime.now(timezone.utc).isoformat(),
        "provenance": {
            "history": "adjusted daily ETF proxy history",
            "yield_disclosure": "Treasury ETF prices are proxies; direct Treasury yield levels are not supplied.",
            "formula_version": "cross-asset-risk-appetite-v1",
            "mock_fallback": False,
        },
    }


def calculate_period_return(history: HistoryData | None) -> float | None:
    if history is None:
        return None
    candles = [candle for candle in history.candles if candle.close > 0]
    selected = candles[-MACRO_SESSIONS:]
    if len(selected) < 2 or selected[0].close <= 0:
        return None
    return round(((selected[-1].close / selected[0].close) - 1) * 100, 4)


def is_eligible_live_history(history: HistoryData | None) -> bool:
    return bool(
        history
        and history.is_live
        and not history.fallback_used
        and str(history.provider or "").lower() not in {"mock", "test", "generated_test_data", "unavailable"}
    )


def calculate_risk_appetite(returns: dict[str, float]) -> tuple[int | None, list[str], list[str]]:
    spy, ief, tlt = returns.get("equities"), returns.get("treasury_10y"), returns.get("treasury_30y")
    gold, oil, dollar, credit = returns.get("gold"), returns.get("oil"), returns.get("dollar"), returns.get("credit")
    score, weight_count = 50.0, 0.0
    supporting: list[str] = []
    defensive: list[str] = []
    if spy is not None and (ief is not None or tlt is not None):
        bonds = average([ief, tlt])
        if bonds is not None:
            spread = spy - bonds
            score += clamp(spread * 2.4, -28, 28)
            weight_count += 2
            if spread > 1.5:
                supporting.append("Equities are outperforming Treasury bond proxies.")
            elif spread < -1.5:
                defensive.append("Treasury bond proxies are outperforming equities.")
    if credit is not None and ief is not None:
        spread = credit - ief
        score += clamp(spread * 1.2, -12, 12)
        weight_count += 1
        if spread > 1:
            supporting.append("Credit risk appetite is stronger than intermediate Treasuries.")
        elif spread < -1:
            defensive.append("Credit is lagging intermediate Treasuries.")
    if spy is not None and gold is not None:
        spread = gold - spy
        score += clamp(-spread * 1.1, -12, 12)
        weight_count += 1
        if spread > 1.5:
            defensive.append("Gold is outperforming equities.")
        elif spread < -1.5:
            supporting.append("Gold is lagging equities.")
    if spy is not None and dollar is not None:
        spread = dollar - spy
        score += clamp(-spread * 0.8, -8, 8)
        weight_count += 1
        if spread > 1.5:
            defensive.append("Dollar strength is a macro headwind.")
    if spy is not None and oil is not None:
        spread = oil - spy
        score += clamp(spread * 0.35 if spy > 0 else -abs(spread) * 0.35, -5, 5 if spy > 0 else 2)
        weight_count += 0.5
        if oil > 3 and spy > 0:
            supporting.append("Oil strength is consistent with firm nominal-growth expectations.")
        elif oil > 3:
            defensive.append("Oil strength without equity confirmation may reflect inflation or supply pressure.")
    return (round(clamp(score, 0, 100)) if weight_count else None, supporting, defensive)


def average(values: list[float | None]) -> float | None:
    valid = [value for value in values if value is not None]
    return sum(valid) / len(valid) if valid else None


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def classify_state(score: int | None) -> str:
    if score is None:
        return "unavailable"
    if score >= 75:
        return "strong_risk_on"
    if score >= 60:
        return "risk_on"
    if score >= 45:
        return "balanced"
    if score >= 30:
        return "defensive_rotation"
    return "risk_off"


def format_state(state: str) -> str:
    return {
        "strong_risk_on": "Strong Risk-On",
        "risk_on": "Risk-On",
        "balanced": "Balanced",
        "defensive_rotation": "Defensive Rotation",
        "risk_off": "Risk-Off",
    }.get(state, "Unavailable")


def confidence_for_asset_count(count: int) -> str:
    return "high" if count >= 6 else "moderate" if count >= 4 else "low" if count >= 2 else "unavailable"


def source_kind_for_assets(assets: list[dict[str, Any]]) -> str:
    if not assets:
        return "unavailable"
    if all(item["is_live"] and item["source_state"] == "live" for item in assets):
        return "live"
    if all(item["is_live"] for item in assets):
        return "cached"
    return "mixed"


def build_summary(state: str, leading: list[str], lagging: list[str], supporting: list[str], risks: list[str]) -> str:
    if state == "unavailable":
        return "Macro overview is unavailable because cross-asset history is incomplete."
    evidence = supporting[0] if supporting else "Cross-asset conditions are balanced."
    risk = f" Current risk: {risks[0]}" if risks else " No dominant current macro risk is identified."
    return f"{format_state(state)} conditions with {' and '.join(leading) or 'limited leadership'} leading and {' and '.join(lagging) or 'limited laggards'} lagging. {evidence}{risk}"
