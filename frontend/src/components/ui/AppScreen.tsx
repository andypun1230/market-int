import { useEffect, useRef, useState } from 'react';
import type { ReactElement, ReactNode } from 'react';
import { useLocalSearchParams, usePathname, useRouter } from 'expo-router';
import { Animated, Platform, ScrollView, StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import type { RefreshControlProps, StyleProp, ViewStyle } from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';

import {
  horizontalGutter,
  isPrimaryRoute,
  maximumContentWidth,
  pageBottomInset,
  type LayoutWidthPolicy,
  widthPolicyForRoute,
} from '@/architecture/layoutPolicy';
import { Spacing, Theme, Typography } from '@/constants/theme';
import { AppButton } from '@/components/ui/AppButton';
import { AppIcon } from '@/components/ui/AppIcon';
import { DataStateSummary } from '@/components/ui/DataStateSummary';
import { UniversalCommandHeader } from '@/features/command/components/UniversalCommandHeader';
import type { CopilotContext } from '@/features/copilot/types';
import { useReducedMotion } from '@/hooks/useReducedMotion';

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
  widthPolicy?: LayoutWidthPolicy;
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
  widthPolicy,
}: AppScreenProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { width: viewportWidth } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const { commandTarget } = useLocalSearchParams<{ commandTarget?: string | string[] }>();
  const target = Array.isArray(commandTarget) ? commandTarget[0] : commandTarget;
  const isPrimaryTab = isPrimaryRoute(pathname);
  const resolvedWidthPolicy = widthPolicy ?? widthPolicyForRoute(pathname);
  const gutter = horizontalGutter(viewportWidth);
  const bottomInset = pageBottomInset({ isPrimary: isPrimaryTab, platform: Platform.OS, safeAreaBottom: insets.bottom });
  const responsiveContentStyle = {
    maxWidth: maximumContentWidth(resolvedWidthPolicy),
    paddingBottom: bottomInset,
    paddingHorizontal: gutter,
  } satisfies ViewStyle;
  const showsDataState = ['/', '/market', '/sectors', '/watchlist', '/more', '/report', '/ai', '/settings', '/about', '/data-sources'].includes(pathname);
  const diagnosticDataState = ['/settings', '/about', '/data-sources'].includes(pathname);
  const [collapsed, setCollapsed] = useState(!isPrimaryTab);
  const reduceMotion = useReducedMotion();
  const [collapseProgress] = useState(() => new Animated.Value(isPrimaryTab ? 0 : 1));
  const [highlightProgress] = useState(() => new Animated.Value(0));
  const scrollRef = useRef<ScrollView | null>(null);

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
            {title ? <Text accessibilityRole="header" style={styles.title}>{title}</Text> : null}
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
    <SafeAreaView edges={['top', 'left', 'right']} style={styles.container}>
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
          contentContainerStyle={[styles.content, contentStyle, responsiveContentStyle]}
          onScroll={(event) => {
            if (!isPrimaryTab) return;
            const nextCollapsed = event.nativeEvent.contentOffset.y > 36;
            if (nextCollapsed !== collapsed) setCollapsed(nextCollapsed);
          }}
          ref={scrollRef}
          refreshControl={refreshControl}
          scrollEventThrottle={16}
          stickyHeaderIndices={stickyHeader ? [0] : undefined}>
          {stickyHeader ? <View style={[styles.stickyHeader, { marginHorizontal: -gutter, paddingHorizontal: gutter }]}>{stickyHeader}</View> : null}
          {stickyHeader ? <View style={styles.stickyBody}>{content}</View> : content}
        </ScrollView>
      ) : (
        <View style={[styles.content, styles.flexContent, contentStyle, responsiveContentStyle]}>{content}</View>
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
    alignSelf: 'center',
    gap: Spacing.three,
    paddingVertical: Spacing.three,
    width: '100%',
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
