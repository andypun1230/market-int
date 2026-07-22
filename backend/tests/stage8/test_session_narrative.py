from __future__ import annotations

import json
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from app.analysis_engines.session import (
    BarInterval,
    CatalystCategory,
    CatalystEvent,
    EvidenceInterpretation,
    IntradayBar,
    SessionAnalysisState,
    SessionAnalysisStatus,
    SessionAnalysisInput,
    SessionDataMode,
    SessionSourceState,
    SessionEvidence,
)
from app.intelligence.session_narrative import (
    NarrativeClaim,
    NarrativeAvailability,
    ProductionSessionDataAdapter,
    SessionNarrativeBuilder,
    SessionNarrativeQuery,
    SessionNarrative,
    SessionNarrativeService,
)


NY = ZoneInfo("America/New_York")
SESSION_DATE = date(2026, 7, 22)


def dt(hour: int, minute: int) -> datetime:
    return datetime(2026, 7, 22, hour, minute, tzinfo=NY)


class ProductionAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = ProductionSessionDataAdapter()
        self.as_of = datetime(2026, 7, 22, 20, 5, tzinfo=timezone.utc)

    def test_production_adapter_reports_daily_only_without_synthesizing_intraday(self) -> None:
        result = self.adapter.availability(
            symbol="SPY",
            daily_history_available=True,
            provider="polygon",
            as_of=self.as_of,
        )

        self.assertEqual(result.data_mode, SessionDataMode.DAILY_ONLY)
        self.assertEqual(result.narrative_availability, NarrativeAvailability.DAILY_ONLY)
        self.assertFalse(result.intraday_supported)
        self.assertFalse(result.test_data_detected)
        narrative = SessionNarrativeBuilder().from_availability(result)
        self.assertEqual(narrative.claims, ())
        self.assertEqual(narrative.evidence, ())
        self.assertIn("not relabeled", " ".join(narrative.caveats))

    def test_get_ready_query_result_composes_status_narrative_and_provenance(self) -> None:
        query = SessionNarrativeQuery(
            symbol="SPY",
            interval=BarInterval.FIVE_MINUTES,
            requested_session_date=date(2026, 7, 21),
            as_of=self.as_of,
        )

        result = self.adapter.query(
            query,
            daily_history_available=True,
            provider="polygon",
            latest_daily_session=date(2026, 7, 21),
            source_id="polygon-daily-cache",
        )

        self.assertEqual(result.status, SessionAnalysisStatus.DAILY_ONLY)
        self.assertEqual(result.availability, NarrativeAvailability.DAILY_ONLY)
        self.assertEqual(result.data_mode, SessionDataMode.DAILY_ONLY)
        self.assertEqual(result.as_of, self.as_of)
        self.assertEqual(result.latest_daily_session, date(2026, 7, 21))
        self.assertEqual(result.provider, "polygon")
        self.assertEqual(result.provenance.dataset, "daily_history")
        self.assertEqual(result.provenance.source_id, "polygon-daily-cache")
        self.assertFalse(result.provenance.intraday_supported)
        self.assertEqual(result.narrative.claims, ())
        self.assertIn("provenance context only", " ".join(result.limitations))
        self.assertEqual(
            set(result.model_dump(mode="json")),
            {
                "query",
                "status",
                "availability",
                "provider",
                "data_mode",
                "as_of",
                "latest_daily_session",
                "narrative",
                "limitations",
                "provenance",
            },
        )

    def test_mock_provider_is_unavailable_and_never_live(self) -> None:
        result = self.adapter.availability(
            symbol="SPY",
            daily_history_available=True,
            provider="mock",
            as_of=self.as_of,
        )

        self.assertEqual(result.data_mode, SessionDataMode.UNAVAILABLE)
        self.assertEqual(result.narrative_availability, NarrativeAvailability.UNAVAILABLE)
        self.assertTrue(result.test_data_detected)
        self.assertFalse(result.intraday_supported)

        response = self.adapter.query(
            SessionNarrativeQuery(
                symbol="SPY",
                interval=BarInterval.FIVE_MINUTES,
                as_of=self.as_of,
            ),
            daily_history_available=True,
            provider="mock",
            latest_daily_session=date(2026, 7, 21),
            source_id="must-not-leak-as-live",
        )
        self.assertEqual(response.status, SessionAnalysisStatus.UNAVAILABLE)
        self.assertEqual(response.provenance.dataset, "unavailable")
        self.assertIsNone(response.provenance.latest_daily_session)
        self.assertIsNone(response.provenance.source_id)
        self.assertTrue(response.provenance.test_data_detected)

    def test_no_source_is_unavailable(self) -> None:
        result = self.adapter.availability(
            symbol="SPY",
            daily_history_available=False,
            provider=None,
            as_of=self.as_of,
        )

        self.assertEqual(result.data_mode, SessionDataMode.UNAVAILABLE)
        self.assertEqual(result.narrative_availability, NarrativeAvailability.UNAVAILABLE)


