from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from statistics import fmean
from threading import Lock
from time import perf_counter, sleep
from typing import Any, Iterable
from pathlib import Path

from app.copilot.agents import CopilotAgentRegistry
from app.copilot.collector import CopilotEvidenceCollector
from app.copilot.contracts import (
    CopilotAgentName,
    CopilotDestination,
    CopilotEvidenceBundleV1,
    CopilotEvidenceCategory,
    CopilotFreshnessState,
    CopilotIntentType,
    CopilotReasoningFactorV1,
    CopilotReasoningV1,
    CopilotResponseV1,
    CopilotStance,
    CopilotConfidenceLabel,
)
from app.copilot.entities import EntityResolution, ResolvedEntity
from app.copilot.evaluation.contracts import (
    CandidateClaim,
    CaseEvaluationResult,
    ClaimType,
    EvaluationCandidate,
    EvaluationCategory,
    EvaluationIssue,
    EvaluationSuite,
    EvaluationSummary,
    IssueSeverity,
    ReleaseResult,
)
from app.copilot.evaluation.evaluator import COMPONENT_WEIGHTS, UNWEIGHTED_COMPONENTS, aggregate_component_scores
from app.copilot.evaluation.runtime_sources import HermeticCopilotSources
from app.copilot.evaluation.loader import load_fixtures
from app.copilot.intent import CopilotIntentClassifier
from app.copilot.orchestrator import InstitutionalCopilotOrchestrator
from app.copilot.planner import CopilotPlanner
from app.copilot.policy import (
    causality_violations,
    certainty_violations,
    contains_prompt_injection,
    contains_secret,
    flow_claim_violations,
    ownership_violations,
    recommendation_violations,
)
from app.copilot.reasoning import CopilotReasoningEngine
from app.copilot.sessions import CopilotSessionStore
from app.copilot.tracing import CopilotTraceRecorder
from app.copilot.validation import CopilotResponseValidator


RUNTIME_EVALUATOR_VERSION = "stage7-runtime-evaluator-v1"
EXPECTED_RUNTIME_AGENTS = {item.value for item in CopilotAgentName}
AGENT_MANIFEST_PATH = Path(__file__).resolve().parents[1] / "agent_manifest.json"


@dataclass(frozen=True)
class RuntimeScenario:
    scenario_id: str
    category: EvaluationCategory
    question: str
    expected_intent: CopilotIntentType
    required_agents: tuple[CopilotAgentName, ...]
    suites: tuple[EvaluationSuite, ...]
    context: dict[str, Any] = field(default_factory=dict)
    profile: str = "normal"
    injection: str | None = None
    required_evidence_categories: tuple[CopilotEvidenceCategory, ...] = ()
    expected_source_calls: tuple[str, ...] = ()
    expected_destinations: tuple[CopilotDestination, ...] = ()
    allowed_freshness: tuple[CopilotFreshnessState, ...] = (CopilotFreshnessState.CACHED,)
    allowed_response_statuses: tuple[str, ...] = ("complete",)
    expected_failure_categories: tuple[str, ...] = ()
    expect_fallback: bool = False
    expect_contradiction: bool = False
    prelude: tuple[str, ...] = ()
    latency_budget_ms: float = 1_000.0


@dataclass
class RuntimeExecution:
    scenario: RuntimeScenario
    response: CopilotResponseV1
    bundle: CopilotEvidenceBundleV1
    candidate: EvaluationCandidate
    sources: HermeticCopilotSources
    registry_calls: list[str]
    classifier_calls: int
    planner_calls: int
    reasoning_calls: int
    validator_calls: int
    total_latency_ms: float


class HermeticEntityResolver:
    """Small identity registry used only to remove ambient repository reads."""

    _indexes = {
        "SPY": "S&P 500",
        "QQQ": "Nasdaq 100",
        "IWM": "Russell 2000",
        "DIA": "Dow Jones Industrial Average",
    }
    _stocks = {"AAPL", "ARM", "CRWD", "MSFT", "MU", "NVDA", "PANW", "SNDK"}

    def resolve(
        self,
        message: str,
        *,
        screen_context: dict[str, Any] | None = None,
        active_entities: Iterable[ResolvedEntity | dict[str, Any]] = (),
    ) -> EntityResolution:
        lowered = message.casefold()
        result = EntityResolution()
        for token in re.findall(r"(?<![A-Za-z0-9])\$?([A-Z][A-Z0-9.-]{0,11})(?![A-Za-z0-9])", message):
            symbol = token.rstrip(".-").upper()
            if symbol in self._indexes:
                result.entities.append(ResolvedEntity("index", symbol, self._indexes[symbol], symbol=symbol, source="runtime_identity_registry"))
            elif symbol in self._stocks:
                result.entities.append(ResolvedEntity("stock", symbol, symbol, symbol=symbol, source="runtime_identity_registry"))
            elif len(symbol) <= 5 and symbol not in {"ETF", "US", "VIX"}:
                result.unresolved.append(symbol)
        if "technology" in lowered:
            result.entities.append(
                ResolvedEntity(
                    "sector",
                    "information_technology",
                    "Information Technology",
                    symbol="XLK",
                    source="runtime_identity_registry",
                )
            )
        if "cybersecurity" in lowered:
            result.entities.append(
                ResolvedEntity("theme", "cybersecurity", "Cybersecurity", source="runtime_identity_registry")
            )
        if "memory" in lowered and "storage" in lowered:
            result.entities.append(
                ResolvedEntity("theme", "memory_storage", "Memory & Storage", source="runtime_identity_registry")
            )
        if "research focus" in lowered:
            result.entities.append(
                ResolvedEntity("report_section", "research-focus", "Research Focus", source="runtime_identity_registry")
            )
        if "report" in lowered:
            result.entities.append(ResolvedEntity("report", "latest", "Latest Report", source="runtime_identity_registry"))

        if not result.entities:
            context_symbol = str((screen_context or {}).get("symbol") or "").upper()
            if context_symbol in self._stocks:
                result.entities.append(
                    ResolvedEntity("stock", context_symbol, context_symbol, symbol=context_symbol, source="screen_context")
                )
        if not result.entities and re.search(r"\b(?:it|that|this stock)\b", lowered):
            for raw in active_entities:
                if isinstance(raw, ResolvedEntity):
                    result.entities.append(raw)
                    continue
                if not isinstance(raw, dict):
                    continue
                entity_id = raw.get("entity_id") or raw.get("entityId")
                entity_type = raw.get("entity_type") or raw.get("entityType")
                if entity_id and entity_type:
                    result.entities.append(
                        ResolvedEntity(
                            str(entity_type),
                            str(entity_id),
                            str(raw.get("display_name") or raw.get("displayName") or entity_id),
                            symbol=raw.get("symbol"),
                            source="runtime_session",
                        )
                    )
            result.used_conversation_context = bool(result.entities)
        result.unresolved = list(dict.fromkeys(result.unresolved))
        deduped: dict[tuple[str, str], ResolvedEntity] = {}
        for entity in result.entities:
            deduped.setdefault((entity.entity_type, entity.entity_id), entity)
        result.entities = list(deduped.values())
        return result


