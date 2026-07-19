#!/usr/bin/env python3
"""Resumably seed SPY and the eleven canonical sector ETF histories."""
from __future__ import annotations
import argparse, json, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path: sys.path.insert(0, str(BACKEND_ROOT))
from app.market_history.updater import BreadthUniverseHistoryUpdater
from app.securities.registry import SECTOR_BY_ID

parser = argparse.ArgumentParser(description="Seed durable sector ETF and SPY Polygon history")
parser.add_argument("--lookback-calendar-days", type=int, default=450); parser.add_argument("--resume", action="store_true"); parser.add_argument("--concurrency", type=int, default=2); parser.add_argument("--max-retries", type=int, default=2); parser.add_argument("--strict-live", action="store_true"); parser.add_argument("--checkpoint", type=Path, default=Path("/tmp/sector-reference-history-checkpoint.json")); parser.add_argument("--json-output", type=Path)
args = parser.parse_args(); symbols = ["SPY", *[item["etf_symbol"] for item in SECTOR_BY_ID.values()]]
completed = set(json.loads(args.checkpoint.read_text()).get("completed", [])) if args.resume and args.checkpoint.exists() else set(); pending = [symbol for symbol in symbols if symbol not in completed]
updater = BreadthUniverseHistoryUpdater(); updater.repository.get_provider_for("daily_history")
results=[]; failures=[]; started=time.perf_counter()
def update(symbol: str):
    for attempt in range(args.max_retries + 1):
        try: return {**updater.update_symbol(symbol, provider_symbol=symbol, lookback_calendar_days=args.lookback_calendar_days, strict_live=args.strict_live), "retry_count": attempt}
        except Exception as exc:
            if attempt >= args.max_retries: raise
            time.sleep(min(2 ** attempt, 4))
with ThreadPoolExecutor(max_workers=max(1, min(args.concurrency, 4))) as pool:
    futures={pool.submit(update, symbol): symbol for symbol in pending}
    for future in as_completed(futures):
        symbol=futures[future]
        try: results.append(future.result()); completed.add(symbol)
        except Exception as exc: failures.append({"symbol": symbol, "error": str(exc), "category": getattr(exc, "category", type(exc).__name__), "request_number": getattr(exc, "request_number", None), "request_id": getattr(exc, "request_id", None), "retry_after": getattr(exc, "retry_after", None)})
        args.checkpoint.write_text(json.dumps({"completed": sorted(completed)}, indent=2))
provider=updater.repository.get_provider_for("daily_history")
report={"symbols": symbols, "completed": len(results), "already_completed": len(symbols)-len(pending), "failed": failures, "inserted_bars":sum(row["inserted_bars"] for row in results), "updated_bars":sum(row["updated_bars"] for row in results), "provider_requests":getattr(provider,"request_count",None), "retries":sum(row["retry_count"] for row in results), "rate_limit_events":getattr(provider,"rate_limit_events",None), "strict_live":args.strict_live, "elapsed_seconds":round(time.perf_counter()-started,3)}
rendered=json.dumps(report, indent=2, sort_keys=True); print(rendered)
if args.json_output: args.json_output.write_text(rendered+"\n")
raise SystemExit(1 if failures else 0)
