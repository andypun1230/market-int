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


@dataclass(frozen=True)
class CanonicalIndexEntry:
    display_symbol: str
    display_name: str
    asset_type: str
    quote_symbol: str
    history_symbol: str
    provider_quote_symbol: str
    provider_history_symbol: str
    proxy_used: bool
    proxy_reason: str | None
    sort_order: int
    enabled: bool
    benchmark_group: str

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
INDEX_SYMBOLS = ("SPY", "QQQ", "IWM", "DIA")
CANONICAL_INDEXES: tuple[CanonicalIndexEntry, ...] = (
    CanonicalIndexEntry("SPY", "S&P 500", "index_proxy", "SPY", "SPY", "SPY", "SPY", False, None, 10, True, "core"),
    CanonicalIndexEntry("QQQ", "Nasdaq-100", "index_proxy", "QQQ", "QQQ", "QQQ", "QQQ", False, None, 20, True, "core"),
    CanonicalIndexEntry("IWM", "Russell 2000", "index_proxy", "IWM", "IWM", "IWM", "IWM", False, None, 30, True, "core"),
    CanonicalIndexEntry("DIA", "Dow Jones", "index_proxy", "DIA", "DIA", "DIA", "DIA", False, None, 40, True, "core"),
    CanonicalIndexEntry("RSP", "S&P 500 Equal Weight", "index_proxy", "RSP", "RSP", "RSP", "RSP", False, None, 50, True, "equal_weight"),
    CanonicalIndexEntry("QQEW", "Nasdaq-100 Equal Weight", "index_proxy", "QQEW", "QQEW", "QQEW", "QQEW", False, None, 60, True, "equal_weight"),
)
CANONICAL_INDEX_BY_DISPLAY_SYMBOL = {entry.display_symbol: entry for entry in CANONICAL_INDEXES}
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


def canonical_index_universe(*, include_optional: bool = False) -> list[CanonicalIndexEntry]:
    entries = [entry for entry in CANONICAL_INDEXES if entry.enabled]
    if not include_optional:
        entries = [entry for entry in entries if entry.benchmark_group == "core"]
    return sorted(entries, key=lambda entry: entry.sort_order)


def get_canonical_index_entry(symbol: str) -> CanonicalIndexEntry:
    provider_symbol = normalize_market_symbol(symbol, apply_alias=True)
    entry = CANONICAL_INDEX_BY_DISPLAY_SYMBOL.get(provider_symbol)
    if entry is None:
        raise KeyError(f"Unsupported index symbol: {symbol}")
    return entry
