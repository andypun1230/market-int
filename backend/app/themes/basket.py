from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Iterable

from app.market_history.storage import DailyBar
from app.themes.models import ThemeBasketBar, ThemeDefinition, ThemeMember
from app.themes.policy import THEME_BASKET_FORMULA_VERSION, ThemePolicy


def build_equal_weight_basket(
    definition: ThemeDefinition,
    members: Iterable[ThemeMember],
    histories: dict[str, tuple[DailyBar, ...]],
    *,
    source_state: str,
    policy: ThemePolicy | None = None,
) -> list[ThemeBasketBar]:
    """Build date-aligned current-basket bars without interpolating sessions."""
    current = policy or ThemePolicy()
    active_members = [member for member in members if member.active]
    histories_by_date = {
        member.ticker.upper(): {bar.session_date: bar for bar in histories.get(member.ticker.upper(), ()) if bar.adjusted and bar.quality_status == "valid"}
        for member in active_members
    }
    sessions = sorted({date for values in histories_by_date.values() for date in values})
    level = 100.0
    bars: list[ThemeBasketBar] = []
    for index, session_date in enumerate(sessions):
        if index == 0:
            continue
        previous_date = sessions[index - 1]
        eligible = [
            member for member in active_members
            if session_date in histories_by_date[member.ticker.upper()]
            and previous_date in histories_by_date[member.ticker.upper()]
            and histories_by_date[member.ticker.upper()][previous_date].close > 0
        ]
        coverage = len(eligible) / len(active_members) if active_members else 0.0
        if coverage < definition.partial_coverage_threshold:
            continue
        returns = [
            histories_by_date[member.ticker.upper()][session_date].close / histories_by_date[member.ticker.upper()][previous_date].close - 1
            for member in eligible
        ]
        daily_return = sum(returns) / len(returns)
        level *= 1 + daily_return
        input_hash = hashlib.sha256(json.dumps({
            "theme_id": definition.theme_id,
            "version": definition.version,
            "date": session_date,
            "previous_date": previous_date,
            "members": [(member.ticker, histories_by_date[member.ticker.upper()][previous_date].close, histories_by_date[member.ticker.upper()][session_date].close) for member in eligible],
            "formula": current.basket_formula_version,
        }, sort_keys=True).encode()).hexdigest()
        bars.append(ThemeBasketBar(
            theme_id=definition.theme_id,
            theme_version=definition.version,
            session_date=session_date,
            index_level=round(level, 8),
            daily_return=round(daily_return, 10),
            eligible_members=len(eligible),
            total_members=len(active_members),
            coverage_ratio=round(coverage, 6),
            source_state=source_state,
            formula_version=current.basket_formula_version,
            input_hash=input_hash,
            generated_at=datetime.now(timezone.utc).isoformat(),
        ))
    return bars
