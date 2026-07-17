import unittest

from app.providers.symbols import normalize_market_symbol
from app.validation.symbol_registry import build_symbol_registry


class SymbolRegistryTests(unittest.TestCase):
    def test_index_display_symbols_map_to_provider_supported_etfs(self) -> None:
        self.assertEqual(normalize_market_symbol("SPX", apply_alias=True), "SPY")
        self.assertEqual(normalize_market_symbol("IXIC", apply_alias=True), "QQQ")
        self.assertEqual(normalize_market_symbol("NDX", apply_alias=True), "QQQ")
        self.assertEqual(normalize_market_symbol("QQQEW", apply_alias=True), "QQEW")
        self.assertEqual(normalize_market_symbol("RUT", apply_alias=True), "IWM")
        self.assertEqual(normalize_market_symbol("DJI", apply_alias=True), "DIA")

    def test_class_share_symbol_is_preserved(self) -> None:
        self.assertEqual(normalize_market_symbol("brk.b", apply_alias=True), "BRK.B")

    def test_ndx_registry_records_provider_history_proxy(self) -> None:
        entries = {entry.app_symbol: entry for entry in build_symbol_registry(["NDX"])}
        ndx = entries["NDX"]

        self.assertEqual(ndx.provider_history_symbol, "QQQ")
        self.assertEqual(ndx.polygon_symbol, "QQQ")
        self.assertEqual(ndx.asset_type, "index_proxy")
        self.assertTrue(ndx.history_proxy)
        self.assertEqual(ndx.proxy_reason, "Nasdaq-100 ETF proxy")


if __name__ == "__main__":
    unittest.main()
