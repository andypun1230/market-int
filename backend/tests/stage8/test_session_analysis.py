from __future__ import annotations

import unittest
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from app.analysis_engines.confidence import CONFIDENCE_ENGINE_VERSION
from app.analysis_engines.contradiction import CONTRADICTION_ENGINE_VERSION
from app.analysis_engines.freshness import FRESHNESS_ENGINE_VERSION
from app.analysis_engines.session import (
    BarInterval,
    BreakoutTestStatus,
    CatalystAttributionConfidence,
    CatalystCategory,
    CatalystEvent,
    CatalystEventStatus,
    IntradayBar,
    MarketCalendarConfig,
    MarketSessionCalendar,
    PhaseCompleteness,
    PhaseDirection,
    ReferenceLevel,
    ReferenceLevelKind,
    ReversalState,
    SessionAnalysisEngine,
    SessionAnalysisInput,
    SessionAnalysisStatus,
    SessionAnalysisState,
    SessionDataMode,
    SessionPhase,
    SessionSourceState,
    TrendState,
    TurningPointKind,
    VolumeBaseline,
    VolumeConfirmationState,
    VolumePaceState,
    VolumeProfilePoint,
    VwapBasis,
)


NY = ZoneInfo("America/New_York")
SESSION_DATE = date(2026, 7, 22)


def dt(hour: int, minute: int, *, day: date = SESSION_DATE) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=NY)


def bar(
    timestamp: datetime,
    opening: float,
    closing: float,
    *,
    low: float | None = None,
    high: float | None = None,
    volume: int = 1_000,
    reported_vwap: bool = True,
    is_final: bool = True,
) -> IntradayBar:
    low_value = low if low is not None else min(opening, closing) - 0.02
    high_value = high if high is not None else max(opening, closing) + 0.02
    return IntradayBar(
        timestamp=timestamp,
        open=float(opening),
        high=float(high_value),
        low=float(low_value),
        close=float(closing),
        volume=volume,
        aggregate_vwap=(float((opening + high_value + low_value + closing) / 4.0) if reported_vwap else None),
        is_final=is_final,
    )


def full_session_bars(*, interval: BarInterval = BarInterval.FIVE_MINUTES) -> tuple[IntradayBar, ...]:
    count = 78 if interval is BarInterval.FIVE_MINUTES else 26
    values: list[IntradayBar] = []
    for index in range(count):
        timestamp = dt(9, 30) + timedelta(minutes=index * interval.minutes)
        opening = 100.0 + index * 0.10
        values.append(bar(timestamp, opening, opening + 0.08))
    return tuple(values)


def analysis_input(
    bars: tuple[IntradayBar, ...],
    *,
    interval: BarInterval = BarInterval.FIVE_MINUTES,
    observed_at: datetime | None = None,
    prior_close: float | None = 99.0,
    reference_levels: tuple[ReferenceLevel, ...] = (),
    volume_baseline: VolumeBaseline | None = None,
    catalysts: tuple[CatalystEvent, ...] = (),
    session_date: date = SESSION_DATE,
    provider: str = "fixture",
    source_state: SessionSourceState = SessionSourceState.TEST,
    test_data: bool = True,
) -> SessionAnalysisInput:
    observed = observed_at or dt(16, 1, day=session_date)
    return SessionAnalysisInput(
        symbol="TEST",
        session_date=session_date,
        interval=interval,
        data_mode=(
            SessionDataMode.INTRADAY_5M
            if interval is BarInterval.FIVE_MINUTES
            else SessionDataMode.INTRADAY_15M
        ),
        bars=bars,
        prior_close=prior_close,
        reference_levels=reference_levels,
        volume_baseline=volume_baseline,
        catalysts=catalysts,
        provider=provider,
        source_id="recorded-session-fixture",
        source_state=source_state,
        generated_at=observed,
        observed_at=observed,
        now=observed + timedelta(minutes=1),
        test_data=test_data,
    )


