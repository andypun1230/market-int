from __future__ import annotations

import unittest
from datetime import timedelta

from app.analysis_engines.news import NewsMarketReactionEngine, NewsMaterialityEngine
from app.intelligence.news import (
    ExpectedDirection,
    MarketReactionObservation,
    MaterialityInputs,
    NewsFreshnessState,
    ReactionClassification,
    ReactionWindow,
    SourceQuality,
)
from tests.stage8.news_helpers import NOW


def observation(
    *,
    window: ReactionWindow = ReactionWindow.CLOSE_TO_CLOSE,
    price_return: float | None = -0.04,
    benchmark_return: float | None = 0.005,
    volume_ratio: float | None = 1.8,
    evidence_ids: tuple[str, ...] = ("price-evidence-1",),
    source_id: str | None = "daily-adjusted-bars:ACME",
    source_quality: SourceQuality = SourceQuality.HIGH_CONFIDENCE_SECONDARY,
) -> MarketReactionObservation:
    return MarketReactionObservation(
        event_id="event-1",
        entity_id="sec-acme",
        symbol="ACME",
        window=window,
        window_start=NOW - timedelta(days=1),
        window_end=NOW,
        price_return=price_return,
        benchmark_return=benchmark_return,
        volume_ratio=volume_ratio,
        expected_direction=ExpectedDirection.POSITIVE,
        evidence_ids=evidence_ids,
        source_id=source_id,
        source_quality=source_quality,
        source_state=NewsFreshnessState.LIVE,
    )


class NewsMaterialityReactionTests(unittest.TestCase):
    def test_watchlist_relevance_does_not_raise_market_materiality(self) -> None:
        engine = NewsMaterialityEngine()
        common = dict(
            source_credibility=1,
            directness=0.8,
            market_scope=0.3,
            freshness=1,
        )
        without_watchlist = engine.assess(
            MaterialityInputs(**common, user_watchlist_relevance=0),
            source_quality=SourceQuality.PRIMARY,
        )
        with_watchlist = engine.assess(
            MaterialityInputs(**common, user_watchlist_relevance=1),
            source_quality=SourceQuality.PRIMARY,
        )

        self.assertEqual(
            without_watchlist.market_materiality,
            with_watchlist.market_materiality,
        )
        self.assertEqual(without_watchlist.user_relevance, 0)
        self.assertEqual(with_watchlist.user_relevance, 100)

    def test_unverified_source_credibility_is_capped(self) -> None:
        engine = NewsMaterialityEngine()
        primary = engine.assess(
            MaterialityInputs(source_credibility=1, directness=1, freshness=1),
            source_quality=SourceQuality.PRIMARY,
        )
        unverified = engine.assess(
            MaterialityInputs(source_credibility=1, directness=1, freshness=1),
            source_quality=SourceQuality.UNVERIFIED,
        )

        self.assertLess(unverified.market_materiality, primary.market_materiality)

    def test_positive_event_with_negative_daily_reaction_is_rejected(self) -> None:
        result = NewsMarketReactionEngine().assess(
            event_id="event-1",
            expected_direction=ExpectedDirection.POSITIVE,
            observations=(observation(),),
        )

        self.assertEqual(
            result.assessment.classification,
            ReactionClassification.REJECTS_POSITIVE,
        )
        self.assertIn("not confirmed", result.assessment.summary)
        self.assertNotIn("caused", result.assessment.summary.casefold())
        self.assertGreater(result.observed_price_strength, 0)

    def test_intraday_window_is_blocked_when_only_daily_data_supported(self) -> None:
        result = NewsMarketReactionEngine().assess(
            event_id="event-1",
            expected_direction=ExpectedDirection.POSITIVE,
            observations=(observation(window=ReactionWindow.FIFTEEN_MINUTES),),
        )

        self.assertEqual(
            result.assessment.classification,
            ReactionClassification.INSUFFICIENT_DATA,
        )
        self.assertEqual(result.assessment.observations, ())
        self.assertIn(
            "intraday_reaction_unavailable_daily_only",
            result.assessment.limitations,
        )

    def test_supported_window_without_price_stays_missing_and_emits_no_price_evidence(self) -> None:
        result = NewsMarketReactionEngine().assess(
            event_id="event-1",
            expected_direction=ExpectedDirection.POSITIVE,
            observations=(
                observation(
                    price_return=None,
                    benchmark_return=0.01,
                    volume_ratio=1.4,
                ),
            ),
        )

        self.assertEqual(
            result.assessment.classification,
            ReactionClassification.INSUFFICIENT_DATA,
        )
        self.assertEqual(result.evidence, ())
        self.assertEqual(result.assessment.evidence_ids, ())
        self.assertIn("price_reaction_unavailable", result.assessment.limitations)

    def test_small_daily_move_is_no_material_reaction(self) -> None:
        result = NewsMarketReactionEngine().assess(
            event_id="event-1",
            expected_direction=ExpectedDirection.NEGATIVE,
            observations=(
                observation(price_return=0.003, benchmark_return=0.001, volume_ratio=None),
            ),
        )

        self.assertEqual(
            result.assessment.classification,
            ReactionClassification.NO_MATERIAL_REACTION,
        )
        self.assertIn("volume_confirmation_unavailable", result.assessment.limitations)

    def test_missing_benchmark_uses_absolute_return_without_fabricating_relative_evidence(self) -> None:
        result = NewsMarketReactionEngine().assess(
            event_id="event-1",
            expected_direction=ExpectedDirection.POSITIVE,
            observations=(observation(price_return=0.02, benchmark_return=None),),
        )

        self.assertEqual(
            result.assessment.classification,
            ReactionClassification.CONFIRMS_POSITIVE,
        )
        self.assertIn(
            "benchmark_relative_reaction_unavailable",
            result.assessment.limitations,
        )
        self.assertIn("absolute price return", result.evidence[0].statement)
        self.assertIn("benchmark-relative return is unavailable", result.evidence[0].statement)
        self.assertNotIn("0.0000", result.evidence[0].statement)

    def test_untraceable_price_observation_cannot_drive_a_reaction_claim(self) -> None:
        result = NewsMarketReactionEngine().assess(
            event_id="event-1",
            expected_direction=ExpectedDirection.POSITIVE,
            observations=(
                observation(
                    price_return=0.03,
                    evidence_ids=(),
                    source_id=None,
                    source_quality=SourceQuality.UNAVAILABLE,
                ),
            ),
        )

        self.assertEqual(
            result.assessment.classification,
            ReactionClassification.INSUFFICIENT_DATA,
        )
        self.assertEqual(result.evidence, ())
        self.assertIn(
            "reaction_source_lineage_unvalidated",
            result.assessment.limitations,
        )

    def test_unverified_price_source_cannot_drive_a_reaction_claim(self) -> None:
        result = NewsMarketReactionEngine().assess(
            event_id="event-1",
            expected_direction=ExpectedDirection.POSITIVE,
            observations=(
                observation(
                    price_return=0.03,
                    source_id="anonymous-price-post",
                    source_quality=SourceQuality.UNVERIFIED,
                ),
            ),
        )

        self.assertEqual(
            result.assessment.classification,
            ReactionClassification.INSUFFICIENT_DATA,
        )
        self.assertEqual(result.evidence, ())
        self.assertIn(
            "reaction_source_lineage_unvalidated",
            result.assessment.limitations,
        )


if __name__ == "__main__":
    unittest.main()
