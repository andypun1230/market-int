from fastapi import APIRouter, HTTPException

from app.models.market import (
    AllStockAnalysisResponse,
    MarketAnalysisResponse,
    StockAnalysisResponse,
)
from app.services.analysis import (
    build_all_stock_analyses,
    build_market_analysis,
    build_stock_analysis,
)

router = APIRouter()


@router.get("/analysis/market", response_model=MarketAnalysisResponse)
async def get_market_analysis() -> MarketAnalysisResponse:
    """Return an AI-ready structured market analysis package."""
    return build_market_analysis()


@router.get("/analysis/stock/{symbol}", response_model=StockAnalysisResponse)
async def get_stock_analysis(symbol: str) -> StockAnalysisResponse:
    """Return an AI-ready structured stock analysis package."""
    try:
        return build_stock_analysis(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/analysis/stocks", response_model=AllStockAnalysisResponse)
async def get_all_stock_analyses() -> AllStockAnalysisResponse:
    """Return AI-ready structured analysis packages for the watchlist universe."""
    return build_all_stock_analyses()
