from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.market_history.storage import DailyBar, DailyBarStorage
from app.securities.models import SecurityProviderSymbol
from app.services.market_data_repository import MarketDataRepository, get_market_data_repository


class BreadthUniverseHistoryUpdater:
    """Fetches only missing/overlap daily history outside interactive request paths."""
    def __init__(self, storage: DailyBarStorage | None = None, repository: MarketDataRepository | None = None) -> None:
        self.storage = storage or DailyBarStorage()
        self.repository = repository or get_market_data_repository()

    def update_symbol(self, ticker: str, *, provider_symbol: str | None = None, canonical_security_id: str | None = None, lookback_calendar_days: int = 450, overlap_days: int = 7, strict_live: bool = False) -> dict[str, Any]:
        latest = self.storage.latest_session(ticker)
        if latest:
            start = datetime.fromisoformat(latest).replace(tzinfo=timezone.utc) - timedelta(days=overlap_days)
            requested_days = max(overlap_days + 5, (datetime.now(timezone.utc) - start).days + 2)
        else:
            requested_days = lookback_calendar_days
        requested_symbol = provider_symbol or ticker
        if strict_live:
            history = self.repository.get_provider_for("daily_history").get_history(requested_symbol, resolution="D", days=requested_days)
        else:
            history = self.repository.get_history(requested_symbol, resolution="D", days=requested_days)
        if (strict_live and history.source_state != "live") or (history.source_state == "mock" and not allow_test_breadth()):
            raise RuntimeError("strict live breadth updater rejects mock history")
        bars = [to_daily_bar(ticker, history.provider or "polygon", candle.timestamp, candle.open, candle.high, candle.low, candle.close, candle.volume, history.as_of, canonical_security_id=canonical_security_id, canonical_ticker=ticker, source_symbol=requested_symbol) for candle in history.candles]
        inserted, updated = self.storage.upsert(bars)
        return {"ticker": ticker.upper(), "provider_symbol": requested_symbol.upper(), "requested_days": requested_days, "received_bars": len(bars), "inserted_bars": inserted, "updated_bars": updated, "earliest_date": bars[0].session_date if bars else None, "latest_date": bars[-1].session_date if bars else None, "provider": history.provider or "polygon", "status": "complete" if bars else "unavailable", "source_state": history.source_state}

    def update_symbol_history_segments(
        self,
        ticker: str,
        *,
        security_id: str,
        segments: list[SecurityProviderSymbol],
        lookback_calendar_days: int = 450,
        strict_live: bool = False,
    ) -> dict[str, Any]:
        """Fetch and stitch non-overlapping provider-symbol eras into one canonical series.

        This is intentionally a seed-only path. Interactive reads continue to use the
        durable canonical series and never invoke a provider or stitching work.
        """
        if not segments:
            raise ValueError("symbol_history_segments_required")
        ordered = sorted(segments, key=lambda item: item.effective_from)
        for previous, current in zip(ordered, ordered[1:]):
            if previous.effective_to is None or previous.effective_to >= current.effective_from:
                raise ValueError("symbol_history_segments_overlap")
        provider = self.repository.get_provider_for("daily_history") if strict_live else None
        all_bars: dict[str, DailyBar] = {}
        source_reports: list[dict[str, Any]] = []
        for segment in ordered:
            existing = [
                bar for bar in self.storage.history(ticker)
                if bar.source_symbol == segment.provider_symbol.upper()
                and bar.session_date >= segment.effective_from
                and (segment.effective_to is None or bar.session_date <= segment.effective_to)
            ]
            # A closed symbol era is immutable. Once it reaches its verified
            # boundary, preserve it and avoid needlessly re-downloading it on resume.
            closed_era_complete = bool(
                segment.effective_to
                and existing
                and existing[-1].session_date >= segment.effective_to
            )
            if closed_era_complete:
                for bar in existing:
                    all_bars[bar.session_date] = bar
                source_reports.append({
                    "provider_symbol": segment.provider_symbol,
                    "effective_from": segment.effective_from,
                    "effective_to": segment.effective_to,
                    "requested_days": 0,
                    "received_bars": 0,
                    "selected_bars": len(existing),
                    "reused_bars": len(existing),
                    "earliest_date": existing[0].session_date,
                    "latest_date": existing[-1].session_date,
                    "source_state": "durable",
                    "provider": segment.provider,
                    "skipped_closed_era": True,
                })
                continue
            requested_days = lookback_calendar_days
            if existing:
                latest_existing = datetime.fromisoformat(existing[-1].session_date).replace(tzinfo=timezone.utc)
                requested_days = max(12, (datetime.now(timezone.utc) - latest_existing).days + 9)
                for bar in existing:
                    all_bars[bar.session_date] = bar
            history = provider.get_history(segment.provider_symbol, resolution="D", days=requested_days) if provider else self.repository.get_history(segment.provider_symbol, resolution="D", days=requested_days)
            if (strict_live and history.source_state != "live") or (history.source_state == "mock" and not allow_test_breadth()):
                raise RuntimeError("strict live history stitch rejects non-live history")
            selected = [candle for candle in history.candles if candle.timestamp[:10] >= segment.effective_from and (segment.effective_to is None or candle.timestamp[:10] <= segment.effective_to)]
            bars = [
                to_daily_bar(
                    ticker, history.provider or segment.provider, candle.timestamp, candle.open, candle.high, candle.low, candle.close, candle.volume,
                    history.as_of, canonical_security_id=security_id, canonical_ticker=ticker, source_symbol=segment.provider_symbol,
                    corporate_action_lineage=segment.corporate_action_lineage,
                )
                for candle in selected
            ]
            for bar in bars:
                previous = all_bars.get(bar.session_date)
                if previous and previous.source_symbol != bar.source_symbol:
                    raise ValueError(f"symbol_history_duplicate_session:{bar.session_date}")
                all_bars[bar.session_date] = bar
            source_reports.append({
                "provider_symbol": segment.provider_symbol, "effective_from": segment.effective_from, "effective_to": segment.effective_to,
                "requested_days": requested_days, "received_bars": len(history.candles), "selected_bars": len(bars), "reused_bars": len(existing),
                "earliest_date": bars[0].session_date if bars else None, "latest_date": bars[-1].session_date if bars else None,
                "source_state": history.source_state, "provider": history.provider or segment.provider,
            })
        stitched = [all_bars[session] for session in sorted(all_bars)]
        if not stitched:
            raise RuntimeError("symbol_history_stitch_no_bars")
        inserted, updated = self.storage.upsert(stitched)
        boundary = _boundary_audit(ordered, stitched)
        return {
            "ticker": ticker.upper(), "canonical_security_id": security_id, "provider": stitched[0].provider,
            "requested_days_per_symbol": lookback_calendar_days, "source_symbols": source_reports,
            "received_bars": len(stitched), "inserted_bars": inserted, "updated_bars": updated,
            "earliest_date": stitched[0].session_date, "latest_date": stitched[-1].session_date,
            "status": "complete", "source_state": "live" if strict_live else "mixed", "stitching": boundary,
        }


