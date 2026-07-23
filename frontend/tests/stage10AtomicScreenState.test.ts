import { atomicRenderFlags, initialAtomicScreenState, reduceAtomicScreenState } from '../src/features/trust/atomicScreenState';

function assert(condition: unknown, message: string) { if (!condition) throw new Error(message); }
let state = initialAtomicScreenState<string>();
assert(state.phase === 'loading', 'initial loading');
state = reduceAtomicScreenState(state, { type: 'request', requestId: 1 });
state = reduceAtomicScreenState(state, { type: 'success', requestId: 1, data: 'rows' });
assert(state.phase === 'available' && state.data === 'rows', 'successful load');
state = reduceAtomicScreenState(state, { type: 'request', requestId: 2 });
assert(state.refreshing && state.data === 'rows', 'background refresh retains content');
state = reduceAtomicScreenState(state, { type: 'failure', requestId: 2, error: 'offline' });
assert(state.phase === 'stale' && state.retained && state.data === 'rows', 'failed refresh retains labelled stale cache');
state = reduceAtomicScreenState(state, { type: 'request', requestId: 3 });
state = reduceAtomicScreenState(state, { type: 'request', requestId: 4 });
state = reduceAtomicScreenState(state, { type: 'success', requestId: 3, data: 'old' });
assert(state.data === 'rows', 'rapid replacement ignores obsolete response');
state = reduceAtomicScreenState(state, { type: 'success', requestId: 4, data: 'fresh' });
assert(state.phase === 'available' && state.data === 'fresh', 'stale-to-fresh transition');
for (const phase of ['empty', 'partial', 'unavailable'] as const) {
  const next = reduceAtomicScreenState(reduceAtomicScreenState(initialAtomicScreenState<string>(), { type: 'request', requestId: 1 }), { type: 'success', requestId: 1, data: phase, phase });
  const flags = atomicRenderFlags(next);
  assert(Object.values(flags).filter(Boolean).length === 1, `${phase} has one render state`);
}
const failed = reduceAtomicScreenState(reduceAtomicScreenState(initialAtomicScreenState<string>(), { type: 'request', requestId: 1 }), { type: 'failure', requestId: 1, error: 'boom' });
assert(failed.phase === 'failed' && atomicRenderFlags(failed).showError, 'failed load');
console.log('PASS Stage 10.2 atomic analytical state');
