from typing import Any

from app.services.analysis import build_market_analysis, build_stock_analysis


def build_market_ai_context(analysis: dict[str, Any] | None = None) -> dict[str, Any]:
    market_analysis = analysis or build_market_analysis()
    regime = market_analysis.get("regime", {})
    market_health = market_analysis.get("market_health", {})
    decision_dashboard = market_analysis.get("decision_dashboard", {})
    playbook = decision_dashboard.get("playbook", {})
    aggressiveness = decision_dashboard.get("aggressiveness", {})
    trading_styles = decision_dashboard.get("trading_styles", {})
    checklist = decision_dashboard.get("checklist", {})
    probabilities = market_analysis.get("probabilities", decision_dashboard.get("probabilities", {}))
    leadership = market_analysis.get("leadership", decision_dashboard.get("leadership", {}))
    decision_confidence = market_analysis.get(
        "decision_confidence",
        decision_dashboard.get("decision_confidence", {}),
    )
    comparison = market_analysis.get("comparison", decision_dashboard.get("comparison", {}))
    risk_dashboard = market_analysis.get("risk_dashboard", decision_dashboard.get("risk_dashboard", {}))
    institutional_intelligence = market_analysis.get(
        "institutional_intelligence",
        decision_dashboard.get("institutional_intelligence", {}),
    )
    sector_etfs = market_analysis.get("sector_etfs", {})
    industry_groups = market_analysis.get("industry_groups", {})
    cap_rotation = market_analysis.get("cap_rotation", {})
    fear_greed = market_analysis.get("fear_greed", {})
    breadth = market_analysis.get("breadth", {}).get("market", {})
    data_transparency = market_analysis.get("data_transparency", {})
    sectors = market_analysis.get("sectors", {})
    institutional_activity = market_analysis.get("institutional_activity", {})

    breadth_status = regime.get("breadth", {}).get("status", "N/A")
    percent_above_50ema = breadth.get("percent_above_50ema")
    institutional_bias = institutional_activity.get("bias", {}).get("bias", "N/A")
    top_sectors = [
        {
            "name": sector.get("name", "N/A"),
            "status": sector.get("status", "N/A"),
            "relative_strength_score": sector.get("relative_strength_score"),
        }
        for sector in sectors.get("leaders", [])[:5]
    ]

    return {
        "market_health": {
            "overall_score": market_health.get("overall_score"),
            "status": market_health.get("status", "N/A"),
            "summary": market_health.get("summary", "N/A"),
            "improving_factors": market_health.get("improving_factors", []),
            "weakening_factors": market_health.get("weakening_factors", []),
            "data_quality": market_health.get("data_quality", {}),
        },
        "decision_intelligence": {
            "playbook_headline": playbook.get("headline", "N/A"),
            "preferred_strategy": playbook.get("preferred_strategy", "N/A"),
            "suggested_aggressiveness": playbook.get("suggested_aggressiveness", "N/A"),
            "main_risk": playbook.get("main_risk", "N/A"),
            "aggressiveness_score": aggressiveness.get("score"),
            "aggressiveness_status": aggressiveness.get("status", "N/A"),
            "preferred_style": trading_styles.get("preferred_style", "N/A"),
            "checklist_grade": checklist.get("grade", "N/A"),
            "checklist_score": checklist.get("score"),
            "checklist_max_score": checklist.get("max_score"),
            "decision_confidence_score": decision_confidence.get("score"),
            "decision_confidence_status": decision_confidence.get("status", "N/A"),
            "top_probability": first_probability(probabilities),
            "leadership_summary": leadership.get("summary", "N/A"),
            "comparison_summary": comparison.get("summary", "N/A"),
            "risk_score": risk_dashboard.get("score"),
            "risk_summary": risk_dashboard.get("summary", "N/A"),
        },
        "institutional_intelligence": {
            "summary": institutional_intelligence.get("summary", "N/A"),
            "sentiment": compact_dashboard(institutional_intelligence.get("sentiment", {})),
            "money_flow": compact_dashboard(institutional_intelligence.get("money_flow", {})),
            "institutional": compact_dashboard(institutional_intelligence.get("institutional", {})),
            "options": compact_dashboard(institutional_intelligence.get("options", {})),
            "liquidity": compact_dashboard(institutional_intelligence.get("liquidity", {})),
        },
        "sector_etfs": {
            "summary": sector_etfs.get("summary", "N/A"),
            "leaders": [
                {
                    "symbol": item.get("symbol", "N/A"),
                    "sector": item.get("sector", "N/A"),
                    "status": item.get("status", "N/A"),
                    "relative_strength_score": item.get("relative_strength_score"),
                }
                for item in sector_etfs.get("items", [])[:3]
            ],
        },
        "industry_groups": {
            "summary": industry_groups.get("summary", "N/A"),
            "leaders": [
                {
                    "name": item.get("name", "N/A"),
                    "parent_sector": item.get("parent_sector", "N/A"),
                    "status": item.get("status", "N/A"),
                    "relative_strength_score": item.get("relative_strength_score"),
                }
                for item in industry_groups.get("items", [])[:3]
            ],
        },
        "cap_rotation": {
            "leader": cap_rotation.get("leader", "N/A"),
            "laggard": cap_rotation.get("laggard", "N/A"),
            "summary": cap_rotation.get("summary", "N/A"),
        },
        "fear_greed": {
            "score": fear_greed.get("score"),
            "status": fear_greed.get("status", "N/A"),
            "summary": fear_greed.get("summary", "N/A"),
        },
        "market_regime": regime.get("status", "N/A"),
        "breadth_status": breadth_status,
        "percent_above_50ema": percent_above_50ema,
        "breadth_universe": data_transparency.get("breadth_universe", breadth.get("universe", "core")),
        "breadth_coverage_percent": data_transparency.get(
            "breadth_coverage_percent",
            breadth.get("coverage_percent"),
        ),
        "data_mode": {
            "breadth": data_transparency.get("breadth_mode", breadth.get("overall_mode", "mock")),
            "sectors": data_transparency.get("sector_mode", "mock"),
            "industry_groups": data_transparency.get("industry_group_mode", "mock"),
            "leadership": data_transparency.get("leadership_mode", "mock"),
        },
        "institutional_bias": institutional_bias,
        "top_sectors": top_sectors,
        "key_opportunities": market_analysis.get("key_opportunities", []),
        "key_risks": market_analysis.get("key_risks", []),
        "what_to_watch": [
            f"Whether market health remains {market_health.get('status', 'N/A')}.",
            f"Whether data mode remains {market_health.get('data_quality', {}).get('overall_mode', 'mock')}.",
            f"Whether the playbook remains {playbook.get('headline', 'N/A')}.",
            f"Whether decision confidence remains {decision_confidence.get('status', 'N/A')}.",
            f"Whether Fear & Greed stays {fear_greed.get('status', 'N/A')}.",
            f"Whether {cap_rotation.get('leader', 'N/A')} leadership persists.",
            f"Whether breadth can hold near {format_percent(percent_above_50ema)} above the 50EMA.",
            "Breadth is based on a core liquid-stock universe, not complete exchange-wide breadth.",
            f"Whether institutional bias remains {institutional_bias}.",
            "Whether money flow, options sentiment, and liquidity remain supportive.",
            "Whether leadership broadens beyond the top sectors and industry groups.",
        ],
    }


