from __future__ import annotations

import unittest

from app.analysis_engines.news import (
    NewsClusteringEngine,
    NewsEntityMappingContext,
    NewsEntityMappingEngine,
)
from app.intelligence.news import (
    CorrectionStatus,
    EntityType,
    MappingRelationship,
    NewsEventStatus,
    NewsEventType,
)
from tests.stage8.news_helpers import (
    NOW,
    mapping_engine,
    normalized_event,
    provider_item,
    security_record,
)


class NewsClusteringMappingTests(unittest.TestCase):
    def test_primary_release_and_syndicated_copy_form_one_cluster(self) -> None:
        primary = normalized_event(provider_item("primary"))
        secondary = normalized_event(
            provider_item(
                "wire",
                headline="Acme raises its full year guidance",
                source_identifier="fixture-newswire",
                source_name="Fixture Newswire",
                source_url="https://wire.fixture.test/acme-guidance",
                confirmed_facts=(),
                is_official_release=False,
            )
        )
        result = NewsClusteringEngine().cluster(
            (secondary, primary),
            entity_symbols_by_event={
                primary.event_id: ("ACME",),
                secondary.event_id: ("ACME",),
            },
        )

        self.assertEqual(len(result.clusters), 1)
        cluster = result.clusters[0]
        self.assertEqual(cluster.source_count, 2)
        self.assertEqual(len(cluster.source_members), 2)
        self.assertEqual(cluster.duplicate_count, 1)
        self.assertEqual(cluster.canonical_event_id, primary.event_id)
        self.assertEqual(cluster.primary_source_event_id, primary.event_id)

    def test_same_company_different_event_types_do_not_cluster(self) -> None:
        guidance = normalized_event(provider_item("guidance"))
        product = normalized_event(
            provider_item(
                "product",
                headline="Acme launches a new product",
                structured_event_type=NewsEventType.PRODUCT_LAUNCH,
            )
        )
        result = NewsClusteringEngine().cluster(
            (guidance, product),
            entity_symbols_by_event={
                guidance.event_id: ("ACME",),
                product.event_id: ("ACME",),
            },
        )

        self.assertEqual(len(result.clusters), 2)

    def test_correction_lineage_unions_changed_headline(self) -> None:
        original = normalized_event(provider_item("original"))
        correction = normalized_event(
            provider_item(
                "corrected",
                headline="Acme corrects an earlier release",
                correction_status=CorrectionStatus.CORRECTED,
                supersedes_provider_event_id="original",
                correction_reason="Corrected guidance range.",
                event_status=NewsEventStatus.CORRECTED,
            )
        )
        result = NewsClusteringEngine().cluster((original, correction))

        self.assertEqual(len(result.clusters), 1)
        self.assertIn(correction.event_id, result.clusters[0].correction_event_ids)

    def test_unverified_rumour_later_confirmed_prefers_primary_source(self) -> None:
        rumour = normalized_event(
            provider_item(
                "rumour",
                headline="Acme is in acquisition talks",
                source_identifier="fixture-unverified",
                source_name="Unverified Fixture",
                source_url="https://unverified.fixture.test/rumour",
                structured_event_type=NewsEventType.MERGER_ACQUISITION,
                event_status=NewsEventStatus.UNVERIFIED,
                confirmed_facts=(),
            )
        )
        confirmed = normalized_event(
            provider_item(
                "confirmed",
                headline="Acme confirms acquisition talks",
                structured_event_type=NewsEventType.MERGER_ACQUISITION,
            )
        )
        result = NewsClusteringEngine().cluster(
            (rumour, confirmed),
            entity_symbols_by_event={
                rumour.event_id: ("ACME",),
                confirmed.event_id: ("ACME",),
            },
        )

        self.assertEqual(len(result.clusters), 1)
        self.assertEqual(result.clusters[0].canonical_event_id, confirmed.event_id)
        self.assertEqual(result.clusters[0].primary_source_event_id, confirmed.event_id)

    def test_rumour_later_retracted_preserves_cluster_contradiction(self) -> None:
        rumour = normalized_event(
            provider_item(
                "rumour",
                headline="Acme is in acquisition talks",
                source_identifier="fixture-unverified",
                source_name="Unverified Fixture",
                source_url="https://unverified.fixture.test/rumour",
                structured_event_type=NewsEventType.MERGER_ACQUISITION,
                event_status=NewsEventStatus.UNVERIFIED,
                confirmed_facts=(),
            )
        )
        retraction = normalized_event(
            provider_item(
                "denial",
                headline="Acme denies acquisition talks",
                structured_event_type=NewsEventType.MERGER_ACQUISITION,
                correction_status=CorrectionStatus.RETRACTED,
                supersedes_provider_event_id="rumour",
                correction_reason="The earlier claim was denied.",
                event_status=NewsEventStatus.RETRACTED,
            )
        )
        result = NewsClusteringEngine().cluster((rumour, retraction))

        self.assertEqual(len(result.clusters), 1)
        self.assertIn(retraction.event_id, result.clusters[0].contradiction_event_ids)
        self.assertIn(retraction.event_id, result.clusters[0].correction_event_ids)

    def test_superseded_record_links_forward_to_successor(self) -> None:
        successor = normalized_event(provider_item("successor"))
        superseded = normalized_event(
            provider_item(
                "old",
                headline="Acme publishes an earlier guidance range",
                correction_status=CorrectionStatus.SUPERSEDED,
                superseded_by_provider_event_id="successor",
                event_status=NewsEventStatus.CORRECTED,
            )
        )
        result = NewsClusteringEngine().cluster((superseded, successor))

        self.assertEqual(len(result.clusters), 1)
        self.assertEqual(
            superseded.correction.superseded_by_event_id,
            "provider:hermetic-news:successor",
        )

    def test_mapping_uses_security_sector_industry_index_theme_and_watchlist_registries(self) -> None:
        event = normalized_event()
        result = mapping_engine().map_event(
            event,
            NewsEntityMappingContext(
                candidate_symbols=("ACME",),
                watchlist_symbols=("ACME",),
            ),
            now=NOW,
        )
        types = {mapping.entity_type for mapping in result.mappings}
        relationships = {mapping.relationship for mapping in result.mappings}

        self.assertTrue(
            {
                EntityType.SECURITY,
                EntityType.COMPANY,
                EntityType.SECTOR,
                EntityType.INDUSTRY,
                EntityType.INDEX,
                EntityType.THEME,
                EntityType.WATCHLIST,
            }.issubset(types)
        )
        self.assertIn(MappingRelationship.THEME_MEMBERSHIP, relationships)
        self.assertTrue(all(mapping.evidence_id for mapping in result.mappings))
        self.assertEqual(
            {item.evidence_id for item in result.evidence},
            {item.evidence_id for item in result.mappings},
        )

    def test_ambiguous_plain_ticker_is_rejected_even_if_registry_has_symbol(self) -> None:
        record = security_record("IT")
        engine = NewsEntityMappingEngine(
            security_resolver=lambda symbol: record if symbol == "IT" else None,
            theme_loader=lambda: [],
        )
        event = normalized_event(
            provider_item(
                headline="Company update (IT) remains unclear",
                structured_symbols=(),
            )
        )
        result = engine.map_event(event, NewsEntityMappingContext(), now=NOW)

        self.assertEqual(result.mappings, ())
        self.assertIn("ambiguous_ticker:IT", result.rejected_candidates)

    def test_unknown_structured_symbol_fails_closed(self) -> None:
        result = mapping_engine(include_theme=False).map_event(
            normalized_event(),
            NewsEntityMappingContext(candidate_symbols=("UNKNOWN",)),
            now=NOW,
        )

        self.assertEqual(result.mappings, ())
        self.assertEqual(result.rejected_candidates, ("unregistered_ticker:UNKNOWN",))


if __name__ == "__main__":
    unittest.main()
