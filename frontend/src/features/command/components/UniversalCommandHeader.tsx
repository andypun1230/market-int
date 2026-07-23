import { useEffect, useMemo, useRef, useState } from 'react';
import { usePathname, useRouter } from 'expo-router';
import { SymbolView } from 'expo-symbols';
import {
  Animated,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import type { NativeSyntheticEvent, TextInputKeyPressEventData } from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';

import { maximumContentWidth, modalBottomInset } from '@/architecture/layoutPolicy';
import { TERMINOLOGY, availabilityTerm } from '@/architecture/terminologyRegistry';
import { MaxContentWidth, Spacing, Theme, Typography } from '@/constants/theme';
import { AppButton } from '@/components/ui/AppButton';
import { createCopilotContext } from '@/features/copilot/context/buildScreenContext';
import { setCopilotLaunchContext } from '@/features/copilot/state/copilotStore';
import type { CopilotContext } from '@/features/copilot/types';
import { sanitizeCopilotContext } from '@/features/copilot/utils/sanitizeCopilotContext';
import {
  buildCommandRegistry,
  buildMostActiveCommands,
  buildTickerCommand,
  EXPLORE_FEATURE_IDS,
  groupCommands,
  searchCommands,
  type CommandCategory,
  type CommandItem,
  type CommandSourceState,
} from '@/features/command/commandModel';
import { useRecentSearches } from '@/features/command/recentSearches';
import { useHomeDashboard } from '@/hooks/useHomeDashboard';
import { useReducedMotion } from '@/hooks/useReducedMotion';

const PLACEHOLDER = 'Search stocks, ETFs, indexes or features';

type UniversalCommandHeaderProps = {
  collapseProgress: Animated.Value;
  copilotContext?: CopilotContext;
  copilotPrompt?: string;
  showExpandedTitle?: boolean;
  subtitle?: string;
  title?: string;
};

export function UniversalCommandHeader({
  collapseProgress,
  copilotContext,
  copilotPrompt,
  showExpandedTitle = false,
  subtitle,
  title,
}: UniversalCommandHeaderProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [searchVisible, setSearchVisible] = useState(false);
  const context = copilotContext ?? createCopilotContext({
    routeName: pathname,
    screenTitle: title ?? 'Market Intelligence',
    screenType: 'general',
    sourceState: 'unavailable',
  });
  const titleHeight = showExpandedTitle
    ? collapseProgress.interpolate({ inputRange: [0, 1], outputRange: [58, 0] })
    : 0;
  const titleOpacity = showExpandedTitle
    ? collapseProgress.interpolate({ inputRange: [0, 0.7, 1], outputRange: [1, 0, 0] })
    : 0;
  const searchHeight = collapseProgress.interpolate({ inputRange: [0, 1], outputRange: [48, 44] });

  useEffect(() => {
    if (typeof document === 'undefined') return;
    const openFromKeyboard = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (event.key !== '/' || target?.tagName === 'INPUT' || target?.tagName === 'TEXTAREA') return;
      event.preventDefault();
      setSearchVisible(true);
    };
    document.addEventListener('keydown', openFromKeyboard);
    return () => document.removeEventListener('keydown', openFromKeyboard);
  }, []);

  const launchCopilot = () => {
    setCopilotLaunchContext(sanitizeCopilotContext(context), copilotPrompt);
    router.push('/ai');
  };

  return (
    <View style={styles.shell}>
      <View style={styles.headerInner}>
        {showExpandedTitle ? (
          <Animated.View style={[styles.titleBlock, { maxHeight: titleHeight, opacity: titleOpacity }]}>
            <Text numberOfLines={1} style={styles.title}>{title}</Text>
            {subtitle ? <Text numberOfLines={1} style={styles.subtitle}>{subtitle}</Text> : null}
          </Animated.View>
        ) : null}
        <View style={styles.commandRow}>
          <Animated.View style={[styles.searchWrap, { height: searchHeight }]}>
            <Pressable
              accessibilityHint="Opens universal navigation search"
              accessibilityLabel={PLACEHOLDER}
              accessibilityRole="button"
              onPress={() => setSearchVisible(true)}
              style={({ pressed }) => [styles.searchButton, pressed && styles.pressed]}>
              <SymbolView name={{ ios: 'magnifyingglass', android: 'search', web: 'search' } as never} size={18} tintColor={Theme.colors.textMuted} weight="medium" />
              <Text adjustsFontSizeToFit minimumFontScale={0.72} numberOfLines={1} style={styles.searchPlaceholder}>{PLACEHOLDER}</Text>
              <View style={styles.shortcutBadge}><Text style={styles.shortcutText}>/</Text></View>
            </Pressable>
          </Animated.View>
          <HeaderAction
            accessibilityLabel="Ask Copilot"
            icon={{ ios: 'sparkles', android: 'auto_awesome', web: 'auto_awesome' }}
            onPress={launchCopilot}
            tintColor={Theme.colors.purple}
          />
          <HeaderAction
            accessibilityLabel="Open settings"
            icon={{ ios: 'gearshape.fill', android: 'settings', web: 'settings' }}
            onPress={() => router.push('/settings')}
            tintColor={Theme.colors.accent}
          />
        </View>
      </View>
      <GlobalSearchOverlay
        context={context}
        onClose={() => setSearchVisible(false)}
        visible={searchVisible}
      />
    </View>
  );
}

