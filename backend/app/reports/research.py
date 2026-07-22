from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from app.reports.document import (
    ResearchCandidate,
    ResearchCandidateScore,
    ResearchSelectionDecision,
    ResearchSelectionExplanation,
    UserRelevanceEvidence,
)


RESEARCH_SCORE_WEIGHTS: dict[str, float] = {
    "market_significance": 0.15,
    "leadership_weakness_magnitude": 0.15,
    "change_acceleration": 0.15,
    "persistence": 0.10,
    "breadth_confirmation": 0.10,
    "volume_confirmation": 0.05,
    "relative_divergence": 0.10,
    "user_relevance": 0.15,
    "data_completeness": 0.03,
    "freshness": 0.02,
}

PRIMARY_MATERIALITY_THRESHOLD = 60.0
SECONDARY_MATERIALITY_THRESHOLD = 65.0
STALE_STATES = {"stale", "unavailable"}
POSITIVE_DIRECTIONS = {"leading", "emerging"}
NEGATIVE_DIRECTIONS = {"weakening", "lagging", "breakdown"}


@dataclass(frozen=True)
class ResearchEngineResult:
    candidates: list[ResearchCandidate]
    decision: ResearchSelectionDecision


class ResearchCandidateEngine:
    """Build and rank research subjects from one frozen report input.

    The engine does not fetch data and does not infer catalysts. A fixed set of
    weights is applied to both positive and negative candidates, with magnitude
    measured in the candidate's supported direction.
    """

    def __init__(self, report: Any, previous_snapshot: dict[str, Any] | None = None) -> None:
        self.report = report.model_dump(mode="json") if hasattr(report, "model_dump") else dict(report)
        self.previous = previous_snapshot or {}
        self.preferences = self.report.get("research_preferences") or {}
        self.watchlist_items = [item for item in ((self.report.get("watchlist_summary") or {}).get("items") or []) if isinstance(item, dict)]
        self.watch_by_symbol = {
            str(item.get("symbol") or item.get("ticker") or "").upper(): item
            for item in self.watchlist_items
            if item.get("symbol") or item.get("ticker")
        }
        self.saved_stocks = self._saved_values("saved_stocks", fallback="symbols_requested", uppercase=True)
        self.saved_sectors = self._saved_values("saved_sectors")
        self.saved_themes = self._saved_values("saved_themes")
        self.taxonomy = [item for item in self.report.get("security_taxonomy") or [] if isinstance(item, dict)]

    def build(self) -> ResearchEngineResult:
        candidates = [*self._theme_candidates(), *self._sector_candidates(), *self._security_candidates()]
        candidates = sorted(candidates, key=candidate_sort_key)
        decision = select_research_focus(candidates)
        return ResearchEngineResult(candidates=candidates, decision=decision)

    def _theme_candidates(self) -> list[ResearchCandidate]:
        context = self.report.get("theme_intelligence") or {}
        rows = [row for row in context.get("items") or [] if isinstance(row, dict)]
        previous_rows = index_rows(self.previous.get("themeRanking") or [], "theme_id", "display_name")
        quality = normalize_quality(context.get("source_state"))
        result: list[ResearchCandidate] = []
        for row in rows:
            theme_id = normalize_id(row.get("theme_id") or row.get("display_name"))
            if not theme_id:
                continue
            prior = previous_rows.get(theme_id) or previous_rows.get(normalize_id(row.get("display_name"))) or {}
            classification = str(row.get("classification") or "Unavailable")
            direction = research_direction(classification, number(path(row, "relative_strength", "vs_spy_1m")))
            members = [enrich_member(item, self.taxonomy) for item in row.get("members") or [] if isinstance(item, dict)]
            parents = [normalize_id(item) for item in path(row, "definition", "parent_sector_ids") or []]
            user = self._user_relevance(theme_id, members, parents=parents, exact_saved=theme_id in self.saved_themes)
            rank = integer(row.get("rank"))
            previous_rank = integer(prior.get("rank"))
            relative_strength = number(path(row, "relative_strength", "vs_spy_1m"))
            previous_rs = number(path(prior, "relative_strength", "vs_spy_1m"))
            returns = {period: number(path(row, "performance", period)) for period in ("1d", "1w", "1m", "3m", "6m", "1y")}
            breadth = number(path(row, "breadth", "percent_above_ema50"))
            previous_breadth = number(path(prior, "breadth", "percent_above_ema50"))
            participation = number(path(row, "participation", "positive_return_participation_pct"))
            previous_participation = number(path(prior, "participation", "positive_return_participation_pct"))
            momentum = number(path(row, "component_scores", "momentum"))
            rotation_change = rotation_delta(row)
            candidate = build_candidate(
                candidate_id=f"theme:{theme_id}", name=str(row.get("display_name") or theme_id), category="theme",
                direction=direction, rank=rank, previous_rank=previous_rank, universe_size=len(rows),
                relative_strength=relative_strength,
                relative_strength_change=delta(relative_strength, previous_rs) if previous_rs is not None else rotation_change,
                returns=returns, breadth=breadth, breadth_change=delta(breadth, previous_breadth), momentum=momentum,
                participation=participation, participation_change=delta(participation, previous_participation),
                volume=None, qualifying_count=integer(row.get("eligible_count")) or len(members), constituents=members,
                taxonomy_chain=theme_taxonomy_chain(row, members), mapping_type="validated_theme_membership",
                user=user, freshness=str(context.get("market_date") or "unknown"), quality=quality,
                coverage=number(row.get("coverage_ratio")), previous_classification=str(prior.get("classification") or "") or None,
                current_classification=classification, has_price_figure=True,
            )
            result.append(candidate)
        return result

    def _sector_candidates(self) -> list[ResearchCandidate]:
        dashboard = self.report.get("sector_dashboard") or {}
        rows = [row for row in dashboard.get("sectors") or [] if isinstance(row, dict)]
        previous_rows = index_rows(self.previous.get("sectorRanking") or [], "id", "name")
        quality = normalize_quality(dashboard.get("source"))
        result: list[ResearchCandidate] = []
        for row in rows:
            sector_id = normalize_id(row.get("id") or row.get("sector_id") or row.get("name"))
            if not sector_id:
                continue
            metadata = row.get("metadata") or {}
            prior = previous_rows.get(sector_id) or previous_rows.get(normalize_id(row.get("name"))) or {}
            prior_metadata = prior.get("metadata") or {}
            classification = str(metadata.get("status") or row.get("classification") or "Unavailable")
            relative_strength = number(metadata.get("relative_strength_1m"))
            direction = research_direction(classification, relative_strength)
            members = [
                {
                    "ticker": str(item.get("ticker") or "").upper(),
                    "company_name": item.get("company_name"),
                    "sector": item.get("sector"),
                    "sector_id": item.get("sector_id"),
                    "industry": item.get("industry"),
                    "mapping_type": "validated_security_master_membership",
                }
                for item in self.taxonomy
                if normalize_id(item.get("sector_id") or item.get("sector")) == sector_id and item.get("ticker")
            ]
            user = self._user_relevance(sector_id, members, exact_saved=sector_id in self.saved_sectors)
            rotation = row.get("rotation") or {}
            current_rotation = rotation.get("1m") if isinstance(rotation.get("1m"), dict) else {}
            momentum = normalize_rotation_score(number(current_rotation.get("relative_momentum")))
            returns = {period: number((row.get("returns") or {}).get(period)) for period in ("1d", "1w", "1m", "3m", "6m", "1y")}
            rank = integer(metadata.get("rank") or row.get("rank"))
            previous_rank = integer(prior_metadata.get("rank") or prior.get("rank"))
            breadth = number(metadata.get("percent_above_50ema"))
            prior_breadth = number(prior_metadata.get("percent_above_50ema"))
            participation = number(metadata.get("participation_percent") or path(row, "participation", "positive_return_participation_pct"))
            prior_participation = number(prior_metadata.get("participation_percent") or path(prior, "participation", "positive_return_participation_pct"))
            candidate = build_candidate(
                candidate_id=f"sector:{sector_id}", name=str(row.get("name") or sector_id), category="sector",
                direction=direction, rank=rank, previous_rank=previous_rank, universe_size=len(rows),
                relative_strength=relative_strength, relative_strength_change=delta(relative_strength, number(prior_metadata.get("relative_strength_1m"))),
                returns=returns, breadth=breadth, breadth_change=delta(breadth, prior_breadth), momentum=momentum,
                participation=participation, participation_change=delta(participation, prior_participation),
                volume=None, qualifying_count=integer(metadata.get("successful_symbols")) or len(members), constituents=members,
                taxonomy_chain=sector_taxonomy_chain(str(row.get("name") or sector_id), members), mapping_type="validated_security_master_membership",
                user=user, freshness=str(metadata.get("as_of") or dashboard.get("market_date") or "unknown"), quality=quality,
                coverage=percentage_ratio(metadata.get("coverage_percent")), previous_classification=str(prior_metadata.get("status") or "") or None,
                current_classification=classification, has_price_figure=True,
            )
            result.append(candidate)
        return result

    def _security_candidates(self) -> list[ResearchCandidate]:
        previous_rows = index_rows(self.previous.get("watchlistSummary") or [], "symbol", "ticker")
        charts = {
            str(item.get("symbol") or item.get("ticker") or "").upper(): item
            for item in self.report.get("stock_charts") or []
            if isinstance(item, dict) and (item.get("symbol") or item.get("ticker"))
        }
        result: list[ResearchCandidate] = []
        for symbol in sorted(self.saved_stocks):
            item = self.watch_by_symbol.get(symbol)
            if not item:
                continue
            prior = previous_rows.get(normalize_id(symbol)) or {}
            current_score = number(item.get("overall_score") or item.get("score"))
            current_change = number(item.get("change_percent") or item.get("quote_change_percent"))
            prior_score = number(prior.get("score") or prior.get("overall_score"))
            status = str(item.get("signal") or item.get("rating") or item.get("overall_status") or "Monitoring")
            prior_status = str(prior.get("signal") or prior.get("rating") or prior.get("status") or "")
            direction = security_direction(current_score, current_change, status)
            taxonomy = next((row for row in self.taxonomy if str(row.get("ticker") or "").upper() == symbol), {})
            user = UserRelevanceEvidence(tier="high", score=100, saved_security_symbols=[symbol], rationale=["The exact security is saved on the user's watchlist."])
            major_change = (bool(prior_status) and prior_status.lower() != status.lower()) or abs((current_score or 0) - (prior_score or current_score or 0)) >= 15 or abs(current_change or 0) >= 4
            candidate = build_candidate(
                candidate_id=f"security:{symbol.lower()}", name=symbol, category="individual_security", direction=direction,
                rank=None, previous_rank=None, universe_size=max(1, len(self.saved_stocks)), relative_strength=number(item.get("rs_rank")),
                relative_strength_change=None, returns={"1d": current_change, "1w": None, "1m": None, "3m": None, "6m": None, "1y": None},
                breadth=None, breadth_change=None, momentum=current_score, volume=number(item.get("relative_volume")),
                participation=None, participation_change=None,
                qualifying_count=1, constituents=[{"ticker": symbol, **taxonomy}], taxonomy_chain=security_taxonomy_chain(symbol, taxonomy),
                mapping_type="validated_security_master_membership" if taxonomy else "saved_security_membership",
                user=user, freshness=str(item.get("analysis_updated_at") or item.get("updated_at") or item.get("as_of") or "unknown"),
                quality=normalize_quality(item.get("source_state")), coverage=1.0 if not item.get("missing_sections") else 0.6,
                previous_classification=prior_status or None, current_classification=status, has_price_figure=len((charts.get(symbol) or {}).get("price_history") or []) >= 30,
                major_individual_change=major_change,
            )
            result.append(candidate)
        return result

    def _saved_values(self, key: str, *, fallback: str | None = None, uppercase: bool = False) -> set[str]:
        values = self.preferences.get(key)
        if values is None and fallback:
            values = (self.report.get("watchlist_summary") or {}).get(fallback)
        normalized = set()
        for value in values or []:
            text = str(value or "").strip()
            if text:
                normalized.add(text.upper() if uppercase else normalize_id(text))
        return normalized

    def _user_relevance(
        self,
        group_id: str,
        members: list[dict[str, Any]],
        *,
        parents: list[str] | None = None,
        exact_saved: bool = False,
    ) -> UserRelevanceEvidence:
        member_symbols = {str(item.get("ticker") or "").upper() for item in members}
        direct_saved = sorted(member_symbols.intersection(self.saved_stocks))
        fresh_saved = [symbol for symbol in direct_saved if not watchlist_item_stale(self.watch_by_symbol.get(symbol))]
        stale = bool(direct_saved) and not fresh_saved
        saved_parent = bool(set(parents or []).intersection(self.saved_sectors))
        rationale: list[str] = []
        score = 0.0
        tier = "low"
        if exact_saved:
            score, tier = 100.0, "high"
            rationale.append("The exact sector or theme is saved.")
        if len(fresh_saved) >= 3:
            score, tier = 100.0, "high"
            rationale.append(f"{len(fresh_saved)} saved securities have validated membership in the subject.")
        elif fresh_saved and score < 100:
            score, tier = max(score, 60.0), "moderate"
            rationale.append(f"{len(fresh_saved)} saved securit{'y' if len(fresh_saved) == 1 else 'ies'} has validated membership in the subject.")
        if saved_parent and score < 100:
            score, tier = max(score, 60.0), "moderate"
            rationale.append("A validated parent sector is saved.")
        if stale:
            rationale.append("Saved-security overlap is stale or unavailable and does not elevate the score.")
        if not rationale:
            rationale.append("No direct saved-item overlap is available.")
        return UserRelevanceEvidence(
            tier=tier, score=score, exact_saved_group=exact_saved, saved_parent_group=saved_parent,
            saved_security_symbols=fresh_saved, stale=stale, rationale=rationale,
        )


