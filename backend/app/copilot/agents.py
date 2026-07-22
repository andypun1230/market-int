from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Callable, Iterable

from app.copilot.agent_contracts import load_agent_contracts, validate_agent_result
from app.copilot.contracts import (
    AgentResultV1,
    CopilotAgentName,
    CopilotAgentStatus,
    CopilotConfidenceLabel,
    CopilotDestination,
    CopilotEvidenceCategory,
    CopilotEvidenceV1,
    CopilotFreshnessState,
    CopilotFreshnessV1,
    CopilotIntentV1,
    CopilotInterpretationClass,
    CopilotLevelV1,
    CopilotPlanV1,
    CopilotSourceReferenceV1,
)
from app.copilot.planner import navigation_destination
from app.copilot.policy import contains_prompt_injection, contains_secret
from app.copilot.sources import (
    CopilotWatchlistMembership,
    TrustedCopilotSources,
    aggregate_source_states,
    extract_saved_symbols,
    freshness_state,
    has_explicit_saved_symbol_hint,
    normalize_source_state,
    parse_datetime,
)
from app.reports.document import EvidencePoint, ReportDocument


@dataclass(frozen=True)
class AgentExecutionContext:
    request_id: str
    question: str
    intent: CopilotIntentV1
    plan: CopilotPlanV1
    client_context: dict[str, Any]

    @property
    def stale_after_seconds(self) -> int:
        return self.plan.freshness_requirements.maximum_age_seconds or 129_600


