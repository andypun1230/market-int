from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.copilot.evaluation.contracts import EvaluationSuite, ReleaseResult
from app.copilot.evaluation.loader import load_fixtures
from app.copilot.evaluation.runtime import run_runtime_suite, runtime_scenarios
from app.copilot.evaluation.runner import render_text_summary, run_suite, write_machine_result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Stage 7 Copilot evaluations.")
    parser.add_argument("--suite", choices=[item.value for item in EvaluationSuite], default="full")
    parser.add_argument(
        "--mode",
        choices=("runtime", "routing", "reference"),
        default="runtime",
        help=(
            "runtime executes the release-bearing production pipeline with hermetic sources; "
            "routing and reference are non-release-bearing contract checks."
        ),
    )
    parser.add_argument("--fixtures", type=Path, help="Override the frozen fixture directory.")
    parser.add_argument("--output", type=Path, help="Write the complete machine-readable JSON result.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--list-cases", action="store_true")
    parser.add_argument(
        "--reference-only",
        action="store_true",
        help="Deprecated alias for --mode reference.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    mode = "reference" if args.reference_only else args.mode
    if args.list_cases:
        if mode == "runtime":
            print("\n".join(case.scenario_id for case in runtime_scenarios() if EvaluationSuite(args.suite) in case.suites))
        else:
            cases = load_fixtures(args.fixtures)
            print("\n".join(case.fixture_id for case in cases if EvaluationSuite(args.suite) in case.suites))
        return 0
    if mode == "runtime":
        summary = run_runtime_suite(args.suite)
    else:
        summary = run_suite(
            args.suite,
            fixture_root=args.fixtures,
            use_runtime_routing=mode == "routing",
        )
    if args.output:
        write_machine_result(summary, args.output)
    if args.format == "json":
        print(json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True))
    else:
        print(render_text_summary(summary))
    return 1 if summary.result == ReleaseResult.FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
