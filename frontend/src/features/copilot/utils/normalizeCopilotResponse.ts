import type {
  CopilotActionV1,
  CopilotAnswerSections,
  CopilotChatResponse,
  CopilotEntityV1,
  CopilotEvidenceV1,
  CopilotFreshnessSummaryV1,
  CopilotFreshnessV1,
  CopilotGroundingV1,
  CopilotIntentV1,
  CopilotPlanStepV1,
  CopilotPlanV1,
  CopilotReasoningFactorV1,
  CopilotReasoningV1,
  CopilotSourceReferenceV1,
  CopilotSourceState,
  CopilotValidationResultV1,
} from '@/features/copilot/types';

type NormalizeDefaults = {
  requestId?: string | null;
  threadId?: string | null;
  generatedAt?: string;
};

export function normalizeCopilotChatResponse(raw: unknown, defaults: NormalizeDefaults = {}): CopilotChatResponse {
  const root = asRecord(raw);
  const answerSections = normalizeAnswerSections(value(root, 'answerSections', 'answer_sections'));
  const reasoning = normalizeReasoning(value(root, 'reasoning', 'synthesis'), answerSections);
  const answer = text(value(root, 'answer'))
    || reasoning?.directAnswer
    || answerSections?.directAnswer
    || 'Copilot completed the request without a narrative answer.';
  const grounding = normalizeGrounding(value(root, 'grounding'), defaults.generatedAt);
  const evidenceBundle = asRecord(value(root, 'evidenceBundle', 'evidence_bundle'));
  const evidence = list(value(root, 'evidence') ?? value(evidenceBundle, 'evidence'))
    .map(normalizeCopilotEvidence)
    .filter((item): item is CopilotEvidenceV1 => item !== null);
  const contradictoryEvidence = list(
    value(root, 'contradictoryEvidence', 'contradictory_evidence')
      ?? value(evidenceBundle, 'contradictoryEvidence', 'contradictory_evidence'),
  ).map(normalizeCopilotEvidence).filter((item): item is CopilotEvidenceV1 => item !== null)
    .map((item) => ({ ...item, stance: 'contradicts' as const }));
  const rawConfidence = finiteNumber(value(root, 'confidence'));
  const confidenceRecord = asRecord(value(root, 'answerConfidence', 'answer_confidence'));
  const confidenceLevel = normalizeConfidenceLevel(value(confidenceRecord, 'level'));
  const freshnessSummary = normalizeFreshnessSummary(
    value(root, 'freshnessSummary', 'freshness_summary')
      ?? value(evidenceBundle, 'freshnessSummary', 'freshness_summary'),
    grounding.sourceState,
  );
  const sourceState = freshnessSummary?.overallState ?? grounding.sourceState;

  return {
    schemaVersion: text(value(root, 'schemaVersion', 'schema_version', 'version')) || 'copilot-chat-response-v1',
    requestId: text(value(root, 'requestId', 'request_id')) || defaults.requestId || null,
    planId: text(value(root, 'planId', 'plan_id')) || text(value(asRecord(value(root, 'plan')), 'planId', 'plan_id')) || null,
    threadId: text(value(root, 'threadId', 'thread_id')) || defaults.threadId || 'copilot-local',
    answer,
    status: normalizeStatus(value(root, 'status'), sourceState),
    intent: normalizeCopilotIntent(value(root, 'intent')),
    plan: normalizeCopilotPlan(value(root, 'plan')),
    reasoning,
    answerSections,
    evidence,
    contradictoryEvidence,
    actions: list(value(root, 'actions') ?? value(evidenceBundle, 'deepLinks', 'deep_links'))
      .map(normalizeCopilotAction)
      .filter((item): item is CopilotActionV1 => item !== null),
    warnings: stringList(value(root, 'warnings') ?? value(evidenceBundle, 'warnings')),
    missingEvidence: stringList(
      value(root, 'missingEvidence', 'missing_evidence')
        ?? value(evidenceBundle, 'unavailableEvidence', 'unavailable_evidence'),
    ),
    freshnessSummary,
    grounding,
    suggestedFollowUps: stringList(value(root, 'suggestedFollowUps', 'suggested_follow_ups')),
    confidence: rawConfidence === null ? confidenceScore(confidenceLevel) : Math.max(0, Math.min(100, rawConfidence)),
    answerConfidence: confidenceRecord ? {
      level: confidenceLevel,
      reasons: stringList(value(confidenceRecord, 'reasons')),
    } : null,
    generatedBy: text(value(root, 'generatedBy', 'generated_by')) || 'deterministic-fallback',
    disclaimer: text(value(root, 'disclaimer')),
    validation: normalizeValidation(value(root, 'validation')),
    agentTimingsMs: numberRecord(value(root, 'agentTimingsMs', 'agent_timings_ms')),
  };
}

