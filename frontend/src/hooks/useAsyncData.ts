import { useCallback, useEffect, useRef, useState } from 'react';

import { isRequestCancelled } from '@/services/requestCache';

type UseAsyncDataOptions = {
  enabled?: boolean;
};

export function useAsyncData<T>(
  asyncFunction: () => Promise<T>,
  options: UseAsyncDataOptions = {},
) {
  const { enabled = true } = options;
  const mountedRef = useRef(false);
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    if (!enabled) {
      return null;
    }

    setLoading(true);
    setError(null);

    try {
      const nextData = await asyncFunction();

      if (mountedRef.current) {
        setData(nextData);
      }

      return nextData;
    } catch (asyncError) {
      if (isRequestCancelled(asyncError)) {
        return null;
      }
      if (mountedRef.current) {
        setError(getErrorMessage(asyncError));
      }

      return null;
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [asyncFunction, enabled]);

  useEffect(() => {
    mountedRef.current = true;
    const timeout = setTimeout(() => {
      if (enabled) {
        refetch();
      } else if (mountedRef.current) {
        setLoading(false);
      }
    }, 0);

    return () => {
      clearTimeout(timeout);
      mountedRef.current = false;
    };
  }, [enabled, refetch]);

  return { data, loading, error, refetch };
}

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : 'Unable to load data.';
}