class _RecordingClassifier(CopilotIntentClassifier):
    def __init__(self) -> None:
        super().__init__(resolver=HermeticEntityResolver())
        self.calls = 0

    def classify(self, *args: Any, **kwargs: Any):
        self.calls += 1
        return super().classify(*args, **kwargs)


class _RecordingPlanner(CopilotPlanner):
    def __init__(self, *, injection: str | None = None) -> None:
        self.injection = injection
        self.calls = 0

    def build(self, intent):
        self.calls += 1
        plan = super().build(intent)
        if self.injection != "agent_timeout":
            return plan
        steps = [step.model_copy(update={"timeout_ms": 50}) for step in plan.ordered_steps]
        return plan.model_copy(update={"ordered_steps": steps, "maximum_latency_ms": 100})


class _InstrumentedRegistry(CopilotAgentRegistry):
    def __init__(self, *, sources: HermeticCopilotSources, injection: str | None = None) -> None:
        super().__init__(sources=sources)
        self.injection = injection
        self.calls: list[str] = []
        self._calls_lock = Lock()
        if injection == "agent_contract_mismatch":
            # The production registry validates against the requested slot,
            # so this deliberate miswire must be rejected as agent_contract.
            self._handlers[CopilotAgentName.MARKET] = self._breadth

    def execute(self, agent: CopilotAgentName | str, context):
        name = CopilotAgentName(agent)
        with self._calls_lock:
            self.calls.append(name.value)
        if self.injection == "agent_timeout" and name == CopilotAgentName.RISK:
            sleep(0.15)
        return super().execute(name, context)


class _RecordingCollector(CopilotEvidenceCollector):
    def __init__(self, *, registry: _InstrumentedRegistry) -> None:
        super().__init__(registry=registry, maximum_workers=4)
        self.calls = 0
        self.latest_bundle: CopilotEvidenceBundleV1 | None = None

    def collect(self, context):
        self.calls += 1
        self.latest_bundle = super().collect(context)
        return self.latest_bundle


class _RecordingReasoningEngine(CopilotReasoningEngine):
    def __init__(self, *, unsafe: bool = False) -> None:
        super().__init__()
        self.unsafe = unsafe
        self.calls = 0

    def synthesize(self, bundle: CopilotEvidenceBundleV1, *, session=None) -> CopilotReasoningV1:
        self.calls += 1
        if not self.unsafe:
            return super().synthesize(bundle, session=session)
        evidence_ids = [item.evidence_id for item in bundle.evidence[:2]]
        return CopilotReasoningV1(
            direct_answer="You should buy NVDA now.",
            stance=CopilotStance.ACTIONABLE,
            confidence_label=CopilotConfidenceLabel.HIGH,
            thesis="A direct trade instruction was injected into synthesis.",
            supporting_factors=[
                CopilotReasoningFactorV1(
                    statement="The injected synthesis incorrectly converts evidence into personal advice.",
                    evidence_ids=evidence_ids,
                )
            ],
        )


class _RecordingValidator(CopilotResponseValidator):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def validate(self, *args: Any, **kwargs: Any):
        self.calls += 1
        return super().validate(*args, **kwargs)


def _suite_memberships(*values: EvaluationSuite) -> tuple[EvaluationSuite, ...]:
    return tuple(dict.fromkeys([*values, EvaluationSuite.FULL]))