export function normalizeSourceState(input: unknown): CopilotSourceState {
  const normalized = text(input).toLowerCase().replaceAll('-', '_');
  if (normalized === 'live') return 'live';
  if (normalized === 'delayed') return 'delayed';
  if (normalized === 'cached' || normalized === 'cache') return 'cached';
  if (normalized === 'stale') return 'stale';
  if (normalized === 'test' || normalized === 'fixture') return 'test';
  if (normalized === 'mock') return 'mock';
  if (normalized === 'partial') return 'partial';
  if (normalized === 'mixed') return 'mixed';
  return 'unavailable';
}

export function buildPartialCopilotResponse({
  answer,
  evidence = [],
  actions = [],
  warnings = [],
  requestId,
  threadId,
  sourceState = 'partial',
}: {
  actions?: CopilotActionV1[];
  answer: string;
  evidence?: CopilotEvidenceV1[];
  requestId: string;
  sourceState?: CopilotSourceState;
  threadId?: string | null;
  warnings?: string[];
}): CopilotChatResponse {
  const generatedAt = new Date().toISOString();
  return normalizeCopilotChatResponse({
    requestId,
    threadId: threadId ?? 'copilot-local',
    answer,
    status: 'partial',
    evidence,
    actions,
    warnings,
    freshnessSummary: { overallState: sourceState },
    grounding: { contextUsed: [], sourceState, generatedAt },
    confidence: 0,
    suggestedFollowUps: [],
    generatedBy: 'partial-stream',
    disclaimer: '',
  }, { requestId, threadId, generatedAt });
}

export function normalizeCopilotEntity(input: unknown): CopilotEntityV1 | null {
  if (typeof input === 'string') {
    const displayName = input.trim();
    if (!displayName) return null;
    return {
      entityId: displayName,
      entityType: /^[A-Z][A-Z0-9.-]{0,9}$/.test(displayName) ? 'stock' : 'app_feature',
      displayName,
      symbol: /^[A-Z][A-Z0-9.-]{0,9}$/.test(displayName) ? displayName : null,
      confidence: 1,
      resolutionSource: 'legacy',
    };
  }
  const record = asRecord(input);
  if (!record) return null;
  const entityId = text(value(record, 'entityId', 'entity_id', 'id'));
  const displayName = text(value(record, 'displayName', 'display_name', 'name')) || entityId;
  if (!entityId && !displayName) return null;
  return {
    entityId: entityId || displayName,
    entityType: text(value(record, 'entityType', 'entity_type', 'type')) || 'app_feature',
    displayName,
    symbol: nullableText(value(record, 'symbol', 'ticker')),
    confidence: clamp01(finiteNumber(value(record, 'confidence')) ?? 1),
    resolutionSource: text(value(record, 'resolutionSource', 'resolution_source')) || 'registry',
  };
}