function HeaderAction({ accessibilityLabel, icon, onPress, tintColor }: {
  accessibilityLabel: string;
  icon: { android: string; ios: string; web: string };
  onPress: () => void;
  tintColor: string;
}) {
  return (
    <AppButton
      accessibilityLabel={accessibilityLabel}
      label={accessibilityLabel}
      leadingIcon={<SymbolView name={icon as never} size={19} tintColor={tintColor} weight="bold" />}
      onPress={onPress}
      style={styles.headerAction}
      variant="icon"
    />
  );
}

function GlobalSearchOverlay({ context, onClose, visible }: {
  context: CopilotContext;
  onClose: () => void;
  visible: boolean;
}) {
  const router = useRouter();
  const reduceMotion = useReducedMotion();
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const insets = useSafeAreaInsets();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const { homeDashboard } = useHomeDashboard(visible);
  const { addRecent, clearRecents, items: recentItems } = useRecentSearches();
  const registry = useMemo(() => buildCommandRegistry(), []);
  const mostActive = useMemo(() => buildMostActiveCommands(
    (homeDashboard?.watchlist_summary.items ?? []).map((item) => ({
      changePercent: item.change_percent,
      fallbackUsed: item.fallback_used,
      isLive: item.is_live,
      isStale: item.is_stale,
      source: item.source ?? item.source_state ?? item.data_source,
      symbol: item.symbol,
    })),
  ), [homeDashboard]);
  const explore = useMemo(() => registry.filter((item) => EXPLORE_FEATURE_IDS.includes(item.id)), [registry]);
  const queryResults = useMemo(() => {
    if (!query.trim()) return [];
    const matches = searchCommands(registry, query);
    const ticker = matches.length ? null : buildTickerCommand(query);
    const unique = ticker && !matches.some((item) => item.title === ticker.title && (item.category === 'Stocks' || item.category === 'ETFs'))
      ? [ticker, ...matches]
      : matches;
    return [
      ...unique,
      {
        category: 'Copilot Suggestions' as const,
        id: `copilot-${query.trim().toLowerCase()}`,
        keywords: [query],
        metadata: 'Ask with current screen context',
        pathname: '/ai',
        title: `Ask Copilot about "${query.trim()}"`,
      },
    ];
  }, [query, registry]);
  const groups = query.trim() ? groupCommands(queryResults) : [];
  const keyboardItems = query.trim() ? groups.flatMap((group) => group.items) : [...recentItems, ...mostActive, ...explore];

  useEffect(() => {
    if (typeof document === 'undefined') return;
    if (visible) {
      returnFocusRef.current = document.activeElement as HTMLElement | null;
      return;
    }
    returnFocusRef.current?.focus?.();
  }, [visible]);

  const close = () => {
    setQuery('');
    setSelectedIndex(0);
    onClose();
  };

  const openItem = (item: CommandItem) => {
    addRecent(item);
    close();
    if (item.category === 'Copilot Suggestions') {
      setCopilotLaunchContext(sanitizeCopilotContext(context), query.trim());
      router.push('/ai');
      return;
    }
    router.push({ pathname: item.pathname, params: item.params } as never);
  };

  const handleKeyPress = (event: NativeSyntheticEvent<TextInputKeyPressEventData>) => {
    if (event.nativeEvent.key === 'ArrowDown') {
      setSelectedIndex((current) => Math.min(current + 1, Math.max(0, keyboardItems.length - 1)));
    } else if (event.nativeEvent.key === 'ArrowUp') {
      setSelectedIndex((current) => Math.max(0, current - 1));
    } else if (event.nativeEvent.key === 'Enter' && keyboardItems[selectedIndex]) {
      openItem(keyboardItems[selectedIndex]);
    } else if (event.nativeEvent.key === 'Escape') {
      close();
    }
  };

  return (
    <Modal animationType={reduceMotion ? 'none' : 'fade'} onRequestClose={close} presentationStyle="fullScreen" visible={visible}>
      <SafeAreaView edges={['top', 'left', 'right']} style={styles.overlay}>
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.overlayKeyboard}>
        <View accessibilityLabel="Search" accessibilityViewIsModal role="dialog" style={styles.overlayInner}>
          <View style={styles.overlaySearchRow}>
            <Pressable accessibilityLabel="Close search" accessibilityRole="button" onPress={close} style={({ pressed }) => [styles.overlayBack, pressed && styles.pressed]}>
              <SymbolView name={{ ios: 'chevron.left', android: 'arrow_back', web: 'arrow_back' } as never} size={19} tintColor={Theme.colors.text} weight="bold" />
            </Pressable>
            <View style={styles.overlayInputWrap}>
              <SymbolView name={{ ios: 'magnifyingglass', android: 'search', web: 'search' } as never} size={19} tintColor={Theme.colors.accent} weight="medium" />
              <TextInput
                accessibilityLabel="Global search"
                autoCapitalize="none"
                autoCorrect={false}
                autoFocus
                onChangeText={(value) => {
                  setQuery(value);
                  setSelectedIndex(0);
                }}
                onKeyPress={handleKeyPress}
                placeholder={PLACEHOLDER}
                placeholderTextColor={Theme.colors.textMuted}
                returnKeyType="search"
                style={styles.overlayInput}
                value={query}
              />
              {query ? (
                <Pressable accessibilityLabel="Clear search" accessibilityRole="button" onPress={() => { setQuery(''); setSelectedIndex(0); }} style={styles.clearQuery}>
                  <SymbolView name={{ ios: 'xmark.circle.fill', android: 'cancel', web: 'cancel' } as never} size={18} tintColor={Theme.colors.textMuted} />
                </Pressable>
              ) : null}
            </View>
          </View>

          <ScrollView contentContainerStyle={[styles.resultsContent, { paddingBottom: modalBottomInset(insets.bottom) }]} keyboardShouldPersistTaps="handled">
            {query.trim() ? (
              groups.length ? groups.map((group) => (
                <CommandSection
                  items={group.items}
                  key={group.category}
                  onPress={openItem}
                  selectedId={keyboardItems[selectedIndex]?.id}
                  title={group.category}
                />
              )) : <Text style={styles.emptyText}>{TERMINOLOGY.empty.noMatchingResults}</Text>
            ) : (
              <>
                <CommandSection
                  actionLabel={recentItems.length ? 'Clear' : undefined}
                  emptyLabel="Your recent destinations will appear here."
                  items={recentItems}
                  onAction={clearRecents}
                  onPress={openItem}
                  selectedId={keyboardItems[selectedIndex]?.id}
                  title="Recent Searches"
                />
                <CommandSection
                  emptyLabel="Active market data is updating."
                  items={mostActive}
                  onPress={openItem}
                  selectedId={keyboardItems[selectedIndex]?.id}
                  title="Most Active Markets"
                />
                <CommandSection
                  items={explore}
                  onPress={openItem}
                  selectedId={keyboardItems[selectedIndex]?.id}
                  title="Explore Features"
                />
              </>
            )}
          </ScrollView>
        </View>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </Modal>
  );
}

