from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from app.copilot.evaluation.contracts import EvaluationSuite, GoldenEvaluationCase


def default_fixture_root() -> Path:
    return Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "stage7"


def load_fixtures(root: str | Path | None = None) -> list[GoldenEvaluationCase]:
    """Load and strictly validate repository-native JSON/JSONL fixtures."""

    fixture_root = Path(root) if root is not None else default_fixture_root()
    paths = sorted(fixture_root.glob("*.json")) + sorted(fixture_root.glob("*.jsonl"))
    cases: list[GoldenEvaluationCase] = []
    for path in paths:
        if path.name.startswith("manifest"):
            continue
        if path.suffix == ".jsonl":
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        else:
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows = payload if isinstance(payload, list) else payload.get("cases", [])
        for index, row in enumerate(rows, start=1):
            try:
                cases.append(GoldenEvaluationCase.model_validate(row))
            except Exception as exc:  # pragma: no cover - exact Pydantic text is version-specific
                raise ValueError(f"Invalid Stage 7 fixture {path}:{index}: {exc}") from exc
    if not cases:
        raise ValueError(f"No Stage 7 evaluation fixtures found in {fixture_root}")
    ids = [case.fixture_id for case in cases]
    if len(ids) != len(set(ids)):
        duplicates = sorted({fixture_id for fixture_id in ids if ids.count(fixture_id) > 1})
        raise ValueError(f"Duplicate Stage 7 fixture IDs: {duplicates}")
    return cases


def cases_for_suite(
    cases: Iterable[GoldenEvaluationCase],
    suite: EvaluationSuite | str,
) -> list[GoldenEvaluationCase]:
    selected = EvaluationSuite(suite)
    if selected == EvaluationSuite.FULL:
        return list(cases)
    return [case for case in cases if selected in case.suites]
