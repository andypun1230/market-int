from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.copilot.contracts import (
    CopilotConfidenceLabel,
    CopilotDestination,
    CopilotEvidenceBundleV1,
    CopilotEvidenceV1,
    CopilotFreshnessState,
    CopilotIntentType,
    CopilotIntentV1,
    CopilotLevelV1,
    CopilotReasoningFactorV1,
    CopilotReasoningV1,
    CopilotSessionContextV1,
    CopilotStance,
)
from app.copilot.policy import (
    causality_violations,
    contains_prompt_injection,
    contains_secret,
    ownership_violations,
    recommendation_violations,
)


PORTFOLIO_FALLBACK = (
    "Portfolio holdings are not yet connected. I can analyse your watchlist and saved themes instead."
)

_CONSTRAINED_STATES = {
    CopilotFreshnessState.STALE,
    CopilotFreshnessState.TEST,
    CopilotFreshnessState.PARTIAL,
    CopilotFreshnessState.MIXED,
    CopilotFreshnessState.UNAVAILABLE,
}

_NEGATIVE_TERMS = {
    "avoid",
    "bearish",
    "below",
    "cautious",
    "defensive",
    "deteriorating",
    "deterioration",
    "elevated risk",
    "failed",
    "fragile",
    "high risk",
    "lagging",
    "missing",
    "negative",
    "narrow",
    "not confirmed",
    "partial",
    "risk-off",
    "stale",
    "unavailable",
    "unconfirmed",
    "weak",
    "weakening",
}

_POSITIVE_TERMS = {
    "above",
    "bullish",
    "confirmed",
    "constructive",
    "healthy",
    "improving",
    "leading",
    "low risk",
    "outperforming",
    "positive",
    "risk-on",
    "strong",
    "strengthening",
}

_WATCHLIST_CAUTION_STATUS_TERMS = (
    "avoid",
    "cautious",
    "defensive",
    "deteriorating",
    "failed",
    "fragile",
    "lagging",
    "needs confirmation",
    "negative",
    "not confirmed",
    "poor setup",
    "risk-off",
    "unconfirmed",
    "weak",
)

_WATCHLIST_CAUTION_RISK_TERMS = (
    "critical",
    "elevated",
    "high",
    "severe",
)