class CopilotAgentRegistry:
    """Deterministic, read-only adapters over durable application outputs."""

    def __init__(self, sources: TrustedCopilotSources | None = None) -> None:
        self.sources = sources or TrustedCopilotSources()
        self._handlers: dict[CopilotAgentName, Callable[[AgentExecutionContext], AgentResultV1]] = {
            CopilotAgentName.MARKET: self._market,
            CopilotAgentName.INDEX: self._index,
            CopilotAgentName.BREADTH: self._breadth,
            CopilotAgentName.LEADERSHIP: self._leadership,
            CopilotAgentName.SECTOR: self._sector,
            CopilotAgentName.THEME: self._theme,
            CopilotAgentName.MACRO: self._macro,
            CopilotAgentName.RISK: self._risk,
            CopilotAgentName.STOCK: self._stock,
            CopilotAgentName.WATCHLIST: self._watchlist,
            CopilotAgentName.REPORT: self._report,
            CopilotAgentName.RESEARCH: self._research,
            CopilotAgentName.NAVIGATION: self._navigation,
            CopilotAgentName.EDUCATIONAL: self._educational,
            CopilotAgentName.PORTFOLIO: self._portfolio,
        }

    def execute(self, agent: CopilotAgentName | str, context: AgentExecutionContext) -> AgentResultV1:
        name = CopilotAgentName(agent)
        started = perf_counter()
        handler = self._handlers[name]
        try:
            result = handler(context)
        except Exception as exc:
            result = _unavailable_result(
                name,
                warning=f"{name.value} evidence adapter failed safely.",
                failure_category=type(exc).__name__,
            )
        result = result.model_copy(update={"duration_ms": round((perf_counter() - started) * 1000, 3)})
        # Validate against the contract for the requested registry slot, not
        # the self-declared agent name in the returned payload.  Otherwise a
        # miswired handler could return a perfectly valid result for a
        # different agent and bypass the registry boundary.
        contract_validation = validate_agent_result(
            result,
            contract=load_agent_contracts()[name],
        )
        if contract_validation.status == "failed":
            codes = ", ".join(
                dict.fromkeys(issue.code for issue in contract_validation.issues if issue.severity == "error")
            )
            return _unavailable_result(
                name,
                warning=f"{name.value} output failed its Stage 7 validation contract ({codes}).",
                failure_category="agent_contract",
            ).model_copy(update={"duration_ms": result.duration_ms})
        return result

    def _market(self, context: AgentExecutionContext) -> AgentResultV1:
        snapshot = self.sources.market_snapshot()
        if snapshot is None:
            return _unavailable_result(CopilotAgentName.MARKET, warning="No immutable market snapshot is available.")
        freshness = _freshness(
            source_state=snapshot.source_summary.get("source_state"),
            status=snapshot.status,
            generated_at=snapshot.published_at,
            observed_at=snapshot.market_timestamp,
            market_date=(snapshot.market_timestamp or "")[:10] or None,
            expires_at=snapshot.expires_at,
            completeness=snapshot.input_coverage.coverage_ratio,
            provider="market_snapshot",
            warnings=[*snapshot.warnings, *snapshot.missing_dependencies],
            stale_after_seconds=context.stale_after_seconds,
        )
        source = _source(
            dataset="market_snapshot",
            raw_id=snapshot.snapshot_id,
            provider="market_snapshot",
            generated_at=snapshot.published_at,
            market_date=freshness.market_date,
        )
        evidence: list[CopilotEvidenceV1] = []
        observations: list[str] = []
        conclusions: list[str] = []
        health = snapshot.section_payload("health")
        if isinstance(health, dict):
            if health.get("status") is not None:
                evidence.append(_evidence(CopilotEvidenceCategory.MARKET, "US market", "market health classification", health.get("status"), source, freshness, interpretation=CopilotInterpretationClass.ENGINE_CONCLUSION))
            if health.get("overall_score") is not None:
                evidence.append(_evidence(CopilotEvidenceCategory.MARKET, "US market", "market health score", health.get("overall_score"), source, freshness, unit="score / 100"))
            summary = _clean_text(health.get("summary"))
            if summary:
                observations.append(summary)
                conclusions.append(summary)
            for value in list(health.get("improving_factors") or [])[:3]:
                text = _clean_text(value)
                if text:
                    observations.append(text)
            weakening = [_clean_text(value) for value in list(health.get("weakening_factors") or [])[:3]]
            weakening = [value for value in weakening if value]
        else:
            weakening = []
        return _result(
            CopilotAgentName.MARKET,
            freshness,
            evidence=evidence,
            observations=observations,
            conclusions=conclusions,
            contradictions=weakening,
            sources=[source],
            destinations=[CopilotDestination.MARKET_OVERVIEW, CopilotDestination.HEALTH],
            warnings=snapshot.warnings,
        )

    def _index(self, context: AgentExecutionContext) -> AgentResultV1:
        snapshot = self.sources.market_snapshot()
        if snapshot is None:
            return _unavailable_result(CopilotAgentName.INDEX, warning="No immutable index snapshot is available.")
        freshness = _freshness(
            source_state=snapshot.source_summary.get("source_state"), status=snapshot.status,
            generated_at=snapshot.published_at, observed_at=snapshot.market_timestamp,
            market_date=(snapshot.market_timestamp or "")[:10] or None, expires_at=snapshot.expires_at,
            completeness=snapshot.input_coverage.coverage_ratio, provider="market_snapshot:indexes",
            warnings=snapshot.warnings, stale_after_seconds=context.stale_after_seconds,
        )
        source = _source("market_snapshot:indexes", snapshot.snapshot_id, "market_snapshot", snapshot.published_at, freshness.market_date)
        rows = snapshot.section_payload("indexes")
        requested = set(context.intent.ticker_symbols)
        evidence: list[CopilotEvidenceV1] = []
        observations: list[str] = []
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("display_symbol") or row.get("symbol") or "").upper()
            if requested and symbol not in requested:
                continue
            name = str(row.get("display_name") or symbol)
            for metric, key, unit in (
                ("price", "price", None), ("session change", "change_percent", "%"), ("trend", "trend", None),
            ):
                if row.get(key) is not None:
                    evidence.append(_evidence(CopilotEvidenceCategory.INDEX, symbol or name, metric, row.get(key), source, freshness, unit=unit))
            if symbol:
                parts = [f"{symbol}: {row.get('trend') or 'trend unavailable'}"]
                if row.get("change_percent") is not None:
                    parts.append(f"session change {row.get('change_percent')}%")
                observations.append("; ".join(parts) + ".")
        return _result(CopilotAgentName.INDEX, freshness, evidence=evidence, observations=observations, sources=[source], destinations=[CopilotDestination.INDEXES])

    def _breadth(self, context: AgentExecutionContext) -> AgentResultV1:
        snapshot = self.sources.breadth_snapshot()
        if snapshot is None:
            return _unavailable_result(CopilotAgentName.BREADTH, warning="No immutable breadth snapshot is available.")
        coverage = float(snapshot.coverage.get("coverage_ratio") or 0)
        freshness = _freshness(
            source_state=snapshot.source_state, status=snapshot.status, generated_at=snapshot.created_at,
            observed_at=snapshot.latest_input_timestamp, market_date=snapshot.market_date, completeness=coverage,
            provider=",".join(snapshot.providers) or "breadth_snapshot", warnings=[*snapshot.warnings, *snapshot.missing_dependencies],
            stale_after_seconds=context.stale_after_seconds,
        )
        source = _source("breadth_snapshot", snapshot.snapshot_id, ",".join(snapshot.providers) or "breadth_snapshot", snapshot.created_at, snapshot.market_date)
        values = [
            ("breadth score", snapshot.score, "score / 100"),
            ("breadth classification", snapshot.classification, None),
            ("breadth trend", snapshot.trend, None),
            ("percent above 20 EMA", snapshot.moving_average_breadth.get("percent_above_20ema"), "%"),
            ("percent above 50 EMA", snapshot.moving_average_breadth.get("percent_above_50ema"), "%"),
            ("percent above 200 EMA", snapshot.moving_average_breadth.get("percent_above_200ema"), "%"),
            ("advance-decline ratio", snapshot.advance_decline.get("advance_decline_ratio"), None),
        ]
        evidence = [_evidence(CopilotEvidenceCategory.BREADTH, snapshot.universe_id, metric, value, source, freshness, unit=unit) for metric, value, unit in values if value is not None]
        observations = [f"Breadth is {snapshot.classification} with a {snapshot.trend} trend and {snapshot.confidence} engine confidence."]
        contradictions = [str(value.get("description") or value) for value in snapshot.divergences[:4] if value]
        return _result(CopilotAgentName.BREADTH, freshness, evidence=evidence, observations=observations, contradictions=contradictions, sources=[source], destinations=[CopilotDestination.BREADTH], warnings=snapshot.warnings)

    def _sector(self, context: AgentExecutionContext) -> AgentResultV1:
        snapshot = self.sources.sector_snapshot()
        if snapshot is None:
            return _unavailable_result(CopilotAgentName.SECTOR, warning="No immutable sector snapshot is available.")
        return self._ranked_snapshot_result(
            agent=CopilotAgentName.SECTOR, category=CopilotEvidenceCategory.SECTOR,
            dataset="sector_snapshot", raw_id=snapshot.snapshot_id, market_date=snapshot.market_date,
            generated_at=snapshot.generated_at, status=snapshot.status, source_state=snapshot.source_state,
            rows=list(snapshot.sectors), requested=set(context.intent.sectors), id_key="sector_id",
            summary=snapshot.rotation_summary, rankings=list(snapshot.rankings), warnings=list(snapshot.warnings),
            completeness=float(snapshot.coverage.get("constituent_coverage_ratio") or 0),
            destination=CopilotDestination.SECTOR_DETAIL, stale_after_seconds=context.stale_after_seconds,
        )

    def _theme(self, context: AgentExecutionContext) -> AgentResultV1:
        snapshot = self.sources.theme_snapshot()
        if snapshot is None:
            return _unavailable_result(CopilotAgentName.THEME, warning="No immutable theme snapshot is available.")
        return self._ranked_snapshot_result(
            agent=CopilotAgentName.THEME, category=CopilotEvidenceCategory.THEME,
            dataset="theme_snapshot", raw_id=snapshot.snapshot_id, market_date=snapshot.market_date,
            generated_at=snapshot.generated_at, status=snapshot.status, source_state=snapshot.source_state,
            rows=list(snapshot.rows), requested=set(context.intent.themes), id_key="theme_id",
            summary=snapshot.rotation_summary, rankings=list(snapshot.rankings), warnings=list(snapshot.warnings),
            completeness=float(snapshot.member_coverage.get("coverage_ratio") or snapshot.member_coverage.get("member_coverage_ratio") or 0),
            destination=CopilotDestination.THEME_DETAIL, stale_after_seconds=context.stale_after_seconds,
        )

    def _leadership(self, context: AgentExecutionContext) -> AgentResultV1:
        # Sector leadership is sourced from the reviewed sector ranking.  This
        # supports taxonomy-level questions without fabricating an entity.
        snapshot = self.sources.sector_snapshot()
        if snapshot is None:
            return _unavailable_result(CopilotAgentName.LEADERSHIP, warning="No immutable leadership snapshot is available.")
        freshness = _freshness(
            source_state=snapshot.source_state, status=snapshot.status, generated_at=snapshot.generated_at,
            market_date=snapshot.market_date, completeness=float(snapshot.coverage.get("constituent_coverage_ratio") or 0),
            provider="sector_snapshot", warnings=snapshot.warnings, stale_after_seconds=context.stale_after_seconds,
        )
        source = _source("sector_snapshot:leadership", snapshot.snapshot_id, "sector_snapshot", snapshot.generated_at, snapshot.market_date)
        rows_by_id = {str(row.get("sector_id")): row for row in snapshot.sectors}
        evidence: list[CopilotEvidenceV1] = []
        observations = [snapshot.rotation_summary] if snapshot.rotation_summary else []
        for rank, sector_id in enumerate(snapshot.rankings[:5], start=1):
            row = rows_by_id.get(str(sector_id), {})
            display = str(row.get("display_name") or sector_id)
            evidence.append(_evidence(CopilotEvidenceCategory.LEADERSHIP, str(sector_id), "leadership rank", rank, source, freshness, current_state=str(row.get("classification") or "unclassified"), interpretation=CopilotInterpretationClass.ENGINE_CONCLUSION))
            if row.get("composite_score") is not None:
                evidence.append(_evidence(CopilotEvidenceCategory.LEADERSHIP, str(sector_id), "sector composite score", row.get("composite_score"), source, freshness, unit="score / 100"))
            observations.append(f"#{rank} {display}: {row.get('classification') or 'unclassified'}.")
        return _result(CopilotAgentName.LEADERSHIP, freshness, evidence=evidence, observations=observations, sources=[source], destinations=[CopilotDestination.LEADERSHIP], warnings=snapshot.warnings)

    def _ranked_snapshot_result(
        self, *, agent: CopilotAgentName, category: CopilotEvidenceCategory, dataset: str,
        raw_id: str, market_date: str, generated_at: str, status: str, source_state: str,
        rows: list[dict[str, Any]], requested: set[str], id_key: str, summary: str,
        rankings: list[str], warnings: list[str], completeness: float,
        destination: CopilotDestination, stale_after_seconds: int,
    ) -> AgentResultV1:
        freshness = _freshness(source_state=source_state, status=status, generated_at=generated_at, market_date=market_date, completeness=completeness, provider=dataset, warnings=warnings, stale_after_seconds=stale_after_seconds)
        source = _source(dataset, raw_id, dataset, generated_at, market_date)
        evidence: list[CopilotEvidenceV1] = []
        observations = [summary] if summary else []
        selected = [row for row in rows if not requested or str(row.get(id_key)) in requested]
        if not requested:
            order = {value: index for index, value in enumerate(rankings)}
            selected = sorted(selected, key=lambda row: order.get(str(row.get(id_key)), 999))[:5]
        for row in selected[:8]:
            entity = str(row.get(id_key) or row.get("display_name") or "unknown")
            display = str(row.get("display_name") or entity)
            rank = row.get("rank")
            classification = row.get("classification")
            score = row.get("composite_score")
            if rank is not None:
                evidence.append(_evidence(category, entity, "rank", rank, source, freshness, current_state=str(classification or "unclassified"), interpretation=CopilotInterpretationClass.ENGINE_CONCLUSION))
            if score is not None:
                evidence.append(_evidence(category, entity, "composite score", score, source, freshness, unit="score / 100"))
            if classification is not None:
                evidence.append(_evidence(category, entity, "classification", classification, source, freshness, interpretation=CopilotInterpretationClass.ENGINE_CONCLUSION))
            observations.append(f"{display}: rank {rank if rank is not None else 'unavailable'}, {classification or 'classification unavailable'}.")
        return _result(agent, freshness, evidence=evidence, observations=observations, sources=[source], destinations=[destination], warnings=warnings)

    def _macro(self, context: AgentExecutionContext) -> AgentResultV1:
        document = self.sources.latest_report_document()
        if document is None:
            return _unavailable_result(CopilotAgentName.MACRO, warning="No validated report evidence is available for macro context.")
        evidence = self._report_evidence(document, context, CopilotEvidenceCategory.MACRO, keywords={"rate", "yield", "treasury", "oil", "dollar", "gold", "credit", "macro", "inflation"})
        freshness, source = _report_freshness_and_source(document, context.stale_after_seconds)
        conclusions = [claim.statement for claim in document.claims if _matches_keywords(claim.statement, {"rate", "yield", "oil", "dollar", "credit", "macro"})][:4]
        missing = [] if evidence else ["No registered macro evidence matched the request."]
        return _result(CopilotAgentName.MACRO, freshness, evidence=evidence, conclusions=conclusions, sources=[source], destinations=[CopilotDestination.MACRO], missing=missing)

    def _risk(self, context: AgentExecutionContext) -> AgentResultV1:
        document = self.sources.latest_report_document()
        if document is None:
            return _unavailable_result(CopilotAgentName.RISK, warning="No validated report risk evidence is available.")
        freshness, source = _report_freshness_and_source(document, context.stale_after_seconds)
        evidence = self._report_evidence(document, context, CopilotEvidenceCategory.RISK, keywords={"risk", "volatility", "invalidate", "breadth", "drawdown", "support"})
        levels: list[CopilotLevelV1] = []
        for index, statement in enumerate(document.thesis.invalidation_conditions[:5], start=1):
            item = _evidence(
                CopilotEvidenceCategory.RISK,
                "report thesis",
                "stored thesis invalidation condition",
                statement,
                source,
                freshness,
                interpretation=CopilotInterpretationClass.CONTRADICTION,
                report_reference=f"{document.report_id}:thesis:invalidation:{index}",
                contradicts_claim_ids=["report-thesis"],
            )
            evidence.append(item)
            levels.append(CopilotLevelV1(label="Report thesis invalidation condition", value=statement, evidence_id=item.evidence_id))
        conclusions = [condition.rationale for condition in document.monitoring_conditions[:5]]
        contradictions = list(document.thesis.invalidation_conditions[:5])
        observations = [f"Report posture: {document.thesis.posture}.", document.thesis.concise_thesis]
        return _result(CopilotAgentName.RISK, freshness, evidence=evidence, observations=observations, conclusions=conclusions, contradictions=contradictions, levels=levels, sources=[source], destinations=[CopilotDestination.HEALTH, CopilotDestination.REPORT_SCENARIOS], warnings=document.limitations)

    def _report(self, context: AgentExecutionContext) -> AgentResultV1:
        document = self.sources.latest_report_document()
        if document is None:
            return _unavailable_result(CopilotAgentName.REPORT, warning="No validated ReportDocument is available.")
        freshness, source = _report_freshness_and_source(document, context.stale_after_seconds)
        evidence = self._report_evidence(document, context, CopilotEvidenceCategory.REPORT)
        conclusions = [document.thesis.concise_thesis, *[claim.statement for claim in document.claims[:4]]]
        contradictions = [claim.statement for claim in document.claims if claim.counter_evidence_ids][:3]
        levels: list[CopilotLevelV1] = []
        missing: list[str] = []
        if context.intent.sub_intent == "report_change":
            if document.previous_report_available and document.thesis.previous_thesis:
                change = _evidence(
                    CopilotEvidenceCategory.REPORT,
                    "report thesis",
                    "stored change since previous report",
                    document.thesis.thesis_change,
                    source,
                    freshness,
                    interpretation=CopilotInterpretationClass.ENGINE_CONCLUSION,
                    report_reference=f"{document.report_id}:thesis:change",
                    supports_claim_ids=["report-thesis-change"],
                )
                evidence.append(change)
                conclusions = [document.thesis.thesis_change, document.thesis.concise_thesis]
            else:
                missing.append("No prior immutable report is available, so no change narrative can be validated.")
        if context.intent.intent == "SCENARIO_QUERY" and document.scenarios:
            conclusions = [f"{scenario.label}: requires {'; '.join(scenario.required_conditions[:3])}." for scenario in document.scenarios[:3]]
            contradictions = [value for scenario in document.scenarios[:3] for value in scenario.invalidation[:2]]
            for scenario in document.scenarios[:3]:
                for index, statement in enumerate(scenario.required_conditions[:3], start=1):
                    item = _evidence(
                        CopilotEvidenceCategory.REPORT,
                        scenario.scenario_id,
                        "stored scenario required condition",
                        statement,
                        source,
                        freshness,
                        interpretation=CopilotInterpretationClass.ENGINE_CONCLUSION,
                        report_reference=f"{document.report_id}:{scenario.scenario_id}:required:{index}",
                        supports_claim_ids=[scenario.scenario_id],
                    )
                    evidence.append(item)
                    levels.append(CopilotLevelV1(label="Scenario confirmation condition", value=statement, evidence_id=item.evidence_id))
                for index, statement in enumerate(scenario.invalidation[:2], start=1):
                    item = _evidence(
                        CopilotEvidenceCategory.REPORT,
                        scenario.scenario_id,
                        "stored scenario invalidation condition",
                        statement,
                        source,
                        freshness,
                        interpretation=CopilotInterpretationClass.CONTRADICTION,
                        report_reference=f"{document.report_id}:{scenario.scenario_id}:invalidation:{index}",
                        contradicts_claim_ids=[scenario.scenario_id],
                    )
                    evidence.append(item)
                    levels.append(CopilotLevelV1(label="Scenario invalidation condition", value=statement, evidence_id=item.evidence_id))
        else:
            for index, statement in enumerate(document.thesis.confirmation_conditions[:3], start=1):
                item = _evidence(
                    CopilotEvidenceCategory.REPORT,
                    "report thesis",
                    "stored thesis confirmation condition",
                    statement,
                    source,
                    freshness,
                    interpretation=CopilotInterpretationClass.ENGINE_CONCLUSION,
                    report_reference=f"{document.report_id}:thesis:confirmation:{index}",
                    supports_claim_ids=["report-thesis"],
                )
                evidence.append(item)
                levels.append(CopilotLevelV1(label="Report thesis confirmation condition", value=statement, evidence_id=item.evidence_id))
            for index, statement in enumerate(document.thesis.invalidation_conditions[:3], start=1):
                item = _evidence(
                    CopilotEvidenceCategory.REPORT,
                    "report thesis",
                    "stored thesis invalidation condition",
                    statement,
                    source,
                    freshness,
                    interpretation=CopilotInterpretationClass.CONTRADICTION,
                    report_reference=f"{document.report_id}:thesis:invalidation:{index}",
                    contradicts_claim_ids=["report-thesis"],
                )
                evidence.append(item)
                levels.append(CopilotLevelV1(label="Report thesis invalidation condition", value=statement, evidence_id=item.evidence_id))
        return _result(CopilotAgentName.REPORT, freshness, evidence=evidence, observations=[f"Report date: {document.market_date}."], conclusions=conclusions, contradictions=contradictions, levels=levels, sources=[source], destinations=[CopilotDestination.REPORT], warnings=document.limitations, missing=missing)

    def _research(self, context: AgentExecutionContext) -> AgentResultV1:
        document = self.sources.latest_report_document()
        if document is None or document.research_focus is None:
            return _unavailable_result(CopilotAgentName.RESEARCH, warning="No qualified Research Focus is available in the latest report.")
        focus = document.research_focus
        freshness, source = _report_freshness_and_source(document, context.stale_after_seconds)
        wanted = set(focus.evidence_ids)
        evidence = self._report_evidence(document, context, CopilotEvidenceCategory.RESEARCH, explicit_ids=wanted, limit=12)
        focus_claim_id = f"research-focus:{focus.candidate_id}"
        evidence = [
            item.model_copy(update={"supports_claim_ids": list(dict.fromkeys([*item.supports_claim_ids, focus_claim_id]))})
            for item in evidence
        ]
        selection_evidence: list[CopilotEvidenceV1] = []
        for index, statement in enumerate(focus.why_selected[:5], start=1):
            selection_evidence.append(
                _evidence(
                    CopilotEvidenceCategory.RESEARCH,
                    focus.subject,
                    "stored Research Focus selection reason",
                    statement,
                    source,
                    freshness,
                    interpretation=CopilotInterpretationClass.ENGINE_CONCLUSION,
                    report_reference=f"{document.report_id}:{focus.candidate_id}:selection:{index}",
                    supports_claim_ids=[focus_claim_id],
                )
            )
        evidence = [*selection_evidence, *evidence]
        levels: list[CopilotLevelV1] = []
        counter = _evidence(
            CopilotEvidenceCategory.RESEARCH,
            focus.subject,
            "stored Research Focus counter-thesis",
            focus.counter_thesis,
            source,
            freshness,
            interpretation=CopilotInterpretationClass.CONTRADICTION,
            report_reference=f"{document.report_id}:{focus.candidate_id}:counter-thesis",
            contradicts_claim_ids=[focus_claim_id],
        )
        evidence.append(counter)
        for index, statement in enumerate(focus.confirmation_conditions[:5], start=1):
            item = _evidence(
                CopilotEvidenceCategory.RESEARCH,
                focus.subject,
                "stored Research Focus confirmation condition",
                statement,
                source,
                freshness,
                interpretation=CopilotInterpretationClass.ENGINE_CONCLUSION,
                report_reference=f"{document.report_id}:{focus.candidate_id}:confirmation:{index}",
                supports_claim_ids=[focus_claim_id],
            )
            evidence.append(item)
            levels.append(CopilotLevelV1(label="Research Focus confirmation condition", value=statement, evidence_id=item.evidence_id))
        for index, statement in enumerate(focus.invalidation_conditions[:5], start=1):
            item = _evidence(
                CopilotEvidenceCategory.RESEARCH,
                focus.subject,
                "stored Research Focus invalidation condition",
                statement,
                source,
                freshness,
                interpretation=CopilotInterpretationClass.CONTRADICTION,
                report_reference=f"{document.report_id}:{focus.candidate_id}:invalidation:{index}",
                contradicts_claim_ids=[focus_claim_id],
            )
            evidence.append(item)
            levels.append(CopilotLevelV1(label="Research Focus invalidation condition", value=statement, evidence_id=item.evidence_id))
        conclusions = [focus.executive_answer, focus.main_thesis, *focus.execution_implications[:3]]
        contradictions = [focus.counter_thesis, *focus.invalidation_conditions[:3]]
        observations = [focus.question, *focus.key_evidence[:3]]
        return _result(CopilotAgentName.RESEARCH, freshness, evidence=evidence, observations=observations, conclusions=conclusions, contradictions=contradictions, levels=levels, sources=[source], destinations=[CopilotDestination.REPORT_RESEARCH_FOCUS], warnings=document.limitations)

    def _stock(self, context: AgentExecutionContext) -> AgentResultV1:
        symbols = list(context.intent.ticker_symbols)
        if not symbols and context.intent.intent == "WATCHLIST_REVIEW":
            membership = self._watchlist_membership(context)
            symbols = list(membership.symbols or ())
        if not symbols:
            return _unavailable_result(CopilotAgentName.STOCK, warning="No validated stock symbol was supplied for stock evidence.")
        results = [self._one_stock(symbol, context) for symbol in symbols[:10]]
        evidence = [item for result in results for item in result.evidence]
        observations = [item for result in results for item in result.observations]
        conclusions = [item for result in results for item in result.conclusions]
        contradictions = [item for result in results for item in result.contradictions]
        levels = [item for result in results for item in result.levels]
        sources = _dedupe_sources(item for result in results for item in result.source_references)
        warnings = list(dict.fromkeys(item for result in results for item in result.warnings))
        missing = list(dict.fromkeys(item for result in results for item in result.missing_data))
        freshness = _merge_freshness([result.freshness for result in results])
        return _result(CopilotAgentName.STOCK, freshness, evidence=evidence, observations=observations, conclusions=conclusions, contradictions=contradictions, levels=levels, sources=sources, destinations=[CopilotDestination.STOCK_DETAIL, CopilotDestination.STOCK_TECHNICAL, CopilotDestination.STOCK_RISK], warnings=warnings, missing=missing)

    def _one_stock(self, symbol: str, context: AgentExecutionContext) -> AgentResultV1:
        snapshot = self.sources.stock_snapshot(symbol)
        if snapshot is None:
            return _unavailable_result(CopilotAgentName.STOCK, warning=f"No immutable stock snapshot is available for {symbol}.")
        freshness = _freshness(
            source_state=snapshot.source_state, status=snapshot.status, generated_at=snapshot.published_at,
            observed_at=snapshot.latest_history_timestamp, market_date=snapshot.latest_history_date,
            expires_at=snapshot.expires_at, completeness=snapshot.coverage_ratio,
            provider="stock_snapshot", warnings=[*snapshot.warnings, *snapshot.missing_dependencies],
            test=snapshot.test_data or snapshot.mock_data, stale_after_seconds=context.stale_after_seconds,
        )
        source = _source("stock_snapshot", snapshot.snapshot_id, "stock_snapshot", snapshot.published_at, snapshot.latest_history_date)
        evidence: list[CopilotEvidenceV1] = []
        observations: list[str] = []
        conclusions: list[str] = []
        contradictions: list[str] = []
        levels: list[CopilotLevelV1] = []
        rating = snapshot.section_payload("rating")
        assessment = snapshot.section_payload("overall_assessment")
        summary = snapshot.section_payload("executive_summary")
        if isinstance(rating, dict):
            for metric, key, unit in (("setup rating", "rating", None), ("setup score", "overall_score", "score / 100"), ("risk level", "risk_level", None), ("setup status", "status", None)):
                if rating.get(key) is not None:
                    evidence.append(_evidence(CopilotEvidenceCategory.TECHNICAL, symbol, metric, rating.get(key), source, freshness, unit=unit, interpretation=CopilotInterpretationClass.ENGINE_CONCLUSION))
            explanation = _clean_text(rating.get("explanation"))
            if explanation:
                conclusions.append(explanation)
            contradictions.extend(_clean_text(value) for value in list(rating.get("warnings") or []) if _clean_text(value))
        elif isinstance(assessment, dict):
            for metric, key in (("setup score", "score"), ("setup status", "status")):
                if assessment.get(key) is not None:
                    evidence.append(_evidence(CopilotEvidenceCategory.TECHNICAL, symbol, metric, assessment.get(key), source, freshness, interpretation=CopilotInterpretationClass.ENGINE_CONCLUSION))
        if isinstance(summary, dict):
            body = _clean_text(summary.get("body"))
            if body and body not in conclusions:
                conclusions.append(body)
        technical = snapshot.section_payload("technical")
        if isinstance(technical, dict):
            for metric, key, unit in (("current price", "current_price", None), ("20-session return", "return_20d", "%"), ("RSI 14", "rsi_14", None), ("EMA 20", "ema_20", None), ("EMA 50", "ema_50", None)):
                if technical.get(key) is not None:
                    evidence.append(_evidence(CopilotEvidenceCategory.TECHNICAL, symbol, metric, technical.get(key), source, freshness, unit=unit))
        for section_name, category in (("trend", CopilotEvidenceCategory.TECHNICAL), ("volume", CopilotEvidenceCategory.SIGNAL), ("relative_strength", CopilotEvidenceCategory.LEADERSHIP)):
            payload = snapshot.section_payload(section_name)
            if not isinstance(payload, dict):
                continue
            text = _clean_text(payload.get("summary") or payload.get("explanation"))
            if text:
                observations.append(text)
            value = payload.get("status") or payload.get("signal") or payload.get("volume_quality")
            if value is not None:
                evidence.append(_evidence(category, symbol, f"{section_name.replace('_', ' ')} state", value, source, freshness, interpretation=CopilotInterpretationClass.ENGINE_CONCLUSION))
        support = snapshot.section_payload("support_resistance")
        if isinstance(support, dict):
            for label, key in (("current price", "current_price"), ("confirmation level", "breakout_level"), ("risk reference", "stop_reference")):
                if support.get(key) is None:
                    continue
                item = _evidence(CopilotEvidenceCategory.TECHNICAL, symbol, label, support.get(key), source, freshness)
                evidence.append(item)
                levels.append(CopilotLevelV1(label=f"{symbol} {label}", value=support.get(key), evidence_id=item.evidence_id))
        missing = list(snapshot.missing_dependencies)
        return _result(CopilotAgentName.STOCK, freshness, evidence=evidence, observations=observations, conclusions=conclusions, contradictions=contradictions, levels=levels, sources=[source], warnings=snapshot.warnings, missing=missing)

    def _watchlist(self, context: AgentExecutionContext) -> AgentResultV1:
        membership = self._watchlist_membership(context)
        if membership.symbols is None:
            return _unavailable_result(
                CopilotAgentName.WATCHLIST,
                warning=membership.limitation or "Saved-list membership is unavailable in this context.",
            )
        symbols = list(membership.symbols)
        warning = membership.limitation or ""
        freshness = CopilotFreshnessV1(
            state=CopilotFreshnessState.CACHED,
            generated_at=datetime.now(timezone.utc).isoformat(),
            completeness=1,
            provider=membership.provider,
            warnings=[warning] if warning else [],
        )
        source = _source(
            "saved_membership",
            membership.source_id,
            membership.provider,
            freshness.generated_at,
            None,
        )
        if not symbols:
            return _result(
                CopilotAgentName.WATCHLIST,
                freshness,
                observations=["The saved-symbol list is confirmed empty."],
                conclusions=["There are no saved stocks to review."],
                metrics={"membership_state": "empty", "membership_scope": membership.scope},
                sources=[source],
                destinations=[CopilotDestination.WATCHLIST],
                warnings=[warning] if warning else [],
            )
        evidence = [
            _evidence(
                CopilotEvidenceCategory.WATCHLIST,
                symbol,
                "saved membership",
                "saved",
                source,
                freshness,
            )
            for symbol in symbols[:50]
        ]
        return _result(
            CopilotAgentName.WATCHLIST,
            freshness,
            evidence=evidence,
            observations=[f"Saved list contains {len(symbols)} validated symbol identifier(s)."],
            metrics={"membership_state": "available", "membership_scope": membership.scope},
            sources=[source],
            destinations=[CopilotDestination.WATCHLIST],
            warnings=[warning] if warning else [],
        )

    def _watchlist_membership(self, context: AgentExecutionContext) -> CopilotWatchlistMembership:
        if has_explicit_saved_symbol_hint(context.client_context):
            return CopilotWatchlistMembership(
                symbols=tuple(extract_saved_symbols(context.client_context)),
                scope="device_local",
                provider="client_local_membership",
                source_id=f"membership-{context.request_id}",
                limitation=(
                    "Saved-list membership came from this device's local app context; "
                    "backend account scoping is not available."
                ),
            )
        return self.sources.watchlist_membership()

    def _navigation(self, context: AgentExecutionContext) -> AgentResultV1:
        target = navigation_destination(context.intent.sub_intent)
        freshness = CopilotFreshnessV1(state=CopilotFreshnessState.LIVE, generated_at=datetime.now(timezone.utc).isoformat(), completeness=1, provider="route_registry")
        return _result(CopilotAgentName.NAVIGATION, freshness, conclusions=[f"Open the registered {target.value} destination."], destinations=[target])

    def _educational(self, context: AgentExecutionContext) -> AgentResultV1:
        lowered = context.question.casefold()
        glossary = {
            "breadth": "Market breadth describes how widely a market move is shared across the reviewed security universe.",
            "relative strength": "Relative strength compares a security's observed performance with a benchmark over the same period.",
            "rotation": "Rotation is a change in relative leadership among sectors, themes, or groups.",
            "support": "Support is an observed price area where prior demand has appeared; it is a reference, not a guarantee.",
            "resistance": "Resistance is an observed price area where prior supply has appeared; it is a reference, not a guarantee.",
            "volume": "Volume measures traded activity and can help assess whether participation confirms a price move.",
        }
        answer = next((definition for term, definition in glossary.items() if term in lowered), "I can explain breadth, relative strength, rotation, support, resistance, or volume using the app's terminology.")
        # A bounded definition makes no live-market claim, so market-data
        # freshness is intentionally unavailable rather than mislabeled live.
        freshness = CopilotFreshnessV1(state=CopilotFreshnessState.UNAVAILABLE, generated_at=datetime.now(timezone.utc).isoformat(), completeness=1, provider="copilot_glossary")
        return _result(CopilotAgentName.EDUCATIONAL, freshness, conclusions=[answer])

    def _portfolio(self, context: AgentExecutionContext) -> AgentResultV1:
        freshness = CopilotFreshnessV1(state=CopilotFreshnessState.UNAVAILABLE, generated_at=datetime.now(timezone.utc).isoformat(), completeness=0, provider="unavailable")
        return _result(CopilotAgentName.PORTFOLIO, freshness, conclusions=["Portfolio holdings are not yet connected. I can analyse your watchlist and saved themes instead."], missing=["Portfolio holdings are not connected."], destinations=[CopilotDestination.WATCHLIST])

    def _report_evidence(
        self,
        document: ReportDocument,
        context: AgentExecutionContext,
        category: CopilotEvidenceCategory,
        *,
        keywords: set[str] | None = None,
        explicit_ids: set[str] | None = None,
        limit: int = 8,
    ) -> list[CopilotEvidenceV1]:
        terms = {term for term in re.findall(r"[a-z0-9]+", context.question.casefold()) if len(term) > 3}
        source_map = {item.source_id: item for item in document.sources}
        support_map: dict[str, list[str]] = {}
        contradiction_map: dict[str, list[str]] = {}
        for claim in document.claims:
            for evidence_id in claim.evidence_ids:
                support_map.setdefault(evidence_id, []).append(claim.claim_id)
            for evidence_id in claim.counter_evidence_ids:
                contradiction_map.setdefault(evidence_id, []).append(claim.claim_id)
        rows = list(document.evidence)
        if explicit_ids is not None:
            rows = [item for item in rows if item.evidence_id in explicit_ids]
        elif keywords:
            rows = [item for item in rows if _matches_keywords(item.metric, keywords)]
        elif terms:
            scored = sorted(rows, key=lambda item: sum(term in item.metric.casefold() for term in terms), reverse=True)
            if scored and any(sum(term in item.metric.casefold() for term in terms) for item in scored):
                rows = scored
        result: list[CopilotEvidenceV1] = []
        for item in rows[:limit]:
            registered = source_map.get(item.source_id)
            provider = registered.provider if registered else "report_registry"
            source = _source(
                dataset=registered.dataset if registered else "report_evidence",
                raw_id=item.source_id,
                provider=provider,
                # Source identity belongs to the immutable registered source,
                # while the evidence point below retains its own observation
                # timestamp in freshness.  Mixing those timestamps under one
                # source ID creates conflicting lineage across report rows.
                generated_at=(registered.timestamp if registered else None) or document.generated_at,
                market_date=document.market_date,
            )
            item_state = normalize_source_state(item.freshness)
            freshness = _freshness(
                source_state=item_state, status=document.source_status, generated_at=item.timestamp or document.generated_at,
                market_date=document.market_date, completeness=document.thesis.data_completeness, provider=provider,
                warnings=document.limitations, stale_after_seconds=context.stale_after_seconds,
            )
            result.append(
                _evidence(
                    category, "latest report", item.metric, item.current_value, source, freshness,
                    prior=item.previous_value, change=item.change, unit=item.unit, timeframe=item.timeframe,
                    report_reference=f"{document.report_id}:{item.evidence_id}",
                    supports_claim_ids=support_map.get(item.evidence_id, []),
                    contradicts_claim_ids=contradiction_map.get(item.evidence_id, []),
                )
            )
        return result


