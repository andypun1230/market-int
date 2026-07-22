from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Path, Query

from app.analysis_engines.session import BarInterval
from app.intelligence.news import (
    NewsEventType,
    NewsIntelligenceResult,
    NewsQuery,
    NewsQueryMode,
    SourceQuality,
    get_news_intelligence_service,
)
from app.intelligence.session_narrative import (
    ProductionSessionDataAdapter,
    ProductionSessionNarrativeResult,
    SessionNarrativeQuery,
)
from app.market_history.storage import DailyBarStorage


router = APIRouter(prefix="/intelligence", tags=["intelligence"])
_SESSION_ADAPTER = ProductionSessionDataAdapter()
_NEW_YORK = ZoneInfo("America/New_York")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _news_query(
    mode: NewsQueryMode,
    *,
    as_of: datetime | None,
    start: datetime | None,
    end: datetime | None,
    entity_id: str | None = None,
    symbols: tuple[str, ...] = (),
    event_type: list[NewsEventType] | None = None,
    source_quality: list[SourceQuality] | None = None,
    minimum_materiality: int = 0,
    limit: int = 20,
) -> NewsQuery:
    return NewsQuery(
        mode=mode,
        as_of=as_of or _now(),
        start_at=start,
        end_at=end,
        entity_id=entity_id,
        symbols=symbols,
        event_types=tuple(event_type or ()),
        source_qualities=tuple(source_quality or ()),
        minimum_materiality=minimum_materiality,
        limit=limit,
    )


def _query_news(query: NewsQuery) -> NewsIntelligenceResult:
    # The production factory is deliberately unavailable until a licensed
    # provider is configured. It never falls back to hermetic fixtures.
    return get_news_intelligence_service().query(
        query,
        watchlist_symbols=(
            query.symbols if query.mode is NewsQueryMode.WATCHLIST else ()
        ),
    )


@router.get("/news/market", response_model=NewsIntelligenceResult)
def market_news(
    as_of: datetime | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    event_type: list[NewsEventType] | None = Query(default=None),
    source_quality: list[SourceQuality] | None = Query(default=None),
    minimum_materiality: int = Query(default=0, ge=0, le=100),
) -> NewsIntelligenceResult:
    return _query_news(
        _news_query(
            NewsQueryMode.MARKET,
            as_of=as_of,
            start=start,
            end=end,
            event_type=event_type,
            source_quality=source_quality,
            minimum_materiality=minimum_materiality,
            limit=limit,
        )
    )


@router.get("/news/index/{index_id}", response_model=NewsIntelligenceResult)
def index_news(
    index_id: str,
    as_of: datetime | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    event_type: list[NewsEventType] | None = Query(default=None),
    source_quality: list[SourceQuality] | None = Query(default=None),
    minimum_materiality: int = Query(default=0, ge=0, le=100),
) -> NewsIntelligenceResult:
    normalized = index_id.strip().upper()
    return _query_news(
        _news_query(
            NewsQueryMode.INDEX,
            as_of=as_of,
            start=start,
            end=end,
            entity_id=normalized,
            symbols=(normalized,),
            event_type=event_type,
            source_quality=source_quality,
            minimum_materiality=minimum_materiality,
            limit=limit,
        )
    )


@router.get("/news/security/{symbol}", response_model=NewsIntelligenceResult)
def security_news(
    symbol: str,
    as_of: datetime | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    event_type: list[NewsEventType] | None = Query(default=None),
    source_quality: list[SourceQuality] | None = Query(default=None),
    minimum_materiality: int = Query(default=0, ge=0, le=100),
) -> NewsIntelligenceResult:
    normalized = symbol.strip().upper()
    return _query_news(
        _news_query(
            NewsQueryMode.SECURITY,
            as_of=as_of,
            start=start,
            end=end,
            entity_id=normalized,
            symbols=(normalized,),
            event_type=event_type,
            source_quality=source_quality,
            minimum_materiality=minimum_materiality,
            limit=limit,
        )
    )


@router.get("/news/sector/{sector_id}", response_model=NewsIntelligenceResult)
def sector_news(
    sector_id: str,
    as_of: datetime | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    event_type: list[NewsEventType] | None = Query(default=None),
    source_quality: list[SourceQuality] | None = Query(default=None),
    minimum_materiality: int = Query(default=0, ge=0, le=100),
) -> NewsIntelligenceResult:
    return _query_news(
        _news_query(
            NewsQueryMode.SECTOR,
            as_of=as_of,
            start=start,
            end=end,
            entity_id=sector_id.strip().casefold(),
            event_type=event_type,
            source_quality=source_quality,
            minimum_materiality=minimum_materiality,
            limit=limit,
        )
    )


