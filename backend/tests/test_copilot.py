import unittest
from unittest.mock import patch

from app.services.copilot_context_builder import sanitize_copilot_context
from app.services.copilot_formatting import format_copilot_label
from app.services.copilot_service import answer_copilot_chat


class CopilotTests(unittest.TestCase):
    def test_sanitizer_removes_sensitive_keys_and_limits_lists(self) -> None:
        context = {
            "screenType": "home",
            "sourceState": "mock",
            "api_key": "secret",
            "watchlist": {"items": [{"ticker": str(index)} for index in range(20)]},
        }

        sanitized = sanitize_copilot_context(context)

        self.assertNotIn("api_key", sanitized)
        self.assertEqual(len(sanitized["watchlist"]["items"]), 12)

    def test_conviction_explanation_uses_real_components(self) -> None:
        with patch("app.services.copilot_service.generate_structured_chat_response", return_value=None):
            response = answer_copilot_chat(
                "Why is Conviction only 77?",
                {
                    "screenType": "report",
                    "screenTitle": "Daily Report",
                    "sourceState": "mock",
                    "report": {
                        "marketConviction": {
                            "score": 77,
                            "rating": "Constructive",
                            "whyNotHigher": ["Sentiment remains elevated."],
                            "whyNotLower": ["Breadth confirms the trend."],
                            "contributors": [{"label": "Breadth", "score": 80}],
                        },
                        "risk": {"score": 22, "status": "Low Risk"},
                        "breadth": {"score": 74, "status": "Broad participation"},
                        "topSector": "Technology",
                        "confidence": {"score": 79, "reason": "trend and breadth agree"},
                    },
                },
            )

        self.assertIn("77", response["answer"])
        self.assertIn("Today's story", response["answer"])
        self.assertIn("strongest counterargument", response["answer"].lower())
        self.assertIn("So what", response["answer"])
        self.assertNotIn("mock market data", response["answer"].lower())
        self.assertIn("Daily Report", response["grounding"]["contextUsed"])
        self.assertEqual(response["grounding"]["sourceState"], "mock")
        self.assertEqual(response["answerConfidence"]["level"], "moderate")
        self.assertTrue(any("Trend" in reason or "Health" in reason for reason in response["answerConfidence"]["reasons"]))
        self.assertLessEqual(len(response["answerSections"]["why"]), 3)
        self.assertLessEqual(len(response["answerSections"]["whatWouldChange"]), 2)

    def test_watchlist_ranking_uses_loaded_items(self) -> None:
        with patch("app.services.copilot_service.generate_structured_chat_response", return_value=None):
            response = answer_copilot_chat(
                "Rank my watchlist.",
                {
                    "screenType": "watchlist",
                    "screenTitle": "Watchlist",
                    "sourceState": "mixed",
                    "watchlist": {
                        "items": [
                            {"ticker": "ARM", "score": 70, "signal": "Watching", "changePercent": 8.5},
                            {"ticker": "NVDA", "score": 90, "signal": "Strong Momentum", "trend": "Bullish", "changePercent": -0.5},
                        ],
                    },
                },
            )

        self.assertIn("NVDA", response["answer"])
        self.assertLess(response["answer"].find("NVDA"), response["answer"].find("ARM") if "ARM" in response["answer"] else 999)
        self.assertEqual(response["grounding"]["sourceState"], "mixed")

    def test_dynamic_comparison_loads_missing_peer(self) -> None:
        with (
            patch("app.services.copilot_service.generate_structured_chat_response", return_value=None),
            patch(
                "app.services.copilot_entities.build_stock_ai_context",
                return_value={
                    "score": 88,
                    "status": "Constructive",
                    "risk_level": "Moderate",
                    "relative_strength_status": "Strong",
                    "multi_timeframe_alignment": "Bullish",
                    "volume_quality": "Healthy",
                    "main_pattern": {"name": "near_breakout"},
                    "data_quality": {"overall_mode": "mixed"},
                },
            ),
        ):
            response = answer_copilot_chat(
                "Compare this stock with NVDA",
                {
                    "screenType": "stock",
                    "screenTitle": "ARM Stock Detail",
                    "sourceState": "mixed",
                    "stock": {
                        "stock": {"ticker": "ARM"},
                        "stockRating": {"overall_score": 76},
                        "status": "Constructive",
                    },
                },
            )

        self.assertIn("ARM", response["answer"])
        self.assertIn("NVDA", response["answer"])
        self.assertTrue(any(item.startswith("Conviction:") or item.startswith("Momentum:") for item in response["answerSections"]["why"]))
        self.assertIn("Data gap", response["answerSections"]["mainCaution"])

    def test_conversation_memory_routes_follow_up(self) -> None:
        with patch("app.services.copilot_service.generate_structured_chat_response", return_value=None):
            response = answer_copilot_chat(
                "Would Financials change that?",
                {
                    "screenType": "report",
                    "screenTitle": "Daily Report",
                    "sourceState": "mock",
                    "report": {
                        "marketConviction": {
                            "score": 77,
                            "rating": "Selective",
                            "contributors": [{"label": "Breadth", "score": 80}],
                        },
                        "risk": {"score": 22, "status": "Low Risk"},
                        "breadth": {"score": 72, "status": "Broad participation"},
                        "topSector": "Technology",
                    },
                },
                history=[{"role": "user", "content": "Why is Conviction 77?"}],
            )

        self.assertIn("Conviction", response["answer"])
        self.assertIn("If", response["answer"])

    def test_internal_labels_are_human_readable(self) -> None:
        self.assertEqual(format_copilot_label("near_breakout"), "Near breakout")
        self.assertEqual(format_copilot_label("primarySignal"), "Primary Signal")

    def test_financial_advice_request_is_reframed(self) -> None:
        with patch("app.services.copilot_service.generate_structured_chat_response", return_value=None):
            response = answer_copilot_chat(
                "Should I buy NVDA?",
                {
                    "screenType": "stock",
                    "screenTitle": "NVDA Stock Detail",
                    "sourceState": "mock",
                    "stock": {"symbol": "NVDA", "score": 85},
                },
            )

        self.assertIn("cannot give personal buy", response["answer"].lower())
        self.assertNotIn("Buy NVDA now", response["answer"])
        self.assertEqual(response["answerConfidence"]["level"], "moderate")


if __name__ == "__main__":
    unittest.main()
