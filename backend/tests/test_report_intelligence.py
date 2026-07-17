import unittest

from app.services.report_intelligence import (
    DecisionChecklistEngine,
    MarketConvictionEngine,
    MarketEvolutionEngine,
    PreviousPlaybookEngine,
    ReportComparisonEngine,
    RelationshipEngine,
    ScenarioEngine,
    SignalConvergenceEngine,
    build_hidden_warnings,
    build_report_intelligence,
)


class ReportIntelligenceTests(unittest.TestCase):
    def test_comparison_ignores_noise_and_keeps_meaningful_changes(self) -> None:
        previous = {
            "marketHealth": {"score": 80},
            "risk": {"score": 31},
            "breadth": {"score": 69},
            "regime": "Uptrend Under Pressure",
            "sectorRanking": [{"name": "Technology"}, {"name": "Utilities"}, {"name": "Financials"}],
            "themeRanking": [{"name": "AI Infrastructure"}, {"name": "Memory"}],
            "watchlistSummary": [{"symbol": "NVDA", "setup": "Neutral", "trend": "Watch"}],
            "macroSummary": {"events": ["CPI"]},
        }
        current = {
            "marketHealth": {"score": 85},
            "risk": {"score": 22},
            "breadth": {"score": 71},
            "regime": "Confirmed Uptrend",
            "sectorRanking": [{"name": "Technology"}, {"name": "Financials"}, {"name": "Utilities"}],
            "themeRanking": [{"name": "Memory"}, {"name": "AI Infrastructure"}],
            "watchlistSummary": [{"symbol": "NVDA", "setup": "Strong Setup", "trend": "Bullish"}],
            "macroSummary": {"events": ["CPI", "Fed speakers"]},
        }

        changes = ReportComparisonEngine().compare(previous, current)
        labels = [item["label"] for item in changes["items"]]

        self.assertTrue(changes["available"])
        self.assertIn("Market Health", labels)
        self.assertIn("Risk", labels)
        self.assertNotIn("Breadth", labels)
        self.assertIn("Market Regime", labels)
        self.assertIn("NVDA Setup", labels)
        self.assertTrue(any("Macro Event" == label for label in labels))
        self.assertTrue(all(item.get("reason") for item in changes["items"] if item.get("label") != "Market Regime"))
        self.assertLessEqual(len(changes["items"]), 8)
        self.assertFalse(any(item.get("previous") == "#1" and item.get("current") == "#1" for item in changes["items"]))

    def test_signal_convergence_rating_changes_with_inputs(self) -> None:
        strong = {
            "signalSummary": {
                "trend": 90,
                "breadth": 80,
                "sectorStrength": 82,
                "volume": 75,
                "momentum": 77,
                "risk": 22,
                "sentiment": 65,
            },
            "themeRanking": [{"name": "Memory", "return": 2.4}],
            "macroSummary": {"state": "Neutral"},
        }
        weak = {
            "signalSummary": {
                "trend": 45,
                "breadth": 42,
                "sectorStrength": 50,
                "volume": 45,
                "momentum": 40,
                "risk": 72,
                "sentiment": 88,
            },
            "themeRanking": [{"name": "Memory", "return": -1.2}],
            "macroSummary": {"state": "High Risk"},
        }

        self.assertEqual(SignalConvergenceEngine().calculate(strong)["rating"], "High")
        self.assertEqual(SignalConvergenceEngine().calculate(weak)["rating"], "Low")

    def test_market_conviction_reacts_to_disagreement(self) -> None:
        aligned = {
            "signalSummary": {"trend": 90, "breadth": 90, "sectorStrength": 85, "volume": 85, "momentum": 88, "risk": 20, "sentiment": 62},
            "sectorRanking": [{"name": "Technology", "return": 2.0}],
            "themeRanking": [{"name": "Memory", "return": 2.0}],
            "macroSummary": {"state": "Neutral"},
        }
        conflicted = {
            "signalSummary": {"trend": 90, "breadth": 35, "sectorStrength": 55, "volume": 45, "momentum": 50, "risk": 68, "sentiment": 85},
            "sectorRanking": [{"name": "Technology", "return": -1.0}],
            "themeRanking": [{"name": "Memory", "return": -1.0}],
            "macroSummary": {"state": "High Risk"},
        }

        high = MarketConvictionEngine().calculate(aligned, SignalConvergenceEngine().calculate(aligned), [])
        low = MarketConvictionEngine().calculate(conflicted, SignalConvergenceEngine().calculate(conflicted), ["Trend is not confirmed."])

        self.assertGreater(high["score"], low["score"])
        self.assertIn(high["rating"], {"High Conviction", "Exceptional Alignment"})
        self.assertTrue(high["whyNotHigher"])
        self.assertTrue(high["whyNotLower"])

    def test_decision_checklist_and_scenarios_are_deterministic(self) -> None:
        snapshot = {
            "signalSummary": {"trend": 80, "breadth": 75, "sectorStrength": 70, "risk": 30},
            "macroSummary": {"state": "Neutral"},
            "watchlistSummary": [{"changePercent": 1.0}, {"changePercent": -0.5}],
        }

        checklist = DecisionChecklistEngine().build(snapshot)
        scenarios = ScenarioEngine().build(snapshot, {"score": 80}, [])

        self.assertEqual(checklist["total"], 7)
        self.assertTrue(all(item.get("reason") for item in checklist["items"]))
        self.assertEqual(len(scenarios), 3)
        self.assertEqual(scenarios[0]["name"], "Bullish Continuation")
        self.assertEqual(sum(item["probability"] for item in scenarios), 100)
        self.assertTrue(all(item.get("why") and item.get("changesProbability") for item in scenarios))

    def test_relationship_engine_detects_cross_signal_context(self) -> None:
        snapshot = {
            "signalSummary": {
                "trend": 82,
                "breadth": 78,
                "risk": 24,
                "sentiment": 78,
                "volume": 72,
            },
            "sectorRanking": [{"name": "Technology", "return": 1.5}],
            "themeRanking": [{"name": "Semiconductors", "return": 2.1}],
        }

        relationships = RelationshipEngine().detect(snapshot)

        self.assertGreaterEqual(len(relationships), 2)
        self.assertTrue(any("Breadth" in item for item in relationships))
        self.assertTrue(any("Sector and theme" in item for item in relationships))

    def test_previous_playbook_and_evolution_use_stored_reports_only(self) -> None:
        previous = {
            "marketHealth": {"score": 76},
            "risk": {"score": 31},
            "sectorRanking": [{"name": "Technology"}],
            "playbook": {"headline": "Stay Selective"},
            "historicalMetrics": {"health": 76, "risk": 31, "breadth": 62, "conviction": 68, "confidence": 70},
        }
        current = {
            "marketHealth": {"score": 85},
            "risk": {"score": 22},
            "sectorRanking": [{"name": "Technology"}],
            "historicalMetrics": {"health": 85, "risk": 22, "breadth": 71},
        }

        review = PreviousPlaybookEngine().review(previous, current)
        evolution = MarketEvolutionEngine().build([previous], current, {"score": 91}, {"score": 87})

        self.assertTrue(review["available"])
        self.assertGreaterEqual(review["score"], 7.5)
        self.assertTrue(evolution["available"])
        self.assertEqual(len(evolution["points"]), 2)

    def test_hidden_warnings_detect_contradictions(self) -> None:
        snapshot = {
            "signalSummary": {
                "trend": 85,
                "breadth": 48,
                "risk": 20,
                "sentiment": 82,
                "sectorStrength": 78,
                "volume": 44,
            },
            "sectorRanking": [{"name": "Technology", "return": 3.0}, {"name": "Utilities", "return": -1.0}],
            "themeRanking": [{"name": "Memory", "return": 2.2}],
            "watchlistSummary": [{"symbol": "MU", "changePercent": -2.0}, {"symbol": "ARM", "changePercent": -1.0}],
        }

        warnings = build_hidden_warnings(snapshot, {"items": []})

        self.assertGreaterEqual(len(warnings), 3)
        self.assertTrue(any("breadth" in warning.lower() for warning in warnings))
        self.assertTrue(any("sentiment" in warning.lower() for warning in warnings))

    def test_report_intelligence_builds_shared_narrative(self) -> None:
        snapshot = {
            "regime": "Confirmed Uptrend",
            "marketHealth": {"score": 85, "status": "Very Healthy"},
            "risk": {"score": 22, "status": "Low"},
            "breadth": {"score": 80, "status": "Healthy"},
            "sectorRanking": [{"name": "Technology", "return": 2.0}],
            "themeRanking": [{"name": "Memory", "return": 2.4}],
            "watchlistSummary": [],
            "signalSummary": {
                "trend": 80,
                "breadth": 80,
                "sectorStrength": 78,
                "volume": 70,
                "momentum": 76,
                "risk": 22,
                "sentiment": 66,
            },
            "macroSummary": {"state": "Neutral", "events": []},
            "playbook": {"headline": "Stay Selective", "mainRisk": "Elevated sentiment"},
        }

        intelligence = build_report_intelligence(None, snapshot)

        self.assertIn("narrative", intelligence)
        self.assertIn("crossTabNarrative", intelligence["narrative"])
        self.assertEqual(intelligence["convergence"]["rating"], "High")
        self.assertIn("conviction", intelligence)
        self.assertIn("checklist", intelligence)
        self.assertIn("confidence", intelligence)
        self.assertIn("relationships", intelligence)
        self.assertIn("commentary", intelligence)
        self.assertIn("tradeOff", intelligence["commentary"])
        self.assertIn("historicalContext", intelligence["commentary"])
        self.assertIn("confidenceReasoning", intelligence["narrative"])
        self.assertEqual(len(intelligence["scenarios"]), 3)


if __name__ == "__main__":
    unittest.main()