def build_candidate(
    *,
    candidate_id: str,
    name: str,
    category: str,
    direction: str,
    rank: int | None,
    previous_rank: int | None,
    universe_size: int,
    relative_strength: float | None,
    relative_strength_change: float | None,
    returns: dict[str, float | None],
    breadth: float | None,
    breadth_change: float | None,
    participation: float | None,
    participation_change: float | None,
    momentum: float | None,
    volume: float | None,
    qualifying_count: int,
    constituents: list[dict[str, Any]],
    taxonomy_chain: list[dict[str, str]],
    mapping_type: str,
    user: UserRelevanceEvidence,
    freshness: str,
    quality: str,
    coverage: float | None,
    previous_classification: str | None,
    current_classification: str,
    has_price_figure: bool,
    major_individual_change: bool = False,
) -> ResearchCandidate:
    rank_change = previous_rank - rank if rank is not None and previous_rank is not None else None
    persistence_score = persistence(direction, [returns.get(period) for period in ("1w", "1m", "3m")], relative_strength)
    completeness_values = [rank, relative_strength, returns.get("1m"), returns.get("3m"), breadth, momentum, coverage]
    if category == "individual_security":
        completeness_values = [returns.get("1d"), relative_strength, momentum, coverage]
    completeness = sum(value is not None for value in completeness_values) / max(1, len(completeness_values))
    market_significance = significance(direction, rank, universe_size, returns.get("1d"), category)
    magnitude = directional_magnitude(direction, momentum, relative_strength, returns.get("1m"), current_classification)
    change_score = acceleration(rank_change, relative_strength_change, breadth_change, previous_classification, current_classification)
    breadth_score = directional_breadth(direction, breadth)
    relative_score = min(100.0, abs(relative_strength or 0) * 10) if relative_strength is not None else None
    freshness_score = 100.0 if quality in {"live", "cached", "test"} and freshness != "unknown" else 65.0 if quality in {"mixed", "partial"} else 0.0
    dimensions: dict[str, float | None] = {
        "market_significance": market_significance,
        "leadership_weakness_magnitude": magnitude,
        "change_acceleration": change_score,
        "persistence": persistence_score,
        "breadth_confirmation": breadth_score,
        "volume_confirmation": volume,
        "relative_divergence": relative_score,
        "user_relevance": user.score,
        "data_completeness": completeness * 100,
        "freshness": freshness_score,
    }
    contributions = {
        key: round((value or 0) * RESEARCH_SCORE_WEIGHTS[key], 3)
        for key, value in dimensions.items()
    }
    total = round(sum(contributions.values()), 2)
    figure_types = ["research_priority_comparison"]
    if has_price_figure or any(returns.get(period) is not None for period in ("1w", "1m", "3m")):
        figure_types.append("subject_relative_strength")
    if category in {"sector", "theme"} and qualifying_count >= 3:
        figure_types.append("constituent_or_peer_comparison")
    disqualifiers: list[str] = []
    if quality in STALE_STATES:
        disqualifiers.append("stale_or_unavailable_subject_data")
    if completeness < 0.60:
        disqualifiers.append("data_completeness_below_60_percent")
    if len(figure_types) < 2:
        disqualifiers.append("fewer_than_two_supported_figures")
    if category in {"sector", "theme", "industry_group", "security_cluster"} and qualifying_count < 3:
        disqualifiers.append("fewer_than_three_qualifying_constituents")
    if category == "individual_security" and not major_individual_change:
        disqualifiers.append("individual_security_change_not_material")
    if current_classification.lower() == "unavailable":
        disqualifiers.append("classification_unavailable")
    if direction == "divergence" and abs(relative_strength or 0) < 3:
        disqualifiers.append("neutral_without_material_divergence")
    if total < PRIMARY_MATERIALITY_THRESHOLD:
        disqualifiers.append("materiality_score_below_threshold")
    evidence_ids = evidence_ids_for(candidate_id, {
        "rank": rank, "relative-strength": relative_strength, "return-1w": returns.get("1w"),
        "return-1m": returns.get("1m"), "return-3m": returns.get("3m"), "breadth": breadth,
        "momentum": momentum, "coverage": coverage, "daily-change": returns.get("1d"),
    })
    return ResearchCandidate(
        candidate_id=candidate_id, name=name, category=category, direction=direction,
        current_rank=rank, previous_rank=previous_rank, rank_change=rank_change,
        current_relative_strength=relative_strength, relative_strength_change=relative_strength_change,
        returns=returns, breadth=breadth, breadth_change=breadth_change, momentum=momentum,
        participation=participation, participation_change=participation_change,
        volume_confirmation=volume, persistence=persistence_score, market_relative_divergence=relative_strength,
        qualifying_constituent_count=qualifying_count, constituents=constituents, taxonomy_chain=taxonomy_chain,
        mapping_type=mapping_type, user_relevance=user, freshness=freshness, source_quality=quality,
        data_completeness=round(completeness, 4), evidence_ids=evidence_ids,
        supported_figure_types=figure_types, disqualifying_conditions=sorted(set(disqualifiers)),
        score=ResearchCandidateScore(
            total=total, materiality_threshold=PRIMARY_MATERIALITY_THRESHOLD, weights=RESEARCH_SCORE_WEIGHTS,
            dimension_scores=dimensions, weighted_contributions=contributions,
            missing_dimensions=sorted(key for key, value in dimensions.items() if value is None),
        ),
    )


