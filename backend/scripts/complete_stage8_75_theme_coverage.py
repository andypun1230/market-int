#!/usr/bin/env python3
"""Audit and apply the final provider-backed Stage 8.75 coverage pass.

The live audit/refresh in this command is deliberately separate from the
hermetic release gate.  It uses only the configured Polygon provider, the
canonical security master, and the existing durable-history updater.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.market_history.storage import DailyBarStorage
from app.market_history.updater import BreadthUniverseHistoryUpdater
from app.providers.polygon_provider import PolygonMarketDataProvider
from app.securities.models import SecurityAlias, SecurityProviderSymbol, SecurityRecord
from app.securities.registry import SECTOR_BY_ID
from app.securities.storage import SecurityMasterStorage
from app.themes.launch import RETIRED_THEME_MAPPINGS, THEME_MAPPINGS, get_launch_theme_registry


BASELINE_SYMBOLS_PATH = BACKEND_ROOT / "data" / "reference" / "themes" / "stage8.75-unregistered-symbols-v1.txt"
ALLOWED_EXCHANGES = {"XNAS": "NASDAQ", "XNYS": "NYSE", "XASE": "NYSE American"}
ALLOWED_ASSET_TYPES = {"CS": "equity", "ADRC": "adr"}
SUCCESSORS = {"SQ": "XYZ", "FI": "FISV", "PARA": "PSKY"}
LEGACY_METADATA_DATES = {"SQ": "2025-01-17", "FI": "2025-11-10", "PARA": "2025-08-06", "DESP": "2025-05-14", "JNPR": "2025-07-01"}
DELISTED_SYMBOLS = {"DESP", "JNPR"}
INSTRUMENT_REVIEW_SYMBOLS = {"ABB", "ADYEY", "FANUY", "NTDOY"}
PROVIDER_SEGMENTS = {
    "XYZ": (
        ("SQ", "2015-11-19", "2025-01-17", "ticker_rename:SQ_to_XYZ"),
        ("XYZ", "2025-01-21", None, "ticker_rename:SQ_to_XYZ"),
    ),
    "FISV": (
        ("FISV", "1986-09-25", "2023-06-06", "ticker_rename:FISV_to_FI_to_FISV"),
        ("FI", "2023-06-07", "2025-11-10", "ticker_rename:FISV_to_FI_to_FISV"),
        ("FISV", "2025-11-11", None, "ticker_rename:FISV_to_FI_to_FISV"),
    ),
    "PSKY": (
        ("PARA", "2022-02-17", "2025-08-06", "merger_successor:PARA_to_PSKY"),
        ("PSKY", "2025-08-07", None, "merger_successor:PARA_to_PSKY"),
    ),
}

CATEGORY_NAMES = {
    2: "valid active symbol but missing security-master registration",
    4: "renamed ticker",
    6: "delisted",
    7: "acquired or merged",
    8: "ETF, ADR, foreign listing, or special instrument needing explicit support decision",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_security_id(details: dict[str, Any]) -> str:
    ticker = str(details.get("ticker") or "").upper()
    figi = str(details.get("composite_figi") or "").strip()
    cik = str(details.get("cik") or "").strip()
    identity = f"composite_figi:{figi}" if figi else f"cik_ticker:{cik}:{ticker}"
    return f"theme-sec-{hashlib.sha256(f'polygon:{identity}'.encode()).hexdigest()[:16]}"


def provider_details(provider: PolygonMarketDataProvider, symbol: str, on_date: str | None = None) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    try:
        return provider.get_ticker_details(symbol, on_date=on_date), None
    except Exception as error:
        return None, {
            "category": getattr(error, "category", type(error).__name__),
            "message": str(error),
            "request_id": getattr(error, "request_id", None),
            "retry_after": getattr(error, "retry_after", None),
        }


def parallel_map(items: list[str], function: Callable[[str], Any], concurrency: int) -> dict[str, Any]:
    result: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=max(1, min(concurrency, 4))) as pool:
        futures = {pool.submit(function, item): item for item in items}
        for future in as_completed(futures):
            result[futures[future]] = future.result()
    return result


def security_record(details: dict[str, Any], audited_at: str) -> SecurityRecord:
    ticker = str(details["ticker"]).upper()
    provider_type = str(details.get("type") or "")
    return SecurityRecord(
        security_id=stable_security_id(details),
        ticker=ticker,
        company_name=str(details.get("name") or ticker).strip(),
        exchange=ALLOWED_EXCHANGES[str(details["primary_exchange"])],
        asset_type=ALLOWED_ASSET_TYPES[provider_type],
        active=True,
        sector="Unknown",
        sector_id=None,
        industry=str(details.get("sic_description") or "").strip() or None,
        quote_provider_symbol=ticker,
        history_provider_symbol=ticker,
        currency=str(details.get("currency_name") or "USD").upper(),
        country="US",
        effective_from=str(details.get("list_date") or audited_at[:10]),
        source=f"polygon-reference:/v3/reference/tickers/{ticker}",
        source_timestamp=audited_at,
        verified_at=audited_at,
        metadata_version=1,
    )


def eligible_current(details: dict[str, Any] | None) -> bool:
    return bool(
        details
        and details.get("active") is True
        and details.get("market") == "stocks"
        and details.get("locale") == "us"
        and details.get("primary_exchange") in ALLOWED_EXCHANGES
        and details.get("type") in ALLOWED_ASSET_TYPES
    )


def apply_security_master(storage: SecurityMasterStorage, records: dict[str, SecurityRecord], audited_at: str) -> dict[str, Any]:
    before = storage.active_securities(tuple(records))
    for record in records.values():
        storage.upsert_security(record)

    source = "stage8.75-provider-identity-audit:polygon-reference-and-adjusted-daily-history"
    aliases = (
        SecurityAlias("SQ", records["XYZ"].security_id, "Block, Inc.", "2025-01-17", "ticker_rename", "same_entity_same_figi_and_cik", source, audited_at),
        SecurityAlias("FI", records["FISV"].security_id, "Fiserv, Inc.", "2025-11-10", "ticker_rename", "same_entity_same_figi_and_cik", source, audited_at),
        SecurityAlias("PARA", records["PSKY"].security_id, "Paramount Global Class B", "2025-08-06", "merger", "successor_entity_contiguous_provider_history", source, audited_at),
    )
    for alias in aliases:
        storage.upsert_alias(alias)
    provider_symbols: list[SecurityProviderSymbol] = []
    for canonical, segments in PROVIDER_SEGMENTS.items():
        for provider_symbol, effective_from, effective_to, lineage in segments:
            item = SecurityProviderSymbol(
                security_id=records[canonical].security_id,
                provider="polygon",
                purpose="history",
                provider_symbol=provider_symbol,
                effective_from=effective_from,
                effective_to=effective_to,
                source=source,
                verified_at=audited_at,
                corporate_action_lineage=lineage,
            )
            storage.upsert_provider_symbol(item)
            provider_symbols.append(item)
    return {
        "eligible_records": len(records),
        "newly_registered": sorted(set(records) - set(before)),
        "existing_reverified": sorted(set(records) & set(before)),
        "aliases_upserted": [item.alias_ticker for item in aliases],
        "provider_symbol_segments": [item.model_dump() for item in provider_symbols],
    }


def refresh_history(
    records: dict[str, SecurityRecord],
    storage: SecurityMasterStorage,
    *,
    concurrency: int,
    lookback: int,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    registry = get_launch_theme_registry()
    references = {"SPY"}
    references.update(symbol for definition in registry.launch() for symbol in definition.benchmark_symbols)
    references.update(SECTOR_BY_ID[item]["etf_symbol"] for definition in registry.launch() for item in definition.parent_sector_ids if item in SECTOR_BY_ID)
    canonical_symbols = set(records)
    direct_symbols = sorted(canonical_symbols - set(PROVIDER_SEGMENTS))
    reference_symbols = sorted(references - canonical_symbols)
    updater = BreadthUniverseHistoryUpdater()
    provider = updater.repository.get_provider_for("daily_history")
    request_count_before = int(getattr(provider, "request_count", 0))
    rate_limits_before = int(getattr(provider, "rate_limit_events", 0))

    def update(symbol: str) -> dict[str, Any]:
        if symbol in PROVIDER_SEGMENTS:
            segments = storage.provider_symbols(symbol, provider="polygon", purpose="history")
            return updater.update_symbol_history_segments(
                symbol,
                security_id=records[symbol].security_id,
                segments=segments,
                lookback_calendar_days=lookback,
                strict_live=True,
            )
        record = records.get(symbol)
        return updater.update_symbol(
            symbol,
            provider_symbol=record.history_provider_symbol if record else symbol,
            canonical_security_id=record.security_id if record else None,
            lookback_calendar_days=lookback,
            strict_live=True,
        )

    requested = [*direct_symbols, *sorted(PROVIDER_SEGMENTS), *reference_symbols]
    results: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max(1, min(concurrency, 4))) as pool:
        futures = {pool.submit(update, symbol): symbol for symbol in requested}
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                results[symbol] = future.result()
            except Exception as error:
                failures.append({
                    "symbol": symbol,
                    "category": getattr(error, "category", type(error).__name__),
                    "error": str(error),
                    "request_id": getattr(error, "request_id", None),
                    "retry_after": getattr(error, "retry_after", None),
                })
    inserted = sum(int(item.get("inserted_bars", 0)) for item in results.values())
    updated = sum(int(item.get("updated_bars", 0)) for item in results.values())
    received = sum(int(item.get("received_bars", 0)) for item in results.values())
    latest = [str(item.get("latest_date")) for item in results.values() if item.get("latest_date")]
    report = {
        "configured_path": "existing provider router -> strict-live Polygon daily history -> DailyBarStorage",
        "lookback_calendar_days": lookback,
        "concurrency": max(1, min(concurrency, 4)),
        "requested_symbols": requested,
        "requested_symbol_count": len(requested),
        "new_security_symbols": sorted(canonical_symbols),
        "benchmark_symbols": sorted(references),
        "completed_symbols": sorted(results),
        "failed": failures,
        "inserted_bars": inserted,
        "updated_bars": updated,
        "skipped_bars": max(0, received - inserted - updated),
        "received_bars": received,
        "provider_requests": int(getattr(provider, "request_count", 0)) - request_count_before,
        "rate_limit_events": int(getattr(provider, "rate_limit_events", 0)) - rate_limits_before,
        "latest_complete_market_date": min(latest) if latest else None,
        "adjusted_policy": True,
        "strict_live": True,
        "test_or_mock_rows": 0,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    return report, results


def history_probe(provider: PolygonMarketDataProvider, symbol: str, lookback: int) -> dict[str, Any]:
    try:
        history = provider.get_history(symbol, resolution="D", days=lookback)
        candles = history.candles
        return {
            "available": True,
            "session_count": len(candles),
            "earliest_date": candles[0].timestamp[:10],
            "latest_date": candles[-1].timestamp[:10],
            "adjusted": history.adjusted,
            "source_state": history.source_state,
            "error": None,
        }
    except Exception as error:
        return {
            "available": False,
            "session_count": 0,
            "earliest_date": None,
            "latest_date": None,
            "adjusted": None,
            "source_state": "unavailable",
            "error": {"category": getattr(error, "category", type(error).__name__), "message": str(error)},
        }


def stored_history_state(bars: list[Any]) -> dict[str, Any]:
    dates = [item.session_date for item in bars]
    return {
        "available": bool(bars),
        "session_count": len(bars),
        "earliest_date": dates[0] if dates else None,
        "latest_date": dates[-1] if dates else None,
        "adjusted": all(item.adjusted for item in bars) if bars else None,
        "source_state": "live" if bars else "unavailable",
        "duplicate_sessions": len(dates) - len(set(dates)),
        "history_21d_capable": len(bars) >= 22,
        "history_50d_capable": len(bars) >= 50,
        "history_200d_capable": len(bars) >= 200,
    }


def mapping_context(symbol: str) -> tuple[list[str], list[dict[str, str]]]:
    rows = [item for item in (*THEME_MAPPINGS, *RETIRED_THEME_MAPPINGS) if item.symbol == symbol]
    return sorted({item.theme_id for item in rows}), [
        {"theme_id": item.theme_id, "exposure": item.exposure, "review_status": item.review_status}
        for item in sorted(rows, key=lambda item: (item.theme_id, item.exposure))
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Complete the provider-backed Stage 8.75 symbol coverage pass.")
    parser.add_argument("--audit-output", type=Path, default=REPOSITORY_ROOT / "artifacts" / "stage8.75-symbol-coverage-audit.json")
    parser.add_argument("--refresh-output", type=Path, default=REPOSITORY_ROOT / "artifacts" / "stage8.75-history-refresh.json")
    parser.add_argument("--apply", action="store_true", help="Apply approved security-master and alias records.")
    parser.add_argument("--refresh-history", action="store_true", help="Run the existing strict-live updater for approved symbols and references.")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--lookback-calendar-days", type=int, default=450)
    args = parser.parse_args()
    if args.refresh_history and not args.apply:
        parser.error("--refresh-history requires --apply")

    audited_at = now_iso()
    baseline = [line.strip().upper() for line in BASELINE_SYMBOLS_PATH.read_text().splitlines() if line.strip()]
    if len(baseline) != 138 or len(set(baseline)) != 138:
        raise RuntimeError("stage8_75_baseline_symbol_set_must_contain_138_unique_symbols")
    provider = PolygonMarketDataProvider()
    current = parallel_map(baseline, lambda symbol: provider_details(provider, symbol), args.concurrency)
    extra_symbols = sorted({*SUCCESSORS.values(), "ABBNY"})
    extras = parallel_map(extra_symbols, lambda symbol: provider_details(provider, symbol), args.concurrency)
    historical: dict[str, tuple[dict[str, Any] | None, dict[str, Any] | None]] = {}
    for symbol, on_date in LEGACY_METADATA_DATES.items():
        historical[symbol] = provider_details(provider, symbol, on_date)

    current_details = {symbol: value[0] for symbol, value in current.items() if value[0]}
    candidate_details = {symbol: details for symbol, details in current_details.items() if eligible_current(details)}
    for successor in SUCCESSORS.values():
        details = extras[successor][0]
        if not eligible_current(details):
            raise RuntimeError(f"verified_successor_not_currently_eligible:{successor}")
        candidate_details[successor] = details
    for legacy, successor in (("SQ", "XYZ"), ("FI", "FISV")):
        old = historical[legacy][0] or {}
        new = candidate_details[successor]
        if not old.get("composite_figi") or old.get("composite_figi") != new.get("composite_figi") or old.get("cik") != new.get("cik"):
            raise RuntimeError(f"same_entity_ticker_transition_identity_mismatch:{legacy}:{successor}")
    paramount = historical["PARA"][0] or {}
    if not paramount or paramount.get("primary_exchange") != candidate_details["PSKY"].get("primary_exchange"):
        raise RuntimeError("paramount_merger_successor_exchange_continuity_not_verified")
    if len(candidate_details) != 132:
        raise RuntimeError(f"expected_132_supported_canonical_candidates:found_{len(candidate_details)}")
    records = {symbol: security_record(details, audited_at) for symbol, details in candidate_details.items()}
    figis = [str(details.get("composite_figi")) for details in candidate_details.values() if details.get("composite_figi")]
    if len(figis) != len(set(figis)):
        raise RuntimeError("duplicate_composite_figi_in_security_master_candidates")

    security_storage = SecurityMasterStorage()
    apply_report: dict[str, Any] = {"applied": False, "eligible_records": len(records)}
    if args.apply:
        apply_report = {"applied": True, **apply_security_master(security_storage, records, audited_at)}

    refresh_report: dict[str, Any] = {"executed": False}
    refresh_results: dict[str, dict[str, Any]] = {}
    if args.refresh_history:
        refresh_report, refresh_results = refresh_history(
            records,
            security_storage,
            concurrency=args.concurrency,
            lookback=args.lookback_calendar_days,
        )
        refresh_report["executed"] = True
        args.refresh_output.parent.mkdir(parents=True, exist_ok=True)
        args.refresh_output.write_text(json.dumps(refresh_report, indent=2, sort_keys=True) + "\n")
        if refresh_report["failed"]:
            raise RuntimeError(f"strict_live_history_refresh_failures:{refresh_report['failed']}")

    bars_storage = DailyBarStorage()
    stored = bars_storage.histories(tuple(records)) if args.refresh_history else {symbol: [] for symbol in records}
    exceptional = sorted(DELISTED_SYMBOLS | INSTRUMENT_REVIEW_SYMBOLS)
    exceptional_history = parallel_map(exceptional, lambda symbol: history_probe(provider, symbol, args.lookback_calendar_days), args.concurrency)

    rows: list[dict[str, Any]] = []
    for symbol in baseline:
        canonical = "ABBNY" if symbol == "ABB" else SUCCESSORS.get(symbol, symbol)
        details = current[symbol][0]
        historical_details = historical.get(symbol, (None, None))[0]
        canonical_details = candidate_details.get(canonical) or extras.get(canonical, (None, None))[0] or details
        themes, exposures = mapping_context(symbol)
        manual_review = False
        if symbol in {"SQ", "FI"}:
            category = 4
            action = f"Register {canonical}; retain {symbol} as a verified historical alias and provider-history segment; use {canonical} in the active mapping."
        elif symbol == "PARA":
            category = 7
            action = "Register PSKY as the verified merger successor; retain PARA as a historical alias and provider-history segment; preserve the thematic exposure."
        elif symbol in DELISTED_SYMBOLS:
            category = 6
            action = "Do not register as active; retain the mapping as an explicit unsupported historical gap pending a governed issuer-action review."
            manual_review = True
        elif symbol in INSTRUMENT_REVIEW_SYMBOLS:
            category = 8
            action = "Do not register or auto-substitute; OTC ADR/special-instrument support requires an explicit future policy decision."
            manual_review = True
        else:
            category = 2
            action = "Register the approved current US-exchange listing and persist strict-live adjusted Polygon history."

        if canonical in stored and stored[canonical]:
            history = stored_history_state(stored[canonical])
        else:
            history = exceptional_history.get(symbol, {"available": False, "session_count": 0, "earliest_date": None, "latest_date": None, "adjusted": None, "source_state": "not_refreshed", "error": None})
            history = {
                **history,
                "duplicate_sessions": 0,
                "history_21d_capable": int(history.get("session_count") or 0) >= 22,
                "history_50d_capable": int(history.get("session_count") or 0) >= 50,
                "history_200d_capable": int(history.get("session_count") or 0) >= 200,
            }
        provider_supported = canonical in records
        current_status = "active_supported" if category == 2 else "renamed_active_successor" if category == 4 else "active_merger_successor" if category == 7 else "historical_delisted" if category == 6 else "explicit_instrument_review_required"
        evidence_symbols = [symbol] if canonical == symbol else [symbol, canonical]
        row = {
            "symbol": symbol,
            "canonical_symbol": canonical if symbol != "ABB" else "ABBNY (unapproved candidate only)",
            "company_entity_name": str((canonical_details or historical_details or {}).get("name") or "Unknown"),
            "exchange": str((canonical_details or historical_details or {}).get("primary_exchange") or "Unknown"),
            "asset_type": ALLOWED_ASSET_TYPES.get(str((canonical_details or historical_details or {}).get("type") or ""), str((canonical_details or historical_details or {}).get("type") or "unknown")),
            "category": {"number": category, "name": CATEGORY_NAMES[category]},
            "current_status": current_status,
            "provider_support": provider_supported,
            "provider_current_metadata": details is not None,
            "provider_error": current[symbol][1],
            "history_availability": history,
            "alias_or_ticker_change": {
                "legacy_symbol": symbol if symbol in SUCCESSORS else None,
                "successor_symbol": SUCCESSORS.get(symbol),
                "provider_segments": [
                    {"provider_symbol": item[0], "effective_from": item[1], "effective_to": item[2], "lineage": item[3]}
                    for item in PROVIDER_SEGMENTS.get(canonical, ())
                ],
            },
            "current_mapped_themes": themes,
            "mapping_exposures": exposures,
            "recommended_action": action,
            "evidence_provenance": {
                "provider": "polygon",
                "reference_endpoints": [f"/v3/reference/tickers/{item}" for item in evidence_symbols],
                "history_endpoint": "/v2/aggs/ticker/{symbol}/range/1/day/{from}/{to}",
                "approved_repository_client": "app.providers.polygon_provider.PolygonMarketDataProvider",
                "audited_at": audited_at,
                "historical_reference_date": LEGACY_METADATA_DATES.get(symbol),
                "composite_figi": (canonical_details or {}).get("composite_figi"),
                "cik": (canonical_details or {}).get("cik"),
            },
            "manual_review_required": manual_review,
        }
        rows.append(row)

    category_counts = {str(number): sum(item["category"]["number"] == number for item in rows) for number in sorted(CATEGORY_NAMES)}
    artifact = {
        "stage": "8.75-final-security-master-coverage",
        "audit_version": 1,
        "audited_at": audited_at,
        "scope": "The exact 138 symbols absent from the canonical master at the validated Stage 8.75 baseline.",
        "source_symbol_file": str(BASELINE_SYMBOLS_PATH.relative_to(REPOSITORY_ROOT)),
        "symbol_count": len(rows),
        "classification_contract": "Each audited symbol has exactly one numbered governed category.",
        "category_counts": category_counts,
        "valid_active_with_approved_canonical_successor": sum(item["category"]["number"] in {2, 4, 7} for item in rows),
        "manual_review_required": [item["symbol"] for item in rows if item["manual_review_required"]],
        "unsupported_or_not_registered": [item["symbol"] for item in rows if not item["provider_support"]],
        "security_master_apply": apply_report,
        "production_history_refresh": refresh_report,
        "provider_audit_statistics": {
            "reference_and_exception_history_requests": provider.request_count,
            "rate_limit_events": provider.rate_limit_events,
            "current_metadata_successes": len(current_details),
            "current_metadata_failures": len(baseline) - len(current_details),
            "candidate_canonical_records": len(records),
        },
        "support_policy": {
            "approved_exchanges": ALLOWED_EXCHANGES,
            "approved_asset_types": ALLOWED_ASSET_TYPES,
            "exchange_listed_adrs": "supported when current Polygon metadata and adjusted strict-live history both validate",
            "otc_adrs": "not registered in this pass; explicit instrument-policy review required",
            "missing_history": "never converted to zero and never substituted with fixtures, generated data, or another symbol",
        },
        "mapping_corrections": [
            {"theme_id": "digital_payments", "legacy_symbol": "SQ", "successor_symbol": "XYZ", "exposure": "core", "provider_boundary": "2025-01-17/2025-01-21", "reason": "same CIK and composite FIGI; contiguous adjusted provider history"},
            {"theme_id": "digital_payments", "legacy_symbol": "FI", "successor_symbol": "FISV", "exposure": "significant", "provider_boundary": "2025-11-10/2025-11-11", "reason": "same CIK and composite FIGI; contiguous adjusted provider history"},
            {"theme_id": "streaming_digital_entertainment", "legacy_symbol": "PARA", "successor_symbol": "PSKY", "exposure": "significant", "provider_boundary": "2025-08-06/2025-08-07", "reason": "provider-verified merger successor with contiguous adjusted history; entity identifiers intentionally differ"},
        ],
        "symbols": rows,
    }
    args.audit_output.parent.mkdir(parents=True, exist_ok=True)
    args.audit_output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "audit_output": str(args.audit_output),
        "refresh_output": str(args.refresh_output) if args.refresh_history else None,
        "audited": len(rows),
        "category_counts": category_counts,
        "eligible_canonical_records": len(records),
        "newly_registered": len(apply_report.get("newly_registered", [])),
        "history_refresh_failures": len(refresh_report.get("failed", [])),
        "provider_requests": provider.request_count + int(refresh_report.get("provider_requests", 0)),
        "rate_limit_events": provider.rate_limit_events + int(refresh_report.get("rate_limit_events", 0)),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
