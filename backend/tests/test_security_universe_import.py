from __future__ import annotations

import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.providers.finnhub_provider import ProviderRequestError
from app.securities.import_validation import validate_reviewed_source_rows
from app.securities.models import BreadthUniverseMember
from app.securities.service import SecurityMasterService
from app.securities.storage import SecurityMasterStorage


BACKEND_ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = BACKEND_ROOT / "data" / "reference" / "sp100-2026-07-18.csv"


def load_seed_module():
    spec = importlib.util.spec_from_file_location("seed_breadth_universe", BACKEND_ROOT / "scripts" / "seed_breadth_universe.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SecurityUniverseImportTests(unittest.TestCase):
    def test_reviewed_sp100_source_has_expected_count_and_contract(self) -> None:
        with SOURCE_FILE.open(newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            errors = validate_reviewed_source_rows(rows, reader.fieldnames)
        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 101)
        self.assertEqual(len({row["ticker"] for row in rows}), 101)
        brk = next(row for row in rows if row["ticker"] == "BRK.B")
        self.assertEqual(brk["history_provider_symbol"], "BRK-B")

    def test_reviewed_contract_rejects_missing_provenance_and_bad_mapping(self) -> None:
        rows = [{
            "ticker": "BRK.B", "company_name": "Berkshire", "exchange": "NYSE", "sector": "Financials",
            "industry": "",
            "active": "true", "quote_provider_symbol": "BRK.B", "history_provider_symbol": "BRK-B",
            "asset_type": "equity", "source": "review", "source_effective_date": "2026-07-16", "verified_at": "2026-07-18",
        }]
        errors = validate_reviewed_source_rows(rows, list(rows[0]))
        self.assertIn("row:2:unexpected_quote_provider_symbol:BRK.B", errors)
        self.assertIn("file:missing_columns:industry", validate_reviewed_source_rows(rows, [key for key in rows[0] if key != "industry"]))

    def test_import_persists_reviewed_source_fields_and_provider_symbols(self) -> None:
        with SOURCE_FILE.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        with tempfile.TemporaryDirectory() as tmp:
            service = SecurityMasterService(SecurityMasterStorage(Path(tmp) / "sp100.sqlite3"))
            report = service.import_universe(name="sp100", version="v20260718", effective_date="2026-07-18", benchmark_symbol="SPY", rows=rows, source="fallback", source_timestamp="2026-07-16", dry_run=False)
            security = service.storage.security("BRK.B")
            universe = service.storage.get_active_universe("sp100")
        self.assertEqual(report.member_count, 101)
        self.assertEqual(universe.source_timestamp, "2026-07-16")
        self.assertEqual(security.history_provider_symbol, "BRK-B")
        self.assertEqual(security.source, "BlackRock iShares OEF fund-holdings export")
        self.assertEqual(security.verified_at, "2026-07-18")

    def test_staged_seed_selection_is_deterministic_and_rejects_unknown_symbols(self) -> None:
        seed = load_seed_module()
        members = [
            BreadthUniverseMember("u", "a", "AAPL", "Information Technology"),
            BreadthUniverseMember("u", "m", "MSFT", "Information Technology"),
            BreadthUniverseMember("u", "x", "XOM", "Energy"),
        ]
        self.assertEqual([member.ticker for member in seed.select_members(members, None, 2)], ["AAPL", "MSFT"])
        self.assertEqual([member.ticker for member in seed.select_members(members, "XOM,AAPL", None)], ["AAPL", "XOM"])
        with self.assertRaisesRegex(ValueError, "not active universe"):
            seed.select_members(members, "INVALID", None)

    def test_staged_seed_retries_rate_limits_without_losing_the_member(self) -> None:
        seed = load_seed_module()

        class Updater:
            attempts = 0
            provider_symbols: list[str] = []

            def update_symbol(self, ticker: str, *, provider_symbol: str, lookback_calendar_days: int, strict_live: bool) -> dict:
                self.attempts += 1
                self.provider_symbols.append(provider_symbol)
                if self.attempts == 1:
                    raise ProviderRequestError("rate limited", category="rate_limited")
                return {"ticker": ticker, "status": "complete"}

        updater = Updater()
        with patch.object(seed.time, "sleep") as sleep:
            result = seed.update_with_retries(updater, "AAPL", "AAPL", 450, 2, True)
        self.assertEqual(result["retry_count"], 1)
        self.assertEqual(updater.attempts, 2)
        self.assertEqual(updater.provider_symbols, ["AAPL", "AAPL"])
        sleep.assert_called_once_with(1)


if __name__ == "__main__":
    unittest.main()