class CopilotReasoningEngine:
    """Create a bounded, evidence-first synthesis without recalculating engines."""

    def __init__(self, *, maximum_factors: int = 5) -> None:
        self.maximum_factors = max(1, min(10, maximum_factors))

    def synthesize(
        self,
        bundle: CopilotEvidenceBundleV1,
        *,
        session: CopilotSessionContextV1 | None = None,
    ) -> CopilotReasoningV1:
        intent = CopilotIntentType(bundle.intent.intent)
        if intent == CopilotIntentType.PORTFOLIO_QUERY:
            return self._portfolio(bundle)
        if intent == CopilotIntentType.APP_NAVIGATION:
            return self._navigation(bundle)
        if intent == CopilotIntentType.EDUCATIONAL_QUERY:
            return self._educational(bundle)
        if intent == CopilotIntentType.UNSUPPORTED_OR_AMBIGUOUS:
            return self._ambiguous(bundle)
        if (
            intent == CopilotIntentType.WATCHLIST_REVIEW
            and not bundle.evidence
            and _watchlist_membership_is_confirmed_empty(bundle)
        ):
            return self._empty_watchlist(bundle)

        evidence_by_id = {item.evidence_id: item for item in bundle.evidence}
        supporting, opposing = self._partition_evidence(bundle)
        supporting_factors = self._evidence_factors(supporting)
        opposing_factors = self._evidence_factors(opposing)
        if intent == CopilotIntentType.WATCHLIST_REVIEW:
            # Put one already-computed caution status per symbol first so the
            # named attention candidates always retain evidence-level
            # citations.  This preserves engine order and does not rerank or
            # recompute the underlying stock assessments.
            attention_factors = self._evidence_factors(
                _watchlist_attention_evidence(bundle)
            )
            opposing_factors = _dedupe_factors(
                [*attention_factors, *opposing_factors]
            )
        missing = _missing_evidence(bundle)
        surfaced_opposition_ids = {
            evidence_id
            for factor in opposing_factors
            for evidence_id in factor.evidence_ids
        }
        omitted_opposition_ids = set(bundle.contradictory_evidence_ids) - surfaced_opposition_ids
        if omitted_opposition_ids:
            missing.append(
                "Additional contradictory evidence remains in the evidence registry."
            )

        # Agent-level prose has source lineage but no evidence-level citation.
        # Preserve that distinction instead of silently promoting it as fact.
        if any(result.contradictions for result in bundle.agent_results) and not opposing_factors:
            missing.append(
                "An engine reported a contradiction without an evidence-level citation; it was not promoted as a factual claim."
            )

        confirmation, invalidation = self._conditions(bundle, evidence_by_id)
        constrained = _is_constrained(bundle)
        stance = self._stance(intent, bundle, constrained)
        direct_answer = self._direct_answer(intent, bundle, stance, constrained)

        if intent == CopilotIntentType.STOCK_DECISION_SUPPORT:
            if not supporting_factors:
                supporting_factors = [
                    CopilotReasoningFactorV1(
                        statement="No validated supporting evidence was available; confidence is limited.",
                        evidence_ids=[],
                    )
                ]
            if not opposing_factors:
                opposing_factors = [
                    CopilotReasoningFactorV1(
                        statement="No validated opposing evidence was available; that absence limits confidence.",
                        evidence_ids=[],
                    )
                ]
            if not confirmation:
                missing.append("No validated confirmation level is available.")
            if not invalidation:
                missing.append("No validated invalidation or risk-reference level is available.")

        if intent == CopilotIntentType.SCENARIO_QUERY:
            scenario_conditions = self._trusted_agent_conditions(bundle, "scenario")
            confirmation = _dedupe_factors([*scenario_conditions, *confirmation])[: self.maximum_factors]
        elif intent == CopilotIntentType.FOLLOW_UP:
            confirmation, invalidation, follow_up_missing = self._follow_up_conditions(
                bundle,
                session,
                confirmation,
                invalidation,
            )
            missing.extend(follow_up_missing)

        confidence = self._confidence(intent, bundle, missing, constrained)
        risks = opposing_factors[: self.maximum_factors]
        if not risks and constrained:
            risks = [
                CopilotReasoningFactorV1(
                    statement=(
                        f"Evidence state is {bundle.freshness_summary.overall_state.value}; "
                        "the conclusion is monitoring-only."
                    ),
                    evidence_ids=[],
                )
            ]

        destinations = _registered_destination_candidates(bundle)
        personalization_note = None
        if intent == CopilotIntentType.WATCHLIST_REVIEW or bundle.intent.personalization_relevant:
            personalization_note = (
                "Saved-list membership is used only as monitoring context; holdings data was not inferred."
            )

        return CopilotReasoningV1(
            direct_answer=direct_answer,
            stance=stance,
            confidence_label=confidence,
            thesis=self._thesis(intent, direct_answer, stance),
            supporting_factors=supporting_factors[: self.maximum_factors],
            contradictory_factors=opposing_factors[: self.maximum_factors],
            key_risks=risks,
            confirmation_conditions=confirmation[: self.maximum_factors],
            invalidation_conditions=invalidation[: self.maximum_factors],
            missing_evidence=list(dict.fromkeys(value for value in missing if value)),
            personalization_note=personalization_note,
            related_research=_related_research(bundle),
            recommended_app_destinations=destinations,
        )

    # Alias kept deliberately small so orchestration code can inject the
    # engine under either a synthesis-oriented or reasoning-oriented name.
    def reason(
        self,
        bundle: CopilotEvidenceBundleV1,
        *,
        session: CopilotSessionContextV1 | None = None,
    ) -> CopilotReasoningV1:
        return self.synthesize(bundle, session=session)

    def _portfolio(self, bundle: CopilotEvidenceBundleV1) -> CopilotReasoningV1:
        return CopilotReasoningV1(
            direct_answer=PORTFOLIO_FALLBACK,
            stance=CopilotStance.INSUFFICIENT_EVIDENCE,
            confidence_label=CopilotConfidenceLabel.HIGH,
            thesis=PORTFOLIO_FALLBACK,
            missing_evidence=["Portfolio holdings are not connected."],
            personalization_note="Saved items are not treated as owned positions.",
            recommended_app_destinations=_registered_destination_candidates(bundle),
            disclaimer_class="portfolio_data_unavailable",
        )

    def _navigation(self, bundle: CopilotEvidenceBundleV1) -> CopilotReasoningV1:
        destinations = _registered_destination_candidates(bundle)
        destination = destinations[0] if destinations else CopilotDestination.MARKET_OVERVIEW
        label = destination.value.replace("_", " ").title()
        direct = f"Open {label}."
        return CopilotReasoningV1(
            direct_answer=direct,
            stance=CopilotStance.NEUTRAL,
            confidence_label=CopilotConfidenceLabel.HIGH,
            thesis=direct,
            recommended_app_destinations=[destination],
            disclaimer_class="app_navigation",
        )

    def _educational(self, bundle: CopilotEvidenceBundleV1) -> CopilotReasoningV1:
        conclusion = _first_safe_agent_text(bundle, agent_name="educational")
        direct = conclusion or (
            "I can explain breadth, relative strength, rotation, support, resistance, or volume using the app's terminology."
        )
        return CopilotReasoningV1(
            direct_answer=direct,
            stance=CopilotStance.NEUTRAL,
            confidence_label=CopilotConfidenceLabel.HIGH,
            thesis=direct,
            disclaimer_class="market_education",
        )

    def _ambiguous(self, bundle: CopilotEvidenceBundleV1) -> CopilotReasoningV1:
        direct = bundle.intent.clarification_question or (
            "I do not have enough information to resolve that request. Please name the market, security, or app section you mean."
        )
        return CopilotReasoningV1(
            direct_answer=direct,
            stance=CopilotStance.INSUFFICIENT_EVIDENCE,
            confidence_label=CopilotConfidenceLabel.LIMITED,
            thesis="The request needs a validated entity or a more specific question before evidence can be collected.",
            missing_evidence=list(dict.fromkeys([*bundle.intent.unresolved_entities, *bundle.unavailable_evidence])),
            recommended_app_destinations=_registered_destination_candidates(bundle),
        )

    def _empty_watchlist(self, bundle: CopilotEvidenceBundleV1) -> CopilotReasoningV1:
        conclusion = _first_safe_agent_text(bundle, agent_name="watchlist")
        direct = conclusion or "There are no saved stocks to review."
        return CopilotReasoningV1(
            direct_answer=direct,
            stance=CopilotStance.NEUTRAL,
            confidence_label=CopilotConfidenceLabel.HIGH,
            thesis=direct,
            missing_evidence=_missing_evidence(bundle),
            personalization_note=(
                "Saved-list membership is used only as monitoring context; holdings data was not inferred."
            ),
            recommended_app_destinations=_registered_destination_candidates(bundle),
            disclaimer_class="saved_list_empty",
        )

    def _partition_evidence(
        self,
        bundle: CopilotEvidenceBundleV1,
    ) -> tuple[list[CopilotEvidenceV1], list[CopilotEvidenceV1]]:
        explicit_opposing = set(bundle.contradictory_evidence_ids)
        preferred_support = set(bundle.supporting_evidence_ids)
        positive: list[CopilotEvidenceV1] = []
        neutral: list[CopilotEvidenceV1] = []
        opposing: list[CopilotEvidenceV1] = []
        for item in bundle.evidence:
            statement = _evidence_statement(item)
            if statement is None:
                continue
            polarity = _polarity(statement)
            if item.evidence_id in explicit_opposing or item.interpretation_class.value == "contradiction":
                opposing.append(item)
            elif (
                bundle.intent.intent == CopilotIntentType.WATCHLIST_REVIEW
                and _is_watchlist_caution_evidence(item)
            ):
                opposing.append(item)
            elif polarity < 0:
                opposing.append(item)
            elif polarity > 0:
                positive.append(item)
            else:
                neutral.append(item)

        ordered_support = [
            item
            for item in [*positive, *neutral]
            if not preferred_support or item.evidence_id in preferred_support
        ]
        if not ordered_support:
            ordered_support = [*positive, *neutral]
        if bundle.intent.intent == CopilotIntentType.RESEARCH_QUERY:
            selection = [item for item in ordered_support if "selection reason" in item.metric.casefold()]
            ordered_support = [*selection, *[item for item in ordered_support if item not in selection]]
        return _dedupe_evidence(ordered_support), _dedupe_evidence(opposing)

    def _evidence_factors(self, evidence: Iterable[CopilotEvidenceV1]) -> list[CopilotReasoningFactorV1]:
        factors: list[CopilotReasoningFactorV1] = []
        for item in evidence:
            statement = _evidence_statement(item)
            if statement:
                factors.append(
                    CopilotReasoningFactorV1(statement=statement, evidence_ids=[item.evidence_id])
                )
            if len(factors) >= self.maximum_factors:
                break
        return factors

    def _conditions(
        self,
        bundle: CopilotEvidenceBundleV1,
        evidence_by_id: dict[str, CopilotEvidenceV1],
    ) -> tuple[list[CopilotReasoningFactorV1], list[CopilotReasoningFactorV1]]:
        confirmation: list[CopilotReasoningFactorV1] = []
        invalidation: list[CopilotReasoningFactorV1] = []
        for result in bundle.agent_results:
            for level in result.levels:
                if level.evidence_id not in evidence_by_id:
                    continue
                factor = _level_factor(level)
                if factor is None:
                    continue
                label = level.label.casefold()
                if any(term in label for term in ("confirm", "breakout", "resistance")):
                    confirmation.append(factor)
                elif any(term in label for term in ("invalid", "risk", "stop", "support")):
                    invalidation.append(factor)
        return _dedupe_factors(confirmation), _dedupe_factors(invalidation)

    def _trusted_agent_conditions(
        self,
        bundle: CopilotEvidenceBundleV1,
        kind: str,
    ) -> list[CopilotReasoningFactorV1]:
        factors: list[CopilotReasoningFactorV1] = []
        for result in bundle.agent_results:
            if result.agent.value != "report":
                continue
            result_ids = [item.evidence_id for item in result.evidence[:3]]
            for conclusion in result.conclusions:
                text = _safe_external_text(conclusion)
                if text is None:
                    continue
                if kind == "scenario" and not any(
                    term in text.casefold() for term in ("requires", "scenario", "condition")
                ):
                    continue
                factors.append(
                    CopilotReasoningFactorV1(
                        statement=f"The validated report states: {text}",
                        evidence_ids=result_ids,
                    )
                )
        return factors

    def _follow_up_conditions(
        self,
        bundle: CopilotEvidenceBundleV1,
        session: CopilotSessionContextV1 | None,
        confirmation: list[CopilotReasoningFactorV1],
        invalidation: list[CopilotReasoningFactorV1],
    ) -> tuple[
        list[CopilotReasoningFactorV1],
        list[CopilotReasoningFactorV1],
        list[str],
    ]:
        missing: list[str] = []
        sub_intent = bundle.intent.sub_intent.casefold()
        if sub_intent == "confirmation" and not confirmation:
            missing.append("No cited confirmation condition is available for this follow-up.")
        elif sub_intent in {"invalidation", "risk"} and not invalidation:
            missing.append("No cited invalidation condition is available for this follow-up.")
        if session and session.relevant_evidence_ids:
            current_ids = {item.evidence_id for item in bundle.evidence}
            if not current_ids.intersection(session.relevant_evidence_ids):
                missing.append(
                    "Prior-turn evidence is not present in this evidence bundle, so it was not reused."
                )
        return confirmation, invalidation, missing

    def _stance(
        self,
        intent: CopilotIntentType,
        bundle: CopilotEvidenceBundleV1,
        constrained: bool,
    ) -> CopilotStance:
        if not bundle.evidence:
            return CopilotStance.INSUFFICIENT_EVIDENCE
        if intent == CopilotIntentType.STOCK_DECISION_SUPPORT:
            return (
                CopilotStance.INSUFFICIENT_EVIDENCE
                if constrained
                else CopilotStance.WAIT_FOR_CONFIRMATION
            )
        if intent in {CopilotIntentType.STOCK_COMPARISON, CopilotIntentType.INDEX_ANALYSIS}:
            return CopilotStance.INSUFFICIENT_EVIDENCE if constrained else CopilotStance.MIXED
        if intent == CopilotIntentType.STOCK_ANALYSIS:
            return CopilotStance.INSUFFICIENT_EVIDENCE if constrained else CopilotStance.MONITOR
        if intent in {CopilotIntentType.MARKET_STATE, CopilotIntentType.MARKET_EXPLANATION}:
            if constrained:
                return CopilotStance.CAUTIOUS
            state_text = " ".join(
                _safe_scalar_text(item.current_state if item.current_state is not None else item.value) or ""
                for item in bundle.evidence
                if item.category.value in {"market", "breadth", "risk"}
            ).casefold()
            if any(term in state_text for term in ("defensive", "risk-off")):
                return CopilotStance.DEFENSIVE
            if any(term in state_text for term in ("cautious", "weak", "deteriorating")):
                return CopilotStance.CAUTIOUS
            if any(term in state_text for term in ("selective", "mixed", "narrow")):
                return CopilotStance.SELECTIVELY_CONSTRUCTIVE
            if any(term in state_text for term in ("constructive", "healthy", "improving", "risk-on")):
                return CopilotStance.CONSTRUCTIVE
        return CopilotStance.NEUTRAL

    def _direct_answer(
        self,
        intent: CopilotIntentType,
        bundle: CopilotEvidenceBundleV1,
        stance: CopilotStance,
        constrained: bool,
    ) -> str:
        if not bundle.evidence:
            return "There is insufficient validated evidence to answer this reliably."
        if intent == CopilotIntentType.STOCK_DECISION_SUPPORT:
            if constrained:
                return (
                    "There is insufficient current, complete evidence to assess the setup. "
                    "Wait for confirmation."
                )
            return "Wait for confirmation. The setup remains conditional on the cited confirmation and risk levels."
        if intent == CopilotIntentType.MARKET_STATE:
            label = stance.value.replace("_", " ")
            return f"The validated engine evidence supports a {label} market posture."
        if intent == CopilotIntentType.MARKET_EXPLANATION:
            posture_label = "stored" if constrained else "current"
            return (
                f"The {posture_label} posture reflects the cited engine observations and contradictions; "
                "the evidence supports association, not an unvalidated causal claim."
            )
        if intent == CopilotIntentType.BREADTH_QUERY:
            value = _metric_value(bundle.evidence, "breadth classification")
            return (
                f"The breadth engine classifies participation as {value}."
                if value
                else "The breadth engine evidence is available below, with any divergence kept explicit."
            )
        if intent == CopilotIntentType.SECTOR_ANALYSIS:
            return "The deterministic sector ranking evidence identifies the current leadership structure below."
        if intent == CopilotIntentType.THEME_ANALYSIS:
            return "The deterministic theme evidence identifies the current relative leadership structure below."
        if intent == CopilotIntentType.STOCK_ANALYSIS:
            return "The stock snapshot supports a monitoring assessment; use the cited engine conditions and risks."
        if intent in {CopilotIntentType.STOCK_COMPARISON, CopilotIntentType.INDEX_ANALYSIS}:
            return "The comparison is mixed; the cited engine evidence should be compared on the same horizon."
        if intent == CopilotIntentType.WATCHLIST_REVIEW:
            candidates = [
                item.entity
                for item in _watchlist_attention_evidence(bundle)[: self.maximum_factors]
            ]
            if candidates:
                names = _join_names(candidates)
                verb = "is" if len(candidates) == 1 else "are"
                return (
                    f"{names} {verb} the attention candidate"
                    f"{'s' if len(candidates) != 1 else ''} identified by the cited deterministic "
                    "setup/risk status evidence. This is an unranked monitoring review; "
                    "holdings were not inferred."
                )
            return (
                "There is insufficient cited caution-status evidence to single out a saved stock; "
                "continue monitoring, and holdings were not inferred."
            )
        if intent == CopilotIntentType.REPORT_QUERY:
            if bundle.intent.sub_intent == "report_change":
                if any("No prior immutable report" in value for value in bundle.unavailable_evidence):
                    return "No prior immutable report is available, so no change narrative can be validated."
                return "The change since the prior report is limited to the stored, cited report-change evidence below."
            return "The latest validated report thesis is supported by the cited evidence and remains conditional on its risks."
        if intent == CopilotIntentType.RESEARCH_QUERY:
            return "The latest validated Research Focus includes supporting evidence, a counter-thesis, and invalidation conditions."
        if intent == CopilotIntentType.SCENARIO_QUERY:
            return "The validated report frames scenarios conditionally; no scenario is treated as a prediction."
        if intent == CopilotIntentType.RISK_QUERY:
            return "The validated report evidence surfaces the key risks and invalidation conditions below."
        if intent == CopilotIntentType.MACRO_QUERY:
            return "The report-backed macro evidence provides context; the relationships are not presented as unvalidated causality."
        if intent == CopilotIntentType.FOLLOW_UP:
            return {
                "confirmation": "Confirmation depends on the cited conditions below.",
                "invalidation": "The cited invalidation conditions are shown below.",
                "risk": "The cited risk and invalidation evidence is shown below.",
                "navigation": "The relevant registered app destination is available below.",
            }.get(
                bundle.intent.sub_intent.casefold(),
                "The prior conclusion is explained only by the evidence cited in this response.",
            )
        return "The available validated evidence supports a monitoring-only conclusion."

    @staticmethod
    def _thesis(
        intent: CopilotIntentType,
        direct_answer: str,
        stance: CopilotStance,
    ) -> str:
        if intent == CopilotIntentType.STOCK_DECISION_SUPPORT:
            return (
                "The setup should remain in monitoring status until deterministic confirmation is present; "
                "opposing evidence and invalidation conditions remain material."
            )
        if intent == CopilotIntentType.SCENARIO_QUERY:
            return "Scenario analysis is conditional and must be evaluated against confirmation and invalidation evidence."
        if stance == CopilotStance.INSUFFICIENT_EVIDENCE:
            return "The evidence is insufficient for a reliable market conclusion."
        return direct_answer

    @staticmethod
    def _confidence(
        intent: CopilotIntentType,
        bundle: CopilotEvidenceBundleV1,
        missing: list[str],
        constrained: bool,
    ) -> CopilotConfidenceLabel:
        if intent in {CopilotIntentType.APP_NAVIGATION, CopilotIntentType.EDUCATIONAL_QUERY}:
            return CopilotConfidenceLabel.HIGH
        if constrained or missing or not bundle.evidence:
            return CopilotConfidenceLabel.LIMITED
        if len(bundle.evidence) >= 3:
            return CopilotConfidenceLabel.MODERATE
        return CopilotConfidenceLabel.LIMITED