def select_research_focus(candidates: list[ResearchCandidate]) -> ResearchSelectionDecision:
    qualified = [candidate for candidate in candidates if not candidate.disqualifying_conditions]
    selected = qualified[0] if qualified else None
    secondary = next(
        (
            candidate for candidate in qualified[1:]
            if candidate.score.total >= SECONDARY_MATERIALITY_THRESHOLD
            and candidate.direction != selected.direction
            and selected.score.total - candidate.score.total <= 15
        ),
        None,
    ) if selected else None
    explanations: list[ResearchSelectionExplanation] = []
    for candidate in candidates[:8]:
        reasons = []
        if candidate.disqualifying_conditions:
            reasons.extend(candidate.disqualifying_conditions)
        else:
            reasons.append("qualified_market_evidence")
            reasons.append(f"user_relevance_{candidate.user_relevance.tier}")
        explanations.append(ResearchSelectionExplanation(
            candidate_id=candidate.candidate_id, candidate_name=candidate.name, score=candidate.score.total,
            score_difference=round((selected.score.total - candidate.score.total), 2) if selected else None,
            selected=bool(selected and candidate.candidate_id == selected.candidate_id), reasons=reasons,
        ))
    if selected:
        selected_because = [
            f"Research Priority Score {selected.score.total:.1f} exceeded the {PRIMARY_MATERIALITY_THRESHOLD:.1f} materiality threshold.",
            f"The subject is classified {selected.direction} using current market, relative-strength, and participation evidence.",
            *selected.user_relevance.rationale,
            f"{selected.qualifying_constituent_count} qualifying constituent securities and {len(selected.supported_figure_types)} supported figure types are available.",
        ]
        missing = selected.score.missing_dimensions
        return ResearchSelectionDecision(
            selected_candidate_id=selected.candidate_id,
            secondary_candidate_id=secondary.candidate_id if secondary else None,
            materiality_threshold=PRIMARY_MATERIALITY_THRESHOLD,
            selected_because=selected_because,
            competing_candidates=explanations,
            omitted_candidate_count=max(0, len(candidates) - 1 - int(secondary is not None)),
            user_relevance_contribution=selected.score.weighted_contributions.get("user_relevance", 0),
            missing_evidence=missing,
            freshness_status=selected.freshness,
        )
    return ResearchSelectionDecision(
        materiality_threshold=PRIMARY_MATERIALITY_THRESHOLD,
        no_selection_reason="No standalone research subject met the evidence and materiality threshold for this report.",
        competing_candidates=explanations,
        omitted_candidate_count=len(candidates),
        missing_evidence=sorted({reason for candidate in candidates for reason in candidate.disqualifying_conditions}),
        freshness_status="unavailable" if not candidates else "insufficient",
    )


