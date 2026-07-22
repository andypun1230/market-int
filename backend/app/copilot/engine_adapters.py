from __future__ import annotations

from typing import Any, Iterable

from app.analysis_engines.evidence_validation import EvidenceValidationEngine
from app.analysis_engines.freshness import (
    FreshnessAvailabilityEngine,
    FreshnessAvailabilityInput,
)
from app.copilot.contracts import CopilotEvidenceV1, CopilotFreshnessV1


class CopilotFreshnessAdapter:
    """Map shared freshness facts to the stable Stage 7 Copilot contract."""

    def __init__(self, engine: FreshnessAvailabilityEngine | None = None) -> None:
        self.engine = engine or FreshnessAvailabilityEngine()

    def evaluate(
        self,
        *,
        source_state: Any,
        status: Any,
        generated_at: str | None,
        observed_at: str | None,
        market_date: str | None,
        expires_at: str | None,
        completeness: float,
        provider: str,
        warnings: Iterable[str],
        test: bool,
        stale_after_seconds: int,
    ) -> CopilotFreshnessV1:
        result = self.engine.evaluate(
            FreshnessAvailabilityInput(
                source_state=source_state,
                provider_status=status,
                generated_at=generated_at,
                observed_at=observed_at,
                market_date=market_date,
                expires_at=expires_at,
                stale_after_seconds=stale_after_seconds,
                completeness=completeness,
                provider=provider,
                test_data=test,
                warnings=tuple(warnings),
            )
        )
        return CopilotFreshnessV1(
            state=result.state,
            market_date=result.market_date,
            generated_at=result.generated_at,
            observed_at=result.observed_at,
            expires_at=result.expires_at,
            age_seconds=result.age_seconds,
            completeness=result.completeness,
            provider=result.provider,
            warnings=list(result.warnings),
        )

    def aggregate_states(self, values: Iterable[Any]) -> str:
        return self.engine.aggregate_states(values)


class CopilotEvidenceValidationAdapter:
    """Map shared evidence identity handling to Stage 7 evidence models."""

    def __init__(self, engine: EvidenceValidationEngine | None = None) -> None:
        self.engine = engine or EvidenceValidationEngine()

    def deduplicate(self, values: Iterable[CopilotEvidenceV1]) -> list[CopilotEvidenceV1]:
        result = self.engine.deduplicate(
            values,
            identity=lambda value: value.evidence_id,
        )
        return list(result.items)
