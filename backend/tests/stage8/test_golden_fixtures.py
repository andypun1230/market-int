from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path

from tests.fixtures.stage8.generate_cases import build_cases, render, validate


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "stage8" / "cases.jsonl"


class Stage8GoldenFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = [json.loads(line) for line in FIXTURE_PATH.read_text(encoding="utf-8").splitlines()]

    def test_checked_in_corpus_matches_deterministic_generator(self) -> None:
        generated = build_cases()
        validate(generated)
        self.assertEqual(FIXTURE_PATH.read_text(encoding="utf-8"), render(generated))

    def test_corpus_has_at_least_one_hundred_meaningful_unique_cases(self) -> None:
        self.assertGreaterEqual(len(self.cases), 100)
        ids = [item["fixture_id"] for item in self.cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(len(item["description"].split()) >= 4 for item in self.cases))

    def test_requested_category_minimums_are_permanent(self) -> None:
        counts = Counter(category for item in self.cases for category in item["categories"])
        minimums = {
            "provider_normalization": 10,
            "source_credibility": 10,
            "classification": 15,
            "clustering": 15,
            "entity_mapping": 15,
            "materiality": 15,
            "market_reaction": 20,
            "session_segmentation": 15,
            "intraday_narrative": 20,
            "routing_synthesis": 20,
            "failure": 20,
        }
        for category, minimum in minimums.items():
            with self.subTest(category=category):
                self.assertGreaterEqual(counts[category], minimum)

    def test_all_thirty_required_release_cases_exist(self) -> None:
        required = {
            "primary-release-syndicated-copies", "rumour-later-confirmed", "rumour-later-disproved",
            "corrected-macro-release", "positive-headline-negative-stock", "negative-headline-positive-stock",
            "no-measurable-reaction", "sector-regulation", "multi-security-event",
            "ambiguous-common-word-ticker", "after-market-close-event", "premarket-event",
            "weekend-news", "stale-event", "missing-event-timestamp", "provider-unavailable",
            "intraday-reversal-after-event", "quiet-session-no-material-news", "daily-only-blocks-intraday",
            "partial-active-session", "shortened-session", "duplicate-different-headlines",
            "article-correction", "contradictory-sources", "macro-without-consensus",
            "bond-etf-proxy-no-yield", "price-without-volume-history", "watchlist-overlap-no-holdings",
            "theme-partial-constituent-impact", "catalyst-after-price-move",
        }
        self.assertTrue(required <= {item["fixture_id"] for item in self.cases})

    def test_fixture_data_can_never_masquerade_as_live_or_persist_bodies(self) -> None:
        for item in self.cases:
            with self.subTest(fixture=item["fixture_id"]):
                self.assertEqual(item["input"]["data_mode"], "hermetic")
                self.assertNotEqual(item["input"]["provider_mode"], "live")
                self.assertFalse(item["network_allowed"])
                self.assertEqual(item["model_calls_allowed"], 0)
                self.assertFalse(item["article_body_storage_allowed"])
                serialized = json.dumps(item).casefold()
                self.assertNotIn("api_key", serialized)
                self.assertNotIn("authentication_token", serialized)


if __name__ == "__main__":
    unittest.main()