def to_daily_bar(
    ticker: str,
    provider: str,
    timestamp: str,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: float,
    source_timestamp: str | None,
    *,
    canonical_security_id: str | None = None,
    canonical_ticker: str | None = None,
    source_symbol: str | None = None,
    corporate_action_lineage: str | None = None,
) -> DailyBar:
    session_date = timestamp[:10]
    return DailyBar(ticker=ticker.upper(), provider=provider.lower(), session_date=session_date, timestamp=timestamp, open=float(open_), high=float(high), low=float(low), close=float(close), volume=float(volume or 0), adjusted=True, source_timestamp=source_timestamp, canonical_security_id=canonical_security_id, canonical_ticker=canonical_ticker or ticker.upper(), source_symbol=source_symbol or ticker.upper(), corporate_action_lineage=corporate_action_lineage)


def allow_test_breadth() -> bool:
    import os
    return (os.getenv("DATA_PROVIDER") or "").lower() in {"test", "generated_test_data"} and os.getenv("BREADTH_ALLOW_TEST_DATA", "false").lower() in {"1", "true", "yes"}


def _boundary_audit(segments: list[SecurityProviderSymbol], bars: list[DailyBar]) -> dict[str, Any]:
    by_symbol = {segment.provider_symbol.upper(): [bar for bar in bars if bar.source_symbol == segment.provider_symbol.upper()] for segment in segments}
    transitions: list[dict[str, Any]] = []
    for previous, current in zip(segments, segments[1:]):
        before = by_symbol[previous.provider_symbol.upper()]
        after = by_symbol[current.provider_symbol.upper()]
        last_before, first_after = (before[-1] if before else None), (after[0] if after else None)
        daily_return = round(first_after.close / last_before.close - 1, 8) if last_before and first_after and last_before.close else None
        transitions.append({
            "from_symbol": previous.provider_symbol.upper(), "to_symbol": current.provider_symbol.upper(), "effective_date": current.effective_from,
            "last_pre_change_session": last_before.session_date if last_before else None, "last_pre_change_close": last_before.close if last_before else None,
            "first_post_change_session": first_after.session_date if first_after else None, "first_post_change_close": first_after.close if first_after else None,
            "boundary_return": daily_return, "overlap_count": len(set(bar.session_date for bar in before) & set(bar.session_date for bar in after)),
            "gap_count": _weekday_gap_count(last_before.session_date, first_after.session_date) if last_before and first_after else None,
            "synthetic_return": False,
        })
    return {"stitched_total_bars": len(bars), "duplicate_count": len(bars) - len({bar.session_date for bar in bars}), "transitions": transitions}


def _weekday_gap_count(left: str, right: str) -> int:
    start = datetime.fromisoformat(left).date() + timedelta(days=1)
    end = datetime.fromisoformat(right).date()
    return sum(1 for offset in range((end - start).days) if (start + timedelta(days=offset)).weekday() < 5)
