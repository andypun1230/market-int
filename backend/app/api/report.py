from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.market import DailyReportResponse
from app.services.report import build_daily_report, generate_daily_report_pdf

router = APIRouter()


@router.get("/report/daily", response_model=DailyReportResponse)
async def get_daily_report() -> DailyReportResponse:
    """Return a stubbed daily market report."""
    return build_daily_report()


@router.get("/report/daily/pdf")
async def get_daily_report_pdf() -> StreamingResponse:
    """Generate and return the daily market report as a PDF."""
    pdf_buffer = generate_daily_report_pdf(build_daily_report())

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="daily_market_report.pdf"'},
    )
