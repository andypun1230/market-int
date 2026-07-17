from __future__ import annotations

from dataclasses import asdict, dataclass

from app.data.universes import CORE_BREADTH_UNIVERSE, SECTOR_ETF_MAP
from app.providers.symbols import normalize_market_symbol


@dataclass(frozen=True)
class SymbolRegistryEntry:
    app_symbol: str
    finnhub_symbol: str
    polygon_symbol: str
    asset_type: str
    quote_supported: bool
    history_supported: bool
    provider_history_symbol: str | None = None
    history_proxy: bool = False
    proxy_reason: str | None = None
    sector: str | None = None
    theme: str | None = None

    def model_dump(self) -> dict[str, object]:
        return asdict(self)


INDEX_ALIASES = {
    "DJI": ("DIA", "ETF proxy for Dow Jones Industrial Average"),
    "IXIC": ("QQQ", "ETF proxy for Nasdaq Composite"),
    "NDX": ("QQQ", "Nasdaq-100 ETF proxy"),
    "RUT": ("IWM", "ETF proxy for Russell 2000"),
    "SPX": ("SPY", "ETF proxy for S&P 500 Index"),
}
DEFAULT_WATCHLIST_SYMBOLS = ("MU", "NVDA", "ARM", "SNDK")
INDEX_SYMBOLS = ("SPY", "QQQ", "IWM", "DJI")
KNOWN_SECTOR_BY_SYMBOL = {item["symbol"]: item.get("sector") for item in CORE_BREADTH_UNIVERSE}


def build_symbol_registry(seed_symbols: list[str] | tuple[str, ...]) -> list[SymbolRegistryEntry]:
    symbols: dict[str, SymbolRegistryEntry] = {}

    def add(symbol: str, *, asset_type: str = "equity", sector: str | None = None, theme: str | None = None) -> None:
        app_symbol = normalize_market_symbol(symbol, apply_alias=False)
        provider_symbol = normalize_market_symbol(app_symbol, apply_alias=True)
        alias = INDEX_ALIASES.get(app_symbol)
        symbols[app_symbol] = SymbolRegistryEntry(
            app_symbol=app_symbol,
            finnhub_symbol=provider_symbol,
            polygon_symbol=provider_symbol,
            asset_type=asset_type,
            quote_supported=True,
            history_supported=True,
            provider_history_symbol=provider_symbol,
            history_proxy=bool(alias),
            proxy_reason=alias[1] if alias else None,
            sector=sector,
            theme=theme,
        )

    for symbol in seed_symbols:
        asset_type = "index_proxy" if symbol.upper() in INDEX_ALIASES else "equity_or_etf"
        add(symbol, asset_type=asset_type)

    for symbol in DEFAULT_WATCHLIST_SYMBOLS + INDEX_SYMBOLS:
        add(symbol, sector=KNOWN_SECTOR_BY_SYMBOL.get(symbol))

    for sector, symbol in SECTOR_ETF_MAP.items():
        add(symbol, asset_type="etf", sector=sector)

    return sorted(symbols.values(), key=lambda entry: entry.app_symbol)


def provider_bound_symbols(seed_symbols: list[str] | tuple[str, ...], *, limit: int | None = None) -> list[str]:
    symbols = [entry.app_symbol for entry in build_symbol_registry(seed_symbols)]
    return symbols if limit is None else symbols[:limit]