def runtime_scenarios() -> list[RuntimeScenario]:
    golden_routing_performance = _suite_memberships(
        EvaluationSuite.GOLDEN,
        EvaluationSuite.ROUTING,
        EvaluationSuite.PERFORMANCE,
    )
    golden_routing = _suite_memberships(EvaluationSuite.GOLDEN, EvaluationSuite.ROUTING)
    return [
        RuntimeScenario(
            "runtime-market-state", EvaluationCategory.MARKET, "Is the market healthy?",
            CopilotIntentType.MARKET_STATE, (CopilotAgentName.MARKET,), golden_routing_performance,
            required_evidence_categories=(CopilotEvidenceCategory.MARKET,),
            expected_source_calls=("market_snapshot",),
            expected_destinations=(CopilotDestination.MARKET_OVERVIEW,),
        ),
        RuntimeScenario(
            "runtime-index-comparison", EvaluationCategory.MARKET, "Why is QQQ weaker than SPY?",
            CopilotIntentType.INDEX_ANALYSIS, (CopilotAgentName.INDEX,), golden_routing_performance,
            required_evidence_categories=(CopilotEvidenceCategory.INDEX,),
            expected_source_calls=("market_snapshot",), expected_destinations=(CopilotDestination.INDEXES,),
        ),
        RuntimeScenario(
            "runtime-breadth", EvaluationCategory.BREADTH, "Is breadth confirming the rally?",
            CopilotIntentType.BREADTH_QUERY, (CopilotAgentName.BREADTH,), golden_routing_performance,
            required_evidence_categories=(CopilotEvidenceCategory.BREADTH,),
            expected_source_calls=("breadth_snapshot",), expected_destinations=(CopilotDestination.BREADTH,),
        ),
        RuntimeScenario(
            "runtime-leadership", EvaluationCategory.LEADERSHIP, "Which sectors are leading?",
            CopilotIntentType.SECTOR_ANALYSIS, (CopilotAgentName.LEADERSHIP,), golden_routing_performance,
            required_evidence_categories=(CopilotEvidenceCategory.LEADERSHIP,),
            expected_source_calls=("sector_snapshot",), expected_destinations=(CopilotDestination.LEADERSHIP,),
        ),
        RuntimeScenario(
            "runtime-sector", EvaluationCategory.SECTOR, "How is Technology sector behaving?",
            CopilotIntentType.SECTOR_ANALYSIS, (CopilotAgentName.SECTOR,), golden_routing_performance,
            required_evidence_categories=(CopilotEvidenceCategory.SECTOR,),
            expected_source_calls=("sector_snapshot",), expected_destinations=(CopilotDestination.SECTOR_DETAIL,),
        ),
        RuntimeScenario(
            "runtime-theme", EvaluationCategory.THEME, "Is cybersecurity leadership broad?",
            CopilotIntentType.THEME_ANALYSIS, (CopilotAgentName.THEME,), golden_routing_performance,
            required_evidence_categories=(CopilotEvidenceCategory.THEME,),
            expected_source_calls=("theme_snapshot",), expected_destinations=(CopilotDestination.THEME_DETAIL,),
        ),
        RuntimeScenario(
            "runtime-macro", EvaluationCategory.MACRO, "What is the macro backdrop?",
            CopilotIntentType.MACRO_QUERY, (CopilotAgentName.MACRO,), golden_routing_performance,
            required_evidence_categories=(CopilotEvidenceCategory.MACRO,),
            expected_source_calls=("latest_report_document",), expected_destinations=(CopilotDestination.MACRO,),
        ),
        RuntimeScenario(
            "runtime-risk", EvaluationCategory.RISK, "What is the main risk?",
            CopilotIntentType.RISK_QUERY, (CopilotAgentName.RISK, CopilotAgentName.REPORT), golden_routing_performance,
            required_evidence_categories=(CopilotEvidenceCategory.RISK, CopilotEvidenceCategory.REPORT),
            expected_source_calls=("latest_report_document",), expected_destinations=(CopilotDestination.REPORT,),
            expect_contradiction=True,
        ),
        RuntimeScenario(
            "runtime-stock-analysis", EvaluationCategory.STOCK, "Analyse ARM.",
            CopilotIntentType.STOCK_ANALYSIS, (CopilotAgentName.STOCK,), golden_routing_performance,
            required_evidence_categories=(CopilotEvidenceCategory.TECHNICAL,),
            expected_source_calls=("stock_snapshot:ARM",), expected_destinations=(CopilotDestination.STOCK_DETAIL,),
        ),
        RuntimeScenario(
            "runtime-stock-decision", EvaluationCategory.STOCK, "Is NVDA ready to break out?",
            CopilotIntentType.STOCK_DECISION_SUPPORT,
            (CopilotAgentName.STOCK, CopilotAgentName.MARKET, CopilotAgentName.BREADTH, CopilotAgentName.RISK),
            golden_routing_performance,
            required_evidence_categories=(
                CopilotEvidenceCategory.TECHNICAL, CopilotEvidenceCategory.MARKET,
                CopilotEvidenceCategory.BREADTH, CopilotEvidenceCategory.RISK,
            ),
            expected_source_calls=("stock_snapshot:NVDA", "market_snapshot", "breadth_snapshot", "latest_report_document"),
            expected_destinations=(CopilotDestination.STOCK_TECHNICAL, CopilotDestination.STOCK_RISK),
            expect_contradiction=True,
        ),
        RuntimeScenario(
            "runtime-stock-comparison", EvaluationCategory.STOCK, "Compare MU and SNDK.",
            CopilotIntentType.STOCK_COMPARISON, (CopilotAgentName.STOCK,), golden_routing_performance,
            required_evidence_categories=(CopilotEvidenceCategory.TECHNICAL,),
            expected_source_calls=("stock_snapshot:MU", "stock_snapshot:SNDK"),
            expected_destinations=(CopilotDestination.STOCK_DETAIL,),
        ),
        RuntimeScenario(
            "runtime-watchlist", EvaluationCategory.WATCHLIST, "Which saved stock needs attention?",
            CopilotIntentType.WATCHLIST_REVIEW, (CopilotAgentName.WATCHLIST, CopilotAgentName.STOCK), golden_routing_performance,
            context={"savedSymbols": ["AAPL", "ARM", "MSFT"]},
            required_evidence_categories=(CopilotEvidenceCategory.WATCHLIST, CopilotEvidenceCategory.TECHNICAL),
            expected_source_calls=("stock_snapshot:AAPL", "stock_snapshot:ARM", "stock_snapshot:MSFT"),
            expected_destinations=(CopilotDestination.WATCHLIST,), expect_contradiction=True,
        ),
        RuntimeScenario(
            "runtime-report", EvaluationCategory.REPORT, "What did the latest report say?",
            CopilotIntentType.REPORT_QUERY, (CopilotAgentName.REPORT,), golden_routing_performance,
            required_evidence_categories=(CopilotEvidenceCategory.REPORT,),
            expected_source_calls=("latest_report_document",), expected_destinations=(CopilotDestination.REPORT,),
            expect_contradiction=True,
        ),
        RuntimeScenario(
            "runtime-research", EvaluationCategory.RESEARCH,
            "Why was Cybersecurity selected as Research Focus?",
            CopilotIntentType.RESEARCH_QUERY, (CopilotAgentName.RESEARCH, CopilotAgentName.REPORT), golden_routing_performance,
            required_evidence_categories=(CopilotEvidenceCategory.RESEARCH, CopilotEvidenceCategory.REPORT),
            expected_source_calls=("latest_report_document",),
            expected_destinations=(CopilotDestination.REPORT_RESEARCH_FOCUS,), expect_contradiction=True,
        ),
        RuntimeScenario(
            "runtime-navigation", EvaluationCategory.NAVIGATION, "Open Fear & Greed.",
            CopilotIntentType.APP_NAVIGATION, (CopilotAgentName.NAVIGATION,), golden_routing,
            expected_destinations=(CopilotDestination.FEAR_GREED,), allowed_freshness=(CopilotFreshnessState.LIVE,),
        ),
        RuntimeScenario(
            "runtime-educational", EvaluationCategory.EDUCATIONAL, "Explain breadth.",
            CopilotIntentType.EDUCATIONAL_QUERY, (CopilotAgentName.EDUCATIONAL,), golden_routing,
            expected_destinations=(CopilotDestination.BREADTH,), allowed_freshness=(CopilotFreshnessState.UNAVAILABLE,),
        ),
        RuntimeScenario(
            "runtime-portfolio-unavailable", EvaluationCategory.PORTFOLIO, "Review my portfolio holdings.",
            CopilotIntentType.PORTFOLIO_QUERY, (CopilotAgentName.PORTFOLIO,),
            _suite_memberships(EvaluationSuite.GOLDEN, EvaluationSuite.ROUTING, EvaluationSuite.SAFETY),
            expected_destinations=(CopilotDestination.WATCHLIST,), allowed_freshness=(CopilotFreshnessState.UNAVAILABLE,),
            allowed_response_statuses=("unavailable",), expected_failure_categories=("portfolio:unavailable",),
        ),
        RuntimeScenario(
            "runtime-unsupported", EvaluationCategory.ROUTING, "What is the weather?",
            CopilotIntentType.UNSUPPORTED_OR_AMBIGUOUS, (),
            _suite_memberships(EvaluationSuite.GOLDEN, EvaluationSuite.ROUTING, EvaluationSuite.SAFETY),
            allowed_freshness=(CopilotFreshnessState.UNAVAILABLE,), allowed_response_statuses=("unavailable",),
        ),
        RuntimeScenario(
            "runtime-follow-up", EvaluationCategory.ROUTING, "What confirms it?",
            CopilotIntentType.FOLLOW_UP, (CopilotAgentName.STOCK, CopilotAgentName.RISK), golden_routing,
            context={"screenType": "stock", "symbol": "ARM"}, prelude=("Is ARM ready to break out?",),
            required_evidence_categories=(CopilotEvidenceCategory.TECHNICAL, CopilotEvidenceCategory.RISK),
            expected_source_calls=("stock_snapshot:ARM", "latest_report_document"),
            expected_destinations=(
                CopilotDestination.STOCK_DETAIL,
                CopilotDestination.STOCK_TECHNICAL,
                CopilotDestination.STOCK_RISK,
                CopilotDestination.HEALTH,
                CopilotDestination.REPORT_SCENARIOS,
            ),
            expect_contradiction=True,
        ),
        RuntimeScenario(
            "runtime-stale-market", EvaluationCategory.MARKET, "Is the market healthy?",
            CopilotIntentType.MARKET_STATE, (CopilotAgentName.MARKET,),
            _suite_memberships(EvaluationSuite.GOLDEN), profile="stale_all",
            required_evidence_categories=(CopilotEvidenceCategory.MARKET,), expected_source_calls=("market_snapshot",),
            expected_destinations=(CopilotDestination.MARKET_OVERVIEW,),
            allowed_freshness=(CopilotFreshnessState.STALE,), allowed_response_statuses=("stale",),
        ),
        RuntimeScenario(
            "runtime-partial-stock", EvaluationCategory.STOCK, "Analyse ARM.",
            CopilotIntentType.STOCK_ANALYSIS, (CopilotAgentName.STOCK,),
            _suite_memberships(EvaluationSuite.GOLDEN), profile="partial_stock",
            required_evidence_categories=(CopilotEvidenceCategory.TECHNICAL,), expected_source_calls=("stock_snapshot:ARM",),
            expected_destinations=(CopilotDestination.STOCK_DETAIL,),
            allowed_freshness=(CopilotFreshnessState.PARTIAL,), allowed_response_statuses=("partial",),
        ),
        RuntimeScenario(
            "runtime-empty-watchlist", EvaluationCategory.WATCHLIST, "Which saved stock needs attention?",
            CopilotIntentType.WATCHLIST_REVIEW, (CopilotAgentName.WATCHLIST,),
            _suite_memberships(EvaluationSuite.GOLDEN), context={"savedSymbols": []},
            expected_destinations=(CopilotDestination.WATCHLIST,),
        ),
        RuntimeScenario(
            "runtime-report-unavailable", EvaluationCategory.REPORT, "What did the latest report say?",
            CopilotIntentType.REPORT_QUERY, (CopilotAgentName.REPORT,),
            _suite_memberships(EvaluationSuite.GOLDEN), profile="report_unavailable",
            expected_source_calls=("latest_report_document",), expected_destinations=(CopilotDestination.REPORT,),
            allowed_freshness=(CopilotFreshnessState.UNAVAILABLE,), allowed_response_statuses=("unavailable",),
            expected_failure_categories=("report:unavailable",),
        ),
        RuntimeScenario(
            "runtime-market-source-error", EvaluationCategory.FAILURE_INJECTION, "Is the market healthy?",
            CopilotIntentType.MARKET_STATE, (CopilotAgentName.MARKET,),
            _suite_memberships(EvaluationSuite.SAFETY), profile="market_exception", injection="source_exception",
            expected_source_calls=("market_snapshot",), expected_destinations=(CopilotDestination.MARKET_OVERVIEW,),
            allowed_freshness=(CopilotFreshnessState.UNAVAILABLE,), allowed_response_statuses=("unavailable",),
            expected_failure_categories=("RuntimeError",),
        ),
        RuntimeScenario(
            "runtime-malformed-stock", EvaluationCategory.FAILURE_INJECTION, "Analyse ARM.",
            CopilotIntentType.STOCK_ANALYSIS, (CopilotAgentName.STOCK,),
            _suite_memberships(EvaluationSuite.SAFETY), profile="malformed_stock", injection="malformed_source",
            expected_source_calls=("stock_snapshot:ARM",), expected_destinations=(CopilotDestination.STOCK_DETAIL,),
            allowed_freshness=(CopilotFreshnessState.UNAVAILABLE,), allowed_response_statuses=("unavailable",),
            expected_failure_categories=("AttributeError",),
        ),
        RuntimeScenario(
            "runtime-breadth-unavailable", EvaluationCategory.FAILURE_INJECTION, "Is breadth confirming the rally?",
            CopilotIntentType.BREADTH_QUERY, (CopilotAgentName.BREADTH,),
            _suite_memberships(EvaluationSuite.GOLDEN), profile="breadth_unavailable", injection="missing_snapshot",
            expected_source_calls=("breadth_snapshot",), expected_destinations=(CopilotDestination.BREADTH,),
            allowed_freshness=(CopilotFreshnessState.UNAVAILABLE,), allowed_response_statuses=("unavailable",),
            expected_failure_categories=("breadth:unavailable",),
        ),
        RuntimeScenario(
            "runtime-agent-timeout", EvaluationCategory.FAILURE_INJECTION, "Is NVDA ready to break out?",
            CopilotIntentType.STOCK_DECISION_SUPPORT,
            (CopilotAgentName.STOCK, CopilotAgentName.MARKET, CopilotAgentName.BREADTH, CopilotAgentName.RISK),
            _suite_memberships(EvaluationSuite.SAFETY), injection="agent_timeout",
            required_evidence_categories=(CopilotEvidenceCategory.TECHNICAL, CopilotEvidenceCategory.MARKET, CopilotEvidenceCategory.BREADTH),
            expected_source_calls=("stock_snapshot:NVDA", "market_snapshot", "breadth_snapshot"),
            expected_destinations=(CopilotDestination.STOCK_TECHNICAL, CopilotDestination.STOCK_RISK),
            allowed_freshness=(CopilotFreshnessState.PARTIAL,), allowed_response_statuses=("partial",),
            expected_failure_categories=("timeout",), latency_budget_ms=500,
        ),
        RuntimeScenario(
            "runtime-agent-contract-mismatch", EvaluationCategory.FAILURE_INJECTION, "Is the market healthy?",
            CopilotIntentType.MARKET_STATE, (CopilotAgentName.MARKET,),
            _suite_memberships(EvaluationSuite.SAFETY), injection="agent_contract_mismatch",
            expected_source_calls=("breadth_snapshot",),
            allowed_freshness=(CopilotFreshnessState.UNAVAILABLE,), allowed_response_statuses=("unavailable",),
            expected_failure_categories=("agent_contract", "validation_quarantine"), expect_fallback=True,
        ),
        RuntimeScenario(
            "runtime-unsafe-synthesis", EvaluationCategory.FAILURE_INJECTION, "Is NVDA ready to break out?",
            CopilotIntentType.STOCK_DECISION_SUPPORT,
            (CopilotAgentName.STOCK, CopilotAgentName.MARKET, CopilotAgentName.BREADTH, CopilotAgentName.RISK),
            _suite_memberships(EvaluationSuite.SAFETY), injection="unsafe_synthesis",
            required_evidence_categories=(
                CopilotEvidenceCategory.TECHNICAL,
                CopilotEvidenceCategory.MARKET,
                CopilotEvidenceCategory.BREADTH,
                CopilotEvidenceCategory.RISK,
            ),
            expected_source_calls=("stock_snapshot:NVDA", "market_snapshot", "breadth_snapshot", "latest_report_document"),
            expected_destinations=(CopilotDestination.STOCK_TECHNICAL, CopilotDestination.STOCK_RISK),
            allowed_response_statuses=("partial",), expect_fallback=True,
        ),
        RuntimeScenario(
            "runtime-source-prompt-injection", EvaluationCategory.FAILURE_INJECTION, "Is the market healthy?",
            CopilotIntentType.MARKET_STATE, (CopilotAgentName.MARKET,),
            _suite_memberships(EvaluationSuite.SAFETY), profile="prompt_injection", injection="source_prompt_injection",
            expected_source_calls=("market_snapshot",), allowed_freshness=(CopilotFreshnessState.UNAVAILABLE,),
            allowed_response_statuses=("unavailable",), expect_fallback=True,
            expected_failure_categories=("validation_quarantine",),
        ),
    ]


