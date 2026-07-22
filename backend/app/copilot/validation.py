from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

from app.copilot.actions import get_registered_action, is_registered_route
from app.copilot.contracts import (
    CopilotActionType,
    CopilotActionV1,
    CopilotConfidenceLabel,
    CopilotDestination,
    CopilotEvidenceBundleV1,
    CopilotEvidenceV1,
    CopilotFreshnessState,
    CopilotIntentType,
    CopilotIntentV1,
    CopilotReasoningFactorV1,
    CopilotReasoningV1,
    CopilotSourceReferenceV1,
    CopilotStance,
    CopilotValidationCheck,
    CopilotValidationIssueV1,
    CopilotValidationResultV1,
    CopilotValidationSeverity,
    CopilotValidationStatus,
)
from app.copilot.policy import (
    causality_violations,
    certainty_violations,
    contains_prompt_injection,
    contains_secret,
    flow_claim_violations,
    ownership_violations,
    recommendation_violations,
)
from app.copilot.reasoning import safe_reasoning_fallback


TickerValidator = Callable[[str, CopilotIntentV1], bool]
SourceValidator = Callable[[CopilotSourceReferenceV1, CopilotEvidenceBundleV1], bool]

_CHECKS = list(CopilotValidationCheck)
_CONSTRAINED_STATES = {
    CopilotFreshnessState.STALE,
    CopilotFreshnessState.TEST,
    CopilotFreshnessState.PARTIAL,
    CopilotFreshnessState.MIXED,
    CopilotFreshnessState.UNAVAILABLE,
}

_NUMERIC_PATTERN = re.compile(r"(?<![A-Za-z])[-+]?\d[\d,]*(?:\.\d+)?%?")
_UPPER_TOKEN_PATTERN = re.compile(r"(?<![A-Za-z0-9_$])\$?([A-Z][A-Z0-9.-]{0,5})(?![A-Za-z0-9_])")
_AFFIRMATIVE_TRADE_LABEL_PATTERN = re.compile(
    r"\b(?:this|the setup|[A-Z][A-Z0-9.-]{0,5})\s+is\s+(?:a\s+)?(?:buy|sell|short(?![- ]term\b))\b",
    re.IGNORECASE,
)
_ADDITIONAL_CAUSALITY_PATTERN = re.compile(
    r"\b(?:caused|causes|drives?|triggered|triggers?|led to|results? in)\b",
    re.IGNORECASE,
)
_STALE_ACTION_PATTERN = re.compile(
    r"\b(?:technically actionable|setup is confirmed|confirmed setup|enter (?:the )?(?:trade|position))\b",
    re.IGNORECASE,
)
_BREAKOUT_CONFIRMED_PATTERN = re.compile(
    r"\b(?:breakout (?:is )?confirmed|confirmed breakout)\b",
    re.IGNORECASE,
)
_STALE_CURRENTNESS_PATTERN = re.compile(
    r"\b(?:currently|today|right now|current (?:market|posture|condition|setup|signal|trend|risk|breadth|leadership|price|value|reading|state))\b",
    re.IGNORECASE,
)
_DIRECT_YIELD_PATTERN = re.compile(
    r"\b(?:2[- ]year|10[- ]year|treasury|bond) yields?\s+(?:is|are|at|rose|fell|rising|falling|increased|decreased)\b",
    re.IGNORECASE,
)
_PROXY_MARKERS = {"etf", "proxy", "tlt", "ief", "shy", "hyg", "lqd"}
_FLOW_MARKERS = {"flow", "fund flow", "institutional", "accumulation", "smart money"}
_METRIC_FAMILY_PATTERNS: dict[str, tuple[str, ...]] = {
    "price": ("price", "close", "support", "resistance", "breakout", "trigger", "level"),
    "rsi": ("rsi",),
    "moving_average": ("ema", "sma", "moving average"),
    "return": ("return", "performance", "gain", "loss", "change"),
    "score": ("score", "rating"),
    "volume": ("volume", "participation"),
    "yield": ("yield",),
    "breadth": ("breadth", "advance decline", "constituents above"),
    "count": ("count", "constituent", "securities", "figure types", "items"),
    "ratio": ("ratio", "relative strength"),
    "risk": ("risk", "volatility"),
}

# These are common market/application terms rather than security symbols.
_NON_TICKER_TOKENS = {
    "AD",
    "AI",
    "API",
    "APP",
    "ATR",
    "CPI",
    "ETF",
    "EMA",
    "EPS",
    "GDP",
    "LLM",
    "MACD",
    "MA",
    "NAV",
    "NVT",
    "PCE",
    "PMI",
    "RSI",
    "SEC",
    "SMA",
    "US",
    "USA",
    "USD",
    "VIX",
    "YTD",
}

_UNCITED_SAFE_PREFIXES = (
    "evidence state is ",
    "no validated ",
    "no cited ",
    "portfolio holdings are not ",
)


