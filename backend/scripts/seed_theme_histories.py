#!/usr/bin/env python3
"""Seed durable Polygon history for already reviewed active Theme members."""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path: sys.path.insert(0, str(BACKEND_ROOT))

from app.market_history.updater import BreadthUniverseHistoryUpdater
from app.securities.service import get_security_master_service
from app.themes.identifiers import normalize_theme_id
from app.themes.service import ThemeDefinitionService


def main() -> int:
    parser = argparse.ArgumentParser(description="Mutate durable history only for reviewed active Theme members.", epilog="Theme IDs are canonical snake_case; kebab-case aliases are accepted at the command boundary.")
    parser.add_argument("--theme", metavar="THEME_ID"); parser.add_argument("--all-themes", "--all-active-themes", dest="all_active_themes", action="store_true"); parser.add_argument("--symbols")
    parser.add_argument("--limit", type=int); parser.add_argument("--resume", action="store_true"); parser.add_argument("--lookback-calendar-days", type=int, default=450)
    parser.add_argument("--concurrency", type=int, default=2); parser.add_argument("--checkpoint", type=Path, default=Path("/tmp/theme-history-checkpoint.json")); parser.add_argument("--json-output", type=Path); parser.add_argument("--strict-live", action="store_true")
    args = parser.parse_args()
    if not any((args.theme, args.all_active_themes, args.symbols)): parser.error("select --theme, --all-themes, or explicit --symbols")
    if args.theme:
        try: args.theme = normalize_theme_id(args.theme)
        except ValueError as error: parser.error(str(error))
    active = ThemeDefinitionService().active(); active_by_id = {definition.theme_id: members for definition, members in active}
    if args.symbols:
        symbols = sorted({value.strip().upper() for value in args.symbols.split(",") if value.strip()})
    else:
        selected = active if args.all_active_themes else [(definition, members) for definition, members in active if definition.theme_id == args.theme]
        if not selected: parser.error("requested Theme has no reviewed active definition")
        symbols = sorted({member.ticker for _, members in selected for member in members})
    if args.limit: symbols = symbols[:max(0, args.limit)]
    args.checkpoint.parent.mkdir(parents=True, exist_ok=True)
    prior = json.loads(args.checkpoint.read_text()) if args.resume and args.checkpoint.exists() else {}; completed = set(prior.get("completed", [])); pending = [symbol for symbol in symbols if symbol not in completed]
    updater = BreadthUniverseHistoryUpdater(); master = get_security_master_service(); failures: list[dict[str, object]] = []; results: list[dict[str, object]] = []; started = time.perf_counter()
    def update(symbol: str) -> dict[str, object]:
        security = master.storage.security(symbol)
        if not security or not security.history_provider_symbol: raise RuntimeError("reviewed_theme_security_master_mapping_required")
        symbol_history = master.storage.provider_symbols(symbol, provider="polygon", purpose="history")
        if len(symbol_history) > 1:
            return updater.update_symbol_history_segments(symbol, security_id=security.security_id, segments=symbol_history, lookback_calendar_days=args.lookback_calendar_days, strict_live=args.strict_live)
        return updater.update_symbol(symbol, provider_symbol=security.history_provider_symbol, canonical_security_id=security.security_id, lookback_calendar_days=args.lookback_calendar_days, strict_live=args.strict_live)
    with ThreadPoolExecutor(max_workers=max(1, min(args.concurrency, 4))) as pool:
        futures = {pool.submit(update, symbol): symbol for symbol in pending}
        for future in as_completed(futures):
            symbol = futures[future]
            try: results.append(future.result()); completed.add(symbol)
            except Exception as exc: failures.append({"symbol": symbol, "error": str(exc), "category": getattr(exc, "category", type(exc).__name__), "request_id": getattr(exc, "request_id", None), "retry_after": getattr(exc, "retry_after", None)})
            args.checkpoint.write_text(json.dumps({"completed": sorted(completed)}, indent=2))
    report = {"symbols": symbols, "seeded": len(results), "already_completed": len(symbols) - len(pending), "failed": failures, "inserted_bars": sum(int(row.get("inserted_bars", 0)) for row in results), "updated_bars": sum(int(row.get("updated_bars", 0)) for row in results), "strict_live": args.strict_live, "elapsed_seconds": round(time.perf_counter() - started, 3), "checkpoint": str(args.checkpoint)}
    rendered = json.dumps(report, indent=2, sort_keys=True); print(rendered)
    if args.json_output: args.json_output.write_text(rendered + "\n")
    return 1 if failures else 0


if __name__ == "__main__": raise SystemExit(main())
