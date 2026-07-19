from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from app.breadth.engine import calculate_breadth
from app.breadth.models import BreadthCalculationInput, BreadthSnapshot
from app.breadth.policy import BreadthPolicy
from app.breadth.storage import BreadthSnapshotStorage
from app.market_history.storage import DailyBarStorage
from app.securities.service import SecurityMasterService
from app.semantics import SEMANTICS_VERSION, confidence_with_snapshot_provenance


class BreadthSnapshotBuilder:
    def __init__(self, security_master: SecurityMasterService | None = None, bars: DailyBarStorage | None = None, storage: BreadthSnapshotStorage | None = None) -> None:
        self.security_master = security_master or SecurityMasterService()
        self.bars = bars or DailyBarStorage()
        self.storage = storage or BreadthSnapshotStorage()

    def build_and_publish(self, universe_name: str = "sp100") -> BreadthSnapshot | None:
        universe = self.security_master.storage.get_active_universe(universe_name)
        if universe is None: return None
        members = tuple(self.security_master.storage.members(universe.universe_id))
        histories = {member.ticker: tuple(self.bars.history(member.ticker)) for member in members}
        market_date = max((bars[-1].session_date for bars in histories.values() if bars), default="")
        if not market_date:
            now = datetime.now(timezone.utc).isoformat()
            self.storage.set_state(breadth_namespace(), "last_error", "no_durable_constituent_history", now)
            return self.storage.last_known_good(universe.universe_id, breadth_namespace())
        benchmark = tuple(self.bars.history(universe.benchmark_symbol, end_date=market_date))
        result = calculate_breadth(BreadthCalculationInput(universe=universe, members=members, market_date=market_date, histories=histories, benchmark_history=benchmark, source_metadata={"provider": "polygon"}), BreadthPolicy.from_environment())
        now = datetime.now(timezone.utc).isoformat()
        snapshot_id = f"breadth-{universe.universe_id}-{market_date}-{hashlib.sha256(f'{result.input_hash}:{SEMANTICS_VERSION}'.encode()).hexdigest()[:10]}"
        timestamps = [bar.timestamp for bars in histories.values() for bar in bars]
        data_confidence = confidence_with_snapshot_provenance(
            result.core["data_confidence"], source_snapshot_id=snapshot_id, calculated_at=now
        )
        signal_confidence = confidence_with_snapshot_provenance(
            result.core["signal_confidence"], source_snapshot_id=snapshot_id, calculated_at=now
        )
        core = {**result.core, "data_confidence": data_confidence, "signal_confidence": signal_confidence}
        snapshot = BreadthSnapshot(snapshot_id=snapshot_id, universe_id=universe.universe_id, universe_version=universe.version, market_date=market_date, created_at=now, published_at=now, status=result.coverage["coverage_status"], score=result.score, classification=result.classification, trend=result.trend, confidence=result.confidence, coverage=result.coverage, advance_decline={key: core[key] for key in ("advancing_count", "declining_count", "unchanged_count", "net_advances", "advance_decline_ratio", "advance_decline_ratio_display", "advance_decline_ratio_smoothed", "ratio_method", "percent_advancing", "percent_declining")}, moving_average_breadth={key: core[key] for key in ("percent_above_20ema", "percent_above_50ema", "percent_above_200ema")}, highs_lows={key: core[key] for key in ("new_52_week_highs", "new_52_week_lows", "highs_minus_lows", "high_low_ratio")}, sector_breadth=result.sectors, divergences=detect_divergence(benchmark, self.storage.history(universe.universe_id, "breadth_score", 30)), source_state=source_state(), providers=["polygon"], latest_input_timestamp=max(timestamps) if timestamps else None, oldest_input_timestamp=min(timestamps) if timestamps else None, timestamp_skew=None, warnings=result.warnings, missing_dependencies=result.coverage["members_missing"], calculation_version=BreadthPolicy.from_environment().calculation_version, input_hash=result.input_hash, sections={"core": section(result.coverage, core), "sectors": section(result.coverage, result.sectors), "divergence": section(result.coverage, [])}, semantics_version=SEMANTICS_VERSION, data_confidence=data_confidence, signal_confidence=signal_confidence)
        namespace = breadth_namespace()
        if snapshot.status == "unavailable":
            self.storage.set_state(namespace, "last_error", "minimum_breadth_coverage_not_met", now)
            return self.storage.last_known_good(universe.universe_id, namespace)
        self.storage.publish(snapshot, namespace=namespace)
        return snapshot


def section(coverage: dict, payload: object) -> dict[str, object]:
    return {"status": coverage["coverage_status"], "coverage": coverage["coverage_ratio"], "calculated_at": datetime.now(timezone.utc).isoformat(), "payload": payload, "warnings": coverage["coverage_warnings"]}


def detect_divergence(benchmark: tuple, history: list[dict]) -> list[dict]:
    # Conservative: no signal until sufficient persisted breadth history exists.
    if len(benchmark) < 10 or len(history) < 10: return []
    prices = [bar.close for bar in benchmark[-10:]]; scores = [row["value"] for row in history[-10:] if isinstance(row.get("value"), (int, float))]
    if len(scores) < 10: return []
    price_change = (prices[-1] / prices[0] - 1) * 100; score_change = scores[-1] - scores[0]
    if price_change >= 3 and score_change <= -8: return [{"type": "bearish", "active": True, "detected_at": benchmark[-1].session_date, "lookback": 10, "benchmark_change": round(price_change, 2), "breadth_change": round(score_change, 2), "confidence": "moderate", "explanation": "Benchmark advanced while breadth weakened over ten completed sessions.", "invalidation_condition": "Breadth score recovers above its ten-session starting level."}]
    if price_change <= -3 and score_change >= 8: return [{"type": "bullish", "active": True, "detected_at": benchmark[-1].session_date, "lookback": 10, "benchmark_change": round(price_change, 2), "breadth_change": round(score_change, 2), "confidence": "moderate", "explanation": "Benchmark declined while breadth improved over ten completed sessions.", "invalidation_condition": "Breadth score falls below its ten-session starting level."}]
    return []


def breadth_namespace() -> str:
    import os
    mode = (os.getenv("DATA_PROVIDER") or os.getenv("MARKET_DATA_PROVIDER") or "test").lower()
    history = (os.getenv("HISTORY_DATA_PROVIDER") or os.getenv("HISTORY_PROVIDER") or "polygon").lower()
    return f"{mode}:{history}:{os.getenv('BREADTH_UNIVERSE', 'sp100').lower()}"


def source_state() -> str:
    import os
    return "test" if (os.getenv("DATA_PROVIDER") or "").lower() in {"test", "generated_test_data"} else "live"
