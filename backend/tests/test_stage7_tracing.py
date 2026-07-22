from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.copilot.contracts import CopilotStreamEventType
from app.copilot.entities import EntityResolution
from app.copilot.intent import CopilotIntentClassifier
from app.copilot.orchestrator import InstitutionalCopilotOrchestrator
from app.copilot.sessions import CopilotSessionStore
from app.copilot.tracing import (
    CopilotTraceRecorder,
    load_development_trace,
    redact_trace_text,
    sanitize_trace_value,
)


class _EmptyResolver:
    def resolve(self, message: str, *, screen_context=None, active_entities=()):
        del message, screen_context, active_entities
        return EntityResolution()


class _FailingTraceRecorder:
    enabled = True

    def record(self, **kwargs):
        del kwargs
        raise OSError("trace disk unavailable")


class _ExplodingCollector:
    def collect(self, _context):
        raise RuntimeError("deterministic trace failure")


class Stage7DevelopmentTraceTests(unittest.TestCase):
    @staticmethod
    def orchestrator(recorder) -> InstitutionalCopilotOrchestrator:
        return InstitutionalCopilotOrchestrator(
            classifier=CopilotIntentClassifier(resolver=_EmptyResolver()),
            session_store=CopilotSessionStore(),
            trace_recorder=recorder,
        )

    def test_opt_in_trace_contains_diagnostics_and_no_model_cost_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            recorder = CopilotTraceRecorder(directory, enabled=True)
            response = self.orchestrator(recorder).answer(
                message="Where is Fear & Greed?",
                request_id="trace-navigation",
                thread_id="trace-navigation-thread",
            )
            trace = load_development_trace("trace-navigation", directory=directory)

            self.assertEqual(trace.request_id, response.request_id)
            self.assertEqual(trace.normalized_intent, "APP_NAVIGATION")
            self.assertEqual(trace.selected_agents, ["navigation"])
            self.assertEqual(trace.model_calls, 0)
            self.assertIsNone(trace.token_usage)
            self.assertIsNone(trace.estimated_cost)
            self.assertEqual(trace.final_status, "complete")
            self.assertTrue(trace.deep_links)
            self.assertEqual(trace.rules_triggered, [])
            self.assertTrue(trace.validation_checks_run)
            self.assertFalse(trace.cache_metrics["cacheTelemetryAvailable"])
            self.assertIsNone(trace.cache_metrics["cacheHitRate"])
            self.assertNotIn("observedCacheHitRate", trace.cache_metrics)
            self.assertEqual(trace.agent_results[0]["agent"], "navigation")
            self.assertEqual(trace.final_response["requestId"], "trace-navigation")
            self.assertGreaterEqual(trace.total_latency_ms, 0)
            self.assertTrue(Path(directory, "trace-navigation.json").is_file())

    def test_stream_trace_records_time_to_first_structured_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            recorder = CopilotTraceRecorder(directory, enabled=True)
            events = list(
                self.orchestrator(recorder).iter_stream_events(
                    message="Open the breadth screen.",
                    request_id="trace-stream",
                    thread_id="trace-stream-thread",
                )
            )
            self.assertEqual(events[-1].type, CopilotStreamEventType.COMPLETE)
            trace = load_development_trace("trace-stream", directory=directory)
            self.assertIsNotNone(trace.time_to_first_stream_event_ms)
            self.assertGreaterEqual(trace.time_to_first_stream_event_ms or 0, 0)

    def test_trace_redacts_secrets_and_sensitive_keys(self) -> None:
        raw = (
            "api_key=sk-THISMUSTNOTAPPEAR123456 and Bearer abcdefghijklmnop; "
            "email person@example.com; phone +1 (212) 555-0199; account ID ACCT-92831; saved NVDA"
        )
        cleaned = redact_trace_text(raw, private_terms={"NVDA"})
        payload = sanitize_trace_value(
            {
                "authorization": "Bearer abcdefghijklmnop",
                "nested": {"password": "do-not-store", "safe": raw},
            }
        )
        serialized = str(payload)
        self.assertNotIn("THISMUSTNOTAPPEAR", cleaned)
        self.assertNotIn("person@example.com", cleaned)
        self.assertNotIn("555-0199", cleaned)
        self.assertNotIn("ACCT-92831", cleaned)
        self.assertNotIn("NVDA", cleaned)
        self.assertIn(
            "2026-07-22T04:00:00Z",
            redact_trace_text("2026-07-22T04:00:00Z"),
        )
        self.assertNotIn("abcdefghijklmnop", serialized)
        self.assertNotIn("do-not-store", serialized)
        self.assertIn("[REDACTED]", serialized)

    def test_device_local_membership_is_pseudonymized_in_full_trace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            recorder = CopilotTraceRecorder(directory, enabled=True)
            self.orchestrator(recorder).answer(
                message="Which saved stocks need attention?",
                context={"savedSymbols": ["ARM"]},
                request_id="trace-private-membership",
                thread_id="trace-private-membership-thread",
            )
            trace = load_development_trace("trace-private-membership", directory=directory)
            serialized = json.dumps(trace.model_dump(mode="json", by_alias=True))
            self.assertNotIn('"ARM"', serialized)
            self.assertIn("[PRIVATE:", serialized)

    def test_pipeline_exception_produces_request_id_trace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            recorder = CopilotTraceRecorder(directory, enabled=True)
            orchestrator = InstitutionalCopilotOrchestrator(
                classifier=CopilotIntentClassifier(resolver=_EmptyResolver()),
                collector=_ExplodingCollector(),
                session_store=CopilotSessionStore(),
                trace_recorder=recorder,
            )
            with self.assertRaises(RuntimeError):
                orchestrator.answer(
                    message="Where is Fear & Greed?",
                    request_id="trace-pipeline-exception",
                    thread_id="trace-pipeline-exception-thread",
                )
            trace = load_development_trace("trace-pipeline-exception", directory=directory)
            self.assertEqual(trace.final_status, "failed")
            self.assertEqual(trace.failure_category, "RuntimeError")
            self.assertIn("pipeline_exception:RuntimeError", trace.fallbacks)

    def test_trace_write_failure_never_breaks_copilot_response(self) -> None:
        with self.assertLogs("app.copilot.orchestrator", level="WARNING") as logs:
            response = self.orchestrator(_FailingTraceRecorder()).answer(
                message="Where is Fear & Greed?",
                request_id="trace-failure-safe",
                thread_id="trace-failure-safe-thread",
            )
        self.assertEqual(response.status.value, "complete")
        self.assertTrue(any("institutional_copilot_trace_failed" in value for value in logs.output))


if __name__ == "__main__":
    unittest.main()
