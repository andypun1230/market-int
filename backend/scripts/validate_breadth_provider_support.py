#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.providers.symbols import normalize_market_symbol  # noqa: E402
from app.securities.service import SecurityMasterService  # noqa: E402
from app.services.market_data_repository import MarketDataRepository  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify active breadth-universe provider mappings before a full history seed")
    parser.add_argument("--universe", default="sp100")
    parser.add_argument("--remote", action="store_true", help="Fetch a five-session daily-history probe for every member.")
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--json-output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    master = SecurityMasterService()
    universe = master.storage.get_active_universe(args.universe)
    if not universe:
        raise SystemExit(f"No active universe named {args.universe}; import it explicitly first.")
    repository = MarketDataRepository()
    provider = repository.get_provider_for("daily_history")
    health = provider.get_provider_health().model_dump()
    members = master.storage.members(universe.universe_id)
    results = [mapping_result(master, member.ticker) for member in members]
    mapping_failures = [item for item in results if item["status"] != "mapped"]
    if args.remote and not mapping_failures:
        rate_limited = False
        with ThreadPoolExecutor(max_workers=max(1, min(args.concurrency, 8))) as pool:
            for offset in range(0, len(results), max(1, min(args.concurrency, 8))):
                batch = results[offset:offset + max(1, min(args.concurrency, 8))]
                futures = {pool.submit(probe, provider, item["provider_symbol"]): item for item in batch}
                for future in as_completed(futures):
                    item = futures[future]
                    item.update(future.result())
                    rate_limited = rate_limited or item.get("error_category") == "rate_limited"
                if rate_limited:
                    for remaining in results[offset + len(batch):]:
                        remaining.update({"status": "unsupported", "error_category": "not_probed_rate_limited"})
                    break
    failures = [item for item in results if item["status"] not in {"mapped", "live"}]
    report = {"universe": universe.universe_id, "remote_probe": args.remote, "provider_health": health, "member_count": len(results), "supported": len(results) - len(failures), "unsupported": failures, "results": results}
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered + "\n")
    return 1 if failures else 0


def mapping_result(master: SecurityMasterService, ticker: str) -> dict[str, object]:
    security = master.storage.security(ticker)
    provider_symbol = security.history_provider_symbol if security else None
    if not security or not provider_symbol:
        return {"ticker": ticker, "status": "unsupported", "error_category": "missing_history_mapping"}
    if normalize_market_symbol(provider_symbol) != provider_symbol:
        return {"ticker": ticker, "provider_symbol": provider_symbol, "status": "unsupported", "error_category": "noncanonical_provider_symbol"}
    return {"ticker": ticker, "provider_symbol": provider_symbol, "status": "mapped"}


def probe(provider, provider_symbol: str) -> dict[str, object]:
    try:
        # Probe the provider directly to avoid a previously cached response masking
        # an unavailable or unsupported live symbol.
        history = provider.get_history(provider_symbol, resolution="D", days=5)
        if history.source_state != "live" or not history.candles:
            return {"status": "unsupported", "error_category": "non_live_or_empty_history", "source_state": history.source_state}
        return {"status": "live", "received_bars": len(history.candles), "source_state": history.source_state}
    except Exception as exc:
        return {"status": "unsupported", "error_category": type(exc).__name__, "error": str(exc)}


if __name__ == "__main__":
    raise SystemExit(main())
