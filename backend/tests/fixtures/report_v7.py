from __future__ import annotations

from copy import deepcopy
from math import sin
from typing import Any


THEME_MEMBERS = {
    "cybersecurity": ["CRWD", "PANW", "FTNT", "ZS"],
    "memory_storage": ["MU", "WDC", "STX", "SNDK"],
}


SECURITY_FIXTURE_PROFILES: dict[str, dict[str, Any]] = {
    "PANW": {
        "score": 69,
        "change": 0.7,
        "signal": "Watch",
        "setup": "Tight consolidation near resistance",
        "trend": "Sideways consolidation",
        "summary": "Tight consolidation is approaching resistance on below-average volume.",
        "context": "PANW is consolidating within Cybersecurity after a slower advance.",
    },
    "FTNT": {
        "score": 61,
        "change": -1.4,
        "signal": "Monitor",
        "setup": "Pullback reclaim attempt",
        "trend": "Pullback stabilizing",
        "summary": "The pullback is stabilizing above support, but a reclaim still needs expanding volume.",
        "context": "FTNT is testing support within Cybersecurity after a controlled pullback.",
    },
}


def report_v7_fixture(name: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
    report = base_report()
    previous: dict[str, Any] | None = None
    if name == "user-saved-leading-theme":
        save_theme(report, "cybersecurity", THEME_MEMBERS["cybersecurity"][:3])
    elif name == "user-saved-weakening-theme":
        report["theme_intelligence"]["items"] = [
            theme_row("memory_storage", "Memory & Storage", 2, "Weakening", 34, -7.5, 28, -9, THEME_MEMBERS["memory_storage"]),
            neutral_theme(),
        ]
        save_theme(report, "memory_storage", THEME_MEMBERS["memory_storage"][:3])
        previous = previous_snapshot(theme="memory_storage", theme_rank=1, theme_classification="Leading", theme_rs=4.0, theme_breadth=72)
    elif name == "market-leading-theme-no-overlap":
        report["theme_intelligence"]["items"] = [
            theme_row("cybersecurity", "Cybersecurity", 1, "Leading", 95, 11, 94, 16, THEME_MEMBERS["cybersecurity"]),
            neutral_theme(),
        ]
        report["research_preferences"] = {"saved_stocks": [], "saved_sectors": [], "saved_themes": []}
        report["watchlist_summary"] = {"source_state": "live", "items": [], "symbols_requested": []}
        report["stock_charts"] = []
    elif name == "market-lagging-sector-deterioration":
        report["theme_intelligence"]["items"] = [neutral_theme()]
        report["sector_dashboard"]["sectors"] = [
            sector_row("utilities", "Utilities", 1, "Neutral", 52, 0.2, 54, 0.1),
            sector_row("information_technology", "Information Technology", 3, "Lagging", 18, -9.0, 18, -12),
            sector_row("industrials", "Industrials", 2, "Neutral", 50, 0.0, 50, 0.0),
        ]
        previous = previous_snapshot(sector="information_technology", sector_rank=1, sector_classification="Leading", sector_rs=5, sector_breadth=74)
    elif name == "market-lagging-theme":
        report["theme_intelligence"]["items"] = [
            neutral_theme(),
            theme_row("memory_storage", "Memory & Storage", 2, "Lagging", 18, -10, 22, -13, THEME_MEMBERS["memory_storage"]),
        ]
        report["research_preferences"] = {"saved_stocks": [], "saved_sectors": [], "saved_themes": []}
        report["watchlist_summary"] = {"source_state": "live", "items": [], "symbols_requested": []}
        report["stock_charts"] = []
        previous = previous_snapshot(theme="memory_storage", theme_rank=1, theme_classification="Leading", theme_rs=4, theme_breadth=70)
    elif name == "individual-saved-stock-major-change":
        report["theme_intelligence"]["items"] = [neutral_theme()]
        report["sector_dashboard"]["sectors"] = []
        report["watchlist_summary"]["items"] = [watch_item("CRWD", score=24, change=-6.5, signal="Sell risk", setup="Fresh breakdown")]
        report["research_preferences"] = {"saved_stocks": ["CRWD"], "saved_sectors": [], "saved_themes": []}
        report["stock_charts"] = [stock_chart("CRWD", direction=-1)]
        previous = previous_snapshot(watch_symbol="CRWD", watch_score=78, watch_signal="Buy", watch_setup="Breakout")
    elif name == "multiple-saved-stocks-one-theme":
        save_theme(report, "cybersecurity", THEME_MEMBERS["cybersecurity"])
    elif name == "saved-stock-diverging-from-leading-theme":
        save_theme(report, "cybersecurity", ["CRWD"])
        report["watchlist_summary"]["items"] = [watch_item("CRWD", score=31, change=-4.5, signal="Weak", setup="Below support")]
        report["stock_charts"] = [stock_chart("CRWD", direction=-1)]
    elif name == "no-qualifying-focus":
        report["theme_intelligence"]["items"] = [neutral_theme()]
        report["sector_dashboard"]["sectors"] = [sector_row("industrials", "Industrials", 1, "Neutral", 50, 0.2, 50, 0.1)]
        report["research_preferences"] = {"saved_stocks": [], "saved_sectors": [], "saved_themes": []}
        report["watchlist_summary"] = {"source_state": "live", "items": [], "symbols_requested": []}
        report["stock_charts"] = []
    elif name == "empty-watchlist":
        report["watchlist_summary"] = {"source_state": "live", "items": [], "symbols_requested": []}
        report["research_preferences"] = {"saved_stocks": [], "saved_sectors": [], "saved_themes": []}
        report["stock_charts"] = []
    elif name == "stale-watchlist":
        report["theme_intelligence"]["items"] = [theme_row("cybersecurity", "Cybersecurity", 1, "Leading", 78, 5, 70, 8, THEME_MEMBERS["cybersecurity"])]
        report["watchlist_summary"]["source_state"] = "stale"
        report["watchlist_summary"]["items"] = [watch_item(symbol, source_state="stale") for symbol in THEME_MEMBERS["cybersecurity"][:3]]
        report["research_preferences"] = {"saved_stocks": THEME_MEMBERS["cybersecurity"][:3], "saved_sectors": [], "saved_themes": []}
    elif name == "partial-taxonomy":
        save_theme(report, "cybersecurity", THEME_MEMBERS["cybersecurity"][:3])
        report["security_taxonomy"] = report["security_taxonomy"][:1]
    elif name == "missing-breadth":
        save_theme(report, "cybersecurity", THEME_MEMBERS["cybersecurity"][:3])
        report["theme_intelligence"]["items"][0]["breadth"] = {}
    elif name == "first-report":
        save_theme(report, "cybersecurity", THEME_MEMBERS["cybersecurity"][:3])
        previous = None
    elif name == "previous-report-comparison":
        save_theme(report, "cybersecurity", THEME_MEMBERS["cybersecurity"][:3])
        previous = previous_snapshot(theme="cybersecurity", theme_rank=2, theme_classification="Improving", theme_rs=2, theme_breadth=60)
    elif name == "weekend-report":
        save_theme(report, "cybersecurity", THEME_MEMBERS["cybersecurity"][:3])
        report["generated_at"] = "2026-07-25T03:00:00+00:00"
    elif name == "mixed-source-report":
        save_theme(report, "cybersecurity", THEME_MEMBERS["cybersecurity"][:3])
        report["macro"]["source_state"] = "cached"
        report["sector_dashboard"]["source"] = "mixed"
    else:
        raise KeyError(name)
    return deepcopy(report), deepcopy(previous)


def base_report() -> dict[str, Any]:
    closes = [100 + index * 0.35 for index in range(100)]
    theme_rows = [
        theme_row("cybersecurity", "Cybersecurity", 1, "Leading", 86, 7.5, 82, 11, THEME_MEMBERS["cybersecurity"]),
        neutral_theme(),
    ]
    watch_symbols = ["CRWD", "PANW", "FTNT"]
    return {
        "report_id": "daily-2026-07-21-v7-fixture",
        "report_pdf_format_version": "daily-report-pdf-v7",
        "market_date": "2026-07-21",
        "date": "2026-07-21",
        "generated_at": "2026-07-21T21:30:00+00:00",
        "market_regime": "Selective Risk",
        "market_health": {"overall_score": 68},
        "report_snapshot": {"historicalMetrics": {"breadth": 58}},
        "recommendation_confidence": {"score": 72},
        "risk_dashboard": {"score": 42},
        "fear_greed": {"score": 61},
        "sector_leaders": ["Information Technology"],
        "semantic_context": {"snapshot_ids": {"market": "market-v7", "breadth": "unavailable", "sector": "sector-v7", "theme": "theme-v7"}},
        "index_histories": {symbol: closes for symbol in ("SPY", "QQQ", "IWM", "DIA")},
        "macro": {"source_state": "live"},
        "sector_dashboard": {
            "source": "live", "snapshot_id": "sector-v7", "market_date": "2026-07-21", "as_of": "2026-07-21",
            "sectors": [
                sector_row("information_technology", "Information Technology", 1, "Leading", 84, 5.5, 78, 8),
                sector_row("industrials", "Industrials", 2, "Neutral", 52, 0.5, 55, 1),
                sector_row("utilities", "Utilities", 3, "Lagging", 30, -4, 32, -5),
            ],
        },
        "theme_intelligence": {"available": True, "source_state": "live", "snapshot_id": "theme-v7", "market_date": "2026-07-21", "items": theme_rows},
        "theme_report": {"available": True, "market_date": "2026-07-21", "leadership": [], "rotation": {"items": []}},
        "watchlist_summary": {
            "source_state": "live", "symbols_requested": watch_symbols,
            "items": [watch_item(symbol) for symbol in watch_symbols],
        },
        "stock_charts": [stock_chart(symbol) for symbol in watch_symbols],
        "research_preferences": {"saved_stocks": watch_symbols, "saved_sectors": [], "saved_themes": ["cybersecurity"]},
        "security_taxonomy": taxonomy_rows(),
        "market_evolution": {"points": timeline_points()},
    }


def theme_row(theme_id: str, name: str, rank: int, classification: str, score: float, rs: float, breadth: float, return_1m: float, members: list[str]) -> dict[str, Any]:
    return {
        "theme_id": theme_id, "display_name": name, "version": "v1", "rank": rank,
        "classification": classification, "composite_score": score, "coverage_ratio": 1.0,
        "eligible_count": len(members), "member_count": len(members),
        "performance": {"1d": return_1m / 20, "1w": return_1m / 4, "1m": return_1m, "3m": return_1m * 1.8, "6m": return_1m * 2.5, "1y": return_1m * 3.2},
        "relative_strength": {"vs_spy_1w": rs * .5, "vs_spy_1m": rs, "vs_spy_3m": rs * 1.4, "trend": "Improving" if rs >= 0 else "Weakening"},
        "breadth": {"percent_above_ema20": breadth + 5, "percent_above_ema50": breadth, "percent_above_ema200": breadth - 10},
        "participation": {"positive_return_participation_pct": breadth, "participation_score": breadth},
        "concentration": {"classification": "low", "top_contributors": [{"ticker": members[0], "absolute_contribution_share_pct": 28}] if members else []},
        "component_scores": {"momentum": score, "relative_strength": score, "breadth": breadth, "participation": breadth, "concentration_quality": 85},
        "definition": {"parent_sector_ids": ["information_technology"], "parent_sector_labels": ["Information Technology"]},
        "members": [{"ticker": symbol, "company_name": symbol, "role": "core", "weight": 1 / len(members), "return_1m": return_1m + index} for index, symbol in enumerate(members)],
    }


def neutral_theme() -> dict[str, Any]:
    return theme_row("balanced_infrastructure", "Balanced Infrastructure", 2, "Neutral", 50, 0.2, 50, 0.3, ["IBM", "CSCO", "ORCL"])


def sector_row(sector_id: str, name: str, rank: int, classification: str, score: float, rs: float, breadth: float, return_1m: float) -> dict[str, Any]:
    return {
        "id": sector_id, "name": name, "symbol": "XLK" if sector_id == "information_technology" else "XLI",
        "returns": {"1d": return_1m / 20, "1w": return_1m / 4, "1m": return_1m, "3m": return_1m * 1.8, "6m": return_1m * 2.5, "1y": return_1m * 3.2},
        "rotation": {"1m": {"relative_strength": 100 + rs, "relative_momentum": 100 + (score - 50) / 5, "quadrant": classification.lower()}},
        "source": "live",
        "metadata": {"status": classification, "rank": rank, "composite_score": score, "relative_strength_1m": rs, "percent_above_50ema": breadth, "coverage_percent": 100, "successful_symbols": 8, "total_members": 8, "as_of": "2026-07-21", "snapshot_id": "sector-v7"},
    }


def watch_item(
    symbol: str,
    *,
    score: float | None = None,
    change: float | None = None,
    signal: str | None = None,
    setup: str | None = None,
    source_state: str = "live",
) -> dict[str, Any]:
    profile = SECURITY_FIXTURE_PROFILES.get(symbol.upper(), {})
    score_value = float(score if score is not None else profile.get("score", 76))
    change_value = float(change if change is not None else profile.get("change", 1.8))
    signal_value = str(signal if signal is not None else profile.get("signal", "Buy"))
    setup_value = str(setup if setup is not None else profile.get("setup", "Base breakout"))
    item = {
        "symbol": symbol, "ticker": symbol, "change_percent": change_value, "overall_score": score_value,
        "signal": signal_value, "setup": setup_value,
        "trend": str(profile.get("trend") or ("Uptrend" if score_value >= 50 else "Downtrend")),
        "rs_rank": score_value, "source_state": source_state, "overall_status": "complete" if source_state == "live" else source_state,
        "missing_sections": [], "analysis_updated_at": "2026-07-21T20:00:00+00:00",
    }
    if profile.get("summary"):
        item["summary"] = profile["summary"]
    if profile.get("context"):
        item["context"] = profile["context"]
    return item


def stock_chart(symbol: str, *, direction: int = 1) -> dict[str, Any]:
    normalized = symbol.upper()
    if normalized == "PANW" and direction == 1:
        prices = [
            round(185 + 0.27 * min(index, 70) + 0.06 * max(index - 70, 0) + 1.9 * sin(index / 4.7), 2)
            for index in range(100)
        ]
        volumes = [
            1_350_000 + index * 2_200 + int(90_000 * (1 + sin(index / 3.8)))
            for index in range(100)
        ]
        volumes[-1] = int((sum(volumes[-20:-1]) / 19) * 0.78)
        support = round(min(prices[-20:]) - 0.6, 2)
        resistance = round(max(prices[-20:]) + 0.4, 2)
        breakout = round(max(prices[-20:]) + 1.0, 2)
        reason = "PANW is consolidating after an observed advance with volume below its recent average."
    elif normalized == "FTNT" and direction == 1:
        prices = []
        for index in range(100):
            if index < 70:
                baseline = 66 + index * 0.24
            elif index < 90:
                baseline = 82.8 - (index - 70) * 0.20
            else:
                baseline = 78.8 + (index - 90) * 0.32
            prices.append(round(baseline + 0.9 * sin(index / 3.7), 2))
        volumes = [
            900_000 + index * 1_500 + int(70_000 * (1 + sin(index / 2.9)))
            for index in range(100)
        ]
        volumes[-1] = int((sum(volumes[-20:-1]) / 19) * 1.45)
        support = round(min(prices[-20:]) - 0.4, 2)
        resistance = round(max(prices[-20:]) + 0.5, 2)
        breakout = round(max(prices[-20:]) + 0.9, 2)
        reason = "FTNT is attempting to reclaim its observed pullback range with expanding latest-session volume."
    else:
        prices = [100 + direction * index * .35 for index in range(100)]
        volumes = [1_000_000 + index * 2500 for index in range(100)]
        support = min(prices[-20:]) - 1
        resistance = max(prices[-20:]) + 1
        breakout = max(prices[-20:]) + 1.5
        reason = f"{symbol} has a deterministic V7 fixture history."
    return {
        "symbol": symbol, "price_history": prices, "volumes": volumes,
        "support": support, "resistance": resistance, "breakout": breakout,
        "source": "live", "as_of": "2026-07-21", "reason": reason,
    }


def taxonomy_rows() -> list[dict[str, Any]]:
    rows = []
    for theme_id, members in THEME_MEMBERS.items():
        industry = "Cybersecurity" if theme_id == "cybersecurity" else "Data Storage"
        for symbol in members:
            rows.append({"security_id": f"sec-{symbol.lower()}", "ticker": symbol, "company_name": symbol, "sector": "Information Technology", "sector_id": "information_technology", "industry": industry, "mapping_type": "validated_security_master_membership"})
    for symbol in ("IBM", "CSCO", "ORCL"):
        rows.append({"security_id": f"sec-{symbol.lower()}", "ticker": symbol, "company_name": symbol, "sector": "Information Technology", "sector_id": "information_technology", "industry": "IT Services", "mapping_type": "validated_security_master_membership"})
    return rows


def save_theme(report: dict[str, Any], theme_id: str, symbols: list[str]) -> None:
    report["research_preferences"] = {"saved_stocks": list(symbols), "saved_sectors": [], "saved_themes": [theme_id]}
    report["watchlist_summary"]["symbols_requested"] = list(symbols)
    report["watchlist_summary"]["items"] = [watch_item(symbol) for symbol in symbols]
    report["stock_charts"] = [stock_chart(symbol) for symbol in symbols]


def previous_snapshot(
    *,
    theme: str | None = None,
    theme_rank: int = 1,
    theme_classification: str = "Leading",
    theme_rs: float = 5,
    theme_breadth: float = 70,
    sector: str | None = None,
    sector_rank: int = 1,
    sector_classification: str = "Leading",
    sector_rs: float = 5,
    sector_breadth: float = 70,
    watch_symbol: str | None = None,
    watch_score: float = 70,
    watch_signal: str = "Buy",
    watch_setup: str = "Base breakout",
) -> dict[str, Any]:
    themes = [] if not theme else [{"theme_id": theme, "display_name": theme.replace("_", " ").title(), "rank": theme_rank, "classification": theme_classification, "relative_strength": {"vs_spy_1m": theme_rs}, "breadth": {"percent_above_ema50": theme_breadth}}]
    sectors = [] if not sector else [{"id": sector, "name": sector.replace("_", " ").title(), "metadata": {"rank": sector_rank, "status": sector_classification, "relative_strength_1m": sector_rs, "percent_above_50ema": sector_breadth}}]
    watch = [] if not watch_symbol else [{"symbol": watch_symbol, "score": watch_score, "signal": watch_signal, "mainSetup": watch_setup}]
    return {"overallThesis": "Prior conditional thesis.", "marketDate": "2026-07-20", "themeRanking": themes, "sectorRanking": sectors, "watchlistSummary": watch}


def timeline_points() -> list[dict[str, Any]]:
    return [
        {"marketDate": "2026-07-08", "regime": "Range", "health": 52, "breadth": 44, "risk": 61, "volatilityState": "Elevated", "sectorLeader": "Industrials", "sectorLaggard": "Utilities", "researchFocus": "Industrials"},
        {"marketDate": "2026-07-09", "regime": "Range", "health": 53, "breadth": 45, "risk": 60, "volatilityState": "Elevated", "sectorLeader": "Industrials", "sectorLaggard": "Utilities", "researchFocus": "Industrials"},
        {"marketDate": "2026-07-10", "regime": "Range", "health": 54, "breadth": 46, "risk": 59, "volatilityState": "Elevated", "sectorLeader": "Industrials", "sectorLaggard": "Utilities", "researchFocus": "Industrials"},
        {"marketDate": "2026-07-13", "regime": "Selective", "health": 56, "breadth": 48, "risk": 57, "volatilityState": "Moderate", "sectorLeader": "Industrials", "sectorLaggard": "Utilities", "researchFocus": "Industrials"},
        {"marketDate": "2026-07-14", "regime": "Selective", "health": 58, "breadth": 50, "risk": 54, "volatilityState": "Moderate", "sectorLeader": "Technology", "sectorLaggard": "Utilities", "researchFocus": "Cybersecurity"},
        {"marketDate": "2026-07-15", "regime": "Selective", "health": 60, "breadth": 52, "risk": 52, "volatilityState": "Moderate", "sectorLeader": "Technology", "sectorLaggard": "Utilities", "researchFocus": "Cybersecurity"},
        {"marketDate": "2026-07-16", "regime": "Selective", "health": 62, "breadth": 54, "risk": 49, "volatilityState": "Contained", "sectorLeader": "Technology", "sectorLaggard": "Utilities", "researchFocus": "Cybersecurity"},
        {"marketDate": "2026-07-17", "regime": "Selective", "health": 64, "breadth": 55, "risk": 47, "volatilityState": "Contained", "sectorLeader": "Technology", "sectorLaggard": "Utilities", "researchFocus": "Cybersecurity"},
        {"marketDate": "2026-07-20", "regime": "Selective Risk", "health": 66, "breadth": 57, "risk": 44, "volatilityState": "Contained", "sectorLeader": "Technology", "sectorLaggard": "Utilities", "researchFocus": "Cybersecurity"},
        {"marketDate": "2026-07-21", "regime": "Selective Risk", "health": 68, "breadth": 58, "risk": 42, "volatilityState": "Contained", "sectorLeader": "Technology", "sectorLaggard": "Utilities", "researchFocus": "Cybersecurity"},
    ]
