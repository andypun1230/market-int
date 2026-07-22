from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from hashlib import sha256
from math import sqrt
from typing import Any

from app.analysis_engines.confidence import (
    ConfidenceAdjustmentEngine,
    ConfidenceAdjustmentInput,
)
from app.analysis_engines.contradiction import (
    ContradictionAnalysisInput,
    ContradictionEngine,
    ContradictionFinding,
)
from app.analysis_engines.evidence_validation import EvidenceValidationEngine, SourceRecord
from app.analysis_engines.freshness import FreshnessAvailabilityEngine, FreshnessAvailabilityInput
from app.analysis_engines.session.calendar import MarketSessionCalendar
from app.analysis_engines.session.contracts import (
    BreakoutTestStatus,
    CatalystAttributionConfidence,
    CatalystEventStatus,
    CatalystReactionWindow,
    CatalystTimelineItem,
    CloseLocationBand,
    ConfidenceContribution,
    EvidenceInterpretation,
    IntradayBar,
    LevelTest,
    PhaseAggregate,
    PhaseCompleteness,
    PhaseDirection,
    PhaseVolume,
    PriceVwapRelation,
    ReferenceLevel,
    ReferenceLevelKind,
    REGULAR_SESSION_PHASES,
    ReversalState,
    SegmentedBar,
    SessionAnalysisInput,
    SessionAnalysisResult,
    SessionAnalysisState,
    SessionAnalysisStatus,
    SessionConfidence,
    SessionConfidenceEffect,
    SessionConfidenceLabel,
    SessionContradictions,
    SessionDataMode,
    SessionEvidence,
    SessionFreshness,
    SessionPhase,
    SessionQuality,
    SessionSourceState,
    SessionStructure,
    TrendState,
    TurningPointKind,
    TurningPointRecord,
    TurningPointSupportBar,
    VolumeAnalysis,
    VolumeConfirmationState,
    VolumePaceState,
    VwapAnalysis,
    VwapBasis,
    SourceAvailabilityState,
)