class CopilotResponseValidator:
    """Validate grounded reasoning before it is exposed as a Copilot answer."""

    def __init__(
        self,
        *,
        ticker_validator: TickerValidator | None = None,
        source_validator: SourceValidator | None = None,
    ) -> None:
        self.ticker_validator = ticker_validator
        self.source_validator = source_validator

    def validate(
        self,
        bundle: CopilotEvidenceBundleV1,
        reasoning: CopilotReasoningV1,
        actions: Sequence[CopilotActionV1] = (),
        *,
        question: str | None = None,
        intent: CopilotIntentV1 | None = None,
    ) -> CopilotValidationResultV1:
        selected_intent = intent or bundle.intent
        issues: list[CopilotValidationIssueV1] = []
        issues.extend(self._validate_evidence_references(bundle, reasoning, selected_intent))
        issues.extend(self._validate_contradiction_preservation(bundle, reasoning))
        issues.extend(self._validate_numerical_claims(bundle, reasoning))
        issues.extend(self._validate_tickers(bundle, reasoning, selected_intent))
        issues.extend(self._validate_sources(bundle))
        issues.extend(self._validate_report_lineage(bundle, selected_intent))
        issues.extend(self._validate_causality(reasoning))
        issues.extend(self._validate_proxy_labeling(bundle, reasoning))
        issues.extend(self._validate_confirmed_claims(bundle, reasoning))
        issues.extend(self._validate_condition_coherence(bundle, reasoning))
        issues.extend(self._validate_confidence_freshness(bundle, reasoning, selected_intent))
        issues.extend(self._validate_freshness_language(bundle, reasoning))
        issues.extend(self._validate_high_risk_language(bundle, reasoning))
        issues.extend(self._validate_ownership(reasoning))
        issues.extend(self._validate_stale_actionability(bundle, reasoning))
        issues.extend(self._validate_recommendations(reasoning))
        issues.extend(self._validate_prompt_injection(question or bundle.question, bundle, reasoning, actions))
        issues.extend(self._validate_actions(actions, selected_intent))
        issues = _dedupe_issues(issues)
        failed = any(issue.severity == CopilotValidationSeverity.ERROR for issue in issues)
        return CopilotValidationResultV1(
            status=CopilotValidationStatus.FAILED if failed else CopilotValidationStatus.PASSED,
            checks_run=_CHECKS,
            issues=issues,
            fallback_used=False,
        )

    def validate_and_fallback(
        self,
        bundle: CopilotEvidenceBundleV1,
        reasoning: CopilotReasoningV1,
        actions: Sequence[CopilotActionV1] = (),
        *,
        question: str | None = None,
        intent: CopilotIntentV1 | None = None,
    ) -> tuple[CopilotReasoningV1, CopilotValidationResultV1]:
        result = self.validate(
            bundle,
            reasoning,
            actions,
            question=question,
            intent=intent,
        )
        if result.status == CopilotValidationStatus.PASSED:
            return reasoning, result
        fallback = self.safe_fallback(
            bundle,
            intent=intent,
            issues=result.issues,
        )
        fallback_result = result.model_copy(
            update={
                "status": CopilotValidationStatus.FALLBACK,
                "fallback_used": True,
            }
        )
        return fallback, fallback_result

    def safe_fallback(
        self,
        bundle: CopilotEvidenceBundleV1,
        *,
        intent: CopilotIntentV1 | None = None,
        issues: Iterable[CopilotValidationIssueV1] = (),
    ) -> CopilotReasoningV1:
        reasons = [issue.message for issue in issues if issue.severity == CopilotValidationSeverity.ERROR]
        return safe_reasoning_fallback(bundle, intent=intent, reasons=reasons)

    def _validate_evidence_references(
        self,
        bundle: CopilotEvidenceBundleV1,
        reasoning: CopilotReasoningV1,
        intent: CopilotIntentV1,
    ) -> list[CopilotValidationIssueV1]:
        issues: list[CopilotValidationIssueV1] = []
        evidence_ids = [item.evidence_id for item in bundle.evidence]
        known = set(evidence_ids)
        if len(evidence_ids) != len(known):
            issues.append(_issue(
                CopilotValidationCheck.EVIDENCE_REFERENCES,
                CopilotValidationSeverity.ERROR,
                "Evidence IDs in the bundle must be unique.",
            ))
        for factor in _reasoning_factors(reasoning):
            missing = [value for value in factor.evidence_ids if value not in known]
            if missing:
                issues.append(_issue(
                    CopilotValidationCheck.EVIDENCE_REFERENCES,
                    CopilotValidationSeverity.ERROR,
                    "A reasoning factor references evidence that is not in the collected bundle.",
                ))
            if len(factor.evidence_ids) != len(set(factor.evidence_ids)):
                issues.append(_issue(
                    CopilotValidationCheck.EVIDENCE_REFERENCES,
                    CopilotValidationSeverity.ERROR,
                    "A reasoning factor repeats an evidence reference.",
                ))
            if not factor.evidence_ids and not _is_safe_uncited_factor(factor.statement):
                issues.append(_issue(
                    CopilotValidationCheck.EVIDENCE_REFERENCES,
                    CopilotValidationSeverity.ERROR,
                    "A factual reasoning factor has no evidence reference.",
                ))

        intent_type = CopilotIntentType(intent.intent)
        exempt = {
            CopilotIntentType.APP_NAVIGATION,
            CopilotIntentType.EDUCATIONAL_QUERY,
            CopilotIntentType.PORTFOLIO_QUERY,
            CopilotIntentType.UNSUPPORTED_OR_AMBIGUOUS,
        }
        cited = {value for factor in _reasoning_factors(reasoning) for value in factor.evidence_ids}
        deterministic_fallback = (
            reasoning.disclaimer_class == "grounding_validation_fallback"
            or (
                reasoning.stance == CopilotStance.INSUFFICIENT_EVIDENCE
                and not _reasoning_factors(reasoning)
                and "insufficient validated evidence" in reasoning.direct_answer.casefold()
            )
        )
        if bundle.evidence and intent_type not in exempt and not cited and not deterministic_fallback:
            issues.append(_issue(
                CopilotValidationCheck.EVIDENCE_REFERENCES,
                CopilotValidationSeverity.ERROR,
                "The response contains collected market evidence but cites none of it.",
            ))
        if intent_type == CopilotIntentType.STOCK_DECISION_SUPPORT:
            if not any(factor.evidence_ids for factor in reasoning.supporting_factors):
                issues.append(_issue(
                    CopilotValidationCheck.EVIDENCE_REFERENCES,
                    CopilotValidationSeverity.WARNING,
                    "No cited supporting factor was available for decision support.",
                ))
            if not any(factor.evidence_ids for factor in reasoning.contradictory_factors):
                issues.append(_issue(
                    CopilotValidationCheck.EVIDENCE_REFERENCES,
                    CopilotValidationSeverity.WARNING,
                    "No cited opposing factor was available for decision support.",
                ))
        return issues

    def _validate_numerical_claims(
        self,
        bundle: CopilotEvidenceBundleV1,
        reasoning: CopilotReasoningV1,
    ) -> list[CopilotValidationIssueV1]:
        issues: list[CopilotValidationIssueV1] = []
        evidence_by_id = {item.evidence_id: item for item in bundle.evidence}
        for label, text, cited_ids in _claim_segments(reasoning):
            for fragment in _claim_fragments(text):
                claimed = _numeric_tokens(fragment)
                if not claimed:
                    continue
                unsupported: set[str] = set()
                for number in claimed:
                    if cited_ids:
                        candidates = [
                            evidence_by_id[value]
                            for value in cited_ids
                            if value in evidence_by_id
                            and _evidence_matches_claim(evidence_by_id[value], fragment, bundle)
                        ]
                    else:
                        # Headline/thesis numbers have no citation field of
                        # their own.  They are accepted only when the same
                        # number is repeated in a cited factor and that
                        # factor's evidence matches the headline entity,
                        # metric and unit.  This prevents a SPY RSI of 100
                        # from authorizing an uncited NVDA price of 100.
                        candidates = _cited_support_for_uncited_number(
                            fragment,
                            number,
                            reasoning,
                            evidence_by_id,
                            bundle,
                        )
                    if number not in _evidence_numeric_tokens(candidates):
                        unsupported.add(number)
                if unsupported:
                    issues.append(_issue(
                        CopilotValidationCheck.NUMERICAL_CLAIMS,
                        CopilotValidationSeverity.ERROR,
                        f"{label} contains a numerical claim that is not present in evidence for the same cited claim or entity.",
                    ))
        return issues

    @staticmethod
    def _validate_contradiction_preservation(
        bundle: CopilotEvidenceBundleV1,
        reasoning: CopilotReasoningV1,
    ) -> list[CopilotValidationIssueV1]:
        deterministic_no_claim_fallback = (
            reasoning.stance == CopilotStance.INSUFFICIENT_EVIDENCE
            and not _reasoning_factors(reasoning)
            and (
                reasoning.disclaimer_class == "grounding_validation_fallback"
                or "insufficient validated evidence" in reasoning.direct_answer.casefold()
            )
        )
        if deterministic_no_claim_fallback:
            # A fail-closed response promotes no thesis, so it has no thesis
            # whose counter-evidence could be misleadingly omitted.  Bundle
            # defects are still caught by their own checks on the second
            # validation pass and cause evidence quarantine.
            return []
        expected = set(bundle.contradictory_evidence_ids)
        if not expected:
            return []
        cited = {
            evidence_id
            for factor in [
                *reasoning.contradictory_factors,
                *reasoning.key_risks,
                *reasoning.invalidation_conditions,
            ]
            for evidence_id in factor.evidence_ids
        }
        preserved = expected.intersection(cited)
        if not preserved:
            return [_issue(
                CopilotValidationCheck.CONTRADICTION_PRESERVATION,
                CopilotValidationSeverity.ERROR,
                "Collected contradictory evidence was omitted from challenge/risk reasoning.",
            )]
        omitted = expected - cited
        disclosure = any(
            "additional contradictory evidence" in value.casefold()
            for value in reasoning.missing_evidence
        )
        if omitted and not disclosure:
            return [_issue(
                CopilotValidationCheck.CONTRADICTION_PRESERVATION,
                CopilotValidationSeverity.ERROR,
                "Material contradictory evidence was truncated without disclosure.",
            )]
        return []

    def _validate_tickers(
        self,
        bundle: CopilotEvidenceBundleV1,
        reasoning: CopilotReasoningV1,
        intent: CopilotIntentV1,
    ) -> list[CopilotValidationIssueV1]:
        allowed = {symbol.upper() for symbol in intent.ticker_symbols}
        allowed.update(
            entity.symbol.upper()
            for entity in intent.entities
            if entity.symbol
        )
        allowed.update(
            item.entity.upper()
            for item in bundle.evidence
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9.-]{0,5}", item.entity)
        )
        evidence_by_id = {item.evidence_id: item for item in bundle.evidence}
        segments: list[tuple[str, list[str]]] = [
            (reasoning.direct_answer, []),
            (reasoning.thesis, []),
            *[(factor.statement, factor.evidence_ids) for factor in _reasoning_factors(reasoning)],
            *[(value, []) for value in reasoning.related_research],
        ]
        if reasoning.personalization_note:
            segments.append((reasoning.personalization_note, []))
        invalid: list[str] = []
        for text, cited_ids in segments:
            segment_allowed = set(allowed)
            for evidence_id in cited_ids:
                item = evidence_by_id.get(evidence_id)
                if item:
                    # A symbol appearing in the exact cited evidence is
                    # grounded even when it is a benchmark/proxy rather than
                    # the user's primary entity (for example SPY or HYG in a
                    # stored scenario condition).  Uncited invented symbols
                    # remain invalid.
                    segment_allowed.update(_evidence_ticker_tokens(item))
            for symbol in sorted(_ticker_tokens(text, segment_allowed) - segment_allowed):
                if self.ticker_validator and self.ticker_validator(symbol, intent):
                    continue
                invalid.append(symbol)
        if not invalid:
            return []
        return [_issue(
            CopilotValidationCheck.TICKERS,
            CopilotValidationSeverity.ERROR,
            "The response contains a security-like symbol that was not resolved by the intent or evidence registry.",
        )]

    def _validate_sources(self, bundle: CopilotEvidenceBundleV1) -> list[CopilotValidationIssueV1]:
        issues: list[CopilotValidationIssueV1] = []
        registered: dict[str, CopilotSourceReferenceV1] = {}
        for source in bundle.source_summary:
            existing = registered.get(source.source_id)
            if existing is not None and _source_identity(existing) != _source_identity(source):
                issues.append(_issue(
                    CopilotValidationCheck.SOURCES,
                    CopilotValidationSeverity.ERROR,
                    "One source ID resolves to conflicting provider, dataset, timestamp, or raw-snapshot lineage.",
                ))
            registered.setdefault(source.source_id, source)
        for result in bundle.agent_results:
            for source in result.source_references:
                existing = registered.get(source.source_id)
                if existing is not None and _source_identity(existing) != _source_identity(source):
                    issues.append(_issue(
                        CopilotValidationCheck.SOURCES,
                        CopilotValidationSeverity.ERROR,
                        "One source ID resolves to conflicting provider, dataset, timestamp, or raw-snapshot lineage.",
                    ))
                registered.setdefault(source.source_id, source)
        for item in bundle.evidence:
            source = item.source
            if source.source_id not in registered:
                # Report evidence can retain a more precise per-item source
                # than the agent-level source summary. Accept that typed raw
                # lineage, but surface the summary omission for observability.
                severity = (
                    CopilotValidationSeverity.WARNING
                    if source.raw_engine_reference
                    else CopilotValidationSeverity.ERROR
                )
                issues.append(_issue(
                    CopilotValidationCheck.SOURCES,
                    severity,
                    (
                        "An evidence item retains raw engine lineage but is absent from the agent-level source summary."
                        if severity == CopilotValidationSeverity.WARNING
                        else "An evidence item references a source outside the collected source registry."
                    ),
                ))
            elif _source_identity(registered[source.source_id]) != _source_identity(source):
                issues.append(_issue(
                    CopilotValidationCheck.SOURCES,
                    CopilotValidationSeverity.ERROR,
                    "Evidence reuses a registered source ID with different source lineage.",
                ))
            if not source.provider.strip() or source.provider.casefold() == "unavailable" or not source.dataset.strip():
                issues.append(_issue(
                    CopilotValidationCheck.SOURCES,
                    CopilotValidationSeverity.ERROR,
                    "A factual evidence item does not identify a validated provider and dataset.",
                ))
            if self.source_validator and not self.source_validator(source, bundle):
                issues.append(_issue(
                    CopilotValidationCheck.SOURCES,
                    CopilotValidationSeverity.ERROR,
                    "An evidence source was rejected by the configured source validator.",
                ))
        return issues

    @staticmethod
    def _validate_report_lineage(
        bundle: CopilotEvidenceBundleV1,
        intent: CopilotIntentV1,
    ) -> list[CopilotValidationIssueV1]:
        report_evidence = [item for item in bundle.evidence if item.report_reference]
        if not report_evidence:
            return []
        issues: list[CopilotValidationIssueV1] = []
        report_ids: set[str] = set()
        for item in report_evidence:
            reference = str(item.report_reference or "")
            if not re.fullmatch(r"[A-Za-z0-9_.:-]+", reference):
                issues.append(_issue(
                    CopilotValidationCheck.REPORT_LINEAGE,
                    CopilotValidationSeverity.ERROR,
                    "A report evidence reference is malformed.",
                ))
                continue
            report_ids.add(reference.split(":", 1)[0])
            source_date = item.source.market_date
            evidence_date = item.freshness.market_date
            if source_date and evidence_date and source_date != evidence_date:
                issues.append(_issue(
                    CopilotValidationCheck.REPORT_LINEAGE,
                    CopilotValidationSeverity.ERROR,
                    "Report evidence has a market date that does not match its source lineage.",
                ))
        if len(report_ids) > 1 and intent.sub_intent != "report_change":
            issues.append(_issue(
                CopilotValidationCheck.REPORT_LINEAGE,
                CopilotValidationSeverity.ERROR,
                "A non-comparison response mixes evidence from different immutable reports.",
            ))
        return issues

    @staticmethod
    def _validate_causality(reasoning: CopilotReasoningV1) -> list[CopilotValidationIssueV1]:
        if not any(
            causality_violations(text) or _ADDITIONAL_CAUSALITY_PATTERN.search(text)
            for text in _reasoning_strings(reasoning)
        ):
            return []
        return [_issue(
            CopilotValidationCheck.CAUSALITY,
            CopilotValidationSeverity.ERROR,
            "The response asserts causality without a validated attribution contract.",
        )]

    @staticmethod
    def _validate_proxy_labeling(
        bundle: CopilotEvidenceBundleV1,
        reasoning: CopilotReasoningV1,
    ) -> list[CopilotValidationIssueV1]:
        evidence_by_id = {item.evidence_id: item for item in bundle.evidence}
        for _label, text, cited_ids in _claim_segments(reasoning):
            if not _DIRECT_YIELD_PATTERN.search(text) or re.search(r"\b(?:proxy|ETF)\b", text, re.IGNORECASE):
                continue
            cited = [evidence_by_id[value] for value in cited_ids if value in evidence_by_id]
            candidates = cited if cited_ids else bundle.evidence
            if any(_evidence_has_marker(item, _PROXY_MARKERS) for item in candidates):
                return [_issue(
                    CopilotValidationCheck.PROXY_LABELING,
                    CopilotValidationSeverity.ERROR,
                    "A bond-ETF or price proxy was presented as a direct yield observation.",
                )]
        return []

    @staticmethod
    def _validate_confirmed_claims(
        bundle: CopilotEvidenceBundleV1,
        reasoning: CopilotReasoningV1,
    ) -> list[CopilotValidationIssueV1]:
        evidence_by_id = {item.evidence_id: item for item in bundle.evidence}
        for _label, text, cited_ids in _claim_segments(reasoning):
            if not _BREAKOUT_CONFIRMED_PATTERN.search(text):
                continue
            cited = [evidence_by_id[value] for value in cited_ids if value in evidence_by_id]
            candidates = cited if cited_ids else bundle.evidence
            claimed_entities = _explicit_claim_entities(text, bundle)
            by_entity: dict[str, dict[str, Any]] = {}
            for item in candidates:
                entity_keys = _evidence_entity_keys(item)
                if claimed_entities and not entity_keys.intersection(claimed_entities):
                    continue
                entity_key = item.entity.strip().casefold()
                state = by_entity.setdefault(
                    entity_key,
                    {"current": [], "trigger": [], "volume": False},
                )
                metric = item.metric.casefold()
                number = _scalar_decimal(item.current_state if item.current_state is not None else item.value)
                if any(term in metric for term in ("breakout", "resistance", "confirmation", "trigger")):
                    if number is not None:
                        state["trigger"].append(number)
                elif metric in {"price", "current price", "last price", "close", "closing price"}:
                    if number is not None:
                        state["current"].append(number)
                if "volume" in metric and _volume_supports_confirmation(item):
                    state["volume"] = True
            supported = any(
                state["current"]
                and state["trigger"]
                and max(state["current"]) > max(state["trigger"])
                and state["volume"]
                for state in by_entity.values()
            )
            if not supported:
                return [_issue(
                    CopilotValidationCheck.CONFIRMED_CLAIMS,
                    CopilotValidationSeverity.ERROR,
                    "A confirmed breakout claim lacks a price beyond its cited trigger or affirmative volume confirmation.",
                )]
        return []

    @staticmethod
    def _validate_condition_coherence(
        bundle: CopilotEvidenceBundleV1,
        reasoning: CopilotReasoningV1,
    ) -> list[CopilotValidationIssueV1]:
        evidence_by_id = {item.evidence_id: item for item in bundle.evidence}
        for confirmation in reasoning.confirmation_conditions:
            for invalidation in reasoning.invalidation_conditions:
                confirmation_ids = set(confirmation.evidence_ids)
                invalidation_ids = set(invalidation.evidence_ids)
                if confirmation_ids.intersection(invalidation_ids):
                    return [_issue(
                        CopilotValidationCheck.CONDITION_COHERENCE,
                        CopilotValidationSeverity.ERROR,
                        "The same evidence is used as both confirmation and invalidation.",
                    )]
                confirmation_items = [evidence_by_id[value] for value in confirmation_ids if value in evidence_by_id]
                invalidation_items = [evidence_by_id[value] for value in invalidation_ids if value in evidence_by_id]
                entities = {item.entity.casefold() for item in confirmation_items}
                if not entities.intersection(item.entity.casefold() for item in invalidation_items):
                    continue
                confirmation_numbers = _numeric_tokens(confirmation.statement)
                invalidation_numbers = _numeric_tokens(invalidation.statement)
                if confirmation_numbers and confirmation_numbers.intersection(invalidation_numbers):
                    return [_issue(
                        CopilotValidationCheck.CONDITION_COHERENCE,
                        CopilotValidationSeverity.ERROR,
                        "Confirmation and invalidation collide at the same cited level for one entity.",
                    )]
        return []

    @staticmethod
    def _validate_confidence_freshness(
        bundle: CopilotEvidenceBundleV1,
        reasoning: CopilotReasoningV1,
        intent: CopilotIntentV1,
    ) -> list[CopilotValidationIssueV1]:
        exempt = {
            CopilotIntentType.APP_NAVIGATION,
            CopilotIntentType.EDUCATIONAL_QUERY,
            CopilotIntentType.PORTFOLIO_QUERY,
            CopilotIntentType.UNSUPPORTED_OR_AMBIGUOUS,
        }
        if intent.intent in exempt or reasoning.confidence_label != CopilotConfidenceLabel.HIGH:
            return []
        summary = bundle.freshness_summary
        constrained = summary.overall_state in _CONSTRAINED_STATES or any((
            summary.stale_count,
            summary.partial_count,
            summary.unavailable_count,
            summary.test_count,
        ))
        if not constrained:
            return []
        return [_issue(
            CopilotValidationCheck.CONFIDENCE_FRESHNESS,
            CopilotValidationSeverity.ERROR,
            "High confidence is not allowed when factual evidence is stale, partial, mixed, test, or unavailable.",
        )]

    @staticmethod
    def _validate_freshness_language(
        bundle: CopilotEvidenceBundleV1,
        reasoning: CopilotReasoningV1,
    ) -> list[CopilotValidationIssueV1]:
        if bundle.freshness_summary.overall_state not in _CONSTRAINED_STATES:
            return []
        evidence_by_id = {item.evidence_id: item for item in bundle.evidence}
        for label, text, cited_ids in _claim_segments(reasoning):
            if not _STALE_CURRENTNESS_PATTERN.search(text):
                continue
            if _explicit_freshness_limitation(text):
                continue
            if label in {"Direct answer", "Thesis"}:
                return [_issue(
                    CopilotValidationCheck.FRESHNESS_LANGUAGE,
                    CopilotValidationSeverity.ERROR,
                    "Constrained evidence was described with current/today certainty.",
                )]
            cited = [evidence_by_id[value] for value in cited_ids if value in evidence_by_id]
            if not cited or any(item.freshness.state in _CONSTRAINED_STATES for item in cited):
                return [_issue(
                    CopilotValidationCheck.FRESHNESS_LANGUAGE,
                    CopilotValidationSeverity.ERROR,
                    "A stale, partial, test, mixed, or unavailable claim was presented as current.",
                )]
        return []

    @staticmethod
    def _validate_high_risk_language(
        bundle: CopilotEvidenceBundleV1,
        reasoning: CopilotReasoningV1,
    ) -> list[CopilotValidationIssueV1]:
        if any(certainty_violations(text) for text in _reasoning_strings(reasoning)):
            return [_issue(
                CopilotValidationCheck.HIGH_RISK_LANGUAGE,
                CopilotValidationSeverity.ERROR,
                "The response uses unsupported certainty or guaranteed-return language.",
            )]
        evidence_by_id = {item.evidence_id: item for item in bundle.evidence}
        for _label, text, cited_ids in _claim_segments(reasoning):
            if not flow_claim_violations(text):
                continue
            cited = [evidence_by_id[value] for value in cited_ids if value in evidence_by_id]
            candidates = cited if cited_ids else bundle.evidence
            if not any(_evidence_has_marker(item, _FLOW_MARKERS) for item in candidates):
                return [_issue(
                    CopilotValidationCheck.HIGH_RISK_LANGUAGE,
                    CopilotValidationSeverity.ERROR,
                    "Institutional-flow or smart-money language lacks a defined cited flow metric.",
                )]
        return []

    @staticmethod
    def _validate_ownership(reasoning: CopilotReasoningV1) -> list[CopilotValidationIssueV1]:
        if not any(ownership_violations(text) for text in _reasoning_strings(reasoning)):
            return []
        return [_issue(
            CopilotValidationCheck.OWNERSHIP,
            CopilotValidationSeverity.ERROR,
            "The response infers ownership or portfolio exposure from unavailable data.",
        )]

    @staticmethod
    def _validate_stale_actionability(
        bundle: CopilotEvidenceBundleV1,
        reasoning: CopilotReasoningV1,
    ) -> list[CopilotValidationIssueV1]:
        summary = bundle.freshness_summary
        try:
            state = CopilotFreshnessState(summary.overall_state)
        except ValueError:
            state = CopilotFreshnessState.UNAVAILABLE
        constrained = state in _CONSTRAINED_STATES or any(
            (
                summary.stale_count,
                summary.partial_count,
                summary.unavailable_count,
                summary.test_count,
            )
        )
        if not constrained:
            return []
        actionable_stance = reasoning.stance in {
            CopilotStance.ACTIONABLE,
            CopilotStance.NEARLY_ACTIONABLE,
        }
        actionable_text = bool(_STALE_ACTION_PATTERN.search(
            f"{reasoning.direct_answer} {reasoning.thesis}"
        ))
        if not actionable_stance and not actionable_text:
            return []
        return [_issue(
            CopilotValidationCheck.STALE_ACTIONABILITY,
            CopilotValidationSeverity.ERROR,
            "Stale, partial, test, mixed, or unavailable evidence cannot support an actionable conclusion.",
        )]

    @staticmethod
    def _validate_recommendations(reasoning: CopilotReasoningV1) -> list[CopilotValidationIssueV1]:
        violations = any(
            recommendation_violations(text)
            for text in _reasoning_strings(reasoning)
        )
        primary_trade_label = bool(_AFFIRMATIVE_TRADE_LABEL_PATTERN.search(
            f"{reasoning.direct_answer} {reasoning.thesis}"
        ))
        if not violations and not primary_trade_label:
            return []
        return [_issue(
            CopilotValidationCheck.RECOMMENDATION,
            CopilotValidationSeverity.ERROR,
            "The response contains an unsupported direct trading recommendation.",
        )]

    @staticmethod
    def _validate_prompt_injection(
        question: str,
        bundle: CopilotEvidenceBundleV1,
        reasoning: CopilotReasoningV1,
        actions: Sequence[CopilotActionV1],
    ) -> list[CopilotValidationIssueV1]:
        texts = [question, *_bundle_external_strings(bundle), *_reasoning_strings(reasoning)]
        texts.extend(action.label for action in actions)
        texts.extend(value for action in actions for value in action.parameters.values())
        if not any(contains_prompt_injection(text) or contains_secret(text) for text in texts):
            return []
        return [_issue(
            CopilotValidationCheck.PROMPT_INJECTION,
            CopilotValidationSeverity.ERROR,
            "Untrusted instructions or secret-like content were detected and were not promoted into the answer.",
        )]

    @staticmethod
    def _validate_actions(
        actions: Sequence[CopilotActionV1],
        intent: CopilotIntentV1,
    ) -> list[CopilotValidationIssueV1]:
        issues: list[CopilotValidationIssueV1] = []
        action_ids = [action.action_id for action in actions]
        if len(action_ids) != len(set(action_ids)):
            issues.append(_issue(
                CopilotValidationCheck.ACTIONS,
                CopilotValidationSeverity.ERROR,
                "Action IDs must be unique.",
            ))
        validated_entities = {entity.entity_id for entity in intent.entities}
        validated_entities.update(entity.symbol for entity in intent.entities if entity.symbol)
        validated_entities.update(intent.ticker_symbols)
        latest_report_destinations = {
            CopilotDestination.REPORT_RESEARCH_FOCUS,
            CopilotDestination.REPORT_SCENARIOS,
            CopilotDestination.REPORT_WATCHLIST,
        }
        for action in actions:
            definition = get_registered_action(action.destination_id)
            if definition is None or not is_registered_route(action.route):
                issues.append(_issue(
                    CopilotValidationCheck.ACTIONS,
                    CopilotValidationSeverity.ERROR,
                    "A response action uses an unregistered destination or route.",
                ))
                continue
            expected_type = definition.get("action_type", CopilotActionType.NAVIGATE)
            expected_highlight = definition.get("highlight_target") or definition.get("section_id")
            mismatched = any((
                action.route != definition.get("route"),
                action.action_type != expected_type,
                action.tab != definition.get("tab"),
                action.sub_tab != definition.get("sub_tab"),
                action.section_id != definition.get("section_id"),
                action.highlight_target != expected_highlight,
            ))
            if mismatched:
                issues.append(_issue(
                    CopilotValidationCheck.ACTIONS,
                    CopilotValidationSeverity.ERROR,
                    "A response action does not match its registered route contract.",
                ))
            registered_latest_report = (
                action.entity == "latest"
                and action.destination_id in latest_report_destinations
            )
            if (
                action.entity
                and not registered_latest_report
                and action.entity not in validated_entities
                and action.entity.upper() not in {
                    value.upper() for value in validated_entities if value
                }
            ):
                issues.append(_issue(
                    CopilotValidationCheck.ACTIONS,
                    CopilotValidationSeverity.ERROR,
                    "A response action targets an entity that was not validated by the intent engine.",
                ))
            expected_parameters: dict[str, str] = {}
            if action.entity:
                expected_parameters["entity"] = action.entity
                if action.destination_id in {
                    CopilotDestination.STOCK_DETAIL,
                    CopilotDestination.STOCK_TECHNICAL,
                    CopilotDestination.STOCK_SIGNALS,
                    CopilotDestination.STOCK_RISK,
                }:
                    expected_parameters["symbol"] = action.entity.upper()
                elif action.destination_id == CopilotDestination.SECTOR_DETAIL:
                    expected_parameters["sectorId"] = action.entity
                elif action.destination_id == CopilotDestination.THEME_DETAIL:
                    expected_parameters["themeId"] = action.entity
            if definition.get("tab"):
                expected_parameters["tab"] = str(definition["tab"])
            if definition.get("sub_tab"):
                expected_parameters["subTab"] = str(definition["sub_tab"])
                if action.destination_id in {
                    CopilotDestination.STOCK_TECHNICAL,
                    CopilotDestination.STOCK_SIGNALS,
                    CopilotDestination.STOCK_RISK,
                }:
                    expected_parameters["stockTab"] = str(definition["sub_tab"])
            if definition.get("section_id"):
                expected_parameters["sectionId"] = str(definition["section_id"])
            if any(
                action.parameters.get(key) != expected
                for key, expected in expected_parameters.items()
            ) or set(action.parameters) != set(expected_parameters):
                issues.append(_issue(
                    CopilotValidationCheck.ACTIONS,
                    CopilotValidationSeverity.ERROR,
                    "A response action contains parameters that do not match its registered destination contract.",
                ))
        return issues