def research_evidence_payloads(candidate: ResearchCandidate) -> list[dict[str, Any]]:
    relative_unit = "rank" if candidate.category == "individual_security" else "percentage points"
    relative_timeframe = "current stock snapshot" if candidate.category == "individual_security" else "1 month versus SPY"
    values = {
        "rank": (candidate.current_rank, candidate.previous_rank, candidate.rank_change, "rank", "current snapshot"),
        "relative-strength": (candidate.current_relative_strength, None, candidate.relative_strength_change, relative_unit, relative_timeframe),
        "return-1w": (candidate.returns.get("1w"), None, None, "percent", "1 week"),
        "return-1m": (candidate.returns.get("1m"), None, None, "percent", "1 month"),
        "return-3m": (candidate.returns.get("3m"), None, None, "percent", "3 months"),
        "breadth": (candidate.breadth, None, candidate.breadth_change, "percent", "current constituent breadth"),
        "participation": (candidate.participation, None, candidate.participation_change, "percent", "current positive-return participation"),
        "momentum": (candidate.momentum, None, None, "score", "current snapshot"),
        "coverage": (candidate.data_completeness * 100, None, None, "percent", "research input completeness"),
        "daily-change": (candidate.returns.get("1d"), None, None, "percent", "latest session"),
    }
    prefix = candidate.candidate_id.replace(":", "-")
    result = []
    for suffix, (value, previous, change, unit, timeframe) in values.items():
        if value is None:
            continue
        result.append({
            "evidence_id": f"research-{prefix}-{suffix}",
            "metric": f"{candidate.name} {suffix.replace('-', ' ')}",
            "current_value": value,
            "previous_value": previous,
            "change": change,
            "unit": unit,
            "timeframe": timeframe,
        })
    result.extend(
        [
            {
                "evidence_id": f"research-{prefix}-qualifying-constituents",
                "metric": f"{candidate.name} qualifying constituent count",
                "current_value": candidate.qualifying_constituent_count,
                "previous_value": None,
                "change": None,
                "unit": "securities",
                "timeframe": "current research universe",
            },
            {
                "evidence_id": f"research-{prefix}-supported-figure-types",
                "metric": f"{candidate.name} supported figure type count",
                "current_value": len(candidate.supported_figure_types),
                "previous_value": None,
                "change": None,
                "unit": "figure types",
                "timeframe": "current research package",
            },
            {
                "evidence_id": f"research-{prefix}-materiality-threshold",
                "metric": "V7 primary Research Focus materiality threshold",
                "current_value": candidate.score.materiality_threshold,
                "previous_value": None,
                "change": None,
                "unit": "score",
                "timeframe": "V7 selection policy",
            },
        ]
    )
    for dimension, weight in candidate.score.weights.items():
        result.append(
            {
                "evidence_id": f"research-{prefix}-weight-{dimension.replace('_', '-')}",
                "metric": f"Research Priority Score weight: {dimension.replace('_', ' ')}",
                "current_value": round(weight * 100, 3),
                "previous_value": None,
                "change": None,
                "unit": "percent",
                "timeframe": "V7 fixed-weight scoring policy",
            }
        )
    for dimension, contribution in candidate.score.weighted_contributions.items():
        result.append(
            {
                "evidence_id": f"research-{prefix}-contribution-{dimension.replace('_', '-')}",
                "metric": f"{candidate.name} weighted contribution: {dimension.replace('_', ' ')}",
                "current_value": contribution,
                "previous_value": None,
                "change": None,
                "unit": "score points",
                "timeframe": "current report",
            }
        )
    return result