def build_reasoning(
    bundle: CopilotEvidenceBundleV1,
    *,
    session: CopilotSessionContextV1 | None = None,
    engine: CopilotReasoningEngine | None = None,
) -> CopilotReasoningV1:
    """Functional entry point for dependency-light callers."""

    return (engine or CopilotReasoningEngine()).synthesize(bundle, session=session)


def safe_reasoning_fallback(
    bundle: CopilotEvidenceBundleV1,
    *,
    intent: CopilotIntentV1 | None = None,
    reasons: Iterable[str] = (),
) -> CopilotReasoningV1:
    """Return a contract-valid fallback containing no promoted market claim."""

    selected_intent = intent or bundle.intent
    intent_type = CopilotIntentType(selected_intent.intent)
    if intent_type == CopilotIntentType.PORTFOLIO_QUERY:
        direct = PORTFOLIO_FALLBACK
        disclaimer = "portfolio_data_unavailable"
    elif intent_type == CopilotIntentType.APP_NAVIGATION:
        destinations = _registered_destination_candidates(bundle)
        destination = destinations[0] if destinations else CopilotDestination.MARKET_OVERVIEW
        direct = f"Open {destination.value.replace('_', ' ').title()}."
        disclaimer = "app_navigation"
    elif intent_type == CopilotIntentType.STOCK_DECISION_SUPPORT:
        direct = (
            "There is insufficient validated evidence to assess the setup reliably. "
            "Wait for confirmation."
        )
        disclaimer = "educational_market_decision_support"
    else:
        direct = "I could not validate a grounded answer. No market conclusion has been promoted."
        disclaimer = "grounding_validation_fallback"
    missing = [*bundle.unavailable_evidence, *[str(value) for value in reasons if value]]
    if not missing:
        missing = ["Response validation did not pass."]
    return CopilotReasoningV1(
        direct_answer=direct,
        stance=CopilotStance.INSUFFICIENT_EVIDENCE,
        confidence_label=CopilotConfidenceLabel.LIMITED,
        thesis="No market conclusion is presented because grounding validation did not pass.",
        missing_evidence=list(dict.fromkeys(missing)),
        recommended_app_destinations=_registered_destination_candidates(bundle),
        disclaimer_class=disclaimer,
    )