function CommandSection({ actionLabel, emptyLabel, items, onAction, onPress, selectedId, title }: {
  actionLabel?: string;
  emptyLabel?: string;
  items: CommandItem[];
  onAction?: () => void;
  onPress: (item: CommandItem) => void;
  selectedId?: string;
  title: string;
}) {
  return (
    <View style={styles.section}>
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>{title}</Text>
        {actionLabel && onAction ? <Pressable accessibilityLabel={actionLabel} accessibilityRole="button" onPress={onAction} style={styles.sectionActionButton}><Text style={styles.sectionAction}>{actionLabel}</Text></Pressable> : null}
      </View>
      {items.length ? items.map((item) => (
        <CommandRow isSelected={selectedId === item.id} item={item} key={item.id} onPress={() => onPress(item)} />
      )) : <Text style={styles.emptyText}>{emptyLabel}</Text>}
    </View>
  );
}

function CommandRow({ isSelected, item, onPress }: { isSelected: boolean; item: CommandItem; onPress: () => void }) {
  return (
    <Pressable
      accessibilityLabel={`${item.title}, ${item.metadata}`}
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [styles.resultRow, isSelected && styles.resultRowSelected, pressed && styles.pressed]}>
      <View style={[styles.resultIcon, { backgroundColor: iconTone(item.category) }]}>
        <SymbolView name={iconForCategory(item.category) as never} size={17} tintColor={iconColor(item.category)} weight="bold" />
      </View>
      <View style={styles.resultCopy}>
        <Text numberOfLines={1} style={styles.resultTitle}>{item.title}</Text>
        <Text numberOfLines={1} style={styles.resultMetadata}>{item.metadata}</Text>
      </View>
      {item.sourceState ? <SourceBadge state={item.sourceState} /> : null}
      <SymbolView name="chevron.right" size={14} tintColor={Theme.colors.textMuted} weight="bold" />
    </Pressable>
  );
}

