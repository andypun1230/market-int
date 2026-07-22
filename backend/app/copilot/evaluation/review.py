from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from pydantic import Field, model_validator

from app.copilot.evaluation.contracts import (
    CaseEvaluationResult,
    EvaluationCandidate,
    EvaluationModel,
    EvaluationSummary,
    GoldenEvaluationCase,
    IssueSeverity,
)
from app.copilot.evaluation.loader import default_fixture_root, load_fixtures


HUMAN_REVIEW_SCHEMA_VERSION = "stage7-human-review-v1"
_UNSET = object()


class ReviewClassification(str, Enum):
    CORRECT = "correct"
    PARTIALLY_CORRECT = "partially_correct"
    INCORRECT = "incorrect"
    TOO_GENERIC = "too_generic"
    TOO_CONFIDENT = "too_confident"
    MISSING_CONTRADICTION = "missing_contradiction"
    WRONG_EVIDENCE = "wrong_evidence"
    WRONG_ROUTING = "wrong_routing"
    WRONG_LINK = "wrong_link"


class ReviewUsefulness(str, Enum):
    USEFUL = "useful"
    NOT_USEFUL = "not_useful"
    UNREVIEWED = "unreviewed"


class ReviewAvailability(str, Enum):
    AVAILABLE = "available"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class ReviewField(EvaluationModel):
    availability: ReviewAvailability
    value: Any = None
    reason: str | None = None

    @model_validator(mode="after")
    def availability_matches_value(self) -> "ReviewField":
        if self.availability == ReviewAvailability.UNAVAILABLE:
            if self.value is not None:
                raise ValueError("unavailable review fields cannot contain a value")
            if not self.reason:
                raise ValueError("unavailable review fields require a reason")
        elif self.value is None:
            raise ValueError("available and partial review fields require a value")
        elif self.availability == ReviewAvailability.PARTIAL and not self.reason:
            raise ValueError("partial review fields require a reason")
        elif self.availability == ReviewAvailability.AVAILABLE and self.reason is not None:
            raise ValueError("available review fields cannot contain an unavailable reason")
        return self

    @classmethod
    def available(cls, value: Any) -> "ReviewField":
        return cls(availability=ReviewAvailability.AVAILABLE, value=value)

    @classmethod
    def partial(cls, value: Any, reason: str) -> "ReviewField":
        return cls(availability=ReviewAvailability.PARTIAL, value=value, reason=reason)

    @classmethod
    def unavailable(cls, reason: str) -> "ReviewField":
        return cls(availability=ReviewAvailability.UNAVAILABLE, reason=reason)


class ReviewComparison(EvaluationModel):
    expected: Any
    observed: ReviewField


class ReviewCaseMetadata(EvaluationModel):
    description: str
    category: str
    suites: list[str]
    tags: list[str]
    as_of: str
    rationale: str


class ReviewerAssessment(EvaluationModel):
    classification: ReviewClassification | None = None
    usefulness: ReviewUsefulness = ReviewUsefulness.UNREVIEWED
    notes: str | None = None
    reviewer: str | None = None
    reviewed_at: str | None = None


class HumanReviewCase(EvaluationModel):
    fixture_id: str
    case: ReviewCaseMetadata
    question: str
    routing: ReviewComparison
    plan: ReviewComparison
    agents: ReviewComparison
    raw_agent_outputs: ReviewField
    evidence: ReviewComparison
    contradictions: ReviewComparison
    final_answer: ReviewComparison
    structured_output: ReviewField
    deep_links: ReviewComparison
    freshness: ReviewComparison
    latency: ReviewComparison
    model_usage: ReviewComparison
    validator_failures: ReviewComparison
    validator_warnings: ReviewField
    evaluation: dict[str, Any]
    review: ReviewerAssessment = Field(default_factory=ReviewerAssessment)


class HumanReviewSource(EvaluationModel):
    cases: str
    evaluation_result: str
    evaluation_schema_version: str
    evaluator_version: str
    evaluation_mode: str
    evaluation_suite: str
    evaluation_generated_at: str
    evaluation_release_result: str


