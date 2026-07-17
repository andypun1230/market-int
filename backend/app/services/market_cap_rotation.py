from app.models.market import MarketCapRotationItem, MarketCapRotationResponse

MARKET_CAP_ROTATION = [
    {
        "category": "Mega Cap",
        "symbol": "QQQ",
        "score": 88,
        "return_1w": 2.8,
        "return_1m": 7.1,
        "relative_strength": 91,
        "money_flow": "Inflow",
        "status": "Leading",
    },
    {
        "category": "Large Cap",
        "symbol": "SPY",
        "score": 82,
        "return_1w": 2.1,
        "return_1m": 5.6,
        "relative_strength": 84,
        "money_flow": "Inflow",
        "status": "Strong",
    },
    {
        "category": "Mid Cap",
        "symbol": "MDY",
        "score": 64,
        "return_1w": 0.8,
        "return_1m": 2.3,
        "relative_strength": 61,
        "money_flow": "Neutral",
        "status": "Neutral",
    },
    {
        "category": "Small Cap",
        "symbol": "IWM",
        "score": 52,
        "return_1w": -0.4,
        "return_1m": 0.9,
        "relative_strength": 46,
        "money_flow": "Outflow",
        "status": "Lagging",
    },
    {
        "category": "Equal Weight",
        "symbol": "RSP",
        "score": 58,
        "return_1w": 0.5,
        "return_1m": 1.8,
        "relative_strength": 55,
        "money_flow": "Neutral",
        "status": "Neutral",
    },
]


def build_market_cap_rotation() -> MarketCapRotationResponse:
    items = [MarketCapRotationItem(**item) for item in MARKET_CAP_ROTATION]
    ranked = sorted(items, key=lambda item: item.score, reverse=True)

    return MarketCapRotationResponse(
        items=items,
        leader=ranked[0].category,
        laggard=ranked[-1].category,
        summary="Mega-cap growth continues to lead while small caps lag.",
    )
