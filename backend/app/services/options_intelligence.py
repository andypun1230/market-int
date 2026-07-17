import os
from datetime import datetime, timedelta, timezone
from statistics import mean

from app.models.market import OptionsIntelligenceResponse, SymbolOptionsIntelligence
from app.providers.cache import get_cached_value, set_cached_value
from app.providers.intelligence_models import (
    OptionContractData,
    OptionsChainData,
    SourceMetadata,
)
from app.providers.selector import get_options_provider
from app.services.service_cache import get_or_compute, get_service_ttl


def build_options_intelligence() -> OptionsIntelligenceResponse:
    return get_or_compute(
        "options-intelligence",
        get_service_ttl("SERVICE_CACHE_INSTITUTIONAL_TTL_SECONDS", 300),
        _build_options_intelligence_uncached,
    )


def _build_options_intelligence_uncached() -> OptionsIntelligenceResponse:
    underlyings = get_options_underlyings()
    items = [analyze_symbol_options(symbol) for symbol in underlyings]
    score = round(mean(item.score for item in items)) if items else 55
    put_call_ratios = [item.put_call_ratio for item in items if item.put_call_ratio is not None]
    iv_values = [item.implied_volatility_rank for item in items if item.implied_volatility_rank is not None]
    metadata = build_dashboard_metadata(items)

    return OptionsIntelligenceResponse(
        score=score,
        status="Constructive Options Tone" if score >= 70 else "Mixed Options Tone",
        put_call_ratio=round(mean(put_call_ratios), 2) if put_call_ratios else 0.9,
        implied_volatility_rank=round(mean(iv_values)) if iv_values else 50,
        skew="Estimated from option-chain volume and open interest",
        options_flow_bias=get_options_bias(score),
        unusual_activity=[
            candidate
            for item in items
            for candidate in item.unusual_volume_candidates[:1]
        ][:5] or ["No unusual options activity confirmed."],
        summary=(
            "Options intelligence uses live option chains when available; otherwise "
            "deterministic fallback keeps gamma and put/call estimates clearly marked."
        ),
        market_summary={
            "items_analyzed": len(items),
            "estimated_gamma_regime": most_common([item.estimated_gamma_regime for item in items]),
            "average_expected_move": round(mean([item.expected_move for item in items if item.expected_move is not None]), 2)
            if any(item.expected_move is not None for item in items)
            else None,
        },
        items=[item.model_dump() for item in items],
        expected_move=round(mean([item.expected_move for item in items if item.expected_move is not None]), 2)
        if any(item.expected_move is not None for item in items)
        else None,
        estimated_gamma_regime=most_common([item.estimated_gamma_regime for item in items]),
        call_wall=None,
        put_wall=None,
        confidence=metadata["quality_score"],
        metadata=metadata,
    )


def analyze_symbol_options(symbol: str) -> SymbolOptionsIntelligence:
    normalized = symbol.upper()
    cache_key = f"options-analysis:{normalized}:{time_bucket()}"
    cached = get_cached_value(cache_key)
    if cached is not None:
        return cached

    try:
        chain = get_options_provider().get_option_chain(
            normalized,
            max_expirations=int(os.getenv("OPTIONS_MAX_EXPIRATIONS", "4")),
        )
    except Exception as exc:
        chain = build_fallback_chain(normalized, str(exc))

    result = analyze_chain(chain)
    set_cached_value(cache_key, result, int(os.getenv("OPTIONS_CACHE_TTL_SECONDS", "300")))
    return result