function SourceBadge({ state }: { state: CommandSourceState }) {
  const color = state === 'live' ? Theme.colors.success : state === 'test' ? Theme.colors.warning : state === 'unavailable' ? Theme.colors.textMuted : Theme.colors.accent;
  const label = availabilityTerm(state);
  return <View accessibilityLabel={`Availability: ${label}`} accessible style={[styles.sourceBadge, { borderColor: color }]}><View accessibilityElementsHidden aria-hidden importantForAccessibility="no-hide-descendants" style={[styles.sourceDot, { backgroundColor: color }]} /><Text style={[styles.sourceText, { color }]}>{label}</Text></View>;
}

function iconForCategory(category: CommandCategory) {
  if (category === 'Stocks' || category === 'ETFs' || category === 'Indexes') return { ios: 'chart.line.uptrend.xyaxis', android: 'show_chart', web: 'show_chart' };
  if (category === 'Sectors' || category === 'Themes') return { ios: 'square.grid.2x2', android: 'category', web: 'category' };
  if (category === 'Reports') return { ios: 'doc.text', android: 'description', web: 'description' };
  if (category === 'Settings') return { ios: 'gearshape', android: 'settings', web: 'settings' };
  if (category === 'Copilot Suggestions') return { ios: 'sparkles', android: 'auto_awesome', web: 'auto_awesome' };
  return { ios: 'command', android: 'apps', web: 'apps' };
}

function iconTone(category: CommandCategory) {
  if (category === 'Copilot Suggestions' || category === 'Themes') return Theme.colors.purpleSoft;
  if (category === 'Settings') return Theme.colors.cardElevated;
  return Theme.colors.accentSoft;
}

function iconColor(category: CommandCategory) {
  return category === 'Copilot Suggestions' || category === 'Themes' ? Theme.colors.purple : Theme.colors.accent;
}

