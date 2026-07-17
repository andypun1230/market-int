from typing import Any

from app.services.analysis import (
    build_all_stock_analyses,
    build_market_analysis,
    build_stock_analysis,
)
from app.services.ai_prompts import (
    MARKET_ANALYST_SYSTEM_PROMPT,
    STOCK_ANALYST_SYSTEM_PROMPT,
)
from app.services.ai_context import build_market_ai_context, build_stock_ai_context
from app.services.ai_validation import valid_confidence, valid_string, valid_string_list
from app.services.openai_client import generate_structured_summary

DISCLAIMER = "This is educational market analysis only and not financial advice."
GENERATED_BY = "rules"
MARKET_NEXT_UPDATE = "Next scheduled market refresh"
STOCK_NEXT_UPDATE = "Next scheduled watchlist refresh"


def generate_market_narrative() -> dict[str, Any]:
    analysis = build_market_analysis()
    rule_summary = build_rule_market_narrative(analysis)
    openai_summary = generate_structured_summary(
        MARKET_ANALYST_SYSTEM_PROMPT,
        {
            "context": build_market_ai_context(analysis),
            "fallback_summary": rule_summary,
            "required_shape": "market_ai_summary",
        },
    )

    if openai_summary:
        return merge_market_openai_summary(rule_summary, openai_summary)

    return rule_summary