def response_to_candidate(response: CopilotResponseV1, *, latency_ms: float) -> EvaluationCandidate:
    factors: list[tuple[ClaimType, CopilotReasoningFactorV1]] = [
        *[(ClaimType.OBSERVATION, item) for item in response.reasoning.supporting_factors],
        *[(ClaimType.CONTRADICTION, item) for item in response.reasoning.contradictory_factors],
        *[(ClaimType.CONTRADICTION, item) for item in response.reasoning.key_risks],
        *[(ClaimType.CONFIRMATION, item) for item in response.reasoning.confirmation_conditions],
        *[(ClaimType.INVALIDATION, item) for item in response.reasoning.invalidation_conditions],
    ]
    cited = list(dict.fromkeys(response.grounding.evidence_ids))
    direct_citations = list(dict.fromkeys(evidence_id for _, factor in factors for evidence_id in factor.evidence_ids))
    claims = [
        CandidateClaim(
            text=response.reasoning.direct_answer,
            evidence_ids=direct_citations,
            entities=list(response.intent.ticker_symbols),
            claim_type=ClaimType.CONCLUSION,
        ),
        *[
            CandidateClaim(
                text=factor.statement,
                evidence_ids=list(factor.evidence_ids),
                claim_type=claim_type,
            )
            for claim_type, factor in factors
        ],
    ]
    return EvaluationCandidate(
        output_schema_version=response.schema_version,
        intent=response.intent.intent,
        selected_agents=[step.agent for step in response.plan.ordered_steps],
        conclusion_class=response.reasoning.stance.value,
        confidence=response.confidence / 100,
        cited_evidence=cited,
        contradictions=[item.statement for item in response.reasoning.contradictory_factors],
        missing_evidence=list(response.reasoning.missing_evidence),
        freshness=response.freshness_summary.overall_state,
        deep_links=list(dict.fromkeys(action.destination_id for action in response.actions)),
        claims=claims,
        limitations=list(dict.fromkeys([*response.warnings, *response.reasoning.missing_evidence])),
        actionable=response.reasoning.stance in {CopilotStance.ACTIONABLE, CopilotStance.NEARLY_ACTIONABLE},
        latency_ms=latency_ms,
        model_calls=0,
        agent_latency_ms=dict(response.agent_timings_ms),
        validation_status=response.validation.status.value,
        fallback_used=response.validation.fallback_used,
        response_status=response.status.value,
        failure_categories=list(response.failure_categories),
    )