def _source(dataset: str, raw_id: str, provider: str, generated_at: str | None, market_date: str | None) -> CopilotSourceReferenceV1:
    safe_dataset = _safe_data_label(dataset, "retrieved_dataset")
    safe_provider = _safe_data_label(provider, "retrieved_provider")
    return CopilotSourceReferenceV1(
        source_id=f"src-{_digest(safe_dataset, raw_id)[:16]}",
        provider=safe_provider or "unavailable",
        dataset=safe_dataset,
        generated_at=generated_at,
        market_date=(market_date or "")[:10] or None,
        raw_engine_reference=raw_id,
    )


def _freshness(
    *, source_state: Any, status: Any, generated_at: str | None,
    observed_at: str | None = None, market_date: str | None = None,
    expires_at: str | None = None, completeness: float = 0,
    provider: str = "unavailable", warnings: Iterable[str] = (), test: bool = False,
    stale_after_seconds: int = 129_600,
) -> CopilotFreshnessV1:
    state = freshness_state(source_state=source_state, status=status, expires_at=expires_at, test_data=test)
    timestamp = parse_datetime(observed_at) or parse_datetime(generated_at)
    age: float | None = None
    if timestamp is not None:
        age = max(0, (datetime.now(timezone.utc) - timestamp).total_seconds())
        if state not in {"test", "unavailable"} and age > stale_after_seconds:
            state = "stale"
    return CopilotFreshnessV1(
        state=state,
        market_date=(market_date or "")[:10] or None,
        generated_at=generated_at,
        observed_at=observed_at,
        expires_at=expires_at,
        age_seconds=round(age, 3) if age is not None else None,
        completeness=max(0, min(1, float(completeness or 0))),
        provider=provider,
        warnings=list(dict.fromkeys(_safe_note(value) for value in warnings if value)),
    )


