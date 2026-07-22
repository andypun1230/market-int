#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.reports.document import ReportDocument
from app.reports.document_builder import build_report_document
from app.reports.pdf_v6 import generate_report_pdf_v6
from app.services.report import build_daily_report, get_daily_report_by_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic Report V6 visual-validation samples.")
    parser.add_argument("--output-dir", default="tmp/report-v6-samples")
    parser.add_argument("--report-id", help="Optional immutable source report to transform with the current V6 builder.")
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    report = get_daily_report_by_id(args.report_id) if args.report_id else build_daily_report()
    if report is None:
        raise RuntimeError(f"Unknown source report: {args.report_id}")
    previous_thesis = (report.report_document or {}).get("thesis", {}).get("previous_thesis")
    previous = {"overallThesis": previous_thesis} if previous_thesis else None
    source = build_report_document(report, previous)
    samples = {
        "complete-live-after-close": after_close_fixture(source),
        "mixed-source": mixed_fixture(source),
        "first-baseline": baseline_fixture(source),
        "weekend": weekend_fixture(source),
    }
    manifest = {}
    for name, document in samples.items():
        pdf_path = output / f"report-v6-{name}.pdf"
        json_path = output / f"report-v6-{name}.json"
        pdf_path.write_bytes(generate_report_pdf_v6(document).getvalue())
        json_path.write_text(json.dumps(document.model_dump(mode="json"), indent=2, sort_keys=True), encoding="utf-8")
        manifest[name] = {
            "pdf": str(pdf_path),
            "json": str(json_path),
            "report_id": document.report_id,
            "report_type": document.report_type,
            "source_status": document.source_status,
            "data_completeness": document.thesis.data_completeness,
            "figure_count": document.figure_count,
            "page_count_estimate": document.page_count_estimate,
            "approximate_word_count": document.approximate_word_count,
        }
    manifest_path = output / "report-v6-sample-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


def after_close_fixture(source: ReportDocument) -> ReportDocument:
    market_close = f"{source.market_date}T21:30:00+00:00"
    return source.model_copy(update={
        "report_id": f"{source.report_id}-fixture-after-close",
        "report_type": "After Close",
        "generated_at": market_close,
        "previous_report_available": True,
    })


def mixed_fixture(source: ReportDocument) -> ReportDocument:
    figures = [
        figure.model_copy(update={"quality": figure.quality.model_copy(update={"state": "cached"})})
        if figure.figure_id in {"macro-normalized", "risk-history"}
        else figure
        for figure in source.figures
    ]
    return source.model_copy(update={
        "report_id": f"{source.report_id}-fixture-mixed",
        "source_status": "mixed",
        "figures": figures,
    })


def baseline_fixture(source: ReportDocument) -> ReportDocument:
    thesis = source.thesis.model_copy(update={
        "previous_thesis": None,
        "thesis_change": "Baseline established.",
    })
    sections = []
    for section in source.sections:
        paragraphs = [
            paragraph.replace("Compatible previous-report changes are integrated where evidence aligns.", "Baseline established.")
            for paragraph in section.paragraphs
        ]
        sections.append(section.model_copy(update={"paragraphs": paragraphs}))
    return source.model_copy(update={
        "report_id": f"{source.report_id}-fixture-baseline",
        "thesis": thesis,
        "sections": sections,
        "previous_report_available": False,
    })


def weekend_fixture(source: ReportDocument) -> ReportDocument:
    return source.model_copy(update={
        "report_id": f"{source.report_id}-fixture-weekend",
        "report_type": "Weekend / Holiday",
        "generated_at": "2026-07-19T03:00:00+00:00",
    })


if __name__ == "__main__":
    raise SystemExit(main())
