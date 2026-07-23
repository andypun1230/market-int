import { buildEvidenceClassSummary, evidenceClass } from '../src/features/trust/evidenceClasses';

function assert(condition: unknown, message: string) { if (!condition) throw new Error(message); }
const item = (id: 'price_volume' | 'money_flow' | 'options', availability: 'available' | 'partial' | 'stale' | 'unavailable', direction: 'positive' | 'negative' | 'unavailable', confidence: number | null) => evidenceClass({ id, availability, direction, confidence, freshness: null, provenance: [id], conclusion: availability === 'unavailable' ? null : `${id} conclusion`, limitations: [], evidenceIds: [`${id}-1`] });

const one = buildEvidenceClassSummary([item('price_volume', 'available', 'positive', 90), item('money_flow', 'unavailable', 'unavailable', null), item('options', 'unavailable', 'unavailable', null)], 'institutional evidence');
assert(one.state === 'partial' && one.availableCount === 1, 'one available class cannot imply unavailable direct classes');
assert(one.confidence === 30, 'confidence adjusts by class completeness');
const conflict = buildEvidenceClassSummary([item('price_volume', 'available', 'positive', 80), item('money_flow', 'available', 'negative', 80)], 'evidence');
assert(Boolean(conflict.contradiction), 'conflicting classes remain visible');
assert(buildEvidenceClassSummary([item('price_volume', 'available', 'positive', 80), item('money_flow', 'available', 'positive', 80)]).state === 'available', 'all classes available');
assert(buildEvidenceClassSummary([item('price_volume', 'unavailable', 'unavailable', null)]).state === 'unavailable', 'all unavailable');
assert(buildEvidenceClassSummary([item('price_volume', 'stale', 'positive', 70)]).state === 'stale', 'stale supporting class remains stale');
assert(buildEvidenceClassSummary([item('price_volume', 'partial', 'positive', 70), item('options', 'unavailable', 'unavailable', null)]).state === 'partial', 'partial evidence remains partial');
console.log('PASS Stage 10.2 evidence-class separation');