def _report_freshness_and_source(document: ReportDocument, stale_after_seconds: int) -> tuple[CopilotFreshnessV1, CopilotSourceReferenceV1]:
    freshness = _freshness(
        source_state=document.source_status, status="complete", generated_at=document.generated_at,
        observed_at=document.data_cutoff, market_date=document.market_date,
        completeness=document.thesis.data_completeness, provider="ReportDocument",
        warnings=document.limitations, stale_after_seconds=stale_after_seconds,
    )
    return freshness, _source("ReportDocument", document.report_id, "ReportDocument", document.generated_at, document.market_date)


def _evidence(
    category: CopilotEvidenceCategory,
    entity: str,
    metric: str,
    value: Any,
    source: CopilotSourceReferenceV1,
    freshness: CopilotFreshnessV1,
    *,
    unit: str | None = None,
    current_state: str | None = None,
    prior: Any = None,
    change: Any = None,
    timeframe: str = "current",
    interpretation: CopilotInterpretationClass = CopilotInterpretationClass.OBSERVED_FACT,
    confidence: CopilotConfidenceLabel = CopilotConfidenceLabel.MODERATE,
    report_reference: str | None = None,
    supports_claim_ids: list[str] | None = None,
    contradicts_claim_ids: list[str] | None = None,
) -> CopilotEvidenceV1:
    unsafe = any(_contains_unsafe_data(item) for item in (entity, metric, value, current_state, prior, change, unit))
    safe_entity = _safe_data_label(entity, "retrieved source")
    safe_metric = _safe_data_label(metric, "retrieved field omitted by safety policy")
    safe_value = "[untrusted retrieved text omitted]" if unsafe else value
    safe_current_state = None if unsafe else current_state
    safe_prior = None if unsafe else prior
    safe_change = None if unsafe else change
    safe_unit = None if unsafe else unit
    if unsafe:
        interpretation = CopilotInterpretationClass.MISSING_EVIDENCE
        supports_claim_ids = []
        contradicts_claim_ids = []
    evidence_id = f"ev-{_digest(source.source_id, safe_entity, safe_metric, safe_value)[:20]}"
    return CopilotEvidenceV1(
        evidence_id=evidence_id,
        category=category,
        entity=safe_entity,
        metric=safe_metric,
        value=safe_value,
        unit=safe_unit,
        current_state=safe_current_state,
        prior_value=safe_prior,
        change=safe_change,
        timeframe=timeframe or "current",
        interpretation_class=interpretation,
        source=source,
        freshness=freshness,
        confidence=confidence,
        report_reference=report_reference,
        supports_claim_ids=supports_claim_ids or [],
        contradicts_claim_ids=contradicts_claim_ids or [],
    )


