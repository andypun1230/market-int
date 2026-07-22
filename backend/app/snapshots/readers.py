from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

from app.models.market import (
    AggressivenessResponse,
    BreadthResponse,
    DashboardComparisonResponse,
    DecisionConfidenceResponse,
    DecisionDashboardResponse,
    FearGreedResponse,
    IndustryRotationResponse,
    InstitutionalDashboardResponse,
    InstitutionalIntelligenceResponse,
    LeadershipResponse,
    LiquidityDashboardResponse,
    MarketHealthComponents,
    MarketHealthResponse,
    MarketChecklistResponse,
    MarketPlaybookResponse,
    MarketSentimentResponse,
    MoneyFlowResponse,
    OptionsIntelligenceResponse,
    ProbabilityResponse,
    RegimeInstitutionalActivityResponse,
    RegimeResponse,
    RiskDashboardV2Response,
    RiskResponse,
    SuggestedExposure,
    TradingStyleResponse,
    TrendResponse,
    VolatilityResponse,
)
from app.snapshots.models import MarketSnapshot, SnapshotSection, now_iso
from app.snapshots.service import get_market_snapshot_service, snapshot_age_seconds
from app.services.market_data import canonicalize_index_payloads
from app.services.theme_intelligence import build_theme_intelligence_context

T = TypeVar("T", bound=BaseModel)


def latest_snapshot_or_trigger() -> MarketSnapshot | None:
    service = get_market_snapshot_service()
    snapshot = service.get_latest_snapshot()
    if snapshot is None:
        service.trigger_background_refresh()
    return snapshot


def latest_snapshot_response() -> dict[str, Any]:
    service = get_market_snapshot_service()
    snapshot = service.get_latest_snapshot()
    if snapshot is None:
        service.trigger_background_refresh()
        return initializing_snapshot_response()
    response = {
        **snapshot.model_dump(),
        "age_seconds": snapshot_age_seconds(snapshot),
        "refresh_state": service.get_status(),
    }
    hydrate_snapshot_breadth(response)
    return response


def get_section_payload(name: str) -> Any:
    snapshot = latest_snapshot_or_trigger()
    if snapshot is None:
        return None
    section = snapshot.sections.get(name)
    if not section:
        return None
    if name == "indexes":
        return canonicalize_index_payloads(section.payload)
    return section.payload


def get_home_dashboard_from_snapshot() -> dict[str, Any]:
    payload = get_section_payload("home")
    if isinstance(payload, dict):
        return hydrate_current_theme(decorate_payload(payload))
    return initializing_home_dashboard()


def get_core_snapshot_from_snapshot() -> dict[str, Any]:
    payload = get_section_payload("core")
    if isinstance(payload, dict):
        decorated = hydrate_current_theme(decorate_payload(payload))
        decorated.setdefault("as_of", decorated.get("generated_at") or now_iso())
        return decorated
    return initializing_core_snapshot()


def get_model_from_snapshot(name: str, model: type[T], fallback: T) -> T:
    payload = get_section_payload(name)
    if isinstance(payload, dict):
        try:
            return model.model_validate(payload)
        except Exception:
            return fallback
    return fallback


def get_regime_from_snapshot() -> RegimeResponse:
    return get_model_from_snapshot("regime", RegimeResponse, fallback_regime())


def get_health_from_snapshot() -> MarketHealthResponse:
    return get_model_from_snapshot("health", MarketHealthResponse, fallback_health())


def get_risk_from_snapshot() -> RiskResponse:
    return get_model_from_snapshot("risk", RiskResponse, fallback_risk())


def get_fear_greed_from_snapshot() -> FearGreedResponse:
    payload = get_section_payload("fear_greed")
    if isinstance(payload, dict) and payload.get("source_type") in {"official", "estimated"}:
        try:
            return FearGreedResponse.model_validate(payload)
        except Exception:
            return fallback_fear_greed()
    service = get_market_snapshot_service()
    service.trigger_background_refresh()
    return fallback_fear_greed()


