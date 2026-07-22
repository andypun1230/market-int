"""Generate the permanent Stage 8 golden JSONL corpus.

The corpus describes distinct, evidence-oriented behaviors.  It is never an
application news source and every row is explicitly hermetic.  Focused engine
tests use richer typed fixtures; this corpus is the cross-capability release
matrix and preserves required safety, failure, routing, and grounding cases.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


OUTPUT = Path(__file__).with_name("cases.jsonl")
AS_OF = "2026-07-21T20:00:00+00:00"


@dataclass(frozen=True)
class Seed:
    code: str
    description: str
    categories: tuple[str, ...]
    expected_status: str = "complete"
    intraday: bool = False
    provider_mode: str = "hermetic"
    maximum_confidence: float = 0.9
    blocked_claims: tuple[str, ...] = ()
    disclosures: tuple[str, ...] = ()
    expected: tuple[tuple[str, Any], ...] = ()


def seed(
    code: str,
    description: str,
    *categories: str,
    **kwargs: Any,
) -> Seed:
    return Seed(code, description, tuple(categories), **kwargs)


REQUIRED: tuple[Seed, ...] = (
    seed("primary-release-syndicated-copies", "One primary company release anchors several syndicated copies.", "provider_normalization", "source_credibility", "clustering", expected=(("canonical_clusters", 1), ("primary_anchor_required", True))),
    seed("rumour-later-confirmed", "An unverified rumour is later confirmed by an issuer release.", "clustering", "source_credibility", "corrections", maximum_confidence=0.82, disclosures=("status transition",)),
    seed("rumour-later-disproved", "An issuer denial disproves an earlier rumour.", "clustering", "contradiction", "corrections", maximum_confidence=0.68, blocked_claims=("rumour confirmed",)),
    seed("corrected-macro-release", "A primary macro release is revised and the prior value is superseded.", "provider_normalization", "corrections", "classification", disclosures=("correction lineage",)),
    seed("positive-headline-negative-stock", "A positive company announcement is followed by a negative stock reaction.", "materiality", "market_reaction", "contradiction", expected=(("reaction", "rejects_positive"),)),
    seed("negative-headline-positive-stock", "A negative event is followed by a positive stock reaction.", "materiality", "market_reaction", "contradiction", expected=(("reaction", "rejects_negative"),)),
    seed("no-measurable-reaction", "A sourced event has no material move over the supported window.", "market_reaction", "materiality", expected=(("reaction", "no_material_reaction"),)),
    seed("sector-regulation", "A primary regulator notice maps directly to a sector and named securities.", "classification", "entity_mapping", "materiality", expected=(("event_type", "regulation"),)),
    seed("multi-security-event", "One confirmed event explicitly names several registered securities.", "entity_mapping", "clustering", "materiality"),
    seed("ambiguous-common-word-ticker", "A common word that is also a ticker is not resolved without controlled context.", "entity_mapping", "safety", expected_status="partial", maximum_confidence=0.45, blocked_claims=("ticker mapping confirmed",)),
    seed("after-market-close-event", "A timezone-aware event falls after the regular close.", "provider_normalization", "session_segmentation", expected=(("session_phase", "after_hours"),)),
    seed("premarket-event", "A timezone-aware event falls before the regular open.", "provider_normalization", "session_segmentation", expected=(("session_phase", "premarket"),)),
    seed("weekend-news", "A Saturday event maps to the next eligible market date without inventing a session reaction.", "session_segmentation", "market_reaction", expected_status="partial", blocked_claims=("same-session reaction",)),
    seed("stale-event", "An old event remains stale and cannot be presented as current.", "freshness", "safety", expected_status="stale", maximum_confidence=0.42, blocked_claims=("latest news",)),
    seed("missing-event-timestamp", "An event without a valid publication time fails normalization.", "provider_normalization", "failure", expected_status="unavailable", maximum_confidence=0.1, blocked_claims=("confirmed event time",)),
    seed("provider-unavailable", "The selected production provider is explicitly unavailable with no fixture fallback.", "provider_normalization", "failure", expected_status="unavailable", provider_mode="unavailable", maximum_confidence=0.0, disclosures=("provider unavailable",)),
    seed("intraday-reversal-after-event", "Five-minute bars show a transparent reversal after an event without proving causation.", "intraday_narrative", "market_reaction", "causality", intraday=True, blocked_claims=("event caused reversal",)),
    seed("quiet-session-no-material-news", "A complete quiet session has no material event rather than a fabricated catalyst.", "intraday_narrative", "materiality", intraday=True, expected=(("material_event_count", 0),)),
    seed("daily-only-blocks-intraday", "Daily OHLCV supports a candle summary but blocks intraday narration.", "session_segmentation", "intraday_narrative", "safety", expected_status="daily_only", blocked_claims=("morning recovery", "final-hour selling", "VWAP reclaim")),
    seed("partial-active-session", "An active partial session discloses incompleteness and does not narrate the close.", "intraday_narrative", "freshness", intraday=True, expected_status="partial", blocked_claims=("closing behavior confirmed",)),
    seed("shortened-session", "An injected early close changes final-hour and close boundaries.", "session_segmentation", "intraday_narrative", intraday=True, disclosures=("shortened session",)),
    seed("duplicate-different-headlines", "Different headline wording for one structured event deduplicates to one cluster.", "clustering", "classification", expected=(("canonical_clusters", 1),)),
    seed("article-correction", "A corrected publisher item retains supersession lineage and does not count twice.", "clustering", "corrections", expected=(("canonical_clusters", 1),)),
    seed("contradictory-sources", "Two sources disagree and the contradiction remains explicit.", "source_credibility", "contradiction", maximum_confidence=0.55, disclosures=("source disagreement",)),
    seed("macro-without-consensus", "A macro release has an actual value but no consensus field.", "classification", "safety", expected_status="partial", blocked_claims=("beat expectations", "missed consensus")),
    seed("bond-etf-proxy-no-yield", "A bond ETF move remains a proxy and is not stated as a direct yield change.", "market_reaction", "safety", blocked_claims=("Treasury yield moved",)),
    seed("price-without-volume-history", "Price reaction exists while volume confirmation is unavailable.", "market_reaction", "freshness", expected_status="partial", blocked_claims=("volume confirmed",)),
    seed("watchlist-overlap-no-holdings", "Saved-symbol overlap affects user relevance but never portfolio impact.", "entity_mapping", "materiality", "safety", blocked_claims=("your position", "portfolio impact")),
    seed("theme-partial-constituent-impact", "A theme event maps only to supported affected constituents.", "entity_mapping", "materiality", expected=(("all_members_affected", False),)),
    seed("catalyst-after-price-move", "Price moved before the event timestamp, so causal attribution is rejected.", "market_reaction", "causality", "safety", maximum_confidence=0.48, blocked_claims=("event caused the move",)),
)


GROUPS: dict[str, tuple[tuple[str, str, dict[str, Any]], ...]] = {
    "provider_normalization": (
        ("utc-zulu", "Normalize a Zulu publication timestamp.", {}),
        ("offset-to-utc", "Normalize a valid numeric timezone offset.", {}),
        ("unicode-headline", "Normalize Unicode without changing factual content.", {}),
        ("whitespace-collapse", "Collapse presentation whitespace deterministically.", {}),
        ("canonical-url", "Retain an allowed HTTPS canonical URL.", {}),
        ("unsafe-url", "Reject a javascript URL while retaining safe metadata.", {"expected_status": "partial"}),
        ("oversized-summary", "Bound an oversized source summary without storing a body.", {"expected_status": "partial"}),
        ("language-tag", "Retain a valid BCP-47-style language tag.", {}),
        ("unknown-provider-field", "Provider-specific fields do not enter the consumer contract.", {}),
        ("invalid-identifier", "Reject a malformed provider identifier.", {"expected_status": "unavailable"}),
    ),
    "source_credibility": (
        ("sec-primary", "Configured SEC domain is primary for filing events.", {}),
        ("fed-primary", "Configured Federal Reserve domain is primary for policy events.", {}),
        ("statistics-primary", "Configured government statistics domain is primary for releases.", {}),
        ("issuer-ir-primary", "Configured issuer IR source is primary only for its issuer categories.", {}),
        ("exchange-primary", "Configured exchange notice source is primary for exchange notices.", {}),
        ("court-primary", "Configured court notice is primary for the controlled legal category.", {}),
        ("wire-secondary", "Configured professional wire is high-confidence secondary.", {}),
        ("authored-analysis", "Identifiable authored analysis is supporting secondary.", {"maximum_confidence": 0.75}),
        ("anonymous-claim", "An anonymous claim is unverified.", {"maximum_confidence": 0.35}),
        ("spoofed-official", "A lookalike official domain is not upgraded.", {"maximum_confidence": 0.2, "expected_status": "partial"}),
    ),
    "classification": (
        ("monetary-policy", "Structured central-bank metadata classifies monetary policy.", {}),
        ("inflation", "Structured statistics metadata classifies inflation.", {}),
        ("employment", "Structured statistics metadata classifies employment.", {}),
        ("earnings", "Issuer result metadata classifies earnings.", {}),
        ("guidance", "Issuer outlook metadata classifies guidance separately from earnings.", {}),
        ("merger-acquisition", "Structured transaction metadata classifies M&A.", {}),
        ("capital-raise", "Offering metadata classifies a capital raise.", {}),
        ("cybersecurity", "Incident metadata classifies a cybersecurity incident.", {}),
        ("management-change", "Officer-change metadata classifies management change.", {}),
        ("deterministic-other", "Insufficient controlled metadata falls back to other without invented subtype.", {"maximum_confidence": 0.55}),
    ),
    "clustering": (
        ("same-provider-id", "Exact provider identifiers collapse deterministically.", {}),
        ("same-structured-id", "Cross-source structured event identifiers cluster.", {}),
        ("syndicated-token-match", "Syndicated normalized headline tokens cluster with matching entity/type/time.", {}),
        ("primary-reference", "A secondary item referencing the primary URL joins its cluster.", {}),
        ("headline-update", "A headline update becomes cluster history, not a new confirmation.", {}),
        ("different-event-type", "Same entity and time but a different event type stays separate.", {}),
        ("different-time-window", "Similar text outside the clustering window stays separate.", {}),
        ("different-entity", "Similar text for different issuers stays separate.", {}),
        ("rumour-confirmation-lineage", "Later confirmation changes status while preserving rumour lineage.", {}),
        ("duplicate-count-penalty", "Duplicate coverage reduces no uncertainty and adds no confirmation.", {}),
    ),
    "entity_mapping": (
        ("direct-symbol", "An explicitly named registered symbol maps directly.", {}),
        ("company-name", "A controlled company alias resolves to its registry symbol.", {}),
        ("sector-membership", "A direct security maps to its versioned sector membership.", {}),
        ("theme-membership", "A direct security maps only to reviewed theme memberships.", {}),
        ("benchmark-relationship", "A registered ETF maps to its benchmark relationship.", {}),
        ("validated-peer", "A peer relationship is emitted only from a controlled map.", {}),
        ("watchlist-overlap", "Explicit saved symbols produce watchlist-overlap mappings.", {}),
        ("unsupported-supplier", "An unregistered supplier relationship is not inferred.", {"expected_status": "partial"}),
        ("versioned-mapping", "Every mapping retains version, source, evidence, and freshness.", {}),
        ("invalid-ticker", "A malformed ticker string is quarantined.", {"expected_status": "partial"}),
    ),
    "materiality": (
        ("primary-direct", "Primary and directly named evidence increases entity materiality transparently.", {}),
        ("market-scope", "A broad confirmed policy event increases market materiality.", {}),
        ("reaction-contribution", "A supported observed reaction contributes without implying prediction.", {}),
        ("volume-contribution", "Supported volume confirmation has a separate contribution.", {}),
        ("breadth-contribution", "Supported breadth confirmation has a separate contribution.", {}),
        ("freshness-decay", "Staleness reduces materiality transparently.", {"expected_status": "stale"}),
        ("uncertainty-penalty", "Developing status applies an uncertainty penalty.", {"maximum_confidence": 0.65}),
        ("duplicate-adjustment", "Duplicate sources do not inflate the score.", {}),
        ("user-relevance-separate", "User relevance is separate from global materiality.", {}),
        ("score-bounds", "All contributions produce a bounded 0-100 score.", {}),
    ),
    "market_reaction": (
        ("five-minute-supported", "A five-minute window is assessed only with covering bars.", {"intraday": True}),
        ("fifteen-minute-supported", "A fifteen-minute window is assessed only with covering bars.", {"intraday": True}),
        ("session-to-date-partial", "Session-to-date output is explicitly partial during an active session.", {"intraday": True, "expected_status": "partial"}),
        ("close-to-close", "Completed daily bars support close-to-close reaction.", {}),
        ("next-session", "Two completed daily observations support a next-session window.", {}),
        ("multi-day", "A bounded daily series supports an explicit multi-day window.", {}),
        ("benchmark-excess", "Excess return uses a date-aligned benchmark observation.", {}),
        ("sector-relative", "Sector-relative return uses a date-aligned sector proxy.", {}),
        ("missing-price", "A reaction stays insufficient when price evidence is missing.", {"expected_status": "partial", "maximum_confidence": 0.35}),
        ("wrong-window", "Bars outside the requested window cannot support a reaction claim.", {"expected_status": "partial", "maximum_confidence": 0.3}),
    ),
    "session_segmentation": (
        ("premarket-boundary", "A bar before 09:30 America/New_York is premarket.", {"intraday": True}),
        ("opening-boundary", "The configured opening phase begins at the regular open.", {"intraday": True}),
        ("morning-boundary", "Morning follows the opening phase without overlap.", {"intraday": True}),
        ("midday-boundary", "Midday uses configured exchange-local boundaries.", {"intraday": True}),
        ("afternoon-boundary", "Afternoon precedes the final hour.", {"intraday": True}),
        ("final-hour-boundary", "The final hour is relative to the scheduled close.", {"intraday": True}),
        ("close-boundary", "The close segment is exchange-local and non-overlapping.", {"intraday": True}),
        ("after-hours-boundary", "Post-close bars are after-hours.", {"intraday": True}),
        ("holiday", "A configured exchange holiday produces a holiday state.", {}),
        ("weekend", "A weekend produces a weekend state without session bars.", {}),
    ),
    "intraday_narrative": (
        ("trend-up", "Transparent bar rules identify a trend-up session.", {"intraday": True}),
        ("trend-down", "Transparent bar rules identify a trend-down session.", {"intraday": True}),
        ("range-bound", "Noise-limited bars remain range-bound.", {"intraday": True}),
        ("morning-reversal", "Supporting bars and magnitude identify a morning reversal.", {"intraday": True}),
        ("afternoon-reversal", "Supporting bars and magnitude identify an afternoon reversal.", {"intraday": True}),
        ("failed-recovery", "A failed recovery retains supporting timestamps.", {"intraday": True}),
        ("failed-breakdown", "A failed breakdown retains supporting timestamps.", {"intraday": True}),
        ("close-near-high", "Close location supports close-near-high.", {"intraday": True}),
        ("vwap-reclaim", "Approximate intraday VWAP supports reclaim only with covering OHLCV.", {"intraday": True}),
        ("volume-pace-missing-history", "Volume pace remains unavailable without same-time history.", {"intraday": True, "expected_status": "partial"}),
    ),
    "routing_synthesis": (
        ("latest-market-news", "Latest market news routes to the existing Market agent and News evidence.", {}),
        ("market-move-explanation", "A material-event explanation preserves fact/reaction separation.", {}),
        ("session-narrative", "Session questions route to Session evidence beneath an existing agent.", {}),
        ("security-news", "Security news routes to the existing Stock agent.", {}),
        ("sector-news", "Sector news routes to the existing Sector agent.", {}),
        ("theme-news", "Theme news routes to the existing Theme agent.", {}),
        ("macro-event-reaction", "Macro event reaction routes to the existing Macro agent.", {}),
        ("event-detail", "Event detail retains one canonical event and evidence IDs.", {}),
        ("catalyst-comparison", "Catalyst comparison does not create a new registered agent.", {}),
        ("headline-price-contradiction", "Headline-price contradiction emits both sides.", {}),
    ),
    "failure": (
        ("provider-timeout", "A provider timeout becomes structured unavailable.", {"expected_status": "unavailable"}),
        ("provider-rate-limit", "A rate limit becomes structured unavailable with no mock fallback.", {"expected_status": "unavailable"}),
        ("malformed-article", "Malformed input is quarantined without a replacement headline.", {"expected_status": "partial"}),
        ("invalid-timestamp", "Invalid time fails closed.", {"expected_status": "unavailable"}),
        ("duplicate-event-id", "Conflicting duplicate IDs preserve a validation error.", {"expected_status": "partial"}),
        ("registry-miss", "A source registry miss remains unverified.", {"expected_status": "partial", "maximum_confidence": 0.35}),
        ("mapping-failure", "Mapping failure leaves the entity absent and disclosed.", {"expected_status": "partial"}),
        ("stale-cache", "An expired cache is stale, never live.", {"expected_status": "stale"}),
        ("corrupt-bars", "Corrupted intraday bars block detailed narration.", {"expected_status": "unavailable", "intraday": True}),
        ("missing-calendar", "Missing calendar blocks exchange-session claims.", {"expected_status": "unavailable", "intraday": True}),
    ),
    "safety": (
        ("prompt-injection", "Instruction text inside a headline is quarantined.", {"expected_status": "partial", "maximum_confidence": 0.2}),
        ("html-injection", "HTML is removed from normalized display text.", {}),
        ("markdown-injection", "Markdown links cannot create trusted sources.", {}),
        ("script-tag", "Script content is removed and flagged.", {"expected_status": "partial"}),
        ("malicious-url", "Non-HTTPS and credential-bearing URLs are rejected.", {"expected_status": "partial"}),
        ("oversized-body", "An oversized body is never persisted or traced.", {"expected_status": "partial"}),
        ("source-spoof", "Display-name spoofing cannot override registry identity.", {"expected_status": "partial"}),
        ("fake-official-domain", "A lookalike domain remains unverified.", {"expected_status": "partial", "maximum_confidence": 0.25}),
        ("secret-request", "A request to reveal provider credentials is refused.", {"expected_status": "unavailable"}),
        ("causal-overstatement", "Unsupported causal wording is rejected or rewritten noncausally.", {"expected_status": "partial", "maximum_confidence": 0.5}),
    ),
}


def build_cases() -> list[dict[str, Any]]:
    seeds = list(REQUIRED)
    for category, definitions in GROUPS.items():
        for code, description, overrides in definitions:
            seeds.append(seed(f"{category}-{code}", description, category, **overrides))

    cases: list[dict[str, Any]] = []
    for index, item in enumerate(seeds, start=1):
        categories = list(item.categories)
        # Cross-capability overlaps are intentional: the first release cases
        # also exercise public routing/synthesis, session-boundary cases feed
        # narrative grounding, and hostile inputs are failure injections.
        if index <= 10 and "routing_synthesis" not in categories:
            categories.append("routing_synthesis")
        if index == 1 and "classification" not in categories:
            categories.append("classification")
        if item.code in {
            "market_reaction-five-minute-supported",
            "market_reaction-fifteen-minute-supported",
        } and "intraday_narrative" not in categories:
            categories.append("intraday_narrative")
        if item.code in {
            "session_segmentation-premarket-boundary",
            "session_segmentation-opening-boundary",
            "session_segmentation-morning-boundary",
            "session_segmentation-midday-boundary",
            "session_segmentation-afternoon-boundary",
        } and "intraday_narrative" not in categories:
            categories.append("intraday_narrative")
        if item.code in {
            "intraday_narrative-morning-reversal",
            "intraday_narrative-afternoon-reversal",
        } and "market_reaction" not in categories:
            categories.append("market_reaction")
        if item.code in {
            "safety-prompt-injection",
            "safety-html-injection",
            "safety-markdown-injection",
            "safety-script-tag",
            "safety-malicious-url",
            "safety-oversized-body",
            "safety-source-spoof",
            "safety-fake-official-domain",
        } and "failure" not in categories:
            categories.append("failure")
        expected = {
            "status": item.expected_status,
            "maximum_confidence": item.maximum_confidence,
            "blocked_claims": list(item.blocked_claims),
            "required_disclosures": list(item.disclosures),
            **dict(item.expected),
        }
        cases.append(
            {
                "schema_version": "stage8-golden-case-v1",
                "fixture_id": item.code,
                "ordinal": index,
                "description": item.description,
                "categories": categories,
                "as_of": AS_OF,
                "input": {
                    "data_mode": "hermetic",
                    "provider_mode": item.provider_mode,
                    "intraday_available": item.intraday,
                    "scenario": item.code,
                },
                "expected": expected,
                "network_allowed": False,
                "model_calls_allowed": 0,
                "article_body_storage_allowed": False,
            }
        )
    return cases


def render(cases: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(case, ensure_ascii=False, sort_keys=True) + "\n" for case in cases)


def validate(cases: list[dict[str, Any]]) -> None:
    ids = [case["fixture_id"] for case in cases]
    if len(cases) < 100:
        raise SystemExit("Stage 8 requires at least 100 permanent cases.")
    if len(ids) != len(set(ids)):
        raise SystemExit("Stage 8 fixture IDs must be unique.")
    counts = Counter(category for case in cases for category in case["categories"])
    minimums = {
        "provider_normalization": 10,
        "source_credibility": 10,
        "classification": 15,
        "clustering": 15,
        "entity_mapping": 15,
        "materiality": 15,
        "market_reaction": 20,
        "session_segmentation": 15,
        "intraday_narrative": 20,
        "routing_synthesis": 20,
        "failure": 20,
    }
    missing = {key: (counts[key], required) for key, required in minimums.items() if counts[key] < required}
    if missing:
        raise SystemExit(f"Stage 8 fixture category minimums not met: {missing}")
    for case in cases:
        if case["input"]["data_mode"] != "hermetic" or case["network_allowed"]:
            raise SystemExit(f"Fixture {case['fixture_id']} is not hermetic.")
        if case["model_calls_allowed"] != 0 or case["article_body_storage_allowed"]:
            raise SystemExit(f"Fixture {case['fixture_id']} violates the deterministic storage boundary.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    cases = build_cases()
    validate(cases)
    output = render(cases)
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != output:
            raise SystemExit("Stage 8 golden corpus is missing or out of date; run generate_cases.py.")
        print(json.dumps({"status": "passed", "cases": len(cases)}))
        return 0
    OUTPUT.write_text(output, encoding="utf-8")
    print(json.dumps({"status": "generated", "cases": len(cases), "path": str(OUTPUT)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
