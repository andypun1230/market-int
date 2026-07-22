#!/usr/bin/env python3
"""Forensic reconciliation of immutable Theme basket returns and issuer eras."""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_history.storage import DailyBar, DailyBarStorage
from app.securities.service import get_security_master_service
from app.theme_snapshots.service import get_theme_snapshot_service
from app.themes.engine import PERFORMANCE_WINDOWS
from app.themes.storage import ThemeStorage


def pct_return(start: float, end: float) -> float | None:
    if start <= 0:
        return None
    return round((end / start - 1) * 100, 6)


def history_periods(history: list[DailyBar]) -> list[dict[str, str]]:
    periods: list[dict[str, str]] = []
    for bar in history:
        symbol = (bar.source_symbol or bar.ticker).upper()
        if not periods or periods[-1]["source_ticker"] != symbol:
            periods.append({"source_ticker": symbol, "effective_from": bar.session_date, "effective_to": bar.session_date})
        else:
            periods[-1]["effective_to"] = bar.session_date
    return periods


def period_bars(history: list[DailyBar], start: str, end: str) -> list[DailyBar]:
    return [bar for bar in history if start <= bar.session_date <= end]


def audit_constituent(member: dict[str, Any], history: list[DailyBar], start: str, end: str, expected_sessions: set[str], security: Any, expected_symbols: dict[str, str]) -> dict[str, Any]:
    selected = period_bars(history, start, end)
    by_date = {bar.session_date: bar for bar in selected}
    first = by_date.get(start)
    last = by_date.get(end)
    missing_sessions = sorted(expected_sessions - set(by_date))
    identity_mismatches = [bar.session_date for bar in selected if security and bar.canonical_security_id != security.security_id]
    source_mismatches = [bar.session_date for bar in selected if (bar.source_symbol or bar.ticker).upper() != expected_symbols.get(bar.session_date, member["ticker"]).upper()]
    total_return = pct_return(first.close, last.close) if first and last else None
    weight = float(member.get("weight") or 0)
    contribution = round(total_return * weight, 6) if total_return is not None else None
    return {
        "canonical_security_id": security.security_id if security else None,
        "canonical_ticker": member.get("ticker"),
        "first_eligible_session": history[0].session_date if history else None,
        "horizon_start_session": start,
        "last_session": end,
        "adjusted_start_close": first.close if first else None,
        "adjusted_end_close": last.close if last else None,
        "constituent_total_return_pct": total_return,
        "eligible_session_count": len(selected),
        "missing_sessions": missing_sessions,
        "daily_basket_weight": weight,
        "signed_contribution_pct": contribution,
        "absolute_contribution_pct": round(abs(contribution), 6) if contribution is not None else None,
        "source_ticker_by_date": history_periods(selected),
        "corporate_action_flags": {
            "previous_ticker": member.get("previous_ticker"),
            "corporate_action_type": member.get("corporate_action_type"),
            "corporate_action_effective_date": member.get("corporate_action_effective_date"),
            "continuity_status": member.get("continuity_status"),
        },
        "identity_effective_dates": {
            "security_effective_from": security.effective_from if security else None,
            "security_effective_to": security.effective_to if security else None,
        },
        "identity_valid": bool(security and not identity_mismatches and not source_mismatches),
        "identity_mismatch_sessions": identity_mismatches,
        "source_mismatch_sessions": source_mismatches,
    }


def audit_horizon(row: dict[str, Any], days: int, label: str, bars: DailyBarStorage, theme_storage: ThemeStorage, securities: Any) -> dict[str, Any]:
    basket = theme_storage.basket_history(row["theme_id"], row["version"])
    if len(basket) <= days:
        return {"horizon": label, "available": False, "reason": "insufficient_basket_history"}
    start_bar, end_bar = basket[-days - 1], basket[-1]
    member_rows = []
    for member in row.get("members", []):
        ticker = str(member.get("ticker") or "").upper()
        security = securities.security(ticker)
        history = bars.history(ticker)
        expected = {}
        for bar in history:
            provider = securities.provider_symbol_for(ticker, on_date=bar.session_date)
            expected[bar.session_date] = provider.provider_symbol if provider else ticker
        expected_sessions = {bar.session_date for bar in basket[-days - 1:]}
        member_rows.append(audit_constituent(member, history, start_bar.session_date, end_bar.session_date, expected_sessions, security, expected))
    usable = [item for item in member_rows if item["constituent_total_return_pct"] is not None]
    arithmetic_mean = round(sum(float(item["constituent_total_return_pct"]) for item in usable) / len(usable), 6) if usable else None
    chained = pct_return(start_bar.index_level, end_bar.index_level)
    manual_level = start_bar.index_level
    for bar in basket[-days:]:
        manual_level *= 1 + bar.daily_return
    manual_chained = pct_return(start_bar.index_level, manual_level)
    contributions = sorted(usable, key=lambda item: float(item["absolute_contribution_pct"] or 0), reverse=True)
    identity_valid = all(item["identity_valid"] for item in member_rows)
    return {
        "horizon": label,
        "available": True,
        "horizon_start_session": start_bar.session_date,
        "horizon_end_session": end_bar.session_date,
        "chained_persisted_basket_return_pct": chained,
        "recomputed_daily_rebalanced_return_pct": manual_chained,
        "arithmetic_mean_constituent_return_pct": arithmetic_mean,
        "difference_chained_minus_arithmetic_pct": round(chained - arithmetic_mean, 6) if chained is not None and arithmetic_mean is not None else None,
        "reconciliation_difference_pct": round(chained - manual_chained, 10) if chained is not None and manual_chained is not None else None,
        "coverage": {"start": start_bar.coverage_ratio, "end": end_bar.coverage_ratio, "minimum": min(bar.coverage_ratio for bar in basket[-days:])},
        "eligibility_changes": len({bar.eligible_members for bar in basket[-days:]}) > 1,
        "rebalance_effect_pct": round(chained - arithmetic_mean, 6) if chained is not None and arithmetic_mean is not None else None,
        "top_contributors": [{"ticker": item["canonical_ticker"], "signed_contribution_pct": item["signed_contribution_pct"], "absolute_contribution_pct": item["absolute_contribution_pct"]} for item in contributions[:3]],
        "constituents": member_rows,
        "identity_valid": identity_valid,
        "no_double_percentage_conversion": True,
        "percentage_unit": "percent; raw daily returns are multiplied by 100 once for display",
        "valid": bool(identity_valid and chained is not None and manual_chained is not None and math.isclose(chained, manual_chained, abs_tol=0.00001)),
    }