def candidate_sort_key(candidate: ResearchCandidate) -> tuple[Any, ...]:
    return (
        bool(candidate.disqualifying_conditions),
        -candidate.score.total,
        -candidate.score.weighted_contributions.get("market_significance", 0),
        -candidate.score.weighted_contributions.get("change_acceleration", 0),
        candidate.candidate_id,
    )


def evidence_ids_for(candidate_id: str, values: dict[str, Any]) -> list[str]:
    prefix = candidate_id.replace(":", "-")
    return [f"research-{prefix}-{key}" for key, value in values.items() if value is not None]


def research_direction(classification: str, relative_strength: float | None) -> str:
    value = classification.strip().lower()
    if value == "leading":
        return "leading"
    if value in {"improving", "emerging"}:
        return "emerging"
    if value == "weakening":
        return "weakening"
    if value == "lagging":
        return "lagging"
    if value in {"breakdown", "breaking down"}:
        return "breakdown"
    return "divergence"


def security_direction(score: float | None, daily_change: float | None, status: str) -> str:
    lowered = status.lower()
    if any(value in lowered for value in ("break", "risk", "weak", "sell")) or (score is not None and score < 40):
        return "breakdown" if (daily_change or 0) <= -3 else "weakening"
    if any(value in lowered for value in ("buy", "bull", "ready", "breakout")) or (score is not None and score >= 70):
        return "leading"
    return "divergence"


