from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

from app.market_history.storage import DailyBarStorage
from app.theme_snapshots.models import ThemeSnapshot
from app.theme_snapshots.storage import ThemeSnapshotStorage
from app.themes.basket import build_equal_weight_basket
from app.themes.engine import build_alerts, build_overlap_matrix, build_theme_row
from app.themes.policy import THEME_BASKET_FORMULA_VERSION, THEME_SCORING_FORMULA_VERSION, ThemePolicy, coverage_status
from app.themes.service import ThemeDefinitionService
from app.themes.storage import ThemeStorage


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if load_dotenv is not None:
    # CLI snapshot builds and the API must resolve the same durable namespace.
    load_dotenv(dotenv_path=BACKEND_ROOT / ".env")


def theme_namespace() -> str:
    mode = (os.getenv("DATA_PROVIDER") or os.getenv("MARKET_DATA_PROVIDER") or "test").lower()
    history = (os.getenv("HISTORY_DATA_PROVIDER") or os.getenv("HISTORY_PROVIDER") or "polygon").lower()
    return f"{mode}:{history}:themes"


def source_state() -> str:
    return "test" if (os.getenv("DATA_PROVIDER") or "").lower() in {"test", "generated_test_data"} else "live"


class ThemeSnapshotBuilder:
    def __init__(self, theme_storage: ThemeStorage | None = None, snapshot_storage: ThemeSnapshotStorage | None = None, bars: DailyBarStorage | None = None) -> None:
        self.theme_storage = theme_storage or ThemeStorage()
        self.definition_service = ThemeDefinitionService(self.theme_storage)
        self.snapshot_storage = snapshot_storage or ThemeSnapshotStorage()
        self.bars = bars or DailyBarStorage()

    def build(self, *, publish: bool = True) -> ThemeSnapshot | None:
        namespace = theme_namespace(); now = datetime.now(timezone.utc).isoformat(); active = self.definition_service.active()
        if not active:
            self.snapshot_storage.set_error(namespace, "no_reviewed_active_theme_definitions", now)
            return self.snapshot_storage.latest(namespace)
        benchmark = tuple(self.bars.history("SPY"))
        if not benchmark:
            self.snapshot_storage.set_error(namespace, "no_durable_spy_history", now)
            return self.snapshot_storage.latest(namespace)
        state = source_state(); rows: list[dict] = []
        for definition, members in active:
            histories = {member.ticker.upper(): tuple(self.bars.history(member.ticker)) for member in members}
            generated = build_equal_weight_basket(definition, members, histories, source_state=state)
            self.theme_storage.upsert_basket_bars(generated)
            basket = self.theme_storage.basket_history(definition.theme_id, definition.version, formula_version=THEME_BASKET_FORMULA_VERSION)
            if not basket: continue
            rows.append(build_theme_row(definition, members, histories, basket, benchmark, source_state=state))
        publishable = [row for row in rows if row["coverage_status"] != "unavailable" and row["member_count"] >= ThemePolicy().minimum_live_members]
        if not publishable:
            self.snapshot_storage.set_error(namespace, "theme_coverage_below_publish_threshold", now)
            return self.snapshot_storage.latest(namespace)
        ordered = sorted(publishable, key=lambda row: (row["composite_score"] is None, -(row["composite_score"] or 0), row["theme_id"]))
        active_theme_count = len(ordered)
        for rank, row in enumerate(ordered, 1):
            row["rank"] = rank
            row["pilot_scope"] = {
                "active_reviewed_theme_count": active_theme_count,
                "rank_scope": f"Rank reflects the leadership composite among the {active_theme_count} currently active reviewed pilot themes.",
                "inactive_proposed_themes_excluded": True,
            }
            row["score_semantics"]["relative_rank"] = rank
            row["score_semantics"]["relative_rank_scope"] = f"{active_theme_count} active reviewed pilot themes"
        market_date = max((row.get("rotation_series", {}).get("1M", {}).get("latest_market_date") for row in ordered), default="")
        previous = self.snapshot_storage.latest(namespace)
        alerts = build_alerts(ordered, previous.model_dump() if previous else None, market_date)
        overlap = build_overlap_matrix(ordered)
        member_coverage = {row["theme_id"]: {"coverage_ratio": row["coverage_ratio"], "eligible_count": row["eligible_count"], "member_count": row["member_count"]} for row in ordered}
        # Include the published payload contract so a schema/presentation field
        # added to an immutable snapshot cannot reuse an older snapshot ID.
        input_hash = hashlib.sha256(json.dumps({"themes": [(row["theme_id"], row["version"], row["input_hash"]) for row in ordered], "market_date": market_date, "formula": THEME_SCORING_FORMULA_VERSION, "payload_contract": "theme-snapshot-v2.1"}, sort_keys=True).encode()).hexdigest()
        snapshot = ThemeSnapshot(snapshot_id=f"theme-{market_date}-{hashlib.sha256(input_hash.encode()).hexdigest()[:10]}", schema_version=2, market_date=market_date, generated_at=now, published_at=now, status="complete" if all(row["coverage_status"] == "complete" for row in ordered) else "partial", source_state=state, active_theme_versions=tuple({"theme_id": row["theme_id"], "version": row["version"]} for row in ordered), member_coverage=member_coverage, providers=("polygon",), rows=tuple(ordered), rankings=tuple(row["theme_id"] for row in ordered), rotation_summary=f"{ordered[0]['display_name']} leads the reviewed live ThemeSnapshot." if ordered else "No themes qualify.", overlap_matrix=tuple(overlap), alerts=tuple(alerts), warnings=("Historical results use the current reviewed constituent basket unless historical membership versions are available.", f"Rank reflects the leadership composite among the {active_theme_count} currently active reviewed pilot themes."), input_hash=input_hash, formula_version=THEME_SCORING_FORMULA_VERSION, configuration_signature=hashlib.sha256(json.dumps([(row["theme_id"], row["version"]) for row in ordered]).encode()).hexdigest()[:20])
        if publish: self.snapshot_storage.publish(snapshot, namespace)
        return snapshot