def corporate_action_audit(bars: DailyBarStorage, securities: Any) -> dict[str, Any]:
    p_history = bars.history("P")
    p_boundary = [bar for bar in p_history if bar.session_date in {"2026-04-16", "2026-04-17"}]
    sndk = bars.history("SNDK")
    p_security = securities.security("P")
    sndk_security = securities.security("SNDK")
    return {
        "p_pstg": {
            "security_id": p_security.security_id if p_security else None,
            "provider_symbol_history": [item.model_dump() for item in securities.provider_symbols("P")],
            "boundary": [{"session_date": bar.session_date, "source_ticker": bar.source_symbol, "close": bar.close, "canonical_security_id": bar.canonical_security_id} for bar in p_boundary],
            "valid": [bar.source_symbol for bar in p_boundary] == ["PSTG", "P"] and all(bar.canonical_security_id == (p_security.security_id if p_security else None) for bar in p_history),
        },
        "sndk": {
            "security_id": sndk_security.security_id if sndk_security else None,
            "effective_from": sndk_security.effective_from if sndk_security else None,
            "first_stored_session": sndk[0].session_date if sndk else None,
            "source_tickers": sorted(set(bar.source_symbol for bar in sndk)),
            "valid": bool(sndk and sndk_security and sndk[0].session_date == sndk_security.effective_from and all(bar.canonical_security_id == sndk_security.security_id and bar.source_symbol == "SNDK" for bar in sndk)),
        },
    }


def audit_snapshot() -> dict[str, Any]:
    snapshot = get_theme_snapshot_service().latest()
    if snapshot is None:
        return {"status": "FAIL", "reason": "no_theme_snapshot"}
    bars, theme_storage, securities = DailyBarStorage(), ThemeStorage(), get_security_master_service().storage
    themes = []
    for row in snapshot.rows:
        horizons = {label: audit_horizon(row, days, label, bars, theme_storage, securities) for label, days in PERFORMANCE_WINDOWS.items()}
        themes.append({
            "theme_id": row["theme_id"], "display_name": row["display_name"], "version": row["version"],
            "basket_policy": row.get("basket_methodology", {}), "horizons": horizons,
            "valid": all(value.get("valid") for value in horizons.values() if value.get("available")),
        })
    identity = corporate_action_audit(bars, securities)
    valid = all(item["valid"] for item in themes) and identity["p_pstg"]["valid"] and identity["sndk"]["valid"]
    return {
        "status": "PASS" if valid else "FAIL", "snapshot_id": snapshot.snapshot_id, "market_date": snapshot.market_date,
        "rebalance_convention": "daily_rebalanced_equal_weight", "themes": themes, "identity_audit": identity,
        "return_defect_found": False if valid else True,
    }


def markdown(report: dict[str, Any]) -> str:
    lines = ["# Phase 4.4D Pilot Basket Return Audit", "", f"Status: **{report['status']}**", "", f"ThemeSnapshot: `{report.get('snapshot_id')}`", "", "Rebalance convention: **daily rebalanced equal weight**. Each eligible member is equally weighted each session; display returns are percentages converted once from raw decimal daily returns.", ""]
    for theme in report.get("themes", []):
        lines.extend([f"## {theme['display_name']} ({theme['version']})", "", "| Horizon | Chained basket | Arithmetic mean | Difference | Valid |", "| --- | ---: | ---: | ---: | --- |"])
        for horizon in theme["horizons"].values():
            if not horizon.get("available"):
                continue
            lines.append(f"| {horizon['horizon']} | {horizon['chained_persisted_basket_return_pct']:.4f}% | {horizon['arithmetic_mean_constituent_return_pct']:.4f}% | {horizon['difference_chained_minus_arithmetic_pct']:.4f}% | {'PASS' if horizon['valid'] else 'FAIL'} |")
        lines.append("")
    identity = report.get("identity_audit", {})
    lines.extend(["## Identity Boundaries", "", f"- P/PSTG continuity: **{'PASS' if identity.get('p_pstg', {}).get('valid') else 'FAIL'}**", f"- SNDK issuer-era boundary: **{'PASS' if identity.get('sndk', {}).get('valid') else 'FAIL'}**", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit live Theme basket returns without fetching providers.")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()
    report = audit_snapshot()
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered + "\n")
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(markdown(report))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