export function normalizeCopilotIntent(input: unknown): CopilotIntentV1 | null {
  const record = asRecord(input);
  if (!record) return null;
  const intent = text(value(record, 'intent', 'type'));
  if (!intent) return null;
  return {
    schemaVersion: text(value(record, 'schemaVersion', 'schema_version', 'version')) || 'copilot-intent-v1',
    intentId: text(value(record, 'intentId', 'intent_id')) || 'intent-unavailable',
    intent,
    subIntent: text(value(record, 'subIntent', 'sub_intent')),
    entities: list(value(record, 'entities')).map(normalizeCopilotEntity).filter((item): item is CopilotEntityV1 => item !== null),
    tickerSymbols: stringList(value(record, 'tickerSymbols', 'ticker_symbols')),
    sectors: stringList(value(record, 'sectors')),
    themes: stringList(value(record, 'themes')),
    timeHorizon: text(value(record, 'timeHorizon', 'time_horizon')) || 'unspecified',
    requestedOutputType: text(value(record, 'requestedOutputType', 'requested_output_type')) || 'answer',
    decisionSupportRequested: boolean(value(record, 'decisionSupportRequested', 'decision_support_requested')),
    personalizationRelevant: boolean(value(record, 'personalizationRelevant', 'personalization_relevant')),
    navigationRequested: boolean(value(record, 'navigationRequested', 'navigation_requested')),
    ambiguityLevel: text(value(record, 'ambiguityLevel', 'ambiguity_level')) || 'none',
    confidence: clamp01(finiteNumber(value(record, 'confidence')) ?? 0),
    requiredAgents: stringList(value(record, 'requiredAgents', 'required_agents')),
    optionalAgents: stringList(value(record, 'optionalAgents', 'optional_agents')),
    prohibitedAssumptions: stringList(value(record, 'prohibitedAssumptions', 'prohibited_assumptions')),
    unresolvedEntities: stringList(value(record, 'unresolvedEntities', 'unresolved_entities')),
    clarificationQuestion: nullableText(value(record, 'clarificationQuestion', 'clarification_question')),
  };
}

function normalizeCopilotPlan(input: unknown): CopilotPlanV1 | null {
  const record = asRecord(input);
  if (!record) return null;
  const planId = text(value(record, 'planId', 'plan_id'));
  if (!planId) return null;
  const rawSteps = value(record, 'orderedSteps', 'ordered_steps', 'steps');
  return {
    schemaVersion: text(value(record, 'schemaVersion', 'schema_version', 'version')) || 'copilot-plan-v1',
    planId,
    intentId: text(value(record, 'intentId', 'intent_id')),
    orderedSteps: list(rawSteps).map(normalizePlanStep).filter((item): item is CopilotPlanStepV1 => item !== null),
    requiredAgents: stringList(value(record, 'requiredAgents', 'required_agents')),
    optionalAgents: stringList(value(record, 'optionalAgents', 'optional_agents')),
    dependencies: stringListRecord(value(record, 'dependencies')),
    requiredEntities: stringList(value(record, 'requiredEntities', 'required_entities')),
    evidenceRequirements: list(value(record, 'evidenceRequirements', 'evidence_requirements')),
    freshnessRequirements: asRecord(value(record, 'freshnessRequirements', 'freshness_requirements')),
    responseTemplate: nullableText(value(record, 'responseTemplate', 'response_template')),
    deepLinkRequirements: stringList(value(record, 'deepLinkRequirements', 'deep_link_requirements')),
    fallbackRules: stringList(value(record, 'fallbackRules', 'fallback_rules')),
    maximumLatencyMs: finiteNumber(value(record, 'maximumLatencyMs', 'maximum_latency_ms')),
    parallelExecutionAllowed: value(record, 'parallelExecutionAllowed', 'parallel_execution_allowed') !== false,
  };
}

function normalizePlanStep(input: unknown, index: number): CopilotPlanStepV1 | null {
  const record = asRecord(input);
  if (!record) return null;
  const stepId = text(value(record, 'stepId', 'step_id', 'id')) || `step-${index + 1}`;
  return {
    stepId,
    order: finiteNumber(value(record, 'order')) ?? index + 1,
    agent: text(value(record, 'agent')),
    dependsOn: stringList(value(record, 'dependsOn', 'depends_on')),
    required: value(record, 'required') !== false,
    parallelGroup: finiteNumber(value(record, 'parallelGroup', 'parallel_group')) ?? 1,
    timeoutMs: finiteNumber(value(record, 'timeoutMs', 'timeout_ms')) ?? 1_500,
    purpose: text(value(record, 'purpose', 'label')),
  };
}