def get_decision_from_snapshot(model: type[T], fallback: T) -> T:
    return get_model_from_snapshot("decision", model, fallback)


def get_decision_dashboard_from_snapshot() -> DecisionDashboardResponse:
    value = get_model_from_snapshot("decision", DecisionDashboardResponse, fallback_decision())
    return value.model_copy(update={"theme_intelligence": build_theme_intelligence_context()})


def snapshot_details_payload(group: str) -> dict[str, Any]:
    snapshot = latest_snapshot_or_trigger()
    if snapshot is None:
        return {"partial": True, "cache_status": "initializing", "refreshing": True, "errors": {}}
    if group == "structure":
        breadth = current_breadth_payload() or snapshot.section_payload("breadth")
        return {
            "breadth": {"market": breadth, "sectors": []},
            "sectors": snapshot.section_payload("sectors_summary") or {"leaders": [], "summary": "Sector summary unavailable."},
            "sectorEtfs": {"items": [], "summary": "Sector ETF summary unavailable."},
            "industryGroups": {"items": [], "summary": "Industry groups unavailable."},
            "industryRotation": {"sectors": [], "summary": "Industry rotation unavailable."},
            "leadership": snapshot.section_payload("leadership"),
            "partial": snapshot.status != "complete",
            "cache_status": "snapshot",
            "refreshing": False,
            "snapshot_id": snapshot.snapshot_id,
            "errors": {},
        }
    if group == "decision":
        # The MarketSnapshot remains immutable. Its detail facade must still
        # expose the current durable ThemeSnapshot, matching the standalone
        # Decision endpoint and avoiding stale pre-pilot Theme provenance.
        decision = get_decision_dashboard_from_snapshot().model_dump()
        return {
            "decisionDashboard": decision,
            "probabilities": decision.get("probabilities"),
            "comparison": decision.get("comparison"),
            "riskDashboard": snapshot.section_payload("risk_dashboard"),
            "partial": snapshot.status != "complete",
            "cache_status": "snapshot",
            "refreshing": False,
            "snapshot_id": snapshot.snapshot_id,
            "errors": {},
        }
    return {
        "sentiment": None,
        "moneyFlow": None,
        "institutionalActivity": None,
        "institutional": None,
        "options": None,
        "liquidity": None,
        "partial": True,
        "cache_status": "snapshot",
        "refreshing": False,
        "snapshot_id": snapshot.snapshot_id,
        "errors": {},
    }


def initializing_snapshot_response() -> dict[str, Any]:
    return {
        "snapshot_id": None,
        "status": "initializing",
        "age_seconds": None,
        "refreshing": True,
        "sections": {},
        "warnings": ["Market snapshot is initializing."],
    }


def initializing_home_dashboard() -> dict[str, Any]:
    return {
        "core": initializing_core_snapshot(),
        "risk_summary": {
            "score": None,
            "status": "Unavailable",
            "top_contributors": [],
            "summary": "Market snapshot is initializing.",
        },
        "watchlist_summary": {"items": []},
        "bootstrap": True,
        "refreshing": True,
        "cache_status": "initializing",
        "is_stale": True,
    }


def initializing_core_snapshot() -> dict[str, Any]:
    return {
        "indexes": [],
        "market_health": fallback_health().model_dump(),
        "decision_summary": {
            "playbook": None,
            "aggressiveness": None,
            "preferred_style": None,
            "main_risk": "Market snapshot is initializing.",
            "decision_confidence": None,
        },
        "breadth_summary": None,
        "top_sector": None,
        "lagging_sector": None,
        "top_industry_group": None,
        "as_of": now_iso(),
        "overall_mode": "initializing",
        "bootstrap": True,
        "refreshing": True,
        "cache_status": "initializing",
        "is_stale": True,
    }


def decorate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    snapshot = get_market_snapshot_service().get_latest_snapshot()
    result = dict(payload)
    normalize_embedded_indexes(result)
    hydrate_current_breadth(result)
    if snapshot:
        result["snapshot_id"] = snapshot.snapshot_id
        result["snapshot_status"] = snapshot.status
        result["snapshot_age_seconds"] = snapshot_age_seconds(snapshot)
    return result


