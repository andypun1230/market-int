import { useEffect, useRef, useState } from 'react';
import type { ReactElement, ReactNode } from 'react';
import { useLocalSearchParams, usePathname, useRouter } from 'expo-router';
import { SymbolView } from 'expo-symbols';
import { AccessibilityInfo, Animated, Pressable, SafeAreaView, ScrollView, StyleSheet, Text, View } from 'react-native';
import type { RefreshControlProps, StyleProp, ViewStyle } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';
import { UniversalCommandHeader } from '@/features/command/components/UniversalCommandHeader';
import type { CopilotContext } from '@/features/copilot/types';

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
  const pathname = usePathname();
  const { commandTarget } = useLocalSearchParams<{ commandTarget?: string | string[] }>();
  const target = Array.isArray(commandTarget) ? commandTarget[0] : commandTarget;
  const isPrimaryTab = ['/', '/market', '/sectors', '/watchlist', '/more'].includes(pathname);
  const [collapsed, setCollapsed] = useState(!isPrimaryTab);
  const [reduceMotion, setReduceMotion] = useState(false);
  const [collapseProgress] = useState(() => new Animated.Value(isPrimaryTab ? 0 : 1));
  const [highlightProgress] = useState(() => new Animated.Value(0));
  const scrollRef = useRef<ScrollView | null>(null);

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduceMotion);
    const subscription = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduceMotion);
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
              <Pressable
                accessibilityLabel="Go back"
                accessibilityRole="button"
                hitSlop={8}
                onPress={handleBack}
                style={({ pressed }) => [styles.backButton, pressed && styles.backButtonPressed]}>
                <SymbolView
                  name={{ ios: 'chevron.left', android: 'arrow_back', web: 'arrow_back' } as never}
                  size={17}
                  tintColor={Theme.colors.text}
                  weight="bold"
                />
              </Pressable>
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
      {children}
    </Animated.View>
  ) : <>{pageHeader}{children}</>;

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
    alignItems: 'center',
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    height: 36,
    justifyContent: 'center',
    width: 36,
  },
  backButtonPressed: {
    opacity: 0.72,
  },
  title: {
    color: Theme.colors.textInverse,
    flex: 1,
    fontSize: 29,
    fontWeight: '900',
  },
  subtitle: {
    color: Theme.colors.textInverseMuted,
    fontSize: 15,
    lineHeight: 22,
  },
});
