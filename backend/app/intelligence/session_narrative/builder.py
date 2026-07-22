from __future__ import annotations

from app.analysis_engines.session import (
    SessionAnalysisResult,
    SessionAnalysisState,
    SessionAnalysisStatus,
    SessionConfidenceLabel,
    SessionDataMode,
    SessionSourceState,
)
from app.analysis_engines.session.contracts import EvidenceInterpretation
from app.intelligence.session_narrative.contracts import (
    NarrativeAvailability,
    NarrativeClaim,
    SessionNarrative,
    SessionSourceAvailability,
    availability_from_status,
)


class SessionNarrativeBuilder:
    """Render bounded observations without introducing unsupported causality."""

    def build(self, analysis: SessionAnalysisResult) -> SessionNarrative:
        availability = availability_from_status(analysis.status)
        if analysis.status in {
            SessionAnalysisStatus.DAILY_ONLY,
            SessionAnalysisStatus.UNAVAILABLE,
        }:
            headline = (
                f"{analysis.symbol} intraday session narrative is unavailable: daily data only."
                if analysis.status is SessionAnalysisStatus.DAILY_ONLY
                else f"{analysis.symbol} intraday session narrative is unavailable."
            )
            return SessionNarrative(
                symbol=analysis.symbol,
                session_date=analysis.session_date,
                availability=availability,
                analysis_state=analysis.analysis_state,
                data_mode=analysis.data_mode,
                headline=headline,
                confidence=analysis.confidence.label,
                freshness=analysis.quality.freshness.state,
                coverage=analysis.quality.regular_session_coverage,
                caveats=self._caveats(analysis),
            )

        claims = tuple(
            NarrativeClaim(
                claim_id=f"claim:{item.evidence_id}",
                text=item.statement,
                evidence_ids=(item.evidence_id,),
            )
            for item in analysis.evidence
            if item.interpretation is not EvidenceInterpretation.MISSING_EVIDENCE
        )
        structure = analysis.structure
        if analysis.analysis_state is SessionAnalysisState.PREMARKET_ONLY:
            headline = (
                f"{analysis.symbol} has premarket-only observations; regular-session behavior "
                "is not inferred."
            )
        elif analysis.analysis_state is SessionAnalysisState.AFTER_HOURS_ONLY:
            headline = (
                f"{analysis.symbol} has after-hours-only observations; regular-session behavior "
                "is not inferred."
            )
        elif analysis.analysis_state is SessionAnalysisState.EXTENDED_HOURS_ONLY:
            headline = (
                f"{analysis.symbol} has extended-hours-only observations; regular-session "
                "behavior is not inferred."
            )
        elif structure is None:  # Defensive: strict result contracts permit an unavailable shape.
            headline = f"{analysis.symbol} session observations are incomplete."
        else:
            headline = (
                f"{analysis.symbol} shows a {structure.trend.value} price path with the last "
                f"eligible close in the {structure.close_location_band.value}."
            )
        return SessionNarrative(
            symbol=analysis.symbol,
            session_date=analysis.session_date,
            availability=availability,
            analysis_state=analysis.analysis_state,
            data_mode=analysis.data_mode,
            headline=headline,
            claims=claims,
            evidence=analysis.evidence,
            confidence=analysis.confidence.label,
            freshness=analysis.quality.freshness.state,
            coverage=analysis.quality.regular_session_coverage,
            caveats=self._caveats(analysis),
        )

    def from_availability(self, availability: SessionSourceAvailability) -> SessionNarrative:
        return SessionNarrative(
            symbol=availability.symbol,
            availability=availability.narrative_availability,
            analysis_state=(
                SessionAnalysisState.DAILY_ONLY
                if availability.data_mode is SessionDataMode.DAILY_ONLY
                else SessionAnalysisState.UNAVAILABLE
            ),
            data_mode=availability.data_mode,
            headline=f"{availability.symbol} intraday session narrative is unavailable.",
            confidence=SessionConfidenceLabel.LIMITED,
            freshness=SessionSourceState.UNAVAILABLE,
            coverage=0.0,
            caveats=(
                availability.reason,
                "Daily observations are not relabeled or interpolated as intraday session evidence.",
                "No catalyst causality is inferred without eligible intraday observations.",
            ),
        )

    @staticmethod
    def _caveats(analysis: SessionAnalysisResult) -> tuple[str, ...]:
        caveats = [*analysis.limitations, *analysis.quality.warnings]
        if analysis.vwap is not None:
            caveats.append(analysis.vwap.disclosure)
        if analysis.volume is not None:
            caveats.append(analysis.volume.disclosure)
        caveats.extend(item.disclosure for item in analysis.level_tests)
        if analysis.catalyst_timeline:
            caveats.append("Catalyst entries are timeline hooks only; temporal proximity is not causality.")
        caveats.append(analysis.causality_disclosure)
        return tuple(dict.fromkeys(item for item in caveats if item))