def _result(
    agent: CopilotAgentName,
    freshness: CopilotFreshnessV1,
    *,
    evidence: list[CopilotEvidenceV1] | None = None,
    observations: list[str] | None = None,
    conclusions: list[str] | None = None,
    contradictions: list[str] | None = None,
    levels: list[CopilotLevelV1] | None = None,
    metrics: dict[str, Any] | None = None,
    sources: list[CopilotSourceReferenceV1] | None = None,
    destinations: list[CopilotDestination] | None = None,
    warnings: Iterable[str] = (),
    missing: Iterable[str] = (),
) -> AgentResultV1:
    state = CopilotFreshnessState(freshness.state)
    status = {
        CopilotFreshnessState.STALE: CopilotAgentStatus.STALE,
        CopilotFreshnessState.UNAVAILABLE: CopilotAgentStatus.UNAVAILABLE,
        CopilotFreshnessState.PARTIAL: CopilotAgentStatus.PARTIAL,
        CopilotFreshnessState.MIXED: CopilotAgentStatus.PARTIAL,
        CopilotFreshnessState.TEST: CopilotAgentStatus.PARTIAL,
    }.get(state, CopilotAgentStatus.COMPLETE)
    return AgentResultV1(
        agent=agent,
        status=status,
        observations=[value for value in (observations or []) if value],
        conclusions=[value for value in (conclusions or []) if value],
        contradictions=[value for value in (contradictions or []) if value],
        metrics=metrics or {},
        levels=levels or [],
        source_references=sources or [],
        evidence=_dedupe_agent_evidence(evidence or []),
        freshness=freshness,
        deep_link_targets=destinations or [],
        warnings=list(dict.fromkeys(_safe_note(value) for value in warnings if value)),
        missing_data=list(dict.fromkeys(_safe_note(value) for value in missing if value)),
    )


