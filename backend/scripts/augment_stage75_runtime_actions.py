from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.copilot.evaluation.runtime import run_runtime_scenario, runtime_scenarios


ACTION_CAPTURE_SCHEMA_VERSION = "stage75-runtime-action-capture-v1"


def capture_actions() -> dict[str, list[dict[str, Any]]]:
    """Execute the hermetic runtime scenarios and retain exact action payloads."""

    captured: dict[str, list[dict[str, Any]]] = {}
    for scenario in runtime_scenarios():
        execution = run_runtime_scenario(scenario)
        captured[scenario.scenario_id] = [
            action.model_dump(mode="json", by_alias=True)
            for action in execution.response.actions
        ]
    return captured


def augment(payload: dict[str, Any], actions: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    cases = {
        str(item.get("fixture_id")): item
        for item in payload.get("case_results", [])
    }
    missing = sorted(set(cases) - set(actions))
    unexpected = sorted(set(actions) - set(cases))
    if missing or unexpected:
        raise ValueError(
            "Runtime action capture does not match artifact cases: "
            f"missing={missing}, unexpected={unexpected}"
        )
    for fixture_id, values in actions.items():
        observations = cases[fixture_id].setdefault("observations", {})
        observations["actions"] = values
    payload["stage75_action_capture"] = {
        "schema_version": ACTION_CAPTURE_SCHEMA_VERSION,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "case_count": len(actions),
        "exact_parameters_captured": True,
    }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add exact runtime action payloads to a Stage 7 evaluation artifact."
    )
    parser.add_argument("--artifact", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.artifact.read_text(encoding="utf-8"))
    augmented = augment(payload, capture_actions())
    args.artifact.write_text(
        json.dumps(augmented, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "Stage 7.5 runtime action capture: "
        f"{augmented['stage75_action_capture']['case_count']} cases"
    )


if __name__ == "__main__":
    main()