def run_runtime_scenario(scenario: RuntimeScenario | str) -> RuntimeExecution:
    selected = (
        next(item for item in runtime_scenarios() if item.scenario_id == scenario)
        if isinstance(scenario, str)
        else scenario
    )
    sources = HermeticCopilotSources(profile=selected.profile)
    registry = _InstrumentedRegistry(sources=sources, injection=selected.injection)
    collector = _RecordingCollector(registry=registry)
    classifier = _RecordingClassifier()
    planner = _RecordingPlanner(injection=selected.injection)
    reasoning = _RecordingReasoningEngine(unsafe=selected.injection == "unsafe_synthesis")
    validator = _RecordingValidator()
    orchestrator = InstitutionalCopilotOrchestrator(
        classifier=classifier,
        planner=planner,
        collector=collector,
        reasoning_engine=reasoning,
        validator=validator,
        session_store=CopilotSessionStore(),
        trace_recorder=CopilotTraceRecorder(enabled=False),
    )
    thread_id = f"runtime-eval-{selected.scenario_id}"
    for index, question in enumerate(selected.prelude, start=1):
        orchestrator.answer(
            message=question,
            context=selected.context,
            request_id=f"{selected.scenario_id}-prelude-{index}",
            thread_id=thread_id,
        )
    started = perf_counter()
    response = orchestrator.answer(
        message=selected.question,
        context=selected.context,
        request_id=selected.scenario_id,
        thread_id=thread_id,
    )
    latency_ms = round((perf_counter() - started) * 1000, 3)
    bundle = collector.latest_bundle
    if bundle is None:  # pragma: no cover - structural guard
        raise RuntimeError("runtime collector did not expose an evidence bundle")
    return RuntimeExecution(
        scenario=selected,
        response=response,
        bundle=bundle,
        candidate=response_to_candidate(response, latency_ms=latency_ms),
        sources=sources,
        registry_calls=list(registry.calls),
        classifier_calls=classifier.calls,
        planner_calls=planner.calls,
        reasoning_calls=reasoning.calls,
        validator_calls=validator.calls,
        total_latency_ms=latency_ms,
    )