def validate_copilot_reasoning(
    bundle: CopilotEvidenceBundleV1,
    reasoning: CopilotReasoningV1,
    actions: Sequence[CopilotActionV1] = (),
    *,
    question: str | None = None,
    intent: CopilotIntentV1 | None = None,
    validator: CopilotResponseValidator | None = None,
) -> CopilotValidationResultV1:
    """Functional validator entry point."""

    return (validator or CopilotResponseValidator()).validate(
        bundle,
        reasoning,
        actions,
        question=question,
        intent=intent,
    )


def validate_or_fallback(
    bundle: CopilotEvidenceBundleV1,
    reasoning: CopilotReasoningV1,
    actions: Sequence[CopilotActionV1] = (),
    *,
    question: str | None = None,
    intent: CopilotIntentV1 | None = None,
    validator: CopilotResponseValidator | None = None,
) -> tuple[CopilotReasoningV1, CopilotValidationResultV1]:
    """Validate and replace a failed synthesis with a deterministic fallback."""

    return (validator or CopilotResponseValidator()).validate_and_fallback(
        bundle,
        reasoning,
        actions,
        question=question,
        intent=intent,
    )


def _reasoning_factors(reasoning: CopilotReasoningV1) -> list[CopilotReasoningFactorV1]:
    return [
        *reasoning.supporting_factors,
        *reasoning.contradictory_factors,
        *reasoning.key_risks,
        *reasoning.confirmation_conditions,
        *reasoning.invalidation_conditions,
    ]


