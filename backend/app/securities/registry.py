from __future__ import annotations

from datetime import datetime, timezone

from app.data.universes import CORE_BREADTH_UNIVERSE, SECTOR_ETF_MAP

# The import command, rather than application startup, creates the live universe.
# This source is recorded on every import so membership can be reviewed and replaced.
SP100_SOURCE_URL = "https://www.spglobal.com/spdji/en/indices/equity/sp-100/"
SP100_SOURCE_NAME = "S&P Dow Jones Indices S&P 100 constituent export"


SECTOR_TAXONOMY = (
    ("communication_services", "Communication Services", "XLC", ("communication", "communications", "communication services")),
    ("consumer_discretionary", "Consumer Discretionary", "XLY", ("consumer cyclical", "consumer discretionary", "discretionary")),
    ("consumer_staples", "Consumer Staples", "XLP", ("consumer defensive", "consumer staples", "staples")),
    ("energy", "Energy", "XLE", ("energy",)),
    ("financials", "Financials", "XLF", ("financials", "financial services")),
    ("health_care", "Health Care", "XLV", ("health care", "healthcare")),
    ("industrials", "Industrials", "XLI", ("industrials", "industrial")),
    ("information_technology", "Information Technology", "XLK", ("technology", "information technology", "tech")),
    ("materials", "Materials", "XLB", ("materials", "basic materials")),
    ("real_estate", "Real Estate", "XLRE", ("real estate",)),
    ("utilities", "Utilities", "XLU", ("utilities", "utility")),
)

SECTOR_BY_ID = {item[0]: {"sector_id": item[0], "display_name": item[1], "etf_symbol": item[2]} for item in SECTOR_TAXONOMY}
SECTOR_ALIASES = {alias: item[0] for item in SECTOR_TAXONOMY for alias in (item[0], item[1].lower(), *item[3])}


def canonical_sector_id(value: str | None) -> str | None:
    text = (value or "").strip().lower().replace("&", "and")
    return SECTOR_ALIASES.get(text)


def normalized_sector(value: str | None) -> str:
    sector_id = canonical_sector_id(value)
    return SECTOR_BY_ID[sector_id]["display_name"] if sector_id else "Unknown"


def sector_definition(value: str | None) -> dict[str, str] | None:
    sector_id = canonical_sector_id(value)
    return dict(SECTOR_BY_ID[sector_id]) if sector_id else None


def provider_symbol_for(ticker: str) -> str:
    """Polygon uses a dash for class-share symbols such as BRK.B."""
    return ticker.strip().upper().replace(".", "-")


def default_test_universe_rows() -> list[dict[str, str]]:
    """Deterministic compact universe, only for explicit test mode."""
    return [
        {
            "ticker": item["symbol"],
            "company_name": item["symbol"],
            "sector": normalized_sector(item["sector"]),
            "source": "phase-4.4b-test-fixture",
            "source_timestamp": datetime.now(timezone.utc).date().isoformat(),
        }
        for item in CORE_BREADTH_UNIVERSE[:8]
    ]


def sector_etf_records() -> list[dict[str, str]]:
    return [
        {
            "ticker": ticker,
            "company_name": f"{sector} Select Sector SPDR",
            "sector": normalized_sector(sector),
            "asset_type": "etf",
            "source": "phase-4.4b-sector-etf-registry",
        }
        for sector, ticker in SECTOR_ETF_MAP.items()
    ]