@router.get("/news/theme/{theme_id}", response_model=NewsIntelligenceResult)
def theme_news(
    theme_id: str,
    as_of: datetime | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    event_type: list[NewsEventType] | None = Query(default=None),
    source_quality: list[SourceQuality] | None = Query(default=None),
    minimum_materiality: int = Query(default=0, ge=0, le=100),
) -> NewsIntelligenceResult:
    return _query_news(
        _news_query(
            NewsQueryMode.THEME,
            as_of=as_of,
            start=start,
            end=end,
            entity_id=theme_id.strip().casefold(),
            event_type=event_type,
            source_quality=source_quality,
            minimum_materiality=minimum_materiality,
            limit=limit,
        )
    )


@router.get("/news/watchlist", response_model=NewsIntelligenceResult)
def watchlist_news(
    symbols: str = Query(min_length=1, max_length=500),
    as_of: datetime | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=30, ge=1, le=100),
    event_type: list[NewsEventType] | None = Query(default=None),
    source_quality: list[SourceQuality] | None = Query(default=None),
    minimum_materiality: int = Query(default=0, ge=0, le=100),
) -> NewsIntelligenceResult:
    normalized = tuple(
        dict.fromkeys(
            value.strip().upper()
            for value in symbols.split(",")
            if value.strip()
        )
    )
    if not normalized or len(normalized) > 50:
        raise ValueError("watchlist news requires between 1 and 50 symbols")
    return _query_news(
        _news_query(
            NewsQueryMode.WATCHLIST,
            as_of=as_of,
            start=start,
            end=end,
            symbols=normalized,
            event_type=event_type,
            source_quality=source_quality,
            minimum_materiality=minimum_materiality,
            limit=limit,
        )
    )


@router.get("/news/events/{event_id}", response_model=NewsIntelligenceResult)
def news_event_detail(
    event_id: str = Path(
        min_length=12,
        max_length=200,
        pattern=r"^news-event-[A-Za-z0-9][A-Za-z0-9._:-]{0,188}$",
    ),
    as_of: datetime | None = None,
) -> NewsIntelligenceResult:
    return get_news_intelligence_service().query_cached_event(
        event_id.casefold(),
        as_of=as_of or _now(),
    )


def _session_result(
    symbol: str,
    *,
    interval: BarInterval,
    session_date: date | None,
    as_of: datetime | None,
) -> ProductionSessionNarrativeResult:
    normalized = symbol.strip().upper()
    timestamp = as_of or _now()
    if timestamp.tzinfo is None:
        raise ValueError("session_query_as_of_must_be_timezone_aware")
    if session_date is not None and session_date > timestamp.astimezone(_NEW_YORK).date():
        raise ValueError("requested_session_date_must_not_exceed_as_of_market_date")
    storage = DailyBarStorage()
    latest_raw: str | None
    try:
        market_date = timestamp.astimezone(_NEW_YORK).date().isoformat()
        eligible_history = storage.history(
            normalized,
            "polygon",
            end_date=market_date,
        )
        latest_raw = eligible_history[-1].session_date if eligible_history else None
    except Exception:
        latest_raw = None
    latest = date.fromisoformat(latest_raw) if latest_raw else None
    query = SessionNarrativeQuery(
        symbol=normalized,
        interval=interval,
        requested_session_date=session_date,
        as_of=timestamp,
    )
    return _SESSION_ADAPTER.query(
        query,
        daily_history_available=latest is not None,
        provider="polygon" if latest else None,
        latest_daily_session=latest,
        source_id=(f"daily_price_bars:{normalized}:{latest.isoformat()}" if latest else None),
    )


@router.get("/session/market", response_model=ProductionSessionNarrativeResult)
def market_session_narrative(
    interval: BarInterval = BarInterval.FIVE_MINUTES,
    session_date: date | None = None,
    as_of: datetime | None = None,
) -> ProductionSessionNarrativeResult:
    return _session_result("SPY", interval=interval, session_date=session_date, as_of=as_of)


@router.get("/session/{symbol}", response_model=ProductionSessionNarrativeResult)
def symbol_session_narrative(
    symbol: str,
    interval: BarInterval = BarInterval.FIVE_MINUTES,
    session_date: date | None = None,
    as_of: datetime | None = None,
) -> ProductionSessionNarrativeResult:
    return _session_result(symbol, interval=interval, session_date=session_date, as_of=as_of)
