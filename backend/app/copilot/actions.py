from __future__ import annotations

from typing import Any

from app.copilot.contracts import (
    CopilotActionType,
    CopilotActionV1,
    CopilotDestination,
)


ACTION_REGISTRY: dict[CopilotDestination, dict[str, Any]] = {
    CopilotDestination.HOME: {"label": "Open Market Pulse", "route": "/", "highlight_target": "market-pulse"},
    CopilotDestination.MARKET_OVERVIEW: {"label": "Open Market Overview", "route": "/market", "tab": "overview"},
    CopilotDestination.INDEXES: {"label": "Open Indexes", "route": "/market", "tab": "indexes"},
    CopilotDestination.BREADTH: {"label": "Open Breadth", "route": "/market", "tab": "breadth", "highlight_target": "breadth"},
    CopilotDestination.HEALTH: {"label": "Open Market Health", "route": "/market", "tab": "health"},
    CopilotDestination.FEAR_GREED: {"label": "Open Fear & Greed", "route": "/market", "tab": "decision", "sub_tab": "fear-greed", "highlight_target": "fear-greed"},
    CopilotDestination.INSTITUTIONS: {"label": "Open Institutions", "route": "/market", "tab": "institutions"},
    CopilotDestination.MACRO: {"label": "Open Macro", "route": "/market", "tab": "macro"},
    CopilotDestination.SECTOR_ROTATION: {"label": "Open Sector Rotation", "route": "/sectors", "section_id": "sectorRotation"},
    CopilotDestination.SECTOR_DETAIL: {"label": "Open Sector Detail", "route": "/sectors", "section_id": "sectorHeatmap", "action_type": CopilotActionType.OPEN_ENTITY},
    CopilotDestination.THEME_DETAIL: {"label": "Open Theme Detail", "route": "/sectors", "section_id": "themesHeatmap", "action_type": CopilotActionType.OPEN_ENTITY},
    CopilotDestination.LEADERSHIP: {"label": "Open Leadership Scanner", "route": "/sectors", "section_id": "emergingLeadership"},
    CopilotDestination.STOCK_DETAIL: {"label": "Open Stock Detail", "route": "/watchlist", "section_id": "stocks", "action_type": CopilotActionType.OPEN_ENTITY},
    CopilotDestination.STOCK_TECHNICAL: {"label": "Open Stock Technical", "route": "/watchlist", "section_id": "stocks", "sub_tab": "technical", "action_type": CopilotActionType.OPEN_ENTITY},
    CopilotDestination.STOCK_SIGNALS: {"label": "Open Stock Signals", "route": "/watchlist", "section_id": "stocks", "sub_tab": "signals", "action_type": CopilotActionType.OPEN_ENTITY},
    CopilotDestination.STOCK_RISK: {"label": "Open Stock Risk", "route": "/watchlist", "section_id": "stocks", "sub_tab": "risk", "action_type": CopilotActionType.OPEN_ENTITY},
    CopilotDestination.WATCHLIST: {"label": "Open Watchlist", "route": "/watchlist"},
    CopilotDestination.REPORT: {"label": "Open Daily Report", "route": "/report"},
    CopilotDestination.REPORT_RESEARCH_FOCUS: {"label": "Open Research Focus", "route": "/report", "section_id": "research-focus", "action_type": CopilotActionType.OPEN_REPORT_SECTION},
    CopilotDestination.REPORT_SCENARIOS: {"label": "Open Report Scenarios", "route": "/report", "section_id": "scenarios", "action_type": CopilotActionType.OPEN_REPORT_SECTION},
    CopilotDestination.REPORT_WATCHLIST: {"label": "Open Watchlist Intelligence", "route": "/report", "section_id": "watchlist", "action_type": CopilotActionType.OPEN_REPORT_SECTION},
    CopilotDestination.SETTINGS: {"label": "Open Settings", "route": "/settings"},
}


def get_registered_action(destination: CopilotDestination | str) -> dict[str, Any] | None:
    try:
        key = CopilotDestination(destination)
    except ValueError:
        return None
    value = ACTION_REGISTRY.get(key)
    return dict(value) if value else None


def build_action(
    destination: CopilotDestination | str,
    *,
    entity: str | None = None,
    parameters: dict[str, str] | None = None,
    label: str | None = None,
) -> CopilotActionV1 | None:
    try:
        key = CopilotDestination(destination)
    except ValueError:
        return None
    definition = ACTION_REGISTRY.get(key)
    if not definition:
        return None
    action_parameters = dict(parameters or {})
    if entity:
        action_parameters.setdefault("entity", entity)
        if key in {
            CopilotDestination.STOCK_DETAIL,
            CopilotDestination.STOCK_TECHNICAL,
            CopilotDestination.STOCK_SIGNALS,
            CopilotDestination.STOCK_RISK,
        }:
            action_parameters.setdefault("symbol", entity.upper())
        elif key == CopilotDestination.SECTOR_DETAIL:
            action_parameters.setdefault("sectorId", entity)
        elif key == CopilotDestination.THEME_DETAIL:
            action_parameters.setdefault("themeId", entity)
    if definition.get("tab"):
        action_parameters.setdefault("tab", str(definition["tab"]))
    if definition.get("sub_tab"):
        action_parameters.setdefault("subTab", str(definition["sub_tab"]))
        if key in {
            CopilotDestination.STOCK_TECHNICAL,
            CopilotDestination.STOCK_SIGNALS,
            CopilotDestination.STOCK_RISK,
        }:
            action_parameters.setdefault("stockTab", str(definition["sub_tab"]))
    if definition.get("section_id"):
        action_parameters.setdefault("sectionId", str(definition["section_id"]))
    return CopilotActionV1(
        action_id=f"action-{key.value}-{(entity or 'default').lower()}",
        label=label or str(definition["label"]),
        action_type=definition.get("action_type", CopilotActionType.NAVIGATE),
        destination_id=key,
        route=str(definition["route"]),
        tab=definition.get("tab"),
        sub_tab=definition.get("sub_tab"),
        section_id=definition.get("section_id"),
        entity=entity,
        highlight_target=definition.get("highlight_target") or definition.get("section_id"),
        parameters=action_parameters,
    )


def list_registered_actions() -> list[CopilotActionV1]:
    return [action for destination in ACTION_REGISTRY if (action := build_action(destination))]


def is_registered_route(route: str) -> bool:
    return any(str(value["route"]) == route for value in ACTION_REGISTRY.values())