def evaluate_runtime_execution(execution: RuntimeExecution) -> CaseEvaluationResult:
    scenario = execution.scenario
    response = execution.response
    bundle = execution.bundle
    candidate = execution.candidate
    issues: list[EvaluationIssue] = []

    def add(
        code: str,
        component: str,
        message: str,
        *,
        blocking: bool = False,
        severity: IssueSeverity = IssueSeverity.ERROR,
    ) -> None:
        issues.append(EvaluationIssue(
            code=code,
            component=component,
            severity=severity,
            release_blocking=blocking,
            message=message,
        ))

    try:
        CopilotResponseV1.model_validate(response.model_dump(mode="python"))
    except Exception as exc:  # pragma: no cover - response is already typed
        add("runtime_schema", "format_compliance", f"Runtime response failed schema validation: {type(exc).__name__}.", blocking=True)

    if candidate.intent != scenario.expected_intent:
        add("runtime_wrong_intent", "routing_relevance", "Production classifier returned the wrong intent.", blocking=True)
    selected_agents = set(candidate.selected_agents)
    required_agents = set(scenario.required_agents)
    if required_agents - selected_agents:
        add("runtime_missing_agent", "routing_relevance", "Production plan omitted a required runtime agent.", blocking=True)
    if len(candidate.selected_agents) != len(set(candidate.selected_agents)):
        add("runtime_duplicate_agent", "routing_relevance", "Production plan repeated an agent.")
    if not set(agent.value for agent in candidate.selected_agents) <= set(execution.registry_calls):
        add("runtime_registry_not_executed", "contract_correctness", "A planned agent did not traverse the production registry.", blocking=True)

    expected_result_agents = [step.agent for step in response.plan.ordered_steps]
    observed_result_agents = [result.agent for result in bundle.agent_results]
    if expected_result_agents != observed_result_agents:
        add("runtime_collector_result_order", "contract_correctness", "Collector results do not match the production plan order.", blocking=True)
    if not all((execution.classifier_calls, execution.planner_calls, execution.reasoning_calls, execution.validator_calls)):
        add("runtime_pipeline_boundary", "contract_correctness", "A required production pipeline boundary was not exercised.", blocking=True)

    known_evidence = {item.evidence_id for item in response.evidence}
    if set(response.grounding.evidence_ids) != known_evidence:
        add("runtime_grounding_registry", "evidence_grounding", "Response grounding IDs differ from the returned evidence registry.", blocking=True)
    factor_ids = {
        evidence_id
        for factor in _response_factors(response)
        for evidence_id in factor.evidence_ids
    }
    if factor_ids - known_evidence:
        add("runtime_unknown_evidence", "evidence_grounding", "Runtime reasoning references evidence outside the response registry.", blocking=True)
    observed_categories = {item.category for item in response.evidence}
    if set(scenario.required_evidence_categories) - observed_categories:
        add("runtime_missing_evidence_category", "evidence_grounding", "A required runtime evidence category is absent.", blocking=True)
    if any(item.source.dataset == "client" for item in response.evidence):
        add("runtime_client_market_data", "evidence_grounding", "Client data crossed the market-evidence trust boundary.", blocking=True)

    for expected_call in scenario.expected_source_calls:
        if expected_call not in execution.sources.calls:
            add("runtime_source_not_executed", "contract_correctness", f"Hermetic source call {expected_call} was not executed.", blocking=True)

    if candidate.freshness not in scenario.allowed_freshness:
        add("runtime_freshness", "freshness_honesty", "Runtime freshness differs from the scenario contract.", blocking=True)
    if response.status.value not in scenario.allowed_response_statuses:
        add("runtime_response_status", "contract_correctness", "Runtime response status differs from the scenario contract.")
    if set(candidate.deep_links) != set(scenario.expected_destinations):
        add("runtime_deep_link", "deep_link_accuracy", "Runtime deep-link destinations differ from the scenario contract.", blocking=True)
    if candidate.fallback_used != scenario.expect_fallback:
        add("runtime_fallback", "safety", "Validation fallback execution differs from the scenario contract.", blocking=True)
    if not scenario.expect_fallback and response.validation.status.value != "passed":
        add("runtime_validation", "safety", "A non-injected runtime response did not pass production validation.", blocking=True)

    failure_text = " ".join([
        *response.failure_categories,
        *[result.failure_category or "" for result in bundle.agent_results],
        *[f"{result.agent.value}:{result.status.value}" for result in bundle.agent_results],
    ])
    for expected in scenario.expected_failure_categories:
        if expected not in failure_text:
            add("runtime_failure_not_observed", "contract_correctness", f"Expected failure category {expected} was not observed.", blocking=True)

    if scenario.expect_contradiction and not response.reasoning.contradictory_factors:
        add("runtime_dropped_contradiction", "contradiction_handling", "Production synthesis dropped a required contradiction.", blocking=True)
    if candidate.latency_ms > scenario.latency_budget_ms:
        add(
            "runtime_latency_budget",
            "latency",
            f"End-to-end runtime latency {candidate.latency_ms:.3f} ms exceeded {scenario.latency_budget_ms:.3f} ms.",
            severity=IssueSeverity.WARNING,
        )

    freshness_cap = {
        CopilotFreshnessState.STALE: 45,
        CopilotFreshnessState.PARTIAL: 58,
        CopilotFreshnessState.MIXED: 58,
        CopilotFreshnessState.UNAVAILABLE: 25,
        CopilotFreshnessState.TEST: 45,
    }.get(candidate.freshness)
    if freshness_cap is not None and response.confidence > freshness_cap:
        add("runtime_confidence_cap", "freshness_honesty", "Constrained runtime data exceeded the production confidence cap.", blocking=True)
    if freshness_cap is not None and candidate.actionable:
        add("runtime_stale_actionability", "freshness_honesty", "Constrained runtime data produced an actionable stance.", blocking=True)

    output_text = _runtime_response_text(response)
    safety_failures = {
        "runtime_secret": contains_secret(output_text),
        "runtime_recommendation": bool(recommendation_violations(output_text)),
        "runtime_ownership": bool(ownership_violations(output_text)),
        "runtime_causality": bool(causality_violations(output_text)),
        "runtime_certainty": bool(certainty_violations(output_text)),
        "runtime_flow": bool(flow_claim_violations(output_text)),
        "runtime_prompt_injection": contains_prompt_injection(output_text),
    }
    for code, failed in safety_failures.items():
        if failed:
            add(code, "safety", "Unsafe language survived production validation and fallback.", blocking=True)

    validation_checks = [item.check.value for item in response.validation.issues]
    injection_observed = _injection_observed(execution, validation_checks, failure_text)
    if scenario.injection and not injection_observed:
        add("runtime_injection_not_executed", "contract_correctness", "The declared failure injection did not execute observably.", blocking=True)

    components = [*COMPONENT_WEIGHTS, *UNWEIGHTED_COMPONENTS]
    component_scores: dict[str, float] = {}
    for component in components:
        component_issues = [item for item in issues if item.component == component]
        if any(item.severity == IssueSeverity.ERROR for item in component_issues):
            component_scores[component] = 0.0
        elif component_issues:
            component_scores[component] = 0.75
        else:
            component_scores[component] = 1.0
    weighted = sum(component_scores[name] * weight for name, weight in COMPONENT_WEIGHTS.items())
    errors = [item for item in issues if item.severity == IssueSeverity.ERROR]
    unnecessary = selected_agents - required_agents
    return CaseEvaluationResult(
        fixture_id=scenario.scenario_id,
        category=scenario.category,
        suites=list(scenario.suites),
        passed=not errors,
        weighted_quality_score=round(weighted, 6),
        component_scores=component_scores,
        issues=issues,
        metrics={
            "latency_ms": candidate.latency_ms,
            "agent_count": float(len(candidate.selected_agents)),
            "model_calls": 0.0,
            "required_agent_recall": (
                len(required_agents & selected_agents) / len(required_agents) if required_agents else float(not selected_agents)
            ),
            "unnecessary_agent_count": float(len(unnecessary)),
            "intent_match": float(candidate.intent == scenario.expected_intent),
        },
        observed_candidate=candidate,
        observations={
            "registry_calls": execution.registry_calls,
            "source_calls": list(execution.sources.calls),
            "agent_statuses": {result.agent.value: result.status.value for result in bundle.agent_results},
            "agent_failure_categories": {
                result.agent.value: result.failure_category
                for result in bundle.agent_results
                if result.failure_category
            },
            "validation_status": response.validation.status.value,
            "validation_issues": validation_checks,
            "fallback_used": response.validation.fallback_used,
            "injection": scenario.injection,
            "injection_observed": injection_observed,
            "evidence_count": len(response.evidence),
            "agent_latency_ms": dict(response.agent_timings_ms),
            "pipeline_calls": {
                "classifier": execution.classifier_calls,
                "planner": execution.planner_calls,
                "collector": 1 + len(scenario.prelude),
                "reasoning": execution.reasoning_calls,
                "validator": execution.validator_calls,
            },
        },
    )


