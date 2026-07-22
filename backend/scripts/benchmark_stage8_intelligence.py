from __future__ import annotations

import argparse
import json
import socket
import statistics
import sys
import time
from contextlib import contextmanager
from datetime import date, datetime, time as wall_time, timedelta, timezone
from itertools import count
from pathlib import Path
from typing import Callable
from unittest.mock import patch
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.analysis_engines.news import NewsEntityMappingEngine
from app.analysis_engines.session import (
    BarInterval,
    IntradayBar,
    SessionAnalysisInput,
    SessionDataMode,
    SessionSourceState,
)
from app.copilot.entities import EntityResolution, ResolvedEntity
from app.copilot.agents import CopilotAgentRegistry
from app.copilot.collector import CopilotEvidenceCollector
from app.copilot.intent import CopilotIntentClassifier
from app.copilot.orchestrator import InstitutionalCopilotOrchestrator
from app.copilot.planner import CopilotPlanner
from app.copilot.sessions import CopilotSessionStore
from app.intelligence.news import (
    ExpectedDirection,
    MarketReactionObservation,
    NewsEventStatus,
    NewsEventType,
    NewsFreshnessState,
    NewsIntelligenceService,
    NewsQuery,
    NewsQueryMode,
    ReactionClassification,
    ReactionWindow,
    SourceQuality,
)
from app.intelligence.session_narrative import SessionNarrativeService
from app.providers.news import HermeticNewsProvider, NewsProviderItem
from app.securities.models import SecurityRecord
from main import app as api_app


DEFAULT_ITERATIONS = 250
FIXED_NOW = datetime(2026, 7, 22, 20, 5, tzinfo=timezone.utc)
NY = ZoneInfo("America/New_York")
SESSION_DATE = date(2026, 7, 22)


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * quantile)))
    return ordered[index]


def benchmark(callback: Callable[[], object], *, iterations: int) -> dict[str, float | int]:
    for _ in range(min(10, iterations)):
        callback()
    samples: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter_ns()
        callback()
        samples.append((time.perf_counter_ns() - started) / 1_000_000)
    return {
        "iterations": iterations,
        "mean_ms": round(statistics.fmean(samples), 6),
        "p50_ms": round(percentile(samples, 0.50), 6),
        "p95_ms": round(percentile(samples, 0.95), 6),
        "p99_ms": round(percentile(samples, 0.99), 6),
        "max_ms": round(max(samples), 6),
    }


def news_items() -> tuple[NewsProviderItem, ...]:
    items: list[NewsProviderItem] = []
    cluster_labels = (
        "Orion",
        "Lyra",
        "Draco",
        "Cygnus",
        "Hydra",
        "Vela",
        "Carina",
        "Pavo",
        "Volans",
        "Aquila",
    )
    for cluster_index in range(10):
        for source_index, source_identifier in enumerate(
            ("fixture-company-ir", "fixture-newswire")
        ):
            published_at = FIXED_NOW - timedelta(minutes=cluster_index + 10)
            items.append(
                NewsProviderItem(
                    provider_event_id=f"benchmark-{cluster_index}-{source_index}",
                    headline=f"NVIDIA {cluster_labels[cluster_index]} guidance",
                    summary="NVIDIA published a synthetic guidance update for an offline benchmark.",
                    source_identifier=source_identifier,
                    source_name=(
                        "Hermetic NVIDIA Investor Relations"
                        if source_index == 0
                        else "Hermetic Professional Newswire"
                    ),
                    source_url=(
                        f"https://{'ir' if source_index == 0 else 'wire'}.fixture.test/"
                        f"benchmark/{cluster_index}/{source_index}"
                    ),
                    published_at=published_at,
                    first_seen_at=published_at + timedelta(seconds=source_index),
                    structured_event_type=NewsEventType.GUIDANCE,
                    structured_symbols=("NVDA",),
                    structured_company_names=("NVIDIA Corporation",),
                    confirmed_facts=("The synthetic issuer updated guidance.",),
                    event_status=NewsEventStatus.CONFIRMED,
                    canonical_event_reference=f"benchmark-guidance-{cluster_index}",
                    expected_direction=ExpectedDirection.POSITIVE,
                    is_official_release=source_index == 0,
                )
            )
    return tuple(items)


def news_service() -> NewsIntelligenceService:
    security = SecurityRecord(
        security_id="sec-nvda",
        ticker="NVDA",
        company_name="NVIDIA Corporation",
        sector="Information Technology",
        sector_id="information_technology",
        industry="Semiconductors",
        index_memberships=("S&P 500", "Nasdaq 100"),
        effective_from="2026-01-01",
        source="stage8-hermetic-benchmark",
        source_timestamp="2026-07-01",
        verified_at="2026-07-01T00:00:00Z",
        metadata_version=1,
    )
    mapper = NewsEntityMappingEngine(
        security_resolver=lambda symbol: security if symbol == "NVDA" else None,
        theme_loader=lambda: [],
    )
    return NewsIntelligenceService(
        provider=HermeticNewsProvider(news_items(), clock=lambda: FIXED_NOW),
        mapper=mapper,
    )