def _reasoning_strings(reasoning: CopilotReasoningV1) -> list[str]:
    values = [
        reasoning.direct_answer,
        reasoning.thesis,
        *[factor.statement for factor in _reasoning_factors(reasoning)],
        *reasoning.missing_evidence,
        *reasoning.related_research,
    ]
    if reasoning.personalization_note:
        values.append(reasoning.personalization_note)
    return [value for value in values if value]


def _ticker_claim_strings(reasoning: CopilotReasoningV1) -> list[str]:
    """Ticker validation applies to claims, not honest missing-data labels."""

    values = [
        reasoning.direct_answer,
        reasoning.thesis,
        *[factor.statement for factor in _reasoning_factors(reasoning)],
        *reasoning.related_research,
    ]
    if reasoning.personalization_note:
        values.append(reasoning.personalization_note)
    return [value for value in values if value]


def _ticker_tokens(text: str, allowed_singletons: set[str] | None = None) -> set[str]:
    allowed_singletons = allowed_singletons or set()
    result: set[str] = set()
    for match in _UPPER_TOKEN_PATTERN.finditer(text or ""):
        token = match.group(1).upper().strip(".")
        dollar_prefixed = match.group(0).startswith("$")
        if token in _NON_TICKER_TOKENS:
            continue
        if len(token) > 1 or dollar_prefixed or token in allowed_singletons:
            result.add(token)
    return result