def significance(direction: str, rank: int | None, count: int, daily_change: float | None, category: str) -> float | None:
    if category == "individual_security":
        return min(100.0, abs(daily_change or 0) * 15) if daily_change is not None else None
    if rank is None or count <= 0:
        return None
    percentile = 100.0 if count == 1 else 100 * (count - rank) / max(1, count - 1)
    return round(percentile if direction in POSITIVE_DIRECTIONS else 100 - percentile, 3)


def directional_magnitude(direction: str, momentum: float | None, relative_strength: float | None, return_1m: float | None, classification: str) -> float | None:
    values: list[float] = []
    if momentum is not None:
        values.append(momentum if direction in POSITIVE_DIRECTIONS else 100 - momentum)
    if relative_strength is not None:
        values.append(min(100, max(0, 50 + relative_strength * 8)) if direction in POSITIVE_DIRECTIONS else min(100, max(0, 50 - relative_strength * 8)))
    if return_1m is not None:
        values.append(min(100, max(0, 50 + return_1m * 5)) if direction in POSITIVE_DIRECTIONS else min(100, max(0, 50 - return_1m * 5)))
    class_floor = {"leading": 80, "improving": 65, "weakening": 65, "lagging": 80, "breakdown": 90}.get(classification.lower())
    if class_floor is not None:
        values.append(class_floor)
    return round(sum(values) / len(values), 3) if values else None


