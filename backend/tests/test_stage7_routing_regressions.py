from __future__ import annotations

import unittest

from app.copilot.contracts import CopilotAgentName, CopilotDestination, CopilotIntentType
from app.copilot.entities import EntityResolution
from app.copilot.intent import CopilotIntentClassifier
from app.copilot.planner import CopilotPlanner


class _NoEntityResolver:
    def resolve(self, message: str, *, screen_context=None, active_entities=()):
        del message, screen_context, active_entities
        return EntityResolution()


class Stage7RoutingRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.classifier = CopilotIntentClassifier(resolver=_NoEntityResolver())

    def test_past_tense_market_fall_routes_to_minimal_market_explanation_plan(self) -> None:
        intent = self.classifier.classify("Why did the market fall?")
        plan = CopilotPlanner().build(intent)

        self.assertEqual(intent.intent, CopilotIntentType.MARKET_EXPLANATION)
        self.assertEqual(intent.required_agents, [CopilotAgentName.MARKET, CopilotAgentName.BREADTH])
        self.assertEqual(
            [step.agent for step in plan.ordered_steps],
            [CopilotAgentName.MARKET, CopilotAgentName.BREADTH],
        )
        self.assertLessEqual(len(plan.ordered_steps), 2)
        self.assertEqual(plan.deep_link_requirements, [CopilotDestination.MARKET_OVERVIEW])

    def test_unrelated_weather_question_remains_unsupported(self) -> None:
        intent = self.classifier.classify("What is the weather?")
        self.assertEqual(intent.intent, CopilotIntentType.UNSUPPORTED_OR_AMBIGUOUS)
        self.assertEqual(intent.required_agents, [])


if __name__ == "__main__":
    unittest.main()
