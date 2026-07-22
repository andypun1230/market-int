from __future__ import annotations

from io import BytesIO
from math import isfinite
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import CondPageBreak, Flowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.reports.document import FigureSpec, ReportDocument


INK = colors.HexColor("#101828")
MUTED = colors.HexColor("#667085")
RULE = colors.HexColor("#D0D5DD")
GRID = colors.HexColor("#EAECF0")
BLUE = colors.HexColor("#087EA4")
GREEN = colors.HexColor("#138A5B")
RED = colors.HexColor("#C4323C")
ORANGE = colors.HexColor("#C76D12")
PURPLE = colors.HexColor("#6941C6")
SERIES_COLORS = (BLUE, PURPLE, ORANGE, GREEN, RED, colors.HexColor("#475467"), colors.HexColor("#06AED4"))


def generate_report_pdf_v6(value: ReportDocument | dict[str, Any]) -> BytesIO:
    return generate_report_pdf_document(value)


def generate_report_pdf_document(value: ReportDocument | dict[str, Any], *, stage6: bool = False) -> BytesIO:
    document_model = value if isinstance(value, ReportDocument) else ReportDocument.model_validate(value)
    buffer = BytesIO()
    pdf = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=0.67 * inch,
        bottomMargin=0.54 * inch,
        title=document_model.title,
        author="Market Intelligence App",
        subject=f"{document_model.report_type} research briefing for {document_model.market_date}",
    )
    styles = report_styles()
    story = build_story_stage6(document_model, styles) if stage6 else build_story(document_model, styles)
    pdf.build(
        story,
        onFirstPage=lambda canvas, doc: draw_page(canvas, doc, document_model),
        onLaterPages=lambda canvas, doc: draw_page(canvas, doc, document_model),
    )
    buffer.seek(0)
    return buffer


def build_story_stage6(document: ReportDocument, styles: dict[str, ParagraphStyle]) -> list[Any]:
    figures = {figure.figure_id: figure for figure in document.figures}
    claims = {claim.claim_id: claim for claim in document.claims}
    scenarios = {scenario.scenario_id: scenario for scenario in document.scenarios}
    securities = {security.security_id: security for security in document.securities}
    monitoring = {condition.condition_id: condition for condition in document.monitoring_conditions}
    tables = {table.table_id: table for table in document.tables}
    story: list[Any] = []
    rendered_figures: set[str] = set()
    major_breaks = {"executive-summary", "research-focus", "scenarios", "watchlist", "operating-plan", "methodology"}
    previous_was_small = False
    for section_index, section in enumerate(document.sections):
        section_figures = sorted(
            [figures[item] for item in section.figure_ids if item in figures and item not in rendered_figures],
            key=lambda item: item.figure_number,
        )
        has_table_rows = any(tables[item].rows for item in section.table_ids if item in tables)
        empty_watchlist = section.section_id == "watchlist" and not has_table_rows and not section.security_ids
        force_major_break = section.section_id in major_breaks and not empty_watchlist
        small_section = not section_figures and (section.section_id not in major_breaks or empty_watchlist)
        if section_index:
            if force_major_break or (section_figures and not previous_was_small):
                story.append(PageBreak())
            elif small_section:
                story.append(CondPageBreak(2.15 * inch))
        if section.section_id == "cover":
            story.extend(cover_story_stage6(document, section, styles))
            continue
        story.extend(section_heading(section.number, section.title, section.purpose, styles, question=section.question))
        if section.section_id == "research-focus":
            story.extend(research_inquiry_header_stage6(document, styles))
        for paragraph in section.paragraphs:
            story.append(Paragraph(clean(paragraph), styles["body_lead"] if section.section_id == "executive-summary" else styles["body"]))
            story.append(Spacer(1, 0.07 * inch))
        for claim_id in section.claim_ids:
            claim = claims.get(claim_id)
            if claim:
                story.append(claim_strip(claim.statement, claim.interpretation, claim.trader_implication, styles))
                story.append(Spacer(1, 0.09 * inch))
        if section.scenario_ids:
            story.append(scenario_table([scenarios[item] for item in section.scenario_ids if item in scenarios], styles))
        if section.table_ids:
            for table_id in section.table_ids:
                if table_id in tables:
                    story.extend(render_table_stage6(tables[table_id], styles))
        if section.security_ids:
            selected_securities = [securities[item] for item in section.security_ids if item in securities]
            if section.table_ids and selected_securities:
                story.extend(security_research_queue_stage6(selected_securities, styles))
            for security_index, security in enumerate(selected_securities):
                if security_index or section.table_ids:
                    story.append(PageBreak())
                    story.extend(section_heading(section.number, section.title, "Selected security research - continued", styles, compact=True, question=section.question))
                attached = figures.get(security.figure_id) if security.figure_id and security.figure_id not in rendered_figures else None
                story.extend(security_research_story_stage6(security, attached, styles))
                if attached:
                    rendered_figures.add(attached.figure_id)
        if section.monitoring_condition_ids:
            selected = [monitoring[item] for item in section.monitoring_condition_ids if item in monitoring]
            if selected:
                story.append(KeepTogether(monitoring_table(selected, styles, expanded=section.section_id == "operating-plan")))
        for index, figure in enumerate(section_figures):
            if figure.figure_id in rendered_figures:
                continue
            if index and index % 2 == 0:
                story.append(PageBreak())
                story.extend(section_heading(section.number, section.title, "Continued evidence", styles, compact=True, question=section.question))
            story.append(figure_block(figure, styles, compact=True, stage6=True))
            story.append(Spacer(1, 0.08 * inch))
            rendered_figures.add(figure.figure_id)
        if section.section_id == "methodology":
            story.extend(methodology_story(document, styles, stage6=True))
        previous_was_small = small_section
    return story


def build_story(document: ReportDocument, styles: dict[str, ParagraphStyle]) -> list[Any]:
    figures = {figure.figure_id: figure for figure in document.figures}
    claims = {claim.claim_id: claim for claim in document.claims}
    scenarios = {scenario.scenario_id: scenario for scenario in document.scenarios}
    securities = {security.security_id: security for security in document.securities}
    monitoring = {condition.condition_id: condition for condition in document.monitoring_conditions}
    tables = {table.table_id: table for table in document.tables}
    story: list[Any] = []
    for section_index, section in enumerate(document.sections):
        if section_index:
            story.append(PageBreak())
        if section.section_id == "cover":
            story.extend(cover_story(document, section, figures, styles))
            continue
        story.extend(section_heading(section.number, section.title, section.purpose, styles))
        if section.section_id == "research-focus" and document.research_focus:
            story.extend(research_focus_header(document, styles))
        for paragraph in section.paragraphs:
            story.append(Paragraph(clean(paragraph), styles["body_lead"] if section.section_id == "executive-summary" else styles["body"]))
            story.append(Spacer(1, 0.09 * inch))
        for claim_id in section.claim_ids:
            claim = claims.get(claim_id)
            if claim:
                story.append(claim_strip(claim.statement, claim.interpretation, claim.trader_implication, styles))
                story.append(Spacer(1, 0.11 * inch))
        if section.scenario_ids:
            story.append(scenario_table([scenarios[item] for item in section.scenario_ids if item in scenarios], styles))
        if section.table_ids:
            for table_id in section.table_ids:
                if table_id in tables:
                    story.extend(render_table(tables[table_id], styles))
        if section.security_ids:
            story.extend(security_summary([securities[item] for item in section.security_ids if item in securities], styles))
        if section.monitoring_condition_ids:
            selected = [monitoring[item] for item in section.monitoring_condition_ids if item in monitoring]
            if selected:
                story.extend(monitoring_table(selected, styles, expanded=section.section_id == "operating-plan"))
        section_figures = [figures[item] for item in section.figure_ids if item in figures]
        for index, figure in enumerate(section_figures):
            if index and index % 2 == 0 and section.section_id != "watchlist":
                story.append(PageBreak())
                story.extend(section_heading(section.number, section.title, "Continued evidence", styles, compact=True))
            unpaired_last = index == len(section_figures) - 1 and len(section_figures) % 2 == 1
            story.append(figure_block(figure, styles, compact=len(section_figures) > 1 and not unpaired_last))
            story.append(Spacer(1, 0.1 * inch))
        if section.section_id == "methodology":
            story.extend(methodology_story(document, styles))
    return story


def cover_story(document: ReportDocument, section: Any, figures: dict[str, FigureSpec], styles: dict[str, ParagraphStyle]) -> list[Any]:
    thesis = document.thesis
    story: list[Any] = [
        Spacer(1, 0.05 * inch),
        Paragraph("MARKET INTELLIGENCE RESEARCH", styles["kicker"]),
        Paragraph(clean(document.title), styles["cover_title"]),
        Paragraph(f"{clean(document.report_type)}  |  Market date {clean(document.market_date)}  |  Generated {clean(document.generated_at)}", styles["meta"]),
        Spacer(1, 0.2 * inch),
        thin_rule(),
        Spacer(1, 0.15 * inch),
        Paragraph(f"CURRENT POSTURE  {clean(thesis.posture)}", styles["posture"]),
        Paragraph(clean(thesis.concise_thesis), styles["thesis"]),
        Spacer(1, 0.12 * inch),
        thesis_conditions(thesis, styles),
        Spacer(1, 0.15 * inch),
    ]
    figure = figures.get("index-spy") or next(iter(figures.values()), None)
    if figure:
        story.append(figure_block(figure, styles, compact=False))
    story.extend([
        Spacer(1, 0.1 * inch),
        Paragraph("CONTENTS  Structure  /  Participation  /  Leadership  /  Research Focus  /  Cross-Asset  /  Risk  /  Scenarios  /  Securities  /  Operating Plan", styles["contents"]),
    ])
    return story


