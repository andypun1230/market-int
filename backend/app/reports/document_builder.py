from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from app.breadth.storage import BreadthSnapshotStorage
from app.market_history.storage import DailyBar, DailyBarStorage
from app.reports.document import (
    AnalyticalClaim,
    DataQualityState,
    EvidenceMatrixRow,
    EvidencePoint,
    FigureAnnotation,
    FigureSeries,
    FigureSpec,
    MonitoringCondition,
    MarketTimelineEntry,
    ReportDocument,
    ReportSection,
    ReportThesis,
    ResearchEvidenceQuality,
    ResearchEvolution,
    ResearchFocus,
    ResearchInquiry,
    ResearchRelationshipEdge,
    ResearchRelationshipGraph,
    ResearchRelationshipNode,
    ResearchSecuritySignal,
    SavedSecurityImpact,
    ScenarioSpec,
    SecondaryResearchNote,
    SecurityResearchItem,
    SourceReference,
    TableSpec,
)
from app.reports.research import ResearchCandidateEngine, research_evidence_payloads
from app.sector_snapshots.service import get_sector_snapshot_service
from app.services.sector_dashboard import build_sector_rotation_trails


BAR_PROVIDERS = ("polygon", "massive", "test", "generated_test_data")
SUPPORTED_QUALITY = {"live", "cached", "stale", "test", "mixed", "partial", "unavailable"}


class DocumentBuilder:
    def __init__(self, report: Any, previous_snapshot: dict[str, Any] | None = None) -> None:
        self.report = report.model_dump(mode="json") if hasattr(report, "model_dump") else dict(report)
        self.previous_snapshot = previous_snapshot
        self.sources: dict[str, SourceReference] = {}
        self.evidence: dict[str, EvidencePoint] = {}
        self.claims: dict[str, AnalyticalClaim] = {}
        self.figures: list[FigureSpec] = []
        self.tables: list[TableSpec] = []
        self.securities: list[SecurityResearchItem] = []
        self.monitoring: list[MonitoringCondition] = []
        self.limitations: list[str] = []
        self.research_candidates = []
        self.research_selection = None
        self.research_focus: ResearchFocus | None = None
        self.research_inquiry: ResearchInquiry | None = None
        self.secondary_research_note: SecondaryResearchNote | None = None
        self.market_timeline: list[MarketTimelineEntry] = []
        self.bars = DailyBarStorage()

    def build(self) -> ReportDocument:
        generated_at = str(self.report.get("generated_at") or self.report.get("generated_time") or datetime.now(timezone.utc).isoformat())
        market_date = str(self.report.get("market_date") or self.report.get("date"))
        source_status = self._quality(self._source_state())
        self._register_core_sources(generated_at)
        thesis = self._build_thesis(market_date, generated_at, source_status)
        self._build_index_figures(market_date)
        self._build_breadth_figures(market_date)
        self._build_leadership_figures(market_date)
        self._build_research_focus(market_date)
        self._build_macro_figure(market_date)
        self._build_risk_figure(market_date)
        self._build_market_timeline(market_date)
        self._build_watchlist(market_date)
        scenarios = self._build_scenarios(thesis)
        self._build_monitoring(thesis)
        self._record_unsupported_gaps()
        self._number_figures()
        sections = self._build_sections(thesis, scenarios)
        words = document_word_count(
            thesis, sections, list(self.claims.values()), self.figures, scenarios,
            self.securities, self.monitoring, self.limitations, self.research_focus, self.secondary_research_note,
            self.research_inquiry,
        )
        selected_security_count = sum(item.selected_for_research for item in self.securities)
        paired_figure_count = max(0, len(self.figures) - selected_security_count)
        page_estimate = max(
            10,
            min(
                22,
                7
                + (paired_figure_count + 1) // 2
                + selected_security_count
                + (1 if selected_security_count else 0)
                + (1 if self.research_focus else 0),
            ),
        )
        return ReportDocument(
            document_version="report-document-v2",
            report_id=str(self.report.get("report_id") or f"daily-{market_date}"),
            pdf_format_version="daily-report-pdf-v7",
            title="Daily Market Intelligence Briefing",
            report_type=self._report_type(generated_at, market_date),
            market_date=market_date,
            generated_at=generated_at,
            data_cutoff=self._data_cutoff(generated_at),
            timezone="UTC",
            source_status=source_status,
            thesis=thesis,
            sections=sections,
            evidence=list(self.evidence.values()),
            claims=list(self.claims.values()),
            figures=self.figures,
            tables=self.tables,
            sources=list(self.sources.values()),
            scenarios=scenarios,
            securities=self.securities,
            monitoring_conditions=self.monitoring,
            limitations=sorted(set(self.limitations)),
            page_count_estimate=page_estimate,
            figure_count=len(self.figures),
            approximate_word_count=words,
            previous_report_available=self.previous_snapshot is not None,
            research_candidates=self.research_candidates,
            research_selection=self.research_selection,
            research_focus=self.research_focus,
            secondary_research_note=self.secondary_research_note,
            market_timeline=self.market_timeline,
            research_inquiry=self.research_inquiry,
        )

    def _register_core_sources(self, generated_at: str) -> None:
        semantic = self.report.get("semantic_context") or {}
        snapshot_ids = semantic.get("snapshot_ids") if isinstance(semantic, dict) else {}
        self._source("report", "Internal snapshot services", "Immutable daily report input", generated_at, "internal_snapshot")
        for name in ("market", "breadth", "sector", "theme"):
            snapshot_id = (snapshot_ids or {}).get(name)
            if snapshot_id and snapshot_id != "unavailable":
                self._source(f"snapshot-{name}", "Internal snapshot services", f"{name.title()} snapshot {snapshot_id}", generated_at, "immutable_snapshot")

    def _build_thesis(self, market_date: str, generated_at: str, quality: str) -> ReportThesis:
        regime = str(self.report.get("market_regime") or "Unavailable")
        health = self.report.get("market_health") or {}
        breadth = self.report.get("report_snapshot") or {}
        health_score = number(health.get("overall_score"))
        breadth_value = number(path(breadth, "historicalMetrics", "breadth"))
        confidence = number(path(self.report, "recommendation_confidence", "score"))
        risk_score = number(path(self.report, "risk_dashboard", "score"))
        sentiment_score = number(path(self.report, "fear_greed", "score"))
        health_id = self._evidence("market-health", "Market health score", health_score, "score", "current session", "report", market_date)
        breadth_id = self._evidence("breadth-50", "Constituents above 50-day EMA", breadth_value, "percent", "current session", "snapshot-breadth", market_date)
        confidence_id = self._evidence("decision-confidence", "Decision confidence", confidence, "score", "current report", "report", generated_at)
        risk_id = self._evidence("risk-score", "Risk dashboard score", risk_score, "score", "current session", "report", generated_at)
        sentiment_id = self._evidence("sentiment-score", "Fear and Greed score", sentiment_score, "score", "current session", "report", generated_at)
        supporting = [item for item in (health_id, breadth_id, confidence_id) if item]
        leader = first_text(self.report.get("sector_leaders")) or "durable sector leadership"
        thesis_text = (
            f"The {regime} regime remains the primary operating frame. Index structure, participation, "
            f"leadership led by {leader}, and cross-asset proxy evidence should be used together; incomplete "
            "confirmation favors selective exposure and explicit invalidation levels."
        )
        self._claim(
            "current-thesis",
            thesis_text,
            supporting,
            "The evidence supports a conditional posture rather than a broad causal conclusion.",
            "Favor setups that confirm on price, participation, and volume; reduce risk when those signals diverge.",
            quality,
        )
        risk_evidence = [item for item in (risk_id, sentiment_id, breadth_id) if item]
        self._claim(
            "risk-posture",
            "Current risk, sentiment, and participation are evaluated as separate observations; disagreement between them is treated as counter-evidence.",
            risk_evidence,
            "A point-in-time score needs historical direction and cross-signal confirmation before it can support a stronger conclusion.",
            "Keep position size conditional on benchmark support and participation rather than relying on a single risk score.",
            quality,
        )
        confirmation = [
            "Benchmark price holds above medium-term support while participation improves.",
            "Leadership broadens beyond the current leading groups with confirming volume.",
        ]
        invalidation = [
            "Benchmark price breaks medium-term support while breadth deteriorates.",
            "Credit and volatility proxies stop confirming the prevailing risk posture.",
        ]
        previous_thesis = path(self.previous_snapshot or {}, "narrative", "overallThesis") or path(self.previous_snapshot or {}, "overallThesis")
        return ReportThesis(
            posture=regime,
            concise_thesis=thesis_text,
            previous_thesis=str(previous_thesis) if previous_thesis else None,
            thesis_change="Comparison available in the relevant analytical sections." if previous_thesis else "Baseline established.",
            supporting_evidence_ids=supporting,
            contradictory_evidence_ids=[],
            confirmation_conditions=confirmation,
            invalidation_conditions=invalidation,
            confidence_label=confidence_label(confidence),
            data_completeness=self._completeness(),
        )

    def _build_index_figures(self, market_date: str) -> None:
        for symbol in ("SPY", "QQQ", "IWM", "DIA"):
            bars = self._bars(symbol, market_date)
            if len(bars) < 20:
                closes = (self.report.get("index_histories") or {}).get(symbol) or []
                if len(closes) >= 20:
                    self._build_close_only_figure(symbol, closes, market_date)
                else:
                    self.limitations.append(f"{symbol} structure figure omitted because durable history has fewer than 20 observations.")
                continue
            source_id = self._bar_source(symbol, bars)
            closes = [bar.close for bar in bars[-260:]]
            dates = [bar.session_date for bar in bars[-260:]]
            series = [self._series(f"{symbol}-close", symbol, "price", dates, closes, source_id)]
            for window, color in ((20, "#00A6D6"), (50, "#7A5AF8"), (200, "#D97706")):
                values = moving_average(closes, window)
                if any(value is not None for value in values):
                    series.append(self._series(f"{symbol}-ma{window}", f"MA {window}", "price", dates, values, source_id, color, f"simple moving average ({window} sessions)"))
            volume = [bar.volume for bar in bars[-260:]]
            if any(value > 0 for value in volume):
                series.append(self._series(f"{symbol}-volume", "Volume", "shares", dates, volume, source_id, "#A8B3C7"))
            latest = closes[-1]
            latest_id = self._evidence(f"{symbol.lower()}-close", f"{symbol} adjusted close", latest, "price", "latest session", source_id, dates[-1])
            ma50 = next((value for value in reversed(moving_average(closes, 50)) if value is not None), None)
            ma_id = self._evidence(f"{symbol.lower()}-ma50", f"{symbol} 50-day moving average", ma50, "price", "50 sessions", source_id, dates[-1])
            annotations: list[FigureAnnotation] = []
            recent_window = closes[-20:]
            if recent_window:
                recent_high = max(recent_window)
                recent_low = min(recent_window)
                high_index = len(closes) - len(recent_window) + recent_window.index(recent_high)
                low_index = len(closes) - len(recent_window) + recent_window.index(recent_low)
                high_id = self._evidence(f"{symbol.lower()}-recent-high", f"{symbol} recent high", recent_high, "price", "20 sessions", source_id, dates[high_index])
                low_id = self._evidence(f"{symbol.lower()}-recent-low", f"{symbol} recent low", recent_low, "price", "20 sessions", source_id, dates[low_index])
                if high_id:
                    annotations.append(FigureAnnotation(annotation_id=f"{symbol.lower()}-recent-high", annotation_type="recent_high", label="Recent high", value=recent_high, point_index=high_index, date=dates[high_index], evidence_id=high_id))
                if low_id:
                    annotations.append(FigureAnnotation(annotation_id=f"{symbol.lower()}-recent-low", annotation_type="recent_low", label="Recent low", value=recent_low, point_index=low_index, date=dates[low_index], evidence_id=low_id))
            if ma_id and ma50 is not None:
                annotations.append(FigureAnnotation(annotation_id=f"{symbol.lower()}-ma50-label", annotation_type="moving_average_label", label="MA 50", value=ma50, point_index=len(closes) - 1, date=dates[-1], evidence_id=ma_id))
            prior_date = str((self.previous_snapshot or {}).get("marketDate") or "")
            if prior_date in dates:
                prior_index = dates.index(prior_date)
                prior_id = self._evidence(f"{symbol.lower()}-previous-report", f"{symbol} previous-report close", closes[prior_index], "price", "previous compatible report", source_id, prior_date)
                if prior_id:
                    annotations.append(FigureAnnotation(annotation_id=f"{symbol.lower()}-previous-report", annotation_type="previous_report_marker", label="Previous report", value=closes[prior_index], point_index=prior_index, date=prior_date, evidence_id=prior_id))
            if len(volume) >= 20 and sum(volume[-20:]) > 0:
                volume_average = sum(volume[-20:]) / 20
                ratio = volume[-1] / volume_average if volume_average else 0
                if ratio >= 1.5:
                    volume_id = self._evidence(f"{symbol.lower()}-volume-expansion", f"{symbol} volume versus 20-session average", ratio, "ratio", "latest session", source_id, dates[-1])
                    if volume_id:
                        annotations.append(FigureAnnotation(annotation_id=f"{symbol.lower()}-volume-expansion", annotation_type="volume_expansion", label=f"Volume {ratio:.1f}x", value=latest, point_index=len(closes) - 1, date=dates[-1], evidence_id=volume_id))
            relation = "above" if ma50 is not None and latest >= ma50 else "below" if ma50 is not None else "without a qualified 50-day average"
            observation = f"{symbol} closed at {latest:.2f}, {relation} its 50-day average" + (f" of {ma50:.2f}." if ma50 is not None else ".")
            evidence_ids = [item for item in (latest_id, ma_id) if item]
            self._claim(f"{symbol.lower()}-structure", observation, evidence_ids, "Price structure is descriptive and does not establish causation.", "Use the recent range and moving averages as confirmation and invalidation references.", "live" if source_id.startswith("bars-polygon") else "test")
            self.figures.append(FigureSpec(
                figure_id=f"index-{symbol.lower()}", title=f"{symbol} Price, Trend and Volume", subtitle="Adjusted daily observations with qualified moving averages", question_answered=f"Is {symbol} price structure confirming the market thesis?", chart_type="price_volume", timeframe=f"{len(closes)} sessions", data_series=series, annotations=annotations, source_ids=[source_id], as_of=dates[-1], observation=observation,
                interpretation=f"{symbol} remains a direct test of the report's market-structure thesis.", confirmation_condition="A close above the recent swing high with improving participation.", risk_condition="A break below the medium-term average with deteriorating breadth.", quality=self._data_quality(source_id, len(closes), 200, "adjusted OHLCV with simple moving averages"),
            ))
        self._build_ratio_figure("QQQ", "SPY", market_date)
        self._build_ratio_figure("IWM", "SPY", market_date)

    def _build_close_only_figure(self, symbol: str, closes: list[Any], market_date: str) -> None:
        values = [float(value) for value in closes if number(value) is not None][-260:]
        source_id = "report"
        points = [{"index": index + 1, "value": value} for index, value in enumerate(values)]
        self.figures.append(FigureSpec(
            figure_id=f"index-{symbol.lower()}", title=f"{symbol} Closing-Price Structure", subtitle="Frozen report history; volume and session labels unavailable", question_answered=f"Is {symbol} closing-price structure stable?", chart_type="line", timeframe=f"{len(values)} observations", data_series=[FigureSeries(series_id=f"{symbol}-close", label=symbol, unit="price", points=points, source_id=source_id)], source_ids=[source_id], as_of=market_date,
            observation=f"The frozen report contains {len(values)} {symbol} closing-price observations.", interpretation="The close-only series supports trend inspection but not volume or event alignment.", confirmation_condition="Durable dated OHLCV would strengthen the structure assessment.", risk_condition="Do not infer volume confirmation from this close-only series.", quality=DataQualityState(state="partial", completeness=min(1, len(values) / 200), freshness="current report", transformation="close-only frozen series", warnings=["Session dates and volume unavailable"]),
        ))

    def _build_ratio_figure(self, numerator: str, denominator: str, market_date: str) -> None:
        left = {bar.session_date: bar for bar in self._bars(numerator, market_date)}
        right = {bar.session_date: bar for bar in self._bars(denominator, market_date)}
        dates = sorted(set(left).intersection(right))[-260:]
        if len(dates) < 20:
            self.limitations.append(f"{numerator}/{denominator} ratio omitted because aligned durable history is insufficient.")
            return
        values = [left[date].close / right[date].close for date in dates]
        sources = [self._bar_source(numerator, list(left.values())), self._bar_source(denominator, list(right.values()))]
        source_id = self._source(f"ratio-{numerator.lower()}-{denominator.lower()}", "Internal calculation", f"{numerator}/{denominator} adjusted-close ratio", dates[-1], "derived_series")
        self.figures.append(FigureSpec(
            figure_id=f"ratio-{numerator.lower()}-{denominator.lower()}", title=f"{numerator} Relative to {denominator}", subtitle="Adjusted-close ratio; rising values indicate relative outperformance", question_answered=f"Is {numerator} leadership improving relative to {denominator}?", chart_type="relative_strength", timeframe=f"{len(dates)} shared sessions", data_series=[self._series(f"{numerator}-{denominator}-ratio", f"{numerator}/{denominator}", "ratio", dates, values, source_id)], source_ids=[source_id, *sources], as_of=dates[-1], observation=f"The latest {numerator}/{denominator} ratio is {values[-1]:.4f}.", interpretation="Direction in the ratio provides relative-leadership evidence, not a causal explanation for either asset.", confirmation_condition="A higher ratio high with improving breadth would confirm relative leadership.", risk_condition="A lower ratio low would weaken the relative-leadership case.", quality=DataQualityState(state=self._quality(self._source_state()), completeness=min(1, len(dates) / 200), freshness="latest durable session", transformation="date-aligned adjusted close division"),
        ))

    def _build_breadth_figures(self, market_date: str) -> None:
        snapshot_id = path(self.report, "semantic_context", "snapshot_ids", "breadth")
        snapshot = BreadthSnapshotStorage().get(str(snapshot_id)) if snapshot_id and snapshot_id != "unavailable" else None
        if snapshot is None:
            self.limitations.append("Breadth history figures omitted because the referenced immutable BreadthSnapshot is unavailable.")
            return
        storage = BreadthSnapshotStorage()
        source_id = self._source("breadth-history", ", ".join(snapshot.providers) or "Internal breadth engine", f"BreadthSnapshot history for {snapshot.universe_version}", snapshot.latest_input_timestamp or snapshot.market_date, "immutable_snapshot_series")
        metrics = ("percent_above_20ema", "percent_above_50ema", "percent_above_200ema")
        series: list[FigureSeries] = []
        for metric, label, color in zip(metrics, ("Above 20-day EMA", "Above 50-day EMA", "Above 200-day EMA"), ("#00A6D6", "#7A5AF8", "#D97706")):
            values = storage.history(snapshot.universe_id, metric, days=180, end=market_date)
            points = [{"date": item["market_date"], "value": item["value"]} for item in values if number(item.get("value")) is not None]
            if points:
                series.append(FigureSeries(series_id=metric, label=label, unit="percent", points=points, source_id=source_id, color=color, transformation="immutable snapshot history"))
        if series:
            latest50 = next((point["value"] for item in series if item.series_id == "percent_above_50ema" for point in item.points[-1:]), None)
            self._evidence("breadth-history-50", "Constituents above 50-day EMA", number(latest50), "percent", "latest completed session", source_id, snapshot.market_date)
            self.figures.append(FigureSpec(figure_id="breadth-ma-history", title="Participation Across Trend Horizons", subtitle=f"{snapshot.universe_version} constituent breadth", question_answered="Is participation broadening or narrowing across short, medium and long horizons?", chart_type="breadth_time_series", timeframe="Up to 180 published snapshots", data_series=series, source_ids=[source_id], as_of=snapshot.market_date, observation="Short-, medium-, and long-horizon participation are shown from immutable breadth snapshots.", interpretation="Agreement across horizons strengthens participation evidence; divergence identifies a narrower or transitional market.", confirmation_condition="Rising medium- and long-horizon participation would confirm broader trend support.", risk_condition="Falling participation while the benchmark holds near its high would increase divergence risk.", quality=self._data_quality(source_id, max(len(item.points) for item in series), 20, "immutable snapshot history")))
        for metric, title, question in (("net_advances", "Net Advances", "Are advancing constituents outnumbering decliners?"), ("highs_minus_lows", "New Highs Minus New Lows", "Is internal momentum expanding or contracting?")):
            values = storage.history(snapshot.universe_id, metric, days=180, end=market_date)
            points = [{"date": item["market_date"], "value": item["value"]} for item in values if number(item.get("value")) is not None]
            if len(points) < 2:
                self.limitations.append(f"{title} history omitted because fewer than two published observations are available.")
                continue
            self.figures.append(FigureSpec(figure_id=f"breadth-{metric.replace('_', '-')}", title=title, subtitle=f"{snapshot.universe_version} daily internal participation", question_answered=question, chart_type="breadth_time_series", timeframe=f"{len(points)} published snapshots", data_series=[FigureSeries(series_id=metric, label=title, unit="count", points=points, source_id=source_id, transformation="immutable snapshot history")], source_ids=[source_id], as_of=snapshot.market_date, observation=f"The latest supported {title.lower()} reading is {float(points[-1]['value']):.1f}.", interpretation="The series describes participation direction without implying why constituents advanced or declined.", confirmation_condition="Sustained positive readings would confirm broader participation.", risk_condition="Persistent negative readings would weaken breakout reliability.", quality=self._data_quality(source_id, len(points), 20, "immutable snapshot history")))

    def _build_leadership_figures(self, market_date: str) -> None:
        dashboard = self.report.get("sector_dashboard") or {}
        rows = [item for item in dashboard.get("sectors") or [] if isinstance(item, dict)]
        if rows:
            source_id = self._source("sector-snapshot", str(dashboard.get("source") or "Internal sector engine"), f"Sector snapshot {dashboard.get('snapshot_id') or ''}".strip(), str(dashboard.get("as_of") or market_date), "immutable_snapshot")
            periods = ("1d", "1w", "1m", "3m", "6m", "1y")
            points = [{"label": str(row.get("name") or row.get("symbol")), **{period: number((row.get("returns") or {}).get(period)) for period in periods}} for row in rows]
            self.figures.append(FigureSpec(figure_id="sector-return-heatmap", title="Sector Leadership Matrix", subtitle="Multiple horizons; missing observations remain blank", question_answered="Where is sector leadership established or weakening?", chart_type="leadership_matrix", timeframe="1 day to 1 year", data_series=[FigureSeries(series_id="sector-returns", label="Sector returns", unit="percent", points=points, source_id=source_id, transformation="sector snapshot return matrix")], source_ids=[source_id], as_of=str(dashboard.get("as_of") or market_date), observation="The return matrix separates short-term movement from persistent multi-horizon leadership.", interpretation="Leadership is more robust when relative performance and internal breadth agree across horizons.", confirmation_condition="Improving returns accompanied by stronger sector breadth would confirm sustainable rotation.", risk_condition="Strong ETF returns with weak constituent participation would indicate concentration risk.", quality=self._data_quality(source_id, len(rows), 11, "snapshot matrix")))
        try:
            service = get_sector_snapshot_service()
            snapshot = service.latest()
            rotation = build_sector_rotation_trails(snapshot, service.history()) if snapshot else None
            series_rows = [item for item in (rotation or {}).get("series") or [] if item.get("interval") == "1M" and item.get("trail_points")]
            if series_rows:
                source_id = self._source("sector-rotation", "Internal rotation engine", "Adjusted sector ETF relative-return momentum", snapshot.market_date, "derived_snapshot_series")
                series = [FigureSeries(series_id=str(item.get("entity_id")), label=str(item.get("display_name")), unit="rotation", points=[{"date": point.get("market_date"), "x": point.get("plotted_x"), "y": point.get("plotted_y"), "quadrant": point.get("quadrant")} for point in item.get("trail_points") or []], source_id=source_id, transformation=str(item.get("normalization_version") or "midpoint-100 normalization")) for item in series_rows]
                self.figures.append(FigureSpec(figure_id="sector-rotation", title="Sector Rotation with Tails", subtitle="One-month relative-return momentum versus SPY", question_answered="Which sectors are gaining relative strength and momentum?", chart_type="rotation", timeframe="1 month", data_series=series, source_ids=[source_id], as_of=snapshot.market_date, observation="Rotation tails show direction and persistence rather than only the latest quadrant.", interpretation="Movement toward stronger relative performance and momentum provides confirmation; quadrant position alone is insufficient.", confirmation_condition="A sustained improving-to-leading path with qualifying sector breadth.", risk_condition="A leading-to-weakening path accompanied by deteriorating participation.", quality=self._data_quality(source_id, sum(len(item.points) for item in series), len(series) * 2, "canonical rotation engine")))
        except Exception as exc:
            self.limitations.append(f"Sector rotation figure unavailable: {type(exc).__name__}.")
        theme = self.report.get("theme_report") or {}
        rotation_items = path(theme, "rotation", "items") or []
        theme_series = []
        for item in rotation_items:
            points = [{"date": point.get("market_date"), "x": point.get("relative_strength"), "y": point.get("relative_momentum"), "quadrant": point.get("quadrant")} for point in item.get("trail_points") or [] if number(point.get("relative_strength")) is not None and number(point.get("relative_momentum")) is not None]
            if points:
                theme_series.append(FigureSeries(series_id=str(item.get("theme_id")), label=str(item.get("display_name")), unit="rotation", points=points, source_id="snapshot-theme", transformation=str(path(item, "trail_provenance", "normalization_version") or "canonical theme rotation")))
        if theme_series and "snapshot-theme" in self.sources:
            self.figures.append(FigureSpec(figure_id="theme-rotation", title="Theme Rotation with Tails", subtitle="Reviewed active baskets versus SPY", question_answered="Which reviewed themes are improving or weakening?", chart_type="rotation", timeframe=str(path(theme, "rotation", "selected_interval") or "1M"), data_series=theme_series, source_ids=["snapshot-theme"], as_of=str(theme.get("market_date") or market_date), observation="Theme trails use the reviewed active baskets available in the frozen ThemeSnapshot.", interpretation="The result supports relative monitoring within the reviewed universe, not a claim about unreviewed themes.", confirmation_condition="Improving relative momentum with broad constituent participation.", risk_condition="Weakening relative momentum or elevated constituent concentration.", quality=self._data_quality("snapshot-theme", sum(len(item.points) for item in theme_series), len(theme_series) * 2, "reviewed basket rotation")))

    def _build_research_focus(self, market_date: str) -> None:
        result = ResearchCandidateEngine(self.report, self.previous_snapshot).build()
        registered = []
        for candidate in result.candidates:
            source_id = self._research_source(candidate.category, market_date)
            ids = []
            for payload in research_evidence_payloads(candidate):
                evidence_id = self._evidence(
                    payload["evidence_id"], payload["metric"], payload["current_value"], payload["unit"],
                    payload["timeframe"], source_id, candidate.freshness,
                    freshness="current" if candidate.source_quality not in {"stale", "unavailable"} else candidate.source_quality,
                    previous=payload.get("previous_value"), change=payload.get("change"),
                )
                if evidence_id:
                    ids.append(evidence_id)
            score_id = self._evidence(
                f"research-{candidate.candidate_id.replace(':', '-')}-priority-score",
                f"{candidate.name} Research Priority Score", candidate.score.total, "score", "current report",
                source_id, market_date,
            )
            if score_id:
                ids.append(score_id)
            registered.append(candidate.model_copy(update={"evidence_ids": ids}))
        self.research_candidates = registered
        self.research_selection = result.decision
        selected_id = result.decision.selected_candidate_id
        selected = next((item for item in registered if item.candidate_id == selected_id), None)
        if selected is None:
            question = "Why did no reviewed subject meet the research evidence threshold?"
            rejected = registered[0] if registered else None
            missing = [humanize_research_gap(item) for item in result.decision.missing_evidence[:4]]
            executive_answer = (
                f"No candidate cleared every materiality, freshness, completeness, constituent, and figure gate. "
                f"The highest-ranked candidate was {rejected.name} at {rejected.score.total:.1f}, below or outside the qualifying policy; "
                f"the principal failed gates were {', '.join(missing) if missing else 'insufficient qualified evidence'}."
                if rejected
                else "No candidate had enough current, complete, and figure-ready evidence to support standalone coverage."
            )
            inquiry_evidence = rejected.evidence_ids[:8] if rejected else []
            self.research_inquiry = ResearchInquiry(
                status="no_focus",
                question=question,
                executive_answer=executive_answer,
                evidence_ids=inquiry_evidence,
            )
            self._build_no_focus_research_figure(registered, market_date)
            return

        source_id = self._research_source(selected.category, market_date)
        question = stage6_research_question(selected)
        executive_answer = stage6_executive_answer(selected)
        evidence_quality = self._research_evidence_quality(selected)
        evidence_matrix = self._research_evidence_matrix(selected)
        relationship_graph = self._research_relationship_graph(selected, source_id, market_date)
        leading, lagging = self._research_security_leadership(selected, source_id, market_date)
        evolution = self._research_evolution(selected)
        execution_implications = stage6_execution_implications(selected)
        conclusion_changes = stage6_conclusion_change_conditions(selected)
        figure_ids = self._build_research_figures(
            selected,
            registered,
            source_id,
            market_date,
            question=question,
            evidence_matrix=evidence_matrix,
            relationship_graph=relationship_graph,
            evolution=evolution,
            execution_implications=execution_implications,
            conclusion_changes=conclusion_changes,
        )
        if len(figure_ids) < 2:
            self.limitations.append(f"{selected.name} cleared the score threshold but the Research Focus was omitted because fewer than two substantial figures were supportable.")
            self.research_selection = result.decision.model_copy(update={
                "selected_candidate_id": None,
                "secondary_candidate_id": None,
                "no_selection_reason": "No standalone research subject met the evidence and materiality threshold for this report.",
                "missing_evidence": sorted(set([*result.decision.missing_evidence, "fewer_than_two_supported_figures"])),
            })
            self.research_inquiry = ResearchInquiry(
                status="no_focus",
                question="Why did no reviewed subject meet the research evidence threshold?",
                executive_answer="The leading candidate cleared the score threshold but could not support two substantial evidence figures, so standalone coverage was withheld.",
                evidence_ids=selected.evidence_ids[:8],
            )
            return
        prose = research_focus_prose(selected, result.decision)
        affected = self._saved_security_impacts(selected)
        limitations = list(selected.score.missing_dimensions)
        if selected.mapping_type != "validated_supply_chain":
            limitations.append("The relationship diagram shows validated taxonomy or membership links, not supplier/customer flows.")
        if selected.participation is None:
            limitations.append("A distinct participation measure is unavailable; breadth is not reused as a substitute.")
        relationship_evidence = [item for edge in relationship_graph.edges for item in edge.evidence_ids]
        signal_evidence = [item for signal in [*leading, *lagging] for item in signal.evidence_ids]
        focus_evidence = list(dict.fromkeys([*selected.evidence_ids, *relationship_evidence, *signal_evidence]))
        self.research_inquiry = ResearchInquiry(
            status="qualified",
            question=question,
            executive_answer=executive_answer,
            evidence_ids=selected.evidence_ids[:12],
        )
        self.research_focus = ResearchFocus(
            candidate_id=selected.candidate_id,
            subject=selected.name,
            category=selected.category,
            direction=selected.direction,
            priority_score=selected.score.total,
            classification_label=selected.direction.replace("_", " ").title(),
            user_relevance=selected.user_relevance,
            main_thesis=executive_answer,
            counter_thesis=prose["counter_thesis"],
            why_selected=result.decision.selected_because,
            key_evidence=prose["key_evidence"],
            confirmation_conditions=prose["confirmation_conditions"],
            invalidation_conditions=prose["invalidation_conditions"],
            prose_sections=prose["sections"],
            figure_ids=figure_ids,
            affected_securities=affected,
            taxonomy_chain=selected.taxonomy_chain,
            evidence_ids=focus_evidence,
            limitations=limitations,
            question=question,
            executive_answer=executive_answer,
            evidence_quality=evidence_quality,
            evidence_matrix=evidence_matrix,
            relationship_graph=relationship_graph,
            leading_securities=leading,
            lagging_securities=lagging,
            execution_implications=execution_implications,
            conclusion_change_conditions=conclusion_changes,
            research_evolution=evolution,
        )
        secondary = next((item for item in registered if item.candidate_id == result.decision.secondary_candidate_id), None)
        if secondary:
            self.secondary_research_note = SecondaryResearchNote(
                candidate_id=secondary.candidate_id,
                subject=secondary.name,
                direction=secondary.direction,
                summary=secondary_research_summary(secondary, selected),
                evidence_ids=secondary.evidence_ids,
            )

    def _research_source(self, category: str, market_date: str) -> str:
        if category == "theme":
            context = self.report.get("theme_intelligence") or {}
            return self._source("research-theme", str(context.get("source_state") or "Internal theme engine"), f"Frozen ThemeSnapshot {context.get('snapshot_id') or ''}".strip(), str(context.get("market_date") or market_date), "immutable_snapshot")
        if category == "sector":
            dashboard = self.report.get("sector_dashboard") or {}
            return self._source("research-sector", str(dashboard.get("source") or "Internal sector engine"), f"Frozen SectorSnapshot {dashboard.get('snapshot_id') or ''}".strip(), str(dashboard.get("market_date") or market_date), "immutable_snapshot")
        return self._source("research-watchlist", "Internal watchlist and stock snapshots", "Frozen saved-security research input", market_date, "immutable_snapshot")

    def _build_no_focus_research_figure(self, candidates: list[Any], market_date: str) -> None:
        if not candidates:
            return
        threshold_id = self._evidence(
            "research-materiality-threshold",
            "Research Focus materiality threshold",
            candidates[0].score.materiality_threshold,
            "score",
            "V7 selection policy",
            "report",
            market_date,
        )
        points = [
            {
                "label": candidate.name,
                "value": candidate.score.total,
                "direction": candidate.direction,
                "selected": False,
                "failed_gates": candidate.disqualifying_conditions[:3],
            }
            for candidate in candidates[:8]
        ]
        self.figures.append(FigureSpec(
            figure_id="research-priority-comparison",
            title="Research Priority Tree",
            subtitle="Reviewed candidates and the standalone-coverage gate",
            question_answered="Why did no candidate qualify for standalone research?",
            chart_type="research_priority_tree",
            timeframe="Current report",
            data_series=[FigureSeries(
                series_id="research-priority",
                label="Research Priority Score",
                unit="score",
                points=points,
                source_id="report",
                transformation="documented V7 fixed-weight score and qualification gates",
            )],
            reference_lines=[{
                "label": "Materiality threshold",
                "value": candidates[0].score.materiality_threshold,
                "evidence_id": threshold_id,
                "freshness": "current",
            }] if threshold_id else [],
            source_ids=["report"],
            as_of=market_date,
            observation=f"{len(points)} reviewed candidates are shown; none passed every qualification gate.",
            interpretation="A score is necessary but not sufficient: freshness, completeness, constituent coverage, and figure readiness can withhold standalone coverage.",
            confirmation_condition="A candidate must clear the score threshold and every evidence gate on a compatible report.",
            risk_condition="Promoting a subject with stale, incomplete, or non-visual evidence would overstate the research conclusion.",
            quality=self._data_quality("report", len(points), max(1, len(candidates)), "deterministic selection gate"),
        ))

    def _research_evidence_quality(self, selected: Any) -> ResearchEvidenceQuality:
        prefix = selected.candidate_id.replace(":", "-")
        source_id = self._research_source(selected.category, selected.freshness)
        freshness_score = selected.score.dimension_scores.get("freshness")
        breadth_score = selected.score.dimension_scores.get("breadth_confirmation")
        participation_score = directional_confirmation_score(selected.direction, selected.participation)
        completeness_score = selected.data_completeness * 100
        consistency_score = research_consistency_score(selected)
        participation_evidence_id = candidate_evidence_id(selected, "participation")
        if not participation_evidence_id:
            participation_evidence_id = self._evidence(
                f"research-{prefix}-participation-status",
                f"{selected.name} distinct participation evidence status",
                "Unavailable",
                "status",
                "current research input",
                source_id,
                selected.freshness,
            )
        consistency_evidence_id = self._evidence(
            f"research-{prefix}-directional-consistency",
            f"{selected.name} directional evidence consistency",
            consistency_score,
            "score",
            "current research input",
            source_id,
            selected.freshness,
        )
        grades = {
            "freshness": evidence_grade(freshness_score),
            "breadth": evidence_grade(breadth_score),
            "participation": evidence_grade(participation_score),
            "completeness": evidence_grade(completeness_score),
            "consistency": evidence_grade(consistency_score),
        }
        high_count = sum(value == "High" for value in grades.values())
        low_count = sum(value == "Low" for value in grades.values())
        label = "High" if high_count >= 4 and low_count == 0 else "Low" if low_count >= 2 else "Medium"
        evidence_ids = [
            candidate_evidence_id(selected, "contribution-freshness"),
            candidate_evidence_id(selected, "breadth") or candidate_evidence_id(selected, "contribution-breadth-confirmation"),
            participation_evidence_id,
            candidate_evidence_id(selected, "coverage"),
            consistency_evidence_id,
        ]
        return ResearchEvidenceQuality(
            label=label,
            freshness=grades["freshness"],
            breadth=grades["breadth"],
            participation=grades["participation"],
            completeness=grades["completeness"],
            consistency=grades["consistency"],
            rationale=[
                f"Freshness is {grades['freshness'].lower()} from the frozen {selected.freshness} subject input.",
                f"Breadth is {grades['breadth'].lower()} relative to the selected {selected.direction} direction.",
                "Participation is unavailable and is not replaced by breadth." if selected.participation is None else f"Participation is {grades['participation'].lower()} from a distinct constituent measure.",
                f"Completeness is {grades['completeness'].lower()} at {selected.data_completeness:.0%} of required candidate inputs.",
                f"Directional consistency is {grades['consistency'].lower()} across returns, relative strength, breadth, and available participation.",
            ],
            evidence_ids=[item for item in evidence_ids if item],
        )

    def _research_evidence_matrix(self, selected: Any) -> list[EvidenceMatrixRow]:
        positive = selected.direction in {"leading", "emerging"}
        direction_word = "positive" if positive else "negative" if selected.direction in {"weakening", "lagging", "breakdown"} else "divergent"
        relative_score = selected.score.dimension_scores.get("relative_divergence")
        persistence_score = selected.score.dimension_scores.get("persistence")
        breadth_score = selected.score.dimension_scores.get("breadth_confirmation")
        change_score = selected.score.dimension_scores.get("change_acceleration")
        volume_score = selected.score.dimension_scores.get("volume_confirmation")
        rows = [
            EvidenceMatrixRow(
                dimension="Relative performance",
                finding=f"One-month benchmark-relative evidence is {metric_text(selected.current_relative_strength, ' points')} and is evaluated in the {direction_word} thesis direction.",
                stance=evidence_stance(relative_score),
                implication="Separation from the benchmark determines whether the signal is more than broad-market beta.",
                evidence_ids=[candidate_evidence_id(selected, "relative-strength") or candidate_evidence_id(selected, "contribution-relative-divergence")],
            ),
            EvidenceMatrixRow(
                dimension="Persistence",
                finding=f"The supported 1W/1M/3M profile produces a directional-persistence reading of {metric_text(selected.persistence, '%')}.",
                stance=evidence_stance(persistence_score),
                implication="Cross-horizon agreement supports durability; disagreement identifies an emerging or fading move.",
                evidence_ids=[candidate_evidence_id(selected, "contribution-persistence")],
            ),
            EvidenceMatrixRow(
                dimension="Breadth",
                finding=f"Constituent breadth is {metric_text(selected.breadth, '%')}; the directional confirmation score is {metric_text(breadth_score, '')}.",
                stance=evidence_stance(breadth_score),
                implication="Participation by more constituents reduces concentration risk; narrow breadth limits conviction.",
                evidence_ids=[candidate_evidence_id(selected, "breadth") or candidate_evidence_id(selected, "contribution-breadth-confirmation")],
            ),
            EvidenceMatrixRow(
                dimension="Change and acceleration",
                finding=f"Rank, relative-strength, breadth, and classification changes produce an acceleration reading of {metric_text(change_score, '')}.",
                stance=evidence_stance(change_score),
                implication="A changing signal deserves more research attention than a static trailing rank.",
                evidence_ids=[candidate_evidence_id(selected, "contribution-change-acceleration")],
            ),
            EvidenceMatrixRow(
                dimension="Volume participation",
                finding="No distinct group-level volume confirmation is available." if volume_score is None else f"The supported volume-confirmation reading is {metric_text(volume_score, '')}.",
                stance="neutral" if volume_score is None else evidence_stance(volume_score),
                implication="Missing volume cannot confirm the thesis and contributes zero to priority scoring.",
                evidence_ids=[candidate_evidence_id(selected, "contribution-volume-confirmation")],
            ),
            EvidenceMatrixRow(
                dimension="User relevance",
                finding=f"Personal relevance is {selected.user_relevance.tier}; {len(selected.user_relevance.saved_security_symbols)} saved securities have validated overlap.",
                stance="neutral",
                implication="Personalization changes research priority, not the underlying market conclusion.",
                evidence_ids=[candidate_evidence_id(selected, "contribution-user-relevance")],
            ),
        ]
        return rows

    def _research_relationship_graph(self, selected: Any, source_id: str, market_date: str) -> ResearchRelationshipGraph:
        nodes: dict[str, ResearchRelationshipNode] = {}
        edges: list[ResearchRelationshipEdge] = []
        focus_id = f"focus:{normalize_graph_id(selected.name)}"
        focus_type = "security" if selected.category == "individual_security" else selected.category
        nodes[focus_id] = ResearchRelationshipNode(node_id=focus_id, label=selected.name, node_type=focus_type, depth=2 if selected.category == "theme" else 1)

        def add_node(node_id: str, label: str, node_type: str, depth: int) -> None:
            if node_id not in nodes:
                nodes[node_id] = ResearchRelationshipNode(node_id=node_id, label=label, node_type=node_type, depth=depth)

        def add_edge(source: str, target: str, relationship_type: str, label: str, mapping_source: str, *, structured: bool = False) -> None:
            identifier = f"relationship-{normalize_graph_id(source)}-{normalize_graph_id(target)}-{relationship_type}"
            if any(item.relationship_id == identifier for item in edges):
                return
            evidence_id = self._evidence(
                f"research-{selected.candidate_id.replace(':', '-')}-{identifier}",
                f"Validated relationship: {nodes[source].label} to {nodes[target].label}",
                relationship_type,
                "mapping",
                "current validated relationship graph",
                source_id,
                market_date,
            )
            if evidence_id:
                edges.append(ResearchRelationshipEdge(
                    relationship_id=identifier,
                    source_node_id=source,
                    target_node_id=target,
                    relationship_type=relationship_type,
                    label=label,
                    mapping_source=mapping_source,
                    structured_data=structured,
                    evidence_ids=[evidence_id],
                ))

        if selected.category != "individual_security" and selected.current_relative_strength is not None:
            add_node("benchmark:spy", "SPY benchmark", "benchmark", 0)
            add_edge("benchmark:spy", focus_id, "benchmark_relationship", "1M relative performance", "frozen benchmark-relative metric")

        members = [item for item in selected.constituents if isinstance(item, dict) and item.get("ticker")]
        if selected.category == "theme":
            sectors = sorted({str(item.get("sector")) for item in members if item.get("sector")})
            if not sectors:
                sectors = [str(item.get("name")) for item in selected.taxonomy_chain if str(item.get("level")).lower() == "sector"]
            for sector in sectors[:3]:
                sector_id = f"sector:{normalize_graph_id(sector)}"
                add_node(sector_id, sector, "sector", 1)
                add_edge(sector_id, focus_id, "theme_hierarchy", "validated parent theme", "reviewed theme definition")
        elif selected.category == "individual_security":
            member = members[0] if members else {}
            sector = str(member.get("sector") or "").strip()
            industry = str(member.get("industry") or "").strip()
            parent_id = None
            if sector:
                parent_id = f"sector:{normalize_graph_id(sector)}"
                add_node(parent_id, sector, "sector", 0)
            if industry:
                industry_id = f"industry:{normalize_graph_id(industry)}"
                add_node(industry_id, industry, "industry", 1)
                if parent_id:
                    add_edge(parent_id, industry_id, "sector_hierarchy", "validated sector hierarchy", "security master")
                parent_id = industry_id
            if parent_id:
                add_edge(parent_id, focus_id, "validated_taxonomy", "validated security membership", "security master")

        industry_nodes: dict[str, str] = {}
        for member in ([] if selected.category == "individual_security" else members[:10]):
            symbol = str(member.get("ticker")).upper()
            security_id = f"security:{symbol.lower()}"
            security_depth = 4 if selected.category == "theme" else 3 if selected.category == "sector" else 1
            add_node(security_id, symbol, "security", security_depth)
            industry = str(member.get("industry") or "").strip()
            if industry and selected.category != "individual_security":
                industry_id = f"industry:{normalize_graph_id(industry)}"
                industry_nodes[industry] = industry_id
                add_node(industry_id, industry, "industry", security_depth - 1)
                hierarchy = "sector_hierarchy" if selected.category == "sector" else "validated_taxonomy"
                add_edge(focus_id, industry_id, hierarchy, "validated industry membership", "security master")
                add_edge(industry_id, security_id, "validated_taxonomy", "validated security membership", "security master")
            elif selected.category != "individual_security":
                hierarchy = "theme_hierarchy" if selected.category == "theme" else "sector_hierarchy"
                add_edge(focus_id, security_id, hierarchy, "validated member", selected.mapping_type)

        saved_symbols = set(selected.user_relevance.saved_security_symbols)
        if saved_symbols:
            watch_depth = max((node.depth for node in nodes.values()), default=3) + 1
            add_node("watchlist:saved", "User Saved Stocks", "watchlist", min(8, watch_depth))
            for symbol in sorted(saved_symbols):
                security_id = focus_id if selected.category == "individual_security" and symbol == selected.name.upper() else f"security:{symbol.lower()}"
                if security_id in nodes:
                    add_edge(security_id, "watchlist:saved", "user_watchlist_overlap", "saved watchlist overlap", "frozen research preferences")

        for mapping in self.report.get("validated_relationships") or []:
            if not isinstance(mapping, dict) or mapping.get("relationship_type") != "validated_supply_chain":
                continue
            if not mapping.get("structured_data") or not mapping.get("mapping_source"):
                continue
            source_symbol = str(mapping.get("source_symbol") or "").upper()
            target_symbol = str(mapping.get("target_symbol") or "").upper()
            source_node = f"security:{source_symbol.lower()}"
            target_node = f"security:{target_symbol.lower()}"
            if source_node in nodes and target_node in nodes:
                add_edge(source_node, target_node, "validated_supply_chain", str(mapping.get("label") or "validated supply-chain mapping"), str(mapping["mapping_source"]), structured=True)

        return ResearchRelationshipGraph(nodes=list(nodes.values()), edges=edges)

    def _research_security_leadership(self, selected: Any, source_id: str, market_date: str) -> tuple[list[ResearchSecuritySignal], list[ResearchSecuritySignal]]:
        saved = set(selected.user_relevance.saved_security_symbols)
        observations: list[tuple[str, float, str, str]] = []
        for member in selected.constituents:
            if not isinstance(member, dict) or not member.get("ticker"):
                continue
            symbol = str(member.get("ticker")).upper()
            value = number(member.get("return_1m"))
            metric_label = "1M return"
            timeframe = "1 month"
            if value is None:
                watch = next((item for item in (self.report.get("watchlist_summary") or {}).get("items") or [] if str(item.get("symbol") or item.get("ticker") or "").upper() == symbol), None)
                value = number((watch or {}).get("rs_rank"))
                metric_label = "RS rank"
                timeframe = "current stock snapshot"
            if value is not None:
                observations.append((symbol, value, metric_label, timeframe))
        if not observations and selected.category == "individual_security":
            value = selected.returns.get("1d") if selected.returns.get("1d") is not None else selected.current_relative_strength
            if value is not None:
                observations.append((selected.name.upper(), float(value), "Daily change" if selected.returns.get("1d") is not None else "RS rank", "latest session"))
        observations.sort(key=lambda item: (-item[1], item[0]))
        if not observations:
            return [], []
        group_size = min(3, max(1, len(observations) // 2))
        leader_rows = observations[:group_size]
        laggard_rows = [item for item in reversed(observations[-group_size:]) if item[0] not in {row[0] for row in leader_rows}]

        def build_signal(row: tuple[str, float, str, str], role: str) -> ResearchSecuritySignal:
            symbol, value, metric_label, timeframe = row
            evidence_id = self._evidence(
                f"research-{selected.candidate_id.replace(':', '-')}-{symbol.lower()}-{normalize_graph_id(metric_label)}",
                f"{symbol} {metric_label.lower()} within {selected.name}",
                value,
                "percent" if "return" in metric_label.lower() else "rank",
                timeframe,
                source_id,
                market_date,
            )
            return ResearchSecuritySignal(
                symbol=symbol,
                role=role,
                metric_label=metric_label,
                metric_value=value,
                timeframe=timeframe,
                reason=f"{symbol} is a relative {role} within the supported {selected.name} constituent evidence; this is not a standalone recommendation.",
                saved=symbol in saved,
                evidence_ids=[evidence_id] if evidence_id else [],
            )

        return (
            [build_signal(row, "leader") for row in leader_rows],
            [build_signal(row, "laggard") for row in laggard_rows],
        )

    def _research_evolution(self, selected: Any) -> ResearchEvolution:
        previous_date = str((self.previous_snapshot or {}).get("marketDate") or (self.previous_snapshot or {}).get("market_date") or "") or None
        previous_focus = str((self.previous_snapshot or {}).get("researchFocus") or (self.previous_snapshot or {}).get("research_focus") or "") or None
        timeline_date, timeline_focus = self._prior_timeline_focus()
        previous_date = previous_date or timeline_date
        previous_focus = previous_focus or timeline_focus
        prior_state = previous_candidate_state(self.previous_snapshot or {}, selected)
        no_new_session = is_non_session_report(self.report, selected.freshness)
        yesterday = prior_state or (
            f"The previous compatible report focused on {previous_focus}; comparable candidate-state fields are unavailable."
            if previous_focus
            else "No compatible prior research observation is available."
            if self.previous_snapshot
            else "First report; no prior research observation exists."
        )
        today = (
            f"No new market session: the latest durable {selected.freshness} evidence still classifies {selected.name} as {selected.direction}."
            if no_new_session
            else f"{selected.name} is {selected.direction} with priority {selected.score.total:.1f}, relative strength {metric_text(selected.current_relative_strength, ' points')}, and breadth {metric_text(selected.breadth, '%')}."
        )
        changes = []
        if selected.rank_change is not None:
            changes.append(f"rank {selected.rank_change:+d}")
        if selected.relative_strength_change is not None:
            changes.append(f"relative strength {selected.relative_strength_change:+.1f} points")
        if selected.breadth_change is not None:
            changes.append(f"breadth {selected.breadth_change:+.1f} points")
        what_changed = "; ".join(changes) if changes else "No compatible change fields are available; the current observation is treated as a baseline."
        next_test = stage6_next_evidence_test(selected)
        current_focus = selected.name
        status = "New baseline"
        if previous_focus and normalize_graph_id(previous_focus) != normalize_graph_id(current_focus):
            status = "Focus changed"
        elif prior_state or previous_focus:
            status = "Follow-up"
        return ResearchEvolution(
            previous_report_date=previous_date,
            yesterday=yesterday,
            today=today,
            tomorrow=f"Next test: {next_test}",
            what_changed=what_changed,
            research_follow_up=f"Re-run the same evidence gates on the next compatible snapshot; retain {selected.name} only while direction, breadth, and relative performance remain aligned.",
            previous_focus=previous_focus,
            current_focus=current_focus,
            status=status,
            evidence_ids=selected.evidence_ids[:12],
        )

    def _prior_timeline_focus(self) -> tuple[str | None, str | None]:
        """Return the latest explicit pre-current focus from compatible report history."""
        evolution = self.report.get("market_evolution") or {}
        points = evolution.get("points") or evolution.get("history") or []
        if not isinstance(points, list):
            return None, None
        current_market_date = str(self.report.get("market_date") or self.report.get("date") or "")[:10]
        result: tuple[str | None, str | None] = (None, None)
        for item in points:
            if not isinstance(item, dict):
                continue
            point_date = str(item.get("marketDate") or item.get("market_date") or item.get("date") or "")[:10]
            point_focus = str(item.get("researchFocus") or item.get("research_focus") or "").strip()
            if not point_date or not point_focus or point_date >= current_market_date:
                continue
            result = (point_date, point_focus)
        return result

    def _build_research_figures(
        self,
        selected: Any,
        candidates: list[Any],
        source_id: str,
        market_date: str,
        *,
        question: str,
        evidence_matrix: list[EvidenceMatrixRow],
        relationship_graph: ResearchRelationshipGraph,
        evolution: ResearchEvolution,
        execution_implications: list[str],
        conclusion_changes: list[str],
    ) -> list[str]:
        figure_ids: list[str] = []
        threshold_evidence_id = self._evidence(
            "research-materiality-threshold", "Research Focus materiality threshold",
            selected.score.materiality_threshold, "score", "V7 selection policy", source_id, market_date,
        ) or "research-materiality-threshold"
        priority_id = "research-priority-comparison"
        priority_points = [
            {"label": item.name, "value": item.score.total, "direction": item.direction, "selected": item.candidate_id == selected.candidate_id}
            for item in candidates[:8]
        ]
        if priority_points:
            self.figures.append(FigureSpec(
                figure_id=priority_id, title="Research Priority Tree", subtitle="Fixed-weight materiality score across deterministic candidates",
                question_answered="Why did this subject outrank competing research candidates?", chart_type="research_priority_tree", timeframe="Current report",
                data_series=[FigureSeries(series_id="research-priority", label="Research Priority Score", unit="score", points=priority_points, source_id=source_id, transformation="documented V7 fixed-weight score")],
                reference_lines=[{"label": "Materiality threshold", "value": selected.score.materiality_threshold, "evidence_id": threshold_evidence_id, "freshness": "current"}],
                source_ids=[source_id], as_of=market_date,
                observation=f"{selected.name} ranks first among qualified candidates at {selected.score.total:.1f}.",
                interpretation="The comparison combines market significance, directional magnitude, change, persistence, participation, divergence, user relevance, completeness and freshness; missing volume contributes zero rather than a synthetic confirmation.",
                confirmation_condition="The subject remains above the materiality threshold as its market and participation evidence persists.",
                risk_condition="A lower score or a freshness, completeness, constituent, or figure gate failure removes the standalone focus.",
                quality=DataQualityState(state=selected.source_quality, completeness=selected.data_completeness, freshness=selected.freshness, transformation="fixed-weight deterministic research score", warnings=selected.score.missing_dimensions),
            ))
            figure_ids.append(priority_id)

        # Individual-security structure is rendered once in the selected-security
        # mini report. Keeping it out of Research Focus avoids duplicating the
        # same price evidence in two sections.
        if selected.category != "individual_security":
            profile_points = [
                {"label": period.upper(), "value": selected.returns.get(period)}
                for period in ("1w", "1m", "3m", "6m", "1y")
                if selected.returns.get(period) is not None
            ]
            if selected.current_relative_strength is not None:
                profile_points.append({"label": "VS SPY 1M", "value": selected.current_relative_strength, "kind": "benchmark_relative"})
            if len(profile_points) >= 2:
                figure_id = "research-subject-return-profile"
                self.figures.append(FigureSpec(
                    figure_id=figure_id, title=f"{selected.name} Relative Strength Flow", subtitle="Multi-period returns plus the supported one-month benchmark-relative reading",
                    question_answered="Is the subject's direction recent, persistent, and distinct from the benchmark?", chart_type="relative_strength_flow", timeframe="1 week to 1 year",
                    data_series=[FigureSeries(series_id="subject-returns", label=selected.name, unit="percent / percentage points", points=profile_points, source_id=source_id, transformation="frozen snapshot return and benchmark-relative fields")],
                    source_ids=[source_id], as_of=selected.freshness,
                    observation=f"{selected.name} has {len(profile_points)} supported return horizons for persistence review.",
                    interpretation="Agreement across horizons supports persistence; disagreement identifies an emerging, fading, or unstable move.",
                    confirmation_condition="The next snapshot preserves directional agreement and market-relative strength.",
                    risk_condition="Short-horizon reversal followed by weaker medium-horizon evidence would reduce persistence.",
                    quality=DataQualityState(state=selected.source_quality, completeness=min(1, len(profile_points) / 5), freshness=selected.freshness, transformation="frozen multi-period returns"),
                ))
                figure_ids.append(figure_id)

        if relationship_graph.nodes and relationship_graph.edges:
            figure_id = "research-chain"
            relationship_chart_type = "sector_influence_map" if selected.category == "sector" else "research_chain"
            relationship_title = "Sector Influence Map" if selected.category == "sector" else "Research Chain"
            self.figures.append(FigureSpec(
                figure_id=figure_id,
                title=relationship_title,
                subtitle="Branching map of benchmark, taxonomy, membership, and saved-watchlist relationships",
                question_answered="How does validated structure connect the research subject to industries, securities, and the user's saved list?",
                chart_type=relationship_chart_type,
                timeframe="Current validated mappings",
                data_series=[
                    FigureSeries(series_id="research-chain-nodes", label="Validated nodes", unit="relationship_nodes", points=[item.model_dump(mode="json") for item in relationship_graph.nodes], source_id=source_id, transformation="validated node registry"),
                    FigureSeries(series_id="research-chain-edges", label="Validated edges", unit="relationship_edges", points=[item.model_dump(mode="json") for item in relationship_graph.edges], source_id=source_id, transformation="typed relationship registry"),
                ],
                source_ids=[source_id],
                as_of=market_date,
                observation=f"{len(relationship_graph.nodes)} nodes are connected by {len(relationship_graph.edges)} explicit validated relationships.",
                interpretation="Arrows encode taxonomy, benchmark, membership, or saved-overlap relationships; they do not forecast price direction or imply causality.",
                confirmation_condition="The chain remains valid while the underlying taxonomy and saved-item mappings remain current.",
                risk_condition="Missing or unstructured mappings are omitted; supplier/customer links require a separate structured source.",
                quality=DataQualityState(state=selected.source_quality, completeness=1.0, freshness=selected.freshness, transformation="validated typed relationship graph"),
            ))
            figure_ids.append(figure_id)

        if evidence_matrix:
            figure_id = "research-evidence-matrix"
            self.figures.append(FigureSpec(
                figure_id=figure_id,
                title="Evidence Matrix",
                subtitle="Supports, neutral, and contradicts classification for the primary thesis",
                question_answered="Which evidence supports the answer, and where is confirmation incomplete?",
                chart_type="evidence_matrix",
                timeframe="Current report",
                data_series=[FigureSeries(series_id="research-evidence-matrix", label="Evidence classification", unit="evidence_matrix", points=[item.model_dump(mode="json") for item in evidence_matrix], source_id=source_id, transformation="deterministic stance classification")],
                source_ids=[source_id], as_of=market_date,
                observation=f"{len(evidence_matrix)} evidence dimensions are classified against the thesis.",
                interpretation="Neutral evidence is not treated as support, and missing observations are not converted into synthetic confirmation.",
                confirmation_condition="More dimensions move to Supports through fresh, directionally consistent evidence.",
                risk_condition="Contradictory breadth, persistence, or benchmark-relative evidence would weaken the answer.",
                quality=DataQualityState(state=selected.source_quality, completeness=selected.data_completeness, freshness=selected.freshness, transformation="evidence-to-thesis stance matrix", warnings=selected.score.missing_dimensions),
            ))
            figure_ids.append(figure_id)

        figure_id = "research-decision-framework"
        decision_points = [
            {"stage": "Yesterday", "text": evolution.yesterday, "tone": "neutral"},
            {"stage": "Today", "text": evolution.today, "tone": "current"},
            {"stage": "Next test", "text": evolution.tomorrow, "tone": "confirmation"},
            {"stage": "Execution", "text": execution_implications[0], "tone": "execution"},
            {"stage": "Change conclusion", "text": conclusion_changes[0], "tone": "risk"},
        ]
        self.figures.append(FigureSpec(
            figure_id=figure_id,
            title="Research Evolution and Decision Framework",
            subtitle="Yesterday to today, then the evidence test that governs the next update",
            question_answered="What changed, what should be monitored, and what changes the conclusion?",
            chart_type="decision_framework",
            timeframe="Previous report to next compatible observation",
            data_series=[FigureSeries(series_id="research-decision", label="Research journal", unit="decision_framework", points=decision_points, source_id=source_id, transformation="evidence-linked research continuity")],
            source_ids=[source_id], as_of=market_date,
            observation=evolution.what_changed,
            interpretation="The next step is framed as an evidence test, not a price forecast.",
            confirmation_condition=conclusion_changes[1] if len(conclusion_changes) > 1 else conclusion_changes[0],
            risk_condition="A contradictory compatible snapshot would trigger the explicit change-conclusion rule shown above.",
            quality=DataQualityState(state=selected.source_quality, completeness=selected.data_completeness, freshness=selected.freshness, transformation="compatible research evolution"),
        ))
        figure_ids.append(figure_id)
        return figure_ids

    def _saved_security_impacts(self, selected: Any) -> list[SavedSecurityImpact]:
        impacts: list[SavedSecurityImpact] = []
        source_id = self._research_source(selected.category, selected.freshness)
        charts = {
            str(item.get("symbol") or item.get("ticker") or "").upper(): item
            for item in self.report.get("stock_charts") or [] if isinstance(item, dict)
        }
        for symbol in selected.user_relevance.saved_security_symbols:
            item = next((row for row in (self.report.get("watchlist_summary") or {}).get("items") or [] if str(row.get("symbol") or row.get("ticker") or "").upper() == symbol), {})
            chart = charts.get(symbol) or {}
            score = number(item.get("overall_score"))
            status = str(item.get("setup") or item.get("signal") or item.get("overall_status") or "Monitoring")
            if selected.direction in {"leading", "emerging"}:
                relation = "Confirms group leadership" if score is not None and score >= 60 else "Lags its group"
            else:
                relation = "Breaking down with the group" if score is not None and score < 45 else "Diverging positively"
            level = number(chart.get("support")) or number(chart.get("resistance")) or number(chart.get("breakout"))
            impact_evidence_ids = list(selected.evidence_ids)
            if level is not None:
                level_evidence_id = self._evidence(
                    f"research-{selected.candidate_id.replace(':', '-')}-saved-{symbol.lower()}-key-level",
                    f"{symbol} Research Focus key level",
                    level,
                    "price",
                    "latest frozen daily chart",
                    source_id,
                    str(item.get("analysis_updated_at") or item.get("as_of") or selected.freshness),
                )
                if level_evidence_id:
                    impact_evidence_ids.append(level_evidence_id)
            impacts.append(SavedSecurityImpact(
                symbol=symbol,
                group=selected.name,
                setup_state=status,
                relative_strength=item.get("rs_rank") or item.get("rs_status"),
                trend=str(item.get("trend") or item.get("rating") or "Data insufficient"),
                volume_condition=str(item.get("volume_condition") or "No validated group-level volume field"),
                key_level=format_price(level) if level is not None else "No validated level",
                change_since_previous="Current saved-security snapshot; compatible prior status is unavailable." if not self.previous_snapshot else "See the compatible previous-report status comparison.",
                relation_to_focus=relation,
                freshness=str(item.get("analysis_updated_at") or item.get("as_of") or item.get("source_state") or "unknown"),
                reason_to_monitor=f"{symbol} has validated membership in {selected.name} and is saved on the user's watchlist.",
                evidence_ids=impact_evidence_ids,
            ))
        return impacts

    def _build_macro_figure(self, market_date: str) -> None:
        symbols = (("SPY", "Equities"), ("IEF", "Treasury bond proxy"), ("GLD", "Gold"), ("USO", "Oil"), ("UUP", "US Dollar"), ("HYG", "High-yield credit proxy"))
        histories = {symbol: self._bars(symbol, market_date)[-126:] for symbol, _ in symbols}
        eligible = {symbol: bars for symbol, bars in histories.items() if len(bars) >= 20}
        if len(eligible) < 2:
            self.limitations.append("Normalized cross-asset proxy figure omitted because fewer than two durable series qualify.")
            return
        common_dates = sorted(set.intersection(*(set(bar.session_date for bar in bars) for bars in eligible.values())))
        if len(common_dates) < 20:
            self.limitations.append("Normalized cross-asset proxy figure omitted because aligned history is insufficient.")
            return
        common_dates = common_dates[-126:]
        series = []
        source_ids = []
        labels = dict(symbols)
        for symbol, bars in eligible.items():
            by_date = {bar.session_date: bar.close for bar in bars}
            base = by_date[common_dates[0]]
            values = [100 * by_date[date] / base for date in common_dates]
            source_id = self._bar_source(symbol, bars)
            source_ids.append(source_id)
            series.append(self._series(f"macro-{symbol.lower()}", labels[symbol], "index (start=100)", common_dates, values, source_id, transformation="rebased adjusted close"))
        self.figures.append(FigureSpec(figure_id="macro-normalized", title="Cross-Asset Proxy Confirmation", subtitle="Adjusted ETF prices normalized to 100; bond and credit instruments are price proxies", question_answered="Do supported cross-asset proxies confirm the equity risk posture?", chart_type="normalized_multi_asset", timeframe=f"{len(common_dates)} shared sessions", data_series=series, source_ids=sorted(set(source_ids)), as_of=common_dates[-1], observation="The figure compares direction across supported equity, bond, dollar, commodity, and credit price proxies.", interpretation="Agreement can support the risk posture; disagreement is counter-evidence. The chart does not provide direct yields or credit spreads.", confirmation_condition="Equities and the high-yield proxy outperform defensive proxies on the same horizon.", risk_condition="Defensive proxies strengthen while equities and the high-yield proxy weaken.", quality=DataQualityState(state=self._quality(self._source_state()), completeness=min(1, len(common_dates) / 126), freshness="latest durable session", transformation="date-aligned adjusted closes rebased to 100", warnings=["IEF and HYG are price proxies, not direct yield or spread series"])))

    def _build_risk_figure(self, market_date: str) -> None:
        evolution = self.report.get("market_evolution") or {}
        points = evolution.get("history") or evolution.get("points") or evolution.get("series") or []
        if not isinstance(points, list) or len(points) < 2:
            self.limitations.append("Risk-history figure omitted because fewer than two compatible prior report observations are available.")
            return
        source_id = self._source("report-history", "Internal report storage", "Immutable prior daily report metrics", market_date, "report_history")
        fields = (("risk", "Risk score"), ("health", "Market health"), ("breadth", "Breadth"))
        series = []
        for field, label in fields:
            values = [{"date": item.get("marketDate") or item.get("date"), "value": item.get(field)} for item in points if number(item.get(field)) is not None]
            if values:
                series.append(FigureSeries(series_id=f"risk-{field}", label=label, unit="score", points=values, source_id=source_id, transformation="compatible report snapshots"))
        if series:
            self.figures.append(FigureSpec(figure_id="risk-history", title="Risk and Market-Health History", subtitle="Compatible immutable report observations", question_answered="Is the risk posture improving or deteriorating?", chart_type="risk_history", timeframe=f"{len(points)} reports", data_series=series, source_ids=[source_id], as_of=market_date, observation="The available history shows direction across compatible report-level risk measures.", interpretation="A shallow history is context, not a long-run distribution.", confirmation_condition="Improving health with stable or falling risk would confirm the posture.", risk_condition="Rising risk with falling health would weaken the thesis.", quality=self._data_quality(source_id, len(points), 10, "compatible prior-report metrics")))

    def _build_market_timeline(self, market_date: str) -> None:
        evolution = self.report.get("market_evolution") or {}
        points = evolution.get("points") or evolution.get("history") or []
        if not isinstance(points, list) or len(points) < 3:
            self.limitations.append("Market Evolution figure omitted because fewer than three compatible report observations are available.")
            return
        entries: list[MarketTimelineEntry] = []
        for item in points[-10:]:
            if not isinstance(item, dict):
                continue
            market_point_date = str(item.get("marketDate") or item.get("market_date") or item.get("date") or "")
            if not market_point_date:
                continue
            entries.append(MarketTimelineEntry(
                market_date=market_point_date,
                regime=item.get("regime"),
                market_health=number(item.get("health") or item.get("marketHealth")),
                breadth=number(item.get("breadth")),
                leadership_concentration=number(item.get("leadershipConcentration") or item.get("leadership_concentration")),
                risk=number(item.get("risk")),
                volatility_state=item.get("volatilityState") or item.get("volatility_state"),
                primary_leader=item.get("sectorLeader") or item.get("primaryLeader") or item.get("primary_leader"),
                primary_laggard=item.get("sectorLaggard") or item.get("primaryLaggard") or item.get("primary_laggard"),
                research_focus=(
                    (self.research_focus.subject if self.research_focus else "No standalone focus")
                    if market_point_date == market_date
                    else item.get("researchFocus") or item.get("research_focus")
                ),
            ))
        if len(entries) < 3:
            self.limitations.append("Market Evolution figure omitted because fewer than three dated compatible observations are available.")
            return
        self.market_timeline = entries
        if len(entries) < 10:
            self.limitations.append(f"Research Timeline contains {len(entries)} compatible reports; the remaining history is not backfilled or inferred.")
        source_id = self._source("market-evolution", "Internal report storage", "Compatible immutable report evolution", market_date, "report_history")
        self.figures.append(FigureSpec(
            figure_id="market-evolution", title="Research Timeline", subtitle="Regime, breadth, leadership, risk, volatility and research focus across compatible reports",
            question_answered="How has the market thesis and research priority evolved across the last ten compatible reports?", chart_type="research_timeline",
            timeframe=f"{len(entries)} reports", data_series=[FigureSeries(
                series_id="market-evolution", label="Market evolution", unit="timeline",
                points=[entry.model_dump(mode="json") for entry in entries], source_id=source_id,
                transformation="compatible immutable report metrics only",
            )], source_ids=[source_id], as_of=entries[-1].market_date,
            observation=f"{len(entries)} compatible report observations are available; unavailable fields remain blank.",
            interpretation="The timeline shows sequencing across supported market-state and research fields without filling missing history.",
            confirmation_condition="Improving health and breadth with contained risk would confirm a stronger market state.",
            risk_condition="Rising risk or deteriorating breadth ahead of index weakness would increase caution.",
            quality=self._data_quality(source_id, len(entries), 10, "compatible report timeline"),
        ))

    def _build_watchlist(self, market_date: str) -> None:
        summary = self.report.get("watchlist_summary") or {}
        items = [item for item in summary.get("items") or [] if isinstance(item, dict)]
        if not items:
            self.limitations.append("Security research is abbreviated because the frozen watchlist is empty.")
            return
        source_id = self._source("watchlist", "Internal watchlist and stock snapshots", "Frozen personalized watchlist research", market_date, "immutable_snapshot")
        rows = []
        selected_symbols = self._selected_security_symbols(items)
        previous_items = {
            str(item.get("symbol") or item.get("ticker") or "").upper(): item
            for item in (self.previous_snapshot or {}).get("watchlistSummary") or []
            if isinstance(item, dict)
        }
        for item in items:
            symbol = str(item.get("symbol") or item.get("ticker") or "").upper()
            if not symbol:
                continue
            freshness = str(item.get("source_state") or "unavailable").lower()
            partial = bool(item.get("missing_sections")) or freshness in {"stale", "partial", "unavailable", "test"}
            selected_for_research = symbol in selected_symbols
            change = number(item.get("change_percent"))
            score = number(item.get("overall_score"))
            relative_strength = number(item.get("rs_rank")) or item.get("rs_status")
            trend = str(item.get("trend") or item.get("rating") or item.get("overall_status") or "Data insufficient")
            group = self._security_group(symbol)
            previous_item = previous_items.get(symbol) or {}
            previous_setup = str(previous_item.get("mainSetup") or previous_item.get("setup") or previous_item.get("signal") or "")
            evidence_ids = [item_id for item_id in (
                self._evidence(f"watch-{symbol.lower()}-change", f"{symbol} daily change", change, "percent", "latest session", source_id, str(item.get("updated_at") or market_date), freshness=freshness),
                self._evidence(f"watch-{symbol.lower()}-score", f"{symbol} overall score", score, "score", "current stock snapshot", source_id, str(item.get("analysis_updated_at") or market_date), freshness=freshness),
            ) if item_id]
            setup = str(item.get("setup") or item.get("main_setup") or item.get("pattern") or "Monitoring")
            change_since_previous = f"Changed from {previous_setup}." if previous_setup and previous_setup != setup else "No compatible setup-state change." if previous_setup else "Baseline established."
            category = "Needs Review" if partial else "Developing"
            if not partial and str(item.get("signal") or "").lower() in {"buy", "bullish", "ready", "action_required"}:
                category = "Actionable / Ready"
            chart = next((chart for chart in self.report.get("stock_charts") or [] if str(chart.get("symbol") or "").upper() == symbol), None)
            figure_id = None
            confirmation = "Price and volume confirm the supported trigger while the market thesis remains valid."
            invalidation = "The supported price level fails or participation deteriorates."
            risk_considerations = "Stale or partial inputs must be reviewed before the setup can be actionable." if partial else "Size from the supported invalidation level and current market risk posture."
            volume_condition = "Volume history unavailable"
            confirmation_level = None
            invalidation_level = None
            if selected_for_research and chart and len(chart.get("price_history") or []) >= 30:
                figure_id = f"stock-{symbol.lower()}"
                chart_source = self._source(f"stock-{symbol.lower()}-history", str(chart.get("source") or "Internal market history"), f"{symbol} frozen stock chart history", str(chart.get("as_of") or market_date), "frozen_history")
                closes = [float(value) for value in chart.get("price_history") or [] if number(value) is not None]
                volumes = [float(value) for value in chart.get("volumes") or [] if number(value) is not None]
                if len(volumes) >= 20:
                    average_volume = sum(volumes[-20:]) / 20
                    volume_condition = f"{volumes[-1] / average_volume:.2f}x 20-session average" if average_volume > 0 else "Volume average unavailable"
                points = [{"index": index + 1, "value": value} for index, value in enumerate(closes)]
                data_series = [FigureSeries(series_id=f"{symbol}-close", label=symbol, unit="price", points=points, source_id=chart_source, transformation="frozen adjusted close history")]
                ema_annotations: list[FigureAnnotation] = []
                for window, color in ((20, "#00A6D6"), (50, "#7A5AF8")):
                    average_values = exponential_moving_average(closes, window)
                    if any(value is not None for value in average_values):
                        data_series.append(FigureSeries(series_id=f"{symbol}-ema{window}", label=f"EMA {window}", unit="price", points=[{"index": index + 1, "value": value} for index, value in enumerate(average_values)], source_id=chart_source, color=color, transformation=f"exponential moving average ({window} sessions)"))
                        latest_average = average_values[-1]
                        evidence_id = self._evidence(
                            f"watch-{symbol.lower()}-ema-{window}", f"{symbol} EMA {window}", latest_average,
                            "price", f"{window} observed sessions", chart_source, str(chart.get("as_of") or market_date), freshness=freshness,
                        )
                        if evidence_id and not partial and latest_average is not None:
                            ema_annotations.append(FigureAnnotation(
                                annotation_id=f"{symbol.lower()}-ema-{window}", annotation_type="ema",
                                label=f"EMA {window}", value=latest_average, point_index=len(closes) - 1,
                                evidence_id=evidence_id, freshness=freshness,
                            ))
                if len(volumes) == len(closes):
                    data_series.append(FigureSeries(series_id=f"{symbol}-volume", label="Volume", unit="shares", points=[{"index": index + 1, "value": value} for index, value in enumerate(volumes)], source_id=chart_source))
                levels = {
                    name: number(chart.get(name))
                    for name in ("support", "resistance", "breakout")
                }
                refs = []
                annotations: list[FigureAnnotation] = list(ema_annotations)
                for name, value in levels.items():
                    evidence_id = self._evidence(
                        f"watch-{symbol.lower()}-{name}",
                        f"{symbol} {name} level",
                        value,
                        "price",
                        "current stock snapshot",
                        chart_source,
                        str(chart.get("as_of") or market_date),
                        freshness=freshness,
                    )
                    if evidence_id:
                        evidence_ids.append(evidence_id)
                        if not partial:
                            refs.append({"label": name.title(), "value": value, "evidence_id": evidence_id, "freshness": freshness})
                            annotations.append(FigureAnnotation(
                                annotation_id=f"{symbol.lower()}-{name}", annotation_type=name,
                                label=name.title(), value=value, point_index=len(closes) - 1,
                                evidence_id=evidence_id, freshness=freshness,
                            ))

                trigger_name = "breakout" if levels["breakout"] is not None else "resistance"
                trigger = levels[trigger_name]
                support = levels["support"]
                confirmation_level = trigger
                invalidation_level = support
                if trigger is not None:
                    confirmation = f"Close above the supported {trigger_name} at {format_price(trigger)} with qualifying volume while the market thesis remains valid."
                if support is not None:
                    invalidation = f"Close below supported support at {format_price(support)}, or a material deterioration in participation."
                    if not partial:
                        risk_considerations = f"Reference risk to supported support at {format_price(support)} and the current market risk posture."

                if not partial and closes:
                    latest_close_id = self._evidence(
                        f"watch-{symbol.lower()}-latest-close",
                        f"{symbol} latest close and current thesis marker",
                        closes[-1], "price", "latest observed session", chart_source,
                        str(chart.get("as_of") or market_date), freshness=freshness,
                    )
                    if latest_close_id:
                        annotations.append(FigureAnnotation(
                            annotation_id=f"{symbol.lower()}-current-thesis", annotation_type="current_thesis",
                            label=f"Current thesis: {setup}", value=closes[-1], point_index=len(closes) - 1,
                            evidence_id=latest_close_id, freshness=freshness,
                        ))
                    if trigger is not None and closes[-1] >= trigger:
                        annotations.append(FigureAnnotation(
                            annotation_id=f"{symbol.lower()}-confirmation", annotation_type="confirmation",
                            label="Confirmed", value=closes[-1], point_index=len(closes) - 1,
                            evidence_id=latest_close_id, freshness=freshness,
                            detail=f"Latest close is above the supported {trigger_name} level.",
                        ))
                    if support is not None:
                        support_id = f"watch-{symbol.lower()}-support"
                        annotations.extend([
                            FigureAnnotation(
                                annotation_id=f"{symbol.lower()}-invalidation", annotation_type="invalidation",
                                label="Invalidation", value=support, point_index=len(closes) - 1,
                                evidence_id=support_id, freshness=freshness,
                            ),
                            FigureAnnotation(
                                annotation_id=f"{symbol.lower()}-risk", annotation_type="risk",
                                label="Risk level", value=support, point_index=len(closes) - 1,
                                evidence_id=support_id, freshness=freshness,
                            ),
                        ])
                    previous_price = number(chart.get("previous_report_price") or previous_item.get("close") or previous_item.get("price"))
                    if previous_price is not None:
                        previous_id = self._evidence(
                            f"watch-{symbol.lower()}-previous-report",
                            f"{symbol} previous report price marker", previous_price, "price", "previous compatible report",
                            chart_source, str((self.previous_snapshot or {}).get("marketDate") or market_date), freshness=freshness,
                        )
                        if previous_id:
                            annotations.append(FigureAnnotation(
                                annotation_id=f"{symbol.lower()}-previous-report", annotation_type="previous_report",
                                label="Previous report", value=previous_price,
                                point_index=max(0, len(closes) - 2), evidence_id=previous_id, freshness=freshness,
                            ))
                    supported_types = {"failed_breakout", "gap", "pivot", "trendline"}
                    for annotation_payload in chart.get("validated_annotations") or []:
                        if not isinstance(annotation_payload, dict):
                            continue
                        annotation_type = str(annotation_payload.get("annotation_type") or "").lower().replace(" ", "_")
                        annotation_value = number(annotation_payload.get("value"))
                        point_index = int(annotation_payload.get("point_index")) if number(annotation_payload.get("point_index")) is not None else len(closes) - 1
                        annotation_date = str(annotation_payload.get("date") or "")
                        if annotation_type not in supported_types or annotation_value is None or not 0 <= point_index < len(closes):
                            continue
                        if annotation_date and annotation_date[:10] > str(chart.get("as_of") or market_date)[:10]:
                            continue
                        annotation_id = self._evidence(
                            f"watch-{symbol.lower()}-{annotation_type}-{point_index}",
                            f"{symbol} validated {annotation_type.replace('_', ' ')} annotation",
                            annotation_value, "price", "observed chart history", chart_source,
                            str(chart.get("as_of") or market_date), freshness=freshness,
                        )
                        if annotation_id:
                            annotations.append(FigureAnnotation(
                                annotation_id=f"{symbol.lower()}-{annotation_type}-{point_index}",
                                annotation_type=annotation_type,
                                label=str(annotation_payload.get("label") or annotation_type.replace("_", " ").title()),
                                value=annotation_value,
                                point_index=point_index,
                                date=annotation_date or None,
                                evidence_id=annotation_id,
                                freshness=freshness,
                                detail=str(annotation_payload.get("detail")) if annotation_payload.get("detail") else None,
                            ))

                setup_interpretation = (
                    f"{setup} is eligible for action planning, but selection alone is not an entry and price-volume confirmation remains required."
                    if category == "Actionable / Ready"
                    else f"{setup} remains a monitoring classification and requires price and volume confirmation."
                )
                self.figures.append(FigureSpec(figure_id=figure_id, title=f"{symbol} Setup Structure", subtitle="Frozen daily price, volume and supported levels", question_answered=f"What confirms or invalidates the monitored {symbol} setup?", chart_type="stock_setup", timeframe=f"{len(closes)} observations", data_series=data_series, annotations=annotations, reference_lines=refs, source_ids=[chart_source], as_of=str(chart.get("as_of") or market_date), observation=str(chart.get("reason") or f"{symbol} has a qualified frozen setup history."), interpretation=setup_interpretation, confirmation_condition=confirmation, risk_condition=f"{invalidation} The setup also becomes monitoring-only if its inputs become stale.", quality=DataQualityState(state="partial" if partial else self._quality(freshness), completeness=min(1, len(closes) / 126), freshness=freshness, transformation="frozen stock chart plus snapshot levels", warnings=list(item.get("missing_sections") or []))))
            focus_relation = self._focus_relation(symbol, group)
            sector, themes = self._security_taxonomy_context(symbol)
            research_classification = focus_relation or ("Data insufficient" if partial else "Independent watchlist review")
            reason = "Included from the user's frozen watchlist and ranked stock evidence."
            if focus_relation:
                reason = f"Included because the saved security is linked to the {self.research_focus.subject} Research Focus through validated membership."
            elif selected_for_research:
                reason = "Selected for deeper research by fresh setup quality, material change, and watchlist priority."
            execution_consideration = (
                "Treat as monitoring-only until current price, volume, and level evidence is complete."
                if partial
                else "Selection alone is not an entry; require the supported price-volume confirmation and use the invalidation level to govern the research plan."
                if category == "Actionable / Ready"
                else "Use the supported confirmation and invalidation levels to define whether the setup graduates from monitoring."
            )
            self.securities.append(SecurityResearchItem(
                security_id=f"security-{symbol.lower()}", symbol=symbol, category=category,
                monitoring_bias=str(item.get("signal") or item.get("rating") or "Monitor"), setup_state=setup,
                summary=str(item.get("summary") or item.get("status_sentence") or f"Monitor {setup.lower()} confirmation."),
                evidence_ids=evidence_ids, figure_id=figure_id, confirmation=confirmation, invalidation=invalidation,
                risk_considerations=risk_considerations, reason_for_inclusion=reason, source_ids=[source_id],
                freshness=freshness, actionable=category == "Actionable / Ready", group=group, daily_change=change,
                relative_strength=relative_strength, trend=trend, volume_condition=volume_condition,
                confirmation_level=confirmation_level, invalidation_level=invalidation_level,
                change_since_previous=change_since_previous, research_classification=research_classification,
                focus_relation=focus_relation, source_timestamp=str(item.get("analysis_updated_at") or item.get("updated_at") or item.get("as_of") or market_date),
                why_here=reason,
                context=str(item.get("context") or item.get("summary") or item.get("status_sentence") or f"{symbol} is reviewed within {group}."),
                sector=sector,
                themes=themes,
                execution_consideration=execution_consideration,
                selected_for_research=selected_for_research,
            ))
            rows.append({
                "Ticker": symbol, "Group": group, "Setup state": setup, "Daily change": change,
                "Relative strength": relative_strength, "Trend": trend, "Volume": volume_condition,
                "Confirmation level": confirmation_level, "Invalidation level": invalidation_level,
                "Freshness": freshness, "Research classification": research_classification, "Reason for inclusion": reason,
            })
        self.tables.append(TableSpec(
            table_id="watchlist-candidate-matrix", title="Watchlist Candidate Matrix",
            columns=["Ticker", "Group", "Setup state", "Daily change", "Relative strength", "Trend", "Volume", "Confirmation level", "Invalidation level", "Freshness", "Research classification", "Reason for inclusion"],
            rows=rows, source_ids=[source_id], as_of=market_date,
            quality=self._data_quality(source_id, len(rows), max(1, len(items)), "frozen watchlist classification"),
        ))
        omitted = len([item for item in items if str(item.get("symbol") or item.get("ticker") or "").upper() not in selected_symbols])
        if omitted:
            self.limitations.append(f"{omitted} watchlist securities remain in compact triage and were not selected for a full Stage 6 security deep dive.")

    def _selected_security_symbols(self, items: list[dict[str, Any]]) -> set[str]:
        ranked: list[tuple[float, str]] = []
        for item in items:
            symbol = str(item.get("symbol") or item.get("ticker") or "").upper()
            if not symbol:
                continue
            freshness = str(item.get("source_state") or "unavailable").lower()
            if freshness in {"stale", "unavailable"}:
                continue
            group = self._security_group(symbol)
            relation = self._focus_relation(symbol, group)
            score = number(item.get("overall_score"))
            change = abs(number(item.get("change_percent")) or 0)
            signal = str(item.get("signal") or item.get("rating") or "").lower()
            priority = 100 if relation else 0
            priority += 45 if change >= 4 else change * 5
            priority += 35 if any(token in signal for token in ("buy", "sell", "break", "risk", "ready")) else 0
            priority += abs((score if score is not None else 50) - 50) * 0.5
            ranked.append((priority, symbol))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        limit = min(4, len(ranked))
        return {symbol for _, symbol in ranked[:limit]}

    def _security_taxonomy_context(self, symbol: str) -> tuple[str | None, list[str]]:
        taxonomy = next((item for item in self.report.get("security_taxonomy") or [] if str(item.get("ticker") or "").upper() == symbol), {})
        themes = []
        for row in (self.report.get("theme_intelligence") or {}).get("items") or []:
            members = {str(item.get("ticker") or "").upper() for item in row.get("members") or [] if isinstance(item, dict)}
            if symbol in members:
                themes.append(str(row.get("display_name") or row.get("theme_id")))
        return (str(taxonomy.get("sector")) if taxonomy.get("sector") else None, sorted(set(themes)))

    def _security_group(self, symbol: str) -> str:
        taxonomy = next((item for item in self.report.get("security_taxonomy") or [] if str(item.get("ticker") or "").upper() == symbol), {})
        themes = []
        for row in (self.report.get("theme_intelligence") or {}).get("items") or []:
            members = {str(item.get("ticker") or "").upper() for item in row.get("members") or [] if isinstance(item, dict)}
            if symbol in members:
                themes.append(str(row.get("display_name") or row.get("theme_id")))
        return themes[0] if themes else str(taxonomy.get("industry") or taxonomy.get("sector") or "Unmapped")

    def _focus_relation(self, symbol: str, group: str) -> str | None:
        if not self.research_focus:
            return None
        affected = next((item for item in self.research_focus.affected_securities if item.symbol == symbol), None)
        if affected:
            return affected.relation_to_focus
        candidate = next((item for item in self.research_candidates if item.candidate_id == self.research_focus.candidate_id), None)
        members = {str(item.get("ticker") or "").upper() for item in (candidate.constituents if candidate else [])}
        return "Validated member of the Research Focus" if symbol in members else None

    def _build_scenarios(self, thesis: ReportThesis) -> list[ScenarioSpec]:
        evidence_ids = thesis.supporting_evidence_ids
        leader = first_text(self.report.get("sector_leaders")) or "current leaders"
        return [
            ScenarioSpec(scenario_id="scenario-primary", label="Primary", likelihood="Primary", required_conditions=["Benchmark structure remains above medium-term support.", "Breadth does not deteriorate materially."], confirming_indicators=["Improving participation", "Stable risk proxies"], benchmark_levels=["Recent range and qualified moving averages"], breadth_conditions=["Medium-horizon participation stabilizes or improves"], risk_conditions=["Volatility and credit proxies remain contained"], likely_leadership=[leader], invalidation=thesis.invalidation_conditions, operating_response="Remain selective and add risk only to confirmed setups.", position_sizing_implication="Use normal-to-reduced size according to setup quality and invalidation distance.", evidence_ids=evidence_ids),
            ScenarioSpec(scenario_id="scenario-bullish", label="Bullish Alternative", likelihood="Plausible alternative", required_conditions=["Benchmarks clear recent highs.", "Participation broadens across horizons."], confirming_indicators=["Improving net advances", "Broader sector leadership"], benchmark_levels=["Close above the recent swing high"], breadth_conditions=["Short- and medium-horizon breadth rise together"], risk_conditions=["Credit proxy confirms equity strength"], likely_leadership=[leader, "emerging leaders with improving breadth"], invalidation=["Breakout fails back into the prior range."], operating_response="Increase exposure gradually through confirmed entries rather than chasing extension.", position_sizing_implication="Scale only after confirmation and retain explicit stops.", evidence_ids=evidence_ids),
            ScenarioSpec(scenario_id="scenario-bearish", label="Bearish Alternative", likelihood="Tail risk", required_conditions=["Benchmarks lose medium-term support.", "Participation and risk evidence deteriorate together."], confirming_indicators=["Persistent negative net advances", "Weakening credit proxy"], benchmark_levels=["Close below qualified medium-term support"], breadth_conditions=["Medium- and long-horizon participation decline"], risk_conditions=["Risk history worsens or defensive proxies strengthen"], likely_leadership=["defensive and lower-volatility groups"], invalidation=["Benchmarks reclaim support with improving breadth."], operating_response="Reduce gross exposure, avoid weak breakouts, and preserve liquidity.", position_sizing_implication="Use reduced size or remain uncommitted until evidence stabilizes.", evidence_ids=evidence_ids),
        ]

    def _build_monitoring(self, thesis: ReportThesis) -> None:
        evidence_ids = thesis.supporting_evidence_ids
        conditions = (
            ("benchmark-structure", "Benchmark structure", "Hold qualified medium-term support", "Tests whether the primary trend remains intact.", "Maintain selective exposure while support holds; reduce risk on a confirmed break."),
            ("breadth-confirmation", "Market breadth", "Short- and medium-horizon participation improve together", "Tests whether index strength is broadly supported.", "Become more aggressive only as participation broadens."),
            ("leadership-confirmation", "Leadership", "Relative strength and constituent breadth agree", "Separates durable leadership from concentrated ETF movement.", "Favor groups with both price and participation confirmation."),
            ("risk-invalidation", "Risk proxies", "Credit and defensive proxies do not contradict equities", "Provides cross-asset confirmation without asserting causality.", "Reduce size when cross-asset disagreement grows."),
        )
        self.monitoring = [MonitoringCondition(condition_id=identifier, metric=metric, threshold_or_condition=threshold, rationale=rationale, action_implication=action, evidence_ids=evidence_ids) for identifier, metric, threshold, rationale, action in conditions]
        if self.research_focus:
            self.monitoring.append(MonitoringCondition(
                condition_id="research-focus-confirmation",
                metric=f"{self.research_focus.subject} Research Focus",
                threshold_or_condition="; ".join(self.research_focus.confirmation_conditions[:2]),
                rationale=f"Tests whether the selected {self.research_focus.classification_label.lower()} subject retains relative-strength and participation support.",
                action_implication=f"Upgrade monitoring only if confirmation persists; downgrade it when any listed invalidation condition occurs.",
                evidence_ids=self.research_focus.evidence_ids,
            ))

    def _record_unsupported_gaps(self) -> None:
        self.limitations.extend([
            "Direct Treasury yield and yield-curve histories are unavailable; ETF bond prices are labelled as proxies.",
            "High-yield and investment-grade spread histories are unavailable; HYG is labelled as a price proxy.",
            "VIX history and term structure are unavailable as durable sourced series.",
            "Unsourced economic and earnings event strings are excluded from V7.",
            "No external research URLs, validated causal-attribution model, or historical analogues are available.",
            "Theme histories use the current reviewed basket unless a versioned historical membership record exists.",
        ])

    def _build_sections(self, thesis: ReportThesis, scenarios: list[ScenarioSpec]) -> list[ReportSection]:
        figure_ids = {figure.figure_id for figure in self.figures}
        baseline = "Baseline established." if not self.previous_snapshot else "Compatible previous-report changes are integrated where evidence aligns."
        if self.research_focus:
            focus_summary = (
                f"Research priority: {self.research_focus.subject} is classified {self.research_focus.direction} "
                f"with a {self.research_focus.priority_score:.1f}/100 priority score. Section 6 tests the supporting and "
                "contradictory evidence and defines the conditions that would change that classification."
            )
        else:
            focus_summary = (
                "Research priority: no standalone subject qualified. Section 6 records the failed evidence and "
                "materiality gates instead of substituting a lower-quality topic."
            )
        selected_security_ids = [item.security_id for item in self.securities if item.selected_for_research]
        selected_security_figure_ids = [item.figure_id for item in self.securities if item.selected_for_research and item.figure_id]
        if selected_security_ids:
            watchlist_summary = "Broad watchlist triage stays compact. Only deterministically selected securities receive a mini research report and chart; stale or partial records remain monitoring-only."
        elif self.securities:
            watchlist_summary = "No saved security met the fresh, complete, and material evidence gates for a full mini report. The available names remain in compact triage and monitoring only."
        else:
            watchlist_summary = "No frozen saved-security records are available for selected-security research. No mini report or substitute security is generated."
        research_section = ReportSection(
            section_id="research-focus", number=6, title="Research Question",
            purpose="Answer one material market question with explicit evidence, counter-evidence, relationships, continuity, and decision conditions.",
            question=self.research_inquiry.question if self.research_inquiry else "Did any reviewed subject qualify for standalone research?",
            paragraphs=[],
            figure_ids=self.research_focus.figure_ids if self.research_focus else present(figure_ids, "research-priority-comparison"),
            security_ids=[],
            monitoring_condition_ids=[],
        )
        sections = [
            ReportSection(section_id="cover", number=1, title="Cover and Current Thesis", question="What is the current operating thesis?", purpose="State the posture and define what confirms or invalidates it.", paragraphs=[thesis.concise_thesis], claim_ids=["current-thesis"], figure_ids=present(figure_ids, "index-spy"), monitoring_condition_ids=["benchmark-structure"]),
            ReportSection(section_id="executive-summary", number=2, title="Executive Summary", question="What changed, why does it matter, and where is the evidence incomplete?", purpose="Connect structure, participation, leadership, the research question, cross-asset evidence, and risk into one argument.", paragraphs=[f"{baseline} Structure defines the trend; breadth tests participation; leadership tests concentration; cross-asset proxies provide confirmation or counter-evidence.", "Index strength matters more when growth, small-cap, and industrial benchmarks agree. Divergent relative ratios narrow opportunity even when the benchmark holds its range.", "Breadth and leadership determine execution quality. Broadening improves breakout reliability; concentrated strength raises entry standards and reduces acceptable size.", focus_summary, "Cross-asset evidence is confirmatory, not causal. Direct yields, credit spreads, and volatility term structure remain unavailable and are not inferred from ETF proxies."], claim_ids=["current-thesis"], monitoring_condition_ids=["benchmark-structure", "breadth-confirmation"]),
            ReportSection(section_id="index-structure", number=3, title="Major Index Structure", question="Does index structure confirm the current regime?", purpose="Test trend quality across capitalization and style benchmarks.", paragraphs=["Moving averages define observed structure; volume and benchmark ratios test whether index strength extends across styles."], figure_ids=present(figure_ids, "index-spy", "index-qqq", "index-iwm", "index-dia", "ratio-qqq-spy", "ratio-iwm-spy")),
            ReportSection(section_id="breadth", number=4, title="Breadth and Participation", question="Does breadth confirm the index move?", purpose="Determine whether constituent participation confirms benchmark price.", paragraphs=["Short-, medium-, and long-horizon participation remain separate. Missing internals stay missing rather than being collapsed into a synthetic breadth label."], figure_ids=present(figure_ids, "breadth-ma-history", "breadth-net-advances", "breadth-highs-minus-lows"), monitoring_condition_ids=["breadth-confirmation"]),
            ReportSection(section_id="leadership", number=5, title="Leadership and Rotation", question="Which sectors and themes are driving the tape?", purpose="Separate established leadership from emerging, weakening, and concentrated moves.", paragraphs=["Returns identify persistence, rotation tails show direction, and constituent breadth tests representativeness. A quadrant label alone is insufficient."], figure_ids=present(figure_ids, "sector-return-heatmap", "sector-rotation", "theme-rotation"), monitoring_condition_ids=["leadership-confirmation"]),
            research_section,
            ReportSection(section_id="macro", number=7, title="Cross-Asset and Macro Confirmation", question="Do cross-asset proxies confirm the equity posture?", purpose="Test whether supported market proxies agree with the equity posture and selected research subject.", paragraphs=["Adjusted ETF prices are aligned as observational proxies. Treasury and high-yield ETFs are not direct yields or credit spreads, and no causal transmission is asserted."], figure_ids=present(figure_ids, "macro-normalized")),
            ReportSection(section_id="risk", number=8, title="Risk, Volatility, Credit and Sentiment", question="What could destabilize the thesis?", purpose="Describe current risk and its direction using available history.", paragraphs=["Compatible report history supplies direction; unavailable volatility term structure and spread series remain disclosed gaps.", "The primary risk is joint deterioration in benchmark structure and participation. Point-in-time sentiment cannot replace price, breadth, and cross-asset confirmation."], claim_ids=["risk-posture"] if "risk-posture" in self.claims else [], figure_ids=present(figure_ids, "risk-history", "market-evolution"), monitoring_condition_ids=["risk-invalidation"]),
            ReportSection(section_id="scenarios", number=9, title="Scenario Framework and Events", question="Which evidence would move the market into a different path?", purpose="Translate prior evidence into conditional market paths and include only sourced events.", paragraphs=["Paths use qualitative labels, not unsupported probabilities. Each one identifies conditions, invalidation, leadership, and operating response from evidence already introduced."], scenario_ids=[item.scenario_id for item in scenarios]),
            ReportSection(section_id="watchlist", number=10, title="Personalized Watchlist and Security Research", question="Which saved securities deserve deeper research?", purpose="Prioritize saved-security monitoring without promoting stale or partial evidence.", paragraphs=[watchlist_summary], table_ids=["watchlist-candidate-matrix"] if self.tables else [], security_ids=selected_security_ids, figure_ids=selected_security_figure_ids),
            ReportSection(section_id="operating-plan", number=11, title="Next-Session Operating Plan", question="What must be confirmed or invalidated next session?", purpose="Convert the thesis and Research Focus into explicit monitoring and risk conditions.", paragraphs=["Every condition links a metric to its rationale and action implication; none substitutes for personalized investment advice."], monitoring_condition_ids=[item.condition_id for item in self.monitoring]),
            ReportSection(section_id="methodology", number=12, title="Methodology, Sources and Limitations", question="How strong and auditable is the evidence?", purpose="Make provenance, transformations, research selection and unavailable evidence auditable.", paragraphs=["Interpretations derive from the frozen evidence registry. Figures carry sources, timestamps, quality states, and explicit omissions."], quality_note="; ".join(sorted(set(self.limitations))),),
        ]
        return sections

    def _bars(self, symbol: str, market_date: str) -> list[DailyBar]:
        frozen = (self.report.get("index_ohlcv") or {}).get(symbol)
        if not frozen:
            frozen = path(self.report, "macro", "histories", symbol)
        frozen_bars = bars_from_frozen_history(symbol, frozen, market_date)
        best: list[DailyBar] = frozen_bars
        for provider in BAR_PROVIDERS:
            try:
                candidate = self.bars.history(symbol, provider, end_date=market_date)
            except Exception:
                candidate = []
            if len(candidate) > len(best):
                best = candidate
        return best[-450:]

    def _bar_source(self, symbol: str, bars: list[DailyBar]) -> str:
        provider = bars[-1].provider if bars else "unavailable"
        timestamp = bars[-1].source_timestamp or bars[-1].fetched_at or bars[-1].timestamp if bars else None
        return self._source(f"bars-{provider}-{symbol.lower()}", provider, f"{symbol} adjusted daily OHLCV", timestamp, "market_data")

    def _series(self, series_id: str, label: str, unit: str, dates: list[str], values: list[Any], source_id: str, color: str | None = None, transformation: str = "none") -> FigureSeries:
        return FigureSeries(series_id=series_id, label=label, unit=unit, points=[{"date": date, "value": value} for date, value in zip(dates, values)], source_id=source_id, color=color, transformation=transformation)

    def _source(self, source_id: str, provider: str, dataset: str, timestamp: str | None, source_type: str) -> str:
        if source_id not in self.sources:
            self.sources[source_id] = SourceReference(source_id=source_id, provider=provider or "unavailable", dataset=dataset, timestamp=timestamp, source_type=source_type, access_status="available" if provider != "unavailable" else "unavailable", freshness="current" if timestamp else "unknown")
        return source_id

    def _evidence(
        self,
        evidence_id: str,
        metric: str,
        value: float | str | None,
        unit: str | None,
        timeframe: str,
        source_id: str,
        timestamp: str | None,
        *,
        freshness: str = "current",
        previous: float | str | None = None,
        change: float | str | None = None,
    ) -> str | None:
        if value is None:
            return None
        if source_id not in self.sources:
            source_id = "report"
        self.evidence[evidence_id] = EvidencePoint(evidence_id=evidence_id, metric=metric, current_value=value, previous_value=previous, change=change, unit=unit, timeframe=timeframe, source_id=source_id, timestamp=timestamp, freshness=freshness, reliability="supported", observation_type="point_in_time")
        return evidence_id

    def _claim(self, claim_id: str, statement: str, evidence_ids: list[str], interpretation: str, implication: str, quality: str) -> None:
        if not evidence_ids:
            return
        self.claims[claim_id] = AnalyticalClaim(claim_id=claim_id, statement=statement, evidence_ids=evidence_ids, interpretation=interpretation, trader_implication=implication, confidence="high" if len(evidence_ids) >= 2 else "moderate", evidence_quality=self._quality(quality))

    def _number_figures(self) -> None:
        for number_value, figure in enumerate(self.figures, 1):
            figure.figure_number = number_value

    def _data_quality(self, source_id: str, observations: int, expected: int, transformation: str) -> DataQualityState:
        provider = self.sources.get(source_id).provider.lower() if source_id in self.sources else "unavailable"
        state = "test" if provider in {"test", "generated_test_data"} else self._quality(self._source_state())
        completeness = min(1, observations / max(1, expected))
        if completeness < 0.75 and state not in {"test", "unavailable"}:
            state = "partial"
        return DataQualityState(state=state, completeness=completeness, freshness="latest available observation", transformation=transformation)

    def _source_state(self) -> str:
        values = [
            path(self.report, "macro", "source_state"),
            path(self.report, "sector_dashboard", "source"),
            path(self.report, "theme_intelligence", "source_state"),
        ]
        normalized = {str(value).lower() for value in values if value}
        if "test" in normalized or "generated_test_data" in normalized or "mock" in normalized:
            return "test"
        if len(normalized) > 1:
            return "mixed"
        return next(iter(normalized), "unavailable")

    def _quality(self, value: Any) -> str:
        normalized = str(value or "unavailable").lower()
        if normalized in {"mock", "generated_test_data"}:
            return "test"
        return normalized if normalized in SUPPORTED_QUALITY else "unavailable"

    def _completeness(self) -> float:
        macro = self.report.get("macro") or {}
        components = [
            self.report.get("indexes") or self.report.get("index_histories"),
            (self.report.get("sector_dashboard") or {}).get("sectors") if isinstance(self.report.get("sector_dashboard"), dict) else None,
            (self.report.get("watchlist_summary") or {}).get("items") if isinstance(self.report.get("watchlist_summary"), dict) else None,
            macro.get("assets") if isinstance(macro, dict) and macro.get("source_state") not in {"unavailable", None} else None,
            path(self.report, "semantic_context", "snapshot_ids", "breadth"),
        ]
        return round(sum(bool(item) for item in components) / len(components), 2)

    def _report_type(self, generated_at: str, market_date: str) -> str:
        try:
            generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
            if generated.weekday() >= 5 or generated.date().isoformat() > market_date:
                return "Weekend / Holiday"
            if generated.hour < 13:
                return "Pre-Market"
            if generated.hour < 20:
                return "Intraday"
            return "After Close"
        except ValueError:
            return "Daily"

    def _data_cutoff(self, generated_at: str) -> str:
        timestamps = [source.timestamp for source in self.sources.values() if source.timestamp]
        return max(timestamps) if timestamps else generated_at


def build_report_document(report: Any, previous_snapshot: dict[str, Any] | None = None) -> ReportDocument:
    return DocumentBuilder(report, previous_snapshot).build()


def path(value: Any, *parts: str) -> Any:
    current = value
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace("%", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def format_price(value: float) -> str:
    return f"${value:,.2f}"


def first_text(value: Any) -> str | None:
    if isinstance(value, list):
        return next((str(item) for item in value if item), None)
    return str(value) if value else None


def confidence_label(value: float | None) -> str:
    if value is None:
        return "Unqualified"
    if value >= 80:
        return "High"
    if value >= 60:
        return "Moderate"
    return "Low"


def moving_average(values: list[float], window: int) -> list[float | None]:
    if window <= 0:
        return [None for _ in values]
    result: list[float | None] = []
    total = 0.0
    for index, value in enumerate(values):
        total += value
        if index >= window:
            total -= values[index - window]
        result.append(round(total / window, 6) if index + 1 >= window else None)
    return result


def exponential_moving_average(values: list[float], window: int) -> list[float | None]:
    if window <= 0 or not values:
        return [None for _ in values]
    multiplier = 2 / (window + 1)
    result: list[float | None] = []
    current = values[0]
    for index, value in enumerate(values):
        current = value if index == 0 else (value - current) * multiplier + current
        result.append(round(current, 6) if index + 1 >= window else None)
    return result


def present(available: set[str], *values: str) -> list[str]:
    return [value for value in values if value in available]


def bars_from_frozen_history(symbol: str, payload: Any, market_date: str) -> list[DailyBar]:
    if not isinstance(payload, dict):
        return []
    provider = str(payload.get("provider") or payload.get("source") or "unavailable").lower()
    result: list[DailyBar] = []
    for candle in payload.get("candles") or []:
        if not isinstance(candle, dict):
            continue
        timestamp = str(candle.get("timestamp") or candle.get("date") or "")
        session_date = timestamp[:10]
        if not session_date or session_date > market_date:
            continue
        open_value = number(candle.get("open")); high = number(candle.get("high")); low = number(candle.get("low")); close = number(candle.get("close")); volume = number(candle.get("volume"))
        if None in {open_value, high, low, close} or min(open_value, high, low, close) <= 0:
            continue
        result.append(DailyBar(ticker=symbol, provider=provider, session_date=session_date, timestamp=timestamp, open=open_value, high=high, low=low, close=close, volume=max(0, volume or 0), adjusted=True, fetched_at=payload.get("as_of"), source_timestamp=timestamp, quality_status="valid"))
    return sorted(result, key=lambda item: item.session_date)


def document_word_count(
    thesis: ReportThesis,
    sections: list[ReportSection],
    claims: list[AnalyticalClaim],
    figures: list[FigureSpec],
    scenarios: list[ScenarioSpec],
    securities: list[SecurityResearchItem],
    monitoring: list[MonitoringCondition],
    limitations: list[str],
    research_focus: ResearchFocus | None = None,
    secondary_research_note: SecondaryResearchNote | None = None,
    research_inquiry: ResearchInquiry | None = None,
) -> int:
    values: list[str] = [
        thesis.concise_thesis, thesis.previous_thesis or "", thesis.thesis_change,
        *thesis.confirmation_conditions, *thesis.invalidation_conditions,
    ]
    for section in sections:
        values.extend([section.title, section.question or "", section.purpose, *section.paragraphs, section.quality_note or ""])
    for claim in claims:
        values.extend([claim.statement, claim.interpretation, claim.trader_implication])
    for figure in figures:
        values.extend([figure.title, figure.subtitle, figure.question_answered, figure.observation, figure.interpretation, figure.confirmation_condition, figure.risk_condition])
    for scenario in scenarios:
        values.extend([scenario.label, *scenario.required_conditions, *scenario.confirming_indicators, *scenario.benchmark_levels, *scenario.breadth_conditions, *scenario.risk_conditions, *scenario.likely_leadership, *scenario.invalidation, scenario.operating_response, scenario.position_sizing_implication])
    for security in securities:
        values.extend([security.category, security.monitoring_bias, security.setup_state, security.summary, security.confirmation, security.invalidation, security.risk_considerations, security.reason_for_inclusion, security.why_here or "", security.context or "", security.sector or "", *security.themes, security.execution_consideration or ""])
    for condition in monitoring:
        values.extend([condition.metric, condition.threshold_or_condition, condition.rationale, condition.action_implication])
    if research_focus:
        values.extend([
            research_focus.main_thesis,
            research_focus.counter_thesis,
            *research_focus.why_selected,
            *research_focus.key_evidence,
            *research_focus.confirmation_conditions,
            *research_focus.invalidation_conditions,
            *research_focus.prose_sections.values(),
            research_focus.question,
            research_focus.executive_answer,
            *research_focus.execution_implications,
            *research_focus.conclusion_change_conditions,
        ])
        if research_focus.evidence_quality:
            values.extend(research_focus.evidence_quality.rationale)
        for row in research_focus.evidence_matrix:
            values.extend([row.dimension, row.finding, row.implication])
        if research_focus.relationship_graph:
            values.extend([item.label for item in research_focus.relationship_graph.nodes])
            values.extend([item.label for item in research_focus.relationship_graph.edges])
        for signal in [*research_focus.leading_securities, *research_focus.lagging_securities]:
            values.extend([signal.symbol, signal.metric_label, signal.reason])
        if research_focus.research_evolution:
            evolution = research_focus.research_evolution
            values.extend([evolution.yesterday, evolution.today, evolution.tomorrow, evolution.what_changed, evolution.research_follow_up])
        for item in research_focus.affected_securities:
            values.extend([
                item.symbol, item.group, item.setup_state, str(item.relative_strength or ""), item.trend,
                item.volume_condition, item.key_level, item.change_since_previous, item.relation_to_focus,
                item.reason_to_monitor,
            ])
    if secondary_research_note:
        values.extend([secondary_research_note.subject, secondary_research_note.summary])
    if research_inquiry:
        values.extend([research_inquiry.question, research_inquiry.executive_answer])
    values.extend(limitations)
    return sum(len(value.split()) for value in values if value)


def research_focus_prose(candidate: Any, decision: Any) -> dict[str, Any]:
    score = candidate.score.total
    rank_text = f"rank {candidate.current_rank}" if candidate.current_rank is not None else "an individual-security status change"
    rank_change_text = (
        f"a {candidate.rank_change:+d}-place rank change from {candidate.previous_rank}"
        if candidate.rank_change is not None and candidate.previous_rank is not None else "no compatible prior rank comparison"
    )
    return_1w = metric_text(candidate.returns.get("1w"), "%")
    return_1m = metric_text(candidate.returns.get("1m"), "%")
    return_3m = metric_text(candidate.returns.get("3m"), "%")
    rs_suffix = " rank" if candidate.category == "individual_security" else " percentage points"
    rs_text = metric_text(candidate.current_relative_strength, rs_suffix)
    breadth_text = metric_text(candidate.breadth, "%")
    breadth_character = (
        "broad" if candidate.breadth is not None and candidate.breadth >= 60
        else "narrow" if candidate.breadth is not None and candidate.breadth < 40
        else "mixed" if candidate.breadth is not None else "unavailable"
    )
    direction = candidate.direction.replace("_", " ")
    main_thesis = stage6_executive_answer(candidate)
    counter_thesis = (
        f"The {direction} reading weakens if relative performance and breadth reverse together. "
        f"Distinct participation is {'available' if candidate.participation is not None else 'unavailable'}, group-level volume is {'available' if candidate.volume_confirmation is not None else 'unavailable'}, "
        f"and completeness is {candidate.data_completeness:.0%}; unavailable fields do not count as confirmation."
    )
    evidence = (
        f"{candidate.name} is {rank_text}, with {rank_change_text}. Returns are {return_1w} (1W), {return_1m} (1M), and {return_3m} (3M); "
        f"relative strength is {rs_text}; breadth is {breadth_text}; {candidate.qualifying_constituent_count} securities qualify for the reviewed universe."
    )
    counter = (
        f"Counter evidence is explicit: current participation is {breadth_character}, volume confirmation is {'present' if candidate.volume_confirmation is not None else 'missing'}, "
        f"and the missing scored dimensions are {', '.join(candidate.score.missing_dimensions) if candidate.score.missing_dimensions else 'none'}. "
        "The priority score ranks research need; it is not a forecast or a trade signal."
    )
    relationships = (
        "Industry relationships are limited to benchmark-relative evidence, reviewed hierarchy, validated taxonomy, and exact saved-watchlist overlap. "
        "No causal flow, capital flow, supplier, or customer relationship is inferred."
    )
    execution = " ".join(stage6_execution_implications(candidate))
    changes = " ".join(stage6_conclusion_change_conditions(candidate))
    confirmation_conditions = stage6_conclusion_change_conditions(candidate)[1:]
    invalidation_conditions = [stage6_conclusion_change_conditions(candidate)[0], "Freshness, completeness, figure, or constituent-count gates fail."]
    return {
        "main_thesis": main_thesis,
        "counter_thesis": counter_thesis,
        "key_evidence": [
            f"Research Priority Score {score:.1f} versus {candidate.score.materiality_threshold:.1f} threshold.",
            f"{rank_text.title()} with {rank_change_text}.",
            f"One-month relative strength {rs_text}; 50-day constituent breadth {breadth_text}.",
            f"{candidate.qualifying_constituent_count} qualifying constituents; user relevance {candidate.user_relevance.tier}.",
        ],
        "confirmation_conditions": confirmation_conditions,
        "invalidation_conditions": invalidation_conditions,
        "sections": {
            "evidence": evidence,
            "counter_evidence": counter,
            "industry_relationships": relationships,
            "execution_implications": execution,
            "what_changes_the_conclusion": changes,
        },
    }


def secondary_research_summary(candidate: Any, primary: Any) -> str:
    return (
        f"Observation. {candidate.name} is retained as a secondary note because its {candidate.direction} evidence scored {candidate.score.total:.1f}, "
        f"within 15 points of {primary.name}, while representing an opposing or distinct signal. Evidence includes its supported rank, relative-strength, return, participation, completeness, and freshness fields; missing volume contributes zero. "
        f"Interpretation. The note is not a second primary theme and does not dilute the materiality gate. It provides counter-evidence to the market narrative by showing where leadership or weakness is not uniform. "
        f"Confirmation requires the candidate to remain above the secondary threshold with its direction and participation intact. Invalidation occurs when its score falls below that threshold, its source becomes stale, or its qualifying evidence no longer supports at least two figures. "
        f"Implication. Monitor {candidate.name} as a distinct comparison with {primary.name}; do not infer ownership, a recommendation, capital flow, or a causal relationship between the two subjects."
    )


def metric_text(value: Any, suffix: str) -> str:
    parsed = number(value)
    return "unavailable" if parsed is None else f"{parsed:+.1f}{suffix}"


def normalize_graph_id(value: Any) -> str:
    normalized = "".join(character.lower() if character.isalnum() else "-" for character in str(value or ""))
    return "-".join(part for part in normalized.split("-") if part) or "unknown"


def candidate_evidence_id(candidate: Any, suffix: str) -> str | None:
    expected = f"research-{candidate.candidate_id.replace(':', '-')}-{suffix}"
    return expected if expected in candidate.evidence_ids else None


def evidence_grade(value: float | None) -> str:
    if value is None or value < 45:
        return "Low"
    if value >= 75:
        return "High"
    return "Medium"


def evidence_stance(value: float | None) -> str:
    if value is None:
        return "neutral"
    if value >= 60:
        return "supports"
    if value < 40:
        return "contradicts"
    return "neutral"


def directional_confirmation_score(direction: str, value: float | None) -> float | None:
    if value is None:
        return None
    if direction in {"leading", "emerging"}:
        return value
    if direction in {"weakening", "lagging", "breakdown"}:
        return 100 - value
    return abs(value - 50) * 2


def research_consistency_score(candidate: Any) -> float:
    observations = [
        candidate.returns.get(period)
        for period in ("1w", "1m", "3m")
        if candidate.returns.get(period) is not None
    ]
    if candidate.category != "individual_security" and candidate.current_relative_strength is not None:
        observations.append(candidate.current_relative_strength)
    for participation_value in (candidate.breadth, candidate.participation):
        if participation_value is None:
            continue
        observations.append(participation_value - 50)
    if not observations:
        return 0.0
    if candidate.direction in {"leading", "emerging"}:
        confirming = sum(value > 0 for value in observations)
    elif candidate.direction in {"weakening", "lagging", "breakdown"}:
        confirming = sum(value < 0 for value in observations)
    else:
        confirming = sum(abs(value) >= 2 for value in observations)
    return round(confirming / len(observations) * 100, 2)


def stage6_research_question(candidate: Any) -> str:
    if candidate.category == "individual_security":
        if candidate.direction in {"weakening", "lagging", "breakdown"}:
            return f"Is {candidate.name} weakness temporary or structural?"
        return f"Why does {candidate.name}'s status change deserve standalone research?"
    if candidate.direction in {"leading", "emerging"}:
        if candidate.breadth is not None and candidate.breadth < 45:
            return f"Why is {candidate.name} outperforming despite narrow breadth?"
        return f"Why is {candidate.name} leading, and is participation broad enough to persist?"
    if candidate.direction in {"weakening", "lagging", "breakdown"}:
        return f"Is {candidate.name} weakness temporary or structural?"
    return f"Why is {candidate.name} diverging from its benchmark and peers?"


def stage6_executive_answer(candidate: Any) -> str:
    direction = candidate.direction.replace("_", " ")
    persistence = evidence_grade(candidate.persistence)
    if candidate.breadth is None:
        breadth = "Breadth is unavailable"
    elif candidate.direction in {"leading", "emerging"}:
        breadth = "Breadth confirms broad participation" if candidate.breadth >= 60 else "Breadth is narrow or contrary"
    elif candidate.direction in {"weakening", "lagging", "breakdown"}:
        breadth = "Breadth confirms broad weakness" if candidate.breadth <= 40 else "Breadth does not yet confirm broad weakness"
    else:
        breadth = "Breadth is mixed relative to the divergence thesis"
    missing_confirmation: list[str] = []
    if candidate.participation is None:
        missing_confirmation.append("distinct participation is unavailable")
    if candidate.volume_confirmation is None:
        missing_confirmation.append(
            "comparable volume confirmation is unavailable"
            if candidate.category == "individual_security"
            else "group-level volume confirmation is unavailable"
        )
    if missing_confirmation:
        conditional = f"the conclusion remains conditional because {' and '.join(missing_confirmation)}; missing evidence does not count as confirmation"
    else:
        conditional = "freshness, participation, completeness, and directional consistency support the current classification"
    relative_label = "RS rank" if candidate.category == "individual_security" else "one-month benchmark-relative strength"
    return (
        f"{candidate.name} qualifies as {direction}: priority {candidate.score.total:.1f} exceeds the {candidate.score.materiality_threshold:.1f} gate, "
        f"{relative_label} is {metric_text(candidate.current_relative_strength, '')}, and directional persistence is {persistence.lower()}. "
        f"{breadth}; {conditional}."
    )


def humanize_research_gap(value: str) -> str:
    labels = {
        "stale_or_unavailable_subject_data": "stale or unavailable subject data",
        "data_completeness_below_60_percent": "data completeness below 60%",
        "fewer_than_two_supported_figures": "fewer than two supportable figures",
        "fewer_than_three_qualifying_constituents": "fewer than three qualifying constituents",
        "individual_security_change_not_material": "no material individual-security change",
        "classification_unavailable": "classification unavailable",
        "neutral_without_material_divergence": "no material directional divergence",
        "materiality_score_below_threshold": "priority score below the materiality threshold",
    }
    return labels.get(value, value.replace("_", " "))


def stage6_execution_implications(candidate: Any) -> list[str]:
    if candidate.direction in {"leading", "emerging"}:
        first = f"Keep {candidate.name} on the next-session research list, but require security-level price and volume confirmation before treating a saved name as actionable."
    else:
        first = f"Treat {candidate.name} as a risk and avoidance research priority until relative strength and constituent breadth stabilize together."
    return [
        first,
        "Use the validated group relationship to prioritize review, never as a substitute for the security's own setup and invalidation level.",
        "Downgrade the research priority when the materiality, freshness, completeness, constituent, or figure gates fail.",
    ]


def stage6_conclusion_change_conditions(candidate: Any) -> list[str]:
    if candidate.direction in {"leading", "emerging"}:
        directional_change = f"The conclusion weakens if {candidate.name} loses benchmark-relative strength while constituent breadth turns contrary."
        confirmations = [
            "Directional relative strength persists on the next compatible snapshot.",
            "Constituent breadth and distinct participation remain aligned with leadership.",
        ]
    else:
        directional_change = f"The conclusion changes if {candidate.name} reclaims benchmark-relative strength while constituent breadth stabilizes or improves."
        confirmations = [
            "Negative relative strength persists on the next compatible snapshot.",
            "Constituent breadth and distinct participation remain aligned with weakness.",
        ]
    return [
        directional_change,
        *confirmations,
        f"The Research Priority Score remains above {candidate.score.materiality_threshold:.1f} with current, complete, figure-ready evidence.",
    ]


def stage6_next_evidence_test(candidate: Any) -> str:
    if candidate.direction in {"leading", "emerging"}:
        return (
            f"Recheck whether {candidate.name} keeps positive benchmark-relative strength while breadth and "
            "distinct participation remain aligned."
        )
    return (
        f"Recheck whether {candidate.name} retains negative benchmark-relative strength alongside weak breadth "
        "and distinct participation."
    )


def previous_candidate_state(previous: dict[str, Any], candidate: Any) -> str | None:
    if not previous:
        return None
    if candidate.category == "theme":
        rows = previous.get("themeRanking") or previous.get("theme_ranking") or []
        key = candidate.candidate_id.split(":", 1)[-1]
        row = next((item for item in rows if normalize_graph_id(item.get("theme_id") or item.get("display_name")) == normalize_graph_id(key)), None)
        if row:
            return f"{row.get('display_name') or candidate.name} was {str(row.get('classification') or 'unclassified').lower()}, rank {row.get('rank') or 'unavailable'}, with one-month relative strength {metric_text(path(row, 'relative_strength', 'vs_spy_1m'), ' points')}."
    if candidate.category == "sector":
        rows = previous.get("sectorRanking") or previous.get("sector_ranking") or []
        key = candidate.candidate_id.split(":", 1)[-1]
        row = next((item for item in rows if normalize_graph_id(item.get("id") or item.get("name")) == normalize_graph_id(key)), None)
        if row:
            metadata = row.get("metadata") or {}
            return f"{row.get('name') or candidate.name} was {str(metadata.get('status') or row.get('classification') or 'unclassified').lower()}, rank {metadata.get('rank') or row.get('rank') or 'unavailable'}, with one-month relative strength {metric_text(metadata.get('relative_strength_1m'), ' points')}."
    if candidate.category == "individual_security":
        rows = previous.get("watchlistSummary") or previous.get("watchlist_summary") or []
        row = next((item for item in rows if str(item.get("symbol") or item.get("ticker") or "").upper() == candidate.name.upper()), None)
        if row:
            return f"{candidate.name} was classified {row.get('signal') or row.get('rating') or 'monitoring'} with setup {row.get('mainSetup') or row.get('setup') or 'unavailable'}."
    return None


def is_non_session_report(report: dict[str, Any], market_date: str) -> bool:
    generated_at = str(report.get("generated_at") or report.get("generated_time") or "")
    try:
        generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        return generated.weekday() >= 5 or generated.date().isoformat() > market_date[:10]
    except ValueError:
        return False
