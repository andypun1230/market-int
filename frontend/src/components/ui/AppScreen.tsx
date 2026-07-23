import { useEffect, useRef, useState } from 'react';
import type { ReactElement, ReactNode } from 'react';
import { useLocalSearchParams, usePathname, useRouter } from 'expo-router';
import { AccessibilityInfo, Animated, SafeAreaView, ScrollView, StyleSheet, Text, View } from 'react-native';
import type { RefreshControlProps, StyleProp, ViewStyle } from 'react-native';

import { Spacing, Theme, Typography } from '@/constants/theme';
import { AppButton } from '@/components/ui/AppButton';
import { AppIcon } from '@/components/ui/AppIcon';
import { DataStateSummary } from '@/components/ui/DataStateSummary';
import { UniversalCommandHeader } from '@/features/command/components/UniversalCommandHeader';
import type { CopilotContext } from '@/features/copilot/types';
import { useAppPreferences } from '@/features/preferences/appPreferences';

type AppScreenProps = {
  children: ReactNode;
  copilotContext?: CopilotContext;
  copilotPrompt?: string;
  contentStyle?: StyleProp<ViewStyle>;
  refreshControl?: ReactElement<RefreshControlProps>;
  scroll?: boolean;
  showBackButton?: boolean;
  stickyHeader?: ReactNode;
  subtitle?: string;
  title?: string;
};

export function AppScreen({
  children,
  copilotContext,
  copilotPrompt,
  contentStyle,
  refreshControl,
  scroll = true,
  showBackButton = false,
  stickyHeader,
  subtitle,
  title,
}: AppScreenProps) {
  const router = useRouter();
  const { preferences } = useAppPreferences();
  const pathname = usePathname();
  const { commandTarget } = useLocalSearchParams<{ commandTarget?: string | string[] }>();
  const target = Array.isArray(commandTarget) ? commandTarget[0] : commandTarget;
  const isPrimaryTab = ['/', '/market', '/sectors', '/watchlist', '/more'].includes(pathname);
  const showsDataState = ['/', '/market', '/sectors', '/watchlist', '/more', '/report', '/ai', '/settings', '/about', '/data-sources'].includes(pathname);
  const diagnosticDataState = ['/settings', '/about', '/data-sources'].includes(pathname);
  const [collapsed, setCollapsed] = useState(!isPrimaryTab);
  const [systemReduceMotion, setSystemReduceMotion] = useState(false);
  const reduceMotion = systemReduceMotion || preferences.appearance.reduceMotion;
  const [collapseProgress] = useState(() => new Animated.Value(isPrimaryTab ? 0 : 1));
  const [highlightProgress] = useState(() => new Animated.Value(0));
  const scrollRef = useRef<ScrollView | null>(null);

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setSystemReduceMotion);
    const subscription = AccessibilityInfo.addEventListener('reduceMotionChanged', setSystemReduceMotion);
    return () => subscription.remove();
  }, []);

  useEffect(() => {
    Animated.timing(collapseProgress, {
      duration: reduceMotion ? 0 : 190,
      toValue: collapsed ? 1 : 0,
      useNativeDriver: false,
    }).start();
  }, [collapseProgress, collapsed, reduceMotion]);

  useEffect(() => {
    if (!target) return;
    scrollRef.current?.scrollTo({ animated: !reduceMotion, y: 0 });
    highlightProgress.setValue(0);
    Animated.sequence([
      Animated.timing(highlightProgress, { duration: reduceMotion ? 0 : 220, toValue: 1, useNativeDriver: false }),
      Animated.delay(reduceMotion ? 0 : 650),
      Animated.timing(highlightProgress, { duration: reduceMotion ? 0 : 420, toValue: 0, useNativeDriver: false }),
    ]).start();
  }, [highlightProgress, reduceMotion, target]);
  const handleBack = () => {
    if (router.canGoBack()) {
      router.back();
      return;
    }
    router.replace('/');
  };

  const pageHeader = (
    <>
      {(!isPrimaryTab && title) || showBackButton ? (
        <View style={styles.header}>
          <View style={styles.titleRow}>
            {showBackButton ? (
              <AppButton
                accessibilityLabel="Go back"
                label="Go back"
                leadingIcon={<AppIcon color={Theme.colors.text} name="back" size={17} />}
                onPress={handleBack}
                style={styles.backButton}
                variant="icon"
              />
            ) : null}
            {title ? <Text style={styles.title}>{title}</Text> : null}
          </View>
          {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
        </View>
      ) : null}
    </>
  );

  const content = target ? (
    <Animated.View
      style={[
        styles.commandDestination,
        {
          backgroundColor: highlightProgress.interpolate({ inputRange: [0, 1], outputRange: ['rgba(56, 189, 248, 0)', 'rgba(56, 189, 248, 0.08)'] }),
          borderColor: highlightProgress.interpolate({ inputRange: [0, 1], outputRange: ['rgba(56, 189, 248, 0)', Theme.colors.accent] }),
        },
      ]}>
      {pageHeader}
      {showsDataState ? <DataStateSummary diagnostic={diagnosticDataState} /> : null}
      {children}
    </Animated.View>
  ) : <>{pageHeader}{showsDataState ? <DataStateSummary diagnostic={diagnosticDataState} /> : null}{children}</>;

  return (
    <SafeAreaView style={styles.container}>
      <UniversalCommandHeader
        collapseProgress={collapseProgress}
        copilotContext={copilotContext}
        copilotPrompt={copilotPrompt}
        showExpandedTitle={isPrimaryTab}
        subtitle={subtitle}
        title={title}
      />
      {scroll ? (
        <ScrollView
          contentContainerStyle={[styles.content, contentStyle]}
          onScroll={(event) => {
            if (!isPrimaryTab) return;
            const nextCollapsed = event.nativeEvent.contentOffset.y > 36;
            if (nextCollapsed !== collapsed) setCollapsed(nextCollapsed);
          }}
          ref={scrollRef}
          refreshControl={refreshControl}
          scrollEventThrottle={16}
          stickyHeaderIndices={stickyHeader ? [0] : undefined}>
          {stickyHeader ? <View style={styles.stickyHeader}>{stickyHeader}</View> : null}
          {stickyHeader ? <View style={styles.stickyBody}>{content}</View> : content}
        </ScrollView>
      ) : (
        <View style={[styles.content, styles.flexContent, contentStyle]}>{content}</View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: Theme.colors.background,
    flex: 1,
  },
  content: {
    gap: Spacing.three,
    padding: Spacing.three,
    paddingBottom: Spacing.six,
  },
  commandDestination: {
    borderRadius: Theme.radii.card,
    borderWidth: 1,
    gap: Spacing.three,
  },
  flexContent: {
    flex: 1,
  },
  header: {
    gap: Spacing.one,
    paddingTop: Spacing.two,
  },
  stickyBody: {
    gap: Spacing.three,
  },
  stickyHeader: {
    backgroundColor: Theme.colors.background,
    borderBottomColor: Theme.colors.border,
    borderBottomWidth: 1,
    elevation: 6,
    marginHorizontal: -Spacing.three,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
    shadowColor: '#000000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.18,
    shadowRadius: 6,
    zIndex: 20,
  },
  titleRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
  },
  backButton: {
    borderRadius: Theme.radii.pill,
  },
  title: {
    color: Theme.colors.textInverse,
    flex: 1,
    fontSize: Typography.screenTitle.fontSize,
    fontWeight: Typography.weights.heavy,
  },
  subtitle: {
    color: Theme.colors.textInverseMuted,
    fontSize: Typography.bodyLarge.fontSize,
    lineHeight: 22,
  },
});
