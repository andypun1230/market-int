from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CANDIDATE_FIELDS = (
    "actionable",
    "cited_evidence",
    "claims",
    "conclusion_class",
    "confidence",
    "contradictions",
    "deep_links",
    "freshness",
    "intent",
    "limitations",
    "missing_evidence",
    "model_calls",
    "output_schema_version",
    "selected_agents",
)
OBSERVATION_FIELDS = (
    "actions",
    "agent_failure_categories",
    "agent_statuses",
    "evidence_count",
    "fallback_used",
    "injection_observed",
    "pipeline_calls",
    "registry_calls",
    "source_calls",
    "validation_issues",
    "validation_status",
)


def selected(value: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: value.get(field) for field in fields}


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(len(ordered) - 1, lower + 1)
    weight = position - lower
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * weight, 6)


def performance_summary(payload: dict[str, Any]) -> dict[str, Any]:
    reported = dict(payload.get("performance_metrics") or {})
    performance_latencies = [
        float(item.get("metrics", {}).get("latency_ms", 0))
        for item in payload.get("case_results", [])
        if "performance" in item.get("suites", [])
    ]
    reported["p99_latency_ms"] = percentile(performance_latencies, 0.99)
    reported["performance_case_count"] = len(performance_latencies)
    return reported


def compare(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_cases = {item["fixture_id"]: item for item in before.get("case_results", [])}
    after_cases = {item["fixture_id"]: item for item in after.get("case_results", [])}
    fixture_ids = sorted(set(before_cases) | set(after_cases))
    results: list[dict[str, Any]] = []
    for fixture_id in fixture_ids:
        old = before_cases.get(fixture_id)
        new = after_cases.get(fixture_id)
        mismatches: list[str] = []
        if old is None:
            mismatches.append("missing_before")
        elif new is None:
            mismatches.append("missing_after")
        else:
            if selected(old.get("observed_candidate", {}), CANDIDATE_FIELDS) != selected(
                new.get("observed_candidate", {}), CANDIDATE_FIELDS
            ):
                mismatches.append("observed_candidate")
            if selected(old.get("observations", {}), OBSERVATION_FIELDS) != selected(
                new.get("observations", {}), OBSERVATION_FIELDS
            ):
                mismatches.append("runtime_observations")
            if old.get("component_scores") != new.get("component_scores"):
                mismatches.append("component_scores")
            if old.get("passed") != new.get("passed"):
                mismatches.append("pass_status")
        results.append(
            {
                "fixture_id": fixture_id,
                "equivalent": not mismatches,
                "mismatches": mismatches,
            }
        )

    failures = [item for item in results if not item["equivalent"]]
    before_performance = performance_summary(before)
    after_performance = performance_summary(after)
    before_p95 = float(before_performance.get("p95_latency_ms") or 0)
    after_p95 = float(after_performance.get("p95_latency_ms") or 0)
    return {
        "schema_version": "stage75-semantic-equivalence-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "result": "PASS" if not failures else "FAIL",
        "before": str(before.get("generated_at") or "unknown"),
        "after": str(after.get("generated_at") or "unknown"),
        "case_count": len(results),
        "equivalent_count": len(results) - len(failures),
        "failed_count": len(failures),
        "compared_fields": {
            "observed_candidate": list(CANDIDATE_FIELDS),
            "runtime_observations": list(OBSERVATION_FIELDS),
            "case": ["component_scores", "passed"],
        },
        "ignored_fields": [
            "generated timestamps",
            "case latency",
            "agent latency",
            "internal module paths",
        ],
        "performance": {
            "before": before_performance,
            "after": after_performance,
            "p95_delta_percent": round(
                ((after_p95 - before_p95) / before_p95) * 100,
                6,
            ) if before_p95 else None,
        },
        "cases": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Stage 7 runtime semantics across Stage 7.5.")
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    before = json.loads(args.before.read_text(encoding="utf-8"))
    after = json.loads(args.after.read_text(encoding="utf-8"))
    payload = compare(before, after)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"Stage 7.5 semantic equivalence: {payload['result']} "
        f"({payload['equivalent_count']}/{payload['case_count']} cases equivalent)"
    )
    if payload["result"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
