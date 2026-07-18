#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path: sys.path.insert(0, str(BACKEND_ROOT))

from app.market_history.updater import BreadthUniverseHistoryUpdater  # noqa: E402
from app.providers.finnhub_provider import ProviderRequestError  # noqa: E402
from app.securities.service import SecurityMasterService  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resumable durable S&P 100 daily-history seed")
    parser.add_argument("--universe", default="sp100"); parser.add_argument("--lookback-calendar-days", type=int, default=450)
    parser.add_argument("--resume", action="store_true"); parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--json-output", type=Path); parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--symbols", help="Comma-separated reviewed universe tickers for a staged seed.")
    parser.add_argument("--limit", type=int, help="Seed the first N tickers in canonical ticker order.")
    parser.add_argument("--max-retries", type=int, default=2, help="Bounded retries for rate-limit and transient provider failures.")
    parser.add_argument("--strict-live", action="store_true", help="Bypass repository caches and require direct Polygon live history.")
    return parser.parse_args()


def select_members(members: list, symbols: str | None, limit: int | None) -> list:
    requested = {item.strip().upper() for item in (symbols or "").split(",") if item.strip()}
    known = {member.ticker for member in members}
    unknown = sorted(requested - known)
    if unknown:
        raise ValueError(f"Requested tickers are not active universe members: {','.join(unknown)}")
    selected = [member for member in members if not requested or member.ticker in requested]
    if limit is not None:
        if limit < 1:
            raise ValueError("--limit must be at least 1")
        selected = selected[:limit]
    return selected


def update_with_retries(updater: BreadthUniverseHistoryUpdater, ticker: str, provider_symbol: str, lookback_calendar_days: int, max_retries: int, strict_live: bool) -> dict:
    for attempt in range(max(0, max_retries) + 1):
        try:
            result = updater.update_symbol(ticker, provider_symbol=provider_symbol, lookback_calendar_days=lookback_calendar_days, strict_live=strict_live)
            return {**result, "retry_count": attempt}
        except ProviderRequestError as exc:
            retryable = exc.category in {"rate_limited", "transient", "network", "unavailable"}
            if not retryable or attempt >= max_retries:
                raise
            time.sleep(min(2 ** attempt, 4))


def main() -> int:
    started = time.perf_counter(); args = parse_args(); master = SecurityMasterService(); universe = master.storage.get_active_universe(args.universe)
    if not universe: raise SystemExit(f"No active universe named {args.universe}; import it explicitly first.")
    checkpoint = args.checkpoint or Path(f"/tmp/{universe.universe_id}-seed-checkpoint.json")
    completed = set(json.loads(checkpoint.read_text()).get("completed", [])) if args.resume and checkpoint.exists() else set()
    selected = select_members(master.storage.members(universe.universe_id), args.symbols, args.limit)
    members = [member for member in selected if member.ticker not in completed]
    updater = BreadthUniverseHistoryUpdater(); results = []; failures = []
    if args.strict_live:
        # Construct one shared provider before worker threads start so request
        # counters and rate-limit diagnostics cover every staged symbol.
        updater.repository.get_provider_for("daily_history")
    with ThreadPoolExecutor(max_workers=max(1, min(args.concurrency, 8))) as pool:
        futures = {
            pool.submit(update_with_retries, updater, member.ticker, master.storage.security(member.ticker).history_provider_symbol or member.ticker, args.lookback_calendar_days, args.max_retries, args.strict_live): member.ticker
            for member in members
        }
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                row = future.result(); results.append(row); completed.add(ticker)
            except Exception as exc:
                failures.append({"ticker": ticker, "status": "failed", "error_category": getattr(exc, "category", type(exc).__name__), "error": str(exc), "retry_count": args.max_retries, "request_number": getattr(exc, "request_number", None), "request_id": getattr(exc, "request_id", None), "retry_after": getattr(exc, "retry_after", None)})
            checkpoint.write_text(json.dumps({"completed": sorted(completed)}, indent=2))
    provider = updater.repository.get_provider_for("daily_history")
    report = {"universe": universe.universe_id, "selected_symbols": [member.ticker for member in selected], "requested": len(members), "already_completed": len(selected) - len(members), "completed": len(results), "failed": len(failures), "inserted_bars": sum(row["inserted_bars"] for row in results), "updated_bars": sum(row["updated_bars"] for row in results), "provider_requests": getattr(provider, "request_count", None), "retries": sum(row["retry_count"] for row in results) + sum(row["retry_count"] for row in failures), "rate_limit_events": getattr(provider, "rate_limit_events", None), "elapsed_seconds": round(time.perf_counter() - started, 3), "strict_live": args.strict_live, "results": sorted(results, key=lambda item: item["ticker"]), "failures": failures, "checkpoint": str(checkpoint)}
    rendered = json.dumps(report, indent=2, sort_keys=True); print(rendered)
    if args.json_output: args.json_output.parent.mkdir(parents=True, exist_ok=True); args.json_output.write_text(rendered + "\n")
    return 1 if failures else 0


if __name__ == "__main__": raise SystemExit(main())
