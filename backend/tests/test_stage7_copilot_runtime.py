from __future__ import annotations

import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.copilot import router
from app.copilot.agents import CopilotAgentRegistry
from app.copilot.collector import CopilotEvidenceCollector
from app.copilot.contracts import CopilotIntentType
from app.copilot.orchestrator import (
    InstitutionalCopilotOrchestrator,
    institutional_copilot_enabled,
)
from app.copilot.sessions import CopilotSessionStore
from app.copilot.sources import TrustedCopilotSources


class _HermeticArmSnapshot:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self.snapshot_id = "stage7-arm-session-fixture"
        self.source_state = "cached"
        self.status = "complete"
        self.published_at = now.isoformat()
        self.latest_history_timestamp = now.isoformat()
        self.latest_history_date = now.date().isoformat()
        self.expires_at = (now + timedelta(hours=1)).isoformat()
        self.coverage_ratio = 1.0
        self.warnings: list[str] = []
        self.missing_dependencies: list[str] = []
        self.test_data = False
        self.mock_data = False
        self._sections = {
            "rating": {
                "rating": "B",
                "overall_score": 78,
                "risk_level": "Moderate",
                "status": "Setup Forming",
                "explanation": "ARM has a monitored setup with explicit confirmation and risk levels.",
                "warnings": [],
            },
            "technical": {
                "current_price": 120.0,
                "return_20d": 4.5,
                "rsi_14": 58.0,
                "ema_20": 117.0,
                "ema_50": 110.0,
            },
            "support_resistance": {
                "current_price": 120.0,
                "breakout_level": 125.0,
                "stop_reference": 112.0,
            },
        }

    def section_payload(self, name: str):
        return self._sections.get(name)


class _HermeticArmSources(TrustedCopilotSources):
    """No ambient provider, cache, report, or developer-database dependency."""

    def __init__(self) -> None:
        self._arm = _HermeticArmSnapshot()

    def market_snapshot(self):
        return None

    def breadth_snapshot(self):
        return None

    def stock_snapshot(self, symbol: str):
        return self._arm if symbol.upper() == "ARM" else None

    def latest_report_document(self):
        return None


class _HermeticAttentionSources(_HermeticArmSources):
    """Three saved symbols with two deterministic caution statuses."""

    def __init__(self) -> None:
        arm = _HermeticArmSnapshot()
        aapl = _HermeticArmSnapshot()
        aapl.snapshot_id = "stage7-aapl-attention-fixture"
        aapl._sections["rating"] = {
            "rating": "D",
            "overall_score": 58,
            "risk_level": "Elevated",
            "status": "Avoid / Poor Setup",
            "explanation": "AAPL has a poor setup in the deterministic snapshot.",
            "warnings": [],
        }
        msft = _HermeticArmSnapshot()
        msft.snapshot_id = "stage7-msft-attention-fixture"
        msft._sections["rating"] = {
            "rating": "C",
            "overall_score": 63,
            "risk_level": "Low",
            "status": "Weak / Needs Confirmation",
            "explanation": "MSFT remains weak and needs confirmation in the deterministic snapshot.",
            "warnings": [],
        }
        self._snapshots = {"AAPL": aapl, "ARM": arm, "MSFT": msft}
        self.requested_symbols: list[str] = []

    def stock_snapshot(self, symbol: str):
        normalized = symbol.upper()
        self.requested_symbols.append(normalized)
        return self._snapshots.get(normalized)

    def watchlist_membership(self):
        raise AssertionError("Explicit device-local membership must not call a backend membership source.")


def _arm_orchestrator(store: CopilotSessionStore) -> InstitutionalCopilotOrchestrator:
    registry = CopilotAgentRegistry(sources=_HermeticArmSources())
    collector = CopilotEvidenceCollector(registry=registry, maximum_workers=1)
    return InstitutionalCopilotOrchestrator(session_store=store, collector=collector)


