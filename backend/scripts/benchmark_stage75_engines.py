from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.analysis_engines.confidence import (
    ConfidenceAdjustmentEngine,
    ConfidenceAdjustmentInput,
)
from app.analysis_engines.contradiction import (
    ContradictionAnalysisInput,
    ContradictionEngine,
    ContradictionFinding,
)
from app.analysis_engines.evidence_validation import (
    BreakoutEvidence,
    BreakoutValidationInput,
    ClaimBindingInput,
    EvidenceValidationEngine,
)
from app.analysis_engines.freshness import (
    FreshnessAvailabilityEngine,
    FreshnessAvailabilityInput,
)


ITERATIONS = 5_000


def percentile(values: list[float], value: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * value)))
    return ordered[index]


def benchmark(callback: Callable[[], object], *, iterations: int) -> dict[str, float | int]:
    for _ in range(100):
        callback()
    samples: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter_ns()
        callback()
        samples.append((time.perf_counter_ns() - started) / 1_000)
    return {
        "iterations": iterations,
        "mean_us": round(statistics.fmean(samples), 6),
        "p50_us": round(percentile(samples, 0.50), 6),
        "p95_us": round(percentile(samples, 0.95), 6),
        "p99_us": round(percentile(samples, 0.99), 6),
        "max_us": round(max(samples), 6),
    }


def import_startup(command: str, *, iterations: int = 7) -> dict[str, float | int]:
    samples: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter_ns()
        subprocess.run(
            [sys.executable, "-c", command],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        samples.append((time.perf_counter_ns() - started) / 1_000_000)
    return {
        "iterations": iterations,
        "mean_ms": round(statistics.fmean(samples), 6),
        "p50_ms": round(percentile(samples, 0.50), 6),
        "p95_ms": round(percentile(samples, 0.95), 6),
        "p99_ms": round(percentile(samples, 0.99), 6),
        "max_ms": round(max(samples), 6),
    }


def build_payload(*, iterations: int) -> dict[str, object]:
    fixed_now = datetime(2026, 7, 22, 5, 39, 37, tzinfo=timezone.utc)
    freshness = FreshnessAvailabilityEngine()
    evidence = EvidenceValidationEngine()
    contradiction = ContradictionEngine()
    confidence = ConfidenceAdjustmentEngine()

    callbacks: dict[str, Callable[[], object]] = {
        "freshness_availability": lambda: freshness.evaluate(
            FreshnessAvailabilityInput(
                source_state="cached",
                provider_status="complete",
                generated_at="2026-07-22T05:00:00Z",
                observed_at="2026-07-22T04:59:00Z",
                market_date="2026-07-22",
                completeness=0.94,
                provider="benchmark",
                now=fixed_now,
            )
        ),
        "evidence_claim_binding": lambda: evidence.validate_claim_binding(
            ClaimBindingInput(
                claim="NVDA current price is 111.",
                claim_entities=frozenset({"nvda"}),
                evidence_entities=frozenset({"nvda"}),
                evidence_metric="current price",
                evidence_value=111,
                evidence_timeframe="current",
            )
        ),
        "evidence_breakout_validation": lambda: evidence.validate_breakout_confirmation(
            BreakoutValidationInput(
                claimed_entities=frozenset({"nvda"}),
                evidence=(
                    BreakoutEvidence("NVDA", frozenset({"nvda"}), "current price", 111),
                    BreakoutEvidence("NVDA", frozenset({"nvda"}), "confirmation price", 110),
                    BreakoutEvidence("NVDA", frozenset({"nvda"}), "volume confirmation", "strong"),
                ),
            )
        ),
        "contradiction_preservation": lambda: contradiction.analyze(
            ContradictionAnalysisInput(
                findings=(
                    ContradictionFinding("support", "NVDA: trend is strong."),
                    ContradictionFinding("risk", "NVDA: volume is weak.", explicitly_opposing=True),
                    ContradictionFinding("neutral", "NVDA: RSI is 52."),
                )
            )
        ),
        "confidence_adjustment": lambda: confidence.adjust(
            ConfidenceAdjustmentInput(
                intent="STOCK_ANALYSIS",
                evidence_count=5,
                freshness_state="cached",
                contradiction_count=1,
            )
        ),
    }

    tracemalloc.start()
    engine_metrics = {
        name: benchmark(callback, iterations=iterations)
        for name, callback in callbacks.items()
    }
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    baseline_import = import_startup("import app")
    engine_import = import_startup(
        "import app.analysis_engines.freshness, "
        "app.analysis_engines.evidence_validation, "
        "app.analysis_engines.contradiction, "
        "app.analysis_engines.confidence"
    )
    return {
        "schema_version": "stage75-engine-performance-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hermetic": True,
        "network_calls": 0,
        "model_calls": 0,
        "engine_metrics": engine_metrics,
        "memory": {
            "benchmark_peak_bytes": peak_bytes,
            "benchmark_peak_kib": round(peak_bytes / 1024, 3),
        },
        "import_startup": {
            "baseline": baseline_import,
            "with_analysis_engines": engine_import,
            "mean_delta_ms": round(
                float(engine_import["mean_ms"]) - float(baseline_import["mean_ms"]),
                6,
            ),
        },
        "limitations": [
            "Microbenchmarks measure deterministic engine calls in one Python process.",
            "Fresh-process import measurements include interpreter startup noise.",
            "End-to-end and per-agent latency come from the Stage 7 runtime evaluator.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark deterministic Stage 7.5 engines.")
    parser.add_argument("--iterations", type=int, default=ITERATIONS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = build_payload(iterations=max(100, args.iterations))
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
