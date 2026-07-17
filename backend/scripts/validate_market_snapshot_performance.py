#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from main import app  # noqa: E402
from app.snapshots.models import InputCoverage, MarketSnapshot, SnapshotSection, now_iso  # noqa: E402
from app.snapshots.readers import fallback_decision, fallback_fear_greed, fallback_health, fallback_regime, fallback_risk  # noqa: E402
from app.snapshots.service import get_market_snapshot_service, reset_market_snapshot_service  # noqa: E402


READ_PATHS = [
    "/market/snapshot/latest",
    "/home/dashboard",
    "/market/core-snapshot",
    "/market/regime",
    "/market/health",
    "/market/risk",
    "/market/fear-greed",
    "/market/decision-dashboard",
    "/market/details/decision",
    "/market/details/structure",
]


def main() -> int:
    args = parse_args()
    if args.test:
        os.environ["DATA_PROVIDER"] = "test"
        os.environ["MARKET_DATA_PROVIDER"] = "test"
        os.environ["BREADTH_MAX_SYMBOLS"] = os.getenv("BREADTH_MAX_SYMBOLS", "6")
        os.environ["MAX_SYMBOL_REFRESH_PER_CYCLE"] = os.getenv("MAX_SYMBOL_REFRESH_PER_CYCLE", "6")
    if args.live:
        os.environ["DATA_PROVIDER"] = "live"
        os.environ["QUOTE_DATA_PROVIDER"] = os.getenv("QUOTE_DATA_PROVIDER", "finnhub")
        os.environ["HISTORY_DATA_PROVIDER"] = os.getenv("HISTORY_DATA_PROVIDER", "polygon")
        os.environ["MARKET_DATA_ALLOW_MOCK_FALLBACK"] = os.getenv("MARKET_DATA_ALLOW_MOCK_FALLBACK", "false")
    os.environ.setdefault("MARKET_SNAPSHOT_STARTUP_REFRESH", "false")
    os.environ.setdefault("BACKGROUND_REFRESH_ENABLED", "false")
    if not os.getenv("MARKET_SNAPSHOT_DB_PATH"):
        tmp = tempfile.TemporaryDirectory()
        os.environ["MARKET_SNAPSHOT_DB_PATH"] = str(Path(tmp.name) / "snapshot-validation.sqlite3")
    reset_market_snapshot_service()
    service = get_market_snapshot_service()

    report: dict[str, Any] = {"mode": selected_mode(args), "failures": []}
    if args.cold:
        started = time.perf_counter()
        snapshot = service.build_now()
        report["build"] = {
            "snapshot_id": snapshot.snapshot_id if snapshot else None,
            "status": snapshot.status if snapshot else "unavailable",
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "section_statuses": {
                key: section.status
                for key, section in (snapshot.sections if snapshot else {}).items()
            },
        }
    else:
        snapshot = publish_synthetic_snapshot(service)
        report["build"] = {
            "snapshot_id": snapshot.snapshot_id,
            "status": snapshot.status,
            "duration_ms": 0,
            "section_statuses": {key: section.status for key, section in snapshot.sections.items()},
            "synthetic": True,
        }
    if args.restart:
        snapshot = service.build_now()
        before = snapshot.snapshot_id if snapshot else None
        reset_market_snapshot_service()
        after_snapshot = get_market_snapshot_service().get_latest_snapshot()
        report["restart"] = {
            "before_snapshot_id": before,
            "after_snapshot_id": after_snapshot.snapshot_id if after_snapshot else None,
            "same_snapshot_id": before == (after_snapshot.snapshot_id if after_snapshot else None),
        }

    report["read_latency"] = validate_reads()
    if any(row["status_code"] >= 500 or row["elapsed_ms"] > target_ms(row["path"]) for row in report["read_latency"]):
        report["failures"].append("read_latency_or_status")
    report["status"] = service.get_status()
    write_report(report, args.json_output)
    return 1 if report["failures"] else 0


