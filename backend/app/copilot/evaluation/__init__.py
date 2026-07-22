"""Stage 7 golden and production-runtime evaluation primitives.

Both modes are provider-free and safe to run in CI.  The frozen reference
mode is a non-release-bearing corpus check; ``run_runtime_suite`` executes the
real Copilot pipeline with hermetic source adapters and is release-bearing.
"""

from app.copilot.evaluation.contracts import (
    CaseEvaluationResult,
    EvaluationCandidate,
    EvaluationSummary,
    GoldenEvaluationCase,
)
from app.copilot.evaluation.evaluator import evaluate_case
from app.copilot.evaluation.loader import load_fixtures
from app.copilot.evaluation.runner import run_suite
from app.copilot.evaluation.runtime import run_runtime_suite

__all__ = [
    "CaseEvaluationResult",
    "EvaluationCandidate",
    "EvaluationSummary",
    "GoldenEvaluationCase",
    "evaluate_case",
    "load_fixtures",
    "run_suite",
    "run_runtime_suite",
]
