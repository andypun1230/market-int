from __future__ import annotations

from app.intelligence.news.contracts import (
    EvidenceKind,
    ExpectedDirection,
    InterpretationClass,
    MarketReactionAssessment,
    MarketReactionObservation,
    NewsContractModel,
    NewsEvidenceRecord,
    ReactionClassification,
    ReactionWindow,
    SourceQuality,
)


NEWS_REACTION_VERSION = "news-daily-reaction-v1"
SUPPORTED_DAILY_WINDOWS = (
    ReactionWindow.CLOSE_TO_CLOSE,
    ReactionWindow.NEXT_SESSION,
    ReactionWindow.MULTI_DAY,
)


class NewsReactionResult(NewsContractModel):
    assessment: MarketReactionAssessment
    evidence: tuple[NewsEvidenceRecord, ...]
    observed_price_strength: float
    observed_volume_strength: float
    breadth_strength: float
    cross_asset_strength: float
    engine_version: str = NEWS_REACTION_VERSION


class NewsMarketReactionEngine:
    """Daily-only observation engine with explicit windows and noncausal wording."""

    version = NEWS_REACTION_VERSION

    def __init__(self, *, material_return_threshold: float = 0.005) -> None:
        self.material_return_threshold = material_return_threshold

    def assess(
        self,
        *,
        event_id: str,
        expected_direction: ExpectedDirection,
        observations: tuple[MarketReactionObservation, ...],
    ) -> NewsReactionResult:
        relevant = tuple(
            observation for observation in observations if observation.event_id == event_id
        )
        supported = tuple(
            observation
            for observation in relevant
            if observation.window in SUPPORTED_DAILY_WINDOWS
        )
        limitations: list[str] = []
        if len(relevant) != len(observations):
            limitations.append("reaction_event_identity_mismatch")
        if len(supported) != len(relevant):
            limitations.append("intraday_reaction_unavailable_daily_only")
        with_price = tuple(
            observation
            for observation in supported
            if observation.price_return is not None
            and observation.evidence_ids
            and observation.source_id is not None
            and observation.source_quality
            in {
                SourceQuality.PRIMARY,
                SourceQuality.HIGH_CONFIDENCE_SECONDARY,
                SourceQuality.SUPPORTING_SECONDARY,
            }
        )
        untraceable_price = tuple(
            observation
            for observation in supported
            if observation.price_return is not None and observation not in with_price
        )
        if untraceable_price:
            limitations.append("reaction_source_lineage_unvalidated")
        if not with_price:
            classification = ReactionClassification.INSUFFICIENT_DATA
            summary = "Daily market-reaction evidence is insufficient."
            limitations.append("price_reaction_unavailable")
        else:
            measured_returns = tuple(
                self._measurement_return(observation) for observation in with_price
            )
            material = tuple(
                value
                for value in measured_returns
                if abs(value) >= self.material_return_threshold
            )
            if not material:
                classification = ReactionClassification.NO_MATERIAL_REACTION
                summary = "The available daily window showed no material price reaction."
            elif any(value > 0 for value in material) and any(value < 0 for value in material):
                classification = ReactionClassification.MIXED
                summary = "The event was followed by mixed daily reactions across measured windows."
            else:
                sign = 1 if material[-1] > 0 else -1
                classification = self._classification(expected_direction, sign)
                summary = self._summary(classification)
        if supported and all(observation.volume_ratio is None for observation in supported):
            limitations.append("volume_confirmation_unavailable")
        if with_price and all(observation.benchmark_return is None for observation in with_price):
            limitations.append("benchmark_relative_reaction_unavailable")
        if with_price and expected_direction in {
            ExpectedDirection.UNKNOWN,
            ExpectedDirection.NEUTRAL,
        }:
            limitations.append("expected_event_direction_unavailable")

        evidence = tuple(
            item
            for observation in supported
            for item in self._evidence(event_id, observation)
        )
        evidence_ids = tuple(dict.fromkeys(item.evidence_id for item in evidence))
        return NewsReactionResult(
            assessment=MarketReactionAssessment(
                classification=classification,
                supported_windows=tuple(
                    dict.fromkeys(observation.window for observation in supported)
                ),
                observations=supported,
                summary=summary,
                evidence_ids=evidence_ids,
                limitations=tuple(dict.fromkeys(limitations)),
                methodology_version=NEWS_REACTION_VERSION,
            ),
            evidence=evidence,
            observed_price_strength=max(
                (
                    min(1.0, abs(self._measurement_return(observation)) / 0.05)
                    for observation in with_price
                ),
                default=0.0,
            ),
            observed_volume_strength=max(
                (
                    min(1.0, max(0.0, (observation.volume_ratio or 1.0) - 1.0))
                    for observation in supported
                    if observation.volume_ratio is not None
                ),
                default=0.0,
            ),
            breadth_strength=max(
                (
                    min(1.0, abs(observation.breadth_change or 0.0))
                    for observation in supported
                    if observation.breadth_change is not None
                ),
                default=0.0,
            ),
            cross_asset_strength=max(
                (
                    abs(observation.cross_asset_confirmation or 0.0)
                    for observation in supported
                    if observation.cross_asset_confirmation is not None
                ),
                default=0.0,
            ),
        )

    @staticmethod
    def _measurement_return(observation: MarketReactionObservation) -> float:
        """Return an excess move only when a benchmark observation exists.

        Absolute return remains a valid, separately disclosed measurement.  A
        missing benchmark must never be represented as a zero-return benchmark.
        """

        if observation.price_return is None:
            raise ValueError("price_return_required_for_reaction_measurement")
        if observation.benchmark_return is None:
            return observation.price_return
        return observation.price_return - observation.benchmark_return

    @staticmethod
    def _classification(
        direction: ExpectedDirection,
        sign: int,
    ) -> ReactionClassification:
        if direction == ExpectedDirection.POSITIVE:
            return (
                ReactionClassification.CONFIRMS_POSITIVE
                if sign > 0
                else ReactionClassification.REJECTS_POSITIVE
            )
        if direction == ExpectedDirection.NEGATIVE:
            return (
                ReactionClassification.CONFIRMS_NEGATIVE
                if sign < 0
                else ReactionClassification.REJECTS_NEGATIVE
            )
        return ReactionClassification.MIXED

    @staticmethod
    def _summary(classification: ReactionClassification) -> str:
        wording = {
            ReactionClassification.CONFIRMS_POSITIVE: "The available daily reaction was consistent with the positive event direction.",
            ReactionClassification.CONFIRMS_NEGATIVE: "The available daily reaction was consistent with the negative event direction.",
            ReactionClassification.REJECTS_POSITIVE: "The positive event direction was not confirmed by the available daily reaction.",
            ReactionClassification.REJECTS_NEGATIVE: "The negative event direction was contradicted by the available daily reaction.",
            ReactionClassification.MIXED: "The available daily reaction was mixed.",
        }
        return wording[classification]

    @staticmethod
    def _evidence(
        event_id: str,
        observation: MarketReactionObservation,
    ) -> tuple[NewsEvidenceRecord, ...]:
        if observation.price_return is None:
            # A zero return is an observation; it must never be substituted
            # for missing price data.
            return ()
        if (
            not observation.evidence_ids
            or observation.source_id is None
            or observation.source_quality
            not in {
                SourceQuality.PRIMARY,
                SourceQuality.HIGH_CONFIDENCE_SECONDARY,
                SourceQuality.SUPPORTING_SECONDARY,
            }
        ):
            return ()
        if observation.benchmark_return is None:
            statement = (
                f"The {observation.window.value} absolute price return was "
                f"{observation.price_return:.4f}; benchmark-relative return is unavailable."
            )
        else:
            excess = NewsMarketReactionEngine._measurement_return(observation)
            statement = (
                f"The {observation.window.value} price return was "
                f"{observation.price_return:.4f}; benchmark-relative return was {excess:.4f}."
            )
        return tuple(
            NewsEvidenceRecord(
                evidence_id=evidence_id,
                source_id=observation.source_id,
                event_id=event_id,
                kind=EvidenceKind.PRICE_REACTION,
                statement=statement,
                interpretation_class=InterpretationClass.OBSERVED_FACT,
                entity_ids=tuple(
                    value for value in (observation.entity_id, observation.symbol) if value
                ),
                observed_at=observation.window_end,
                market_date=observation.window_end.date(),
                source_quality=observation.source_quality,
                quarantined=False,
            )
            for evidence_id in observation.evidence_ids
        )