def _missing_evidence(bundle: CopilotEvidenceBundleV1) -> list[str]:
    values = list(bundle.unavailable_evidence)
    for result in bundle.agent_results:
        values.extend(result.missing_data)
    safe_values: list[str] = []
    for value in values:
        safe = _safe_external_text(value)
        if safe:
            safe_values.append(safe)
    return list(dict.fromkeys(safe_values))


def _watchlist_membership_is_confirmed_empty(bundle: CopilotEvidenceBundleV1) -> bool:
    return any(
        result.agent.value == "watchlist"
        and result.metrics.get("membership_state") == "empty"
        for result in bundle.agent_results
    )


def _watchlist_attention_evidence(
    bundle: CopilotEvidenceBundleV1,
) -> list[CopilotEvidenceV1]:
    """Return at most one deterministic caution status per saved symbol.

    Setup status is preferred over risk level when both already exist.  The
    original entity order is retained, so this is a filter rather than a new
    watchlist score or rank.
    """

    by_entity: dict[str, CopilotEvidenceV1] = {}
    for item in bundle.evidence:
        if not _is_watchlist_caution_evidence(item):
            continue
        entity_key = item.entity.casefold()
        existing = by_entity.get(entity_key)
        if existing is None:
            by_entity[entity_key] = item
        elif (
            existing.metric.casefold() != "setup status"
            and item.metric.casefold() == "setup status"
        ):
            by_entity[entity_key] = item
    return list(by_entity.values())


