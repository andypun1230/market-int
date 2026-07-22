#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.reports.document_builder import build_report_document
from app.reports.pdf_v7 import generate_report_pdf_v7
from tests.fixtures.report_v7 import report_v7_fixture


SAMPLES = {
    "personalized-leading-theme": "user-saved-leading-theme",
    "personalized-weakening-theme": "user-saved-weakening-theme",
    "market-led-no-overlap": "market-leading-theme-no-overlap",
    "market-lagging-sector": "market-lagging-sector-deterioration",
    "no-qualifying-focus": "no-qualifying-focus",
    "weekend": "weekend-report",
    "mixed-source": "mixed-source-report",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate and render the required Report V7 validation samples plus an explicit laggard case.")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "output" / "pdf" / "report-v7"))
    parser.add_argument("--render-dir", default=str(PROJECT_ROOT / "tmp" / "pdfs" / "report-v7"))
    parser.add_argument("--dpi", type=int, default=190)
    parser.add_argument("--skip-render", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    render_root = Path(args.render_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    render_root.mkdir(parents=True, exist_ok=True)
    pdftoppm = shutil.which("pdftoppm")
    pdfinfo = shutil.which("pdfinfo")
    if not args.skip_render and not pdftoppm:
        raise RuntimeError("pdftoppm is required for 190-DPI page rendering")

    manifest: dict[str, dict[str, object]] = {}
    for sample_name, fixture_name in SAMPLES.items():
        report, previous = report_v7_fixture(fixture_name)
        document = build_report_document(report, previous)
        pdf_path = output_dir / f"report-v7-{sample_name}.pdf"
        json_path = output_dir / f"report-v7-{sample_name}.json"
        pdf_path.write_bytes(generate_report_pdf_v7(document).getvalue())
        json_path.write_text(json.dumps(document.model_dump(mode="json"), indent=2, sort_keys=True), encoding="utf-8")

        page_count = pdf_page_count(pdf_path, pdfinfo)
        contact_sheet_path: Path | None = None
        rendered_pages: list[Path] = []
        if not args.skip_render:
            sample_render_dir = render_root / sample_name
            sample_render_dir.mkdir(parents=True, exist_ok=True)
            for old_page in sample_render_dir.glob("page-*.png"):
                old_page.unlink()
            subprocess.run(
                [pdftoppm, "-png", "-r", str(args.dpi), str(pdf_path), str(sample_render_dir / "page")],
                check=True,
                capture_output=True,
                text=True,
            )
            rendered_pages = sorted(sample_render_dir.glob("page-*.png"))
            if page_count and len(rendered_pages) != page_count:
                raise RuntimeError(f"{sample_name}: expected {page_count} rendered pages, found {len(rendered_pages)}")
            contact_sheet_path = output_dir / f"report-v7-{sample_name}-contact-sheet.png"
            make_contact_sheet(rendered_pages, contact_sheet_path, title=f"Report V7 · {sample_name}")

        focus = document.research_focus
        manifest[sample_name] = {
            "fixture": fixture_name,
            "pdf": str(pdf_path),
            "document_json": str(json_path),
            "contact_sheet": str(contact_sheet_path) if contact_sheet_path else None,
            "render_directory": str(render_root / sample_name) if not args.skip_render else None,
            "render_dpi": None if args.skip_render else args.dpi,
            "rendered_page_count": len(rendered_pages),
            "actual_page_count": page_count,
            "page_count_estimate": document.page_count_estimate,
            "figure_count": document.figure_count,
            "grounded_word_count": document.approximate_word_count,
            "report_type": document.report_type,
            "source_status": document.source_status,
            "focus_subject": focus.subject if focus else None,
            "focus_direction": focus.direction if focus else None,
            "focus_priority_score": focus.priority_score if focus else None,
            "focus_figure_count": len(focus.figure_ids) if focus else 0,
            "saved_overlap_count": len(focus.user_relevance.saved_security_symbols) if focus else 0,
            "selection_status": "selected" if focus else "no_focus",
        }

    manifest_path = output_dir / "report-v7-sample-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


def pdf_page_count(path: Path, pdfinfo: str | None) -> int | None:
    if not pdfinfo:
        return None
    result = subprocess.run([pdfinfo, str(path)], check=True, capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    return None


def make_contact_sheet(page_paths: list[Path], destination: Path, *, title: str) -> None:
    if not page_paths:
        raise RuntimeError(f"No rendered pages available for {destination.name}")
    columns = 4
    cell_width = 590
    label_height = 32
    margin = 24
    thumbnails: list[Image.Image] = []
    for path in page_paths:
        with Image.open(path) as page:
            thumbnail = page.convert("RGB")
            thumbnail.thumbnail((cell_width - margin, 760), Image.Resampling.LANCZOS)
            thumbnails.append(thumbnail.copy())
    cell_height = max(image.height for image in thumbnails) + label_height + margin
    rows = (len(thumbnails) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_width + margin, rows * cell_height + 72), "#111827")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    draw.text((margin, 20), title, fill="#f8fafc", font=font)
    for index, thumbnail in enumerate(thumbnails):
        column = index % columns
        row = index // columns
        x = margin + column * cell_width
        y = 58 + row * cell_height
        draw.rectangle((x - 2, y - 2, x + thumbnail.width + 2, y + thumbnail.height + 2), fill="#334155")
        sheet.paste(thumbnail, (x, y))
        draw.text((x, y + thumbnail.height + 8), f"Page {index + 1}", fill="#e2e8f0", font=font)
    sheet.save(destination, format="PNG", optimize=True)


if __name__ == "__main__":
    raise SystemExit(main())