function normalizeGrounding(input: unknown, generatedAt?: string): CopilotGroundingV1 {
  const record = asRecord(input);
  return {
    contextUsed: stringList(value(record, 'contextUsed', 'context_used')),
    sourceState: normalizeSourceState(value(record, 'sourceState', 'source_state')),
    generatedAt: text(value(record, 'generatedAt', 'generated_at')) || generatedAt || new Date().toISOString(),
    marketDate: nullableText(value(record, 'marketDate', 'market_date')),
    providers: stringList(value(record, 'providers', 'sources')),
    evidenceIds: stringList(value(record, 'evidenceIds', 'evidence_ids')),
    completeness: finiteNumber(value(record, 'completeness')),
  };
}

function normalizeAnswerSections(input: unknown): CopilotAnswerSections | null {
  const record = asRecord(input);
  if (!record) return null;
  return {
    directAnswer: text(value(record, 'directAnswer', 'direct_answer')),
    why: stringList(value(record, 'why')),
    mainCaution: nullableText(value(record, 'mainCaution', 'main_caution')),
    whatWouldChange: stringList(value(record, 'whatWouldChange', 'what_would_change')),
    evidenceFor: stringList(value(record, 'evidenceFor', 'evidence_for', 'supportingEvidence', 'supporting_evidence')),
    evidenceAgainst: stringList(value(record, 'evidenceAgainst', 'evidence_against', 'opposingEvidence', 'opposing_evidence')),
    keyRisks: stringList(value(record, 'keyRisks', 'key_risks')),
    whatWouldConfirm: stringList(value(
      record,
      'whatWouldConfirm', 'what_would_confirm', 'whatConfirms', 'what_confirms',
      'confirmationConditions', 'confirmation_conditions',
    )),
    whatWouldInvalidate: stringList(value(
      record,
      'whatWouldInvalidate', 'what_would_invalidate', 'whatInvalidates', 'what_invalidates',
      'invalidationConditions', 'invalidation_conditions',
    )),
    missingEvidence: stringList(value(record, 'missingEvidence', 'missing_evidence')),
  };
}

function normalizeReasoning(input: unknown, sections: CopilotAnswerSections | null): CopilotReasoningV1 | null {
  const record = asRecord(input);
  if (!record && !sections) return null;
  const supporting = factorList(value(record, 'supportingFactors', 'supporting_factors'));
  const opposing = factorList(value(record, 'contradictoryFactors', 'contradictory_factors'));
  const risks = factorList(value(record, 'keyRisks', 'key_risks'));
  const confirmation = factorList(value(record, 'confirmationConditions', 'confirmation_conditions'));
  const invalidation = factorList(value(record, 'invalidationConditions', 'invalidation_conditions'));
  return {
    schemaVersion: text(value(record, 'schemaVersion', 'schema_version', 'version')) || 'copilot-reasoning-v1',
    directAnswer: text(value(record, 'directAnswer', 'direct_answer')) || sections?.directAnswer || '',
    stance: nullableText(value(record, 'stance')),
    confidenceLabel: nullableText(value(record, 'confidenceLabel', 'confidence_label')),
    thesis: nullableText(value(record, 'thesis')),
    supportingFactors: supporting.length ? supporting : factorsFromStrings(sections?.evidenceFor?.length ? sections.evidenceFor : sections?.why ?? []),
    contradictoryFactors: opposing.length ? opposing : factorsFromStrings(sections?.evidenceAgainst ?? []),
    contradictions: stringList(value(record, 'contradictions')),
    keyRisks: risks.length ? risks : factorsFromStrings(sections?.mainCaution ? [sections.mainCaution] : sections?.keyRisks ?? []),
    confirmationConditions: confirmation.length ? confirmation : factorsFromStrings(
      sections?.whatWouldConfirm?.length ? sections.whatWouldConfirm : sections?.whatWouldChange ?? [],
    ),
    invalidationConditions: invalidation.length ? invalidation : factorsFromStrings(sections?.whatWouldInvalidate ?? []),
    missingEvidence: stringList(value(record, 'missingEvidence', 'missing_evidence')).length
      ? stringList(value(record, 'missingEvidence', 'missing_evidence'))
      : sections?.missingEvidence ?? [],
    personalizationNote: nullableText(value(record, 'personalizationNote', 'personalization_note')),
    relatedResearch: stringList(value(record, 'relatedResearch', 'related_research')),
    recommendedAppDestinations: stringList(value(record, 'recommendedAppDestinations', 'recommended_app_destinations')),
    disclaimerClass: nullableText(value(record, 'disclaimerClass', 'disclaimer_class')),
  };
}