def _unavailable_result(agent: CopilotAgentName, *, warning: str, failure_category: str | None = None) -> AgentResultV1:
    return AgentResultV1(
        agent=agent,
        status=CopilotAgentStatus.FAILED if failure_category else CopilotAgentStatus.UNAVAILABLE,
        freshness=CopilotFreshnessV1(state=CopilotFreshnessState.UNAVAILABLE, completeness=0, provider="unavailable", warnings=[warning]),
        warnings=[warning],
        missing_data=[warning],
        failure_category=failure_category,
    )


def _merge_freshness(values: list[CopilotFreshnessV1]) -> CopilotFreshnessV1:
    if not values:
        return CopilotFreshnessV1(state=CopilotFreshnessState.UNAVAILABLE, completeness=0, provider="unavailable")
    return CopilotFreshnessV1(
        state=aggregate_source_states(value.state for value in values),
        market_date=max((value.market_date for value in values if value.market_date), default=None),
        generated_at=max((value.generated_at for value in values if value.generated_at), default=None),
        age_seconds=max((value.age_seconds for value in values if value.age_seconds is not None), default=None),
        completeness=min(value.completeness for value in values),
        provider=",".join(dict.fromkeys(value.provider for value in values)),
        warnings=list(dict.fromkeys(warning for value in values for warning in value.warnings)),
    )


