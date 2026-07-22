from __future__ import annotations

import unittest
from copy import deepcopy

from scripts.generate_stage7_copilot_artifacts import (
    STAGE7_SEMANTIC_ASSERTION_IDS,
    execute_fixture,
)
from tests.fixtures.stage7_copilot import (
    STAGE7_COPILOT_FIXTURES,
    STAGE7_FIXTURE_BY_ID,
)


class Stage7ArtifactAssertionTests(unittest.TestCase):
    def test_registry_covers_every_declared_assertion_id_exactly(self) -> None:
        declared = {
            assertion_id
            for fixture in STAGE7_COPILOT_FIXTURES
            for assertion_id in fixture["expected"]["assertions"]
        }

        self.assertEqual(STAGE7_SEMANTIC_ASSERTION_IDS, declared)

    def test_every_fixture_executes_each_declared_semantic_assertion(self) -> None:
        for fixture in STAGE7_COPILOT_FIXTURES:
            with self.subTest(fixture=fixture["caseId"]):
                execution = execute_fixture(fixture)
                assertion_checks = {
                    item["check"].removeprefix("assertion:"): item["status"]
                    for item in execution["validation"]["checksRun"]
                    if item["check"].startswith("assertion:")
                }

                self.assertEqual(execution["status"], "passed")
                self.assertEqual(
                    set(assertion_checks),
                    set(fixture["expected"]["assertions"]),
                )
                self.assertEqual(set(assertion_checks.values()), {"passed"})

    def test_unknown_assertion_id_fails_closed(self) -> None:
        fixture = deepcopy(STAGE7_FIXTURE_BY_ID["market-state"])
        fixture["expected"]["assertions"].append("unknown_semantic_contract")

        execution = execute_fixture(fixture)
        unknown = next(
            item
            for item in execution["validation"]["checksRun"]
            if item["check"] == "assertion:unknown_semantic_contract"
        )

        self.assertEqual(execution["status"], "failed")
        self.assertEqual(unknown["status"], "failed")
        self.assertIn("Unknown semantic assertion ID", unknown["detail"])

    def test_known_assertion_fails_when_its_semantics_do_not_hold(self) -> None:
        fixture = deepcopy(STAGE7_FIXTURE_BY_ID["market-state"])
        fixture["expected"]["assertions"] = ["empty_state_explicit"]

        execution = execute_fixture(fixture)
        semantic = next(
            item
            for item in execution["validation"]["checksRun"]
            if item["check"] == "assertion:empty_state_explicit"
        )

        self.assertEqual(execution["status"], "failed")
        self.assertEqual(semantic["status"], "failed")

    def test_unnecessary_agent_fails_without_explicit_allowlist(self) -> None:
        fixture = deepcopy(STAGE7_FIXTURE_BY_ID["market-explanation"])
        fixture["expected"]["requiredAgents"] = ["market"]

        execution = execute_fixture(fixture)
        selection = next(
            item
            for item in execution["validation"]["checksRun"]
            if item["check"] == "agent_selection"
        )

        self.assertEqual(execution["status"], "failed")
        self.assertEqual(selection["status"], "failed")

    def test_explicit_agent_allowlist_accepts_an_allowed_optional_agent(self) -> None:
        fixture = deepcopy(STAGE7_FIXTURE_BY_ID["market-explanation"])
        fixture["expected"]["requiredAgents"] = ["market"]
        fixture["expected"]["allowedAgents"] = ["market", "breadth"]

        execution = execute_fixture(fixture)
        selection = next(
            item
            for item in execution["validation"]["checksRun"]
            if item["check"] == "agent_selection"
        )

        self.assertEqual(execution["status"], "passed")
        self.assertEqual(selection["status"], "passed")

    def test_explicit_empty_saved_symbols_are_complete_cached_membership(self) -> None:
        execution = execute_fixture(STAGE7_FIXTURE_BY_ID["empty-watchlist"])
        response = execution["response"]
        watchlist = execution["agentResults"][0]

        self.assertEqual(execution["status"], "passed")
        self.assertEqual(response["status"], "complete")
        self.assertEqual(response["freshnessSummary"]["overallState"], "cached")
        self.assertEqual(response["reasoning"]["directAnswer"], "There are no saved stocks to review.")
        self.assertEqual(watchlist["status"], "complete")
        self.assertEqual(watchlist["metrics"]["membership_state"], "empty")
        self.assertEqual(watchlist["metrics"]["membership_scope"], "device_local")


if __name__ == "__main__":
    unittest.main()