def news_query() -> NewsQuery:
    return NewsQuery(
        mode=NewsQueryMode.SECURITY,
        as_of=FIXED_NOW,
        start_at=FIXED_NOW - timedelta(days=1),
        end_at=FIXED_NOW,
        entity_id="NVDA",
        symbols=("NVDA",),
        limit=20,
    )


def reaction_observations() -> tuple[MarketReactionObservation, ...]:
    return tuple(
        MarketReactionObservation(
            event_id=item.provider_event_id,
            entity_id="sec-nvda",
            symbol="NVDA",
            window=ReactionWindow.CLOSE_TO_CLOSE,
            window_start=FIXED_NOW - timedelta(days=1),
            window_end=FIXED_NOW,
            price_return=0.021,
            benchmark_return=0.004,
            volume_ratio=1.35,
            expected_direction=ExpectedDirection.POSITIVE,
            evidence_ids=(f"benchmark-price:{item.provider_event_id}",),
            source_id="stage8-recorded-daily-bars",
            source_quality=SourceQuality.HIGH_CONFIDENCE_SECONDARY,
            source_state=NewsFreshnessState.TEST,
        )
        for item in news_items()
    )


def session_input() -> SessionAnalysisInput:
    bars: list[IntradayBar] = []
    session_start = datetime.combine(SESSION_DATE, wall_time(9, 30), tzinfo=NY)
    for index in range(78):
        opening = 100.0 + index * 0.08
        closing = opening + 0.05
        bars.append(
            IntradayBar(
                timestamp=session_start + timedelta(minutes=index * 5),
                open=opening,
                high=closing + 0.03,
                low=opening - 0.03,
                close=closing,
                volume=100_000 + index * 500,
                aggregate_vwap=(opening + closing) / 2,
                transactions=1_000 + index,
                is_final=True,
            )
        )
    observed_at = datetime.combine(SESSION_DATE, wall_time(16, 1), tzinfo=NY)
    return SessionAnalysisInput(
        symbol="NVDA",
        session_date=SESSION_DATE,
        interval=BarInterval.FIVE_MINUTES,
        data_mode=SessionDataMode.INTRADAY_5M,
        bars=tuple(bars),
        prior_close=99.75,
        provider="stage8_hermetic_benchmark",
        source_id="stage8-recorded-session-benchmark",
        source_state=SessionSourceState.TEST,
        generated_at=observed_at,
        observed_at=observed_at,
        now=observed_at + timedelta(minutes=1),
        test_data=True,
    )


class BenchmarkEntityResolver:
    def resolve(self, message: str, *, screen_context=None, active_entities=()):
        del screen_context, active_entities
        result = EntityResolution()
        if "NVDA" in message.upper():
            result.entities.append(
                ResolvedEntity(
                    "stock",
                    "NVDA",
                    "NVIDIA Corporation",
                    symbol="NVDA",
                    source="stage8-hermetic-benchmark",
                )
            )
        return result


class BenchmarkCopilotSources:
    """Hermetic Stage 8 source facade used by the full Copilot benchmark."""

    def __init__(
        self,
        news: NewsIntelligenceService,
        query: NewsQuery,
        reactions: tuple[MarketReactionObservation, ...],
    ) -> None:
        self.news = news
        self.query = query
        self.reactions = reactions

    def news_intelligence(self, intent, *, watchlist_symbols=(), as_of=None):
        del intent, watchlist_symbols, as_of
        return self.news.query(
            self.query,
            reaction_observations=self.reactions,
        )


class HermeticCallAudit:
    """Count and block external calls while benchmark paths execute."""

    def __init__(self) -> None:
        self.network_calls = 0
        self.model_calls = 0

    def _network_call(self, *args, **kwargs):
        del args, kwargs
        self.network_calls += 1
        raise AssertionError("stage8_benchmark_external_network_call_blocked")

    def _model_call(self, *args, **kwargs):
        del args, kwargs
        self.model_calls += 1
        raise AssertionError("stage8_benchmark_model_call_blocked")

    @contextmanager
    def enforce(self):
        with (
            patch.object(socket.socket, "connect", new=self._network_call),
            patch.object(socket, "create_connection", new=self._network_call),
            patch(
                "app.services.openai_client.generate_structured_chat_response",
                new=self._model_call,
            ),
            patch(
                "app.services.openai_client.generate_structured_summary",
                new=self._model_call,
            ),
        ):
            yield