def analyze_chain(chain: OptionsChainData) -> SymbolOptionsIntelligence:
    calls = [contract for contract in chain.contracts if contract.option_type in ("call", "c")]
    puts = [contract for contract in chain.contracts if contract.option_type in ("put", "p")]
    call_volume = sum(contract.volume or 0 for contract in calls)
    put_volume = sum(contract.volume or 0 for contract in puts)
    call_oi = sum(contract.open_interest or 0 for contract in calls)
    put_oi = sum(contract.open_interest or 0 for contract in puts)
    volume_put_call_ratio = round(put_volume / call_volume, 2) if call_volume else None
    oi_put_call_ratio = round(put_oi / call_oi, 2) if call_oi else None
    weighted_iv = weighted_average_iv(chain.contracts)
    expected_move = calculate_expected_move(chain.contracts, weighted_iv)
    call_wall = max(calls, key=lambda item: item.open_interest or 0).strike if calls else None
    put_wall = max(puts, key=lambda item: item.open_interest or 0).strike if puts else None
    gamma_proxy = calculate_gamma_proxy(chain.contracts)
    gamma_regime = "Positive Estimated Gamma" if gamma_proxy >= 0 else "Negative Estimated Gamma"
    score = calculate_options_score(volume_put_call_ratio, oi_put_call_ratio, weighted_iv, gamma_proxy)

    return SymbolOptionsIntelligence(
        symbol=chain.underlying,
        score=score,
        status=get_options_bias(score),
        put_call_ratio=volume_put_call_ratio,
        implied_volatility_rank=estimate_iv_rank(weighted_iv),
        expected_move=expected_move,
        estimated_gamma_regime=gamma_regime,
        call_wall=call_wall,
        put_wall=put_wall,
        unusual_volume_candidates=find_unusual_candidates(chain.contracts),
        summary=(
            f"{chain.underlying} options tone is {get_options_bias(score).lower()} with "
            f"estimated gamma exposure classified as {gamma_regime.lower()}."
        ),
        metadata={
            **chain.metadata.model_dump(),
            "volume_put_call_ratio": volume_put_call_ratio,
            "open_interest_put_call_ratio": oi_put_call_ratio,
            "gamma_method": (
                "Estimated gamma exposure = contract gamma x open interest x 100 x underlying_price^2. "
                "Call/put signs use simple open-interest assumptions and are not confirmed dealer inventory."
            ),
            "limitations": [
                "Estimated gamma exposure is not confirmed dealer positioning.",
                "Trade direction is unavailable, so open-interest assumptions are neutral proxies.",
            ],
        },
    )


def build_fallback_chain(symbol: str, reason: str) -> OptionsChainData:
    now = datetime.now(timezone.utc)
    underlying_price = {
        "SPY": 625,
        "QQQ": 555,
        "NVDA": 150,
        "MU": 142,
        "ARM": 162,
        "SNDK": 64,
        "IWM": 225,
        "DIA": 445,
    }.get(symbol, 100)
    expirations = [(now + timedelta(days=7 * index)).date().isoformat() for index in range(1, 5)]
    contracts: list[OptionContractData] = []
    for expiration in expirations:
        for offset in (-10, -5, 0, 5, 10):
            strike = round(underlying_price * (1 + offset / 100), 2)
            for option_type in ("call", "put"):
                contracts.append(
                    OptionContractData(
                        ticker=f"O:{symbol}{expiration.replace('-', '')}{option_type[0].upper()}{int(strike * 1000)}",
                        underlying=symbol,
                        expiration=expiration,
                        strike=strike,
                        option_type=option_type,
                        bid=1.2 + abs(offset) * 0.1,
                        ask=1.4 + abs(offset) * 0.1,
                        last=1.3 + abs(offset) * 0.1,
                        volume=max(10, 420 - abs(offset) * 20 + (50 if option_type == "call" else 0)),
                        open_interest=max(100, 1800 - abs(offset) * 75),
                        implied_volatility=0.32 + abs(offset) * 0.005,
                        delta=0.45 if option_type == "call" else -0.45,
                        gamma=0.012,
                        theta=-0.03,
                        vega=0.08,
                        underlying_price=underlying_price,
                        timestamp=now.isoformat(),
                    )
                )

    return OptionsChainData(
        underlying=symbol,
        contracts=contracts,
        metadata=SourceMetadata(
            source="mock-fallback",
            is_live=False,
            is_stale=False,
            fallback_used=True,
            as_of=now.isoformat(),
            quality_score=58,
            warnings=[f"Options provider unavailable: {reason}"],
        ),
    )


def weighted_average_iv(contracts: list[OptionContractData]) -> float | None:
    weighted_values = [
        ((contract.implied_volatility or 0) * (contract.open_interest or contract.volume or 0), contract.open_interest or contract.volume or 0)
        for contract in contracts
        if contract.implied_volatility is not None
    ]
    total_weight = sum(weight for _, weight in weighted_values)
    if total_weight <= 0:
        return None
    return round(sum(value for value, _ in weighted_values) / total_weight, 4)


