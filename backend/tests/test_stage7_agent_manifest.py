from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.copilot.agents import AgentExecutionContext, CopilotAgentRegistry
from app.copilot.contracts import (
    AgentResultV1,
    CopilotAgentName,
    CopilotDestination,
    CopilotEvidenceCategory,
    CopilotFreshnessState,
)


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
MANIFEST_PATH = BACKEND_ROOT / "app" / "copilot" / "agent_manifest.json"


class Stage7AgentManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.agents = cls.manifest["agents"]
        cls.by_id = {item["id"]: item for item in cls.agents}

    def test_manifest_has_exact_enum_and_runtime_registry_coverage(self) -> None:
        expected = {item.value for item in CopilotAgentName}
        self.assertEqual(set(self.by_id), expected)
        self.assertEqual(len(self.by_id), len(self.agents), "Agent IDs must be unique.")

        registry = CopilotAgentRegistry()
        self.assertEqual({item.value for item in registry._handlers}, expected)
        for agent_id, item in self.by_id.items():
            handler_name = item["handler"].removeprefix("CopilotAgentRegistry.")
            self.assertTrue(hasattr(CopilotAgentRegistry, handler_name), agent_id)
            self.assertEqual(registry._handlers[CopilotAgentName(agent_id)].__name__, handler_name)

    def test_every_entry_has_consistent_machine_validation_metadata(self) -> None:
        required_fields = {
            "contractVersion",
            "acceptedInputSchema",
            "outputSchema",
            "allowedEvidenceCategories",
            "allowedDestinations",
            "deterministic",
            "modelDependent",
            "requiredFreshness",
            "availabilityBehavior",
            "promptVersion",
            "modelVersion",
        }
        freshness_fields = {"allowedStates", "maximumAgeSource", "staleActionability"}
        availability_fields = {"missingInput", "partialInput", "exception"}
        for item in self.agents:
            with self.subTest(agent=item["id"]):
                self.assertTrue(required_fields <= set(item))
                self.assertEqual(item["contractVersion"], AgentResultV1.model_fields["schema_version"].default)
                self.assertEqual(
                    item["acceptedInputSchema"],
                    f"{AgentExecutionContext.__module__}.{AgentExecutionContext.__name__}",
                )
                self.assertEqual(
                    item["outputSchema"],
                    f"{AgentResultV1.__module__}.{AgentResultV1.__name__}",
                )
                self.assertIs(item["deterministic"], True)
                self.assertIs(item["modelDependent"], False)
                self.assertIsNone(item["promptVersion"])
                self.assertIsNone(item["modelVersion"])
                self.assertEqual(set(item["requiredFreshness"]), freshness_fields)
                self.assertEqual(set(item["availabilityBehavior"]), availability_fields)

    def test_manifest_values_use_public_contract_enums(self) -> None:
        evidence_categories = {item.value for item in CopilotEvidenceCategory}
        destinations = {item.value for item in CopilotDestination}
        freshness_states = {item.value for item in CopilotFreshnessState}
        for item in self.agents:
            with self.subTest(agent=item["id"]):
                self.assertTrue(set(item["allowedEvidenceCategories"]) <= evidence_categories)
                self.assertTrue(set(item["allowedDestinations"]) <= destinations)
                allowed_freshness = set(item["requiredFreshness"]["allowedStates"])
                self.assertTrue(allowed_freshness)
                self.assertTrue(allowed_freshness <= freshness_states)
                self.assertEqual(
                    item["allowedEvidenceCategories"],
                    item["output_schema"]["evidence_categories"],
                )

    def test_documented_source_and_test_paths_exist(self) -> None:
        for item in self.agents:
            with self.subTest(agent=item["id"]):
                self.assertTrue((REPOSITORY_ROOT / item["source_path"]).is_file())
                self.assertTrue(item["purpose"])
                self.assertTrue(item["accepted_inputs"])
                self.assertTrue(item["consumers"])
                self.assertTrue(item["fallbacks"])
                self.assertTrue(item["existing_tests"])
                self.assertTrue(item["missing_tests"])
                for selector in item["existing_tests"]:
                    test_path = selector.split("::", 1)[0]
                    self.assertTrue((REPOSITORY_ROOT / test_path).is_file(), selector)

    def test_manifest_runtime_contract_matches_header(self) -> None:
        self.assertEqual(self.manifest["schema_version"], "stage7-agent-manifest-v1")
        runtime = self.manifest["runtime"]
        self.assertEqual(runtime["input_contract"], "app.copilot.agents.AgentExecutionContext")
        self.assertEqual(runtime["output_contract"], "app.copilot.contracts.AgentResultV1")
        self.assertEqual(runtime["output_schema_version"], "copilot-agent-result-v1")
        self.assertIsNone(runtime["execution"]["model_client"])
        self.assertIsNone(runtime["execution"]["prompt_template"])
        self.assertIsNone(runtime["execution"]["prompt_version"])


if __name__ == "__main__":
    unittest.main()
