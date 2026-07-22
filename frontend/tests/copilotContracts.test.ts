import {
  normalizeCopilotAction,
  normalizeCopilotChatResponse,
} from '../src/features/copilot/utils/normalizeCopilotResponse';
import { sanitizeCopilotContext } from '../src/features/copilot/utils/sanitizeCopilotContext';
import { mergeHydratedWatchlistMembership } from '../src/features/copilot/utils/watchlistMembershipContext';
import type { CopilotContext } from '../src/features/copilot/types';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

function run() {
  const generalContext: CopilotContext = {
    generatedAt: '2026-07-22T00:00:00Z',
    routeName: '/ai',
    screenTitle: 'Institutional Copilot',
    screenType: 'general',
    sourceState: 'unavailable',
  };
  const beforeHydration = mergeHydratedWatchlistMembership(generalContext, false, [{ name: 'Arm Holdings', ticker: 'ARM' }]);
  assert(!Object.prototype.hasOwnProperty.call(beforeHydration, 'savedSymbols'), 'unhydrated membership remains missing so the server can use its fallback');
  const withMembership = mergeHydratedWatchlistMembership(generalContext, true, [
    { name: 'Arm Holdings', ticker: ' arm ' },
    { name: 'Duplicate ARM', ticker: 'ARM' },
    { ticker: 'NVDA' },
  ]);
  assert(withMembership.savedSymbols?.join(',') === 'ARM,NVDA', 'hydrated saved symbols are normalized and deduplicated');
  const membershipItems = withMembership.watchlist?.items as Record<string, unknown>[];
  assert(membershipItems[0]?.symbol === 'ARM' && membershipItems[0]?.name === 'Arm Holdings', 'membership items contain symbol and optional saved name');
  assert(!('price' in membershipItems[0]) && !('addedAt' in membershipItems[0]), 'membership hints contain no client market values or storage metadata');
  const hydratedEmpty = sanitizeCopilotContext(mergeHydratedWatchlistMembership(generalContext, true, []));
  assert(Array.isArray(hydratedEmpty.savedSymbols) && hydratedEmpty.savedSymbols.length === 0, 'hydrated empty membership remains explicitly present after sanitization');
  assert(Array.isArray(hydratedEmpty.watchlist?.items) && hydratedEmpty.watchlist.items.length === 0, 'hydrated empty watchlist items remain explicit after sanitization');
  const richItems = [{ score: 91, symbol: 'ARM' }];
  const richContext = mergeHydratedWatchlistMembership({ ...generalContext, watchlist: { items: richItems, summary: 'Loaded Watchlist screen context' } }, true, [{ ticker: 'ARM' }]);
  assert(richContext.watchlist?.items === richItems && richContext.watchlist.summary === 'Loaded Watchlist screen context', 'membership injection preserves richer launch watchlist context');

  const response = normalizeCopilotChatResponse({
    schemaVersion: 'institutional-copilot-response-v1',
    requestId: 'request-1',
    planId: 'plan-1',
    threadId: 'thread-1',
    status: 'partial',
    answer: 'Breadth is not confirming the index trend.',
    answerSections: {
      directAnswer: 'Breadth is not confirming the index trend.',
      why: ['Index strength is narrow.'],
      evidenceFor: ['The index remains above trend.'],
      evidenceAgainst: ['Participation is weak.'],
      whatWouldConfirm: ['Participation broadens.'],
      whatWouldInvalidate: ['The index loses trend support.'],
      whatWouldChange: [],
    },
    grounding: {
      contextUsed: ['Market / Breadth'],
      evidenceIds: ['evidence-1'],
      generatedAt: '2026-07-22T01:00:00Z',
      sourceState: 'partial',
    },
    suggestedFollowUps: ['Show me breadth.'],
    confidence: 62,
    answerConfidence: { level: 'moderate', reasons: ['One engine is partial.'] },
    generatedBy: 'deterministic-fallback',
    disclaimer: 'Educational market decision support only.',
    intent: {
      schemaVersion: 'copilot-intent-v1',
      intentId: 'intent-1',
      intent: 'STOCK_ANALYSIS',
      subIntent: 'challenge',
      entities: [{
        entityId: 'NVDA', entityType: 'stock', displayName: 'NVIDIA', symbol: 'NVDA', confidence: 0.99, resolutionSource: 'registry',
      }],
      tickerSymbols: ['NVDA'], sectors: [], themes: [], timeHorizon: 'short_term', requestedOutputType: 'decision_support',
      decisionSupportRequested: true, personalizationRelevant: false, navigationRequested: false,
      ambiguityLevel: 'none', confidence: 0.98, requiredAgents: ['stock'], optionalAgents: [], prohibitedAssumptions: [], unresolvedEntities: [],
    },
    reasoning: {
      schemaVersion: 'copilot-reasoning-v1',
      directAnswer: 'Breadth is not confirming the index trend.',
      stance: 'cautious',
      confidenceLabel: 'moderate',
      thesis: 'Narrow index strength warrants caution.',
      supportingFactors: [{ statement: 'The index remains above trend.', evidenceIds: ['evidence-1'] }],
      contradictoryFactors: [{ statement: 'Participation is weak.', evidenceIds: ['evidence-1'] }],
      keyRisks: [{ statement: 'Narrow leadership can reverse quickly.', evidenceIds: ['evidence-1'] }],
      confirmationConditions: [{ statement: 'Participation broadens.', evidenceIds: ['evidence-1'] }],
      invalidationConditions: [{ statement: 'The index loses trend support.', evidenceIds: ['evidence-1'] }],
      missingEvidence: [],
    },
    evidence: [{
      schemaVersion: 'copilot-evidence-v1', evidenceId: 'evidence-1', category: 'breadth', entity: 'SPX', metric: 'above_50d', value: 43.2,
      timeframe: 'current', interpretationClass: 'observed_fact', confidence: 'moderate',
      source: { sourceId: 'breadth:snapshot', provider: 'Polygon', dataset: 'market-breadth', marketDate: '2026-07-21' },
      freshness: { state: 'partial', marketDate: '2026-07-21', generatedAt: '2026-07-22T01:00:00Z', completeness: 0.82, provider: 'Polygon' },
      supportsClaimIds: [], contradictsClaimIds: ['claim-breadth-confirms'],
    }],
    actions: [{
      actionId: 'action-breadth', label: 'Open Breadth', actionType: 'navigate', destination: 'breadth', route: '/market', tab: 'breadth', parameters: {},
    }],
    freshnessSummary: {
      overallState: 'partial', marketDates: ['2026-07-21'], generatedTimestamps: ['2026-07-22T01:00:00Z'], currentCount: 0,
      staleCount: 0, partialCount: 1, unavailableCount: 0, testCount: 0, warnings: ['One series is incomplete.'],
    },
  });

  assert(response.schemaVersion === 'institutional-copilot-response-v1', 'response schema version is preserved');
  assert(response.intent?.entities[0]?.displayName === 'NVIDIA', 'structured intent entities are retained');
  assert(response.reasoning?.supportingFactors[0]?.statement === 'The index remains above trend.', 'reasoning factor objects retain statements');
  assert(response.reasoning?.supportingFactors[0]?.evidenceIds[0] === 'evidence-1', 'reasoning factor citations are retained');
  assert(response.evidence?.[0]?.source.provider === 'Polygon', 'nested source provider is normalized without stringification');
  assert(response.evidence?.[0]?.freshness.state === 'partial', 'nested evidence freshness is retained');
  assert(response.evidence?.[0]?.stance === 'contradicts', 'contradictory claim references derive the evidence stance');
  assert(response.freshnessSummary?.overallState === 'partial', 'overall freshness state uses the backend field');
  assert(response.answerSections?.whatWouldConfirm[0] === 'Participation broadens.', 'whatWouldConfirm is retained');
  assert(response.answerSections?.whatWouldInvalidate[0] === 'The index loses trend support.', 'whatWouldInvalidate is retained');
  assert(response.actions?.[0]?.destinationId === 'breadth', 'destination compatibility alias normalizes to destinationId');

  const canonicalAction = normalizeCopilotAction({ label: 'Open Macro', actionType: 'navigate', destinationId: 'macro', route: '/market' });
  assert(canonicalAction?.destinationId === 'macro', 'canonical destinationId remains supported');

  console.log('PASS Copilot enriched contracts, evidence provenance, reasoning factors, and compatibility aliases');
}

run();