def hydrate_current_theme(payload: dict[str, Any]) -> dict[str, Any]:
    """Attach the durable ThemeSnapshot at read time without a provider request."""
    result = dict(payload)
    theme = build_theme_intelligence_context()
    result["theme_intelligence"] = theme
    core = result.get("core")
    if isinstance(core, dict):
        result["core"] = {**core, "theme_intelligence": theme}
    return result


def hydrate_current_breadth(payload: dict[str, Any]) -> None:
    """Keep Home and Market reads attached to the current durable breadth snapshot."""
    breadth = current_breadth_payload()
    if not breadth:
        return
    summary = {
        "breadth_score": breadth.get("breadth_score"),
        "breadth_status": breadth.get("breadth_status"),
        "percent_above_50ema": breadth.get("percent_above_50ema"),
        "coverage_percent": breadth.get("coverage_percent"),
        "overall_mode": breadth.get("overall_mode"),
        "universe": breadth.get("universe"),
        "snapshot_id": breadth.get("snapshot_id"),
        "universe_version": breadth.get("universe_version"),
        "market_date": breadth.get("market_date"),
        "coverage_status": breadth.get("coverage_status"),
        "trend": breadth.get("trend"),
        "coverage_dimensions": breadth.get("coverage_dimensions"),
        "data_confidence": breadth.get("data_confidence"),
        "signal_confidence": breadth.get("signal_confidence"),
    }
    core = payload.get("core") if isinstance(payload.get("core"), dict) else payload
    if isinstance(core, dict) and "breadth_summary" in core:
        core["breadth_summary"] = summary


def current_breadth_payload() -> dict[str, Any] | None:
    try:
        from app.services.breadth import calculate_market_breadth
        breadth = calculate_market_breadth().model_dump()
    except Exception:
        return None
    return breadth if breadth.get("snapshot_id") else None


def hydrate_snapshot_breadth(payload: dict[str, Any]) -> None:
    breadth = current_breadth_payload()
    sections = payload.get("sections")
    if not breadth or not isinstance(sections, dict):
        return
    section = sections.get("breadth")
    if isinstance(section, dict):
        section["payload"] = breadth
        section["source_state"] = breadth.get("source_state") or section.get("source_state")
    source_summary = payload.get("source_summary")
    if isinstance(source_summary, dict):
        source_summary["breadth_snapshot_id"] = breadth.get("snapshot_id")


def normalize_embedded_indexes(payload: dict[str, Any]) -> None:
    if isinstance(payload.get("indexes"), list):
        payload["indexes"] = canonicalize_index_payloads(payload["indexes"])
    core = payload.get("core")
    if isinstance(core, dict) and isinstance(core.get("indexes"), list):
        core["indexes"] = canonicalize_index_payloads(core["indexes"])


def fallback_regime() -> RegimeResponse:
    return RegimeResponse(
        status="Unavailable",
        trend=TrendResponse(spy="Unavailable", qqq="Unavailable", iwm="Unavailable", dji="Unavailable"),
        breadth=BreadthResponse(status="Unavailable", stocks_above_20ma=0, stocks_above_50ma=0, stocks_above_200ma=0, advance_decline_ratio=None),
        volatility=VolatilityResponse(vix=0.0, status="Unavailable"),
        institutional_activity=RegimeInstitutionalActivityResponse(distribution_days=0, accumulation_days=0, follow_through_day="Unavailable"),
        explanation="Market snapshot is initializing.",
    )


def fallback_health() -> MarketHealthResponse:
    return MarketHealthResponse(
        overall_score=0,
        status="Unavailable",
        components=MarketHealthComponents(momentum=0, breadth=0, trend=0, volume=0, institutional=0, volatility=0, sector_strength=0),
        component_explanations={},
        summary="Market snapshot is initializing.",
        improving_factors=[],
        weakening_factors=[],
        decision_confidence=None,
        data_quality={"overall_mode": "unavailable", "snapshot_status": "initializing"},
    )