def _evidence_ticker_tokens(item: CopilotEvidenceV1) -> set[str]:
    text = " ".join(
        (
            item.entity,
            item.metric,
            _json_text(item.value),
            _json_text(item.current_state),
            _json_text(item.prior_value),
            _json_text(item.change),
        )
    )
    return _ticker_tokens(text)


def _evidence_has_marker(item: CopilotEvidenceV1, markers: set[str]) -> bool:
    text = " ".join((
        item.entity,
        item.metric,
        item.unit or "",
        item.source.provider,
        item.source.dataset,
        _json_text(item.value),
        _json_text(item.current_state),
    )).casefold()
    return any(marker in text for marker in markers)


def _bundle_external_strings(bundle: CopilotEvidenceBundleV1) -> list[str]:
    values: list[str] = []
    for item in bundle.evidence:
        values.extend([
            item.entity,
            item.metric,
            _json_text(item.value),
            _json_text(item.current_state),
            _json_text(item.prior_value),
            _json_text(item.change),
            item.unit or "",
            item.source.provider,
            item.source.dataset,
        ])
    for result in bundle.agent_results:
        values.extend(result.observations)
        values.extend(result.conclusions)
        values.extend(result.contradictions)
        values.extend(result.warnings)
        values.extend(result.missing_data)
    values.extend(bundle.warnings)
    values.extend(bundle.unavailable_evidence)
    return [value for value in values if value]


