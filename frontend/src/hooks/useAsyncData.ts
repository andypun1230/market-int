import { useCallback, useEffect, useRef, useState } from 'react';

import { isRequestCancelled } from '@/services/requestCache';
import { initialAtomicScreenState, reduceAtomicScreenState } from '@/features/trust/atomicScreenState';

type UseAsyncDataOptions = {
  enabled?: boolean;
};

export function useAsyncData<T>(
  asyncFunction: () => Promise<T>,
  options: UseAsyncDataOptions = {},
) {
  const { enabled = true } = options;
  const mountedRef = useRef(false);
  const requestSequenceRef = useRef(0);
  const [state, setState] = useState(() => initialAtomicScreenState<T>(enabled));

  const refetch = useCallback(async () => {
    if (!enabled) {
      return null;
    }

    const requestSequence = ++requestSequenceRef.current;
    setState((current) => reduceAtomicScreenState(current, { type: 'request', requestId: requestSequence }));

    try {
      const nextData = await asyncFunction();

      if (mountedRef.current && isLatestAsyncDataRequest(requestSequence, requestSequenceRef.current)) {
        setState((current) => reduceAtomicScreenState(current, { type: 'success', requestId: requestSequence, data: nextData }));
      }

      return nextData;
    } catch (asyncError) {
      if (isRequestCancelled(asyncError)) {
        return null;
      }
      if (mountedRef.current && isLatestAsyncDataRequest(requestSequence, requestSequenceRef.current)) {
        setState((current) => reduceAtomicScreenState(current, { type: 'failure', requestId: requestSequence, error: getErrorMessage(asyncError) }));
      }

      return null;
    }
  }, [asyncFunction, enabled]);

  useEffect(() => {
    mountedRef.current = true;
    const timeout = setTimeout(() => {
      if (enabled) {
        refetch();
      } else if (mountedRef.current) {
        setState((current) => reduceAtomicScreenState(current, { type: 'disable' }));
      }
    }, 0);

    return () => {
      clearTimeout(timeout);
      mountedRef.current = false;
    };
  }, [enabled, refetch]);

  return {
    data: state.data,
    loading: state.phase === 'loading',
    error: state.error,
    refetch,
    refreshing: state.refreshing,
    screenState: state.phase,
    retainedData: state.retained,
  };
}

export function isLatestAsyncDataRequest(requestSequence: number, latestRequestSequence: number) {
  return requestSequence === latestRequestSequence;
}

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : 'Unable to load data.';
}
