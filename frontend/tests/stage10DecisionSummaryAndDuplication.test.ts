import { decisionSummary } from '../src/features/trust/decisionSummary';
import { CONCLUSION_OWNERSHIP_REGISTRY, duplicatePrimaryConclusionDomains } from '../src/architecture/conclusionOwnershipRegistry';

function assert(condition: unknown, message: string) { if (!condition) throw new Error(message); }
const summary = decisionSummary({ id: 'test', title: 'Decision summary', currentState: '', whatChanged: null, preferredAction: null, mainRisk: null, invalidation: null, freshness: '', confidence: null, confidenceLabel: '', evidence: null, availability: 'unavailable', contradiction: 'Evidence conflicts', whatWouldChange: 'New evidence', methodology: [] });
assert(summary.currentState === 'Current conclusion unavailable', 'unavailable current state is explicit');
assert(summary.freshness === 'Last update unavailable' && summary.confidenceLabel === 'Confidence unavailable', 'required trust fields receive honest fallbacks');
assert(summary.contradiction === 'Evidence conflicts' && summary.whatWouldChange === 'New evidence', 'contradiction and change condition are preserved');
assert(duplicatePrimaryConclusionDomains().length === 0, 'one primary conclusion per target domain');
assert(CONCLUSION_OWNERSHIP_REGISTRY.find((item) => item.domain === 'sector_breadth_history')?.removed.includes('legacy no-history placeholder'), 'legacy Sector Breadth History duplicate is registered as removed');
assert(CONCLUSION_OWNERSHIP_REGISTRY.find((item) => item.domain === 'institutions')?.removed.includes('unsupported overall Bullish headline'), 'unsupported institutional headline is registered as removed');
console.log('PASS Stage 10.2 decision summary and duplicate conclusion audit');
