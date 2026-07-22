from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

from app.market_history.storage import DailyBarStorage
from app.securities.registry import SECTOR_BY_ID
from app.securities.storage import SecurityMasterStorage
from app.theme_snapshots.models import ThemeSnapshot
from app.theme_snapshots.storage import ThemeSnapshotStorage
from app.rotation.theme_engine import build_theme_rotation_series
from app.rotation.theme_policy import THEME_ROTATION_MODEL_VERSION, THEME_ROTATION_PROFILES
from app.themes.analytics import ThemeAnalyticsEngine
from app.themes.basket import build_equal_weight_basket, build_equal_weight_basket_history
from app.themes.engine import build_alerts, build_overlap_matrix, build_theme_row, to_daily_bar
from app.themes.launch import TAXONOMY_VERSION, ThemeRegistry, get_launch_theme_registry
from app.themes.policy import THEME_BASKET_FORMULA_VERSION, THEME_SCORING_FORMULA_VERSION, THEME_SCORING_WEIGHTS, ThemePolicy, clip_score, representativeness
from app.themes.service import ThemeDefinitionService
from app.themes.storage import ThemeStorage


BACKEND_ROOT = Path(__file__).resolve().parents[2]
LAUNCH_THEME_SCORING_FORMULA_VERSION = "theme-intelligence-composite-v1"
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
    def __init__(
        self,
        theme_storage: ThemeStorage | None = None,
        snapshot_storage: ThemeSnapshotStorage | None = None,
        bars: DailyBarStorage | None = None,
        securities: SecurityMasterStorage | None = None,
        registry: ThemeRegistry | None = None,
        include_launch_registry: bool | None = None,
    ) -> None:
        self.theme_storage = theme_storage or ThemeStorage()
        self.definition_service = ThemeDefinitionService(self.theme_storage)
        self.snapshot_storage = snapshot_storage or ThemeSnapshotStorage()
        self.bars = bars or DailyBarStorage()
        self.securities = securities or SecurityMasterStorage(self.bars.db_path)
        self.registry = registry or get_launch_theme_registry()
        self.analytics = ThemeAnalyticsEngine(self.registry)
        self.include_launch_registry = include_launch_registry

    def build(self, *, publish: bool = True) -> ThemeSnapshot | None:
        namespace = theme_namespace(); now = datetime.now(timezone.utc).isoformat(); active = self.definition_service.active(); state = source_state()
        include_launch = self.include_launch_registry if self.include_launch_registry is not None else state == "live"
        symbols = {"SPY"}
        symbols.update(member.ticker.upper() for _, members in active for member in members)
        if include_launch:
            symbols.update(item.symbol for item in self.registry.mappings)
            symbols.update(symbol for definition in self.registry.launch() for symbol in definition.benchmark_symbols)
            symbols.update(item["etf_symbol"] for item in SECTOR_BY_ID.values())
        histories = {symbol: tuple(values) for symbol, values in self.bars.histories(tuple(symbols)).items()}
        benchmark = histories.get("SPY", ())
        if not active and not include_launch:
            self.snapshot_storage.set_error(namespace, "no_reviewed_active_theme_definitions", now)
            return self.snapshot_storage.latest(namespace)
        if not benchmark:
            self.snapshot_storage.set_error(namespace, "no_durable_spy_history", now)
            return self.snapshot_storage.latest(namespace)
        legacy_rows: list[dict[str, Any]] = []
        for definition, members in active:
            member_histories = {member.ticker.upper(): histories.get(member.ticker.upper(), ()) for member in members}
            generated = build_equal_weight_basket(definition, members, member_histories, source_state=state)
            self.theme_storage.upsert_basket_bars(generated)
            basket = self.theme_storage.basket_history(definition.theme_id, definition.version, formula_version=THEME_BASKET_FORMULA_VERSION)
            if not basket: continue
            legacy_rows.append(build_theme_row(definition, members, member_histories, basket, benchmark, source_state=state))

        launch_rows: list[dict[str, Any]] = []
        coverage_audit: list[dict[str, Any]] = []
        if include_launch:
            launch_rows, coverage_audit = self._build_launch_rows(histories, now, state)
        by_id = {row["theme_id"]: row for row in launch_rows if row.get("status") in {"available", "partial"}}
        # The two original reviewed rows retain their validated calculations;
        # the launch batch only expands the same immutable snapshot contract.
        by_id.update({row["theme_id"]: row for row in legacy_rows})
        publishable = list(by_id.values())
        if not publishable:
            reason = "no_reviewed_active_theme_definitions" if not active and not include_launch else "no_durable_spy_history" if not benchmark else "theme_coverage_below_publish_threshold"
            self.snapshot_storage.set_error(namespace, reason, now)
            return self.snapshot_storage.latest(namespace)

        rankable = [row for row in publishable if self._rankable(row)]
        rankable.sort(key=lambda row: (row.get("composite_score") is None, -(row.get("composite_score") or 0), row["theme_id"]))
        active_theme_count = len(rankable)
        for rank, row in enumerate(rankable, 1):
            row["rank"] = rank
            row["pilot_scope"] = ({
                "active_reviewed_theme_count": active_theme_count, "launch_theme_count": len(self.registry.launch()),
                "rank_scope": f"Rank reflects governed market evidence among {active_theme_count} themes meeting normal coverage, freshness, benchmark, and confidence gates.",
                "partial_and_unavailable_themes_excluded": True,
            } if include_launch else {
                "active_reviewed_theme_count": active_theme_count,
                "rank_scope": f"Rank reflects the leadership composite among the {active_theme_count} currently active reviewed pilot themes.",
                "inactive_proposed_themes_excluded": True,
            })
            row.setdefault("score_semantics", {})["relative_rank"] = rank
            row["score_semantics"]["relative_rank_scope"] = f"{active_theme_count} production-qualified themes" if include_launch else f"{active_theme_count} active reviewed pilot themes"
        partial_rows = sorted((row for row in publishable if row not in rankable), key=lambda row: row["theme_id"])
        for row in partial_rows:
            row["rank"] = None
        ordered = [*rankable, *partial_rows]
        market_date = max((str(row.get("market_date") or row.get("rotation_series", {}).get("1M", {}).get("latest_market_date") or "") for row in ordered), default="")
        previous = self.snapshot_storage.latest(namespace)
        alerts = build_alerts(rankable, previous.model_dump() if previous else None, market_date)
        overlap = build_overlap_matrix(ordered)
        audit_by_id = {row["theme_id"]: row for row in coverage_audit}
        member_coverage = {row["theme_id"]: {"coverage_ratio": row["coverage_ratio"], "eligible_count": row["eligible_count"], "member_count": row["member_count"], **({"gate": audit_by_id[row["theme_id"]]} if row["theme_id"] in audit_by_id else {})} for row in ordered}
        # Include the published payload contract so a schema/presentation field
        # added to an immutable snapshot cannot reuse an older snapshot ID.
        snapshot_formula = LAUNCH_THEME_SCORING_FORMULA_VERSION if include_launch else THEME_SCORING_FORMULA_VERSION
        hash_payload = {"themes": [(row["theme_id"], row["version"], row["input_hash"]) for row in ordered], "market_date": market_date, "formula": snapshot_formula, "rotation_model": THEME_ROTATION_MODEL_VERSION, "payload_contract": "theme-snapshot-v2.2"}
        if include_launch:
            hash_payload.update({"taxonomy_version": TAXONOMY_VERSION, "payload_contract": "theme-snapshot-v3.2"})
        input_hash = hashlib.sha256(json.dumps(hash_payload, sort_keys=True).encode()).hexdigest()
        mapped_symbols = {item.symbol for item in self.registry.mappings}
        benchmark_symbols = symbols - mapped_symbols
        repository_stats = {
            **self.bars.query_statistics,
            "security_master_batch_queries": 1,
            "history_repository_calls": 1,
            "provider_history_calls": 0,
            "unique_symbols_requested": len(symbols),
            "unique_mapped_symbols": len(mapped_symbols),
            "benchmark_symbols_requested": len(benchmark_symbols),
            "overlapping_mapping_reuse": len(self.registry.mappings) - len(mapped_symbols),
            "benchmark_reference_reuse": sum(len(item.benchmark_symbols) for item in self.registry.launch()) - len({symbol for item in self.registry.launch() for symbol in item.benchmark_symbols}),
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_note": "Canonical snapshot build reads the durable repository directly; published warm reads use the taxonomy-versioned snapshot namespace.",
            "snapshot_rows": len(ordered),
            "ranked_rows": len(rankable),
        } if include_launch else {}
        rotation_summary = (f"{rankable[0]['display_name']} leads the governed ThemeSnapshot." if rankable else "No themes meet ranking gates.") if include_launch else (f"{ordered[0]['display_name']} leads the reviewed live ThemeSnapshot." if ordered else "No themes qualify.")
        warnings = ("Historical results use the current reviewed constituent basket unless historical membership versions are available.", f"Rank excludes partial and unavailable themes; {active_theme_count} themes meet normal production gates.") if include_launch else ("Historical results use the current reviewed constituent basket unless historical membership versions are available.", f"Rank reflects the leadership composite among the {active_theme_count} currently active reviewed pilot themes.")
        snapshot = ThemeSnapshot(snapshot_id=f"theme-{market_date}-{hashlib.sha256(input_hash.encode()).hexdigest()[:10]}", schema_version=3 if include_launch else 2, market_date=market_date, generated_at=now, published_at=now, status="complete" if all(row.get("status", "available") == "available" and row["coverage_status"] == "complete" for row in ordered) else "partial", source_state=state, active_theme_versions=tuple({"theme_id": row["theme_id"], "version": row["version"]} for row in ordered), member_coverage=member_coverage, providers=("polygon",), rows=tuple(ordered), rankings=tuple(row["theme_id"] for row in rankable), rotation_summary=rotation_summary, overlap_matrix=tuple(overlap), alerts=tuple(alerts), warnings=warnings, input_hash=input_hash, formula_version=snapshot_formula, configuration_signature=hashlib.sha256(json.dumps([(row["theme_id"], row["version"]) for row in ordered]).encode()).hexdigest()[:20], taxonomy_version=TAXONOMY_VERSION if include_launch else None, repository_stats=repository_stats, coverage_audit=tuple(coverage_audit))
        if publish:
            self.snapshot_storage.publish(snapshot, namespace)
            if include_launch:
                self.snapshot_storage.publish(snapshot, f"{namespace}:{TAXONOMY_VERSION}")
        return snapshot

    def _build_launch_rows(self, histories: dict[str, tuple[Any, ...]], generated_at: str, state: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        symbols = sorted({item.symbol for item in self.registry.mappings})
        securities = self.securities.active_securities(tuple(symbols))
        previous = self.snapshot_storage.latest(theme_namespace())
        previous_rows = {row.get("theme_id"): row for row in previous.rows} if previous else {}
        rows: list[dict[str, Any]] = []; audit: list[dict[str, Any]] = []
        for definition in self.registry.launch():
            mappings = self.registry.constituents(definition.id); mapped = [item.symbol for item in mappings]
            registered = [symbol for symbol in mapped if symbol in securities]
            capable = [symbol for symbol in registered if securities[symbol].history_provider_symbol]
            counts = {days: [symbol for symbol in capable if len(histories.get(symbol, ())) >= days] for days in (1, 2, 22, 50, 200, 253)}
            sector_benchmarks = sorted({SECTOR_BY_ID[sector]["etf_symbol"] for sector in definition.parent_sector_ids if sector in SECTOR_BY_ID})
            required_benchmarks = ["SPY", *sector_benchmarks]
            ready_benchmarks = [symbol for symbol in required_benchmarks if len(histories.get(symbol, ())) >= 22]
            usable = counts[22]
            dates = [histories[symbol][-1].session_date for symbol in [*usable, *ready_benchmarks] if histories.get(symbol)]
            market_date = min(dates) if dates else ""
            aligned = {symbol: tuple(bar for bar in histories.get(symbol, ()) if not market_date or bar.session_date <= market_date) for symbol in capable}
            benchmark_histories = {symbol: tuple(bar for bar in histories.get(symbol, ()) if not market_date or bar.session_date <= market_date) for symbol in set((*definition.benchmark_symbols, *required_benchmarks))}
            analytics = self.analytics.compute(definition.id, aligned, benchmark_histories, as_of=market_date or None, source_state=state, generated_at=generated_at, observed_at=f"{market_date}T21:00:00+00:00" if market_date else None, previous_snapshot=previous_rows.get(definition.id), required_benchmark_symbols=required_benchmarks)
            status = analytics["status"]
            causes: list[str] = []
            if len(registered) < len(mapped): causes.append("missing_security_master_registration")
            if len(capable) < len(registered): causes.append("history_provider_mapping_missing")
            if len(counts[1]) < len(capable): causes.append("history_absent")
            if len(counts[22]) < len(capable): causes.append("minimum_history_window_missing")
            if len(ready_benchmarks) < len(required_benchmarks): causes.append("required_benchmark_history_missing")
            if len(counts[50]) < len(usable): causes.append("breadth_50d_partial")
            if len(counts[200]) < len(usable): causes.append("breadth_200d_partial")
            if analytics["freshness"]["state"] in {"stale", "partial", "mixed", "unavailable"}: causes.append("freshness_constrained")
            if "SPY" not in ready_benchmarks or len(counts[2]) < max(2, definition.minimum_constituents // 2):
                status = "unavailable"
            elif status == "available" and (len(ready_benchmarks) < len(required_benchmarks) or analytics["freshness"]["state"] != "live" or analytics["confidence"]["label"] != "moderate"):
                status = "partial"
            analytics["status"] = status
            coverage = len(usable) / len(mapped) if mapped else 0.0
            basket = build_equal_weight_basket_history(
                theme_id=definition.id,
                theme_version=TAXONOMY_VERSION,
                tickers=mapped,
                histories=aligned,
                source_state=state,
                partial_coverage_threshold=ThemePolicy().partial_coverage_threshold,
                generated_at=generated_at,
            )
            basket_history = tuple(to_daily_bar(item) for item in basket)
            rotation = {
                profile.interval_alias: build_theme_rotation_series(
                    theme_id=definition.id,
                    display_name=definition.name,
                    short_label=definition.short_name,
                    theme_version=TAXONOMY_VERSION,
                    basket_history=basket,
                    benchmark_history=benchmark_histories.get("SPY", ()),
                    profile=profile.profile,
                    source_state=state,
                    data_mode="live" if state == "live" else "test",
                )
                for profile in THEME_ROTATION_PROFILES.values()
            }
            gate = {
                "theme_id": definition.id, "mapped_count": len(mapped), "security_master_count": len(registered),
                "history_provider_capable_count": len(capable), "history_any_count": len(counts[1]), "history_21d_count": len(counts[22]),
                "history_50d_count": len(counts[50]), "history_200d_count": len(counts[200]), "history_1y_count": len(counts[253]),
                "coverage_ratio": round(coverage, 6), "primary_benchmark_available": "SPY" in ready_benchmarks,
                "sector_benchmarks": sector_benchmarks, "sector_benchmark_available": set(sector_benchmarks).issubset(set(ready_benchmarks)),
                "required_benchmarks_available": ready_benchmarks, "market_date": market_date or None, "status": status,
                "unregistered_symbols": [symbol for symbol in mapped if symbol not in securities],
                "provider_mapping_missing_symbols": [symbol for symbol in registered if not securities[symbol].history_provider_symbol],
                "history_missing_symbols": [symbol for symbol in capable if not histories.get(symbol)],
                "minimum_history_missing_symbols": [symbol for symbol in capable if len(histories.get(symbol, ())) < 22],
                "missing_required_benchmarks": [symbol for symbol in required_benchmarks if symbol not in ready_benchmarks],
                "gate": "available requires >=75% mapped 21-session coverage, registry minimum, SPY and every parent-sector reference, current freshness, and moderate confidence; partial requires >=2 computable histories; unavailable is below that floor or lacks SPY.",
                "cause_categories": causes or ["none"],
            }
            audit.append(gate)
            if status in {"available", "partial"}:
                rows.append(self._snapshot_row(analytics, definition, mappings, securities, gate, rotation))
        return rows, audit

    @staticmethod
    def _snapshot_row(analytics: dict[str, Any], definition: Any, mappings: tuple[Any, ...], securities: dict[str, Any], gate: dict[str, Any], rotation: dict[str, Any]) -> dict[str, Any]:
        returns = analytics["relative_strength"]["equal_weight_returns"]
        vs_spy = analytics["relative_strength"].get("vs_spy", {})
        breadth = analytics["breadth"]
        constituents = analytics["constituents"]
        eligible_month = [item for item in constituents if isinstance(item.get("relative_strength"), (int, float))]
        participation = round(sum(item["relative_strength"] > 0 for item in eligible_month) / len(eligible_month) * 100, 4) if eligible_month else None
        concentration_quality = {"broad": 100.0, "moderately_concentrated": 65.0, "narrow": 25.0}.get(analytics["concentration"]["classification"])
        components = {
            "momentum": clip_score(50 + (analytics["momentum"].get("medium_window") or 0) * 5) if analytics["momentum"].get("medium_window") is not None else None,
            "relative_strength": clip_score(50 + (vs_spy.get("1m") or 0) * 5) if vs_spy.get("1m") is not None else None,
            "breadth": breadth.get("percent_above_50_day_average"), "participation": participation,
            "concentration_quality": concentration_quality,
        }
        available = {key: value for key, value in components.items() if value is not None}; total_weight = sum(THEME_SCORING_WEIGHTS[key] for key in available)
        contributions = {key: {"score": value, "weight": round(THEME_SCORING_WEIGHTS[key] / total_weight, 6) if value is not None and total_weight else 0.0, "weighted_contribution": round(value * THEME_SCORING_WEIGHTS[key] / total_weight, 4) if value is not None and total_weight else None} for key, value in components.items()}
        composite = round(sum(item["weighted_contribution"] or 0 for item in contributions.values()), 2) if available else None
        confidence_label = analytics["confidence"]["label"]
        members = []
        by_symbol = {item["symbol"]: item for item in constituents}
        for mapping in mappings:
            metric = by_symbol[mapping.symbol]; security = securities.get(mapping.symbol)
            members.append({"ticker": mapping.symbol, "symbol": mapping.symbol, "company_name": security.company_name if security else mapping.symbol, "role": mapping.exposure, "exposure": mapping.exposure, "weight": round(1 / len(mappings), 8), "return_1m": metric.get("relative_strength"), "availability": metric.get("availability"), "inclusion_reason": mapping.rationale})
        relative = {**analytics["relative_strength"], **{f"vs_spy_{window}": value for window, value in vs_spy.items()}, "trend": analytics["leadership_state"]}
        breadth_legacy = {**breadth, "percent_above_ema20": breadth.get("percent_above_20_day_average"), "percent_above_ema50": breadth.get("percent_above_50_day_average"), "percent_above_ema200": breadth.get("percent_above_200_day_average")}
        coverage_status = "complete" if gate["coverage_ratio"] >= ThemePolicy().complete_coverage_threshold else "partial" if gate["coverage_ratio"] >= ThemePolicy().partial_coverage_threshold else "unavailable"
        row = {
            **analytics, "display_name": definition.name, "version": TAXONOMY_VERSION, "market_date": analytics["market_date"],
            "member_count": len(mappings), "eligible_count": gate["history_21d_count"], "coverage_status": coverage_status,
            "performance": returns, "relative_strength": relative, "breadth": breadth_legacy,
            "participation": {"positive_return_participation_pct": participation, "positive_return_member_count": sum(item["relative_strength"] > 0 for item in eligible_month), "eligible_count": len(eligible_month), "definition": "Equal-weight share of constituents with positive 1-month returns."},
            "component_scores": components, "weighted_contributions": contributions, "composite_score": composite,
            "classification": analytics["leadership_state"].title(), "rank": None,
            "data_confidence": {"score": round(gate["coverage_ratio"] * 100, 2), "label": "Moderate" if analytics["status"] == "available" else "Limited", "reason": f"{gate['history_21d_count']}/{gate['mapped_count']} mapped constituents meet the 21-session computation floor."},
            "signal_confidence": {"score": 70 if confidence_label == "moderate" else 40, "label": confidence_label.title(), "reason": "Stage 7.5 confidence engine with required benchmark, freshness, and missing-dimension caps."},
            "representativeness": representativeness(gate["history_21d_count"]), "members": members,
            "score_semantics": {"score_type": "absolute_weighted_composite", "displayed_score_type": "absolute_weighted_composite", "display_label": "Absolute composite score", "scale": "0-100", "formula_version": LAUNCH_THEME_SCORING_FORMULA_VERSION, "component_scores": components, "weighted_contributions": contributions, "cross_sectional_percentile": None, "interpretation": "The score is an audited weighted sum; rank is assigned only after availability, freshness, benchmark, and confidence gates pass."},
            "basket_methodology": {"policy": "daily_rebalanced_equal_weight", "weighting": "Every eligible registered mapped constituent receives equal weight; missing symbols are excluded and disclosed, never replaced or zero-filled.", "historical_disclosure": "Historical results use the current taxonomy-versioned constituent mapping."},
            "definition": {**definition.model_dump(), "parent_sector_labels": [SECTOR_BY_ID[item]["display_name"] for item in definition.parent_sector_ids if item in SECTOR_BY_ID], "primary_benchmark": "SPY", "secondary_benchmark": gate["sector_benchmarks"][0] if gate["sector_benchmarks"] else None},
            "warnings": ["Historical results use current taxonomy-versioned membership; historical membership reconstruction is unavailable.", *( ["Partial rows are excluded from rankings and strong conclusions."] if analytics["status"] == "partial" else [])],
            "provenance": {"category": "live_verified", "source_state": analytics["source_status"]["state"], "history_provider": "polygon", "taxonomy_version": TAXONOMY_VERSION, "mapping_source": "curated_launch_catalog", "current_basket_historical": True},
            "coverage_gate": gate, "rotation_series": rotation,
        }
        row["input_hash"] = hashlib.sha256(json.dumps({"theme": definition.id, "taxonomy": TAXONOMY_VERSION, "analytics_version": analytics["analytics_version"], "formula": LAUNCH_THEME_SCORING_FORMULA_VERSION, "status": analytics["status"], "coverage_status": coverage_status, "gate": gate, "market_date": analytics["market_date"], "freshness": analytics["freshness"], "confidence": analytics["confidence"], "performance": returns, "components": components, "members": [(item["ticker"], item["availability"], item["return_1m"]) for item in members], "rotation": {interval: {"status": value.get("status"), "latest_market_date": value.get("latest_market_date"), "point_count": value.get("point_count"), "compatibility_signature": value.get("compatibility_signature")} for interval, value in rotation.items()}}, sort_keys=True).encode()).hexdigest()
        return row

    @staticmethod
    def _rankable(row: dict[str, Any]) -> bool:
        if "status" not in row:
            return row.get("coverage_status") != "unavailable" and int(row.get("member_count") or 0) >= ThemePolicy().minimum_live_members
        confidence = row.get("confidence") or {}
        label = confidence.get("label") if isinstance(confidence, dict) else confidence
        freshness = (row.get("freshness") or {}).get("state")
        return row.get("status") == "available" and label == "moderate" and freshness in {"live", "delayed", "cached"}
