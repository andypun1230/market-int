import { rotationTrailHistoryDisclosure, rotationTrailMethodology } from '../src/features/sectors/rotationCopy';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

assert(rotationTrailHistoryDisclosure.includes('adjusted ETF-versus-SPY history'), 'trail copy identifies the real ETF history');
assert(rotationTrailHistoryDisclosure.includes('SectorSnapshots'), 'trail copy distinguishes shallow transition history');
assert(rotationTrailMethodology.includes('Overall rank uses the full sector composite'), 'methodology does not conflate trails and rank');