class NarrativeLanguageTests(unittest.TestCase):
    def test_service_preserves_evidence_and_uses_explicit_noncausal_language(self) -> None:
        bars: list[IntradayBar] = []
        for index in range(6):
            opening = 100.0 + index * 0.1
            bars.append(
                IntradayBar(
                    timestamp=dt(9, 30) + timedelta(minutes=index * 5),
                    open=opening,
                    high=opening + 0.12,
                    low=opening - 0.02,
                    close=opening + 0.10,
                    volume=1_000,
                    aggregate_vwap=opening + 0.05,
                )
            )
        event = CatalystEvent(
            event_id="wire-event",
            occurred_at=dt(9, 42),
            category=CatalystCategory.COMPANY_NEWS,
            headline="Company update",
            source_id="wire",
        )
        observed = dt(10, 0)
        value = SessionAnalysisInput(
            symbol="TEST",
            session_date=SESSION_DATE,
            interval=BarInterval.FIVE_MINUTES,
            data_mode=SessionDataMode.INTRADAY_5M,
            bars=tuple(bars),
            prior_close=99.5,
            catalysts=(event,),
            provider="fixture",
            source_id="session-fixture",
            source_state=SessionSourceState.TEST,
            generated_at=observed,
            observed_at=observed,
            now=observed + timedelta(minutes=1),
            test_data=True,
        )

        envelope = SessionNarrativeService().analyze(value)
        narrative = envelope.narrative

        self.assertEqual(narrative.availability, NarrativeAvailability.PARTIAL)
        self.assertEqual(
            {item.evidence_id for item in narrative.evidence},
            {evidence_id for claim in narrative.claims for evidence_id in claim.evidence_ids},
        )
        self.assertTrue(all(claim.observed_relationship_only for claim in narrative.claims))
        self.assertTrue(all(not claim.causal for claim in narrative.claims))
        catalyst_claims = [
            claim for claim in narrative.claims if "catalyst event" in claim.text.casefold()
        ]
        self.assertEqual(len(catalyst_claims), 1)
        self.assertIn("does not establish causality", catalyst_claims[0].text)
        self.assertIn("does not assert", narrative.causality_disclosure)
        self.assertEqual(narrative.confidence, "limited")

    def test_available_and_partial_claims_require_nested_evidence_lineage(self) -> None:
        evidence = SessionEvidence(
            evidence_id="session:evidence-1",
            entity="TEST",
            metric="extended_phase",
            value="observed",
            statement="Two finalized premarket bars were observed.",
            interpretation=EvidenceInterpretation.OBSERVED_FACT,
            source_id="fixture",
        )
        with self.assertRaises(ValidationError):
            NarrativeClaim(
                claim_id="claim:empty",
                text="Unsupported claim",
                evidence_ids=(),
            )
        with self.assertRaisesRegex(ValidationError, "absent from narrative.evidence"):
            SessionNarrative(
                symbol="TEST",
                session_date=SESSION_DATE,
                availability=NarrativeAvailability.PARTIAL,
                analysis_state=SessionAnalysisState.PREMARKET_ONLY,
                data_mode=SessionDataMode.INTRADAY_5M,
                headline="Premarket observations",
                claims=(
                    NarrativeClaim(
                        claim_id="claim:missing",
                        text="Two finalized premarket bars were observed.",
                        evidence_ids=("session:missing",),
                    ),
                ),
                evidence=(evidence,),
                freshness=SessionSourceState.TEST,
                caveats=("Premarket only.",),
            )

        narrative = SessionNarrative(
            symbol="TEST",
            session_date=SESSION_DATE,
            availability=NarrativeAvailability.PARTIAL,
            analysis_state=SessionAnalysisState.PREMARKET_ONLY,
            data_mode=SessionDataMode.INTRADAY_5M,
            headline="Premarket observations",
            claims=(
                NarrativeClaim(
                    claim_id="claim:present",
                    text=evidence.statement,
                    evidence_ids=(evidence.evidence_id,),
                ),
            ),
            evidence=(evidence,),
            freshness=SessionSourceState.TEST,
            caveats=("Premarket only.",),
        )
        self.assertEqual(narrative.claims[0].evidence_ids, (evidence.evidence_id,))

    def test_premarket_only_narrative_preserves_state_and_complete_claim_lineage(self) -> None:
        bars = (
            IntradayBar(
                timestamp=dt(8, 0),
                open=100.0,
                high=100.2,
                low=99.9,
                close=100.1,
                volume=1_000,
                aggregate_vwap=100.05,
            ),
            IntradayBar(
                timestamp=dt(8, 5),
                open=100.1,
                high=100.3,
                low=100.0,
                close=100.2,
                volume=1_000,
                aggregate_vwap=100.15,
            ),
        )
        observed = dt(8, 10)
        envelope = SessionNarrativeService().analyze(
            SessionAnalysisInput(
                symbol="TEST",
                session_date=SESSION_DATE,
                interval=BarInterval.FIVE_MINUTES,
                data_mode=SessionDataMode.INTRADAY_5M,
                bars=bars,
                provider="fixture",
                source_id="premarket-fixture",
                source_state=SessionSourceState.TEST,
                generated_at=observed,
                observed_at=observed,
                now=observed + timedelta(minutes=1),
                test_data=True,
            )
        )

        self.assertEqual(envelope.analysis.analysis_state, SessionAnalysisState.PREMARKET_ONLY)
        self.assertEqual(envelope.narrative.analysis_state, SessionAnalysisState.PREMARKET_ONLY)
        self.assertIn("premarket-only", envelope.narrative.headline)
        nested_ids = {item.evidence_id for item in envelope.narrative.evidence}
        self.assertTrue(envelope.narrative.claims)
        self.assertTrue(
            all(set(claim.evidence_ids).issubset(nested_ids) for claim in envelope.narrative.claims)
        )

    def test_manifest_declares_fail_closed_production_modes_and_shared_engines(self) -> None:
        manifest_path = (
            Path(__file__).resolve().parents[2]
            / "app"
            / "intelligence"
            / "session_narrative"
            / "session_manifest.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(manifest["calendar_boundary"]["timezone"], "America/New_York")
        self.assertEqual(manifest["production_adapter"]["current_intraday_source"], "unavailable")
        self.assertFalse(manifest["production_adapter"]["daily_to_intraday_resampling"])
        self.assertFalse(manifest["production_adapter"]["mock_as_live"])
        self.assertFalse(manifest["language_policy"]["causality_claims"])
        self.assertEqual(len(manifest["shared_stage75_engines"]), 4)
        self.assertEqual(
            manifest["registered_api_routes"],
            [
                "GET /intelligence/session/market",
                "GET /intelligence/session/{symbol}",
            ],
        )
        self.assertIn("turning_points", manifest["analytics"])


if __name__ == "__main__":
    unittest.main()
