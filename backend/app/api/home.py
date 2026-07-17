from fastapi import APIRouter

from app.services.client_activity import record_client_activity
from app.services.home_dashboard import build_home_dashboard

router = APIRouter()


@router.get("/home/dashboard")
async def get_home_dashboard() -> dict[str, object]:
    """Return a compact dashboard for fast Home screen launch."""
    record_client_activity("home")
    return build_home_dashboard()