class HumanReviewDocument(EvaluationModel):
    schema_version: str = HUMAN_REVIEW_SCHEMA_VERSION
    generated_at: str
    source: HumanReviewSource
    case_count: int = Field(ge=0)
    cases: list[HumanReviewCase]

    @model_validator(mode="after")
    def case_count_matches_cases(self) -> "HumanReviewDocument":
        if self.case_count != len(self.cases):
            raise ValueError("case_count must equal the number of human-review cases")
        fixture_ids = [item.fixture_id for item in self.cases]
        if len(fixture_ids) != len(set(fixture_ids)):
            raise ValueError("human-review fixture IDs must be unique")
        return self


def load_review_cases(path: str | Path | None = None) -> list[GoldenEvaluationCase]:
    """Load either the repository fixture directory or one JSON/JSONL case file."""

    if path is None:
        return load_fixtures()
    source = Path(path)
    if source.is_dir():
        return load_fixtures(source)
    if not source.is_file():
        raise ValueError(f"Stage 7 cases path does not exist: {source}")
    if source.suffix == ".jsonl":
        rows = [
            json.loads(line)
            for line in source.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    elif source.suffix == ".json":
        payload = json.loads(source.read_text(encoding="utf-8"))
        rows = payload if isinstance(payload, list) else payload.get("cases", [])
    else:
        raise ValueError("Stage 7 cases must be a .json or .jsonl file")
    cases: list[GoldenEvaluationCase] = []
    for index, row in enumerate(rows, start=1):
        try:
            cases.append(GoldenEvaluationCase.model_validate(row))
        except Exception as exc:  # pragma: no cover - exact Pydantic text is version-specific
            raise ValueError(f"Invalid Stage 7 fixture {source}:{index}: {exc}") from exc
    if not cases:
        raise ValueError(f"No Stage 7 evaluation fixtures found in {source}")
    fixture_ids = [case.fixture_id for case in cases]
    if len(fixture_ids) != len(set(fixture_ids)):
        duplicates = sorted({item for item in fixture_ids if fixture_ids.count(item) > 1})
        raise ValueError(f"Duplicate Stage 7 fixture IDs: {duplicates}")
    return cases


def load_evaluation_result(path: str | Path) -> EvaluationSummary:
    source = Path(path)
    try:
        return EvaluationSummary.model_validate_json(source.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - exact Pydantic text is version-specific
        raise ValueError(f"Invalid Stage 7 evaluation result {source}: {exc}") from exc


def load_review_document(path: str | Path) -> HumanReviewDocument:
    source = Path(path)
    try:
        return HumanReviewDocument.model_validate_json(source.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - exact Pydantic text is version-specific
        raise ValueError(f"Invalid Stage 7 human-review document {source}: {exc}") from exc


def build_review_document(
    cases: Iterable[GoldenEvaluationCase],
    summary: EvaluationSummary,
    *,
    cases_source: str,
    evaluation_source: str,
    prior_document: HumanReviewDocument | None = None,
) -> HumanReviewDocument:
    """Join fixture contracts and evaluated candidates into a local review artifact."""

    case_by_id = _unique_by_fixture_id(cases, source="case fixture")
    result_by_id = _unique_by_fixture_id(summary.case_results, source="evaluation result")
    if summary.fixture_count != len(summary.case_results):
        raise ValueError(
            "Evaluation fixture_count does not match the number of case_results: "
            f"{summary.fixture_count} != {len(summary.case_results)}"
        )
    unknown = sorted(set(result_by_id) - set(case_by_id))
    if unknown:
        raise ValueError(f"Evaluation results reference unknown fixture IDs: {unknown}")
    prior_reviews = {
        item.fixture_id: item.review.model_copy(deep=True)
        for item in (prior_document.cases if prior_document is not None else [])
    }
    review_cases = [
        _build_review_case(
            case_by_id[result.fixture_id],
            result,
            review=prior_reviews.get(result.fixture_id),
        )
        for result in summary.case_results
    ]
    return HumanReviewDocument(
        generated_at=_utc_now(),
        source=HumanReviewSource(
            cases=cases_source,
            evaluation_result=evaluation_source,
            evaluation_schema_version=summary.schema_version,
            evaluator_version=summary.evaluator_version,
            evaluation_mode=summary.evaluation_mode,
            evaluation_suite=summary.suite.value,
            evaluation_generated_at=summary.generated_at,
            evaluation_release_result=summary.result.value,
        ),
        case_count=len(review_cases),
        cases=review_cases,
    )


def update_reviewer_assessment(
    document: HumanReviewDocument,
    fixture_id: str,
    *,
    classification: ReviewClassification | str | None | object = _UNSET,
    usefulness: ReviewUsefulness | str | object = _UNSET,
    notes: str | None | object = _UNSET,
    reviewer: str | None | object = _UNSET,
    reviewed_at: str | None = None,
) -> HumanReviewDocument:
    """Return a copy with one persisted reviewer decision updated.

    Omitted values remain unchanged. Passing ``None`` clears an optional
    classification, note, or reviewer value.
    """

    if all(value is _UNSET for value in (classification, usefulness, notes, reviewer)):
        raise ValueError("At least one reviewer field must be updated")
    matching = [index for index, item in enumerate(document.cases) if item.fixture_id == fixture_id]
    if not matching:
        raise ValueError(f"Unknown human-review fixture ID: {fixture_id}")
    index = matching[0]
    current = document.cases[index].review
    values = current.model_dump()
    if classification is not _UNSET:
        values["classification"] = (
            None if classification is None else ReviewClassification(classification)
        )
    if usefulness is not _UNSET:
        if usefulness is None:
            raise ValueError("usefulness cannot be null")
        values["usefulness"] = ReviewUsefulness(usefulness)
    if notes is not _UNSET:
        values["notes"] = _optional_text(notes)
    if reviewer is not _UNSET:
        values["reviewer"] = _optional_text(reviewer)
    values["reviewed_at"] = reviewed_at or _utc_now()
    updated_assessment = ReviewerAssessment.model_validate(values)
    updated_cases = [item.model_copy(deep=True) for item in document.cases]
    updated_cases[index] = updated_cases[index].model_copy(
        update={"review": updated_assessment},
        deep=True,
    )
    return document.model_copy(
        update={"generated_at": _utc_now(), "cases": updated_cases},
        deep=True,
    )


def write_review_document(document: HumanReviewDocument, output: str | Path) -> Path:
    """Atomically persist a local review document."""

    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(document.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and annotate a developer-only Stage 7 human-review JSON artifact."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build", help="Join cases.jsonl with a machine evaluation result.")
    build.add_argument(
        "--cases",
        type=Path,
        default=default_fixture_root() / "cases.jsonl",
        help="Stage 7 cases.jsonl (or a fixture directory).",
    )
    build.add_argument("--results", type=Path, required=True, help="Stage 7 machine evaluation JSON.")
    build.add_argument("--output", type=Path, required=True, help="Local human-review JSON to write.")
    build.add_argument(
        "--no-preserve-reviews",
        action="store_true",
        help="Do not carry matching reviewer decisions forward when --output already exists.",
    )

    set_review = commands.add_parser("set-review", help="Persist a reviewer decision for one case.")
    set_review.add_argument("--review-file", type=Path, required=True)
    set_review.add_argument("--case-id", required=True)
    set_review.add_argument("--classification", choices=[item.value for item in ReviewClassification])
    set_review.add_argument("--usefulness", choices=[item.value for item in ReviewUsefulness])
    set_review.add_argument("--notes")
    set_review.add_argument("--reviewer")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            prior = None
            if args.output.exists() and not args.no_preserve_reviews:
                prior = load_review_document(args.output)
            cases = load_review_cases(args.cases)
            summary = load_evaluation_result(args.results)
            document = build_review_document(
                cases,
                summary,
                cases_source=str(args.cases.resolve()),
                evaluation_source=str(args.results.resolve()),
                prior_document=prior,
            )
            target = write_review_document(document, args.output)
            print(f"Wrote {document.case_count} Stage 7 review cases to {target}")
            return 0

        updates = {}
        for name in ("classification", "usefulness", "notes", "reviewer"):
            value = getattr(args, name)
            if value is not None:
                updates[name] = value
        document = load_review_document(args.review_file)
        document = update_reviewer_assessment(
            document,
            args.case_id,
            **updates,
        )
        write_review_document(document, args.review_file)
        print(f"Updated Stage 7 review for {args.case_id} in {args.review_file}")
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _build_review_case(
    case: GoldenEvaluationCase,
    result: CaseEvaluationResult,
    *,
    review: ReviewerAssessment | None,
) -> HumanReviewCase:
    candidate = result.observed_candidate
    candidate_missing = (
        "The evaluation result predates observed-candidate capture or did not persist the "
        "candidate; this value cannot be reconstructed honestly from score metrics."
    )
    evidence_by_id = {
        item.evidence_id: item.model_dump(mode="json")
        for item in case.frozen_input.evidence
    }
    if candidate is None:
        routing = ReviewField.unavailable(candidate_missing)
        plan = ReviewField.unavailable(candidate_missing)
        agents = ReviewField.unavailable(candidate_missing)
        evidence = ReviewField.unavailable(candidate_missing)
        contradictions = ReviewField.unavailable(candidate_missing)
        structured_output = ReviewField.unavailable(candidate_missing)
        deep_links = ReviewField.unavailable(candidate_missing)
        freshness = ReviewField.unavailable(candidate_missing)
    else:
        candidate_payload = candidate.model_dump(mode="json")
        routing = ReviewField.available({"resolved_intent": candidate_payload["intent"]})
        plan = ReviewField.partial(
            {
                "agents_called_in_order": candidate_payload["selected_agents"],
                "deep_link_requirements": candidate_payload["deep_links"],
            },
            "The evaluation candidate captures routing outputs but not full planner step IDs, "
            "dependencies, or evidence requirements.",
        )
        agents = ReviewField.available(candidate_payload["selected_agents"])
        evidence = _observed_evidence(candidate, evidence_by_id)
        contradictions = ReviewField.available(candidate_payload["contradictions"])
        structured_output = ReviewField.available(candidate_payload)
        deep_links = ReviewField.available(candidate_payload["deep_links"])
        freshness = ReviewField.available({
            "state": candidate_payload["freshness"],
            "confidence": candidate_payload["confidence"],
            "missing_evidence": candidate_payload["missing_evidence"],
            "limitations": candidate_payload["limitations"],
        })

    latency_value = result.metrics.get("latency_ms")
    latency = (
        ReviewField.available({"total_ms": latency_value})
        if latency_value is not None
        else ReviewField.unavailable("The evaluation result did not capture total latency.")
    )
    model_calls = result.metrics.get("model_calls")
    model_usage = (
        ReviewField.partial(
            {
                "model_calls": model_calls,
                "token_usage": None,
                "estimated_cost": None,
            },
            "Model-call count is available; token usage and estimated cost are not captured by "
            "the offline evaluation contract.",
        )
        if model_calls is not None
        else ReviewField.unavailable(
            "The evaluation result contains no model-call, token-usage, or estimated-cost data."
        )
    )
    failures = [
        item.model_dump(mode="json")
        for item in result.issues
        if item.severity == IssueSeverity.ERROR
    ]
    warnings = [
        item.model_dump(mode="json")
        for item in result.issues
        if item.severity == IssueSeverity.WARNING
    ]
    return HumanReviewCase(
        fixture_id=case.fixture_id,
        case=ReviewCaseMetadata(
            description=case.description,
            category=case.category.value,
            suites=[item.value for item in case.suites],
            tags=list(case.tags),
            as_of=case.frozen_input.as_of,
            rationale=case.rationale,
        ),
        question=case.frozen_input.question,
        routing=ReviewComparison(
            expected={
                "primary_intent": case.expected_intent.value,
                "acceptable_secondary_intents": [
                    item.value for item in case.acceptable_secondary_intents
                ],
            },
            observed=routing,
        ),
        plan=ReviewComparison(
            expected={
                "required_agents": [item.value for item in case.expected_agent_selection.required],
                "optional_agents": [item.value for item in case.expected_agent_selection.optional],
                "forbidden_agents": [item.value for item in case.expected_agent_selection.forbidden],
                "maximum_agent_count": case.expected_agent_selection.maximum_agent_count,
            },
            observed=plan,
        ),
        agents=ReviewComparison(
            expected={
                "required": [item.value for item in case.expected_agent_selection.required],
                "optional": [item.value for item in case.expected_agent_selection.optional],
                "forbidden": [item.value for item in case.expected_agent_selection.forbidden],
                "maximum_count": case.expected_agent_selection.maximum_agent_count,
            },
            observed=agents,
        ),
        raw_agent_outputs=ReviewField.unavailable(
            "The offline evaluation candidate does not capture per-agent raw outputs."
        ),
        evidence=ReviewComparison(
            expected={
                "required_ids": list(case.required_evidence),
                "forbidden_ids": list(case.forbidden_evidence),
                "frozen_registry": list(evidence_by_id.values()),
            },
            observed=evidence,
        ),
        contradictions=ReviewComparison(
            expected={"handling": case.expected_contradiction_handling.value},
            observed=contradictions,
        ),
        final_answer=ReviewComparison(
            expected={
                "allowed_conclusion_classes": list(case.expected_structured_conclusion),
                "forbidden_claims": list(case.forbidden_claims),
            },
            observed=ReviewField.unavailable(
                "The evaluation contract captures a structured conclusion and claims, not a "
                "synthesized final-answer string. See structured_output for what is available."
            ),
        ),
        structured_output=structured_output,
        deep_links=ReviewComparison(
            expected=[item.value for item in case.expected_deep_links],
            observed=deep_links,
        ),
        freshness=ReviewComparison(
            expected={
                "state": case.expected_freshness_state.value,
                "confidence_minimum": case.allowed_confidence_range.minimum,
                "confidence_maximum": case.allowed_confidence_range.maximum,
            },
            observed=freshness,
        ),
        latency=ReviewComparison(
            expected={"maximum_ms": case.latency_budget_ms},
            observed=latency,
        ),
        model_usage=ReviewComparison(
            expected={"maximum_model_calls": case.model_call_budget},
            observed=model_usage,
        ),
        validator_failures=ReviewComparison(expected=[], observed=ReviewField.available(failures)),
        validator_warnings=ReviewField.available(warnings),
        evaluation={
            "passed": result.passed,
            "weighted_quality_score": result.weighted_quality_score,
            "component_scores": dict(result.component_scores),
            "metrics": dict(result.metrics),
        },
        review=review or ReviewerAssessment(),
    )


def _observed_evidence(
    candidate: EvaluationCandidate,
    evidence_by_id: dict[str, dict[str, Any]],
) -> ReviewField:
    candidate_payload = candidate.model_dump(mode="json")
    cited_ids = candidate_payload["cited_evidence"]
    unknown_ids = [item for item in cited_ids if item not in evidence_by_id]
    value = {
        "cited_ids": cited_ids,
        "resolved": [evidence_by_id[item] for item in cited_ids if item in evidence_by_id],
        "unknown_ids": unknown_ids,
        "claims": candidate_payload["claims"],
    }
    if unknown_ids:
        return ReviewField.partial(
            value,
            "Some cited evidence IDs are absent from the frozen case registry; validator failures "
            "contain the authoritative evaluation outcome.",
        )
    return ReviewField.available(value)


def _unique_by_fixture_id(items: Iterable[Any], *, source: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    duplicates: list[str] = []
    for item in items:
        fixture_id = item.fixture_id
        if fixture_id in result:
            duplicates.append(fixture_id)
        result[fixture_id] = item
    if duplicates:
        raise ValueError(f"Duplicate fixture IDs in {source}: {sorted(set(duplicates))}")
    return result


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
