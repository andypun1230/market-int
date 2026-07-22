from __future__ import annotations

import re

from app.intelligence.news.contracts import (
    ExpectedDirection,
    NewsContractModel,
    NewsEventType,
)


NEWS_TAXONOMY_VERSION = "news-taxonomy-v1"


class EventClassification(NewsContractModel):
    event_type: NewsEventType
    subtype: str | None = None
    expected_direction: ExpectedDirection
    method: str
    matched_rule: str | None = None
    engine_version: str = NEWS_TAXONOMY_VERSION


RULES: tuple[tuple[NewsEventType, str, tuple[str, ...]], ...] = (
    (NewsEventType.MONETARY_POLICY, "central_bank_policy", (r"\bfomc\b", r"\bfederal reserve\b", r"\bpolicy rate\b", r"\brate (?:cut|hike|decision)\b")),
    (NewsEventType.INFLATION, "price_data", (r"\bconsumer price index\b", r"\bcpi\b", r"\bpce inflation\b", r"\binflation\b")),
    (NewsEventType.EMPLOYMENT, "labor_data", (r"\bnonfarm payrolls?\b", r"\bpayrolls?\b", r"\bunemployment\b", r"\bjobless claims?\b")),
    (NewsEventType.ECONOMIC_GROWTH, "growth_data", (r"\bgross domestic product\b", r"\bgdp\b", r"\beconomic growth\b")),
    (NewsEventType.GOVERNMENT_POLICY, "fiscal_or_trade_policy", (r"\btariffs?\b", r"\bfiscal\b", r"\btax (?:bill|policy|change)\b", r"\bgovernment policy\b")),
    (NewsEventType.REGULATION, "regulatory_action", (r"\bregulat(?:or|ion|ory)\b", r"\bnew rule\b", r"\bantitrust\b")),
    (NewsEventType.GEOPOLITICS, "geopolitical_development", (r"\bsanctions?\b", r"\bgeopolit", r"\bceasefire\b", r"\barmed conflict\b")),
    (NewsEventType.GUIDANCE, "company_outlook", (r"\b(?:raises?|lowers?|cuts?) (?:full[- ]year )?(?:guidance|outlook|forecast)\b", r"\bfull[- ]year guidance\b")),
    (NewsEventType.EARNINGS, "financial_results", (r"\bquarterly results?\b", r"\bearnings (?:report|release|results?)\b", r"\b(?:revenue|eps) (?:beat|miss)\b")),
    (NewsEventType.MERGER_ACQUISITION, "transaction", (r"\bacqui(?:res?|sition)\b", r"\bmerger\b", r"\btakeover\b", r"\bbuyout\b")),
    (NewsEventType.CAPITAL_RAISE, "financing", (r"\bcapital raise\b", r"\bshare offering\b", r"\bdebt offering\b", r"\bsecondary offering\b")),
    (NewsEventType.BUYBACK, "share_repurchase", (r"\bshare repurchase\b", r"\bstock buyback\b", r"\bbuyback\b")),
    (NewsEventType.DIVIDEND, "distribution", (r"\bdividend\b",)),
    (NewsEventType.PRODUCT_LAUNCH, "product", (r"\bproduct launch\b", r"\bunveils?\b", r"\blaunches?\b")),
    (NewsEventType.SUPPLY_CHAIN, "supply_chain", (r"\bsupply chain\b", r"\bcomponent shortage\b", r"\bsupplier disruption\b")),
    (NewsEventType.CUSTOMER_CONTRACT, "commercial_contract", (r"\bcustomer contract\b", r"\bawarded (?:a )?contract\b", r"\bpurchase agreement\b")),
    (NewsEventType.LEGAL, "legal_proceeding", (r"\blawsuit\b", r"\bcourt (?:ruling|order)\b", r"\blegal action\b", r"\bsettlement\b")),
    (NewsEventType.MANAGEMENT_CHANGE, "executive_change", (r"\b(?:ceo|cfo|chair) (?:resigns?|retires?|appointed|named)\b", r"\bmanagement change\b")),
    (NewsEventType.ANALYST_ACTION, "analyst_rating", (r"\b(?:upgrade|downgrade|price target)\b", r"\banalyst action\b")),
    (NewsEventType.CREDIT_RATING, "credit_action", (r"\bcredit rating\b", r"\brating (?:upgrade|downgrade)\b")),
    (NewsEventType.CYBERSECURITY_INCIDENT, "cybersecurity", (r"\bcyber(?:security)? (?:incident|attack)\b", r"\bdata breach\b", r"\bransomware\b")),
    (NewsEventType.EXCHANGE_NOTICE, "exchange_action", (r"\bexchange notice\b", r"\btrading halt\b", r"\bdelist(?:ed|ing)?\b")),
    (NewsEventType.MARKET_STRUCTURE, "market_structure", (r"\bmarket structure\b", r"\bsettlement cycle\b", r"\bcircuit breaker\b")),
    (NewsEventType.POSITIONING_COMMENTARY, "commentary", (r"\bpositioning\b", r"\bmarket commentary\b", r"\binvestor sentiment\b")),
)

POSITIVE_PATTERNS = (
    r"\braises? (?:full[- ]year )?(?:guidance|outlook|forecast)\b",
    r"\b(?:beats?|above) expectations\b",
    r"\bapproval\b",
    r"\bwins? (?:a )?contract\b",
    r"\bshare repurchase\b",
)
NEGATIVE_PATTERNS = (
    r"\b(?:lowers?|cuts?) (?:full[- ]year )?(?:guidance|outlook|forecast)\b",
    r"\b(?:misses?|below) expectations\b",
    r"\bdata breach\b",
    r"\btrading halt\b",
    r"\bdowngrade\b",
    r"\blawsuit\b",
)


class NewsTaxonomyEngine:
    version = NEWS_TAXONOMY_VERSION

    def classify(
        self,
        *,
        headline: str,
        summary: str = "",
        confirmed_facts: tuple[str, ...] = (),
        structured_event_type: NewsEventType | None = None,
        structured_subtype: str | None = None,
        structured_direction: ExpectedDirection = ExpectedDirection.UNKNOWN,
    ) -> EventClassification:
        combined = " ".join((headline, summary, *confirmed_facts)).casefold()
        direction = (
            structured_direction
            if structured_direction != ExpectedDirection.UNKNOWN
            else self._direction(combined)
        )
        if structured_event_type is not None:
            return EventClassification(
                event_type=structured_event_type,
                subtype=structured_subtype,
                expected_direction=direction,
                method="structured_metadata",
            )
        for event_type, subtype, patterns in RULES:
            matched = next((pattern for pattern in patterns if re.search(pattern, combined)), None)
            if matched:
                return EventClassification(
                    event_type=event_type,
                    subtype=subtype,
                    expected_direction=direction,
                    method="deterministic_text_fallback",
                    matched_rule=matched,
                )
        return EventClassification(
            event_type=NewsEventType.OTHER,
            expected_direction=direction,
            method="deterministic_default",
        )

    @staticmethod
    def _direction(text: str) -> ExpectedDirection:
        positive = any(re.search(pattern, text) for pattern in POSITIVE_PATTERNS)
        negative = any(re.search(pattern, text) for pattern in NEGATIVE_PATTERNS)
        if positive and not negative:
            return ExpectedDirection.POSITIVE
        if negative and not positive:
            return ExpectedDirection.NEGATIVE
        if positive and negative:
            return ExpectedDirection.NEUTRAL
        return ExpectedDirection.UNKNOWN
