import type { EvidenceClassSummary } from './evidenceClasses';
import { confidenceLabel, freshnessLabel } from './confidenceFreshnessPresentation';
import type { UserFacingDataStateKey } from './userFacingDataState';

export type DecisionSummary = {
  id: string;
  title: string;
  currentState: string;
  whatChanged: string | null;
  preferredAction: string | null;
  mainRisk: string | null;
  invalidation: string | null;
  freshness: string;
  confidence: number | null;
  confidenceLabel: string;
  evidence: EvidenceClassSummary | null;
  availability: UserFacingDataStateKey | 'available';
  contradiction: string | null;
  whatWouldChange: string | null;
  methodology: string[];
};

export function decisionSummary(input: DecisionSummary): DecisionSummary {
  return {
    ...input,
    currentState: nonEmpty(input.currentState, 'Current conclusion unavailable'),
    freshness: freshnessLabel(input.freshness),
    confidenceLabel: confidenceLabel({ confidence: input.confidence, fallback: input.confidenceLabel }),
  };
}

function nonEmpty(value: string | null | undefined, fallback: string) {
  return value?.trim() || fallback;
}