class Stage7CopilotRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = InstitutionalCopilotOrchestrator()

    def test_operational_fields_and_structured_log_are_safe(self) -> None:
        with self.assertLogs("app.copilot.orchestrator", level="INFO") as captured:
            response = self.orchestrator.answer(
                message="Where is Fear & Greed?",
                request_id="runtime-ops-request",
                thread_id="runtime-ops-thread",
            )
        payload = response.model_dump(mode="json", by_alias=True)
        self.assertEqual(payload["requestId"], "runtime-ops-request")
        self.assertEqual(payload["retryCount"], 0)
        self.assertEqual(payload["failureCategories"], [])
        self.assertIn("navigation", payload["agentTimingsMs"])
        self.assertEqual(payload["actions"][0]["destinationId"], "fear_greed")
        record = captured.records[-1]
        event = record.copilot_event
        self.assertEqual(event["request_id"], "runtime-ops-request")
        self.assertEqual(event["evidence_count"], 0)
        self.assertNotIn("question", event)
        self.assertNotIn("message", event)

    def test_stream_preserves_client_request_identity(self) -> None:
        events = list(
            self.orchestrator.iter_stream_events(
                message="Where is Fear & Greed?",
                request_id="runtime-stream-request",
                thread_id="runtime-stream-thread",
            )
        )
        self.assertEqual(events[0].type.value, "start")
        self.assertEqual(events[-1].type.value, "complete")
        self.assertEqual({item.request_id for item in events}, {"runtime-stream-request"})
        self.assertEqual(len({item.event_id for item in events}), len(events))
        self.assertEqual(events[-1].payload["response"]["requestId"], "runtime-stream-request")

    def test_http_json_and_ndjson_routes_and_feature_flag(self) -> None:
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        request = {"requestId": "runtime-http-request", "message": "Where is Fear & Greed?"}
        with patch.dict(os.environ, {"COPILOT_V1_ENABLED": "true"}):
            response = client.post("/copilot/chat", json=request)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["requestId"], "runtime-http-request")
            with client.stream("POST", "/copilot/chat/stream", json=request) as streamed:
                rows = [json.loads(line) for line in streamed.iter_lines() if line]
            self.assertTrue(streamed.headers["content-type"].startswith("application/x-ndjson"))
            self.assertEqual(rows[-1]["payload"]["response"]["requestId"], "runtime-http-request")
        with patch.dict(os.environ, {"COPILOT_V1_ENABLED": "false"}):
            self.assertFalse(institutional_copilot_enabled())
            disabled = client.post("/copilot/chat", json=request)
            self.assertEqual(disabled.status_code, 503)

    def test_client_market_values_do_not_cross_the_trust_boundary(self) -> None:
        sentinel = "987654321.123456"
        response = self.orchestrator.answer(
            message="What is the market condition?",
            context={
                "screenType": "home",
                "sourceState": "live",
                "marketHealth": {"score": sentinel, "status": "Guaranteed Strong Buy"},
                "api_key": "sk-THISMUSTNOTAPPEAR123456789",
            },
        )
        serialized = response.model_dump_json(by_alias=True)
        self.assertNotIn(sentinel, serialized)
        self.assertNotIn("Guaranteed Strong Buy", serialized)
        self.assertNotIn("THISMUSTNOTAPPEAR", serialized)
        self.assertTrue(response.evidence)
        self.assertTrue(all(item.source.dataset != "client" for item in response.evidence))

    def test_report_challenge_conditions_are_cited(self) -> None:
        for prompt in (
            "Why was Cybersecurity selected as Research Focus?",
            "What would invalidate today's market thesis?",
            "What is the bear case in today's report?",
        ):
            with self.subTest(prompt=prompt):
                response = self.orchestrator.answer(message=prompt)
                known = {item.evidence_id for item in response.evidence}
                opposing = response.reasoning.contradictory_factors
                confirmation = response.reasoning.confirmation_conditions
                invalidation = response.reasoning.invalidation_conditions
                self.assertTrue(opposing)
                self.assertTrue(invalidation)
                self.assertTrue(confirmation)
                for factor in [*opposing, *confirmation, *invalidation]:
                    self.assertTrue(factor.evidence_ids)
                    self.assertTrue(set(factor.evidence_ids) <= known)
                self.assertEqual(response.validation.status.value, "passed")

    def test_sequential_stock_follow_ups_preserve_entity_and_base_intent(self) -> None:
        store = CopilotSessionStore()
        orchestrator = _arm_orchestrator(store)
        thread_id = "runtime-arm-follow-up-thread"
        context = {"screenType": "stock", "symbol": "ARM"}

        first = orchestrator.answer(
            message="Should I buy ARM?",
            context=context,
            thread_id=thread_id,
        )
        why = orchestrator.answer(message="Why?", context=context, thread_id=thread_id)
        confirmation = orchestrator.answer(
            message="What confirms it?",
            context=context,
            thread_id=thread_id,
        )
        invalidation = orchestrator.answer(
            message="What invalidates it?",
            context=context,
            thread_id=thread_id,
        )

        self.assertEqual(first.intent.intent.value, "STOCK_DECISION_SUPPORT")
        self.assertEqual(why.intent.intent.value, "FOLLOW_UP")
        for response in (confirmation, invalidation):
            self.assertEqual(response.intent.intent.value, "FOLLOW_UP")
            self.assertEqual(response.intent.ticker_symbols, ["ARM"])
            self.assertEqual(
                {step.agent.value for step in response.plan.ordered_steps},
                {"stock", "risk"},
            )
            known = {item.evidence_id for item in response.evidence}
            for factor in [
                *response.reasoning.confirmation_conditions,
                *response.reasoning.invalidation_conditions,
            ]:
                self.assertTrue(factor.evidence_ids)
                self.assertTrue(set(factor.evidence_ids) <= known)

        self.assertTrue(
            any("ARM confirmation level" in factor.statement for factor in confirmation.reasoning.confirmation_conditions)
        )
        self.assertTrue(
            any("ARM risk reference" in factor.statement for factor in invalidation.reasoning.invalidation_conditions)
        )
        compact = store.get(thread_id)
        self.assertIsNotNone(compact)
        assert compact is not None
        self.assertEqual(compact.active_intent.value, "STOCK_DECISION_SUPPORT")
        self.assertEqual(compact.latest_referenced_stock, "ARM")

    def test_cancel_retry_and_late_completion_cannot_poison_stock_context(self) -> None:
        store = CopilotSessionStore()
        orchestrator = _arm_orchestrator(store)
        thread_id = "runtime-arm-cancel-retry-thread"
        context = {"screenType": "stock", "symbol": "ARM"}

        orchestrator.answer(
            message="Should I buy ARM?",
            context=context,
            request_id="arm-seed",
            thread_id=thread_id,
        )
        delayed = orchestrator.iter_stream_events(
            message="Why?",
            context=context,
            request_id="arm-cancelled",
            thread_id=thread_id,
        )
        # Advance through classification/plan, then emulate a cancelled request
        # whose synchronous backend work finishes after the user's retry.
        self.assertEqual(next(delayed).type.value, "start")
        self.assertEqual(next(delayed).type.value, "intent")
        self.assertEqual(next(delayed).type.value, "plan")

        retry = orchestrator.answer(
            message="Why?",
            context=context,
            request_id="arm-retry",
            thread_id=thread_id,
        )
        retry_context = store.get(thread_id)
        self.assertIsNotNone(retry_context)
        assert retry_context is not None
        retry_revision = retry_context.updated_at
        self.assertEqual(retry.intent.ticker_symbols, ["ARM"])

        late_events = list(delayed)
        self.assertEqual(late_events[-1].type.value, "complete")
        after_late = store.get(thread_id)
        self.assertIsNotNone(after_late)
        assert after_late is not None
        self.assertEqual(after_late.updated_at, retry_revision)

        # Reproduce the pre-fix client payload: Retry completed with a
        # FOLLOW_UP activeIntent even though the analytical base is ARM stock
        # decision support.  Server state must remain authoritative.
        poisoned = retry_context.model_copy(
            update={
                "active_intent": CopilotIntentType.FOLLOW_UP,
                "updated_at": (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat(),
            },
            deep=True,
        )
        confirmation = orchestrator.answer(
            message="What confirms it?",
            context=context,
            request_id="arm-confirmation",
            thread_id=thread_id,
            session_context=poisoned,
        )

        self.assertEqual(confirmation.intent.intent.value, "FOLLOW_UP")
        self.assertEqual(confirmation.intent.ticker_symbols, ["ARM"])
        self.assertEqual(
            {step.agent.value for step in confirmation.plan.ordered_steps},
            {"stock", "risk"},
        )
        self.assertTrue(
            any("ARM confirmation level" in factor.statement for factor in confirmation.reasoning.confirmation_conditions)
        )
        compact = store.get(thread_id)
        self.assertIsNotNone(compact)
        assert compact is not None
        self.assertEqual(compact.active_intent.value, "STOCK_DECISION_SUPPORT")
        self.assertEqual(compact.latest_referenced_stock, "ARM")

    def test_hydrated_saved_membership_drives_watchlist_without_inventing_snapshots(self) -> None:
        orchestrator = _arm_orchestrator(CopilotSessionStore())
        saved = ["ARM", "MU", "SNDK", "NVDA", "MSFT", "AAPL"]
        response = orchestrator.answer(
            message="Which saved stock needs attention?",
            context={
                "screenType": "general",
                "savedSymbols": saved,
                # Rich rows can include API defaults and must not override the
                # authoritative hydrated identity list.
                "watchlist": {"items": [{"symbol": "NOTSAVED", "score": 100}]},
            },
            thread_id="runtime-saved-membership",
        )

        membership = {
            item.entity
            for item in response.evidence
            if item.category.value == "watchlist" and item.metric == "saved membership"
        }
        technical_entities = {
            item.entity for item in response.evidence if item.category.value == "technical"
        }
        self.assertEqual(membership, set(saved))
        self.assertNotIn("NOTSAVED", membership)
        self.assertEqual(technical_entities, {"ARM"})
        self.assertNotIn("There are no saved stocks", response.reasoning.direct_answer)
        self.assertIn("holdings were not inferred", response.reasoning.direct_answer)
        self.assertTrue(any("backend account scoping is not available" in item for item in response.warnings))
        self.assertIn("not inferred", response.reasoning.personalization_note or "")

    def test_watchlist_direct_answer_names_only_cited_attention_candidates(self) -> None:
        sources = _HermeticAttentionSources()
        registry = CopilotAgentRegistry(sources=sources)
        collector = CopilotEvidenceCollector(registry=registry, maximum_workers=1)
        orchestrator = InstitutionalCopilotOrchestrator(
            session_store=CopilotSessionStore(),
            collector=collector,
        )
        response = orchestrator.answer(
            message="Which saved stock needs attention?",
            context={
                "screenType": "general",
                "savedSymbols": ["AAPL", "ARM", "MSFT"],
            },
            thread_id="runtime-attention-candidates",
        )

        self.assertEqual(response.validation.status.value, "passed")
        self.assertFalse(response.validation.fallback_used)
        self.assertIn("AAPL and MSFT", response.reasoning.direct_answer)
        self.assertNotIn("ARM", response.reasoning.direct_answer)
        self.assertIn("unranked monitoring review", response.reasoning.direct_answer)
        self.assertIn("holdings were not inferred", response.reasoning.direct_answer)

        evidence_by_id = {item.evidence_id: item for item in response.evidence}
        attention_citations = {
            evidence_by_id[evidence_id].entity
            for factor in response.reasoning.key_risks
            for evidence_id in factor.evidence_ids
            if evidence_id in evidence_by_id
            and evidence_by_id[evidence_id].metric in {"setup status", "risk level"}
        }
        self.assertEqual(attention_citations, {"AAPL", "MSFT"})
        self.assertTrue(
            all(
                factor.evidence_ids
                and set(factor.evidence_ids) <= set(evidence_by_id)
                for factor in response.reasoning.key_risks
            )
        )
        self.assertEqual(sources.requested_symbols, ["AAPL", "ARM", "MSFT"])

    def test_explicit_empty_saved_membership_beats_rich_rows(self) -> None:
        orchestrator = _arm_orchestrator(CopilotSessionStore())
        response = orchestrator.answer(
            message="Which saved stock needs attention?",
            context={
                "screenType": "general",
                "savedSymbols": [],
                "watchlist": {"items": [{"symbol": "ARM", "score": 100}]},
            },
            thread_id="runtime-empty-membership",
        )

        self.assertEqual(response.reasoning.direct_answer, "There are no saved stocks to review.")
        self.assertFalse(response.evidence)
        self.assertFalse(response.reasoning.missing_evidence)
        self.assertFalse(any("Required watchlist evidence" in item for item in response.warnings))
        self.assertEqual(
            {step.agent.value for step in response.plan.ordered_steps},
            {"watchlist"},
        )

    def test_missing_saved_membership_is_unavailable_not_empty(self) -> None:
        orchestrator = _arm_orchestrator(CopilotSessionStore())
        response = orchestrator.answer(
            message="Which saved stock needs attention?",
            context={"screenType": "general"},
            thread_id="runtime-missing-membership",
        )

        self.assertNotIn("There are no saved stocks", response.reasoning.direct_answer)
        self.assertIn("insufficient validated evidence", response.reasoning.direct_answer.casefold())
        self.assertTrue(
            any("device-local" in item and "not supplied" in item for item in response.reasoning.missing_evidence)
        )
        self.assertFalse(response.evidence)


if __name__ == "__main__":
    unittest.main()
