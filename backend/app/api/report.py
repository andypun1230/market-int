from io import BytesIO

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.models.market import DailyReportResponse
from app.services.report import (
    build_daily_report,
    get_daily_report_by_id,
    get_daily_report_history,
    get_daily_report_pdf_bytes,
    get_latest_daily_report,
)

router = APIRouter()


@router.get("/report/daily", response_model=DailyReportResponse)
async def get_daily_report(
    stocks: str | None = Query(default=None),
    sectors: str | None = Query(default=None),
    themes: str | None = Query(default=None),
) -> DailyReportResponse:
    """Return the immutable current report for the current snapshot identity."""
    return build_daily_report(
        saved_stocks=parse_saved_values(stocks),
        saved_sectors=parse_saved_values(sectors),
        saved_themes=parse_saved_values(themes),
    )


@router.get("/report/daily/pdf")
async def get_daily_report_pdf(report_id: str | None = Query(default=None)) -> StreamingResponse:
    """Return the immutable PDF for the requested report, or the current report."""
    try:
        report, pdf = get_daily_report_pdf_bytes(report_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="report_not_found") from exc

    return StreamingResponse(
        BytesIO(pdf),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="daily_market_report_{report.report_id}.pdf"',
            "X-Report-Id": report.report_id or "",
            "X-Report-Schema-Version": report.report_schema_version or "",
        },
    )


@router.get("/report/daily/latest")
async def get_latest_report_metadata() -> dict:
    report = get_latest_daily_report()
    if report is None:
        return {"latest_report": None}
    return {
        "latest_report": {
            "report_id": report.report_id,
            "market_date": report.market_date,
            "generated_at": report.generated_at,
            "report_schema_version": report.report_schema_version,
            "report_cache_key": report.report_cache_key,
            "snapshot_ids": (report.semantic_context or {}).get("snapshot_ids") or {},
        }
    }


@router.get("/report/daily/history")
async def get_report_history(limit: int = Query(default=30, ge=1, le=200)) -> dict:
    return {"items": get_daily_report_history(limit)}


@router.get("/report/daily/{report_id}", response_model=DailyReportResponse)
async def get_historical_daily_report(report_id: str) -> DailyReportResponse:
    report = get_daily_report_by_id(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report_not_found")
    return report


def parse_saved_values(value: str | None) -> list[str]:
    if not value:
        return []
    result: list[str] = []
    seen: set[str] = set()
    for raw_item in value.split(","):
        item = raw_item.strip()
        key = item.casefold()
        if not item or key in seen:
            continue
        seen.add(key)
        result.append(item)
        if len(result) == 50:
            break
    return result
