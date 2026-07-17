from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.analysis import router as analysis_router
from app.api.ai import router as ai_router
from app.api.copilot import router as copilot_router
from app.api.home import router as home_router
from app.api.market import router as market_router
from app.api.report import router as report_router
from app.api.system import router as system_router
from app.api.test_data import router as test_data_router
from app.cache.persistent_cache import initialize_persistent_cache, vacuum_expired_entries
from app.providers.finnhub_provider import ProviderRequestError
from app.services.background_refresh import (
    start_background_refresh_coordinator,
    stop_background_refresh_coordinator,
)
from app.snapshots.service import get_market_snapshot_service
from app.stock_snapshots.service import get_stock_snapshot_service
from app.services.workload_manager import interactive_request

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_persistent_cache()
    vacuum_expired_entries()
    get_market_snapshot_service().initialize()
    get_stock_snapshot_service().initialize()
    start_background_refresh_coordinator()
    get_market_snapshot_service().start_background_refresh()
    try:
        yield
    finally:
        get_market_snapshot_service().stop_background_refresh()
        stop_background_refresh_coordinator()


app = FastAPI(title="Market Intelligence Backend", version="0.1.0", lifespan=lifespan)

allowed_origins = [
    "http://localhost:8081",
    "http://localhost:8082",
    "http://localhost:19006",
    "http://127.0.0.1:8081",
    "http://127.0.0.1:8082",
    "http://127.0.0.1:19006",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.exception_handler(ProviderRequestError)
async def provider_request_error_handler(request: Request, exc: ProviderRequestError):
    category = getattr(exc, "category", "provider_error")
    status_code = 429 if category == "rate_limit" else 503
    logger.info(
        "Controlled provider failure path=%s category=%s",
        request.url.path,
        category,
    )
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "unavailable",
            "source_state": "unavailable",
            "category": category,
            "message": "Market data is unavailable for this request.",
            "path": request.url.path,
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.info("Controlled request validation failure path=%s reason=%s", request.url.path, exc)
    return JSONResponse(
        status_code=400,
        content={
            "status": "unavailable",
            "source_state": "unavailable",
            "category": "invalid_request",
            "message": str(exc) or "Request is invalid.",
            "path": request.url.path,
        },
    )


@app.middleware("http")
async def track_interactive_request(request, call_next):
    with interactive_request():
        return await call_next(request)

app.include_router(market_router)
app.include_router(home_router)
app.include_router(report_router)
app.include_router(analysis_router)
app.include_router(ai_router)
app.include_router(copilot_router)
app.include_router(system_router)
app.include_router(test_data_router)
