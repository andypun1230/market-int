from __future__ import annotations

from io import BytesIO
from typing import Any

from app.reports.document import ReportDocument
from app.reports.pdf_v6 import generate_report_pdf_document


def generate_report_pdf_v7(value: ReportDocument | dict[str, Any]) -> BytesIO:
    document = value if isinstance(value, ReportDocument) else ReportDocument.model_validate(value)
    if document.pdf_format_version != "daily-report-pdf-v7":
        raise ValueError("V7 renderer requires daily-report-pdf-v7")
    return generate_report_pdf_document(document, stage6=True)