def build_rule_market_narrative(analysis: dict[str, Any]) -> dict[str, Any]:
    regime = analysis["regime"]
    market_health = analysis.get("market_health", {})
    decision_dashboard = analysis.get("decision_dashboard", {})
    playbook = decision_dashboard.get("playbook", {})
    aggressiveness = decision_dashboard.get("aggressiveness", {})
    probabilities = analysis.get("probabilities", decision_dashboard.get("probabilities", {}))
    decision_confidence = analysis.get(
        "decision_confidence",
        decision_dashboard.get("decision_confidence", {}),
    )
    risk_dashboard = analysis.get("risk_dashboard", decision_dashboard.get("risk_dashboard", {}))
    sector_etfs = analysis.get("sector_etfs", {})
    industry_groups = analysis.get("industry_groups", {})
    cap_rotation = analysis.get("cap_rotation", {})
    fear_greed = analysis.get("fear_greed", {})
    breadth = analysis["breadth"]["market"]
    sectors = analysis["sectors"]
    institutional_activity = analysis["institutional_activity"]
    institutional_intelligence = analysis.get("institutional_intelligence", {})
    risk = analysis["risk"]["market"]

    regime_status = regime.get("status", "Unknown")
    breadth_status = regime.get("breadth", {}).get("status", "unknown")
    percent_above_50ema = breadth.get("percent_above_50ema")
    breadth_coverage = breadth.get("coverage_percent")
    breadth_universe = breadth.get("universe", "core")
    institutional_bias = institutional_activity.get("bias", {}).get("bias", "Unknown")
    leading_sector = first_sector_name(sectors)
    headline = build_market_headline(regime_status, institutional_bias)
    market_health_status = market_health.get("status", "N/A")
    market_health_score = market_health.get("overall_score", "N/A")
    data_quality = market_health.get("data_quality", {})
    data_mode = data_quality.get("overall_mode", "mock")
    live_components = data_quality.get("live_components", [])
    fallback_components = data_quality.get("fallback_components", [])
    playbook_headline = playbook.get("headline", "N/A")
    preferred_strategy = playbook.get("preferred_strategy", "N/A")
    aggressiveness_status = aggressiveness.get("status", "N/A")
    aggressiveness_score = aggressiveness.get("score", "N/A")
    top_probability = first_probability(probabilities)
    confidence_status = decision_confidence.get("status", "N/A")
    confidence_score = decision_confidence.get("score", "N/A")
    risk_score = risk_dashboard.get("score", "N/A")
    fear_greed_status = fear_greed.get("status", "N/A")
    cap_leader = cap_rotation.get("leader", "N/A")
    sector_etf_leaders = [
        item.get("sector", "N/A")
        for item in sector_etfs.get("items", [])[:2]
    ]
    industry_group_leaders = [
        item.get("name", "N/A")
        for item in industry_groups.get("items", [])[:3]
    ]

    summary = (
        f"Market health is {market_health_status} with a score of {market_health_score}. "
        f"Today’s playbook is {playbook_headline}, with {aggressiveness_status} "
        f"aggressiveness at {aggressiveness_score}/100 and {preferred_strategy} preferred. "
        f"Decision confidence is {confidence_status} at {confidence_score}/100, "
        f"and the top probability setup is {top_probability.get('strategy', 'N/A')} "
        f"at {top_probability.get('probability', 'N/A')}%. "
        f"Risk dashboard score is {risk_score}/100. "
        f"This analysis currently uses {data_mode} data; "
        f"live components include {format_component_list(live_components)}, "
        f"while fallback components include {format_component_list(fallback_components)}. "
        f"Fear & Greed is {fear_greed_status}, and {cap_leader} is leading cap rotation. "
        f"The market regime is {regime_status}. Core liquid-stock breadth ({breadth_universe}) "
        f"is {breadth_status.lower()} with {format_percent(percent_above_50ema)} above the 50EMA "
        f"and {format_percent(breadth_coverage)} coverage. "
        f"Institutional bias is {institutional_bias}, and the leading broad sector is {leading_sector}. "
        f"Institutional intelligence shows {institutional_intelligence.get('summary', 'N/A')} "
        "Options gamma is estimated, money flow is estimated, and large prints are only block-trade candidates. "
        f"Leading industry groups are {', '.join(industry_group_leaders) if industry_group_leaders else 'N/A'}. "
        f"Sector ETF leadership is focused on {', '.join(sector_etf_leaders) if sector_etf_leaders else 'N/A'}. "
        "The main takeaway is to stay selective and monitor whether leadership broadens or narrows."
    )

    return {
        "type": "market_ai_summary",
        "headline": headline,
        "summary": summary,
        "confidence": calculate_market_confidence(regime_status, institutional_bias, percent_above_50ema),
        "generated_by": GENERATED_BY,
        "next_update": MARKET_NEXT_UPDATE,
        "key_points": analysis["summary_points"],
        "opportunities": analysis["key_opportunities"],
        "risks": analysis["key_risks"],
        "what_to_watch": [
            f"Whether market health remains {market_health_status}.",
            f"Whether the data mix improves from {data_mode}.",
            f"Whether the playbook stays {playbook_headline}.",
            f"Whether decision confidence stays {confidence_status}.",
            f"Whether {top_probability.get('strategy', 'N/A')} remains the highest-probability setup.",
            f"Whether {preferred_strategy} remains the preferred strategy.",
            f"Whether Fear & Greed remains {fear_greed_status} without becoming excessive.",
            f"Whether {cap_leader} leadership persists or broadens.",
            f"Whether core breadth can hold above {format_percent(percent_above_50ema)} above the 50EMA.",
            f"Whether institutional bias remains {institutional_bias}.",
            "Whether money flow, options sentiment, and liquidity remain constructive.",
            f"Whether {leading_sector} continues to lead as a broad sector.",
            "Whether leading industry groups keep confirming the broader sector move.",
            risk.get("main_risks", ["Upcoming macro catalysts"])[0],
        ],
        "disclaimer": DISCLAIMER,
    }


def generate_stock_narrative(symbol: str) -> dict[str, Any]:
    analysis = build_stock_analysis(symbol)
    rule_summary = build_rule_stock_narrative(analysis)
    openai_summary = generate_structured_summary(
        STOCK_ANALYST_SYSTEM_PROMPT,
        {
            "context": build_stock_ai_context(symbol, analysis),
            "fallback_summary": rule_summary,
            "required_shape": "stock_ai_summary",
        },
    )

    if openai_summary:
        return merge_stock_openai_summary(rule_summary, openai_summary)

    return rule_summary