def _is_watchlist_caution_evidence(item: CopilotEvidenceV1) -> bool:
    value = _safe_scalar_text(
        item.current_state if item.current_state is not None else item.value
    )
    if value is None:
        return False
    metric = item.metric.casefold().strip()
    lowered = value.casefold()
    if metric == "setup status":
        return any(term in lowered for term in _WATCHLIST_CAUTION_STATUS_TERMS)
    if metric == "risk level":
        return any(term in lowered for term in _WATCHLIST_CAUTION_RISK_TERMS)
    return False


def _join_names(values: list[str]) -> str:
    if len(values) <= 1:
        return values[0] if values else ""
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return f"{', '.join(values[:-1])}, and {values[-1]}"


def _is_constrained(bundle: CopilotEvidenceBundleV1) -> bool:
    summary = bundle.freshness_summary
    try:
        state = CopilotFreshnessState(summary.overall_state)
    except ValueError:
        return True
    return state in _CONSTRAINED_STATES or any(
        (
            summary.stale_count,
            summary.partial_count,
            summary.unavailable_count,
            summary.test_count,
        )
    )


def _evidence_statement(item: CopilotEvidenceV1) -> str | None:
    entity = _safe_external_text(item.entity, maximum_length=100)
    metric = _safe_external_text(item.metric, maximum_length=140)
    value = _safe_scalar_text(item.current_state if item.current_state is not None else item.value)
    unit = _safe_external_text(item.unit or "", maximum_length=50)
    if not entity or not metric or value is None:
        return None
    display_value = value.rstrip(".")
    suffix = f" {unit}" if unit and unit.casefold() not in display_value.casefold() else ""
    return f"{entity}: {metric} is {display_value}{suffix}."