def cover_story_stage6(document: ReportDocument, section: Any, styles: dict[str, ParagraphStyle]) -> list[Any]:
    thesis = document.thesis
    inquiry = document.research_inquiry
    if document.research_focus:
        focus = document.research_focus
        inquiry_answer = (
            f"{focus.subject} is the qualified {focus.direction} research priority at {focus.priority_score:.1f}/100. "
            "Section 6 tests the supporting evidence, counter-evidence, and failure conditions."
        )
    elif inquiry and inquiry.status == "no_focus":
        inquiry_answer = "No subject passed every research gate; standalone coverage is withheld rather than replaced with a lower-quality topic."
    else:
        inquiry_answer = "No structured research inquiry is available in this stored report."
    inquiry_question = inquiry.question if inquiry else "Which market question deserves research?"
    story: list[Any] = [
        Spacer(1, 0.06 * inch),
        Paragraph("MARKET INTELLIGENCE RESEARCH", styles["kicker"]),
        Paragraph(clean(document.title), styles["cover_title"]),
        Paragraph(f"{clean(document.report_type)}  |  Market date {clean(document.market_date)}  |  Generated {clean(document.generated_at)}", styles["meta"]),
        Spacer(1, 0.17 * inch),
        thin_rule(),
        Spacer(1, 0.14 * inch),
        Paragraph(f"CURRENT POSTURE  {clean(thesis.posture)}", styles["posture"]),
        Paragraph(clean(thesis.concise_thesis), styles["thesis"]),
        Spacer(1, 0.12 * inch),
        thesis_conditions(thesis, styles),
        Spacer(1, 0.18 * inch),
        Paragraph("TODAY'S RESEARCH QUESTION", styles["table_label"]),
        Paragraph(clean(inquiry_question), styles["research_question"]),
        Spacer(1, 0.05 * inch),
        Paragraph(clean(inquiry_answer), styles["executive_answer"]),
        Spacer(1, 0.18 * inch),
        Paragraph("CONTENTS", styles["table_label"]),
        Paragraph("Structure  /  Participation  /  Leadership  /  Research Question  /  Cross-Asset  /  Risk  /  Scenarios  /  Securities  /  Operating Plan", styles["contents"]),
        Spacer(1, 0.12 * inch),
        Paragraph("Every conclusion is linked to frozen evidence. Missing observations remain missing; relationship arrows encode validated structure, not forecasts.", styles["disclaimer"]),
    ]
    return story


def section_heading(number_value: int, title: str, purpose: str, styles: dict[str, ParagraphStyle], compact: bool = False, question: str | None = None) -> list[Any]:
    result = [
        Paragraph(f"{number_value:02d}  {clean(title).upper()}", styles["section"]),
    ]
    if question:
        result.append(Paragraph(clean(question), styles["section_question"]))
    result.extend([
        Paragraph(clean(purpose), styles["section_purpose"]),
        Spacer(1, 0.05 * inch if compact else 0.09 * inch),
        thin_rule(),
        Spacer(1, 0.08 * inch),
    ])
    return result