def _claim_segments(
    reasoning: CopilotReasoningV1,
) -> list[tuple[str, str, list[str]]]:
    values: list[tuple[str, str, list[str]]] = [
        ("Direct answer", reasoning.direct_answer, []),
        ("Thesis", reasoning.thesis, []),
    ]
    for factor in _reasoning_factors(reasoning):
        values.append(("Reasoning factor", factor.statement, factor.evidence_ids))
    if reasoning.personalization_note:
        values.append(("Personalization note", reasoning.personalization_note, []))
    values.extend(("Missing-evidence note", value, []) for value in reasoning.missing_evidence)
    return values


def _claim_fragments(text: str) -> list[str]:
    return [
        value.strip()
        for value in re.split(r"(?<=[!?;])\s+|(?<=[A-Za-z0-9])\.\s+(?=[A-Z])", text or "")
        if value.strip()
    ]


def _uncited_claim_evidence(
    text: str,
    bundle: CopilotEvidenceBundleV1,
) -> list[CopilotEvidenceV1]:
    lowered = text.casefold()
    explicit_entities = {
        item.entity.casefold()
        for item in bundle.evidence
        if item.entity and re.search(rf"(?<![A-Za-z0-9]){re.escape(item.entity.casefold())}(?![A-Za-z0-9])", lowered)
    }
    if explicit_entities:
        return [item for item in bundle.evidence if item.entity.casefold() in explicit_entities]
    if len(bundle.intent.ticker_symbols) == 1:
        symbol = bundle.intent.ticker_symbols[0].casefold()
        matching = [item for item in bundle.evidence if item.entity.casefold() == symbol]
        if matching:
            return matching
    entities = {item.entity.casefold() for item in bundle.evidence if item.entity}
    return list(bundle.evidence) if len(entities) == 1 else []


