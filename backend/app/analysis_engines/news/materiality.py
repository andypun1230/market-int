from __future__ import annotations

from app.intelligence.news.contracts import (
    MaterialityAssessment,
    MaterialityContribution,
    MaterialityInputs,
    SourceQuality,
)


NEWS_MATERIALITY_VERSION = "news-materiality-v1"
SOURCE_CREDIBILITY_CAP = {
    SourceQuality.PRIMARY: 1.0,
    SourceQuality.HIGH_CONFIDENCE_SECONDARY: 0.8,
    SourceQuality.SUPPORTING_SECONDARY: 0.5,
    SourceQuality.UNVERIFIED: 0.1,
    SourceQuality.UNAVAILABLE: 0.0,
}


class NewsMaterialityEngine:
    """Transparent ranking score; it is not a return forecast."""

    version = NEWS_MATERIALITY_VERSION

    def assess(
        self,
        inputs: MaterialityInputs,
        *,
        source_quality: SourceQuality,
    ) -> MaterialityAssessment:
        credibility = min(inputs.source_credibility, SOURCE_CREDIBILITY_CAP[source_quality])
        market_components = (
            ("source_credibility", 15 * credibility, "Configured source-quality contribution."),
            ("directness", 18 * inputs.directness, "Directly affected entities increase ranking."),
            ("surprise", 12 * inputs.surprise, "Structured surprise evidence contribution."),
            ("market_scope", 12 * inputs.market_scope, "Breadth of explicitly mapped market scope."),
            ("entity_significance", 10 * inputs.entity_significance, "Configured entity significance."),
            ("observed_price_reaction", 14 * inputs.observed_price_reaction, "Observed reaction contribution."),
            ("observed_volume_reaction", 10 * inputs.observed_volume_reaction, "Observed volume contribution."),
            ("breadth_confirmation", 8 * inputs.breadth_confirmation, "Observed breadth contribution."),
            ("cross_asset_confirmation", 8 * inputs.cross_asset_confirmation, "Observed cross-asset contribution."),
            ("duration", 5 * inputs.duration, "Observed reaction duration contribution."),
            ("freshness", 5 * inputs.freshness, "Event freshness contribution."),
            ("duplicate_source_adjustment", -min(10.0, inputs.duplicate_count * 2.0), "Repeated coverage is not independent confirmation."),
            ("uncertainty_penalty", -20 * inputs.uncertainty, "Developing, disputed, or unverified evidence penalty."),
        )
        entity_components = (
            10 * credibility,
            25 * inputs.directness,
            15 * inputs.surprise,
            15 * inputs.entity_significance,
            20 * inputs.observed_price_reaction,
            10 * inputs.observed_volume_reaction,
            5 * inputs.duration,
            -20 * inputs.uncertainty,
        )
        contributions = tuple(
            MaterialityContribution(
                component=f"market.{name}",
                points=round(points, 2),
                reason=reason,
            )
            for name, points, reason in market_components
            if points != 0
        )
        return MaterialityAssessment(
            market_materiality=self._score(sum(points for _, points, _ in market_components)),
            entity_materiality=self._score(sum(entity_components)),
            user_relevance=self._score(inputs.user_watchlist_relevance * 100),
            contributions=contributions,
            methodology_version=NEWS_MATERIALITY_VERSION,
        )

    @staticmethod
    def _score(value: float) -> int:
        return max(0, min(100, round(value)))
