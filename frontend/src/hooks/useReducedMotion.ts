import { useEffect, useState } from 'react';
import { AccessibilityInfo } from 'react-native';

import { useAppPreferences } from '@/features/preferences/appPreferences';
import { resolveReducedMotion } from '@/features/preferences/reducedMotionPolicy';

export function useReducedMotion() {
  const { preferences } = useAppPreferences();
  const [systemPreference, setSystemPreference] = useState(false);

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setSystemPreference);
    const subscription = AccessibilityInfo.addEventListener('reduceMotionChanged', setSystemPreference);
    return () => subscription.remove();
  }, []);

  return resolveReducedMotion(preferences.appearance.reduceMotion, systemPreference);
}