def build_stock_ai_context(
    symbol: str,
    analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stock_analysis = analysis or build_stock_analysis(symbol)
    stock_rating = stock_analysis.get("stock_rating", {})
    relative_strength = stock_analysis.get("relative_strength", {})
    patterns = stock_analysis.get("patterns", {}).get("patterns", [])
    volume = stock_analysis.get("volume", {})
    trendline = stock_analysis.get("trendline", {})
    risk_plan = stock_analysis.get("risk_plan", {})
    multi_timeframe = stock_analysis.get("multi_timeframe", {})
    main_pattern = patterns[0] if patterns else {}

    return {
        "symbol": stock_analysis.get("symbol", symbol.upper()),
        "rating": stock_rating.get("rating", "N/A"),
        "score": stock_rating.get("overall_score"),
        "status": stock_rating.get("status", "N/A"),
        "data_quality": stock_rating.get("data_quality", {}),
        "risk_level": risk_plan.get("risk_level", stock_rating.get("risk_level", "N/A")),
        "relative_strength_status": relative_strength.get("status", "N/A"),
        "main_pattern": {
            "name": main_pattern.get("name", "N/A"),
            "status": main_pattern.get("status", "N/A"),
            "confidence": main_pattern.get("confidence"),
        },
        "volume_quality": volume.get("volume_quality", "N/A"),
        "trendline_status": trendline.get("rising_support", {}).get(
            "status",
            trendline.get("summary", "N/A"),
        ),
        "multi_timeframe_alignment": multi_timeframe.get("alignment", "N/A"),
        "key_strengths": stock_analysis.get("strengths", [])[:3],
        "warnings": stock_analysis.get("warnings", [])[:3],
        "what_to_watch": [
            "Whether price confirms the main setup around key levels.",
            "Whether volume remains constructive.",
            "Whether the risk plan remains intact.",
        ],
    }


def format_percent(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.2f}%"

    return "N/A"


def first_probability(probabilities: dict[str, Any]) -> dict[str, Any]:
    items = probabilities.get("items", [])
    if not items:
        return {"strategy": "N/A", "probability": None, "confidence": None}

    item = items[0]
    return {
        "strategy": item.get("strategy", "N/A"),
        "probability": item.get("probability"),
        "confidence": item.get("confidence"),
    }


def compact_dashboard(dashboard: dict[str, Any]) -> dict[str, Any]:
    return {
        "score": dashboard.get("score"),
        "status": dashboard.get("status", "N/A"),
        "summary": dashboard.get("summary", "N/A"),
    }
