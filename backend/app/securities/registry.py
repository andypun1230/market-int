from __future__ import annotations

from datetime import datetime, timezone

from app.data.universes import CORE_BREADTH_UNIVERSE, SECTOR_ETF_MAP

# The import command, rather than application startup, creates the live universe.
# This source is recorded on every import so membership can be reviewed and replaced.
SP100_SOURCE_URL = "https://www.spglobal.com/spdji/en/indices/equity/sp-100/"
SP100_SOURCE_NAME = "S&P Dow Jones Indices S&P 100 constituent export"


def normalized_sector(value: str | None) -> str:
    text = (value or "Unknown").strip()
    aliases = {
        "technology": "Information Technology",
        "healthcare": "Health Care",
        "consumer defensive": "Consumer Staples",
    }
    return aliases.get(text.lower(), text)


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