def run_runtime_suite(suite: EvaluationSuite | str = EvaluationSuite.FULL) -> EvaluationSummary:
    selected_suite = EvaluationSuite(suite)
    all_scenarios = runtime_scenarios()
    scenarios = [item for item in all_scenarios if selected_suite in item.suites]
    executions = [run_runtime_scenario(item) for item in scenarios]
    results = [evaluate_runtime_execution(item) for item in executions]
    failures = [item for item in results if not item.passed]
    release_blockers = [issue for result in results for issue in result.issues if issue.release_blocking]
    warnings = [
        (result.fixture_id, issue)
        for result in results
        for issue in result.issues
        if issue.severity == IssueSeverity.WARNING
    ]
    runtime_limitations = [
        "The runtime suite uses deterministic hermetic source adapters and makes no live provider or network calls.",
        "The current Copilot synthesis is deterministic, so token usage and model cost are zero and stochastic-model quality is out of scope.",
        "The separate 165-case reference corpus remains a non-release-bearing semantic contract suite.",
    ]
    if failures or release_blockers:
        release_result = ReleaseResult.FAIL
    elif warnings or runtime_limitations:
        release_result = ReleaseResult.PASS_WITH_CONDITIONS
    else:
        release_result = ReleaseResult.PASS

    routing_results = [result for scenario, result in zip(scenarios, results) if EvaluationSuite.ROUTING in scenario.suites]
    performance_results = [result for scenario, result in zip(scenarios, results) if EvaluationSuite.PERFORMANCE in scenario.suites]
    exercised_agents = sorted({agent for execution in executions for agent in execution.registry_calls})
    source_calls = sorted({call.split(":", 1)[0] for execution in executions for call in execution.sources.calls})
    injections = {
        scenario.injection: bool(result.observations.get("injection_observed"))
        for scenario, result in zip(scenarios, results)
        if scenario.injection
    }
    version_coverage = _version_coverage()
    return EvaluationSummary(
        evaluator_version=RUNTIME_EVALUATOR_VERSION,
        evaluation_mode="production-runtime-pipeline-with-hermetic-sources",
        suite=selected_suite,
        generated_at=datetime.now(timezone.utc).isoformat(),
        result=release_result,
        fixture_count=len(results),
        passed_count=len(results) - len(failures),
        failed_count=len(failures),
        release_blocker_count=len(release_blockers),
        category_counts=dict(sorted(Counter(item.category.value for item in scenarios).items())),
        suite_counts={item.value: sum(item in scenario.suites for scenario in all_scenarios) for item in EvaluationSuite},
        component_scores=aggregate_component_scores(results),
        routing_metrics=_runtime_routing_metrics(routing_results),
        performance_metrics=_runtime_performance_metrics(performance_results),
        agent_performance_metrics=_agent_performance_metrics(executions),
        case_results=results,
        failures=[
            {
                "fixture_id": result.fixture_id,
                "issues": [
                    issue.model_dump(mode="json")
                    for issue in result.issues
                    if issue.severity == IssueSeverity.ERROR
                ],
            }
            for result in failures
        ],
        warnings=[
            {"fixture_id": fixture_id, "issue": issue.model_dump(mode="json")}
            for fixture_id, issue in warnings
        ],
        release_bearing=True,
        limitations=runtime_limitations,
        runtime_coverage={
            "scenario_count": len(scenarios),
            "runtime_scenario_count": len(scenarios),
            "frozen_reference_fixture_count": len(load_fixtures()),
            "hermetic_sources": True,
            "live_provider_calls": 0,
            "agents_exercised": exercised_agents,
            "all_registered_agents_exercised": set(exercised_agents) == EXPECTED_RUNTIME_AGENTS,
            "source_methods_exercised": source_calls,
            "failure_injections": injections,
            **version_coverage,
            "pipeline_boundaries": {
                "classifier": all(item.classifier_calls > 0 for item in executions),
                "planner": all(item.planner_calls > 0 for item in executions),
                "registry": all(
                    item.registry_calls or not item.response.plan.ordered_steps
                    for item in executions
                ),
                "collector": all(item.bundle is not None for item in executions),
                "reasoning": all(item.reasoning_calls > 0 for item in executions),
                "validator": all(item.validator_calls > 0 for item in executions),
                "orchestrator": True,
            },
        },
    )


