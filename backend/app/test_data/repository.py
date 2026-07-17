from __future__ import annotations

import json
import os
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[2]
TEST_DATA_DIR = BACKEND_ROOT / ".test-data"
STATUS_PATH = TEST_DATA_DIR / "status.json"
SCHEMA_VERSION = 1
DEFAULT_SCENARIO = os.getenv("TEST_DATA_DEFAULT_SCENARIO", "balanced_market")
DEFAULT_SEED = os.getenv("TEST_DATA_DEFAULT_SEED", "test-market-001")

_lock = Lock()


@dataclass(frozen=True)
class TestDataState:
    mode: str
    scenario: str
    seed: str
    generated_at: str
    source: str
    data_status: str
    is_mock: bool
    schema_version: int


def get_test_data_state() -> TestDataState:
    """Return the active generated test-data state, creating it if missing."""
    with _lock:
        state = read_state()
        if state is None:
            state = build_state(DEFAULT_SCENARIO, DEFAULT_SEED)
            write_state(state)
        return state


def regenerate_test_data(scenario: str | None = None, seed: str | None = None) -> TestDataState:
    """Persist a new active test snapshot identity.

    Market services keep their existing interfaces. The active seed is consumed
    by the generated-test provider, while cache invalidation makes existing
    endpoints rebuild from the new deterministic snapshot.
    """
    normalized_scenario = normalize_scenario(scenario)
    normalized_seed = normalize_seed(seed)
    with _lock:
        state = build_state(normalized_scenario, normalized_seed)
        write_state(state)
    return state


def get_test_data_status() -> dict[str, Any]:
    state = get_test_data_state()
    return {
        **asdict(state),
        "label": "Generated Test Data",
        "last_regenerated": state.generated_at,
        "scenarios": get_test_data_scenarios(),
    }


def get_test_data_scenarios() -> list[dict[str, str]]:
    return [
        {
            "id": "balanced_market",
            "label": "Balanced Market",
            "description": "Mixed leadership with constructive but selective breadth.",
        },
        {
            "id": "risk_on",
            "label": "Risk-On",
            "description": "Stronger momentum, leadership, and broad participation.",
        },
        {
            "id": "risk_off",
            "label": "Risk-Off",
            "description": "Weakening trend, lower breadth, and defensive behavior.",
        },
        {
            "id": "rotation",
            "label": "Rotation",
            "description": "Uneven performance with clear sector and theme rotation.",
        },
    ]


def build_state(scenario: str, seed: str) -> TestDataState:
    return TestDataState(
        mode="TEST_DATA",
        scenario=scenario,
        seed=seed,
        generated_at=datetime.now(timezone.utc).isoformat(),
        source="generated_test_data",
        data_status="test",
        is_mock=True,
        schema_version=SCHEMA_VERSION,
    )


def normalize_scenario(value: str | None) -> str:
    allowed = {item["id"] for item in get_test_data_scenarios()}
    normalized = (value or DEFAULT_SCENARIO).strip().lower().replace(" ", "_")
    return normalized if normalized in allowed else DEFAULT_SCENARIO


def normalize_seed(value: str | None) -> str:
    if value and value.strip():
        return value.strip()
    return f"test-{random.randint(100000, 999999)}"


def read_state() -> TestDataState | None:
    try:
        if not STATUS_PATH.exists():
            return None
        payload = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        return TestDataState(
            mode=str(payload.get("mode") or "TEST_DATA"),
            scenario=normalize_scenario(payload.get("scenario")),
            seed=str(payload.get("seed") or DEFAULT_SEED),
            generated_at=str(payload.get("generated_at") or datetime.now(timezone.utc).isoformat()),
            source="generated_test_data",
            data_status="test",
            is_mock=True,
            schema_version=int(payload.get("schema_version") or SCHEMA_VERSION),
        )
    except Exception:
        return None


def write_state(state: TestDataState) -> None:
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(asdict(state), indent=2, sort_keys=True), encoding="utf-8")
