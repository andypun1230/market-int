import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

import { getProviderStatus, getTestDataStatus } from '@/services/api';
import { areTestScenariosEnabled } from '@/services/runtimeConfig';
import type { ProviderStatus, TestDataStatus } from '@/types/market';

import { classifyUserFacingDataState, type UserFacingDataState } from './userFacingDataState';

type Diagnostics = { provider: ProviderStatus | null; testData: TestDataStatus | null };
type ContextValue = { dataState: UserFacingDataState; diagnostics: Diagnostics; refresh: () => Promise<void> };

const UserFacingDataStateContext = createContext<ContextValue | null>(null);

export function UserFacingDataStateProvider({ children }: { children: ReactNode }) {
  const testScenariosEnabled = areTestScenariosEnabled();
  const [diagnostics, setDiagnostics] = useState<Diagnostics>({ provider: null, testData: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    const requests = testScenariosEnabled
      ? Promise.allSettled([getProviderStatus(), getTestDataStatus()])
      : Promise.allSettled([getProviderStatus()]);
    const [providerResult, testResult] = await requests;
    const provider = providerResult.status === 'fulfilled' ? providerResult.value : null;
    const testData = testResult?.status === 'fulfilled' ? testResult.value : null;
    setDiagnostics({ provider, testData });
    setError(providerResult.status === 'rejected' ? message(providerResult.reason) : null);
    setLoading(false);
  }, [testScenariosEnabled]);

  useEffect(() => {
    const timeout = setTimeout(() => void refresh(), 0);
    return () => clearTimeout(timeout);
  }, [refresh]);

  const dataState = useMemo(() => classifyUserFacingDataState({
    provider: diagnostics.provider,
    testData: diagnostics.testData,
    loading,
    error,
    scenarioActive: testScenariosEnabled && isTestMode(diagnostics.provider),
  }), [diagnostics, error, loading, testScenariosEnabled]);

  return (
    <UserFacingDataStateContext.Provider value={{ dataState, diagnostics, refresh }}>
      {children}
    </UserFacingDataStateContext.Provider>
  );
}

export function useUserFacingDataState() {
  const value = useContext(UserFacingDataStateContext);
  if (!value) throw new Error('useUserFacingDataState must be used within UserFacingDataStateProvider.');
  return value;
}

function isTestMode(provider: ProviderStatus | null) {
  return ['test', 'mock', 'generated_test_data'].includes(
    (provider?.configured_provider ?? provider?.market_data_provider ?? '').toLowerCase(),
  );
}

function message(error: unknown) {
  return error instanceof Error ? error.message : 'Provider status unavailable.';
}