def acceleration(rank_change: int | None, rs_change: float | None, breadth_change: float | None, previous_classification: str | None, current_classification: str) -> float | None:
    values: list[float] = []
    if rank_change is not None:
        values.append(min(100, abs(rank_change) * 25))
    if rs_change is not None:
        values.append(min(100, abs(rs_change) * 15))
    if breadth_change is not None:
        values.append(min(100, abs(breadth_change) * 4))
    if previous_classification and previous_classification.lower() != current_classification.lower():
        values.append(85)
    return round(sum(values) / len(values), 3) if values else None


def persistence(direction: str, values: Iterable[float | None], relative_strength: float | None) -> float | None:
    observations = [value for value in values if value is not None]
    if relative_strength is not None:
        observations.append(relative_strength)
    if not observations:
        return None
    if direction in POSITIVE_DIRECTIONS:
        confirming = sum(value > 0 for value in observations)
    elif direction in NEGATIVE_DIRECTIONS:
        confirming = sum(value < 0 for value in observations)
    else:
        confirming = sum(abs(value) >= 2 for value in observations)
    return round(confirming / len(observations) * 100, 3)


def directional_breadth(direction: str, breadth: float | None) -> float | None:
    if breadth is None:
        return None
    return breadth if direction in POSITIVE_DIRECTIONS else 100 - breadth if direction in NEGATIVE_DIRECTIONS else abs(breadth - 50) * 2