def fallback_risk() -> RiskResponse:
    return RiskResponse(
        risk_level="Unavailable",
        main_risks=["Market snapshot is initializing."],
        suggested_positioning="Keep existing values visible while the snapshot refreshes.",
    )


def fallback_fear_greed() -> FearGreedResponse:
    return FearGreedResponse(
        score=None,
        status="Unavailable",
        components=[],
        summary="Fear & Greed unavailable while the market snapshot refreshes.",
        title="Fear & Greed unavailable",
        subtitle="Latest verified reading could not be retrieved",
        source=None,
        source_type=None,
        stale=True,
        confidence=0,
        cache_status="initializing",
        partial=True,
        coverage_percent=0.0,
        coverage_components=0,
        required_components=7,
        overall_mode="unavailable",
        dependencies_requested=7,
        dependencies_available=0,
        dependencies_missing=["market_snapshot"],
        degraded_reasons=["initializing"],
    )


def fallback_decision() -> DecisionDashboardResponse:
    summary = "Market snapshot is initializing."
    risk_dashboard = RiskDashboardV2Response(score=50, contributors=[], warnings=[summary], upcoming_events=[], summary=summary)
    return DecisionDashboardResponse(
        aggressiveness=AggressivenessResponse(
            score=0,
            status="Unavailable",
            suggested_exposure=SuggestedExposure(stocks=0, cash=100, margin="Avoid", options="Avoid"),
            summary=summary,
            reasons=[],
            cautions=[summary],
        ),
        trading_styles=TradingStyleResponse(items=[], preferred_style="N/A", summary=summary),
        checklist=MarketChecklistResponse(score=0, max_score=0, grade="N/A", items=[], summary=summary),
        playbook=MarketPlaybookResponse(
            headline="Market snapshot initializing",
            summary=summary,
            preferred_strategy="N/A",
            suggested_aggressiveness="Unavailable",
            top_sector="N/A",
            top_industry_group="N/A",
            cap_rotation_leader="N/A",
            main_risk=summary,
            action_guidelines=[],
            avoid=[],
            disclaimer="Educational market decision support only, not financial advice.",
        ),
        probabilities=ProbabilityResponse(items=[], summary=summary),
        leadership=LeadershipResponse(categories=[], summary=summary, overall_mode="unavailable", coverage_percent=0.0, as_of=now_iso()),
        decision_confidence=DecisionConfidenceResponse(score=0, status="Unavailable", contributors=[], disagreements=[], summary=summary),
        comparison=DashboardComparisonResponse(items=[], summary=summary),
        industry_rotation=IndustryRotationResponse(sectors=[], summary=summary, overall_mode="unavailable", coverage_percent=0.0, as_of=now_iso()),
        risk_dashboard=risk_dashboard,
        institutional_intelligence=InstitutionalIntelligenceResponse(
            sentiment=MarketSentimentResponse(score=0, status="Unavailable", signals=[], opportunities=[], risks=[], summary=summary, overall_mode="unavailable"),
            money_flow=MoneyFlowResponse(score=0, status="Unavailable", items=[], summary=summary),
            institutional=InstitutionalDashboardResponse(
                score=0,
                status="Unavailable",
                accumulation_distribution="Unavailable",
                block_trade_bias="Unavailable",
                dark_pool_bias="Unavailable",
                program_trading="Unavailable",
                signals=[],
                risks=[],
                summary=summary,
            ),
            options=OptionsIntelligenceResponse(
                score=0,
                status="Unavailable",
                put_call_ratio=0.0,
                implied_volatility_rank=0,
                skew="Unavailable",
                options_flow_bias="Unavailable",
                unusual_activity=[],
                summary=summary,
            ),
            liquidity=LiquidityDashboardResponse(
                score=0,
                status="Unavailable",
                spread_condition="Unavailable",
                depth_condition="Unavailable",
                funding_condition="Unavailable",
                volume_condition="Unavailable",
                warnings=[summary],
                summary=summary,
            ),
            summary=summary,
        ),
    )