def build_payload(*, iterations: int) -> dict[str, object]:
    iterations = max(1, iterations)
    news = news_service()
    query = news_query()
    reactions = reaction_observations()
    session = SessionNarrativeService()
    session_value = session_input()
    classifier = CopilotIntentClassifier(resolver=BenchmarkEntityResolver())
    planner = CopilotPlanner()
    registry = CopilotAgentRegistry(
        sources=BenchmarkCopilotSources(news, query, reactions)
    )
    collector = CopilotEvidenceCollector(registry=registry, maximum_workers=1)
    orchestrator = InstitutionalCopilotOrchestrator(
        classifier=classifier,
        planner=planner,
        collector=collector,
        session_store=CopilotSessionStore(maximum_sessions=max(500, iterations + 20)),
    )
    request_sequence = count()

    def copilot_answer():
        sequence = next(request_sequence)
        return orchestrator.answer(
            message="What news affected NVDA today?",
            request_id=f"stage8-benchmark-{sequence}",
            thread_id=f"stage8-benchmark-thread-{sequence}",
        )

    audit = HermeticCallAudit()

    def run_news():
        return news.query(query, reaction_observations=reactions)

    with audit.enforce():
        news_result = run_news()
        session_result = session.analyze(session_value)
        route_intent = classifier.classify("What news affected NVDA today?")
        route_plan = planner.build(route_intent)
        copilot_result = copilot_answer()
        api_client = TestClient(api_app)
        news_endpoint_response = api_client.get(
            "/intelligence/news/security/NVDA",
            params={"as_of": FIXED_NOW.isoformat()},
        )
        session_endpoint_response = api_client.get(
            "/intelligence/session/NVDA",
            params={"as_of": FIXED_NOW.isoformat()},
        )

        news_latency = benchmark(run_news, iterations=iterations)
        session_latency = benchmark(
            lambda: session.analyze(session_value), iterations=iterations
        )
        routing_latency = benchmark(
            lambda: planner.build(classifier.classify("What news affected NVDA today?")),
            iterations=iterations,
        )
        copilot_latency = benchmark(copilot_answer, iterations=iterations)
        news_endpoint_latency = benchmark(
            lambda: api_client.get(
                "/intelligence/news/security/NVDA",
                params={"as_of": FIXED_NOW.isoformat()},
            ),
            iterations=iterations,
        )
        session_endpoint_latency = benchmark(
            lambda: api_client.get(
                "/intelligence/session/NVDA",
                params={"as_of": FIXED_NOW.isoformat()},
            ),
            iterations=iterations,
        )
        api_client.close()

    news_threshold_ms = 250.0
    session_threshold_ms = 250.0
    routing_threshold_ms = 50.0
    copilot_threshold_ms = 500.0
    endpoint_threshold_ms = 500.0
    returned_evidence_ids = {item.evidence_id for item in news_result.evidence}
    threshold_results = {
        "news_pipeline_p95_under_250ms": float(news_latency["p95_ms"]) < news_threshold_ms,
        "session_pipeline_p95_under_250ms": float(session_latency["p95_ms"])
        < session_threshold_ms,
        "copilot_routing_p95_under_50ms": float(routing_latency["p95_ms"])
        < routing_threshold_ms,
        "copilot_full_pipeline_p95_under_500ms": float(copilot_latency["p95_ms"])
        < copilot_threshold_ms,
        "news_endpoint_p95_under_500ms": float(news_endpoint_latency["p95_ms"])
        < endpoint_threshold_ms,
        "session_endpoint_p95_under_500ms": float(session_endpoint_latency["p95_ms"])
        < endpoint_threshold_ms,
        "endpoints_return_structured_200": news_endpoint_response.status_code == 200
        and session_endpoint_response.status_code == 200,
        "duplicate_reduction_at_least_40_percent": news_result.metrics.duplicate_reduction_ratio
        >= 0.4,
        "canonical_events_nonzero": len(news_result.events) > 0,
        "mapped_canonical_events_complete": len(news_result.events) > 0 and all(
            any(mapping.symbol == "NVDA" for mapping in event.affected_entities)
            for event in news_result.events
        ),
        "mapping_evidence_lineage_complete": len(news_result.events) > 0 and all(
            mapping.evidence_id in returned_evidence_ids
            for event in news_result.events
            for mapping in event.affected_entities
        ),
        "materiality_contributions_complete": len(news_result.events) > 0 and all(
            event.materiality is not None and bool(event.materiality.contributions)
            for event in news_result.events
        ),
        "reaction_evidence_lineage_complete": len(news_result.events) > 0 and all(
            event.reaction is not None
            and event.reaction.classification
            is not ReactionClassification.INSUFFICIENT_DATA
            and bool(event.reaction.evidence_ids)
            and set(event.reaction.evidence_ids).issubset(returned_evidence_ids)
            for event in news_result.events
        ),
        "session_regular_coverage_complete": session_result.analysis.quality.regular_session_coverage
        == 1.0,
    }
    return {
        "schema_version": "stage8-context-intelligence-performance-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(threshold_results.values()) else "FAIL",
        "hermetic": True,
        "network_calls": audit.network_calls,
        "model_calls": audit.model_calls,
        "external_call_audit": {
            "network_connect_intercepted": audit.network_calls,
            "model_gateway_calls_intercepted": audit.model_calls,
            "policy": "all attempted external calls fail the benchmark",
        },
        "news_pipeline": {
            "latency": news_latency,
            "component_latency_ms": {
                "provider_fetch": news_result.metrics.provider_fetch_ms,
                "normalization": news_result.metrics.normalization_ms,
                "clustering": news_result.metrics.clustering_ms,
                "mapping": news_result.metrics.mapping_ms,
                "materiality": news_result.metrics.materiality_ms,
                "reaction_analysis": news_result.metrics.reaction_ms,
                "materiality_and_reaction_total": news_result.metrics.materiality_reaction_ms,
                "full_service": news_result.metrics.total_ms,
            },
            "provider_event_count": news_result.metrics.provider_event_count,
            "normalized_event_count": news_result.metrics.normalized_event_count,
            "cluster_count": news_result.metrics.cluster_count,
            "returned_event_count": news_result.metrics.returned_event_count,
            "duplicate_reduction_ratio": news_result.metrics.duplicate_reduction_ratio,
            "mapped_canonical_event_ratio": round(
                sum(
                    any(mapping.symbol == "NVDA" for mapping in event.affected_entities)
                    for event in news_result.events
                )
                / len(news_result.events),
                6,
            ),
            "mapping_evidence_lineage_ratio": round(
                sum(
                    mapping.evidence_id in returned_evidence_ids
                    for event in news_result.events
                    for mapping in event.affected_entities
                )
                / max(
                    1,
                    sum(
                        len(event.affected_entities)
                        for event in news_result.events
                    ),
                ),
                6,
            ),
            "materiality_contribution_count": sum(
                len(event.materiality.contributions) if event.materiality else 0
                for event in news_result.events
            ),
            "reaction_evidence_count": sum(
                len(event.reaction.evidence_ids) if event.reaction else 0
                for event in news_result.events
            ),
            "provider_mode": news_result.provider.mode.value,
            "freshness": news_result.freshness.state.value,
        },
        "session_pipeline": {
            "latency": session_latency,
            "input_bar_count": len(session_value.bars),
            "status": session_result.analysis.status.value,
            "regular_session_coverage": session_result.analysis.quality.regular_session_coverage,
            "evidence_count": len(session_result.analysis.evidence),
            "freshness": session_result.analysis.quality.freshness.state.value,
        },
        "copilot_routing": {
            "latency": routing_latency,
            "intent": route_intent.intent.value,
            "sub_intent": route_intent.sub_intent,
            "required_agents": [item.value for item in route_intent.required_agents],
            "evidence_categories": [
                item.category.value for item in route_plan.evidence_requirements
            ],
        },
        "copilot_full_pipeline": {
            "latency": copilot_latency,
            "response_status": copilot_result.status.value,
            "validation_status": copilot_result.validation.status.value,
            "evidence_count": len(copilot_result.evidence),
            "model_calls": audit.model_calls,
        },
        "endpoints": {
            "news_security": {
                "path": "/intelligence/news/security/NVDA",
                "latency": news_endpoint_latency,
                "status_code": news_endpoint_response.status_code,
                "service_status": news_endpoint_response.json().get("status"),
            },
            "session_security": {
                "path": "/intelligence/session/NVDA",
                "latency": session_endpoint_latency,
                "status_code": session_endpoint_response.status_code,
                "service_status": session_endpoint_response.json().get("status"),
            },
        },
        "thresholds": {
            "news_pipeline_p95_ms": news_threshold_ms,
            "session_pipeline_p95_ms": session_threshold_ms,
            "copilot_routing_p95_ms": routing_threshold_ms,
            "copilot_full_pipeline_p95_ms": copilot_threshold_ms,
            "endpoint_p95_ms": endpoint_threshold_ms,
        },
        "threshold_results": threshold_results,
        "limitations": [
            "Measurements exercise deterministic in-process services with synthetic metadata and recorded bars.",
            "No live news, intraday market-data, network, or model provider is invoked.",
            "Host load can affect wall-clock percentiles; thresholds are release guards, not service-level objectives.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark deterministic Stage 8 context-intelligence paths."
    )
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = build_payload(iterations=max(10, args.iterations))
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    if payload["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
