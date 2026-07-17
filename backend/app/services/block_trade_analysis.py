import os
from datetime import datetime, timezone
from statistics import median

from app.data.universes import get_symbol_sector
from app.providers.cache import get_cached_value, set_cached_value
from app.providers.intelligence_models import BlockTradeCandidate, SourceMetadata, TradePrintData
from app.providers.selector import get_trade_flow_provider
from app.services.pattern_detection import WATCHLIST_SYMBOLS


def analyze_block_trade_candidates(symbol: str) -> dict:
    normalized = symbol.upper()
    cache_key = f"institutional:{normalized}:{time_bucket()}"
    cached = get_cached_value(cache_key)
    if cached is not None:
        return cached

    try:
        provider = get_trade_flow_provider()
        trades = provider.get_recent_trades(
            normalized,
            lookback_minutes=int(os.getenv("BLOCK_TRADE_LOOKBACK_MINUTES", "60")),
        )
        health = provider.get_trade_flow_health()
        metadata = live_metadata(health.provider, health.reachable and health.provider != "mock-trade-flow", trades)
    except Exception as exc:
        trades = build_fallback_trades(normalized)
        metadata = SourceMetadata(
            source="mock-fallback",
            is_live=False,
            is_stale=False,
            fallback_used=True,
            as_of=now_iso(),
            quality_score=55,
            warnings=[f"Trade-flow provider unavailable: {exc}"],
        )

    candidates = detect_block_candidates(trades, metadata)
    result = {
        "symbol": normalized,
        "candidates": [candidate.model_dump() for candidate in candidates],
        "block_notional": round(sum(candidate.notional for candidate in candidates), 2),
        "confidence": metadata.quality_score,
        "limitations": [
            "Large-print activity is a heuristic, not confirmed institutional identity.",
            "Classification does not infer actual buyer or seller.",
        ],
        "metadata": metadata.model_dump(),
    }
    set_cached_value(cache_key, result, int(os.getenv("TRADE_FLOW_CACHE_TTL_SECONDS", "300")))
    return result


def build_institutional_large_print_dashboard() -> dict:
    rows = [analyze_block_trade_candidates(symbol) for symbol in WATCHLIST_SYMBOLS]
    candidates = [
        candidate
        for row in rows
        for candidate in row["candidates"]
    ]
    candidates = sorted(candidates, key=lambda item: item["notional"], reverse=True)[:8]
    block_notional_by_symbol = {
        row["symbol"]: row["block_notional"]
        for row in rows
        if row["block_notional"] > 0
    }
    block_notional_by_sector: dict[str, float] = {}
    for symbol, notional in block_notional_by_symbol.items():
        sector = get_symbol_sector(symbol)
        block_notional_by_sector[sector] = round(block_notional_by_sector.get(sector, 0) + notional, 2)

    modes = [
        row["metadata"].get("source", "mock")
        for row in rows
    ]
    fallback_count = sum(1 for row in rows if row["metadata"].get("fallback_used"))

    return {
        "largest_block_candidates": candidates,
        "block_notional_by_symbol": block_notional_by_symbol,
        "block_notional_by_sector": block_notional_by_sector,
        "repeated_large_print_symbols": [
            row["symbol"] for row in rows if len(row["candidates"]) >= 2
        ],
        "confidence": round(sum(row["confidence"] or 55 for row in rows) / len(rows)) if rows else 55,
        "limitations": [
            "Block-trade candidates are large-print heuristics.",
            "No buyer/seller identity is inferred from anonymous prints.",
        ],
        "metadata": {
            "overall_mode": "mixed" if fallback_count else "live" if all(mode == "polygon" for mode in modes) else "mock",
            "fallback_used": fallback_count > 0,
            "as_of": now_iso(),
        },
    }


def detect_block_candidates(
    trades: list[TradePrintData],
    metadata: SourceMetadata,
) -> list[BlockTradeCandidate]:
    if not trades:
        return []

    min_notional = float(os.getenv("BLOCK_TRADE_MIN_NOTIONAL", "1000000"))
    min_relative = float(os.getenv("BLOCK_TRADE_MIN_RELATIVE_SIZE", "5.0"))
    median_size = median([trade.size for trade in trades]) or 1
    candidates: list[BlockTradeCandidate] = []
    for trade in trades:
        relative_size = trade.size / median_size
        if trade.notional < min_notional and relative_size < min_relative:
            continue
        classification = "Large Print"
        candidates.append(
            BlockTradeCandidate(
                symbol=trade.symbol,
                price=trade.price,
                size=trade.size,
                notional=trade.notional,
                relative_size=round(relative_size, 2),
                classification=classification,
                confidence=metadata.quality_score or 55,
                reason="Meets notional or relative-size large-print threshold; buyer/seller identity is not inferred.",
                timestamp=trade.timestamp,
                metadata=metadata,
            )
        )
    return sorted(candidates, key=lambda item: item.notional, reverse=True)[:10]


def build_fallback_trades(symbol: str) -> list[TradePrintData]:
    base_price = {"NVDA": 150, "MU": 142, "ARM": 162, "SNDK": 64}.get(symbol, 100)
    return [
        TradePrintData(
            symbol=symbol,
            price=base_price + index * 0.1,
            size=size,
            notional=round((base_price + index * 0.1) * size, 2),
            exchange="simulated",
            conditions=[],
            timestamp=now_iso(),
        )
        for index, size in enumerate([1200, 1800, 9500, 1400, 11200, 1600, 1300])
    ]


def live_metadata(source: str, is_live: bool, trades: list[TradePrintData]) -> SourceMetadata:
    return SourceMetadata(
        source=source,
        is_live=is_live,
        is_stale=False,
        fallback_used=False,
        as_of=trades[0].timestamp if trades else now_iso(),
        quality_score=80 if trades else 50,
        warnings=[] if trades else ["No recent trades returned."],
    )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def time_bucket() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