def _dedupe_sources(values: Iterable[CopilotSourceReferenceV1]) -> list[CopilotSourceReferenceV1]:
    result: dict[str, CopilotSourceReferenceV1] = {}
    for value in values:
        result[value.source_id] = value
    return list(result.values())


def _dedupe_agent_evidence(values: Iterable[CopilotEvidenceV1]) -> list[CopilotEvidenceV1]:
    result: dict[str, CopilotEvidenceV1] = {}
    for value in values:
        result.setdefault(value.evidence_id, value)
    return list(result.values())


def _digest(*values: Any) -> str:
    payload = json.dumps(values, sort_keys=True, default=str, ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _matches_keywords(value: str, keywords: set[str]) -> bool:
    lowered = value.casefold()
    return any(keyword in lowered for keyword in keywords)


def _contains_unsafe_data(value: Any) -> bool:
    try:
        text = json.dumps(value, sort_keys=True, default=str, ensure_ascii=True)
    except (TypeError, ValueError):
        text = str(value or "")
    return contains_prompt_injection(text) or contains_secret(text)


def _safe_note(value: Any) -> str:
    if _contains_unsafe_data(value):
        return "Untrusted source text was omitted by safety policy."
    return _clean_text(value)[:500]


def _safe_data_label(value: Any, fallback: str) -> str:
    text = _clean_text(value)
    if not text or _contains_unsafe_data(text):
        return fallback
    return text[:160]
