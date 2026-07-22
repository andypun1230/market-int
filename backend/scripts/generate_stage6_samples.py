#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING, Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

if TYPE_CHECKING:
    from app.reports.document import ReportDocument


RENDER_DPI = 190
SAMPLES = {
    "leading-theme": "market-leading-theme-no-overlap",
    "lagging-theme": "market-lagging-theme",
    "no-focus": "no-qualifying-focus",
    "weekend": "weekend-report",
    "mixed": "mixed-source-report",
    "personalized": "user-saved-leading-theme",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the six required Stage 6 research-intelligence validation reports and 190-DPI renders."
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "output" / "pdf" / "stage-6"),
        help="Directory for the Stage 6 PDFs, document JSON, contact sheets, and manifest.",
    )
    parser.add_argument(
        "--render-dir",
        default=str(PROJECT_ROOT / "tmp" / "pdfs" / "stage-6"),
        help="Directory for the 190-DPI per-page PNG renders.",
    )
    args = parser.parse_args(argv)

    from app.reports.document_builder import build_report_document
    from app.reports.pdf_v7 import generate_report_pdf_v7
    from scripts.generate_report_v7_samples import make_contact_sheet, pdf_page_count
    from tests.fixtures.report_v7 import report_v7_fixture

    output_dir = Path(args.output_dir).resolve()
    render_root = Path(args.render_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    render_root.mkdir(parents=True, exist_ok=True)

    pdftoppm = shutil.which("pdftoppm")
    pdfinfo = shutil.which("pdfinfo")
    if not pdftoppm or not pdfinfo:
        missing = ", ".join(name for name, path in (("pdftoppm", pdftoppm), ("pdfinfo", pdfinfo)) if not path)
        raise RuntimeError(f"Stage 6 sample generation requires Poppler tools: {missing}")

    sample_manifest: dict[str, dict[str, Any]] = {}
    for sample_name, fixture_name in SAMPLES.items():
        report, previous = report_v7_fixture(fixture_name)
        document = build_report_document(report, previous)

        pdf_path = output_dir / f"stage-6-{sample_name}.pdf"
        json_path = output_dir / f"stage-6-{sample_name}.json"
        contact_sheet_path = output_dir / f"stage-6-{sample_name}-contact-sheet.png"
        sample_render_dir = render_root / sample_name
        sample_render_dir.mkdir(parents=True, exist_ok=True)

        pdf_path.write_bytes(generate_report_pdf_v7(document).getvalue())
        json_path.write_text(
            json.dumps(document.model_dump(mode="json"), indent=2, sort_keys=True),
            encoding="utf-8",
        )

        for old_page in sample_render_dir.glob("page-*.png"):
            old_page.unlink()
        subprocess.run(
            [
                pdftoppm,
                "-png",
                "-r",
                str(RENDER_DPI),
                str(pdf_path),
                str(sample_render_dir / "page"),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        rendered_pages = sorted(sample_render_dir.glob("page-*.png"), key=rendered_page_number)
        actual_page_count = pdf_page_count(pdf_path, pdfinfo)
        if actual_page_count is None:
            raise RuntimeError(f"{sample_name}: pdfinfo did not return a page count")
        if len(rendered_pages) != actual_page_count:
            raise RuntimeError(
                f"{sample_name}: expected {actual_page_count} rendered pages, found {len(rendered_pages)}"
            )
        make_contact_sheet(rendered_pages, contact_sheet_path, title=f"Stage 6 | {sample_name}")

        sample_manifest[sample_name] = build_sample_manifest(
            document=document,
            fixture_name=fixture_name,
            pdf_path=pdf_path,
            json_path=json_path,
            contact_sheet_path=contact_sheet_path,
            render_dir=sample_render_dir,
            actual_page_count=actual_page_count,
            rendered_page_count=len(rendered_pages),
        )

    manifest = {
        "stage": "6",
        "sample_count": len(sample_manifest),
        "required_samples": list(SAMPLES),
        "render_dpi": RENDER_DPI,
        "output_directory": str(output_dir),
        "render_directory": str(render_root),
        "samples": sample_manifest,
    }
    manifest_path = output_dir / "stage-6-sample-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


def build_sample_manifest(
    *,
    document: ReportDocument,
    fixture_name: str,
    pdf_path: Path,
    json_path: Path,
    contact_sheet_path: Path,
    render_dir: Path,
    actual_page_count: int,
    rendered_page_count: int,
) -> dict[str, Any]:
    focus = document.research_focus
    inquiry = document.research_inquiry
    evidence_quality = focus.evidence_quality if focus else None
    relationship_graph = focus.relationship_graph if focus else None
    selected_securities = [item for item in document.securities if item.selected_for_research]
    annotated_figures = [item for item in document.figures if item.annotations]
    relationship_types = sorted(
        {edge.relationship_type for edge in relationship_graph.edges}
    ) if relationship_graph else []

    return {
        "fixture": fixture_name,
        "artifacts": {
            "pdf": str(pdf_path),
            "document_json": str(json_path),
            "contact_sheet": str(contact_sheet_path),
            "render_directory": str(render_dir),
        },
        "report": {
            "report_id": document.report_id,
            "report_type": document.report_type,
            "market_date": document.market_date,
            "source_status": document.source_status,
            "document_version": document.document_version,
            "pdf_format_version": document.pdf_format_version,
        },
        "page_stats": {
            "actual_count": actual_page_count,
            "rendered_count": rendered_page_count,
            "estimate": document.page_count_estimate,
            "render_dpi": RENDER_DPI,
        },
        "figure_stats": {
            "total_count": document.figure_count,
            "focus_count": len(focus.figure_ids) if focus else 0,
            "annotated_count": len(annotated_figures),
            "annotation_count": sum(len(item.annotations) for item in annotated_figures),
        },
        "focus_stats": {
            "status": inquiry.status if inquiry else ("qualified" if focus else "no_focus"),
            "question": inquiry.question if inquiry else (focus.question if focus else None),
            "executive_answer": inquiry.executive_answer if inquiry else (focus.executive_answer if focus else None),
            "subject": focus.subject if focus else None,
            "category": focus.category if focus else None,
            "direction": focus.direction if focus else None,
            "priority_score": focus.priority_score if focus else None,
            "classification_label": focus.classification_label if focus else None,
        },
        "evidence_stats": {
            "registry_count": len(document.evidence),
            "focus_evidence_count": len(focus.evidence_ids) if focus else len(inquiry.evidence_ids) if inquiry else 0,
            "matrix_row_count": len(focus.evidence_matrix) if focus else 0,
            "quality": evidence_quality.model_dump(mode="json") if evidence_quality else None,
        },
        "relationship_stats": {
            "node_count": len(relationship_graph.nodes) if relationship_graph else 0,
            "edge_count": len(relationship_graph.edges) if relationship_graph else 0,
            "relationship_types": relationship_types,
        },
        "timeline_stats": {
            "entry_count": len(document.market_timeline),
            "first_market_date": document.market_timeline[0].market_date if document.market_timeline else None,
            "last_market_date": document.market_timeline[-1].market_date if document.market_timeline else None,
            "focus_entry_count": sum(bool(item.research_focus) for item in document.market_timeline),
        },
        "security_stats": {
            "total_count": len(document.securities),
            "selected_count": len(selected_securities),
            "selected_symbols": [item.symbol for item in selected_securities],
            "selected_with_figure_count": sum(bool(item.figure_id) for item in selected_securities),
            "leading_signal_count": len(focus.leading_securities) if focus else 0,
            "lagging_signal_count": len(focus.lagging_securities) if focus else 0,
        },
    }


def rendered_page_number(path: Path) -> int:
    try:
        return int(path.stem.rsplit("-", 1)[1])
    except (IndexError, ValueError) as exc:
        raise RuntimeError(f"Unexpected rendered page filename: {path.name}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