def _level_factor(level: CopilotLevelV1) -> CopilotReasoningFactorV1 | None:
    label = _safe_external_text(level.label, maximum_length=120)
    value = _safe_scalar_text(level.value)
    unit = _safe_external_text(level.unit or "", maximum_length=50)
    if not label or value is None:
        return None
    display_value = value.rstrip(".")
    suffix = f" {unit}" if unit and unit.casefold() not in display_value.casefold() else ""
    return CopilotReasoningFactorV1(
        statement=f"The validated {label} is {display_value}{suffix}.",
        evidence_ids=[level.evidence_id],
    )


def _safe_scalar_text(value: Any) -> str | None:
    if value is None or isinstance(value, (dict, list, tuple, set)):
        return None
    if isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, float):
        # Preserve the exact engine value. Rounding here would create a new
        # number and correctly fail numerical-grounding validation.
        text = str(value)
    else:
        text = str(value)
    return _safe_external_text(text, maximum_length=360)


def _safe_external_text(value: Any, *, maximum_length: int = 360) -> str | None:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    if any(
        (
            contains_prompt_injection(text),
            contains_secret(text),
            bool(recommendation_violations(text)),
            bool(ownership_violations(text)),
            bool(causality_violations(text)),
        )
    ):
        return None
    if len(text) <= maximum_length:
        return text
    prefix = text[: max(1, maximum_length - 1)].rsplit(" ", 1)[0].rstrip(" ,;:.")
    return f"{prefix}…"