class SessionAnalysisEngine:
    """Pure, deterministic analysis of finalized 5/15-minute OHLCV bars."""

    def __init__(
        self,
        *,
        calendar: MarketSessionCalendar | None = None,
        freshness_engine: FreshnessAvailabilityEngine | None = None,
        evidence_engine: EvidenceValidationEngine | None = None,
        contradiction_engine: ContradictionEngine | None = None,
        confidence_engine: ConfidenceAdjustmentEngine | None = None,
    ) -> None:
        self.calendar = calendar or MarketSessionCalendar()
        self.freshness_engine = freshness_engine or FreshnessAvailabilityEngine()
        self.evidence_engine = evidence_engine or EvidenceValidationEngine()
        self.contradiction_engine = contradiction_engine or ContradictionEngine()
        self.confidence_engine = confidence_engine or ConfidenceAdjustmentEngine()

    def analyze(self, value: SessionAnalysisInput) -> SessionAnalysisResult:
        bounds = self.calendar.bounds(value.session_date)
        expected_full = self.calendar.regular_bar_starts(value.session_date, value.interval)
        freshness = self._freshness(value, completeness=0.0)
        base_limitations = [
            "Only finalized 5-minute or 15-minute OHLCV bars are eligible.",
            "Extended-hours bars are segmented when present, but extended-hours completeness is not inferred.",
            "All catalyst relationships are temporal observations, not causal explanations.",
        ]

        if value.data_mode in {SessionDataMode.DAILY_ONLY, SessionDataMode.UNAVAILABLE}:
            status = (
                SessionAnalysisStatus.DAILY_ONLY
                if value.data_mode is SessionDataMode.DAILY_ONLY
                else SessionAnalysisStatus.UNAVAILABLE
            )
            warning = (
                "Only daily data is available; intraday session structure was not inferred."
                if status is SessionAnalysisStatus.DAILY_ONLY
                else "No eligible intraday source is available."
            )
            quality = SessionQuality(
                is_calendar_session=bounds.is_open,
                is_early_close=bounds.is_early_close,
                session_complete=False,
                expected_regular_bars=len(expected_full),
                observed_regular_bars=0,
                regular_session_coverage=0.0,
                missing_regular_bar_starts=expected_full,
                excluded_closed_hours_bars=0,
                excluded_unfinalized_bars=0,
                freshness=freshness,
                warnings=(warning,),
            )
            return self._empty_result(
                value,
                status=status,
                analysis_state=(
                    SessionAnalysisState.DAILY_ONLY
                    if status is SessionAnalysisStatus.DAILY_ONLY
                    else SessionAnalysisState.UNAVAILABLE
                ),
                quality=quality,
                limitations=(*base_limitations, warning),
            )

        duration = timedelta(minutes=value.interval.minutes)
        observed_at = value.observed_at.astimezone(self.calendar.timezone)
        segmented: list[SegmentedBar] = []
        eligible: list[IntradayBar] = []
        closed_hours = 0
        unfinalized = 0
        for bar in value.bars:
            phase = self.calendar.phase_at(bar.timestamp, session_date=value.session_date)
            finalized = bar.is_final and bar.timestamp + duration <= value.observed_at
            included = finalized and phase is not SessionPhase.CLOSED
            segmented.append(
                SegmentedBar(
                    timestamp=bar.timestamp,
                    phase=phase,
                    included_in_regular_session=included and phase in REGULAR_SESSION_PHASES,
                    included_in_analysis=included,
                )
            )
            if phase is SessionPhase.CLOSED:
                closed_hours += 1
            elif not finalized:
                unfinalized += 1
            else:
                eligible.append(bar)

        regular = [
            bar
            for bar in eligible
            if self.calendar.phase_at(bar.timestamp, session_date=value.session_date)
            in REGULAR_SESSION_PHASES
        ]
        expected_to_observation = self.calendar.regular_bar_starts(
            value.session_date,
            value.interval,
            completed_through=observed_at,
        )
        expected_set = set(expected_to_observation)
        observed_starts = {
            bar.timestamp.astimezone(self.calendar.timezone)
            for bar in regular
            if bar.timestamp.astimezone(self.calendar.timezone) in expected_set
        }
        missing = tuple(timestamp for timestamp in expected_to_observation if timestamp not in observed_starts)
        coverage = min(1.0, len(observed_starts) / len(expected_set)) if expected_set else 0.0
        freshness = self._freshness(value, completeness=coverage)
        session_complete = bool(
            bounds.is_open
            and bounds.regular_close is not None
            and observed_at >= bounds.regular_close
            and len(observed_starts) >= max(0, len(expected_full) - 1)
        )
        warnings: list[str] = []
        if not bounds.is_open:
            warnings.append("The injected market calendar marks this date closed.")
        if missing:
            warnings.append(f"{len(missing)} expected completed regular-session bars are missing.")
        if closed_hours:
            warnings.append(f"{closed_hours} bars outside configured extended hours were excluded.")
        if unfinalized:
            warnings.append(f"{unfinalized} unfinished or future-ending bars were excluded.")
        if freshness.state in {"stale", "partial", "mixed", "test", "unavailable"}:
            warnings.append(f"Source freshness is constrained: {freshness.state}.")
        if not regular:
            warnings.append("No finalized regular-session bars are eligible for analysis.")

        quality = SessionQuality(
            is_calendar_session=bounds.is_open,
            is_early_close=bounds.is_early_close,
            session_complete=session_complete,
            expected_regular_bars=len(expected_to_observation),
            observed_regular_bars=len(observed_starts),
            regular_session_coverage=round(coverage, 6),
            missing_regular_bar_starts=missing,
            excluded_closed_hours_bars=closed_hours,
            excluded_unfinalized_bars=unfinalized,
            freshness=freshness,
            warnings=tuple(warnings),
        )
        phases = self._phase_aggregates(value, eligible, expected_to_observation)
        if not bounds.is_open:
            closed_state = (
                SessionAnalysisState.CLOSED_WEEKEND
                if value.session_date.weekday() >= 5
                else SessionAnalysisState.CLOSED_HOLIDAY
            )
            return self._empty_result(
                value,
                status=SessionAnalysisStatus.UNAVAILABLE,
                analysis_state=closed_state,
                quality=quality,
                segmented=tuple(segmented),
                phases=phases,
                limitations=(*base_limitations, *warnings),
            )
        if not regular:
            extended_phases = {
                item.phase
                for item in segmented
                if item.included_in_analysis
                and item.phase in {SessionPhase.PREMARKET, SessionPhase.AFTER_HOURS}
            }
            if extended_phases == {SessionPhase.PREMARKET}:
                analysis_state = SessionAnalysisState.PREMARKET_ONLY
            elif extended_phases == {SessionPhase.AFTER_HOURS}:
                analysis_state = SessionAnalysisState.AFTER_HOURS_ONLY
            elif extended_phases:
                analysis_state = SessionAnalysisState.EXTENDED_HOURS_ONLY
            else:
                analysis_state = SessionAnalysisState.UNAVAILABLE
            if analysis_state is not SessionAnalysisState.UNAVAILABLE:
                return self._extended_hours_result(
                    value,
                    analysis_state=analysis_state,
                    segmented=tuple(segmented),
                    phases=phases,
                    quality=quality,
                    limitations=(
                        *base_limitations,
                        *warnings,
                        "Only extended-hours bars are eligible; no regular-session structure, VWAP, volume pace, or level inference was produced.",
                    ),
                )
            return self._empty_result(
                value,
                status=SessionAnalysisStatus.UNAVAILABLE,
                analysis_state=analysis_state,
                quality=quality,
                segmented=tuple(segmented),
                phases=phases,
                limitations=(*base_limitations, *warnings),
            )

        structure = self._structure(value, regular)
        vwap = self._vwap(regular)
        volume = self._volume(value, regular, structure)
        level_tests = self._level_tests(value.reference_levels, regular, volume)
        turning_points = self._turning_points(value, regular)
        catalyst_timeline = self._catalyst_timeline(value, eligible)
        evidence = self._evidence(
            value,
            structure=structure,
            vwap=vwap,
            volume=volume,
            level_tests=level_tests,
            turning_points=turning_points,
            catalyst_timeline=catalyst_timeline,
            quality=quality,
        )
        evidence = self._add_explicit_contradictions(value, structure, vwap, volume, evidence)
        contradictions = self._contradictions(evidence)
        unsupported = sum(
            (
                value.prior_close is None,
                value.volume_baseline is None,
                not value.reference_levels,
            )
        )
        confidence = self._confidence(
            evidence=evidence,
            freshness=freshness,
            missing_count=len(missing),
            unsupported_count=unsupported,
            contradiction_count=len(contradictions.explicit_contradiction_evidence_ids),
            test_data=value.test_data,
        )
        status = SessionAnalysisStatus.COMPLETE
        if (
            coverage < 0.98
            or freshness.state in {"stale", "partial", "mixed", "test", "unavailable"}
            or not session_complete
        ):
            status = SessionAnalysisStatus.PARTIAL
        limitations = list(base_limitations)
        if value.prior_close is None:
            limitations.append("Prior close is unavailable, so the opening gap is not calculated.")
        if value.volume_baseline is None:
            limitations.append("No historical cumulative-volume baseline is available; volume pace is unavailable.")
        if not value.reference_levels:
            limitations.append("No source-backed support or resistance levels were supplied for testing.")
        if vwap.basis is not VwapBasis.REPORTED_BAR_VWAP:
            limitations.append(vwap.disclosure)

        return SessionAnalysisResult(
            symbol=value.symbol,
            session_date=value.session_date,
            status=status,
            analysis_state=SessionAnalysisState.REGULAR_SESSION,
            data_mode=value.data_mode,
            interval=value.interval,
            source_id=value.source_id,
            segmented_bars=tuple(segmented),
            phases=phases,
            structure=structure,
            vwap=vwap,
            volume=volume,
            level_tests=level_tests,
            turning_points=turning_points,
            catalyst_timeline=catalyst_timeline,
            quality=quality,
            evidence=evidence,
            contradictions=contradictions,
            confidence=confidence,
            limitations=tuple(dict.fromkeys(limitations)),
        )

    def _empty_result(
        self,
        value: SessionAnalysisInput,
        *,
        status: SessionAnalysisStatus,
        analysis_state: SessionAnalysisState,
        quality: SessionQuality,
        limitations: tuple[str, ...],
        segmented: tuple[SegmentedBar, ...] = (),
        phases: tuple[PhaseAggregate, ...] = (),
    ) -> SessionAnalysisResult:
        contradictions = SessionContradictions(
            supporting_evidence_ids=(),
            opposing_evidence_ids=(),
            neutral_evidence_ids=(),
            explicit_contradiction_evidence_ids=(),
            engine_version=self.contradiction_engine.version,
        )
        confidence = self._confidence(
            evidence=(),
            freshness=quality.freshness,
            missing_count=max(1, quality.expected_regular_bars),
            unsupported_count=1,
            contradiction_count=0,
            test_data=value.test_data,
        )
        return SessionAnalysisResult(
            symbol=value.symbol,
            session_date=value.session_date,
            status=status,
            analysis_state=analysis_state,
            data_mode=value.data_mode,
            interval=value.interval,
            source_id=value.source_id,
            segmented_bars=segmented,
            phases=phases,
            quality=quality,
            contradictions=contradictions,
            confidence=confidence,
            limitations=tuple(dict.fromkeys(limitations)),
        )

    def _extended_hours_result(
        self,
        value: SessionAnalysisInput,
        *,
        analysis_state: SessionAnalysisState,
        segmented: tuple[SegmentedBar, ...],
        phases: tuple[PhaseAggregate, ...],
        quality: SessionQuality,
        limitations: tuple[str, ...],
    ) -> SessionAnalysisResult:
        evidence = tuple(
            self._evidence_item(
                value,
                f"phase_aggregate:{phase.phase.value}",
                {
                    "observed_bars": phase.observed_bars,
                    "open": phase.open,
                    "high": phase.high,
                    "low": phase.low,
                    "close": phase.close,
                    "return_pct": phase.return_pct,
                    "range_points": phase.range_points,
                    "direction": phase.direction.value,
                    "volatility_proxy_pct": phase.volatility_proxy_pct,
                    "close_location": phase.close_location,
                    "completeness": phase.completeness.value,
                },
                None,
                (
                    f"{phase.observed_bars} finalized {phase.phase.value} bars were observed; "
                    "the aggregate is extended-hours context only and does not imply regular-session behavior."
                ),
                EvidenceInterpretation.OBSERVED_FACT,
                phase=phase.phase,
            )
            for phase in phases
            if phase.phase in {SessionPhase.PREMARKET, SessionPhase.AFTER_HOURS}
            and phase.observed_bars
        )
        contradictions = self._contradictions(evidence)
        confidence = self._confidence(
            evidence=evidence,
            freshness=quality.freshness,
            missing_count=len(quality.missing_regular_bar_starts),
            unsupported_count=3,
            contradiction_count=0,
            test_data=value.test_data,
        )
        return SessionAnalysisResult(
            symbol=value.symbol,
            session_date=value.session_date,
            status=SessionAnalysisStatus.PARTIAL,
            analysis_state=analysis_state,
            data_mode=value.data_mode,
            interval=value.interval,
            source_id=value.source_id,
            segmented_bars=segmented,
            phases=phases,
            quality=quality,
            evidence=evidence,
            contradictions=contradictions,
            confidence=confidence,
            limitations=tuple(dict.fromkeys(limitations)),
        )

    def _freshness(self, value: SessionAnalysisInput, *, completeness: float) -> SessionFreshness:
        result = self.freshness_engine.evaluate(
            FreshnessAvailabilityInput(
                source_state=value.source_state.value,
                generated_at=value.generated_at.isoformat(),
                observed_at=value.observed_at.isoformat(),
                market_date=value.session_date.isoformat(),
                stale_after_seconds=value.stale_after_seconds,
                completeness=completeness,
                provider=value.provider,
                market_session_context="us_equity_intraday",
                test_data=value.test_data,
                now=value.now,
            )
        )
        return SessionFreshness(
            state=SessionSourceState(result.state),
            availability=SourceAvailabilityState(result.availability),
            age_seconds=result.age_seconds,
            completeness=result.completeness,
            provider=result.provider,
            warnings=result.warnings,
            engine_version=result.engine_version,
        )

    def _phase_aggregates(
        self,
        value: SessionAnalysisInput,
        bars: list[IntradayBar],
        expected: tuple[datetime, ...],
    ) -> tuple[PhaseAggregate, ...]:
        by_phase: dict[SessionPhase, list[IntradayBar]] = defaultdict(list)
        for bar in bars:
            by_phase[self.calendar.phase_at(bar.timestamp, session_date=value.session_date)].append(bar)
        expected_by_phase: dict[SessionPhase, int] = defaultdict(int)
        for timestamp in expected:
            expected_by_phase[self.calendar.phase_at(timestamp, session_date=value.session_date)] += 1
        ordered = (
            SessionPhase.PREMARKET,
            SessionPhase.OPENING_PHASE,
            SessionPhase.MORNING,
            SessionPhase.MIDDAY,
            SessionPhase.AFTERNOON,
            SessionPhase.FINAL_HOUR,
            SessionPhase.CLOSE,
            SessionPhase.AFTER_HOURS,
        )
        result: list[PhaseAggregate] = []
        for phase in ordered:
            phase_bars = by_phase.get(phase, [])
            expected_count = expected_by_phase.get(phase, 0)
            if phase in {SessionPhase.PREMARKET, SessionPhase.AFTER_HOURS}:
                # Extended-hours coverage cannot be inferred from the presence
                # of a few bars because the input does not declare a requested
                # extended-hours window.
                expected_count = 0
            observed_count = len(phase_bars)
            coverage = min(1.0, observed_count / expected_count) if expected_count else None
            opening = phase_bars[0].open if phase_bars else None
            closing = phase_bars[-1].close if phase_bars else None
            high = max((bar.high for bar in phase_bars), default=None)
            low = min((bar.low for bar in phase_bars), default=None)
            phase_range = high - low if high is not None and low is not None else None
            return_pct = (
                (closing / opening - 1.0) * 100.0
                if opening is not None and closing is not None
                else None
            )
            if return_pct is None:
                direction = PhaseDirection.UNAVAILABLE
            elif return_pct > 0:
                direction = PhaseDirection.UP
            elif return_pct < 0:
                direction = PhaseDirection.DOWN
            else:
                direction = PhaseDirection.FLAT
            close_returns = [
                (current.close / previous.close - 1.0) * 100.0
                for previous, current in zip(phase_bars, phase_bars[1:])
            ]
            volatility = (
                sqrt(sum(item * item for item in close_returns) / len(close_returns))
                if close_returns
                else None
            )
            close_location = (
                (closing - low) / phase_range
                if closing is not None and low is not None and phase_range is not None and phase_range > 0
                else None
            )
            if close_location is None:
                close_band = CloseLocationBand.UNDEFINED
            elif close_location >= 0.75:
                close_band = CloseLocationBand.UPPER
            elif close_location <= 0.25:
                close_band = CloseLocationBand.LOWER
            else:
                close_band = CloseLocationBand.MIDDLE
            if expected_count == 0:
                completeness = PhaseCompleteness.UNASSESSED
            elif observed_count == 0:
                completeness = PhaseCompleteness.MISSING
            elif observed_count >= expected_count:
                completeness = PhaseCompleteness.COMPLETE
            else:
                completeness = PhaseCompleteness.PARTIAL
            aggregate_limitations: list[str] = []
            if expected_count == 0:
                aggregate_limitations.append(
                    "Expected-bar completeness is unassessed for this phase at the observation boundary."
                )
            if observed_count == 1:
                aggregate_limitations.append(
                    "Volatility proxy requires at least two finalized bars and is unavailable."
                )
            result.append(
                PhaseAggregate(
                    phase=phase,
                    observed_bars=observed_count,
                    expected_bars=expected_count,
                    coverage=round(coverage, 6) if coverage is not None else None,
                    open=opening,
                    high=high,
                    low=low,
                    close=closing,
                    return_pct=round(return_pct, 6) if return_pct is not None else None,
                    volume=sum(bar.volume for bar in phase_bars),
                    range_points=round(phase_range, 8) if phase_range is not None else None,
                    range_pct_of_open=(
                        round(phase_range / opening * 100.0, 6)
                        if phase_range is not None and opening is not None
                        else None
                    ),
                    direction=direction,
                    volatility_proxy_pct=(round(volatility, 6) if volatility is not None else None),
                    close_location=(
                        round(close_location, 6) if close_location is not None else None
                    ),
                    close_location_band=close_band,
                    completeness=completeness,
                    limitations=tuple(aggregate_limitations),
                )
            )
        return tuple(result)

    @staticmethod
    def _structure(value: SessionAnalysisInput, bars: list[IntradayBar]) -> SessionStructure:
        opening = bars[0].open
        closing = bars[-1].close
        high_bar = max(bars, key=lambda bar: (bar.high, -bar.timestamp.timestamp()))
        low_bar = min(bars, key=lambda bar: (bar.low, bar.timestamp.timestamp()))
        high = high_bar.high
        low = low_bar.low
        range_points = high - low
        close_location = (closing - low) / range_points if range_points > 0 else None
        if close_location is None:
            band = CloseLocationBand.UNDEFINED
        elif close_location >= 0.75:
            band = CloseLocationBand.UPPER
        elif close_location <= 0.25:
            band = CloseLocationBand.LOWER
        else:
            band = CloseLocationBand.MIDDLE
        closes = [bar.close for bar in bars]
        path_distance = sum(abs(current - previous) for previous, current in zip(closes, closes[1:]))
        efficiency = abs(closing - closes[0]) / path_distance if path_distance > 0 else 0.0
        net_change_pct = (closing / opening - 1.0) * 100.0
        if net_change_pct >= 0.25 and efficiency >= 0.45:
            trend = TrendState.UP
        elif net_change_pct <= -0.25 and efficiency >= 0.45:
            trend = TrendState.DOWN
        else:
            trend = TrendState.SIDEWAYS
        down_excursion = (opening - low) / opening * 100.0
        up_excursion = (high - opening) / opening * 100.0
        reversal = ReversalState.NONE
        if down_excursion >= 0.30 and closing > opening and (close_location or 0.0) >= 0.65:
            reversal = ReversalState.BULLISH
        elif up_excursion >= 0.30 and closing < opening and (close_location or 1.0) <= 0.35:
            reversal = ReversalState.BEARISH
        return SessionStructure(
            open=opening,
            high=high,
            low=low,
            close=closing,
            high_at=high_bar.timestamp,
            low_at=low_bar.timestamp,
            prior_close=value.prior_close,
            gap_pct=(
                round((opening / value.prior_close - 1.0) * 100.0, 6)
                if value.prior_close is not None
                else None
            ),
            range_points=round(range_points, 8),
            range_pct_of_open=round(range_points / opening * 100.0, 6),
            close_location=round(close_location, 6) if close_location is not None else None,
            close_location_band=band,
            net_change_pct=round(net_change_pct, 6),
            directional_efficiency=round(min(1.0, efficiency), 6),
            trend=trend,
            reversal=reversal,
        )

    @staticmethod
    def _vwap(bars: list[IntradayBar]) -> VwapAnalysis:
        total_volume = sum(bar.volume for bar in bars)
        if total_volume <= 0:
            return VwapAnalysis(
                basis=VwapBasis.UNAVAILABLE,
                reported_vwap_volume_coverage=0.0,
                last_price_relation=PriceVwapRelation.UNAVAILABLE,
                disclosure="Session VWAP is unavailable because eligible volume is zero.",
            )
        weighted = 0.0
        reported_volume = 0
        for bar in bars:
            if bar.aggregate_vwap is not None:
                price = bar.aggregate_vwap
                reported_volume += bar.volume
            else:
                price = (bar.high + bar.low + bar.close) / 3.0
            weighted += price * bar.volume
        session_vwap = weighted / total_volume
        coverage = reported_volume / total_volume
        if coverage >= 1.0:
            basis = VwapBasis.REPORTED_BAR_VWAP
            disclosure = "Session VWAP is volume-weighted from provider-reported aggregate bar VWAP values."
        elif coverage <= 0.0:
            basis = VwapBasis.TYPICAL_PRICE_PROXY
            disclosure = (
                "VWAP is an OHLC typical-price proxy because provider-reported bar VWAP is unavailable; "
                "it is not transaction-level VWAP."
            )
        else:
            basis = VwapBasis.MIXED
            disclosure = (
                "VWAP mixes provider-reported aggregate bar VWAP with OHLC typical-price proxies; "
                "it is not a uniform transaction-level measure."
            )
        deviation = (bars[-1].close / session_vwap - 1.0) * 100.0
        relation = PriceVwapRelation.AT
        if deviation > 0.01:
            relation = PriceVwapRelation.ABOVE
        elif deviation < -0.01:
            relation = PriceVwapRelation.BELOW
        return VwapAnalysis(
            session_vwap=round(session_vwap, 8),
            basis=basis,
            reported_vwap_volume_coverage=round(coverage, 6),
            last_price_deviation_pct=round(deviation, 6),
            last_price_relation=relation,
            disclosure=disclosure,
        )

    def _volume(
        self,
        value: SessionAnalysisInput,
        bars: list[IntradayBar],
        structure: SessionStructure,
    ) -> VolumeAnalysis:
        observed = sum(bar.volume for bar in bars)
        phase_totals: dict[SessionPhase, int] = defaultdict(int)
        for bar in bars:
            phase_totals[self.calendar.phase_at(bar.timestamp, session_date=value.session_date)] += bar.volume
        by_phase = tuple(
            PhaseVolume(
                phase=phase,
                volume=phase_totals.get(phase, 0),
                observed_share=(round(phase_totals.get(phase, 0) / observed, 6) if observed else 0.0),
            )
            for phase in (
                SessionPhase.OPENING_PHASE,
                SessionPhase.MORNING,
                SessionPhase.MIDDAY,
                SessionPhase.AFTERNOON,
                SessionPhase.FINAL_HOUR,
                SessionPhase.CLOSE,
            )
        )
        baseline = value.volume_baseline
        fraction: float | None = None
        expected: float | None = None
        ratio: float | None = None
        pace = VolumePaceState.UNAVAILABLE
        disclosure = (
            "Volume pace is unavailable without a source-backed expected session volume and "
            "cumulative intraday profile; observed volume alone does not measure order flow."
        )
        if baseline is not None:
            through = max(bar.timestamp for bar in bars) + timedelta(minutes=value.interval.minutes)
            elapsed = self.calendar.regular_minutes_elapsed(value.session_date, through)
            bounds = self.calendar.bounds(value.session_date)
            complete = bool(bounds.regular_close and through >= bounds.regular_close)
            if complete:
                fraction = 1.0
            elif baseline.cumulative_profile:
                fraction = self._interpolate_profile(baseline.cumulative_profile, elapsed)
            if fraction is not None and fraction > 0:
                expected = baseline.expected_session_volume * fraction
                ratio = observed / expected if expected > 0 else None
                if ratio is not None:
                    if ratio > 1.10:
                        pace = VolumePaceState.ABOVE
                    elif ratio < 0.90:
                        pace = VolumePaceState.BELOW
                    else:
                        pace = VolumePaceState.IN_LINE
                disclosure = (
                    "Volume pace compares observed regular-session volume with the supplied "
                    "historical expected-volume profile; it does not measure order flow."
                )
        confirmation = VolumeConfirmationState.UNAVAILABLE
        if pace is not VolumePaceState.UNAVAILABLE:
            if structure.trend is TrendState.UP and pace is VolumePaceState.ABOVE:
                confirmation = VolumeConfirmationState.CONFIRMS_UP
            elif structure.trend is TrendState.DOWN and pace is VolumePaceState.ABOVE:
                confirmation = VolumeConfirmationState.CONFIRMS_DOWN
            elif structure.trend is not TrendState.SIDEWAYS and pace is VolumePaceState.BELOW:
                confirmation = VolumeConfirmationState.DOES_NOT_CONFIRM
            else:
                confirmation = VolumeConfirmationState.NEUTRAL
        return VolumeAnalysis(
            observed_volume=observed,
            expected_volume_to_observation=(round(expected, 3) if expected is not None else None),
            expected_cumulative_fraction=(round(fraction, 6) if fraction is not None else None),
            pace_ratio=(round(ratio, 6) if ratio is not None else None),
            pace_state=pace,
            confirmation=confirmation,
            by_phase=by_phase,
            baseline_source_id=baseline.source_id if baseline else None,
            disclosure=disclosure,
        )

    @staticmethod
    def _interpolate_profile(points: tuple[Any, ...], minute_offset: int) -> float | None:
        if not points:
            return None
        if minute_offset <= points[0].minute_offset:
            return points[0].cumulative_fraction
        for left, right in zip(points, points[1:]):
            if minute_offset <= right.minute_offset:
                width = right.minute_offset - left.minute_offset
                if width <= 0:
                    return right.cumulative_fraction
                weight = (minute_offset - left.minute_offset) / width
                return left.cumulative_fraction + weight * (
                    right.cumulative_fraction - left.cumulative_fraction
                )
        return points[-1].cumulative_fraction

    def _turning_points(
        self,
        value: SessionAnalysisInput,
        bars: list[IntradayBar],
    ) -> tuple[TurningPointRecord, ...]:
        """Confirm conservative close-based five-bar pivots.

        Endpoints are intentionally ineligible. Both the approach and departure
        legs must move at least 0.30%, and nearby candidates compete on the
        smaller adjacent leg so bar noise cannot create dense pivot sequences.
        """

        radius = 2
        minimum_leg_pct = 0.30
        candidates: list[tuple[int, TurningPointRecord]] = []
        for index in range(radius, len(bars) - radius):
            support = bars[index - radius : index + radius + 1]
            left = support[:radius]
            current = support[radius]
            right = support[radius + 1 :]
            left_closes = [item.close for item in left]
            right_closes = [item.close for item in right]
            if current.close > max(left_closes) and current.close > max(right_closes):
                kind = TurningPointKind.PEAK
                left_anchor = min(left_closes)
                right_anchor = min(right_closes)
                left_leg = (current.close / left_anchor - 1.0) * 100.0
                right_leg = (current.close - right_anchor) / current.close * 100.0
            elif current.close < min(left_closes) and current.close < min(right_closes):
                kind = TurningPointKind.TROUGH
                left_anchor = max(left_closes)
                right_anchor = max(right_closes)
                left_leg = (left_anchor - current.close) / left_anchor * 100.0
                right_leg = (right_anchor / current.close - 1.0) * 100.0
            else:
                continue
            magnitude = min(left_leg, right_leg)
            if magnitude < minimum_leg_pct:
                continue
            metric = self._turning_point_metric(kind, current.timestamp)
            evidence_id = self._evidence_id(value, metric)
            identity = sha256(
                f"{value.symbol}|{value.session_date.isoformat()}|{kind.value}|{current.timestamp.isoformat()}".encode(
                    "utf-8"
                )
            ).hexdigest()[:16]
            confidence = SessionConfidenceLabel.LIMITED
            if (
                not value.test_data
                and value.source_state
                in {SessionSourceState.LIVE, SessionSourceState.DELAYED, SessionSourceState.CACHED}
                and magnitude >= 0.75
            ):
                confidence = SessionConfidenceLabel.MODERATE
            candidates.append(
                (
                    index,
                    TurningPointRecord(
                        turning_point_id=f"turning-point:{identity}",
                        kind=kind,
                        timestamp=current.timestamp,
                        phase=self.calendar.phase_at(
                            current.timestamp,
                            session_date=value.session_date,
                        ),
                        price=current.close,
                        supporting_bars=tuple(
                            TurningPointSupportBar(timestamp=item.timestamp, close=item.close)
                            for item in support
                        ),
                        movement_magnitude_pct=round(magnitude, 6),
                        evidence_ids=(evidence_id,),
                        confidence=confidence,
                        limitations=(
                            "Confirmed from a strict five-bar close-price pivot with two finalized bars on each side.",
                            "Movement magnitude is the smaller adjacent leg and must be at least 0.30%.",
                            "The turning point is descriptive, omits unconfirmed endpoints, and is not predictive.",
                        ),
                    ),
                )
            )

        separated: list[tuple[int, TurningPointRecord]] = []
        for candidate in candidates:
            if separated and candidate[0] - separated[-1][0] < radius * 2:
                if candidate[1].movement_magnitude_pct > separated[-1][1].movement_magnitude_pct:
                    separated[-1] = candidate
                continue
            separated.append(candidate)
        if len(separated) > 6:
            strongest = sorted(
                separated,
                key=lambda item: (-item[1].movement_magnitude_pct, item[0]),
            )[:6]
            separated = sorted(strongest, key=lambda item: item[0])
        return tuple(item for _, item in separated)

    @staticmethod
    def _turning_point_metric(kind: TurningPointKind, timestamp: datetime) -> str:
        return f"turning_point:{kind.value}:{timestamp.isoformat()}"

    @staticmethod
    def _level_tests(
        levels: tuple[ReferenceLevel, ...],
        bars: list[IntradayBar],
        volume: VolumeAnalysis,
    ) -> tuple[LevelTest, ...]:
        high = max(bar.high for bar in bars)
        low = min(bar.low for bar in bars)
        close = bars[-1].close
        results: list[LevelTest] = []
        for level in levels:
            if level.kind is ReferenceLevelKind.RESISTANCE:
                touched = high >= level.price
                breached = high > level.price
                closed_beyond = close > level.price
                matching_volume = volume.confirmation is VolumeConfirmationState.CONFIRMS_UP
            else:
                touched = low <= level.price
                breached = low < level.price
                closed_beyond = close < level.price
                matching_volume = volume.confirmation is VolumeConfirmationState.CONFIRMS_DOWN
            if not touched:
                status = BreakoutTestStatus.NOT_TESTED
            elif breached and closed_beyond and matching_volume:
                status = BreakoutTestStatus.CONFIRMED_BREAK
            elif breached and closed_beyond:
                status = BreakoutTestStatus.UNCONFIRMED_BREAK
            elif breached:
                status = BreakoutTestStatus.REJECTED
            else:
                status = BreakoutTestStatus.TESTED_HELD
            results.append(
                LevelTest(
                    level_id=level.level_id,
                    kind=level.kind,
                    price=level.price,
                    touched=touched,
                    breached_intrabar=breached,
                    closed_beyond=closed_beyond,
                    status=status,
                    source_id=level.source_id,
                    disclosure=(
                        "A confirmed break requires a close beyond the supplied level and matching "
                        "volume-path confirmation; the test is descriptive, not predictive."
                    ),
                )
            )
        return tuple(results)

    def _catalyst_timeline(
        self,
        value: SessionAnalysisInput,
        bars: list[IntradayBar],
    ) -> tuple[CatalystTimelineItem, ...]:
        result: list[CatalystTimelineItem] = []
        duration = timedelta(minutes=value.interval.minutes)
        for event in sorted(value.catalysts, key=lambda item: (item.occurred_at, item.event_id)):
            if event.occurred_at.astimezone(self.calendar.timezone).date() != value.session_date:
                continue
            if event.published_at is not None and event.published_at > value.observed_at:
                # Point-in-time output must not use an event that had not yet
                # been published at the injected analysis boundary.
                continue
            before = [bar for bar in bars if bar.timestamp + duration <= event.occurred_at]
            window_end = event.occurred_at + timedelta(minutes=event.observation_window_minutes)
            after = [
                bar
                for bar in bars
                if event.occurred_at <= bar.timestamp
                and bar.timestamp + duration <= window_end
            ]
            price_before = before[-1].close if before else None
            price_after = after[-1].close if after else None
            response = (
                (price_after / price_before - 1.0) * 100.0
                if price_before is not None and price_after is not None
                else None
            )
            attribution_limitations = [
                "Observed timing and price movement do not establish that the event caused the response."
            ]
            if price_before is None:
                attribution_limitations.append(
                    "No eligible finalized bar closed before the event timestamp."
                )
            if price_after is None:
                attribution_limitations.append(
                    "No eligible finalized post-event bar closed inside the requested reaction window."
                )
            if window_end > value.observed_at:
                attribution_limitations.append(
                    "The requested reaction window was incomplete at the observation boundary."
                )
            if event.event_status in {
                CatalystEventStatus.RETRACTED,
                CatalystEventStatus.DISPUTED,
                CatalystEventStatus.UNVERIFIED,
            }:
                attribution_limitations.append(
                    f"Event status is {event.event_status.value}; attribution is unavailable."
                )
            attribution_confidence = CatalystAttributionConfidence.UNAVAILABLE
            if (
                response is not None
                and event.event_status
                in {
                    CatalystEventStatus.CONFIRMED,
                    CatalystEventStatus.DEVELOPING,
                    CatalystEventStatus.CORRECTED,
                }
            ):
                attribution_confidence = CatalystAttributionConfidence.LIMITED
            result.append(
                CatalystTimelineItem(
                    event_id=event.event_id,
                    category=event.category,
                    headline=event.headline,
                    occurred_at=event.occurred_at,
                    published_at=event.published_at,
                    phase=self.calendar.phase_at(event.occurred_at, session_date=value.session_date),
                    source_id=event.source_id,
                    affected_entities=event.affected_entities,
                    event_status=event.event_status,
                    materiality=event.materiality,
                    reaction_window=CatalystReactionWindow(
                        start=event.occurred_at,
                        end=window_end,
                        requested_minutes=event.observation_window_minutes,
                        eligible_bar_starts=tuple(bar.timestamp for bar in after),
                    ),
                    price_before=price_before,
                    price_after=price_after,
                    observed_response_pct=round(response, 6) if response is not None else None,
                    attribution_confidence=attribution_confidence,
                    attribution_limitations=tuple(attribution_limitations),
                )
            )
        return tuple(result)

    def _evidence(
        self,
        value: SessionAnalysisInput,
        *,
        structure: SessionStructure,
        vwap: VwapAnalysis,
        volume: VolumeAnalysis,
        level_tests: tuple[LevelTest, ...],
        turning_points: tuple[TurningPointRecord, ...],
        catalyst_timeline: tuple[CatalystTimelineItem, ...],
        quality: SessionQuality,
    ) -> tuple[SessionEvidence, ...]:
        source = SourceRecord(
            source_id=value.source_id,
            provider=value.provider,
            dataset=value.dataset,
            generated_at=value.generated_at.isoformat(),
            market_date=value.session_date.isoformat(),
            raw_engine_reference=value.source_id,
        )
        if not self.evidence_engine.source_timestamp_is_valid(source):
            return ()
        items: list[SessionEvidence] = [
            self._evidence_item(
                value,
                "regular_session_coverage",
                quality.regular_session_coverage,
                "ratio",
                (
                    f"Eligible finalized bars cover {quality.regular_session_coverage * 100.0:.1f}% "
                    "of expected completed regular-session intervals."
                ),
                EvidenceInterpretation.OBSERVED_FACT,
            ),
            self._evidence_item(
                value,
                "source_freshness",
                quality.freshness.state.value,
                None,
                f"The shared freshness engine classifies the source as {quality.freshness.state.value}.",
                EvidenceInterpretation.ENGINE_CONCLUSION,
            ),
            self._evidence_item(
                value,
                "range",
                structure.range_pct_of_open,
                "% of open",
                f"The observed regular-session range is {structure.range_pct_of_open:.2f}% of the open.",
                EvidenceInterpretation.OBSERVED_FACT,
            ),
            self._evidence_item(
                value,
                "close_location",
                structure.close_location,
                "0-1 range",
                f"The last eligible close is in the {structure.close_location_band.value} of the observed range.",
                EvidenceInterpretation.ENGINE_CONCLUSION,
            ),
            self._evidence_item(
                value,
                "trend",
                structure.trend.value,
                None,
                f"The deterministic price-path test classifies the session as {structure.trend.value}.",
                EvidenceInterpretation.ENGINE_CONCLUSION,
            ),
        ]
        if quality.missing_regular_bar_starts:
            items.append(
                self._evidence_item(
                    value,
                    "missing_regular_bars",
                    len(quality.missing_regular_bar_starts),
                    "bars",
                    (
                        f"{len(quality.missing_regular_bar_starts)} expected completed "
                        "regular-session intervals are missing."
                    ),
                    EvidenceInterpretation.MISSING_EVIDENCE,
                )
            )
        if structure.gap_pct is not None:
            items.append(
                self._evidence_item(
                    value,
                    "opening_gap",
                    structure.gap_pct,
                    "%",
                    f"The regular-session open is {structure.gap_pct:+.2f}% versus the supplied prior close.",
                    EvidenceInterpretation.OBSERVED_FACT,
                )
            )
        if structure.reversal is not ReversalState.NONE:
            items.append(
                self._evidence_item(
                    value,
                    "reversal_test",
                    structure.reversal.value,
                    None,
                    f"The deterministic excursion-and-close test identifies {structure.reversal.value}.",
                    EvidenceInterpretation.ENGINE_CONCLUSION,
                )
            )
        if vwap.session_vwap is not None:
            items.append(
                self._evidence_item(
                    value,
                    "session_vwap_deviation",
                    vwap.last_price_deviation_pct,
                    "%",
                    (
                        f"The last eligible close is {vwap.last_price_deviation_pct:+.2f}% "
                        f"{vwap.last_price_relation.value} the calculated VWAP measure."
                    ),
                    EvidenceInterpretation.ENGINE_CONCLUSION,
                )
            )
        if volume.pace_ratio is not None:
            items.append(
                self._evidence_item(
                    value,
                    "volume_pace",
                    volume.pace_ratio,
                    "ratio",
                    f"Observed regular-session volume is {volume.pace_ratio:.2f}x the supplied expected pace.",
                    EvidenceInterpretation.ENGINE_CONCLUSION,
                )
            )
        for level in level_tests:
            items.append(
                self._evidence_item(
                    value,
                    f"level_test:{level.level_id}",
                    level.status.value,
                    None,
                    f"The supplied {level.kind.value} level {level.price:g} tested as {level.status.value}.",
                    EvidenceInterpretation.ENGINE_CONCLUSION,
                    source_id=level.source_id,
                )
            )
        for point in turning_points:
            items.append(
                self._evidence_item(
                    value,
                    self._turning_point_metric(point.kind, point.timestamp),
                    point.movement_magnitude_pct,
                    "% smaller adjacent leg",
                    (
                        f"A confirmed five-bar {point.kind.value} occurred at "
                        f"{point.timestamp.isoformat()} with a {point.movement_magnitude_pct:.2f}% "
                        "minimum adjacent movement; this is descriptive and not predictive."
                    ),
                    EvidenceInterpretation.ENGINE_CONCLUSION,
                    phase=point.phase,
                )
            )
        for item in catalyst_timeline:
            affected = ", ".join(item.affected_entities) if item.affected_entities else "no declared entities"
            statement = (
                f"Sourced catalyst event {item.event_id} ({item.event_status.value}; affected: {affected}) "
                f"was timestamped during {item.phase.value} with attribution confidence "
                f"{item.attribution_confidence.value}; temporal proximity does not establish causality."
            )
            items.append(
                self._evidence_item(
                    value,
                    f"catalyst_timeline:{item.event_id}",
                    item.observed_response_pct,
                    "%" if item.observed_response_pct is not None else None,
                    statement,
                    EvidenceInterpretation.OBSERVED_FACT,
                    source_id=item.source_id,
                    phase=item.phase,
                )
            )
        deduped = self.evidence_engine.deduplicate(
            items,
            identity=lambda item: item.evidence_id,
            fingerprint=lambda item: item.model_dump(mode="json"),
        )
        return deduped.items

    def _add_explicit_contradictions(
        self,
        value: SessionAnalysisInput,
        structure: SessionStructure,
        vwap: VwapAnalysis,
        volume: VolumeAnalysis,
        evidence: tuple[SessionEvidence, ...],
    ) -> tuple[SessionEvidence, ...]:
        additions: list[SessionEvidence] = []
        by_metric = {item.metric: item.evidence_id for item in evidence}
        if structure.trend is TrendState.UP and structure.close_location_band is CloseLocationBand.LOWER:
            additions.append(
                self._evidence_item(
                    value,
                    "contradiction:up_path_lower_close",
                    "up_path_with_lower_quartile_close",
                    None,
                    "The upward path conflicts with a lower-quartile last close.",
                    EvidenceInterpretation.CONTRADICTION,
                    contradicts=tuple(
                        item for item in (by_metric.get("trend"), by_metric.get("close_location")) if item
                    ),
                )
            )
        elif structure.trend is TrendState.DOWN and structure.close_location_band is CloseLocationBand.UPPER:
            additions.append(
                self._evidence_item(
                    value,
                    "contradiction:down_path_upper_close",
                    "down_path_with_upper_quartile_close",
                    None,
                    "The downward path conflicts with an upper-quartile last close.",
                    EvidenceInterpretation.CONTRADICTION,
                    contradicts=tuple(
                        item for item in (by_metric.get("trend"), by_metric.get("close_location")) if item
                    ),
                )
            )
        if (
            vwap.last_price_relation is PriceVwapRelation.BELOW
            and structure.trend is TrendState.UP
            and "trend" in by_metric
        ):
            additions.append(
                self._evidence_item(
                    value,
                    "contradiction:up_path_below_vwap",
                    "up_path_but_below_vwap",
                    None,
                    "The upward path and below-VWAP last close are opposing observations.",
                    EvidenceInterpretation.CONTRADICTION,
                    contradicts=(by_metric["trend"],),
                )
            )
        if (
            volume.confirmation is VolumeConfirmationState.DOES_NOT_CONFIRM
            and structure.trend is not TrendState.SIDEWAYS
            and "trend" in by_metric
        ):
            additions.append(
                self._evidence_item(
                    value,
                    "contradiction:volume_path_nonconfirmation",
                    volume.confirmation.value,
                    None,
                    "The supplied volume baseline does not confirm the directional price path.",
                    EvidenceInterpretation.CONTRADICTION,
                    contradicts=tuple(
                        item for item in (by_metric.get("trend"), by_metric.get("volume_pace")) if item
                    ),
                )
            )
        return (*evidence, *additions)

    def _contradictions(self, evidence: tuple[SessionEvidence, ...]) -> SessionContradictions:
        analysis = self.contradiction_engine.analyze(
            ContradictionAnalysisInput(
                findings=tuple(
                    ContradictionFinding(
                        evidence_id=item.evidence_id,
                        statement=item.statement,
                        interpretation_class=item.interpretation.value,
                        contradicts_claim_ids=item.contradicts_evidence_ids,
                        explicitly_opposing=item.interpretation is EvidenceInterpretation.CONTRADICTION,
                        preferred_support=item.interpretation is not EvidenceInterpretation.MISSING_EVIDENCE,
                    )
                    for item in evidence
                )
            )
        )
        explicit = tuple(
            item.evidence_id
            for item in evidence
            if item.interpretation is EvidenceInterpretation.CONTRADICTION
        )
        return SessionContradictions(
            supporting_evidence_ids=analysis.supporting_evidence_ids,
            opposing_evidence_ids=analysis.opposing_evidence_ids,
            neutral_evidence_ids=analysis.neutral_evidence_ids,
            explicit_contradiction_evidence_ids=explicit,
            engine_version=analysis.engine_version,
        )

    def _confidence(
        self,
        *,
        evidence: tuple[SessionEvidence, ...],
        freshness: SessionFreshness,
        missing_count: int,
        unsupported_count: int,
        contradiction_count: int,
        test_data: bool,
    ) -> SessionConfidence:
        result = self.confidence_engine.adjust(
            ConfidenceAdjustmentInput(
                intent="session_narrative",
                evidence_count=sum(
                    item.interpretation is not EvidenceInterpretation.MISSING_EVIDENCE
                    for item in evidence
                ),
                freshness_state=freshness.state,
                missing_evidence_count=missing_count,
                stale_count=int(freshness.state == "stale"),
                partial_count=int(freshness.state in {"partial", "mixed"}),
                unavailable_count=int(freshness.state == "unavailable"),
                test_count=int(test_data),
                contradiction_count=contradiction_count,
                unsupported_dimension_count=unsupported_count,
                source_quality="intraday_ohlcv",
            )
        )
        return SessionConfidence(
            label=SessionConfidenceLabel(result.label),
            maximum_allowed=SessionConfidenceLabel(result.maximum_allowed),
            constrained=result.constrained,
            contributions=tuple(
                ConfidenceContribution(
                    rule=item.rule,
                    effect=SessionConfidenceEffect(item.effect),
                    resulting_cap=(
                        SessionConfidenceLabel(item.resulting_cap)
                        if item.resulting_cap is not None
                        else None
                    ),
                    reason=item.reason,
                )
                for item in result.contributions
            ),
            engine_version=result.engine_version,
        )

    @staticmethod
    def _evidence_id(
        value: SessionAnalysisInput,
        metric: str,
        source_id: str | None = None,
    ) -> str:
        identity = sha256(
            f"{value.symbol}|{value.session_date.isoformat()}|{metric}|{source_id or value.source_id}".encode(
                "utf-8"
            )
        ).hexdigest()[:16]
        return f"session:{identity}"

    @staticmethod
    def _evidence_item(
        value: SessionAnalysisInput,
        metric: str,
        metric_value: Any,
        unit: str | None,
        statement: str,
        interpretation: EvidenceInterpretation,
        *,
        source_id: str | None = None,
        phase: SessionPhase | None = None,
        contradicts: tuple[str, ...] = (),
    ) -> SessionEvidence:
        return SessionEvidence(
            evidence_id=SessionAnalysisEngine._evidence_id(value, metric, source_id),
            entity=value.symbol,
            metric=metric,
            value=metric_value,
            unit=unit,
            statement=statement,
            interpretation=interpretation,
            source_id=source_id or value.source_id,
            phase=phase,
            contradicts_evidence_ids=contradicts,
        )