def build_rule_stock_narrative(analysis: dict[str, Any]) -> dict[str, Any]:
    stock_rating = analysis["stock_rating"]
    relative_strength = analysis["relative_strength"]
    patterns = analysis["patterns"].get("patterns", [])
    volume = analysis["volume"]
    risk_plan = analysis["risk_plan"]
    multi_timeframe = analysis["multi_timeframe"]

    normalized_symbol = analysis["symbol"]
    rating = stock_rating.get("rating", "N/A")
    overall_score = stock_rating.get("overall_score", "N/A")
    rs_status = relative_strength.get("status", "N/A")
    main_pattern = patterns[0] if patterns else None
    main_pattern_name = main_pattern.get("name", "N/A") if main_pattern else "N/A"
    volume_quality = volume.get("volume_quality", "N/A")
    risk_level = risk_plan.get("risk_level", stock_rating.get("risk_level", "N/A"))
    alignment = multi_timeframe.get("alignment", "N/A")
    data_mode = (stock_rating.get("data_quality") or {}).get("overall_mode", "mock")

    headline = (
        f"{normalized_symbol} shows {rs_status.lower()} relative strength "
        f"with {risk_level.lower()} risk"
    )
    summary = (
        f"{normalized_symbol} is rated {rating} with an overall score of {overall_score}. "
        f"Relative strength status is {rs_status}, the main detected pattern is {main_pattern_name}, "
        f"volume quality is {volume_quality}, and multi-timeframe alignment is {alignment}. "
        f"The current stock analysis data mode is {data_mode}; pattern and intraday timeframe inputs may remain simulated. "
        "The setup may be worth monitoring, but the risk plan and confirmation signals should remain central."
    )

    return {
        "type": "stock_ai_summary",
        "symbol": normalized_symbol,
        "headline": headline,
        "summary": summary,
        "confidence": calculate_stock_confidence(overall_score, main_pattern),
        "generated_by": GENERATED_BY,
        "next_update": STOCK_NEXT_UPDATE,
        "why_it_matters": [
            f"{normalized_symbol} has an overall score of {overall_score} and rating {rating}.",
            f"Relative strength is {rs_status}, which helps frame leadership quality.",
            f"The main setup is {main_pattern_name}, so confirmation depends on price behavior around key levels.",
            f"Volume quality is {volume_quality}, which affects conviction in the setup.",
            f"Data mode is {data_mode}, so source quality should be checked before relying on the setup.",
        ],
        "strengths": analysis["strengths"][:2],
        "risks": analysis["warnings"][:2],
        "what_to_watch": [
            "The setup improves if price confirms the key breakout or resistance area on constructive volume.",
            "The setup weakens if price loses support or violates the risk plan.",
            f"Monitor whether multi-timeframe alignment remains {alignment}.",
            f"Monitor whether risk level improves from {risk_level}.",
        ],
        "disclaimer": DISCLAIMER,
    }


def generate_all_stock_narratives() -> dict[str, Any]:
    analyses = build_all_stock_analyses()
    items = [
        generate_stock_narrative(item["symbol"])
        for item in analyses["items"]
    ]
    confidence_values = [
        item["confidence"] for item in items if isinstance(item.get("confidence"), (int, float))
    ]
    generated_by = "openai" if any(item.get("generated_by") == "openai" for item in items) else GENERATED_BY

    return {
        "type": "stock_ai_summaries",
        "items": items,
        "summary_points": analyses["summary_points"],
        "confidence": round(sum(confidence_values) / len(confidence_values)) if confidence_values else 70,
        "generated_by": generated_by,
        "next_update": STOCK_NEXT_UPDATE,
        "disclaimer": DISCLAIMER,
    }