def _polarity(statement: str) -> int:
    lowered = statement.casefold()
    negative = any(term in lowered for term in _NEGATIVE_TERMS)
    positive = any(term in lowered for term in _POSITIVE_TERMS)
    if negative and not positive:
        return -1
    if positive and not negative:
        return 1
    return 0


def _metric_value(evidence: list[CopilotEvidenceV1], metric: str) -> str | None:
    for item in evidence:
        if item.metric.casefold() == metric.casefold():
            return _safe_scalar_text(item.current_state if item.current_state is not None else item.value)
    return None


def _first_safe_agent_text(bundle: CopilotEvidenceBundleV1, *, agent_name: str) -> str | None:
    for result in bundle.agent_results:
        if result.agent.value != agent_name:
            continue
        for value in [*result.conclusions, *result.observations]:
            safe = _safe_external_text(value)
            if safe:
                return safe
    return None


def _related_research(bundle: CopilotEvidenceBundleV1) -> list[str]:
    categories = {item.category.value for item in bundle.evidence}
    related: list[str] = []
    if categories.intersection({"report", "risk", "macro"}):
        related.append("Latest Report")
    if "research" in categories:
        related.append("Research Focus")
    return related


def _registered_destination_candidates(bundle: CopilotEvidenceBundleV1) -> list[CopilotDestination]:
    values = [*bundle.plan.deep_link_requirements, *bundle.deep_link_targets]
    result: list[CopilotDestination] = []
    for value in values:
        try:
            destination = CopilotDestination(value)
        except ValueError:
            continue
        if destination not in result:
            result.append(destination)
    return result


def _dedupe_evidence(values: Iterable[CopilotEvidenceV1]) -> list[CopilotEvidenceV1]:
    result: dict[str, CopilotEvidenceV1] = {}
    for value in values:
        result.setdefault(value.evidence_id, value)
    return list(result.values())


def _dedupe_factors(values: Iterable[CopilotReasoningFactorV1]) -> list[CopilotReasoningFactorV1]:
    result: dict[tuple[str, tuple[str, ...]], CopilotReasoningFactorV1] = {}
    for value in values:
        key = (value.statement, tuple(value.evidence_ids))
        result.setdefault(key, value)
    return list(result.values())
