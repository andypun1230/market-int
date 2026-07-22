from __future__ import annotations

from datetime import date, datetime, timezone

from app.analysis_engines.session import SessionAnalysisStatus, SessionDataMode
from app.intelligence.session_narrative.builder import SessionNarrativeBuilder
from app.intelligence.session_narrative.contracts import (
    NarrativeAvailability,
    ProductionSessionNarrativeResult,
    SessionNarrativeProvenance,
    SessionNarrativeQuery,
    SessionSourceAvailability,
)


class ProductionSessionDataAdapter:
    """Honest capability boundary for the current production market-data stack.

    The configured providers expose quotes and daily history, not finalized
    5/15-minute OHLCV.  This adapter intentionally does not resample daily bars,
    synthesize bars, or promote a mock/test provider to live intraday evidence.
    """

    _TEST_PROVIDER_NAMES = frozenset(
        {"mock", "test", "fixture", "generated_test_data", "mock_market_data"}
    )

    def __init__(self, *, narrative_builder: SessionNarrativeBuilder | None = None) -> None:
        self.narrative_builder = narrative_builder or SessionNarrativeBuilder()

    def availability(
        self,
        *,
        symbol: str,
        daily_history_available: bool,
        provider: str | None,
        as_of: datetime | None = None,
    ) -> SessionSourceAvailability:
        timestamp = as_of or datetime.now(timezone.utc)
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        normalized = (provider or "").strip().casefold().replace("-", "_")
        test_provider = normalized in self._TEST_PROVIDER_NAMES or normalized.startswith(
            ("mock_", "test_", "fixture_")
        )
        if test_provider:
            return SessionSourceAvailability(
                symbol=symbol,
                data_mode=SessionDataMode.UNAVAILABLE,
                narrative_availability=NarrativeAvailability.UNAVAILABLE,
                intraday_supported=False,
                provider=provider,
                as_of=timestamp,
                reason=(
                    "A test or mock provider is configured and is not eligible for production "
                    "session narratives."
                ),
                test_data_detected=True,
            )
        if daily_history_available:
            return SessionSourceAvailability(
                symbol=symbol,
                data_mode=SessionDataMode.DAILY_ONLY,
                narrative_availability=NarrativeAvailability.DAILY_ONLY,
                intraday_supported=False,
                provider=provider,
                as_of=timestamp,
                reason=(
                    "The production source supplies daily history only; no finalized 5/15-minute "
                    "bars are available for a session narrative."
                ),
            )
        return SessionSourceAvailability(
            symbol=symbol,
            data_mode=SessionDataMode.UNAVAILABLE,
            narrative_availability=NarrativeAvailability.UNAVAILABLE,
            intraday_supported=False,
            provider=provider,
            as_of=timestamp,
            reason="No eligible production intraday or daily source is available.",
        )

    def query(
        self,
        value: SessionNarrativeQuery,
        *,
        daily_history_available: bool,
        provider: str | None,
        latest_daily_session: date | None = None,
        source_id: str | None = None,
    ) -> ProductionSessionNarrativeResult:
        """Compose the canonical fail-closed production response.

        The registered GET handlers validate query parameters into
        ``SessionNarrativeQuery`` and return this model directly.  The handler
        remains responsible for determining whether daily history exists and
        its latest completed session; this adapter performs no provider reads.
        """

        availability = self.availability(
            symbol=value.symbol,
            daily_history_available=daily_history_available,
            provider=provider,
            as_of=value.as_of,
        )
        narrative = self.narrative_builder.from_availability(availability)
        status = (
            SessionAnalysisStatus.DAILY_ONLY
            if availability.data_mode is SessionDataMode.DAILY_ONLY
            else SessionAnalysisStatus.UNAVAILABLE
        )
        limitations = (
            availability.reason,
            "No production source currently supplies finalized 5/15-minute OHLCV bars.",
            (
                "The latest daily session is provenance context only and is not used to infer "
                "intraday phases, VWAP, volume pace, or catalysts."
            ),
            narrative.causality_disclosure,
        )
        eligible_daily = availability.data_mode is SessionDataMode.DAILY_ONLY
        provenance = SessionNarrativeProvenance(
            provider=provider,
            dataset="daily_history" if eligible_daily else "unavailable",
            source_id=source_id if eligible_daily else None,
            data_mode=availability.data_mode,
            as_of=value.as_of,
            latest_daily_session=latest_daily_session if eligible_daily else None,
            intraday_supported=False,
            test_data_detected=availability.test_data_detected,
        )
        return ProductionSessionNarrativeResult(
            query=value,
            status=status,
            availability=availability.narrative_availability,
            provider=provider,
            data_mode=availability.data_mode,
            as_of=value.as_of,
            latest_daily_session=provenance.latest_daily_session,
            narrative=narrative,
            limitations=limitations,
            provenance=provenance,
        )
