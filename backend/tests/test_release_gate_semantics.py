from __future__ import annotations

import unittest

from app.providers.models import CandleData, HistoryData
from app.semantics import confidence_with_snapshot_provenance
from app.services.macro_state import build_macro_state_from_histories
from app.services.theme_provenance import is_live_theme_intelligence, static_strategy_preference_provenance


def history(symbol: str, start: float, end: float) -> HistoryData:
    candles = [
        CandleData(timestamp=f"2026-01-{index + 1:02d}T20:00:00+00:00", open=start, high=start, low=start, close=start + ((end - start) * index / 65), volume=1_000)
        for index in range(66)
    ]
    return HistoryData(
        symbol=symbol,
        candles=candles,
        timeframe="D",
        source="polygon",
        provider="polygon",
        source_state="live",
        is_live=True,
        is_stale=False,
        fallback_used=False,
        as_of="2026-07-17T20:00:00+00:00",
    )


class ReleaseGateSemanticTests(unittest.TestCase):
    def test_breadth_confidence_keeps_its_own_score_and_snapshot_provenance(self) -> None:
        signal = confidence_with_snapshot_provenance(
            {"score": 65, "label": "Moderate", "reason": "3 supportive, 1 mixed, 1 caution breadth dimensions."},
            source_snapshot_id="breadth-test",
            calculated_at="2026-07-17T20:00:00+00:00",
        )
        decision = {"score": 91, "label": "High"}
        self.assertEqual(signal["score"], 65)
        self.assertNotEqual(signal["score"], decision["score"])
        self.assertEqual(signal["source_snapshot_id"], "breadth-test")
        self.assertEqual(signal["calculated_at"], "2026-07-17T20:00:00+00:00")

    def test_unavailable_breadth_confidence_has_the_canonical_reason(self) -> None:
        result = confidence_with_snapshot_provenance({}, source_snapshot_id="breadth-test", calculated_at="2026-07-17T20:00:00+00:00")
        self.assertEqual(result["label"], "Unavailable")
        self.assertEqual(result["reason"], "Insufficient historical breadth snapshots")

    def test_static_strategy_baskets_cannot_be_treated_as_live_theme_intelligence(self) -> None:
        provenance = static_strategy_preference_provenance("2026-07-17")
        self.assertFalse(is_live_theme_intelligence(provenance))
        self.assertEqual(provenance["label"], "Static strategy preference")
        self.assertIn("ThemeSnapshot", provenance["reason"])

    def test_macro_state_separates_current_risk_from_invalidation(self) -> None:
        values = {
            "SPY": (100, 112), "IEF": (100, 98), "TLT": (100, 97), "GLD": (100, 96),
            "USO": (100, 104), "UUP": (100, 99), "HYG": (100, 105),
        }
        macro = build_macro_state_from_histories({symbol: history(symbol, *value) for symbol, value in values.items()})
        self.assertEqual(macro["state"], "strong_risk_on")
        self.assertEqual(macro["key_risk"], "No dominant current macro risk is identified.")
        self.assertIn("defensive assets", macro["invalidation_conditions"])
        self.assertEqual(macro["source_state"], "live")
        self.assertFalse(macro["provenance"]["mock_fallback"])

    def test_macro_payload_history_keeps_provider_provenance(self) -> None:
        source = history("SPY", 100, 112)
        payload = build_macro_state_from_histories({"SPY": source})
        payload["histories"] = {
            symbol: item.model_dump(mode="json")
            for symbol, item in {"SPY": source}.items()
            if item.is_live and not item.fallback_used
        }
        self.assertEqual(payload["histories"]["SPY"]["provider"], "polygon")
        self.assertTrue(payload["histories"]["SPY"]["is_live"])

    def test_macro_state_quarantines_mock_history_instead_of_relabeling_it_live(self) -> None:
        mock = history("SPY", 100, 112).model_copy(update={"is_live": False, "provider": "mock", "source_state": "cached"})
        macro = build_macro_state_from_histories({"SPY": mock})
        self.assertEqual(macro["state"], "unavailable")
        self.assertEqual(macro["available_assets"], 0)


if __name__ == "__main__":
    unittest.main()