def merge_market_openai_summary(
    fallback: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    summary = fallback.copy()
    summary.update(
        {
            "headline": valid_string(candidate.get("headline"), fallback["headline"]),
            "summary": valid_string(candidate.get("summary"), fallback["summary"]),
            "confidence": valid_confidence(candidate.get("confidence"), fallback["confidence"]),
            "generated_by": "openai",
            "next_update": valid_string(candidate.get("next_update"), fallback["next_update"]),
            "key_points": valid_string_list(candidate.get("key_points"), fallback["key_points"]),
            "opportunities": valid_string_list(candidate.get("opportunities"), fallback["opportunities"]),
            "risks": valid_string_list(candidate.get("risks"), fallback["risks"]),
            "what_to_watch": valid_string_list(candidate.get("what_to_watch"), fallback["what_to_watch"]),
            "disclaimer": valid_string(candidate.get("disclaimer"), fallback["disclaimer"]),
        }
    )
    return summary


def merge_stock_openai_summary(
    fallback: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    summary = fallback.copy()
    summary.update(
        {
            "headline": valid_string(candidate.get("headline"), fallback["headline"]),
            "summary": valid_string(candidate.get("summary"), fallback["summary"]),
            "confidence": valid_confidence(candidate.get("confidence"), fallback["confidence"]),
            "generated_by": "openai",
            "next_update": valid_string(candidate.get("next_update"), fallback["next_update"]),
            "why_it_matters": valid_string_list(
                candidate.get("why_it_matters"),
                fallback["why_it_matters"],
            ),
            "strengths": valid_string_list(candidate.get("strengths"), fallback["strengths"]),
            "risks": valid_string_list(candidate.get("risks"), fallback["risks"]),
            "what_to_watch": valid_string_list(candidate.get("what_to_watch"), fallback["what_to_watch"]),
            "disclaimer": valid_string(candidate.get("disclaimer"), fallback["disclaimer"]),
        }
    )
    return summary


def build_market_headline(regime_status: str, institutional_bias: str) -> str:
    if regime_status == "Confirmed Uptrend":
        return "Market trend is constructive, but leadership quality still matters"

    if regime_status == "Uptrend Under Pressure":
        return "Market uptrend is under pressure and selectivity matters"

    if regime_status == "Correction":
        return "Market is in correction and risk control comes first"

    if institutional_bias == "Bullish":
        return "Market remains choppy with selective institutional support"

    return "Market remains choppy with selective leadership"


def first_sector_name(sectors: dict[str, Any]) -> str:
    leaders = sectors.get("leaders", [])
    if not leaders:
        return "N/A"

    return leaders[0].get("name", "N/A")


def first_probability(probabilities: dict[str, Any]) -> dict[str, Any]:
    items = probabilities.get("items", [])
    if not items:
        return {"strategy": "N/A", "probability": "N/A", "confidence": "N/A"}

    return items[0]


def format_percent(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.2f}%"

    return "N/A"


def format_component_list(items: Any) -> str:
    if isinstance(items, list) and items:
        return ", ".join(str(item).replace("_", " ") for item in items)

    return "none"


def calculate_market_confidence(
    regime_status: str,
    institutional_bias: str,
    percent_above_50ema: Any,
) -> int:
    confidence = 72

    if regime_status == "Confirmed Uptrend":
        confidence += 10
    elif regime_status == "Correction":
        confidence -= 8

    if institutional_bias == "Bullish":
        confidence += 6
    elif institutional_bias in {"Cautious", "Bearish"}:
        confidence -= 5

    if isinstance(percent_above_50ema, (int, float)):
        if percent_above_50ema >= 60:
            confidence += 5
        elif percent_above_50ema < 45:
            confidence -= 7

    return max(50, min(95, confidence))


def calculate_stock_confidence(overall_score: Any, main_pattern: dict[str, Any] | None) -> int:
    confidence = 68

    if isinstance(overall_score, (int, float)):
        confidence = round((confidence + overall_score) / 2)

    if main_pattern and isinstance(main_pattern.get("confidence"), (int, float)):
        confidence = round((confidence + main_pattern["confidence"]) / 2)

    return max(50, min(96, confidence))