def validate_reads() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with patch("app.services.market_data_repository.MarketDataRepository._fetch_history", side_effect=AssertionError("provider history called during snapshot read")):
        with patch("app.services.market_data_repository.MarketDataRepository._fetch_quote", side_effect=AssertionError("provider quote called during snapshot read")):
            with TestClient(app) as client:
                snapshot_id: str | None = None
                for path in READ_PATHS:
                    started = time.perf_counter()
                    response = client.get(path)
                    elapsed_ms = int((time.perf_counter() - started) * 1000)
                    payload = response.json() if "application/json" in response.headers.get("content-type", "") else {}
                    if path == "/market/snapshot/latest":
                        snapshot_id = payload.get("snapshot_id")
                    rows.append(
                        {
                            "path": path,
                            "status_code": response.status_code,
                            "elapsed_ms": elapsed_ms,
                            "snapshot_id": payload.get("snapshot_id") or snapshot_id,
                            "target_ms": target_ms(path),
                        }
                    )
    return rows


def publish_synthetic_snapshot(service) -> MarketSnapshot:
    decision = fallback_decision()
    core = {
        "indexes": [],
        "market_health": fallback_health().model_dump(),
        "decision_summary": {
            "playbook": decision.playbook.model_dump(),
            "aggressiveness": decision.aggressiveness.model_dump(),
            "preferred_style": decision.trading_styles.preferred_style,
            "main_risk": decision.playbook.main_risk,
        },
        "breadth_summary": None,
        "top_sector": None,
        "top_industry_group": None,
        "as_of": now_iso(),
        "overall_mode": "test",
        "bootstrap": False,
        "refreshing": False,
        "cache_status": "snapshot",
        "is_stale": False,
    }
    sections = {
        "regime": synthetic_section(fallback_regime().model_dump()),
        "health": synthetic_section(fallback_health().model_dump()),
        "risk": synthetic_section(fallback_risk().model_dump()),
        "fear_greed": synthetic_section(fallback_fear_greed().model_dump()),
        "decision": synthetic_section(decision.model_dump()),
        "risk_dashboard": synthetic_section(decision.risk_dashboard.model_dump()),
        "leadership": synthetic_section(decision.leadership.model_dump()),
        "breadth": synthetic_section(None, status="partial"),
        "indexes": synthetic_section([]),
        "core": synthetic_section(core),
        "home": synthetic_section({
            "core": core,
            "risk_summary": {"score": 50, "status": "Moderate", "top_contributors": [], "summary": "Synthetic snapshot."},
            "watchlist_summary": {"items": []},
            "bootstrap": False,
            "refreshing": False,
            "cache_status": "snapshot",
            "is_stale": False,
        }),
    }
    snapshot = MarketSnapshot(
        snapshot_id=f"market-validation-{int(time.time())}",
        status="partial",
        created_at=now_iso(),
        published_at=now_iso(),
        expires_at=now_iso(),
        stale_until=now_iso(),
        build_started_at=now_iso(),
        build_completed_at=now_iso(),
        build_duration_ms=0,
        input_coverage=InputCoverage(required_requested=4, required_available=2, optional_requested=0, optional_available=0, coverage_ratio=0.5),
        source_summary={"source_state": "test", "input_hash": "synthetic"},
        sections=sections,
    )
    service.storage.publish_snapshot(snapshot)
    return snapshot


def synthetic_section(payload, status: str = "complete") -> SnapshotSection:
    return SnapshotSection(
        status=status,
        calculated_at=now_iso(),
        source_state="test",
        coverage_ratio=1.0 if status == "complete" else 0.5,
        dependencies_requested=1,
        dependencies_available=1 if status == "complete" else 0,
        payload=payload,
    )


def target_ms(path: str) -> int:
    return 300 if path == "/market/snapshot/latest" else 800 if path.startswith("/market/details") else 500


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate market snapshot build/read performance.")
    parser.add_argument("--test", action="store_true", help="Use deterministic test providers.")
    parser.add_argument("--live", action="store_true", help="Use live provider configuration from env/defaults.")
    parser.add_argument("--cold", action="store_true", help="Run a cold build before read checks.")
    parser.add_argument("--warm", action="store_true", help="Run warm read checks after a build.")
    parser.add_argument("--restart", action="store_true", help="Verify persisted latest snapshot survives service recreation.")
    parser.add_argument("--soak", action="store_true", help="Reserved for repeated read checks.")
    parser.add_argument("--json-output", type=Path)
    return parser.parse_args()


def selected_mode(args: argparse.Namespace) -> str:
    if args.live:
        provider = "live"
    else:
        provider = "test"
    modes = [name for name in ["cold", "warm", "restart", "soak"] if getattr(args, name)]
    return f"{provider}:{','.join(modes or ['warm'])}"


def write_report(report: dict[str, Any], output: Path | None) -> None:
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
