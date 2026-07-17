from __future__ import annotations

import re


SYMBOL_ALIASES = {
    "DJI": "DIA",
    "IXIC": "QQQ",
    "NDX": "QQQ",
    "QQQEW": "QQEW",
    "RUT": "IWM",
    "SPX": "SPY",
}
INVALID_SYMBOL_PLACEHOLDERS = {"INVALID", "INVALID_SYMBOL", "BAD_SYMBOL"}


def normalize_market_symbol(symbol: str, *, apply_alias: bool = False) -> str:
    value = str(symbol or "").strip().upper()
    if not value:
        raise ValueError("Symbol is required")
    if len(value) > 12:
        raise ValueError("Symbol is too long")
    if value in INVALID_SYMBOL_PLACEHOLDERS:
        raise ValueError("Symbol is marked invalid for validation")
    if not re.fullmatch(r"[A-Z0-9.\-]+", value):
        raise ValueError("Symbol contains unsupported characters")
    return SYMBOL_ALIASES.get(value, value) if apply_alias else value


def normalize_symbol_list(symbols: list[str], *, apply_alias: bool = False, limit: int = 50) -> list[str]:
    normalized: list[str] = []
    for symbol in symbols:
        value = normalize_market_symbol(symbol, apply_alias=apply_alias)
        if value not in normalized:
            normalized.append(value)
        if len(normalized) >= limit:
            break
    return normalized
