from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.providers.cache import clear_provider_cache
from app.services.service_cache import invalidate_service_cache
from app.test_data.repository import (
    get_test_data_scenarios,
    get_test_data_status,
    regenerate_test_data,
)

router = APIRouter()


class RegenerateTestDataRequest(BaseModel):
    scenario: str | None = None
    seed: str | None = None


@router.get("/test-data/status")
async def get_test_data_status_endpoint() -> dict[str, Any]:
    """Return the active local generated market-data snapshot metadata."""
    return get_test_data_status()


@router.get("/test-data/scenarios")
async def get_test_data_scenarios_endpoint() -> dict[str, object]:
    """Return supported deterministic test-market scenarios."""
    return {"items": get_test_data_scenarios()}


@router.post("/test-data/regenerate")
async def regenerate_test_data_endpoint(request: RegenerateTestDataRequest) -> dict[str, Any]:
    """Regenerate local test-market data and clear market caches."""
    state = regenerate_test_data(scenario=request.scenario, seed=request.seed)
    clear_provider_cache()
    invalidate_service_cache()
    return {
        "status": "success",
        "message": "Generated test data has been regenerated.",
        "test_data": get_test_data_status(),
        "seed": state.seed,
        "scenario": state.scenario,
        "generated_at": state.generated_at,
    }
