import { DarkTheme, DefaultTheme, Stack, ThemeProvider } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { useColorScheme } from 'react-native';

import { AnimatedSplashOverlay } from '@/components/animated-icon';
import { WatchlistProvider } from '@/features/watchlist/store';
import { useAppPreferences } from '@/features/preferences/appPreferences';
import { UserFacingDataStateProvider } from '@/features/trust/UserFacingDataStateProvider';

SplashScreen.preventAutoHideAsync();

export default function TabLayout() {
  const colorScheme = useColorScheme();
  const { preferences } = useAppPreferences();
  const effectiveColorScheme = preferences.appearance.theme === 'system' ? colorScheme : 'dark';
  return (
    <ThemeProvider value={effectiveColorScheme === 'dark' ? DarkTheme : DefaultTheme}>
      <UserFacingDataStateProvider>
        <WatchlistProvider>
        <AnimatedSplashOverlay reduceMotion={preferences.appearance.reduceMotion} />
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Screen name="(tabs)" />
          <Stack.Screen name="report" />
          <Stack.Screen name="ai" />
          <Stack.Screen name="notifications" />
          <Stack.Screen name="profile" />
          <Stack.Screen name="appearance" />
          <Stack.Screen name="language-region" />
          <Stack.Screen name="data-usage" />
          <Stack.Screen name="settings" />
          <Stack.Screen name="data-sources" />
          <Stack.Screen name="disclaimer" />
          <Stack.Screen name="privacy" />
          <Stack.Screen name="about" />
          <Stack.Screen name="accessibility" />
        </Stack>
        </WatchlistProvider>
      </UserFacingDataStateProvider>
    </ThemeProvider>
  );
}