class SessionCalendarTests(unittest.TestCase):
    def test_holidays_and_early_closes_are_injected_and_hermetic(self) -> None:
        holiday = date(2026, 7, 3)
        early = date(2026, 11, 27)
        calendar = MarketSessionCalendar(
            MarketCalendarConfig(
                holidays=frozenset({holiday}),
                early_closes={early: time(13, 0)},
            )
        )

        self.assertFalse(calendar.bounds(holiday).is_open)
        self.assertTrue(calendar.bounds(early).is_early_close)
        self.assertEqual(len(calendar.regular_bar_starts(early, BarInterval.FIVE_MINUTES)), 42)
        self.assertEqual(len(calendar.regular_bar_starts(early, BarInterval.FIFTEEN_MINUTES)), 14)
        bounds = calendar.bounds(early)
        self.assertEqual(bounds.opening_phase_end, dt(10, 30, day=early))
        self.assertEqual(bounds.final_hour_start, dt(12, 0, day=early))
        self.assertEqual(bounds.close_phase_start, dt(12, 30, day=early))
        self.assertEqual(calendar.phase_at(dt(11, 59, day=early)), SessionPhase.MORNING)
        self.assertEqual(calendar.phase_at(dt(12, 0, day=early)), SessionPhase.FINAL_HOUR)
        self.assertEqual(calendar.phase_at(dt(12, 29, day=early)), SessionPhase.FINAL_HOUR)
        self.assertEqual(calendar.phase_at(dt(12, 30, day=early)), SessionPhase.CLOSE)
        self.assertEqual(calendar.phase_at(dt(13, 0, day=early)), SessionPhase.AFTER_HOURS)

    def test_new_york_boundaries_are_dst_safe(self) -> None:
        calendar = MarketSessionCalendar()
        summer_open_utc = datetime(2026, 7, 22, 13, 30, tzinfo=timezone.utc)
        winter_open_utc = datetime(2026, 1, 22, 14, 30, tzinfo=timezone.utc)

        self.assertEqual(calendar.phase_at(summer_open_utc), SessionPhase.OPEN)
        self.assertEqual(calendar.phase_at(winter_open_utc), SessionPhase.OPEN)

    def test_phase_boundaries_cover_extended_and_regular_segments(self) -> None:
        calendar = MarketSessionCalendar()
        cases = (
            (dt(4, 0), SessionPhase.PREMARKET),
            (dt(9, 30), SessionPhase.OPENING_PHASE),
            (dt(10, 29), SessionPhase.OPENING_PHASE),
            (dt(10, 30), SessionPhase.MORNING),
            (dt(12, 0), SessionPhase.MIDDAY),
            (dt(14, 0), SessionPhase.AFTERNOON),
            (dt(15, 0), SessionPhase.FINAL_HOUR),
            (dt(15, 29), SessionPhase.FINAL_HOUR),
            (dt(15, 30), SessionPhase.CLOSE),
            (dt(16, 0), SessionPhase.AFTER_HOURS),
            (dt(20, 0), SessionPhase.CLOSED),
        )
        for timestamp, expected in cases:
            with self.subTest(timestamp=timestamp):
                self.assertEqual(calendar.phase_at(timestamp), expected)