def _explicit_claim_entities(
    text: str,
    bundle: CopilotEvidenceBundleV1,
) -> set[str]:
    lowered = text.casefold()
    entities: set[str] = set()
    for item in bundle.evidence:
        value = item.entity.strip()
        if value and re.search(
            rf"(?<![A-Za-z0-9]){re.escape(value.casefold())}(?![A-Za-z0-9])",
            lowered,
        ):
            entities.add(value.casefold())
    for symbol in _ticker_tokens(text):
        entities.add(symbol.casefold())
    return entities


def _evidence_entity_keys(item: CopilotEvidenceV1) -> set[str]:
    keys = {item.entity.strip().casefold()} if item.entity.strip() else set()
    keys.update(value.casefold() for value in _evidence_ticker_tokens(item))
    return keys


def _metric_families(text: str) -> set[str]:
    lowered = text.casefold().replace("-", " ")
    return {
        family
        for family, markers in _METRIC_FAMILY_PATTERNS.items()
        if any(marker in lowered for marker in markers)
    }


def _evidence_matches_claim(
    item: CopilotEvidenceV1,
    claim: str,
    bundle: CopilotEvidenceBundleV1,
) -> bool:
    entities = _explicit_claim_entities(claim, bundle)
    if entities and not entities.intersection(_evidence_entity_keys(item)):
        return False
    claim_metrics = _metric_families(claim)
    evidence_descriptor = " ".join((
        item.metric,
        item.unit or "",
        _json_text(item.value),
        _json_text(item.current_state),
    ))
    evidence_metrics = _metric_families(evidence_descriptor)
    if claim_metrics and not claim_metrics.intersection(evidence_metrics):
        return False
    lowered = claim.casefold()
    unit = f"{item.unit or ''} {_json_text(item.value)} {_json_text(item.current_state)}".casefold()
    metric = item.metric.casefold()
    if ("%" in claim or "percent" in lowered or "percentage" in lowered) and not (
        "%" in unit or "percent" in unit or "percentage" in metric
    ):
        return False
    if "$" in claim and not any(value in f"{metric} {unit}" for value in ("price", "usd", "dollar")):
        return False
    return True