export function normalizeCopilotEvidence(input: unknown): CopilotEvidenceV1 | null {
  const record = asRecord(input);
  if (!record) return null;
  const evidenceId = text(value(record, 'evidenceId', 'evidence_id', 'id'));
  if (!evidenceId) return null;
  const source = normalizeSourceReference(value(record, 'source'), record, evidenceId);
  const freshness = normalizeFreshnessDetail(
    value(record, 'freshness', 'sourceState', 'source_state'),
    source,
    record,
  );
  const supportsClaimIds = stringList(value(record, 'supportsClaimIds', 'supports_claim_ids'));
  const contradictsClaimIds = stringList(value(record, 'contradictsClaimIds', 'contradicts_claim_ids'));
  return {
    schemaVersion: text(value(record, 'schemaVersion', 'schema_version', 'version')) || 'copilot-evidence-v1',
    evidenceId,
    category: text(value(record, 'category')) || 'market',
    entity: text(value(record, 'entity')) || 'market',
    metric: text(value(record, 'metric')) || 'observation',
    value: value(record, 'value') ?? null,
    unit: nullableText(value(record, 'unit')),
    currentState: nullableText(value(record, 'currentState', 'current_state')),
    priorValue: value(record, 'priorValue', 'prior_value') ?? null,
    change: value(record, 'change') ?? null,
    timeframe: text(value(record, 'timeframe')) || 'current',
    interpretation: nullableText(value(record, 'interpretation')),
    interpretationClass: text(value(record, 'interpretationClass', 'interpretation_class')) || 'observed_fact',
    source,
    freshness,
    confidence: normalizeEvidenceConfidence(value(record, 'confidence')),
    deepLink: nullableText(value(record, 'deepLink', 'deep_link')),
    reportReference: nullableText(value(record, 'reportReference', 'report_reference')),
    supportsClaimIds,
    contradictsClaimIds,
    stance: normalizeStance(value(record, 'stance'), supportsClaimIds, contradictsClaimIds),
  };
}

export function normalizeCopilotAction(input: unknown): CopilotActionV1 | null {
  const record = asRecord(input);
  if (!record) return null;
  const label = text(value(record, 'label', 'title'));
  const route = nullableText(value(record, 'route', 'pathname'));
  const destinationId = nullableText(value(record, 'destinationId', 'destination_id', 'destination'));
  if (!label || (!route && !destinationId)) return null;
  const rawParameters = asRecord(value(record, 'parameters', 'params'));
  const parameters = rawParameters ? Object.fromEntries(
    Object.entries(rawParameters).flatMap(([key, item]) => {
      const itemText = nullableText(item);
      return itemText === null ? [] : [[key, itemText]];
    }),
  ) : undefined;
  const actionType = text(value(record, 'actionType', 'action_type'));
  return {
    schemaVersion: text(value(record, 'schemaVersion', 'schema_version', 'version')) || 'copilot-action-v1',
    actionId: nullableText(value(record, 'actionId', 'action_id')) ?? undefined,
    label,
    actionType: normalizeActionType(actionType),
    destinationId,
    destination: nullableText(value(record, 'destination')),
    route,
    tab: nullableText(value(record, 'tab')),
    subTab: nullableText(value(record, 'subTab', 'sub_tab')),
    sectionId: nullableText(value(record, 'sectionId', 'section_id')),
    entity: nullableText(value(record, 'entity')),
    highlightTarget: nullableText(value(record, 'highlightTarget', 'highlight_target')),
    parameters,
  };
}

function normalizeSourceReference(
  input: unknown,
  evidenceRecord: Record<string, unknown>,
  evidenceId: string,
): CopilotSourceReferenceV1 {
  const record = asRecord(input);
  const legacySource = typeof input === 'string' ? input.trim() : '';
  const provider = text(value(record, 'provider'))
    || text(value(evidenceRecord, 'provider'))
    || legacySource
    || 'unavailable';
  const dataset = text(value(record, 'dataset')) || text(value(evidenceRecord, 'dataset')) || 'app-engine';
  return {
    sourceId: text(value(record, 'sourceId', 'source_id')) || `${provider}:${dataset}:${evidenceId}`,
    provider,
    dataset,
    generatedAt: nullableText(value(record, 'generatedAt', 'generated_at') ?? value(evidenceRecord, 'generatedAt', 'generated_at')),
    marketDate: nullableText(value(record, 'marketDate', 'market_date') ?? value(evidenceRecord, 'marketDate', 'market_date')),
    rawEngineReference: nullableText(value(record, 'rawEngineReference', 'raw_engine_reference')),
  };
}