class SessionContractTests(unittest.TestCase):
    def test_contracts_reject_naive_timestamps_extra_fields_and_mock_as_live(self) -> None:
        with self.assertRaises(ValidationError):
            IntradayBar.model_validate(
                {
                    "timestamp": datetime(2026, 7, 22, 9, 30),
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.0,
                    "close": 100.5,
                    "volume": 1_000,
                }
            )
        with self.assertRaises(ValidationError):
            IntradayBar.model_validate(
                {
                    "timestamp": dt(9, 30),
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.0,
                    "close": 100.5,
                    "volume": 1_000,
                    "unexpected": True,
                }
            )
        recorded_bar = bar(dt(9, 30), 100.0, 100.1)
        with self.assertRaisesRegex(ValidationError, "cannot be represented as live"):
            SessionAnalysisInput(
                symbol="TEST",
                session_date=SESSION_DATE,
                interval=BarInterval.FIVE_MINUTES,
                data_mode=SessionDataMode.INTRADAY_5M,
                bars=(recorded_bar,),
                provider="mock",
                source_id="bad-source",
                source_state=SessionSourceState.LIVE,
                generated_at=dt(9, 36),
                observed_at=dt(9, 36),
                now=dt(9, 37),
            )

    def test_contract_rejects_daily_bars_as_intraday_payload(self) -> None:
        with self.assertRaisesRegex(ValidationError, "cannot contain intraday bars"):
            SessionAnalysisInput(
                symbol="TEST",
                session_date=SESSION_DATE,
                interval=BarInterval.FIVE_MINUTES,
                data_mode=SessionDataMode.DAILY_ONLY,
                bars=(bar(dt(9, 30), 100.0, 100.1),),
                provider="polygon",
                source_id="daily-source",
                source_state=SessionSourceState.CACHED,
                generated_at=dt(16, 0),
                observed_at=dt(16, 0),
                now=dt(16, 1),
            )

    def test_contract_rejects_duplicate_catalyst_ids(self) -> None:
        event = CatalystEvent(
            event_id="duplicate",
            occurred_at=dt(9, 31),
            category=CatalystCategory.COMPANY_NEWS,
            headline="Sourced update",
            source_id="wire",
        )
        with self.assertRaisesRegex(ValidationError, "event IDs must be unique"):
            analysis_input(
                (bar(dt(9, 30), 100.0, 100.1),),
                observed_at=dt(9, 36),
                catalysts=(event, event),
            )


class SessionAnalysisEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = SessionAnalysisEngine()

    def test_full_session_computes_structure_vwap_volume_breakout_and_evidence(self) -> None:
        bars = full_session_bars()
        baseline = VolumeBaseline(
            expected_session_volume=60_000,
            as_of=dt(16, 0) - timedelta(days=1),
            source_id="volume-baseline",
            cumulative_profile=(
                VolumeProfilePoint(minute_offset=0, cumulative_fraction=0.0),
                VolumeProfilePoint(minute_offset=195, cumulative_fraction=0.50),
                VolumeProfilePoint(minute_offset=390, cumulative_fraction=1.0),
            ),
        )
        level = ReferenceLevel(
            level_id="resistance-104",
            kind=ReferenceLevelKind.RESISTANCE,
            price=104.0,
            source_id="reviewed-levels",
            as_of=dt(9, 0),
        )
        catalyst = CatalystEvent(
            event_id="event-1",
            occurred_at=dt(10, 2),
            category=CatalystCategory.COMPANY_NEWS,
            headline="Company published an operational update",
            source_id="news-wire",
        )

        result = self.engine.analyze(
            analysis_input(
                bars,
                reference_levels=(level,),
                volume_baseline=baseline,
                catalysts=(catalyst,),
            )
        )

        self.assertEqual(result.status, SessionAnalysisStatus.PARTIAL)  # test data is constrained
        self.assertTrue(result.quality.session_complete)
        self.assertEqual(result.quality.expected_regular_bars, 78)
        self.assertEqual(result.quality.observed_regular_bars, 78)
        self.assertEqual(result.quality.regular_session_coverage, 1.0)
        self.assertEqual(result.structure.trend, TrendState.UP)
        self.assertGreater(result.structure.gap_pct, 1.0)
        self.assertEqual(result.vwap.basis, VwapBasis.REPORTED_BAR_VWAP)
        self.assertGreater(result.vwap.last_price_deviation_pct, 0.0)
        self.assertEqual(result.volume.pace_state, VolumePaceState.ABOVE)
        self.assertEqual(result.volume.confirmation, VolumeConfirmationState.CONFIRMS_UP)
        self.assertEqual(result.level_tests[0].status, BreakoutTestStatus.CONFIRMED_BREAK)
        self.assertEqual(result.catalyst_timeline[0].relationship, "temporal_proximity_only")
        self.assertIn("does not establish causality", result.catalyst_timeline[0].disclosure)
        self.assertGreaterEqual(len(result.evidence), 8)
        self.assertEqual(result.quality.freshness.engine_version, FRESHNESS_ENGINE_VERSION)
        self.assertEqual(result.contradictions.engine_version, CONTRADICTION_ENGINE_VERSION)
        self.assertEqual(result.confidence.engine_version, CONFIDENCE_ENGINE_VERSION)
        self.assertEqual(result.confidence.label, "limited")

    def test_complete_recorded_source_can_reach_moderate_but_never_high_confidence(self) -> None:
        bars = full_session_bars()
        baseline = VolumeBaseline(
            expected_session_volume=78_000,
            as_of=dt(9, 0),
            source_id="volume-baseline",
            cumulative_profile=(
                VolumeProfilePoint(minute_offset=0, cumulative_fraction=0.0),
                VolumeProfilePoint(minute_offset=390, cumulative_fraction=1.0),
            ),
        )
        level = ReferenceLevel(
            level_id="reviewed-resistance",
            kind=ReferenceLevelKind.RESISTANCE,
            price=104.0,
            source_id="reviewed-levels",
            as_of=dt(9, 0),
        )
        result = self.engine.analyze(
            analysis_input(
                bars,
                volume_baseline=baseline,
                reference_levels=(level,),
                provider="recorded_vendor",
                source_state=SessionSourceState.DELAYED,
                test_data=False,
            )
        )

        self.assertEqual(result.status, SessionAnalysisStatus.COMPLETE)
        self.assertEqual(result.confidence.label, "moderate")
        self.assertEqual(result.confidence.maximum_allowed, "moderate")

    def test_phase_aggregates_include_enriched_metrics_and_exact_normal_counts(self) -> None:
        result = self.engine.analyze(analysis_input(full_session_bars()))
        phases = {item.phase: item for item in result.phases}

        expected_counts = {
            SessionPhase.OPENING_PHASE: 12,
            SessionPhase.MORNING: 18,
            SessionPhase.MIDDAY: 24,
            SessionPhase.AFTERNOON: 12,
            SessionPhase.FINAL_HOUR: 6,
            SessionPhase.CLOSE: 6,
        }
        for phase, expected in expected_counts.items():
            with self.subTest(phase=phase):
                aggregate = phases[phase]
                self.assertEqual(aggregate.observed_bars, expected)
                self.assertEqual(aggregate.expected_bars, expected)
                self.assertEqual(aggregate.completeness, PhaseCompleteness.COMPLETE)
                self.assertEqual(aggregate.direction, PhaseDirection.UP)
                self.assertGreater(aggregate.range_points, 0)
                self.assertGreater(aggregate.range_pct_of_open, 0)
                self.assertIsNotNone(aggregate.volatility_proxy_pct)
                self.assertIsNotNone(aggregate.close_location)

    def test_early_close_rebases_final_hour_and_close_aggregate_counts(self) -> None:
        early = date(2026, 11, 27)
        calendar = MarketSessionCalendar(
            MarketCalendarConfig(early_closes={early: time(13, 0)})
        )
        engine = SessionAnalysisEngine(calendar=calendar)
        bars = tuple(
            bar(
                dt(9, 30, day=early) + timedelta(minutes=index * 5),
                100.0 + index * 0.05,
                100.03 + index * 0.05,
            )
            for index in range(42)
        )
        result = engine.analyze(
            analysis_input(
                bars,
                session_date=early,
                observed_at=dt(13, 1, day=early),
            )
        )
        phases = {item.phase: item for item in result.phases}

        self.assertEqual(phases[SessionPhase.OPENING_PHASE].observed_bars, 12)
        self.assertEqual(phases[SessionPhase.MORNING].observed_bars, 18)
        self.assertEqual(phases[SessionPhase.MIDDAY].observed_bars, 0)
        self.assertEqual(phases[SessionPhase.AFTERNOON].observed_bars, 0)
        self.assertEqual(phases[SessionPhase.FINAL_HOUR].observed_bars, 6)
        self.assertEqual(phases[SessionPhase.CLOSE].observed_bars, 6)
        self.assertTrue(result.quality.is_early_close)

    def test_turning_points_are_deterministic_evidence_linked_and_conservative(self) -> None:
        closes = (100.0, 100.2, 101.0, 100.4, 100.0, 99.7, 99.0, 99.7, 100.2, 100.4)
        bars = tuple(
            bar(
                dt(9, 30) + timedelta(minutes=index * 5),
                closing - 0.02,
                closing,
            )
            for index, closing in enumerate(closes)
        )
        value = analysis_input(bars, observed_at=dt(10, 20))

        first = self.engine.analyze(value)
        second = self.engine.analyze(value)

        self.assertEqual(first.turning_points, second.turning_points)
        self.assertEqual(
            tuple(item.kind for item in first.turning_points),
            (TurningPointKind.PEAK, TurningPointKind.TROUGH),
        )
        evidence_ids = {item.evidence_id for item in first.evidence}
        for point in first.turning_points:
            self.assertEqual(len(point.supporting_bars), 5)
            self.assertGreaterEqual(point.movement_magnitude_pct, 0.30)
            self.assertTrue(set(point.evidence_ids).issubset(evidence_ids))
            self.assertEqual(point.confidence, "limited")
            self.assertTrue(point.limitations)

        noisy = tuple(
            bar(
                dt(9, 30) + timedelta(minutes=index * 5),
                100.0,
                100.04 if index % 2 else 100.0,
            )
            for index in range(12)
        )
        noisy_result = self.engine.analyze(analysis_input(noisy, observed_at=dt(10, 30)))
        self.assertEqual(noisy_result.turning_points, ())

    def test_premarket_and_after_hours_only_states_preserve_extended_aggregates(self) -> None:
        premarket = (
            bar(dt(8, 0), 100.0, 100.1),
            bar(dt(8, 5), 100.1, 100.2),
        )
        pre_result = self.engine.analyze(
            analysis_input(premarket, observed_at=dt(8, 10))
        )
        self.assertEqual(pre_result.status, SessionAnalysisStatus.PARTIAL)
        self.assertEqual(pre_result.analysis_state, SessionAnalysisState.PREMARKET_ONLY)
        self.assertIsNone(pre_result.structure)
        self.assertIsNone(pre_result.vwap)
        self.assertTrue(pre_result.evidence)
        pre_phase = next(item for item in pre_result.phases if item.phase is SessionPhase.PREMARKET)
        self.assertEqual(pre_phase.observed_bars, 2)
        self.assertEqual(pre_phase.completeness, PhaseCompleteness.UNASSESSED)

        after_hours = (
            bar(dt(16, 0), 100.0, 99.9),
            bar(dt(16, 5), 99.9, 99.8),
        )
        after_result = self.engine.analyze(
            analysis_input(after_hours, observed_at=dt(16, 10))
        )
        self.assertEqual(after_result.analysis_state, SessionAnalysisState.AFTER_HOURS_ONLY)
        self.assertIsNone(after_result.structure)
        self.assertIsNone(after_result.volume)
        after_phase = next(
            item for item in after_result.phases if item.phase is SessionPhase.AFTER_HOURS
        )
        self.assertEqual(after_phase.direction, PhaseDirection.DOWN)

    def test_closed_holiday_weekend_and_open_empty_states_are_distinct(self) -> None:
        holiday = date(2026, 7, 3)
        holiday_engine = SessionAnalysisEngine(
            calendar=MarketSessionCalendar(MarketCalendarConfig(holidays=frozenset({holiday})))
        )
        holiday_result = holiday_engine.analyze(
            analysis_input(
                (),
                session_date=holiday,
                observed_at=dt(12, 0, day=holiday),
            )
        )
        self.assertEqual(holiday_result.analysis_state, SessionAnalysisState.CLOSED_HOLIDAY)
        self.assertEqual(holiday_result.status, SessionAnalysisStatus.UNAVAILABLE)
        self.assertIsNone(holiday_result.structure)

        saturday = date(2026, 7, 25)
        weekend_result = self.engine.analyze(
            analysis_input(
                (),
                session_date=saturday,
                observed_at=dt(12, 0, day=saturday),
            )
        )
        self.assertEqual(weekend_result.analysis_state, SessionAnalysisState.CLOSED_WEEKEND)

        empty_open = self.engine.analyze(analysis_input((), observed_at=dt(12, 0)))
        self.assertEqual(empty_open.analysis_state, SessionAnalysisState.UNAVAILABLE)

    def test_catalyst_timeline_preserves_metadata_and_exact_reaction_window(self) -> None:
        bars = tuple(
            bar(
                dt(9, 30) + timedelta(minutes=index * 5),
                100.0 + index * 0.1,
                100.05 + index * 0.1,
            )
            for index in range(10)
        )
        event = CatalystEvent(
            event_id="event-window",
            occurred_at=dt(10, 2),
            published_at=dt(10, 1),
            category=CatalystCategory.POLICY,
            headline="Official policy update",
            source_id="official-release",
            affected_entities=("SPY", "QQQ"),
            event_status=CatalystEventStatus.CORRECTED,
            materiality=88,
            observation_window_minutes=15,
        )
        not_yet_published = CatalystEvent(
            event_id="future-publication",
            occurred_at=dt(9, 45),
            published_at=datetime(2026, 7, 22, 10, 20, 30, tzinfo=NY),
            category=CatalystCategory.COMPANY_NEWS,
            headline="Later publication",
            source_id="wire",
        )
        result = self.engine.analyze(
            analysis_input(
                bars,
                observed_at=dt(10, 20),
                catalysts=(not_yet_published, event),
            )
        )

        self.assertEqual(len(result.catalyst_timeline), 1)
        item = result.catalyst_timeline[0]
        self.assertEqual(item.event_id, "event-window")
        self.assertEqual(item.published_at, dt(10, 1))
        self.assertEqual(item.affected_entities, ("SPY", "QQQ"))
        self.assertEqual(item.event_status, CatalystEventStatus.CORRECTED)
        self.assertEqual(item.materiality, 88)
        self.assertEqual(item.reaction_window.start, dt(10, 2))
        self.assertEqual(item.reaction_window.end, dt(10, 17))
        self.assertEqual(item.reaction_window.eligible_bar_starts, (dt(10, 5), dt(10, 10)))
        self.assertEqual(item.attribution_confidence, CatalystAttributionConfidence.LIMITED)
        self.assertIn("does not establish causality", item.disclosure)

    def test_fifteen_minute_bars_segment_across_all_phases(self) -> None:
        timestamps = (
            dt(4, 0),
            dt(9, 30),
            dt(10, 30),
            dt(12, 0),
            dt(14, 0),
            dt(15, 0),
            dt(15, 30),
            dt(16, 0),
        )
        bars = tuple(bar(timestamp, 100.0 + index, 100.1 + index) for index, timestamp in enumerate(timestamps))
        result = self.engine.analyze(
            analysis_input(
                bars,
                interval=BarInterval.FIFTEEN_MINUTES,
                observed_at=dt(16, 16),
                prior_close=99.0,
            )
        )

        self.assertEqual(
            tuple(item.phase for item in result.segmented_bars),
            (
                SessionPhase.PREMARKET,
                SessionPhase.OPENING_PHASE,
                SessionPhase.MORNING,
                SessionPhase.MIDDAY,
                SessionPhase.AFTERNOON,
                SessionPhase.FINAL_HOUR,
                SessionPhase.CLOSE,
                SessionPhase.AFTER_HOURS,
            ),
        )
        self.assertEqual(result.interval, BarInterval.FIFTEEN_MINUTES)

    def test_unfinalized_bar_is_excluded_and_missing_coverage_is_explicit(self) -> None:
        bars = (
            bar(dt(9, 30), 100.0, 100.1),
            bar(dt(9, 35), 100.1, 100.2, is_final=False),
        )
        result = self.engine.analyze(
            analysis_input(bars, observed_at=dt(9, 40), prior_close=99.0)
        )

        self.assertEqual(result.quality.expected_regular_bars, 2)
        self.assertEqual(result.quality.observed_regular_bars, 1)
        self.assertEqual(result.quality.regular_session_coverage, 0.5)
        self.assertEqual(result.quality.excluded_unfinalized_bars, 1)
        self.assertEqual(result.status, SessionAnalysisStatus.PARTIAL)

    def test_vwap_proxy_and_volume_pace_fail_closed_without_supported_inputs(self) -> None:
        bars = tuple(
            bar(
                dt(9, 30) + timedelta(minutes=index * 5),
                100.0 + index * 0.1,
                100.05 + index * 0.1,
                reported_vwap=False,
            )
            for index in range(6)
        )
        result = self.engine.analyze(
            analysis_input(bars, observed_at=dt(10, 0), volume_baseline=None)
        )

        self.assertEqual(result.vwap.basis, VwapBasis.TYPICAL_PRICE_PROXY)
        self.assertIn("not transaction-level VWAP", result.vwap.disclosure)
        self.assertEqual(result.volume.pace_state, VolumePaceState.UNAVAILABLE)
        self.assertEqual(result.volume.confirmation, VolumeConfirmationState.UNAVAILABLE)
        self.assertIn("does not measure order flow", " ".join(result.limitations + (result.volume.disclosure,)))

    def test_reversal_test_uses_excursion_and_close_location(self) -> None:
        bars = (
            bar(dt(9, 30), 100.0, 99.7, low=99.4, high=100.1),
            bar(dt(9, 35), 99.7, 100.2, low=99.6, high=100.3),
            bar(dt(9, 40), 100.2, 100.8, low=100.1, high=100.9),
        )
        result = self.engine.analyze(analysis_input(bars, observed_at=dt(9, 45)))

        self.assertEqual(result.structure.reversal, ReversalState.BULLISH)

    def test_volume_nonconfirmation_is_preserved_as_explicit_contradiction(self) -> None:
        bars = tuple(
            bar(
                dt(9, 30) + timedelta(minutes=index * 5),
                100.0 + index * 0.1,
                100.08 + index * 0.1,
            )
            for index in range(6)
        )
        baseline = VolumeBaseline(
            expected_session_volume=100_000,
            as_of=dt(9, 0),
            source_id="volume-baseline",
            cumulative_profile=(
                VolumeProfilePoint(minute_offset=0, cumulative_fraction=0.0),
                VolumeProfilePoint(minute_offset=30, cumulative_fraction=0.20),
                VolumeProfilePoint(minute_offset=390, cumulative_fraction=1.0),
            ),
        )
        result = self.engine.analyze(
            analysis_input(bars, observed_at=dt(10, 0), volume_baseline=baseline)
        )

        self.assertEqual(result.structure.trend, TrendState.UP)
        self.assertEqual(result.volume.confirmation, VolumeConfirmationState.DOES_NOT_CONFIRM)
        self.assertEqual(len(result.contradictions.explicit_contradiction_evidence_ids), 1)
        contradiction_id = result.contradictions.explicit_contradiction_evidence_ids[0]
        self.assertIn(contradiction_id, result.contradictions.opposing_evidence_ids)
        self.assertTrue(any(item.evidence_id == contradiction_id for item in result.evidence))

    def test_daily_only_analysis_never_infers_session_structure(self) -> None:
        observed = dt(16, 1)
        value = SessionAnalysisInput(
            symbol="SPY",
            session_date=SESSION_DATE,
            interval=BarInterval.FIVE_MINUTES,
            data_mode=SessionDataMode.DAILY_ONLY,
            provider="polygon",
            source_id="daily-history",
            source_state=SessionSourceState.CACHED,
            generated_at=observed,
            observed_at=observed,
            now=observed + timedelta(minutes=1),
        )

        result = self.engine.analyze(value)

        self.assertEqual(result.status, SessionAnalysisStatus.DAILY_ONLY)
        self.assertIsNone(result.structure)
        self.assertEqual(result.evidence, ())
        self.assertEqual(result.confidence.label, "limited")
        self.assertIn("daily data", " ".join(result.limitations).lower())


if __name__ == "__main__":
    unittest.main()