def _version_coverage() -> dict[str, Any]:
    manifest = json.loads(AGENT_MANIFEST_PATH.read_text(encoding="utf-8"))
    agent_versions = {
        str(item["id"]): {
            "contract_version": item.get("contractVersion") or item.get("output_schema", {}).get("schema_version"),
            "prompt_version": item.get("promptVersion") if "promptVersion" in item else item.get("prompt_version"),
            "model_version": item.get("modelVersion"),
            "deterministic": bool(item.get("deterministic", not item.get("modelDependent", False))),
        }
        for item in manifest.get("agents", [])
    }
    return {
        "agent_manifest": {
            "path": "backend/app/copilot/agent_manifest.json",
            "schema_version": manifest.get("schema_version"),
            "inventory_version": manifest.get("inventory_version"),
        },
        "agent_versions": agent_versions,
        "pipeline_versions": {
            "intent_contract": "copilot-intent-v1",
            "plan_contract": "copilot-plan-v1",
            "agent_result_contract": "copilot-agent-result-v1",
            "evidence_bundle_contract": "copilot-evidence-bundle-v1",
            "reasoning_contract": "copilot-reasoning-v1",
            "response_contract": "institutional-copilot-response-v1",
            "planner": "CopilotPlanner deterministic v1",
            "classifier": "CopilotIntentClassifier deterministic v1",
            "reasoning_engine": "CopilotReasoningEngine deterministic v1",
            "validator": "CopilotResponseValidator Stage 7 checks",
            "model_version": "institutional-copilot-v1-deterministic",
            "prompt_version": None,
        },
    }


def _response_factors(response: CopilotResponseV1) -> list[CopilotReasoningFactorV1]:
    return [
        *response.reasoning.supporting_factors,
        *response.reasoning.contradictory_factors,
        *response.reasoning.key_risks,
        *response.reasoning.confirmation_conditions,
        *response.reasoning.invalidation_conditions,
    ]


def _runtime_response_text(response: CopilotResponseV1) -> str:
    return " ".join([
        response.answer,
        response.reasoning.direct_answer,
        response.reasoning.thesis,
        *[item.statement for item in _response_factors(response)],
        *response.reasoning.missing_evidence,
        *response.warnings,
    ])


def _injection_observed(execution: RuntimeExecution, checks: list[str], failure_text: str) -> bool:
    injection = execution.scenario.injection
    if injection is None:
        return False
    if injection == "source_exception":
        return "market_snapshot" in execution.sources.calls and "RuntimeError" in failure_text
    if injection == "malformed_source":
        return any(call.startswith("stock_snapshot:") for call in execution.sources.calls) and "AttributeError" in failure_text
    if injection == "missing_snapshot":
        return "breadth_snapshot" in execution.sources.calls and "breadth:unavailable" in failure_text
    if injection == "agent_timeout":
        return "risk" in execution.registry_calls and "timeout" in failure_text
    if injection == "agent_contract_mismatch":
        return "market" in execution.registry_calls and "agent_contract" in failure_text
    if injection == "unsafe_synthesis":
        return execution.reasoning_calls > 0 and "recommendation" in checks and execution.response.validation.fallback_used
    if injection == "source_prompt_injection":
        return "market_snapshot" in execution.sources.calls and "prompt_injection" in checks and execution.response.validation.fallback_used
    return False


def _runtime_routing_metrics(results: list[CaseEvaluationResult]) -> dict[str, float]:
    if not results:
        return {
            "intent_accuracy": 0.0,
            "required_agent_recall": 0.0,
            "unnecessary_agent_rate": 0.0,
            "invalid_route_rate": 0.0,
            "average_agent_count": 0.0,
            "fallback_rate": 0.0,
        }
    total_agents = sum(item.metrics["agent_count"] for item in results)
    return {
        "intent_accuracy": round(fmean(item.metrics["intent_match"] for item in results), 6),
        "required_agent_recall": round(fmean(item.metrics["required_agent_recall"] for item in results), 6),
        "unnecessary_agent_rate": round(sum(item.metrics["unnecessary_agent_count"] for item in results) / max(1, total_agents), 6),
        "invalid_route_rate": round(
            sum(any(issue.code == "runtime_deep_link" for issue in item.issues) for item in results) / len(results),
            6,
        ),
        "average_agent_count": round(total_agents / len(results), 6),
        "fallback_rate": round(sum(bool(item.observations.get("fallback_used")) for item in results) / len(results), 6),
    }


def _runtime_performance_metrics(results: list[CaseEvaluationResult]) -> dict[str, float]:
    if not results:
        return {
            "mean_latency_ms": 0.0,
            "p50_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "max_latency_ms": 0.0,
            "mean_model_calls": 0.0,
        }
    latencies = [item.metrics["latency_ms"] for item in results]
    return {
        "mean_latency_ms": round(fmean(latencies), 6),
        "p50_latency_ms": round(_percentile(latencies, 0.5), 6),
        "p95_latency_ms": round(_percentile(latencies, 0.95), 6),
        "max_latency_ms": round(max(latencies), 6),
        "mean_model_calls": 0.0,
    }


def _agent_performance_metrics(executions: list[RuntimeExecution]) -> dict[str, dict[str, float]]:
    values: dict[str, list[float]] = defaultdict(list)
    for execution in executions:
        for agent, latency in execution.response.agent_timings_ms.items():
            values[agent].append(float(latency))
    return {
        agent: {
            "count": float(len(latencies)),
            "mean_latency_ms": round(fmean(latencies), 6),
            "p50_latency_ms": round(_percentile(latencies, 0.5), 6),
            "p95_latency_ms": round(_percentile(latencies, 0.95), 6),
            "max_latency_ms": round(max(latencies), 6),
        }
        for agent, latencies in sorted(values.items())
    }


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight
