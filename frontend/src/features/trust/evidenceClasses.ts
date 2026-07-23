export const EVIDENCE_CLASS_IDS = [
  'price_volume', 'breadth', 'relative_strength', 'money_flow', 'options', 'liquidity',
  'large_prints', 'macro', 'news', 'fundamentals', 'technical', 'theme', 'sector', 'market_context',
] as const;

export type EvidenceClassId = typeof EVIDENCE_CLASS_IDS[number];
export type EvidenceAvailability = 'available' | 'partial' | 'stale' | 'unavailable';
export type EvidenceDirection = 'positive' | 'negative' | 'neutral' | 'mixed' | 'unavailable';

export type EvidenceClass = {
  id: EvidenceClassId;
  label: string;
  availability: EvidenceAvailability;
  freshness: string | null;
  confidence: number | null;
  provenance: string[];
  conclusion: string | null;
  direction: EvidenceDirection;
  limitations: string[];
  evidenceIds: string[];
};

export type EvidenceClassSummary = {
  classes: EvidenceClass[];
  state: 'available' | 'partial' | 'stale' | 'unavailable';
  headline: string;
  confidence: number | null;
  completeness: number;
  availableCount: number;
  totalCount: number;
  contradiction: string | null;
};

export function buildEvidenceClassSummary(classes: EvidenceClass[], subject = 'evidence'): EvidenceClassSummary {
  const usable = classes.filter((item) => item.availability !== 'unavailable');
  const available = classes.filter((item) => item.availability === 'available');
  const stale = classes.filter((item) => item.availability === 'stale');
  const confidenceValues = usable.map((item) => item.confidence).filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
  const completeness = classes.length ? usable.length / classes.length : 0;
  const rawConfidence = confidenceValues.length ? confidenceValues.reduce((sum, value) => sum + value, 0) / confidenceValues.length : null;
  const confidence = rawConfidence === null ? null : Math.round(rawConfidence * completeness);
  const directions = new Set(usable.map((item) => item.direction).filter((direction) => direction === 'positive' || direction === 'negative'));
  const contradiction = directions.size > 1 ? `Available ${subject} classes conflict; no cross-class confirmation is implied.` : null;
  const state = !usable.length ? 'unavailable'
    : stale.length && stale.length === usable.length ? 'stale'
      : available.length === classes.length ? 'available'
        : 'partial';
  const headline = state === 'available' ? `${title(subject)} fully available`
    : state === 'stale' ? `${title(subject)} is stale`
      : state === 'partial' ? `Partial ${subject}`
        : `${title(subject)} unavailable`;
  return { classes, state, headline, confidence, completeness, availableCount: usable.length, totalCount: classes.length, contradiction };
}

export function evidenceClass(input: Omit<EvidenceClass, 'label'> & { label?: string }): EvidenceClass {
  if (!EVIDENCE_CLASS_IDS.includes(input.id)) throw new Error(`Unsupported evidence class: ${input.id}`);
  return { ...input, label: input.label ?? input.id.split('_').map(title).join(' ') };
}

function title(value: string) {
  return value ? value[0].toUpperCase() + value.slice(1) : value;
}