def _claims_semantically_compatible(
    first: str,
    second: str,
    bundle: CopilotEvidenceBundleV1,
) -> bool:
    first_entities = _explicit_claim_entities(first, bundle)
    second_entities = _explicit_claim_entities(second, bundle)
    if first_entities and second_entities and not first_entities.intersection(second_entities):
        return False
    first_metrics = _metric_families(first)
    second_metrics = _metric_families(second)
    if first_metrics and second_metrics and not first_metrics.intersection(second_metrics):
        return False
    first_percent = "%" in first or "percent" in first.casefold() or "percentage" in first.casefold()
    second_percent = "%" in second or "percent" in second.casefold() or "percentage" in second.casefold()
    if first_percent != second_percent and (first_metrics or second_metrics):
        return False
    return True


def _cited_support_for_uncited_number(
    claim: str,
    number: str,
    reasoning: CopilotReasoningV1,
    evidence_by_id: dict[str, CopilotEvidenceV1],
    bundle: CopilotEvidenceBundleV1,
) -> list[CopilotEvidenceV1]:
    supported: list[CopilotEvidenceV1] = []
    for factor in _reasoning_factors(reasoning):
        if number not in _numeric_tokens(factor.statement):
            continue
        if not _claims_semantically_compatible(claim, factor.statement, bundle):
            continue
        for evidence_id in factor.evidence_ids:
            item = evidence_by_id.get(evidence_id)
            if item is None:
                continue
            if not _evidence_matches_claim(item, claim, bundle):
                continue
            if not _evidence_matches_claim(item, factor.statement, bundle):
                continue
            if number in _evidence_numeric_tokens([item]):
                supported.append(item)
    return supported


def _explicit_freshness_limitation(text: str) -> bool:
    lowered = text.casefold()
    return any(
        marker in lowered
        for marker in (
            "unavailable",
            "stale",
            "not current",
            "not live",
            "historical",
            "stored ",
            "at the time",
            "as of ",
            "delayed",
        )
    )


def _scalar_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    raw = str(value).strip().replace(",", "").rstrip("%")
    if not re.fullmatch(r"[-+]?\d+(?:\.\d+)?", raw):
        return None
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def _volume_supports_confirmation(item: CopilotEvidenceV1) -> bool:
    value = item.current_state if item.current_state is not None else item.value
    if isinstance(value, bool):
        return value
    number = _scalar_decimal(value)
    metric = item.metric.casefold()
    if number is not None:
        return any(term in metric for term in ("ratio", "relative", "vs average")) and number >= 1
    text = str(value or "").casefold()
    if any(term in text for term in ("weak", "below average", "declining", "missing", "partial", "unavailable", "not confirmed")):
        return False
    return any(term in text for term in ("strong", "above average", "expanding", "confirmed", "supportive"))


def _source_identity(source: CopilotSourceReferenceV1) -> tuple[str | None, ...]:
    return (
        source.provider,
        source.dataset,
        source.generated_at,
        source.market_date,
        source.raw_engine_reference,
    )


def _numeric_tokens(text: str) -> set[str]:
    return {_normalize_number(match.group(0)) for match in _NUMERIC_PATTERN.finditer(text)}


def _normalize_number(value: str) -> str:
    raw = value.replace(",", "").lstrip("+").rstrip("%")
    try:
        number = Decimal(raw)
    except InvalidOperation:
        return raw
    if not number:
        return "0"
    return format(number.normalize(), "f")


def _evidence_numeric_tokens(evidence: Iterable[CopilotEvidenceV1]) -> set[str]:
    result: set[str] = set()
    for item in evidence:
        text = " ".join((
            item.entity,
            item.metric,
            _json_text(item.value),
            _json_text(item.current_state),
            _json_text(item.prior_value),
            _json_text(item.change),
            item.unit or "",
            item.timeframe,
        ))
        result.update(_numeric_tokens(text))
    return result


def _is_safe_uncited_factor(statement: str) -> bool:
    lowered = statement.strip().casefold()
    return lowered.startswith(_UNCITED_SAFE_PREFIXES)


def _json_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, sort_keys=True, default=str, ensure_ascii=True)
    except (TypeError, ValueError):
        return str(value)


def _issue(
    check: CopilotValidationCheck,
    severity: CopilotValidationSeverity,
    message: str,
) -> CopilotValidationIssueV1:
    return CopilotValidationIssueV1(check=check, severity=severity, message=message)


def _dedupe_issues(values: Iterable[CopilotValidationIssueV1]) -> list[CopilotValidationIssueV1]:
    result: dict[tuple[str, str, str], CopilotValidationIssueV1] = {}
    for value in values:
        key = (value.check.value, value.severity.value, value.message)
        result.setdefault(key, value)
    return list(result.values())