def theme_taxonomy_chain(row: dict[str, Any], members: list[dict[str, Any]]) -> list[dict[str, str]]:
    chain: list[dict[str, str]] = []
    for sector in path(row, "definition", "parent_sector_labels") or []:
        chain.append({"level": "Sector", "name": str(sector), "relationship": "validated taxonomy parent"})
    chain.append({"level": "Theme", "name": str(row.get("display_name") or row.get("theme_id")), "relationship": "reviewed theme definition"})
    industries = sorted({str(item.get("industry")) for item in members if item.get("industry")})
    for industry in industries[:3]:
        chain.append({"level": "Industry", "name": industry, "relationship": "validated security-master membership"})
    for item in members[:8]:
        chain.append({"level": "Security", "name": str(item.get("ticker")), "relationship": "validated theme membership"})
    return chain


def sector_taxonomy_chain(name: str, members: list[dict[str, Any]]) -> list[dict[str, str]]:
    chain = [{"level": "Sector", "name": name, "relationship": "validated canonical sector"}]
    for industry in sorted({str(item.get("industry")) for item in members if item.get("industry")})[:4]:
        chain.append({"level": "Industry", "name": industry, "relationship": "validated security-master membership"})
    for item in members[:8]:
        chain.append({"level": "Security", "name": str(item.get("ticker")), "relationship": "validated sector membership"})
    return chain


def security_taxonomy_chain(symbol: str, taxonomy: dict[str, Any]) -> list[dict[str, str]]:
    chain = []
    if taxonomy.get("sector"):
        chain.append({"level": "Sector", "name": str(taxonomy["sector"]), "relationship": "validated security-master membership"})
    if taxonomy.get("industry"):
        chain.append({"level": "Industry", "name": str(taxonomy["industry"]), "relationship": "validated security-master membership"})
    chain.append({"level": "Security", "name": symbol, "relationship": "saved security"})
    return chain


def enrich_member(member: dict[str, Any], taxonomy: list[dict[str, Any]]) -> dict[str, Any]:
    symbol = str(member.get("ticker") or "").upper()
    mapped = next((item for item in taxonomy if str(item.get("ticker") or "").upper() == symbol), {})
    return {**member, **{key: mapped.get(key) for key in ("sector", "sector_id", "industry") if mapped.get(key)}, "ticker": symbol, "mapping_type": "validated_theme_membership"}


def index_rows(rows: list[Any], *keys: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in keys:
            value = row.get(key)
            if value:
                result[normalize_id(value)] = row
    return result


def watchlist_item_stale(item: dict[str, Any] | None) -> bool:
    if not item:
        return True
    state = str(item.get("source_state") or item.get("overall_status") or "unavailable").lower()
    return state in STALE_STATES or bool(item.get("stale") or item.get("is_stale"))


def normalize_quality(value: Any) -> str:
    normalized = str(value or "unavailable").lower()
    if normalized in {"mock", "generated_test_data"}:
        return "test"
    return normalized if normalized in {"live", "cached", "stale", "test", "mixed", "partial", "unavailable"} else "unavailable"


def normalize_rotation_score(value: float | None) -> float | None:
    if value is None:
        return None
    return min(100.0, max(0.0, 50 + (value - 100) * 5))


def rotation_delta(row: dict[str, Any]) -> float | None:
    selected = path(row, "rotation_series", "1M") or {}
    # The new Theme Rotation coordinates are contextual visualization evidence,
    # not an implicit replacement for report candidate relative-strength
    # scoring. Only the explicitly legacy dependency may supply this fallback.
    if selected.get("formula_version") != "relative-return-momentum-v1":
        return None
    points = [point for point in selected.get("trail_points") or [] if isinstance(point, dict)]
    if len(points) < 2:
        return None
    return delta(number(points[-1].get("plotted_x")), number(points[-2].get("plotted_x")))


def percentage_ratio(value: Any) -> float | None:
    parsed = number(value)
    return parsed / 100 if parsed is not None else None


def delta(current: float | None, previous: float | None) -> float | None:
    return round(current - previous, 4) if current is not None and previous is not None else None


def normalize_id(value: Any) -> str:
    return str(value or "").strip().lower().replace("&", "and").replace("/", " ").replace("-", "_").replace(" ", "_")


def path(value: Any, *parts: str) -> Any:
    current = value
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(str(value).replace("%", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def integer(value: Any) -> int | None:
    parsed = number(value)
    return int(parsed) if parsed is not None else None
