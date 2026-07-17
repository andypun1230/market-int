from app.models.market import InstitutionalIntelligenceResponse
from app.services.institutional_dashboard import build_institutional_dashboard
from app.services.liquidity_dashboard import build_liquidity_dashboard
from app.services.market_sentiment import build_market_sentiment_dashboard
from app.services.money_flow import build_money_flow_dashboard
from app.services.options_intelligence import build_options_intelligence
from app.services.service_cache import get_or_compute, get_service_ttl


def build_institutional_intelligence_dashboard() -> InstitutionalIntelligenceResponse:
    return get_or_compute(
        "institutional-intelligence",
        get_service_ttl("SERVICE_CACHE_INSTITUTIONAL_TTL_SECONDS", 300),
        _build_institutional_intelligence_dashboard_uncached,
    )


def _build_institutional_intelligence_dashboard_uncached() -> InstitutionalIntelligenceResponse:
    sentiment = build_market_sentiment_dashboard()
    money_flow = build_money_flow_dashboard()
    institutional = build_institutional_dashboard()
    options = build_options_intelligence()
    liquidity = build_liquidity_dashboard()

    return InstitutionalIntelligenceResponse(
        sentiment=sentiment,
        money_flow=money_flow,
        institutional=institutional,
        options=options,
        liquidity=liquidity,
        summary=(
            f"Institutional intelligence is constructive: {institutional.status} institutional bias, "
            f"{money_flow.status.lower()} estimated money flow, {options.status.lower()} with "
            f"estimated gamma exposure, {liquidity.status.lower()} liquidity, and large-print "
            "activity treated only as block-trade candidates."
        ),
    )