def calculate_expected_move(contracts: list[OptionContractData], weighted_iv: float | None) -> float | None:
    atm = min(
        contracts,
        key=lambda item: abs((item.underlying_price or item.strike) - item.strike),
        default=None,
    )
    if atm is None or atm.underlying_price is None:
        return None

    same_expiration = [item for item in contracts if item.expiration == atm.expiration]
    call = min((item for item in same_expiration if item.option_type == "call"), key=lambda item: abs(item.strike - atm.strike), default=None)
    put = min((item for item in same_expiration if item.option_type == "put"), key=lambda item: abs(item.strike - atm.strike), default=None)
    if call and put and call.bid is not None and call.ask is not None and put.bid is not None and put.ask is not None:
        straddle = ((call.bid + call.ask) / 2) + ((put.bid + put.ask) / 2)
        return round((straddle / atm.underlying_price) * 100, 2)
    if weighted_iv is not None:
        return round((weighted_iv / (52 ** 0.5)) * 100, 2)
    return None


def calculate_gamma_proxy(contracts: list[OptionContractData]) -> float:
    total = 0.0
    for contract in contracts:
        if contract.gamma is None or contract.open_interest is None or contract.underlying_price is None:
            continue
        sign = 1 if contract.option_type == "call" else -1
        total += sign * contract.gamma * contract.open_interest * 100 * (contract.underlying_price ** 2)
    return round(total, 2)


def calculate_options_score(
    volume_put_call_ratio: float | None,
    oi_put_call_ratio: float | None,
    weighted_iv: float | None,
    gamma_proxy: float,
) -> int:
    score = 60
    if volume_put_call_ratio is not None:
        score += 12 if volume_put_call_ratio < 0.8 else -8 if volume_put_call_ratio > 1.2 else 0
    if oi_put_call_ratio is not None:
        score += 8 if oi_put_call_ratio < 0.9 else -6 if oi_put_call_ratio > 1.3 else 0
    if weighted_iv is not None and weighted_iv > 0.55:
        score -= 8
    if gamma_proxy < 0:
        score -= 5
    return max(0, min(100, score))


def estimate_iv_rank(weighted_iv: float | None) -> int | None:
    if weighted_iv is None:
        return None
    return max(0, min(100, round((weighted_iv - 0.15) / 0.65 * 100)))


def find_unusual_candidates(contracts: list[OptionContractData]) -> list[str]:
    candidates = [
        f"{contract.underlying} {contract.expiration} {contract.strike:g} {contract.option_type}"
        for contract in contracts
        if (contract.volume or 0) >= max(500, (contract.open_interest or 0) * 0.5)
    ]
    return candidates[:5] or ["No unusual-volume candidates detected."]


def get_options_bias(score: int) -> str:
    if score >= 75:
        return "Constructive Options Tone"
    if score >= 55:
        return "Mixed Options Tone"
    return "Defensive Options Tone"


def build_dashboard_metadata(items: list[SymbolOptionsIntelligence]) -> dict:
    live_count = sum(1 for item in items if item.metadata and item.metadata.get("is_live"))
    fallback_count = sum(1 for item in items if item.metadata and item.metadata.get("fallback_used"))
    return {
        "overall_mode": "live" if live_count == len(items) and items else "mixed" if live_count or fallback_count else "mock",
        "quality_score": round(mean([item.metadata.get("quality_score", 55) for item in items if item.metadata])) if items else 55,
        "coverage_percent": round((len(items) / len(get_options_underlyings())) * 100, 2) if get_options_underlyings() else 0,
        "gamma_method": "Estimated gamma exposure; not confirmed dealer positioning.",
        "limitations": [
            "Options data is live only when provider entitlement permits.",
            "Estimated gamma exposure uses open-interest assumptions.",
        ],
    }


def most_common(values: list[str | None]) -> str | None:
    filtered = [value for value in values if value]
    if not filtered:
        return None
    return max(set(filtered), key=filtered.count)


def get_options_underlyings() -> list[str]:
    return [
        symbol.strip().upper()
        for symbol in os.getenv("OPTIONS_UNDERLYINGS", "SPY,QQQ,IWM,DIA,MU,NVDA,ARM,SNDK").split(",")
        if symbol.strip()
    ]


def time_bucket() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
