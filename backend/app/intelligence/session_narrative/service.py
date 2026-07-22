from __future__ import annotations

from app.analysis_engines.session import SessionAnalysisEngine, SessionAnalysisInput
from app.intelligence.session_narrative.builder import SessionNarrativeBuilder
from app.intelligence.session_narrative.contracts import SessionNarrativeEnvelope


class SessionNarrativeService:
    """Small orchestration boundary; provider reads remain outside this domain."""

    def __init__(
        self,
        *,
        analysis_engine: SessionAnalysisEngine | None = None,
        narrative_builder: SessionNarrativeBuilder | None = None,
    ) -> None:
        self.analysis_engine = analysis_engine or SessionAnalysisEngine()
        self.narrative_builder = narrative_builder or SessionNarrativeBuilder()

    def analyze(self, value: SessionAnalysisInput) -> SessionNarrativeEnvelope:
        analysis = self.analysis_engine.analyze(value)
        return SessionNarrativeEnvelope(
            analysis=analysis,
            narrative=self.narrative_builder.build(analysis),
        )
