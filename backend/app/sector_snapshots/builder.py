from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone

from app.market_history.storage import DailyBarStorage
from app.rotation.engine import build_rotation_series
from app.rotation.policy import INTERVAL_POLICIES, ROTATION_FORMULA_VERSION, ROTATION_NORMALIZATION_VERSION
from app.securities.registry import SECTOR_BY_ID
from app.securities.service import SecurityMasterService
from app.sector_snapshots.engine import build_sector_rows
from app.sector_snapshots.models import SectorSnapshot
from app.sector_snapshots.policy import SectorPolicy
from app.sector_snapshots.storage import SectorSnapshotStorage
from app.semantics import SEMANTICS_VERSION


def sector_namespace() -> str:
    # Match the provider bootstrap path so snapshot readers do not depend on
    # whether another endpoint happened to import the provider first.
    import app.providers.selector  # noqa: F401
    mode = (os.getenv("DATA_PROVIDER") or os.getenv("MARKET_DATA_PROVIDER") or "test").lower()
    history = (os.getenv("HISTORY_DATA_PROVIDER") or os.getenv("HISTORY_PROVIDER") or "polygon").lower()
    return f"{mode}:{history}:{os.getenv('BREADTH_UNIVERSE', 'sp100').lower()}"


class SectorSnapshotBuilder:
    def __init__(self, security_master: SecurityMasterService | None = None, bars: DailyBarStorage | None = None, storage: SectorSnapshotStorage | None = None) -> None:
        self.security_master = security_master or SecurityMasterService()
        self.bars = bars or DailyBarStorage()
        self.storage = storage or SectorSnapshotStorage()

    def build(self, universe_name: str = "sp100", *, publish: bool = True) -> SectorSnapshot | None:
        universe = self.security_master.storage.get_active_universe(universe_name)
        if universe is None:
            return None
        members = tuple(self.security_master.storage.members(universe.universe_id))
        histories = {member.ticker: tuple(self.bars.history(member.ticker)) for member in members}
        market_date = max((bars[-1].session_date for bars in histories.values() if bars), default="")
        now = datetime.now(timezone.utc).isoformat()
        if not market_date:
            self.storage.set_error(sector_namespace(), "no_durable_constituent_history", now)
            return self.storage.latest(universe.universe_id, sector_namespace())
        etf_histories = {definition["etf_symbol"]: tuple(self.bars.history(definition["etf_symbol"], end_date=market_date)) for definition in SECTOR_BY_ID.values()}
        benchmark = tuple(self.bars.history("SPY", end_date=market_date))
        rows, coverage, input_hash = build_sector_rows(members, histories, etf_histories, benchmark, SectorPolicy())
        no_mock = source_state() == "live"
        complete = coverage["constituent_coverage_ratio"] >= .95 and coverage["etf_coverage_ratio"] == 1 and not coverage["invalid_classifications"] and no_mock
        partial = coverage["constituent_coverage_ratio"] >= .50 and coverage["etf_coverage_ratio"] > 0 and not coverage["invalid_classifications"] and no_mock
        status = "complete" if complete else "partial" if partial else "unavailable"
        warnings = ["Sector breadth is calculated from the reviewed S&P 100 universe; it is not full-market breadth."]
        if len(benchmark) < 200: warnings.append("SPY history is below the EMA200 readiness threshold.")
        if coverage["invalid_classifications"]: warnings.append("Some active members lack a reviewed canonical sector classification.")
        if status != "complete": warnings.append("Coverage does not qualify for a complete sector snapshot.")
        ordered = sorted(rows, key=lambda row: (row["composite_score"] if row["composite_score"] is not None else -1, row["sector_id"]), reverse=True)
        for rank, row in enumerate(ordered, 1):
            row["rank"] = rank
            row["rotation_series"] = {
                interval: build_rotation_series(
                    entity_type="sector",
                    entity_id=row["sector_id"],
                    display_name=row["display_name"],
                    short_label=row["etf_symbol"],
                    entity_symbol=row["etf_symbol"],
                    entity_history=etf_histories[row["etf_symbol"]],
                    benchmark_symbol="SPY",
                    benchmark_history=benchmark,
                    interval=interval,
                    source_state=source_state(),
                    data_mode="live" if source_state() == "live" else "test",
                    universe_id=universe.universe_id,
                    universe_version=universe.version,
                    coverage_ratio=row["coverage_ratio"],
                ).model_dump()
                for interval in INTERVAL_POLICIES
            }
        rankings = tuple(row["sector_id"] for row in ordered)
        alerts = alerts_for(rows, self.storage.history(universe.universe_id, 30))
        input_hash = hashlib.sha256(f"{input_hash}:rotation-series-contract-v1:{ROTATION_FORMULA_VERSION}:{ROTATION_NORMALIZATION_VERSION}:{SEMANTICS_VERSION}".encode()).hexdigest()
        snapshot = SectorSnapshot(snapshot_id=f"sector-{universe.universe_id}-{market_date}-{hashlib.sha256(input_hash.encode()).hexdigest()[:10]}", schema_version=4, universe_id=universe.universe_id, universe_version=universe.version, market_date=market_date, generated_at=now, status=status, coverage=coverage, benchmark="SPY", source_state=source_state(), provider_provenance={"history_provider": "polygon", "history_source_state": source_state(), "request_time_provider_calls": 0, "universe_scope": "S&P 100", "rotation_formula_version": ROTATION_FORMULA_VERSION, "rotation_normalization_version": ROTATION_NORMALIZATION_VERSION}, sectors=tuple(ordered), rankings=rankings, rotation_summary=rotation_summary(ordered), alerts=tuple(alerts), warnings=tuple(warnings), input_hash=input_hash, semantics_version=SEMANTICS_VERSION)
        if publish and status != "unavailable":
            self.storage.publish(snapshot, sector_namespace())
        elif status == "unavailable":
            self.storage.set_error(sector_namespace(), "minimum_sector_coverage_not_met", now)
        return snapshot if status != "unavailable" else self.storage.latest(universe.universe_id, sector_namespace())


def source_state() -> str:
    import app.providers.selector  # noqa: F401
    return "test" if (os.getenv("DATA_PROVIDER") or "").lower() in {"test", "generated_test_data"} else "live"


def rotation_summary(rows: list[dict]) -> str:
    leaders = [row["display_name"] for row in sorted(rows, key=lambda row: row["composite_score"] if row["composite_score"] is not None else -1, reverse=True)[:2]]
    return f"{', '.join(leaders) if leaders else 'No sectors'} lead the reviewed S&P 100 sector snapshot."


def alerts_for(rows: list[dict], history: list[dict]) -> list[dict]:
    if not history:
        return []
    previous = {row["sector_id"]: row for row in history[-1].get("sectors", [])}
    alerts: list[dict] = []
    for row in rows:
        before = previous.get(row["sector_id"], {}).get("classification")
        current = row["classification"]
        if current in {"Leading", "Improving"} and current != before:
            alerts.append({"alert_id": f"{row['sector_id']}:{current}:{row['price_metrics']['return_1m']}", "sector_id": row["sector_id"], "type": f"entered_{current.lower()}", "market_date": history[-1].get("market_date"), "explanation": f"{row['display_name']} entered {current}."})
    return alerts
