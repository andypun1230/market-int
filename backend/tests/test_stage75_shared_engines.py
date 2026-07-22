from __future__ import annotations

import unittest
from datetime import datetime, timezone

from app.analysis_engines.confidence import (
    CONFIDENCE_ENGINE_VERSION,
    ConfidenceAdjustmentEngine,
    ConfidenceAdjustmentInput,
)
from app.analysis_engines.contradiction import (
    CONTRADICTION_ENGINE_VERSION,
    ContradictionAnalysisInput,
    ContradictionEngine,
    ContradictionFinding,
    ContradictionPreservationInput,
)
from app.analysis_engines.evidence_validation import (
    EVIDENCE_VALIDATION_ENGINE_VERSION,
    BreakoutEvidence,
    BreakoutValidationInput,
    ClaimBindingInput,
    EvidenceValidationEngine,
    SourceRecord,
)
from app.analysis_engines.freshness import (
    FRESHNESS_ENGINE_VERSION,
    FreshnessAvailabilityEngine,
    FreshnessAvailabilityInput,
    FreshnessSummaryInput,
)


class FreshnessAvailabilityEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = FreshnessAvailabilityEngine()
        self.now = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)

    def test_injected_now_deterministically_marks_old_observation_stale(self) -> None:
        result = self.engine.evaluate(
            FreshnessAvailabilityInput(
                source_state="live",
                generated_at="2026-07-22T11:58:00Z",
                observed_at="2026-07-22T11:50:00Z",
                market_date="2026-07-22-extra",
                stale_after_seconds=300,
                completeness=1.4,
                provider="fixture",
                warnings=("late source", "late source"),
                now=self.now,
            )
        )

        self.assertEqual(result.engine_version, FRESHNESS_ENGINE_VERSION)
        self.assertEqual(result.state, "stale")
        self.assertEqual(result.availability, "partial")
        self.assertEqual(result.age_seconds, 600.0)
        self.assertEqual(result.market_date, "2026-07-22")
        self.assertEqual(result.completeness, 1.0)
        self.assertEqual(result.confidence_cap_recommendation, "limited")
        self.assertEqual(result.warnings, ("late source",))

    def test_partial_missing_and_malformed_inputs_fail_closed(self) -> None:
        cases = (
            (
                "provider partial",
                FreshnessAvailabilityInput(
                    source_state="live",
                    provider_status="partial",
                    generated_at="2026-07-22T12:00:00Z",
                    completeness=0.7,
                    now=self.now,
                ),
                ("partial", "partial", 0.7, 0.0),
            ),
            (
                "missing source state",
                FreshnessAvailabilityInput(source_state=None, now=self.now),
                ("unavailable", "unavailable", 0.0, None),
            ),
            (
                "malformed source and timestamps",
                FreshnessAvailabilityInput(
                    source_state="not-a-real-state",
                    generated_at="not-a-timestamp",
                    expires_at="also-not-a-timestamp",
                    completeness="not-a-number",  # type: ignore[arg-type]
                    now=self.now,
                ),
                ("unavailable", "unavailable", 0.0, None),
            ),
            (
                "initializing provider",
                FreshnessAvailabilityInput(
                    source_state="live",
                    provider_status="initializing",
                    now=self.now,
                ),
                ("unavailable", "unavailable", 0.0, None),
            ),
        )

        for label, value, expected in cases:
            with self.subTest(label=label):
                result = self.engine.evaluate(value)
                self.assertEqual(
                    (result.state, result.availability, result.completeness, result.age_seconds),
                    expected,
                )
                self.assertEqual(result.confidence_cap_recommendation, "limited")

    def test_summary_aggregates_mixed_states_counts_and_lineage_deterministically(self) -> None:
        result = self.engine.summarize(
            (
                FreshnessSummaryInput(
                    state="live",
                    market_date="2026-07-22",
                    generated_at="2026-07-22T12:00:00Z",
                    warnings=("shared",),
                ),
                FreshnessSummaryInput(
                    state="stale",
                    market_date="2026-07-21",
                    generated_at="2026-07-22T11:00:00Z",
                    warnings=("stale", "shared"),
                ),
                FreshnessSummaryInput(state="unavailable", warnings=("missing",)),
            )
        )

        self.assertEqual(result.overall_state, "mixed")
        self.assertEqual(result.market_dates, ("2026-07-21", "2026-07-22"))
        self.assertEqual(
            result.generated_timestamps,
            ("2026-07-22T11:00:00Z", "2026-07-22T12:00:00Z"),
        )
        self.assertEqual(result.current_count, 1)
        self.assertEqual(result.stale_count, 1)
        self.assertEqual(result.partial_count, 0)
        self.assertEqual(result.unavailable_count, 1)
        self.assertEqual(result.test_count, 0)
        self.assertEqual(result.warnings, ("shared", "stale", "missing"))
        self.assertEqual(result.confidence_cap_recommendation, "limited")

        live_plus_missing = self.engine.aggregate_states(("live", "unavailable"))
        self.assertEqual(live_plus_missing, "partial")
        self.assertEqual(self.engine.aggregate_states(()), "unavailable")


class EvidenceValidationEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = EvidenceValidationEngine()

    def test_deduplication_is_first_win_and_reports_only_conflicting_duplicates(self) -> None:
        values = (
            {"id": "ev-a", "value": 1},
            {"id": "ev-a", "value": 1},
            {"id": "ev-a", "value": 2},
            {"id": "ev-b", "value": 3},
        )
        result = self.engine.deduplicate(
            values,
            identity=lambda item: item["id"],
            fingerprint=lambda item: {"value": item["value"]},
        )

        self.assertEqual(result.engine_version, EVIDENCE_VALIDATION_ENGINE_VERSION)
        self.assertEqual(result.items, (values[0], values[3]))
        self.assertEqual(result.duplicate_count, 2)
        self.assertEqual(len(result.collisions), 1)
        self.assertEqual(result.collisions[0].identity, "ev-a")
        self.assertNotEqual(
            result.collisions[0].first_fingerprint,
            result.collisions[0].duplicate_fingerprint,
        )

    def test_claim_binding_enforces_entity_metric_unit_period_and_quarantine(self) -> None:
        valid = self.engine.validate_claim_binding(
            ClaimBindingInput(
                claim="AAPL 20-session return is 5%.",
                claim_entities=frozenset({"aapl"}),
                evidence_entities=frozenset({"aapl"}),
                evidence_metric="20-session return",
                evidence_unit="%",
                evidence_value=5,
                claim_timeframe="20 sessions",
                evidence_timeframe="20 SESSIONS",
            )
        )
        self.assertTrue(valid.valid)
        self.assertEqual(valid.reasons, ())

        cases = (
            (
                "entity",
                ClaimBindingInput(
                    claim="AAPL RSI is 55.",
                    claim_entities=frozenset({"aapl"}),
                    evidence_entities=frozenset({"msft"}),
                    evidence_metric="RSI 14",
                    evidence_value=55,
                ),
                "entity_mismatch",
            ),
            (
                "metric",
                ClaimBindingInput(
                    claim="AAPL RSI is 55.",
                    claim_entities=frozenset({"aapl"}),
                    evidence_entities=frozenset({"aapl"}),
                    evidence_metric="current price",
                    evidence_value=55,
                ),
                "metric_mismatch",
            ),
            (
                "unit",
                ClaimBindingInput(
                    claim="AAPL 20-session return is 5%.",
                    claim_entities=frozenset({"aapl"}),
                    evidence_entities=frozenset({"aapl"}),
                    evidence_metric="20-session return",
                    evidence_unit="points",
                    evidence_value=5,
                ),
                "unit_mismatch",
            ),
            (
                "period",
                ClaimBindingInput(
                    claim="AAPL 20-session return is 5%.",
                    claim_entities=frozenset({"aapl"}),
                    evidence_entities=frozenset({"aapl"}),
                    evidence_metric="20-session return",
                    evidence_unit="%",
                    evidence_value=5,
                    claim_timeframe="20 sessions",
                    evidence_timeframe="1 session",
                ),
                "period_mismatch",
            ),
            (
                "quarantine",
                ClaimBindingInput(
                    claim="AAPL RSI is 55.",
                    claim_entities=frozenset({"aapl"}),
                    evidence_entities=frozenset({"aapl"}),
                    evidence_metric="RSI 14",
                    evidence_value=55,
                    evidence_quarantined=True,
                ),
                "evidence_unsuitable",
            ),
        )
        for label, value, reason in cases:
            with self.subTest(label=label):
                result = self.engine.validate_claim_binding(value)
                self.assertFalse(result.valid)
                self.assertIn(reason, result.reasons)

    def test_breakout_confirmation_requires_price_trigger_and_volume_for_same_security(self) -> None:
        aapl_price = BreakoutEvidence(
            entity="AAPL",
            entity_keys=frozenset({"aapl"}),
            metric="current price",
            value=125,
        )
        aapl_trigger = BreakoutEvidence(
            entity="AAPL",
            entity_keys=frozenset({"aapl"}),
            metric="breakout level",
            value=120,
        )
        aapl_volume = BreakoutEvidence(
            entity="AAPL",
            entity_keys=frozenset({"aapl"}),
            metric="volume state",
            value="Strong above average volume",
        )
        msft_trigger = BreakoutEvidence(
            entity="MSFT",
            entity_keys=frozenset({"msft"}),
            metric="breakout level",
            value=120,
        )

        self.assertTrue(
            self.engine.validate_breakout_confirmation(
                BreakoutValidationInput(
                    claimed_entities=frozenset({"aapl"}),
                    evidence=(aapl_price, aapl_trigger, aapl_volume),
                )
            )
        )
        self.assertFalse(
            self.engine.validate_breakout_confirmation(
                BreakoutValidationInput(
                    claimed_entities=frozenset({"aapl", "msft"}),
                    evidence=(aapl_price, msft_trigger, aapl_volume),
                )
            )
        )
        self.assertFalse(
            self.engine.validate_breakout_confirmation(
                BreakoutValidationInput(
                    claimed_entities=frozenset({"aapl"}),
                    evidence=(aapl_price, aapl_trigger),
                )
            )
        )

    def test_source_lineage_rejects_malformed_timestamp_and_market_date(self) -> None:
        valid = SourceRecord(
            source_id="src-valid",
            provider="fixture",
            dataset="prices",
            generated_at="2026-07-22T12:00:00Z",
            market_date="2026-07-22",
            raw_engine_reference="snapshot-1",
        )
        bad_timestamp = SourceRecord(
            source_id="src-time",
            provider="fixture",
            dataset="prices",
            generated_at="not-a-time",
            market_date="2026-07-22",
            raw_engine_reference="snapshot-2",
        )
        bad_date = SourceRecord(
            source_id="src-date",
            provider="fixture",
            dataset="prices",
            generated_at=None,
            market_date="07/22/2026",
            raw_engine_reference="snapshot-3",
        )

        self.assertTrue(self.engine.source_timestamp_is_valid(valid))
        self.assertFalse(self.engine.source_timestamp_is_valid(bad_timestamp))
        self.assertFalse(self.engine.source_timestamp_is_valid(bad_date))


class ContradictionEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ContradictionEngine()

    def test_analysis_preserves_explicit_and_lexical_opposition(self) -> None:
        result = self.engine.analyze(
            ContradictionAnalysisInput(
                findings=(
                    ContradictionFinding(
                        evidence_id="support",
                        statement="Breadth is healthy and improving.",
                        preferred_support=True,
                    ),
                    ContradictionFinding(
                        evidence_id="weakness",
                        statement="Participation is weak and deteriorating.",
                    ),
                    ContradictionFinding(
                        evidence_id="explicit",
                        statement="The setup appears constructive.",
                        interpretation_class="contradiction",
                        contradicts_claim_ids=("thesis",),
                    ),
                )
            )
        )

        self.assertEqual(result.engine_version, CONTRADICTION_ENGINE_VERSION)
        self.assertEqual(result.supporting_evidence_ids, ("support",))
        self.assertEqual(result.opposing_evidence_ids, ("weakness", "explicit"))
        self.assertEqual(result.polarity_by_evidence_id["explicit"], "positive")

    def test_preservation_requires_at_least_one_citation_and_disclosed_truncation(self) -> None:
        none_preserved = self.engine.validate_preservation(
            ContradictionPreservationInput(
                expected_evidence_ids=("risk-a", "risk-b"),
                cited_evidence_ids=("support",),
                truncation_disclosed=True,
            )
        )
        self.assertFalse(none_preserved.valid)
        self.assertEqual(none_preserved.reason, "no_contradiction_preserved")
        self.assertEqual(none_preserved.omitted_evidence_ids, ("risk-a", "risk-b"))

        hidden_truncation = self.engine.validate_preservation(
            ContradictionPreservationInput(
                expected_evidence_ids=("risk-a", "risk-b"),
                cited_evidence_ids=("risk-a",),
                truncation_disclosed=False,
            )
        )
        self.assertFalse(hidden_truncation.valid)
        self.assertEqual(hidden_truncation.reason, "truncation_not_disclosed")
        self.assertEqual(hidden_truncation.preserved_evidence_ids, ("risk-a",))
        self.assertEqual(hidden_truncation.omitted_evidence_ids, ("risk-b",))

        disclosed = self.engine.validate_preservation(
            ContradictionPreservationInput(
                expected_evidence_ids=("risk-a", "risk-b"),
                cited_evidence_ids=("risk-a",),
                truncation_disclosed=True,
            )
        )
        self.assertTrue(disclosed.valid)
        self.assertEqual(disclosed.preserved_evidence_ids, ("risk-a",))
        self.assertEqual(disclosed.omitted_evidence_ids, ("risk-b",))

        fail_closed = self.engine.validate_preservation(
            ContradictionPreservationInput(
                expected_evidence_ids=("risk-a",),
                cited_evidence_ids=(),
                truncation_disclosed=False,
                fail_closed_no_claim=True,
            )
        )
        self.assertTrue(fail_closed.valid)
        self.assertEqual(fail_closed.preserved_evidence_ids, ())
        self.assertEqual(fail_closed.omitted_evidence_ids, ())


class ConfidenceAdjustmentEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ConfidenceAdjustmentEngine()

    def test_fresh_evidence_depth_sets_moderate_with_explicit_contribution(self) -> None:
        result = self.engine.adjust(
            ConfidenceAdjustmentInput(
                intent="MARKET_STATE",
                evidence_count=3,
                freshness_state="live",
            )
        )

        self.assertEqual(result.engine_version, CONFIDENCE_ENGINE_VERSION)
        self.assertEqual(result.label, "moderate")
        self.assertEqual(result.maximum_allowed, "moderate")
        self.assertFalse(result.constrained)
        self.assertEqual(
            [(item.rule, item.effect, item.resulting_cap) for item in result.contributions],
            [("evidence_depth", "set", "moderate")],
        )

    def test_constrained_missing_and_contradictory_input_exposes_every_rule(self) -> None:
        result = self.engine.adjust(
            ConfidenceAdjustmentInput(
                intent="STOCK_DECISION_SUPPORT",
                evidence_count=5,
                freshness_state="live",
                missing_evidence_count=1,
                partial_count=1,
                contradiction_count=2,
                unsupported_dimension_count=1,
                fallback_used=True,
            )
        )

        contributions = {
            item.rule: (item.effect, item.resulting_cap)
            for item in result.contributions
        }
        self.assertTrue(result.constrained)
        self.assertEqual(result.label, "limited")
        self.assertEqual(result.maximum_allowed, "limited")
        self.assertEqual(
            contributions,
            {
                "freshness_availability_cap": ("cap", "limited"),
                "missing_dimension_cap": ("cap", "limited"),
                "contradiction_preserved": ("none", None),
            },
        )
        self.assertTrue(self.engine.label_exceeds("high", result.maximum_allowed))
        self.assertFalse(self.engine.label_exceeds("limited", result.maximum_allowed))

    def test_no_evidence_and_non_market_exemption_have_explicit_caps(self) -> None:
        no_evidence = self.engine.adjust(
            ConfidenceAdjustmentInput(
                intent="MARKET_STATE",
                evidence_count=0,
                freshness_state="live",
            )
        )
        self.assertEqual(no_evidence.label, "limited")
        self.assertEqual(
            [item.rule for item in no_evidence.contributions],
            ["no_evidence_cap"],
        )

        exempt = self.engine.adjust(
            ConfidenceAdjustmentInput(
                intent="APP_NAVIGATION",
                evidence_count=0,
                freshness_state="unavailable",
                missing_evidence_count=3,
                exempt_from_market_evidence=True,
            )
        )
        self.assertEqual(exempt.label, "high")
        self.assertEqual(exempt.maximum_allowed, "high")
        self.assertFalse(exempt.constrained)
        self.assertEqual(
            [(item.rule, item.effect, item.resulting_cap) for item in exempt.contributions],
            [("non_market_deterministic", "set", "high")],
        )


if __name__ == "__main__":
    unittest.main()