function normalizeFreshnessDetail(
  input: unknown,
  source: CopilotSourceReferenceV1,
  evidenceRecord: Record<string, unknown>,
): CopilotFreshnessV1 {
  const record = asRecord(input);
  return {
    state: normalizeSourceState(record ? value(record, 'state', 'sourceState', 'source_state') : input),
    marketDate: nullableText(value(record, 'marketDate', 'market_date')) ?? source.marketDate ?? null,
    generatedAt: nullableText(value(record, 'generatedAt', 'generated_at')) ?? source.generatedAt ?? null,
    observedAt: nullableText(value(record, 'observedAt', 'observed_at')),
    expiresAt: nullableText(value(record, 'expiresAt', 'expires_at')),
    ageSeconds: finiteNumber(value(record, 'ageSeconds', 'age_seconds')),
    completeness: normalizeCompleteness(value(record, 'completeness') ?? value(evidenceRecord, 'completeness')),
    provider: nullableText(value(record, 'provider')) ?? source.provider,
    warnings: stringList(value(record, 'warnings')),
    label: nullableText(value(record, 'label')),
  };
}

function normalizeFreshnessSummary(input: unknown, fallback: CopilotSourceState): CopilotFreshnessSummaryV1 | null {
  const record = asRecord(input);
  if (!record) return null;
  const legacyMarketDate = nullableText(value(record, 'marketDate', 'market_date'));
  const legacyGeneratedAt = nullableText(value(record, 'generatedAt', 'generated_at'));
  return {
    overallState: normalizeSourceState(value(record, 'overallState', 'overall_state', 'state', 'sourceState', 'source_state') ?? fallback),
    marketDates: uniqueStrings([
      ...stringList(value(record, 'marketDates', 'market_dates')),
      ...(legacyMarketDate ? [legacyMarketDate] : []),
    ]),
    generatedTimestamps: uniqueStrings([
      ...stringList(value(record, 'generatedTimestamps', 'generated_timestamps')),
      ...(legacyGeneratedAt ? [legacyGeneratedAt] : []),
    ]),
    currentCount: finiteNumber(value(record, 'currentCount', 'current_count')) ?? 0,
    staleCount: finiteNumber(value(record, 'staleCount', 'stale_count')) ?? 0,
    partialCount: finiteNumber(value(record, 'partialCount', 'partial_count')) ?? 0,
    unavailableCount: finiteNumber(value(record, 'unavailableCount', 'unavailable_count')) ?? 0,
    testCount: finiteNumber(value(record, 'testCount', 'test_count')) ?? 0,
    warnings: stringList(value(record, 'warnings')),
  };
}

function normalizeValidation(input: unknown): CopilotValidationResultV1 | null {
  const record = asRecord(input);
  if (!record) return null;
  return {
    status: text(value(record, 'status')) || 'failed',
    checksRun: stringList(value(record, 'checksRun', 'checks_run')),
    issues: list(value(record, 'issues')).flatMap((item) => {
      const issue = asRecord(item);
      const message = text(value(issue, 'message'));
      return issue && message ? [{
        check: text(value(issue, 'check')),
        severity: text(value(issue, 'severity')),
        message,
      }] : [];
    }),
    fallbackUsed: boolean(value(record, 'fallbackUsed', 'fallback_used')),
  };
}

function normalizeStatus(input: unknown, source: CopilotSourceState): CopilotChatResponse['status'] {
  const normalized = text(input).toLowerCase();
  if (normalized === 'partial' || normalized === 'stale' || normalized === 'unavailable' || normalized === 'failed') return normalized;
  if (source === 'partial' || source === 'mixed') return 'partial';
  if (source === 'stale') return 'stale';
  if (source === 'unavailable') return 'unavailable';
  return 'complete';
}

