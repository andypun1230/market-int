export type AtomicScreenPhase = 'idle' | 'loading' | 'available' | 'partial' | 'empty' | 'unavailable' | 'stale' | 'failed';

export type AtomicScreenState<T> = {
  phase: AtomicScreenPhase;
  data: T | null;
  error: string | null;
  refreshing: boolean;
  requestId: number;
  retained: boolean;
};

export type AtomicScreenEvent<T> =
  | { type: 'request'; requestId: number }
  | { type: 'success'; requestId: number; data: T; phase?: Exclude<AtomicScreenPhase, 'idle' | 'loading' | 'failed'> }
  | { type: 'failure'; requestId: number; error: string }
  | { type: 'disable' };

export function initialAtomicScreenState<T>(enabled = true): AtomicScreenState<T> {
  return { phase: enabled ? 'loading' : 'idle', data: null, error: null, refreshing: false, requestId: 0, retained: false };
}

export function reduceAtomicScreenState<T>(state: AtomicScreenState<T>, event: AtomicScreenEvent<T>): AtomicScreenState<T> {
  if (event.type === 'disable') return { ...state, phase: state.data ? state.phase : 'idle', refreshing: false };
  if (event.type === 'request') {
    return state.data
      ? { ...state, error: null, refreshing: true, requestId: event.requestId, retained: true }
      : { phase: 'loading', data: null, error: null, refreshing: false, requestId: event.requestId, retained: false };
  }
  if (event.requestId !== state.requestId) return state;
  if (event.type === 'success') {
    return { phase: event.phase ?? 'available', data: event.data, error: null, refreshing: false, requestId: event.requestId, retained: false };
  }
  if (state.data) {
    return { ...state, phase: 'stale', error: event.error, refreshing: false, retained: true };
  }
  return { phase: 'failed', data: null, error: event.error, refreshing: false, requestId: event.requestId, retained: false };
}

export function atomicRenderFlags<T>(state: AtomicScreenState<T>) {
  return {
    showContent: state.data !== null && ['available', 'partial', 'stale'].includes(state.phase),
    showEmpty: state.phase === 'empty',
    showError: state.phase === 'failed',
    showLoading: state.phase === 'loading',
    showUnavailable: state.phase === 'unavailable',
  };
}