def research_focus_header(document: ReportDocument, styles: dict[str, ParagraphStyle]) -> list[Any]:
    focus = document.research_focus
    if focus is None:
        return []
    relevance = focus.user_relevance
    why = "<br/>".join(f"- {clean(item)}" for item in focus.why_selected[:4])
    evidence = "<br/>".join(f"- {clean(item)}" for item in focus.key_evidence[:4])
    summary = Table([
        [Paragraph("SUBJECT", styles["table_label"]), Paragraph("CLASSIFICATION", styles["table_label"]), Paragraph("PRIORITY", styles["table_label"]), Paragraph("USER RELEVANCE", styles["table_label"])],
        [Paragraph(f"<b>{clean(focus.subject)}</b><br/>{clean(focus.category.replace('_', ' ').title())}", styles["table_body"]), Paragraph(clean(focus.classification_label), styles["table_body"]), Paragraph(f"<b>{focus.priority_score:.1f}</b> / 100", styles["table_body"]), Paragraph(f"{clean(relevance.tier.title())}<br/>{len(relevance.saved_security_symbols)} saved securities", styles["table_body"])],
    ], colWidths=[2.25 * inch, 1.45 * inch, 1.15 * inch, 2.05 * inch])
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF7FB")),
        ("BOX", (0, 0), (-1, -1), 0.5, RULE), ("INNERGRID", (0, 0), (-1, -1), 0.25, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    thesis = Table([
        [Paragraph("MAIN THESIS", styles["table_label"]), Paragraph(clean(focus.main_thesis), styles["table_body"])],
        [Paragraph("COUNTER-THESIS", styles["table_label"]), Paragraph(clean(focus.counter_thesis), styles["table_body"])],
        [Paragraph("WHY SELECTED", styles["table_label"]), Paragraph(why, styles["table_body"])],
        [Paragraph("KEY EVIDENCE", styles["table_label"]), Paragraph(evidence, styles["table_body"])],
    ], colWidths=[1.08 * inch, 5.82 * inch])
    thesis.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F2F4F7")),
        ("BOX", (0, 0), (-1, -1), 0.5, RULE), ("INNERGRID", (0, 0), (-1, -1), 0.25, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return [summary, Spacer(1, 0.09 * inch), thesis, Spacer(1, 0.12 * inch)]


def research_inquiry_header_stage6(document: ReportDocument, styles: dict[str, ParagraphStyle]) -> list[Any]:
    inquiry = document.research_inquiry
    focus = document.research_focus
    if inquiry is None:
        return research_focus_header(document, styles)
    answer = Table([[Paragraph("EXECUTIVE ANSWER", styles["table_label"]), Paragraph(clean(inquiry.executive_answer), styles["executive_answer_small"]) ]], colWidths=[1.15 * inch, 5.75 * inch])
    answer.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#EAF7FB")),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#F8FCFD")),
        ("BOX", (0, 0), (-1, -1), 0.6, RULE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    if focus is None:
        return [answer, Spacer(1, 0.1 * inch), Paragraph("Standalone coverage was withheld. The priority tree below shows the reviewed candidates and failed evidence gates; no substitute subject is invented.", styles["body"]), Spacer(1, 0.08 * inch)]
    quality = focus.evidence_quality
    quality_values = [
        ("OVERALL", quality.label if quality else "Unavailable"),
        ("FRESHNESS", quality.freshness if quality else "Unavailable"),
        ("BREADTH", quality.breadth if quality else "Unavailable"),
        ("PARTICIPATION", quality.participation if quality else "Unavailable"),
        ("COMPLETENESS", quality.completeness if quality else "Unavailable"),
        ("CONSISTENCY", quality.consistency if quality else "Unavailable"),
    ]
    quality_table = Table([
        [Paragraph(label, styles["table_label"]) for label, _ in quality_values],
        [Paragraph(f"<b>{clean(value)}</b>", styles["table_body"]) for _, value in quality_values],
    ], colWidths=[1.15 * inch] * 6)
    quality_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F4F7")),
        ("BOX", (0, 0), (-1, -1), 0.5, RULE), ("INNERGRID", (0, 0), (-1, -1), 0.25, RULE),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    leader_text = "<br/>".join(
        f"<b>{clean(item.symbol)}</b> | {clean(item.metric_label)} {clean(item.metric_value)}{' | SAVED' if item.saved else ''}"
        for item in focus.leading_securities[:3]
    ) or "Constituent leader evidence unavailable."
    laggard_text = "<br/>".join(
        f"<b>{clean(item.symbol)}</b> | {clean(item.metric_label)} {clean(item.metric_value)}{' | SAVED' if item.saved else ''}"
        for item in focus.lagging_securities[:3]
    ) or "Constituent laggard evidence unavailable."
    leadership = Table([
        [Paragraph("RELATIVE LEADERS", styles["table_label"]), Paragraph("RELATIVE LAGGARDS", styles["table_label"])],
        [Paragraph(leader_text, styles["table_body"]), Paragraph(laggard_text, styles["table_body"])],
    ], colWidths=[3.45 * inch, 3.45 * inch])
    leadership.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#ECFDF3")),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#FEF3F2")),
        ("BOX", (0, 0), (-1, -1), 0.5, RULE), ("INNERGRID", (0, 0), (-1, -1), 0.25, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return [
        answer, Spacer(1, 0.07 * inch), quality_table,
        Spacer(1, 0.07 * inch), leadership, Spacer(1, 0.09 * inch),
    ]


def figure_block(figure: FigureSpec, styles: dict[str, ParagraphStyle], compact: bool, stage6: bool = False) -> KeepTogether:
    height = stage6_figure_height(figure) if stage6 else (2.28 * inch if compact else 3.55 * inch)
    source = ", ".join(figure.source_ids)
    quality = f"{figure.quality.state}; {figure.quality.completeness:.0%} complete"
    caption = (
        f"<b>Observation.</b> {clean(figure.observation)}<br/>"
        f"<b>Interpretation.</b> {clean(figure.interpretation)}<br/>"
        f"<b>Confirmation.</b> {clean(figure.confirmation_condition)}  "
        f"<b>Risk.</b> {clean(figure.risk_condition)}"
    )
    blocks: list[Any] = [
        Paragraph(f"Figure {figure.figure_number}. {clean(figure.title)}", styles["figure_title"]),
        Paragraph(f"{clean(figure.subtitle)}  |  {clean(figure.timeframe)}  |  As of {clean(figure.as_of or 'unavailable')}", styles["figure_meta"]),
    ]
    if stage6:
        blocks.append(Paragraph(f"QUESTION ANSWERED  {clean(figure.question_answered)}", styles["figure_question"]))
    blocks.extend([
        Spacer(1, 0.04 * inch),
        ResearchFigure(figure, 7.0 * inch, height),
        Spacer(1, 0.06 * inch),
        Paragraph(caption, styles["caption"]),
        Paragraph(f"Source: {clean(source)}  |  Quality: {clean(quality)}", styles["source"]),
    ])
    return KeepTogether(blocks)


def stage6_figure_height(figure: FigureSpec) -> float:
    chart_type = figure.chart_type
    if chart_type == "stock_setup":
        return 2.65 * inch
    if chart_type in {"research_chain", "relationship_map", "sector_influence_map"}:
        depths = [int(point.get("depth") or 0) for series in figure.data_series if series.unit == "relationship_nodes" for point in series.points]
        return min(2.55, max(2.05, 1.65 + 0.16 * (max(depths, default=1) + 1))) * inch
    if chart_type == "research_timeline":
        return 4.1 * inch
    if chart_type in {"evidence_matrix", "decision_framework", "research_evolution"}:
        return 2.3 * inch
    if chart_type == "rotation":
        return 4.1 * inch
    if chart_type == "relative_strength_flow":
        return 4.1 * inch
    if chart_type == "risk_history":
        return 3.6 * inch
    if chart_type in {"research_priority_tree", "priority_comparison"}:
        return 2.2 * inch
    if chart_type in {"heatmap", "leadership_matrix"}:
        rows = len(figure.data_series[0].points) if figure.data_series else 0
        return min(2.45, max(1.45, 0.8 + rows * 0.17)) * inch
    return 2.2 * inch


class ResearchFigure(Flowable):
    def __init__(self, figure: FigureSpec, width: float, height: float) -> None:
        super().__init__()
        self.figure = figure
        self.width = width
        self.height = height

    def draw(self) -> None:
        canvas = self.canv
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#FCFCFD"))
        canvas.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        if self.figure.chart_type in {"heatmap", "leadership_matrix"}:
            self._draw_heatmap(canvas)
        elif self.figure.chart_type == "rotation":
            self._draw_rotation(canvas)
        elif self.figure.chart_type in {"priority_comparison", "research_priority_tree"}:
            self._draw_priority_comparison(canvas)
        elif self.figure.chart_type == "market_timeline":
            self._draw_market_timeline(canvas)
        elif self.figure.chart_type == "research_timeline":
            self._draw_research_timeline(canvas)
        elif self.figure.chart_type in {"research_chain", "relationship_map", "sector_influence_map"}:
            self._draw_research_chain(canvas)
        elif self.figure.chart_type == "evidence_matrix":
            self._draw_evidence_matrix(canvas)
        elif self.figure.chart_type == "relative_strength_flow":
            self._draw_relative_strength_flow(canvas)
        elif self.figure.chart_type in {"decision_framework", "research_evolution"}:
            self._draw_decision_framework(canvas)
        elif self.figure.chart_type in {
            "price_with_volume", "stock_setup", "ratio", "breadth_history", "breadth_internals",
            "price_volume", "relative_strength", "breadth_time_series", "normalized_multi_asset",
            "risk_history", "return_profile", "line",
        }:
            self._draw_lines(canvas)
        else:
            self._empty(canvas, f"Unsupported figure type: {self.figure.chart_type}")
        canvas.restoreState()

    def _draw_lines(self, canvas: Any) -> None:
        has_label_rail = bool(self.figure.reference_lines or self.figure.annotations)
        left, right, bottom, top = 38, 96 if has_label_rail else 12, 22, 18
        plot_w = self.width - left - right
        plot_h = self.height - bottom - top
        line_series = [item for item in self.figure.data_series if item.unit != "shares"]
        volume_series = next((item for item in self.figure.data_series if item.unit == "shares"), None)
        values = [numeric(point.get("value")) for item in line_series for point in item.points]
        values = [value for value in values if value is not None]
        if not values:
            self._empty(canvas)
            return
        low, high = min(values), max(values)
        padding = max((high - low) * 0.08, abs(high) * 0.01, 0.01)
        low -= padding
        high += padding
        volume_h = plot_h * 0.18 if volume_series else 0
        line_bottom = bottom + volume_h
        line_h = plot_h - volume_h
        canvas.setStrokeColor(GRID)
        canvas.setLineWidth(0.45)
        for index in range(5):
            y = line_bottom + line_h * index / 4
            canvas.line(left, y, left + plot_w, y)
            value = low + (high - low) * index / 4
            canvas.setFillColor(MUTED)
            canvas.setFont("Helvetica", 5.5)
            canvas.drawRightString(left - 3, y - 2, compact_number(value))
        max_points = max((len(item.points) for item in line_series), default=1)
        for series_index, item in enumerate(line_series):
            point_values = [(index, numeric(point.get("value"))) for index, point in enumerate(item.points)]
            point_values = [(index, value) for index, value in point_values if value is not None]
            if len(point_values) < 2:
                continue
            color = colors.HexColor(item.color) if item.color else SERIES_COLORS[series_index % len(SERIES_COLORS)]
            canvas.setStrokeColor(color)
            canvas.setLineWidth(1.35 if series_index == 0 else 0.85)
            path_value = canvas.beginPath()
            for point_index, (index, value) in enumerate(point_values):
                x = left + (index / max(1, max_points - 1)) * plot_w
                y = line_bottom + ((value - low) / max(0.000001, high - low)) * line_h
                (path_value.moveTo if point_index == 0 else path_value.lineTo)(x, y)
            canvas.drawPath(path_value, stroke=1, fill=0)
        if volume_series:
            volume_values = [numeric(point.get("value")) or 0 for point in volume_series.points]
            peak = max(volume_values, default=0)
            if peak > 0:
                canvas.setFillColor(colors.HexColor("#D0D5DD"))
                bar_width = max(0.4, plot_w / max(1, len(volume_values)) * 0.72)
                for index, value in enumerate(volume_values):
                    x = left + (index / max(1, len(volume_values) - 1)) * plot_w
                    canvas.rect(x - bar_width / 2, bottom, bar_width, volume_h * value / peak, fill=1, stroke=0)
        label_items: list[tuple[str, str, float, float, float, colors.Color]] = []
        type_colors = {
            "support": GREEN, "resistance": ORANGE, "breakout": BLUE, "failed_breakout": RED,
            "gap": PURPLE, "pivot": ORANGE, "ema": BLUE, "trendline": PURPLE,
            "previous_report": colors.HexColor("#475467"), "previous_report_marker": colors.HexColor("#475467"),
            "current_thesis": BLUE, "risk": RED, "confirmation": GREEN, "confirmation_arrow": GREEN,
            "invalidation": RED, "recent_high": ORANGE, "recent_low": ORANGE,
        }
        for reference in self.figure.reference_lines:
            value = numeric(reference.get("value"))
            if value is None or not low <= value <= high:
                continue
            y = line_bottom + ((value - low) / max(0.000001, high - low)) * line_h
            label = str(reference.get("label") or "Level")
            color = type_colors.get(label.lower().replace(" ", "_"), ORANGE)
            canvas.setStrokeColor(color)
            canvas.setDash(3, 2); canvas.setLineWidth(0.65); canvas.line(left, y, left + plot_w, y); canvas.setDash()
            label_items.append(("reference", f"{label} {compact_number(value)}", left + plot_w, y, y, color))
        for annotation in self.figure.annotations:
            if str(annotation.freshness).lower() in {"stale", "unavailable"}:
                continue
            value = numeric(annotation.value)
            index = annotation.point_index
            if value is None or index is None or not low <= value <= high:
                continue
            x = left + (index / max(1, max_points - 1)) * plot_w
            y = line_bottom + ((value - low) / max(0.000001, high - low)) * line_h
            color = type_colors.get(annotation.annotation_type, ORANGE)
            canvas.setFillColor(color); canvas.circle(x, y, 2.4, fill=1, stroke=0)
            label_items.append(("annotation", short_figure_label(annotation.label), x, y, y, color))
        deduplicated_labels: list[tuple[str, str, float, float, float, colors.Color]] = []
        for item in label_items:
            matching_index = next(
                (index for index, existing in enumerate(deduplicated_labels) if abs(existing[4] - item[4]) < 0.75),
                None,
            )
            if matching_index is None:
                deduplicated_labels.append(item)
                continue
            existing = deduplicated_labels[matching_index]
            if existing[0] == "reference":
                continue
            if item[0] == "reference" or "confirm" in item[1].casefold():
                deduplicated_labels[matching_index] = item
        label_items = deduplicated_labels
        label_positions = spread_label_positions(
            [item[4] for item in label_items], lower=line_bottom + 4, upper=line_bottom + line_h - 4, min_gap=9,
        )
        rail_x = left + plot_w + 5
        for (_, label, x, y, _, color), label_y in zip(label_items, label_positions):
            canvas.setStrokeColor(color); canvas.setLineWidth(0.45); canvas.line(x, y, rail_x - 2, label_y)
            label_text = fit(label, 24)
            label_width = min(right - 8, stringWidth(label_text, "Helvetica-Bold", 6.1) + 6)
            canvas.setFillColor(colors.white); canvas.roundRect(rail_x, label_y - 4, label_width, 9, 2, fill=1, stroke=0)
            canvas.setFillColor(color); canvas.setFont("Helvetica-Bold", 6.1); canvas.drawString(rail_x + 3, label_y - 1, label_text)
        self._legend(canvas, line_series)

    def _draw_priority_comparison(self, canvas: Any) -> None:
        points = self.figure.data_series[0].points if self.figure.data_series else []
        if not points:
            self._empty(canvas)
            return
        left, right, bottom, top = 105, 34, 20, 12
        plot_w = self.width - left - right
        row_h = max(14, (self.height - bottom - top) / max(1, len(points)))
        threshold = next((numeric(item.get("value")) for item in self.figure.reference_lines if item.get("label") == "Materiality threshold"), 60) or 60
        threshold_x = left + plot_w * threshold / 100
        canvas.setStrokeColor(ORANGE); canvas.setDash(3, 2); canvas.line(threshold_x, bottom, threshold_x, self.height - top); canvas.setDash()
        canvas.setFillColor(MUTED); canvas.setFont("Helvetica-Bold", 5.5); canvas.drawCentredString(threshold_x, self.height - 8, f"THRESHOLD {threshold:.0f}")
        for index, point in enumerate(points):
            value = max(0, min(100, numeric(point.get("value")) or 0))
            y = self.height - top - (index + 1) * row_h + 3
            selected = bool(point.get("selected"))
            direction = str(point.get("direction") or "")
            fill = BLUE if selected else GREEN if direction in {"leading", "emerging"} else RED if direction in {"weakening", "lagging", "breakdown"} else PURPLE
            canvas.setFillColor(colors.HexColor("#F2F4F7")); canvas.rect(left, y, plot_w, row_h - 5, fill=1, stroke=0)
            canvas.setFillColor(fill); canvas.rect(left, y, plot_w * value / 100, row_h - 5, fill=1, stroke=0)
            canvas.setFillColor(INK); canvas.setFont("Helvetica-Bold" if selected else "Helvetica", 6.2)
            canvas.drawRightString(left - 5, y + row_h / 2 - 2, fit(str(point.get("label") or ""), 25))
            canvas.drawString(min(left + plot_w - 22, left + plot_w * value / 100 + 3), y + row_h / 2 - 2, f"{value:.1f}")

    def _draw_market_timeline(self, canvas: Any) -> None:
        points = self.figure.data_series[0].points if self.figure.data_series else []
        if not points:
            self._empty(canvas)
            return
        columns = [
            ("DATE", 58, "market_date"), ("REGIME", 78, "regime"), ("HEALTH", 42, "market_health"),
            ("BREADTH", 46, "breadth"), ("RISK", 38, "risk"), ("LEADER", 82, "primary_leader"), ("LAGGARD", 82, "primary_laggard"),
        ]
        total = sum(width for _, width, _ in columns)
        scale = (self.width - 8) / total
        widths = [width * scale for _, width, _ in columns]
        row_h = min(20, (self.height - 20) / max(1, len(points)))
        x = 4
        canvas.setFillColor(INK); canvas.rect(4, self.height - 18, self.width - 8, 15, fill=1, stroke=0)
        for (label, _, _), width in zip(columns, widths):
            canvas.setFillColor(colors.white); canvas.setFont("Helvetica-Bold", 5.6); canvas.drawString(x + 3, self.height - 13, label)
            x += width
        for row_index, point in enumerate(points):
            y = self.height - 18 - (row_index + 1) * row_h
            canvas.setFillColor(colors.white if row_index % 2 == 0 else colors.HexColor("#F9FAFB")); canvas.rect(4, y, self.width - 8, row_h, fill=1, stroke=0)
            x = 4
            for (_, _, key), width in zip(columns, widths):
                value = point.get(key)
                text = "--" if value is None else f"{float(value):.0f}" if key in {"market_health", "breadth", "risk"} and numeric(value) is not None else str(value)
                canvas.setFillColor(INK); canvas.setFont("Helvetica", 5.8); canvas.drawString(x + 3, y + row_h / 2 - 2, fit(text, max(4, int(width / 4.1))))
                x += width

    def _draw_research_timeline(self, canvas: Any) -> None:
        points = (self.figure.data_series[0].points if self.figure.data_series else [])[-10:]
        if not points:
            self._empty(canvas)
            return
        left, right, bottom = 28, 8, 20
        band_height = 54
        band_bottom = self.height - band_height - 4
        plot_top = band_bottom - 10
        plot_w = self.width - left - right
        plot_h = plot_top - bottom
        cell_w = plot_w / max(1, len(points))
        for index, point in enumerate(points):
            cell_x = left + index * cell_w
            canvas.setFillColor(colors.white if index % 2 == 0 else colors.HexColor("#F8FAFC"))
            canvas.setStrokeColor(GRID); canvas.setLineWidth(0.35)
            canvas.rect(cell_x, band_bottom, cell_w, band_height, fill=1, stroke=1)
            center_x = cell_x + cell_w / 2
            text_width = max(12, cell_w - 5)
            date = str(point.get("market_date") or "")
            regime = fit_to_width(str(point.get("regime") or "--"), text_width, "Helvetica-Bold", 5.2)
            focus = fit_to_width(str(point.get("research_focus") or "No focus"), text_width, "Helvetica-Bold", 5.0)
            leader = fit_to_width(str(point.get("primary_leader") or "--"), text_width, "Helvetica", 4.6)
            volatility = fit_to_width(str(point.get("volatility_state") or "--"), text_width, "Helvetica", 4.6)
            canvas.setFillColor(MUTED); canvas.setFont("Helvetica", 4.8)
            canvas.drawCentredString(center_x, band_bottom + 43, date[5:] or "--")
            canvas.setFillColor(INK); canvas.setFont("Helvetica-Bold", 5.2)
            canvas.drawCentredString(center_x, band_bottom + 32, regime)
            canvas.setFillColor(BLUE); canvas.setFont("Helvetica-Bold", 5.0)
            canvas.drawCentredString(center_x, band_bottom + 21, focus)
            canvas.setFillColor(MUTED); canvas.setFont("Helvetica", 4.6)
            canvas.drawCentredString(center_x, band_bottom + 11, leader)
            canvas.drawCentredString(center_x, band_bottom + 3, volatility)
        canvas.setStrokeColor(GRID); canvas.setLineWidth(0.4)
        for level in (0, 25, 50, 75, 100):
            y = bottom + plot_h * level / 100
            canvas.line(left, y, left + plot_w, y)
            canvas.setFillColor(MUTED); canvas.setFont("Helvetica", 5.5); canvas.drawRightString(left - 3, y - 2, str(level))
        breadth_positions: list[tuple[float, float]] = []
        risk_positions: list[tuple[float, float]] = []
        for index, point in enumerate(points):
            x = left + (index + 0.5) * cell_w
            breadth = numeric(point.get("breadth"))
            risk = numeric(point.get("risk"))
            if breadth is not None:
                breadth_positions.append((x, bottom + plot_h * max(0, min(100, breadth)) / 100))
            if risk is not None:
                risk_positions.append((x, bottom + plot_h * max(0, min(100, risk)) / 100))
        for positions, color in ((breadth_positions, BLUE), (risk_positions, RED)):
            if len(positions) >= 2:
                path_value = canvas.beginPath()
                for index, (x, y) in enumerate(positions):
                    (path_value.moveTo if index == 0 else path_value.lineTo)(x, y)
                canvas.setStrokeColor(color); canvas.setLineWidth(1.4); canvas.drawPath(path_value, stroke=1, fill=0)
            canvas.setFillColor(color)
            for x, y in positions:
                canvas.circle(x, y, 2.2, fill=1, stroke=0)
        canvas.setFont("Helvetica-Bold", 5.8); canvas.setFillColor(BLUE); canvas.drawString(left, plot_top + 3, "BREADTH")
        canvas.setFillColor(RED); canvas.drawString(left + 55, plot_top + 3, "RISK")

    def _draw_research_chain(self, canvas: Any) -> None:
        nodes = [point for series in self.figure.data_series if series.unit == "relationship_nodes" for point in series.points]
        edges = [point for series in self.figure.data_series if series.unit == "relationship_edges" for point in series.points]
        if not nodes:
            self._empty(canvas)
            return
        node_by_id = {str(node.get("node_id")): node for node in nodes}
        outgoing: dict[str, list[str]] = {node_id: [] for node_id in node_by_id}
        indegree: dict[str, int] = {node_id: 0 for node_id in node_by_id}
        arrowheads: list[tuple[float, float, float, float]] = []
        for edge in edges:
            source_id = str(edge.get("source_node_id"))
            target_id = str(edge.get("target_node_id"))
            if source_id not in node_by_id or target_id not in node_by_id:
                continue
            outgoing[source_id].append(target_id)
            indegree[target_id] += 1
        ranks = {node_id: 0 for node_id in node_by_id}
        queue = sorted(node_id for node_id, count in indegree.items() if count == 0)
        visited: set[str] = set()
        while queue:
            source_id = queue.pop(0)
            visited.add(source_id)
            for target_id in outgoing[source_id]:
                ranks[target_id] = max(ranks[target_id], ranks[source_id] + 1)
                indegree[target_id] -= 1
                if indegree[target_id] == 0:
                    queue.append(target_id)
                    queue.sort()
        for node_id, node in node_by_id.items():
            if node_id not in visited:
                ranks[node_id] = int(node.get("depth") or 0)
        by_depth: dict[int, list[dict[str, Any]]] = {}
        for node in nodes:
            by_depth.setdefault(ranks[str(node.get("node_id"))], []).append(node)
        depths = sorted(by_depth)
        top_margin, bottom_margin = 15, 12
        vertical_step = (self.height - top_margin - bottom_margin) / max(1, len(depths) - 1)
        positions: dict[str, tuple[float, float, float, float]] = {}
        for depth_index, depth in enumerate(depths):
            row = sorted(by_depth[depth], key=lambda item: str(item.get("label") or ""))
            gap = 6
            box_width = min(108, max(38, (self.width - 12 - gap * max(0, len(row) - 1)) / max(1, len(row))))
            total_width = box_width * len(row) + gap * max(0, len(row) - 1)
            start_x = (self.width - total_width) / 2
            y = self.height - top_margin - depth_index * vertical_step
            for node_index, node in enumerate(row):
                positions[str(node.get("node_id"))] = (start_x + node_index * (box_width + gap), y - 9, box_width, 18)
        for edge in edges:
            source = positions.get(str(edge.get("source_node_id")))
            target = positions.get(str(edge.get("target_node_id")))
            if not source or not target:
                continue
            source_cx, source_cy = source[0] + source[2] / 2, source[1] + source[3] / 2
            target_cx, target_cy = target[0] + target[2] / 2, target[1] + target[3] / 2
            dx, dy = target_cx - source_cx, target_cy - source_cy
            if abs(dy) >= abs(dx):
                x1, x2 = source_cx, target_cx
                if dy < 0:
                    y1, y2 = source[1], target[1] + target[3]
                else:
                    y1, y2 = source[1] + source[3], target[1]
            else:
                y1, y2 = source_cy, target_cy
                if dx < 0:
                    x1, x2 = source[0], target[0] + target[2]
                else:
                    x1, x2 = source[0] + source[2], target[0]
            canvas.setStrokeColor(colors.HexColor("#98A2B3")); canvas.setLineWidth(0.65); canvas.line(x1, y1, x2, y2)
            vector_x, vector_y = x2 - x1, y2 - y1
            vector_length = max(0.001, (vector_x * vector_x + vector_y * vector_y) ** 0.5)
            unit_x, unit_y = vector_x / vector_length, vector_y / vector_length
            arrowheads.append((x2, y2, unit_x, unit_y))
            if vector_length > 28:
                relation = str(edge.get("relationship_type") or edge.get("label") or "").replace("_", " ")
                relation = fit_to_width(relation, 78, "Helvetica", 4.5)
                label_x, label_y = (x1 + x2) / 2, (y1 + y2) / 2 + 1
                label_width = stringWidth(relation, "Helvetica", 4.5) + 5
                canvas.setFillColor(colors.white); canvas.rect(label_x - label_width / 2, label_y - 3, label_width, 7, fill=1, stroke=0)
                canvas.setFillColor(MUTED); canvas.setFont("Helvetica", 4.5)
                canvas.drawCentredString(label_x, label_y - 1, relation)
        node_colors = {
            "benchmark": colors.HexColor("#F2F4F7"), "sector": colors.HexColor("#EFF8FF"),
            "theme": colors.HexColor("#EAF7FB"), "industry": colors.HexColor("#F4F3FF"),
            "security": colors.HexColor("#ECFDF3"), "watchlist": colors.HexColor("#FFF6ED"),
        }
        for node in nodes:
            position = positions[str(node.get("node_id"))]
            x, y, width, height = position
            node_type = str(node.get("node_type") or "")
            canvas.setFillColor(node_colors.get(node_type, colors.white)); canvas.setStrokeColor(BLUE if node_type == "watchlist" else RULE)
            canvas.roundRect(x, y, width, height, 3, fill=1, stroke=1)
            canvas.setFillColor(INK); canvas.setFont("Helvetica-Bold", 5.7)
            canvas.drawCentredString(x + width / 2, y + 7, fit(str(node.get("label") or ""), max(6, int(width / 3.5))))
            canvas.setFillColor(MUTED); canvas.setFont("Helvetica", 4.5); canvas.drawCentredString(x + width / 2, y + 2, node_type.upper())
        # Paint arrowheads after node boxes so the target border cannot mask a
        # directed edge.  Only the tip touches the box; the body remains in the
        # relationship lane and therefore does not obscure node labels.
        canvas.setFillColor(colors.HexColor("#667085"))
        for x2, y2, unit_x, unit_y in arrowheads:
            tip_x, tip_y = x2 - unit_x * 0.8, y2 - unit_y * 0.8
            base_x, base_y = tip_x - unit_x * 6.2, tip_y - unit_y * 6.2
            perp_x, perp_y = -unit_y * 3.1, unit_x * 3.1
            path_value = canvas.beginPath()
            path_value.moveTo(tip_x, tip_y)
            path_value.lineTo(base_x + perp_x, base_y + perp_y)
            path_value.lineTo(base_x - perp_x, base_y - perp_y)
            path_value.close()
            canvas.drawPath(path_value, fill=1, stroke=0)

    def _draw_evidence_matrix(self, canvas: Any) -> None:
        rows = self.figure.data_series[0].points if self.figure.data_series else []
        if not rows:
            self._empty(canvas)
            return
        left = 4
        header_h = 16
        row_h = (self.height - header_h - 4) / max(1, len(rows))
        dimension_w = 88
        finding_w = self.width - dimension_w - 132 - 8
        stance_w = 44
        canvas.setFillColor(INK); canvas.rect(left, self.height - header_h, self.width - 8, header_h - 2, fill=1, stroke=0)
        headers = [("DIMENSION", left + 4), ("FINDING / IMPLICATION", left + dimension_w + 4)]
        for label, x in headers:
            canvas.setFillColor(colors.white); canvas.setFont("Helvetica-Bold", 5.6); canvas.drawString(x, self.height - 11, label)
        for index, label in enumerate(("SUPPORTS", "NEUTRAL", "CONTRADICTS")):
            x = left + dimension_w + finding_w + index * stance_w
            canvas.setFillColor(colors.white); canvas.setFont("Helvetica-Bold", 4.8); canvas.drawCentredString(x + stance_w / 2, self.height - 11, label)
        stance_colors = {"supports": GREEN, "neutral": ORANGE, "contradicts": RED}
        for row_index, row in enumerate(rows):
            y = self.height - header_h - (row_index + 1) * row_h
            canvas.setFillColor(colors.white if row_index % 2 == 0 else colors.HexColor("#F9FAFB")); canvas.rect(left, y, self.width - 8, row_h, fill=1, stroke=0)
            canvas.setFillColor(INK); canvas.setFont("Helvetica-Bold", 5.8)
            draw_wrapped(canvas, str(row.get("dimension") or ""), left + 4, y + row_h - 7, dimension_w - 8, 5.8, 2, bold=True)
            finding = f"{row.get('finding') or ''} {row.get('implication') or ''}"
            draw_wrapped(canvas, finding, left + dimension_w + 4, y + row_h - 6, finding_w - 8, 5.2, 3)
            stance = str(row.get("stance") or "neutral")
            selected_index = {"supports": 0, "neutral": 1, "contradicts": 2}.get(stance, 1)
            for stance_index in range(3):
                x = left + dimension_w + finding_w + stance_index * stance_w + stance_w / 2
                canvas.setFillColor(stance_colors.get(stance, ORANGE) if stance_index == selected_index else colors.HexColor("#EAECF0"))
                canvas.circle(x, y + row_h / 2, 3.4 if stance_index == selected_index else 2.1, fill=1, stroke=0)

    def _draw_relative_strength_flow(self, canvas: Any) -> None:
        points = self.figure.data_series[0].points if self.figure.data_series else []
        values = [numeric(point.get("value")) for point in points]
        values = [value for value in values if value is not None]
        if not values:
            self._empty(canvas)
            return
        left, right, bottom, top = 70, 28, 18, 14
        plot_w = self.width - left - right
        row_h = (self.height - bottom - top) / max(1, len(points))
        magnitude = max(abs(value) for value in values) or 1
        zero_x = left + plot_w / 2
        canvas.setStrokeColor(RULE); canvas.setLineWidth(0.7); canvas.line(zero_x, bottom, zero_x, self.height - top)
        for index, point in enumerate(points):
            value = numeric(point.get("value"))
            if value is None:
                continue
            y = self.height - top - (index + 1) * row_h + row_h * 0.2
            width = abs(value) / magnitude * (plot_w / 2 - 8)
            x = zero_x if value >= 0 else zero_x - width
            fill = GREEN if value >= 0 else RED
            if point.get("kind") == "benchmark_relative":
                fill = BLUE
            canvas.setFillColor(fill); canvas.rect(x, y, width, row_h * 0.55, fill=1, stroke=0)
            canvas.setFillColor(INK); canvas.setFont("Helvetica-Bold", 6.2); canvas.drawRightString(left - 5, y + 2, fit(str(point.get("label") or ""), 18))
            if value >= 0:
                canvas.drawString(x + width + 4, y + 2, f"{value:+.1f}")
            else:
                # Keep negative values adjacent to the zero line so long values
                # cannot collide with the period label at the left margin.
                canvas.setFillColor(colors.white)
                canvas.drawRightString(zero_x - 4, y + 2, f"{value:+.1f}")

    def _draw_decision_framework(self, canvas: Any) -> None:
        points = self.figure.data_series[0].points if self.figure.data_series else []
        if not points:
            self._empty(canvas)
            return
        top_points = points[:3]
        bottom_points = points[3:5]
        card_gap = 7
        top_h = self.height - 8 if not bottom_points else self.height * 0.48
        top_w = (self.width - 8 - card_gap * max(0, len(top_points) - 1)) / max(1, len(top_points))
        tone_colors = {"neutral": colors.HexColor("#F2F4F7"), "current": colors.HexColor("#EAF7FB"), "confirmation": colors.HexColor("#ECFDF3"), "execution": colors.HexColor("#F0F9FF"), "risk": colors.HexColor("#FFF6ED")}
        for index, point in enumerate(top_points):
            x = 4 + index * (top_w + card_gap)
            y = 4 if not bottom_points else self.height - top_h - 4
            draw_decision_card(canvas, point, x, y, top_w, top_h - 4, tone_colors)
            if index < len(top_points) - 1:
                canvas.setStrokeColor(BLUE); canvas.setLineWidth(0.7); canvas.line(x + top_w + 1, y + top_h / 2, x + top_w + card_gap - 1, y + top_h / 2)
        if bottom_points:
            bottom_y = 4
            bottom_h = self.height - top_h - 13
            bottom_w = (self.width - 8 - card_gap * max(0, len(bottom_points) - 1)) / len(bottom_points)
            for index, point in enumerate(bottom_points):
                x = 4 + index * (bottom_w + card_gap)
                draw_decision_card(canvas, point, x, bottom_y, bottom_w, bottom_h, tone_colors)

    def _draw_heatmap(self, canvas: Any) -> None:
        points = self.figure.data_series[0].points if self.figure.data_series else []
        if not points:
            self._empty(canvas)
            return
        periods = [key for key in ("1d", "1w", "1m", "3m", "6m", "1y") if any(point.get(key) is not None for point in points)]
        left = 112
        top = self.height - 24
        row_h = min(18, (self.height - 35) / max(1, len(points)))
        col_w = (self.width - left - 8) / max(1, len(periods))
        canvas.setFont("Helvetica-Bold", 6.5)
        canvas.setFillColor(MUTED)
        for index, period in enumerate(periods):
            canvas.drawCentredString(left + index * col_w + col_w / 2, top + 8, period.upper())
        magnitude = max([abs(numeric(point.get(period)) or 0) for point in points for period in periods] or [1])
        for row_index, point in enumerate(points):
            y = top - (row_index + 1) * row_h
            canvas.setFillColor(INK)
            canvas.setFont("Helvetica", 6.4)
            canvas.drawString(4, y + row_h / 2 - 2, fit(str(point.get("label") or ""), 30))
            for col_index, period in enumerate(periods):
                value = numeric(point.get(period))
                x = left + col_index * col_w
                fill = colors.HexColor("#F2F4F7") if value is None else blend(colors.white, GREEN if value >= 0 else RED, min(0.75, abs(value) / max(0.001, magnitude) * 0.75))
                canvas.setFillColor(fill)
                canvas.rect(x + 1, y + 1, col_w - 2, row_h - 2, fill=1, stroke=0)
                canvas.setFillColor(INK)
                canvas.setFont("Helvetica-Bold", 6.1)
                canvas.drawCentredString(x + col_w / 2, y + row_h / 2 - 2, "--" if value is None else f"{value:+.1f}%")

    def _draw_rotation(self, canvas: Any) -> None:
        left, bottom, right_rail, top = 34, 24, 112, 18
        width, height = self.width - left - right_rail, self.height - bottom - top
        points = [(numeric(point.get("x")), numeric(point.get("y"))) for item in self.figure.data_series for point in item.points]
        values = [value for pair in points for value in pair if value is not None]
        if not values:
            self._empty(canvas)
            return
        distance = max(5, max(abs(value - 100) for value in values) * 1.12)
        low, high = 100 - distance, 100 + distance
        canvas.setFillColor(colors.HexColor("#ECFDF3")); canvas.rect(left + width / 2, bottom + height / 2, width / 2, height / 2, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#EFF8FF")); canvas.rect(left, bottom + height / 2, width / 2, height / 2, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#FFF4ED")); canvas.rect(left + width / 2, bottom, width / 2, height / 2, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#FEF3F2")); canvas.rect(left, bottom, width / 2, height / 2, fill=1, stroke=0)
        canvas.setStrokeColor(RULE); canvas.line(left + width / 2, bottom, left + width / 2, bottom + height); canvas.line(left, bottom + height / 2, left + width, bottom + height / 2)
        terminal_labels: list[tuple[str, float, float, colors.Color]] = []
        for series_index, item in enumerate(self.figure.data_series):
            clean_points = [(numeric(point.get("x")), numeric(point.get("y"))) for point in item.points]
            clean_points = [(x, y) for x, y in clean_points if x is not None and y is not None]
            if not clean_points:
                continue
            color = SERIES_COLORS[series_index % len(SERIES_COLORS)]
            canvas.setStrokeColor(color); canvas.setLineWidth(0.9)
            prior = None
            for point_index, (x_value, y_value) in enumerate(clean_points):
                x = left + (x_value - low) / (high - low) * width
                y = bottom + (y_value - low) / (high - low) * height
                if prior: canvas.line(prior[0], prior[1], x, y)
                prior = (x, y)
                if point_index == len(clean_points) - 1:
                    canvas.setFillColor(color); canvas.circle(x, y, 2.8, fill=1, stroke=0)
                    terminal_labels.append((str(item.label), x, y, color))
        label_positions = spread_label_positions(
            [item[2] for item in terminal_labels],
            lower=bottom + 12,
            upper=bottom + height - 12,
            min_gap=12,
        )
        rail_x = left + width + 8
        for (label, x, y, color), label_y in zip(terminal_labels, label_positions):
            canvas.setStrokeColor(color); canvas.setLineWidth(0.55)
            canvas.line(x, y, rail_x - 3, label_y)
            label_text = fit_to_width(label, right_rail - 21, "Helvetica-Bold", 6)
            canvas.setFillColor(colors.white); canvas.setStrokeColor(colors.HexColor("#E4E7EC"))
            canvas.roundRect(rail_x, label_y - 5, right_rail - 13, 11, 2, fill=1, stroke=1)
            canvas.setFillColor(color); canvas.setFont("Helvetica-Bold", 6)
            canvas.drawString(rail_x + 4, label_y - 2, label_text)
        canvas.setFillColor(MUTED); canvas.setFont("Helvetica-Bold", 6)
        canvas.drawString(left + 3, bottom + height - 9, "IMPROVING")
        canvas.drawRightString(left + width - 3, bottom + height - 9, "LEADING")
        canvas.drawString(left + 3, bottom + 4, "LAGGING")
        canvas.drawRightString(left + width - 3, bottom + 4, "WEAKENING")

    def _legend(self, canvas: Any, series: list[Any]) -> None:
        x = 42
        y = self.height - 11
        for index, item in enumerate(series[:7]):
            color = colors.HexColor(item.color) if item.color else SERIES_COLORS[index % len(SERIES_COLORS)]
            canvas.setStrokeColor(color); canvas.setLineWidth(1.4); canvas.line(x, y, x + 10, y)
            canvas.setFillColor(MUTED); canvas.setFont("Helvetica", 5.7); canvas.drawString(x + 13, y - 2, fit(item.label, 18))
            x += 18 + stringWidth(fit(item.label, 18), "Helvetica", 5.7)
            if x > self.width - 95: break

    def _empty(self, canvas: Any, message: str = "Qualified figure data unavailable") -> None:
        canvas.setFillColor(MUTED); canvas.setFont("Helvetica", 8); canvas.drawCentredString(self.width / 2, self.height / 2, fit(message, 80))


def draw_wrapped(canvas: Any, value: str, x: float, y: float, width: float, font_size: float, max_lines: int, *, bold: bool = False) -> None:
    font_name = "Helvetica-Bold" if bold else "Helvetica"
    words = str(value or "").split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if stringWidth(candidate, font_name, font_size) <= width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and len(" ".join(lines).split()) < len(words):
        lines[-1] = fit(lines[-1], max(5, len(lines[-1]) - 3)) + "..."
    canvas.setFont(font_name, font_size); canvas.setFillColor(INK)
    for index, line in enumerate(lines):
        canvas.drawString(x, y - index * (font_size + 1.5), line)


def draw_decision_card(canvas: Any, point: dict[str, Any], x: float, y: float, width: float, height: float, tone_colors: dict[str, colors.Color]) -> None:
    tone = str(point.get("tone") or "neutral")
    canvas.setFillColor(tone_colors.get(tone, colors.white)); canvas.setStrokeColor(RULE)
    canvas.roundRect(x, y, width, height, 4, fill=1, stroke=1)
    canvas.setFillColor(BLUE if tone in {"current", "confirmation", "execution"} else RED if tone == "risk" else MUTED)
    canvas.setFont("Helvetica-Bold", 6); canvas.drawString(x + 6, y + height - 11, fit(str(point.get("stage") or ""), max(8, int(width / 4))))
    draw_wrapped(canvas, str(point.get("text") or ""), x + 6, y + height - 21, width - 12, 5.4, max(2, int((height - 24) / 7)))


def claim_strip(statement: str, interpretation: str, implication: str, styles: dict[str, ParagraphStyle]) -> Table:
    rows = [[Paragraph("SUPPORTED CLAIM", styles["table_label"]), Paragraph(clean(statement), styles["table_body"])], [Paragraph("INTERPRETATION", styles["table_label"]), Paragraph(clean(interpretation), styles["table_body"])], [Paragraph("TRADER IMPLICATION", styles["table_label"]), Paragraph(clean(implication), styles["table_body"])]]
    table = Table(rows, colWidths=[1.15 * inch, 5.75 * inch])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F2F4F7")), ("BOX", (0, 0), (-1, -1), 0.5, RULE), ("INNERGRID", (0, 0), (-1, -1), 0.25, RULE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return table


def thesis_conditions(thesis: Any, styles: dict[str, ParagraphStyle]) -> Table:
    left = "<b>CONFIRMATION</b><br/>" + "<br/>".join(f"- {clean(item)}" for item in thesis.confirmation_conditions)
    right = "<b>INVALIDATION</b><br/>" + "<br/>".join(f"- {clean(item)}" for item in thesis.invalidation_conditions)
    table = Table([[Paragraph(left, styles["condition"]), Paragraph(right, styles["condition"])]], colWidths=[3.45 * inch, 3.45 * inch])
    table.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, RULE), ("INNERGRID", (0, 0), (-1, -1), 0.5, RULE), ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#F0F9FF")), ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#FFF6ED")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 8)]))
    return table


def scenario_table(scenarios: list[Any], styles: dict[str, ParagraphStyle]) -> Table:
    rows = [[Paragraph("PATH", styles["table_header"]), Paragraph("REQUIRED CONDITIONS", styles["table_header"]), Paragraph("OPERATING RESPONSE", styles["table_header"]), Paragraph("INVALIDATION", styles["table_header"])]]
    for scenario in scenarios:
        conditions = [*scenario.required_conditions, *scenario.benchmark_levels, *scenario.breadth_conditions]
        response = [scenario.operating_response, scenario.position_sizing_implication]
        invalidation = [*scenario.invalidation, *scenario.risk_conditions]
        path_label = f"<b>{clean(scenario.label)}</b>"
        if str(scenario.label).strip().casefold() != str(scenario.likelihood).strip().casefold():
            path_label += f"<br/>{clean(scenario.likelihood)}"
        rows.append([Paragraph(path_label, styles["table_body"]), Paragraph("<br/>".join(f"- {clean(item)}" for item in conditions), styles["table_body"]), Paragraph("<br/>".join(clean(item) for item in response), styles["table_body"]), Paragraph("<br/>".join(f"- {clean(item)}" for item in invalidation), styles["table_body"])])
    table = Table(rows, colWidths=[0.95 * inch, 2.1 * inch, 2.25 * inch, 1.6 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, RULE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return table


def render_table(table_spec: Any, styles: dict[str, ParagraphStyle]) -> list[Any]:
    if table_spec.table_id == "watchlist-candidate-matrix":
        return render_watchlist_candidate_matrix(table_spec, styles)
    columns = table_spec.columns
    rows = [[Paragraph(clean(column).upper(), styles["table_header"]) for column in columns]]
    for item in table_spec.rows[:16]:
        rows.append([Paragraph(clean(format_cell(item.get(column))), styles["table_body"]) for column in columns])
    widths = [7.0 * inch / max(1, len(columns)) for _ in columns]
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(base_table_style())
    return [Paragraph(clean(table_spec.title), styles["subheading"]), Spacer(1, 0.05 * inch), table, Spacer(1, 0.1 * inch)]


def render_table_stage6(table_spec: Any, styles: dict[str, ParagraphStyle]) -> list[Any]:
    if table_spec.table_id != "watchlist-candidate-matrix":
        return render_table(table_spec, styles)
    columns = ["Symbol", "Group", "Setup state", "Relative strength", "Trend", "Confirmation level", "Invalidation level", "Freshness"]
    keys = ["Ticker", "Group", "Setup state", "Relative strength", "Trend", "Confirmation level", "Invalidation level", "Freshness"]
    widths = [0.55, 1.0, 1.1, 0.75, 1.0, 0.9, 0.9, 0.8]
    rows = [[Paragraph(clean(column).upper(), styles["table_header"]) for column in columns]]
    for item in table_spec.rows[:14]:
        rows.append([Paragraph(clean(format_cell(item.get(column))), styles["table_body"]) for column in keys])
    table = Table(rows, colWidths=[value * inch for value in widths], repeatRows=1)
    table.setStyle(base_table_style())
    return [
        Paragraph("Watchlist Triage", styles["subheading"]),
        Paragraph("Broad triage remains compact; full research follows only for selected securities.", styles["figure_meta"]),
        Spacer(1, 0.04 * inch), table, Spacer(1, 0.1 * inch),
    ]


def render_watchlist_candidate_matrix(table_spec: Any, styles: dict[str, ParagraphStyle]) -> list[Any]:
    groups = [
        ("Structure and confirmation", ["Ticker", "Group", "Setup state", "Daily change", "Relative strength", "Trend", "Volume"]),
        ("Levels and research governance", ["Ticker", "Confirmation level", "Invalidation level", "Freshness", "Research classification", "Reason for inclusion"]),
    ]
    result: list[Any] = [Paragraph(clean(table_spec.title), styles["subheading"]), Spacer(1, 0.04 * inch)]
    for label, columns in groups:
        rows = [[Paragraph(clean(column).upper(), styles["table_header"]) for column in columns]]
        for item in table_spec.rows[:16]:
            rows.append([Paragraph(clean(format_cell(item.get(column))), styles["table_body"]) for column in columns])
        if label.startswith("Structure"):
            widths = [0.48, 1.02, 1.12, 0.68, 0.78, 1.18, 1.74]
        else:
            widths = [0.48, 0.78, 0.78, 0.68, 1.35, 2.83]
        table = Table(rows, colWidths=[value * inch for value in widths], repeatRows=1)
        table.setStyle(base_table_style())
        result.extend([Paragraph(label, styles["figure_meta"]), Spacer(1, 0.03 * inch), table, Spacer(1, 0.09 * inch)])
    return result


def security_summary(items: list[Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    result: list[Any] = [Paragraph("Security Research", styles["subheading"])]
    for item in items[:6]:
        status = "ACTIONABLE" if item.actionable else "MONITORING"
        context = (
            f"<b>Group.</b> {clean(item.group or 'Unmapped')}  <b>Trend.</b> {clean(item.trend or 'Unavailable')}  "
            f"<b>Relative strength.</b> {clean(item.relative_strength if item.relative_strength is not None else 'Unavailable')}  "
            f"<b>Volume.</b> {clean(item.volume_condition or 'Unavailable')}<br/>"
            f"<b>Research classification.</b> {clean(item.research_classification)}  "
            f"<b>Change.</b> {clean(item.change_since_previous or 'No compatible comparison.')}"
        )
        result.append(KeepTogether([
            Paragraph(f"{clean(item.symbol)}  |  {clean(item.category)}  |  {status}", styles["security_title"]),
            Paragraph(f"{context}<br/><b>Setup.</b> {clean(item.setup_state)}  <b>Evidence.</b> {clean(item.summary)}<br/><b>Confirms.</b> {clean(item.confirmation)}<br/><b>Invalidates.</b> {clean(item.invalidation)}<br/><b>Risk.</b> {clean(item.risk_considerations)}<br/><b>Source.</b> {clean(item.source_timestamp or item.freshness)}", styles["body"]),
            Spacer(1, 0.1 * inch),
        ]))
    return result


def security_research_story_stage6(item: Any, figure: FigureSpec | None, styles: dict[str, ParagraphStyle]) -> list[Any]:
    status = "ACTION-PLANNING ELIGIBLE" if item.actionable else "MONITORING"
    title = Paragraph(f"{clean(item.symbol)}  |  SELECTED SECURITY RESEARCH  |  {status}", styles["security_title_large"])
    why = item.why_here or item.reason_for_inclusion
    context = item.context or item.summary
    identity = Table([
        [Paragraph("WHY HERE?", styles["table_label"]), Paragraph(clean(why), styles["table_body"])],
        [Paragraph("CONTEXT", styles["table_label"]), Paragraph(clean(context), styles["table_body"])],
    ], colWidths=[1.0 * inch, 5.9 * inch])
    identity.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EAF7FB")),
        ("BOX", (0, 0), (-1, -1), 0.5, RULE), ("INNERGRID", (0, 0), (-1, -1), 0.25, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    theme_text = ", ".join(item.themes) if item.themes else "Unavailable"
    metrics = Table([
        [Paragraph("SETUP", styles["table_label"]), Paragraph("SECTOR / THEME", styles["table_label"]), Paragraph("RELATIVE STRENGTH", styles["table_label"]), Paragraph("VOLUME", styles["table_label"])],
        [Paragraph(clean(item.setup_state), styles["table_body"]), Paragraph(clean(f"{item.sector or 'Unavailable'} / {theme_text}"), styles["table_body"]), Paragraph(clean(item.relative_strength if item.relative_strength is not None else "Unavailable"), styles["table_body"]), Paragraph(clean(item.volume_condition or "Unavailable"), styles["table_body"])],
    ], colWidths=[1.35 * inch, 2.15 * inch, 1.25 * inch, 2.15 * inch])
    metrics.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F4F7")),
        ("BOX", (0, 0), (-1, -1), 0.5, RULE), ("INNERGRID", (0, 0), (-1, -1), 0.25, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    decisions = Table([
        [Paragraph("CONFIRMATION", styles["table_label"]), Paragraph("INVALIDATION / RISK", styles["table_label"])],
        [Paragraph(clean(item.confirmation), styles["table_body"]), Paragraph(clean(f"{item.invalidation} {item.risk_considerations}"), styles["table_body"])],
        [Paragraph("WHAT CHANGED", styles["table_label"]), Paragraph("EXECUTION CONSIDERATION", styles["table_label"])],
        [Paragraph(clean(item.change_since_previous or "No compatible comparison."), styles["table_body"]), Paragraph(clean(item.execution_consideration or "Monitoring only."), styles["table_body"])],
    ], colWidths=[3.45 * inch, 3.45 * inch])
    decisions.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F0F9FF")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#FFF6ED")),
        ("BOX", (0, 0), (-1, -1), 0.5, RULE), ("INNERGRID", (0, 0), (-1, -1), 0.25, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    result: list[Any] = [title, identity, Spacer(1, 0.06 * inch), metrics, Spacer(1, 0.06 * inch), decisions, Spacer(1, 0.08 * inch)]
    if figure:
        result.append(figure_block(figure, styles, compact=True, stage6=True))
    result.append(Paragraph(f"Source: {clean(item.source_timestamp or item.freshness)}", styles["source"]))
    return result


def security_research_queue_stage6(items: list[Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    rows = [[Paragraph("SECURITY", styles["table_header"]), Paragraph("WHY SELECTED", styles["table_header"]), Paragraph("CURRENT SETUP", styles["table_header"]), Paragraph("DECISION GATE", styles["table_header"])]]
    for item in items[:4]:
        gate = item.execution_consideration or item.confirmation
        rows.append([
            Paragraph(f"<b>{clean(item.symbol)}</b><br/>{clean(item.research_classification)}", styles["table_body"]),
            Paragraph(clean(item.why_here or item.reason_for_inclusion), styles["table_body"]),
            Paragraph(clean(f"{item.setup_state} | {item.trend or 'Trend unavailable'} | {item.volume_condition or 'Volume unavailable'}"), styles["table_body"]),
            Paragraph(clean(gate), styles["table_body"]),
        ])
    table = Table(rows, colWidths=[1.05 * inch, 2.05 * inch, 1.8 * inch, 2.0 * inch], repeatRows=1)
    table.setStyle(base_table_style())
    return [Paragraph("Selected Research Queue", styles["subheading"]), Spacer(1, 0.04 * inch), table, Spacer(1, 0.08 * inch)]


def monitoring_table(items: list[Any], styles: dict[str, ParagraphStyle], *, expanded: bool = False) -> list[Any]:
    rows = [[Paragraph("METRIC", styles["table_header"]), Paragraph("CONDITION", styles["table_header"]), Paragraph("WHY IT MATTERS", styles["table_header"]), Paragraph("ACTION", styles["table_header"])]]
    for item in items:
        rows.append([Paragraph(clean(item.metric), styles["table_body"]), Paragraph(clean(item.threshold_or_condition), styles["table_body"]), Paragraph(clean(item.rationale), styles["table_body"]), Paragraph(clean(item.action_implication), styles["table_body"])])
    table = Table(rows, colWidths=[1.05 * inch, 2.0 * inch, 1.9 * inch, 1.95 * inch], repeatRows=1)
    if not expanded:
        table.setStyle(base_table_style())
        return [Paragraph("Evidence-Linked Checklist", styles["subheading"]), Spacer(1, 0.05 * inch), table]
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, RULE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 13), ("BOTTOMPADDING", (0, 0), (-1, -1), 13),
    ]))
    return [Paragraph("Evidence-Linked Checklist", styles["subheading"]), Spacer(1, 0.05 * inch), table]


def methodology_story(document: ReportDocument, styles: dict[str, ParagraphStyle], *, stage6: bool = False) -> list[Any]:
    rows = [[Paragraph("ID", styles["table_header"]), Paragraph("PROVIDER", styles["table_header"]), Paragraph("DATASET", styles["table_header"]), Paragraph("AS OF", styles["table_header"])]]
    for source in document.sources:
        rows.append([Paragraph(clean(source.source_id), styles["table_body"]), Paragraph(clean(source.provider), styles["table_body"]), Paragraph(clean(source.dataset), styles["table_body"]), Paragraph(clean(source.timestamp or "Unavailable"), styles["table_body"])])
    table = Table(rows, colWidths=[1.15 * inch, 1.2 * inch, 2.85 * inch, 1.7 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, RULE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    limitations = "<br/>".join(f"- {clean(item)}" for item in document.limitations)
    selection_story: list[Any] = []
    if document.research_selection:
        decision = document.research_selection
        selected = next((item for item in document.research_candidates if item.candidate_id == decision.selected_candidate_id), None)
        core_evidence_ids = [
            evidence_id for evidence_id in (selected.evidence_ids if selected else [])
            if "-weight-" not in evidence_id and "-contribution-" not in evidence_id
        ][:12]
        omitted_evidence_count = max(0, len(selected.evidence_ids) - len(core_evidence_ids)) if selected else 0
        evidence_summary = ", ".join(core_evidence_ids)
        if omitted_evidence_count:
            evidence_summary += f" (+{omitted_evidence_count} policy/contribution IDs in the serialized registry)"
        selection_rows = [
            [Paragraph("FIELD", styles["table_header"]), Paragraph("RESEARCH FOCUS SELECTION", styles["table_header"])],
            [Paragraph("Subject / classification", styles["table_body"]), Paragraph(clean(f"{selected.name} | {selected.category} / {selected.direction}" if selected else decision.no_selection_reason or "No qualifying subject"), styles["table_body"])],
            [Paragraph("Score / relevance", styles["table_body"]), Paragraph(clean(f"{selected.score.total:.1f} / threshold {decision.materiality_threshold:.1f} | user relevance {selected.user_relevance.tier}" if selected else f"Threshold {decision.materiality_threshold:.1f} | relevance not applied"), styles["table_body"])],
            [Paragraph("Evidence IDs", styles["table_body"]), Paragraph(clean(evidence_summary or "None"), styles["table_body"])],
            [Paragraph("Omissions / limitations", styles["table_body"]), Paragraph(clean(f"{decision.omitted_candidate_count} candidates omitted | {', '.join(decision.missing_evidence) or 'no missing scored dimensions'}"), styles["table_body"])],
        ]
        selection_table = Table(selection_rows, colWidths=[1.35 * inch, 5.55 * inch], repeatRows=1)
        selection_table.setStyle(base_table_style())
        selection_story = [
            Paragraph("Research Focus Selection", styles["subheading"]), Spacer(1, 0.05 * inch),
            selection_table, Spacer(1, 0.12 * inch),
        ]
    result = [
        *selection_story,
        Paragraph("Numbered Source Registry", styles["subheading"]),
        Spacer(1, 0.05 * inch), table, Spacer(1, 0.12 * inch),
        Paragraph("Data Limitations", styles["subheading"]),
        Paragraph(limitations or "No additional limitations recorded.", styles["body"]),
    ]
    if not stage6:
        result.extend([
            Spacer(1, 0.02 * inch),
            Paragraph(
                f"Report ID: {clean(document.report_id)}  |  PDF: {clean(document.pdf_format_version)}  |  Cutoff: {clean(document.data_cutoff)}  |  Completeness: {document.thesis.data_completeness:.0%}<br/>"
                "System-generated interpretations are informational and educational only. They are not personalized investment advice.",
                styles["source"],
            ),
        ])
    return result


def draw_page(canvas: Any, doc: Any, document: ReportDocument) -> None:
    canvas.saveState()
    canvas.setStrokeColor(RULE); canvas.setLineWidth(0.5); canvas.line(0.55 * inch, letter[1] - 0.42 * inch, letter[0] - 0.55 * inch, letter[1] - 0.42 * inch)
    canvas.setFillColor(MUTED); canvas.setFont("Helvetica", 6.5)
    canvas.drawString(0.55 * inch, letter[1] - 0.32 * inch, f"MARKET INTELLIGENCE  /  {document.market_date}")
    canvas.drawRightString(letter[0] - 0.55 * inch, letter[1] - 0.32 * inch, document.report_type.upper())
    canvas.line(0.55 * inch, 0.36 * inch, letter[0] - 0.55 * inch, 0.36 * inch)
    canvas.drawString(0.55 * inch, 0.23 * inch, f"{document.source_status.upper()}  /  {document.pdf_format_version}")
    canvas.drawRightString(letter[0] - 0.55 * inch, 0.23 * inch, f"{doc.page}")
    canvas.restoreState()


def report_styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "kicker": ParagraphStyle("V6Kicker", parent=sample["BodyText"], fontName="Helvetica-Bold", fontSize=7.5, leading=9, textColor=BLUE, spaceAfter=4),
        "cover_title": ParagraphStyle("V6Cover", parent=sample["Title"], fontName="Helvetica-Bold", fontSize=26, leading=29, textColor=INK, spaceAfter=5, letterSpacing=0),
        "meta": ParagraphStyle("V6Meta", parent=sample["BodyText"], fontName="Helvetica", fontSize=7.2, leading=9, textColor=MUTED),
        "posture": ParagraphStyle("V6Posture", parent=sample["BodyText"], fontName="Helvetica-Bold", fontSize=10, leading=12, textColor=GREEN, spaceAfter=5),
        "thesis": ParagraphStyle("V6Thesis", parent=sample["BodyText"], fontName="Helvetica-Bold", fontSize=13, leading=18, textColor=INK),
        "condition": ParagraphStyle("V6Condition", parent=sample["BodyText"], fontName="Helvetica", fontSize=7.3, leading=10, textColor=INK),
        "contents": ParagraphStyle("V6Contents", parent=sample["BodyText"], fontName="Helvetica-Bold", fontSize=6.3, leading=8, textColor=MUTED, alignment=TA_CENTER),
        "section": ParagraphStyle("V6Section", parent=sample["Heading1"], fontName="Helvetica-Bold", fontSize=17, leading=20, textColor=INK, spaceAfter=3),
        "section_question": ParagraphStyle("Stage6SectionQuestion", parent=sample["Heading2"], fontName="Helvetica-Bold", fontSize=13.5, leading=16.5, textColor=BLUE, spaceAfter=3),
        "section_purpose": ParagraphStyle("V6Purpose", parent=sample["BodyText"], fontName="Helvetica", fontSize=8, leading=10, textColor=MUTED),
        "body": ParagraphStyle("V6Body", parent=sample["BodyText"], fontName="Helvetica", fontSize=8.4, leading=12.2, textColor=INK, alignment=TA_LEFT),
        "body_lead": ParagraphStyle("V6Lead", parent=sample["BodyText"], fontName="Helvetica", fontSize=9.5, leading=14, textColor=INK),
        "subheading": ParagraphStyle("V6Subheading", parent=sample["Heading2"], fontName="Helvetica-Bold", fontSize=10, leading=12, textColor=INK, spaceBefore=5),
        "figure_title": ParagraphStyle("V6FigureTitle", parent=sample["Heading3"], fontName="Helvetica-Bold", fontSize=9.2, leading=11, textColor=INK, spaceAfter=2),
        "figure_meta": ParagraphStyle("V6FigureMeta", parent=sample["BodyText"], fontName="Helvetica", fontSize=6.5, leading=8, textColor=MUTED),
        "figure_question": ParagraphStyle("Stage6FigureQuestion", parent=sample["BodyText"], fontName="Helvetica-Bold", fontSize=6.2, leading=7.5, textColor=BLUE, spaceBefore=2),
        "caption": ParagraphStyle("V6Caption", parent=sample["BodyText"], fontName="Helvetica", fontSize=6.7, leading=9, textColor=INK),
        "source": ParagraphStyle("V6Source", parent=sample["BodyText"], fontName="Helvetica", fontSize=5.8, leading=7, textColor=MUTED, spaceTop=2),
        "table_header": ParagraphStyle("V6TableHeader", parent=sample["BodyText"], fontName="Helvetica-Bold", fontSize=6.1, leading=7.5, textColor=colors.white),
        "table_body": ParagraphStyle("V6TableBody", parent=sample["BodyText"], fontName="Helvetica", fontSize=6.2, leading=8, textColor=INK),
        "table_label": ParagraphStyle("V6TableLabel", parent=sample["BodyText"], fontName="Helvetica-Bold", fontSize=5.8, leading=7.2, textColor=MUTED),
        "security_title": ParagraphStyle("V6Security", parent=sample["Heading3"], fontName="Helvetica-Bold", fontSize=8.5, leading=10, textColor=BLUE, spaceBefore=5, spaceAfter=2),
        "security_title_large": ParagraphStyle("Stage6Security", parent=sample["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=BLUE, spaceBefore=2, spaceAfter=5),
        "research_question": ParagraphStyle("Stage6ResearchQuestion", parent=sample["Heading2"], fontName="Helvetica-Bold", fontSize=16.5, leading=20, textColor=INK, spaceAfter=2),
        "executive_answer": ParagraphStyle("Stage6ExecutiveAnswer", parent=sample["BodyText"], fontName="Helvetica-Bold", fontSize=10.5, leading=15, textColor=INK),
        "executive_answer_small": ParagraphStyle("Stage6ExecutiveAnswerSmall", parent=sample["BodyText"], fontName="Helvetica-Bold", fontSize=8.2, leading=11.5, textColor=INK),
        "disclaimer": ParagraphStyle("V6Disclaimer", parent=sample["BodyText"], fontName="Helvetica-Oblique", fontSize=6.2, leading=8, textColor=MUTED, spaceBefore=8),
    }


def base_table_style() -> TableStyle:
    return TableStyle([("BACKGROUND", (0, 0), (-1, 0), INK), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.35, RULE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)])


def thin_rule() -> Table:
    table = Table([[""]], colWidths=[7.0 * inch], rowHeights=[0.5])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), RULE)]))
    return table


def clean(value: Any) -> str:
    return str(value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def numeric(value: Any) -> float | None:
    if isinstance(value, bool): return None
    try:
        result = float(value)
        return result if isfinite(result) else None
    except (TypeError, ValueError):
        return None


def compact_number(value: float) -> str:
    magnitude = abs(value)
    if magnitude >= 1_000_000_000: return f"{value / 1_000_000_000:.1f}B"
    if magnitude >= 1_000_000: return f"{value / 1_000_000:.1f}M"
    if magnitude >= 1_000: return f"{value / 1_000:.1f}K"
    if magnitude < 1: return f"{value:.2f}"
    return f"{value:.1f}"


def spread_label_positions(values: list[float], *, lower: float, upper: float, min_gap: float) -> list[float]:
    if not values:
        return []
    if len(values) == 1:
        return [min(upper, max(lower, values[0]))]
    gap = min(min_gap, max(0, (upper - lower) / (len(values) - 1)))
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    positions = [min(upper, max(lower, value)) for _, value in ordered]
    for index in range(1, len(positions)):
        positions[index] = max(positions[index], positions[index - 1] + gap)
    if positions[-1] > upper:
        positions[-1] = upper
        for index in range(len(positions) - 2, -1, -1):
            positions[index] = min(positions[index], positions[index + 1] - gap)
    result = [0.0] * len(values)
    for (original_index, _), position in zip(ordered, positions):
        result[original_index] = position
    return result


def fit(value: str, length: int) -> str:
    return value if len(value) <= length else value[: max(1, length - 3)] + "..."


def fit_to_width(value: str, width: float, font_name: str, font_size: float) -> str:
    text = str(value or "")
    if stringWidth(text, font_name, font_size) <= width:
        return text
    suffix = "..."
    while text and stringWidth(text + suffix, font_name, font_size) > width:
        text = text[:-1]
    return text.rstrip() + suffix if text else suffix


def short_figure_label(value: str) -> str:
    label = str(value or "").strip()
    if label.casefold().startswith("current thesis:"):
        return "Current thesis"
    replacements = {
        "Risk level": "Risk",
        "Invalidation": "Inval.",
        "Previous report": "Previous",
    }
    for source, target in replacements.items():
        if label.casefold().startswith(source.casefold()):
            label = target + label[len(source):]
            break
    return fit(label, 21)


def blend(left: colors.Color, right: colors.Color, weight: float) -> colors.Color:
    return colors.Color(left.red * (1 - weight) + right.red * weight, left.green * (1 - weight) + right.green * weight, left.blue * (1 - weight) + right.blue * weight)


def format_cell(value: Any) -> str:
    if value is None: return "--"
    if isinstance(value, float): return f"{value:.2f}"
    return str(value)