function normalizeStance(
  input: unknown,
  supportsClaimIds: string[],
  contradictsClaimIds: string[],
): CopilotEvidenceV1['stance'] {
  const normalized = text(input).toLowerCase();
  if (normalized === 'contradicts' || normalized === 'against' || normalized === 'opposes') return 'contradicts';
  if (normalized === 'neutral' || normalized === 'mixed') return 'neutral';
  if (contradictsClaimIds.length && !supportsClaimIds.length) return 'contradicts';
  return 'supports';
}

function normalizeCompleteness(input: unknown): CopilotFreshnessV1['completeness'] {
  const number = finiteNumber(input);
  if (number !== null) return number;
  const normalized = text(input).toLowerCase();
  if (normalized === 'complete' || normalized === 'partial' || normalized === 'unavailable') return normalized;
  return null;
}

function normalizeConfidenceLevel(input: unknown): 'high' | 'moderate' | 'limited' {
  const normalized = text(input).toLowerCase();
  if (normalized === 'high') return 'high';
  if (normalized === 'limited' || normalized === 'low') return 'limited';
  return 'moderate';
}

function normalizeEvidenceConfidence(input: unknown): string | number {
  return typeof input === 'number' || typeof input === 'string' ? input : 'moderate';
}

function normalizeActionType(input: string): CopilotActionV1['actionType'] {
  if (input === 'open_entity' || input === 'open_report_section' || input === 'open_report' || input === 'highlight') return input;
  return 'navigate';
}

function factorList(input: unknown): CopilotReasoningFactorV1[] {
  return list(input).flatMap((item) => {
    if (typeof item === 'string') return item.trim() ? [{ statement: item.trim(), evidenceIds: [] }] : [];
    const record = asRecord(item);
    const statement = text(value(record, 'statement', 'text', 'label'));
    return record && statement ? [{
      statement,
      evidenceIds: stringList(value(record, 'evidenceIds', 'evidence_ids')),
    }] : [];
  });
}

function factorsFromStrings(items: string[]): CopilotReasoningFactorV1[] {
  return items.map((statement) => ({ statement, evidenceIds: [] }));
}

function confidenceScore(level: 'high' | 'moderate' | 'limited') {
  return level === 'high' ? 85 : level === 'limited' ? 45 : 68;
}

function asRecord(input: unknown): Record<string, unknown> | null {
  return input !== null && typeof input === 'object' && !Array.isArray(input)
    ? input as Record<string, unknown>
    : null;
}

function value(record: Record<string, unknown> | null, ...keys: string[]): unknown {
  if (!record) return undefined;
  for (const key of keys) {
    if (key in record) return record[key];
  }
  return undefined;
}

function list(input: unknown): unknown[] {
  return Array.isArray(input) ? input : [];
}

function stringList(input: unknown): string[] {
  if (typeof input === 'string') return input.trim() ? [input.trim()] : [];
  return list(input).map(text).filter(Boolean);
}

function text(input: unknown): string {
  return typeof input === 'string' ? input.trim() : input === null || input === undefined ? '' : String(input).trim();
}

function nullableText(input: unknown): string | null {
  return text(input) || null;
}

function finiteNumber(input: unknown): number | null {
  const parsed = typeof input === 'number' ? input : typeof input === 'string' && input.trim() ? Number(input) : Number.NaN;
  return Number.isFinite(parsed) ? parsed : null;
}

function boolean(input: unknown): boolean {
  return input === true || input === 'true' || input === 1;
}

function clamp01(input: number) {
  return Math.max(0, Math.min(1, input));
}

function uniqueStrings(items: string[]) {
  return [...new Set(items.map((item) => item.trim()).filter(Boolean))];
}

function numberRecord(input: unknown): Record<string, number> | undefined {
  const record = asRecord(input);
  if (!record) return undefined;
  return Object.fromEntries(Object.entries(record).flatMap(([key, item]) => {
    const number = finiteNumber(item);
    return number === null ? [] : [[key, number]];
  }));
}

function stringListRecord(input: unknown): Record<string, string[]> {
  const record = asRecord(input);
  if (!record) return {};
  return Object.fromEntries(Object.entries(record).map(([key, item]) => [key, stringList(item)]));
}