const styles = StyleSheet.create({
  clearQuery: { alignItems: 'center', height: 44, justifyContent: 'center', width: 44 },
  commandRow: { alignItems: 'center', flexDirection: 'row', gap: Spacing.two },
  emptyText: { color: Theme.colors.textMuted, fontSize: Typography.control.fontSize, lineHeight: 20, paddingVertical: Spacing.two },
  headerAction: { borderRadius: Theme.radii.small },
  headerInner: { alignSelf: 'center', maxWidth: MaxContentWidth + Spacing.six, paddingHorizontal: Spacing.three, paddingVertical: Spacing.two, width: '100%' },
  overlay: { backgroundColor: Theme.colors.background, flex: 1 },
  overlayBack: { alignItems: 'center', backgroundColor: Theme.colors.cardMuted, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, height: 46, justifyContent: 'center', width: 46 },
  overlayInner: { alignSelf: 'center', flex: 1, maxWidth: maximumContentWidth('modal_content'), width: '100%' },
  overlayKeyboard: { flex: 1 },
  overlayInput: { color: Theme.colors.text, flex: 1, fontSize: Typography.control.fontSize, fontWeight: Typography.weights.emphasis, minWidth: 0, outlineStyle: 'none' } as never,
  overlayInputWrap: { alignItems: 'center', backgroundColor: Theme.colors.card, borderColor: Theme.colors.accent, borderRadius: Theme.radii.card, borderWidth: 1, flex: 1, flexDirection: 'row', gap: Spacing.two, minHeight: 46, paddingHorizontal: Spacing.three },
  overlaySearchRow: { alignItems: 'center', borderBottomColor: Theme.colors.border, borderBottomWidth: 1, flexDirection: 'row', gap: Spacing.two, padding: Spacing.three },
  pressed: { opacity: 0.72 },
  resultCopy: { flex: 1, gap: 3, minWidth: 0 },
  resultIcon: { alignItems: 'center', borderRadius: Theme.radii.small, height: 34, justifyContent: 'center', width: 34 },
  resultMetadata: { color: Theme.colors.textMuted, fontSize: Typography.small.fontSize },
  resultRow: { alignItems: 'center', borderColor: 'transparent', borderRadius: Theme.radii.small, borderWidth: 1, flexDirection: 'row', gap: Spacing.two, minHeight: 54, paddingHorizontal: Spacing.two, paddingVertical: Spacing.two },
  resultRowSelected: { backgroundColor: Theme.colors.cardMuted, borderColor: Theme.colors.accent },
  resultTitle: { color: Theme.colors.text, fontSize: Typography.body.fontSize, fontWeight: Typography.weights.strong },
  resultsContent: { gap: Spacing.four, padding: Spacing.three, paddingBottom: Spacing.six },
  searchButton: { alignItems: 'center', backgroundColor: Theme.colors.card, borderColor: Theme.colors.border, borderRadius: Theme.radii.card, borderWidth: 1, flex: 1, flexDirection: 'row', gap: Spacing.two, minWidth: 0, paddingHorizontal: Spacing.three },
  searchPlaceholder: { color: Theme.colors.textMuted, flex: 1, fontSize: Typography.control.fontSize, fontWeight: Typography.weights.emphasis, minWidth: 0 },
  searchWrap: { flex: 1, minWidth: 0 },
  section: { gap: Spacing.one },
  sectionAction: { color: Theme.colors.accent, fontSize: Typography.small.fontSize, fontWeight: Typography.weights.strong, padding: Spacing.two },
  sectionActionButton: { alignItems: 'center', justifyContent: 'center', minHeight: 44, minWidth: 44 },
  sectionHeader: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', minHeight: 30 },
  sectionTitle: { color: Theme.colors.textMuted, fontSize: Typography.small.fontSize, fontWeight: Typography.weights.strong, textTransform: 'uppercase' },
  shell: { backgroundColor: Theme.colors.background, borderBottomColor: Theme.colors.border, borderBottomWidth: 1, zIndex: 20 },
  shortcutBadge: { alignItems: 'center', backgroundColor: Theme.colors.cardElevated, borderColor: Theme.colors.border, borderRadius: 5, borderWidth: 1, height: 22, justifyContent: 'center', width: 22 },
  shortcutText: { color: Theme.colors.textMuted, fontSize: Typography.small.fontSize, fontWeight: Typography.weights.strong },
  sourceBadge: { alignItems: 'center', borderRadius: Theme.radii.pill, borderWidth: 1, flexDirection: 'row', gap: 4, paddingHorizontal: 7, paddingVertical: 4 },
  sourceDot: { borderRadius: Theme.radii.pill, height: 5, width: 5 },
  sourceText: { fontSize: Typography.chartLabel.fontSize, fontWeight: Typography.weights.strong, textTransform: 'capitalize' },
  subtitle: { color: Theme.colors.textInverseMuted, fontSize: Typography.body.fontSize, lineHeight: 20 },
  title: { color: Theme.colors.textInverse, fontSize: Typography.screenTitleSmall.fontSize, fontWeight: Typography.weights.heavy },
  titleBlock: { gap: 2, overflow: 'hidden' },
});
