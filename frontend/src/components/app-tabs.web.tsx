import {
  Tabs,
  TabList,
  TabTrigger,
  TabSlot,
  TabTriggerSlotProps,
  TabListProps,
} from 'expo-router/ui';
import { SymbolView } from 'expo-symbols';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { LAYOUT_POLICY } from '@/architecture/layoutPolicy';
import { Spacing, Theme, Typography } from '@/constants/theme';

type TabIcon = {
  ios: string;
  web: string;
};

export default function AppTabs() {
  return (
    <Tabs>
      <TabSlot style={{ height: '100%' }} />
      <TabList asChild>
        <CustomTabList>
          <TabTrigger name="home" href="/" asChild>
            <TabButton icon={{ ios: 'house', web: 'home' }}>Home</TabButton>
          </TabTrigger>
          <TabTrigger name="market" href="/market" asChild>
            <TabButton icon={{ ios: 'chart.line.uptrend.xyaxis', web: 'monitoring' }}>
              Market
            </TabButton>
          </TabTrigger>
          <TabTrigger name="sectors" href="/sectors" asChild>
            <TabButton icon={{ ios: 'square.grid.2x2', web: 'category' }}>Sectors</TabButton>
          </TabTrigger>
          <TabTrigger name="watchlist" href="/watchlist" asChild>
            <TabButton icon={{ ios: 'star', web: 'star' }}>Watchlist</TabButton>
          </TabTrigger>
          <TabTrigger name="more" href="/more" asChild>
            <TabButton icon={{ ios: 'ellipsis.circle', web: 'more_horiz' }}>More</TabButton>
          </TabTrigger>
        </CustomTabList>
      </TabList>
    </Tabs>
  );
}

export function TabButton({
  children,
  icon,
  isFocused,
  ...props
}: TabTriggerSlotProps & { icon: TabIcon }) {
  const tintColor = isFocused ? Theme.colors.textInverse : Theme.colors.tabInactive;

  return (
    <Pressable
      {...props}
      accessibilityLabel={typeof children === 'string' ? children : undefined}
      style={({ pressed }) => pressed && styles.pressed}>
      <View style={[styles.tabButtonView, isFocused && styles.activeTab]}>
        <View accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
          <SymbolView tintColor={tintColor} name={{ web: icon.web, ios: icon.ios } as never} size={18} />
        </View>
        <Text style={[styles.tabLabel, isFocused && styles.activeTabLabel]}>{children}</Text>
      </View>
    </Pressable>
  );
}

export function CustomTabList(props: TabListProps) {
  const insets = useSafeAreaInsets();
  return (
    <View
      {...props}
      style={[styles.tabListContainer, { paddingBottom: Math.max(Spacing.two, insets.bottom) }]}>
      <View style={styles.innerContainer}>{props.children}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  tabListContainer: {
    bottom: 0,
    position: 'absolute',
    width: '100%',
    paddingHorizontal: Spacing.two,
    paddingTop: Spacing.two,
    justifyContent: 'center',
    alignItems: 'center',
    flexDirection: 'row',
  },
  innerContainer: {
    backgroundColor: Theme.colors.tabBar,
    borderColor: Theme.colors.borderDark,
    borderRadius: Theme.radii.card,
    borderWidth: 1,
    flexDirection: 'row',
    alignItems: 'center',
    flexGrow: 1,
    gap: Spacing.one,
    justifyContent: 'space-between',
    maxWidth: LAYOUT_POLICY.widths.constrained_settings,
  },
  pressed: {
    opacity: 0.7,
  },
  tabButtonView: {
    alignItems: 'center',
    borderRadius: Theme.radii.card,
    gap: Spacing.one,
    minWidth: 58,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.two,
  },
  activeTab: {
    backgroundColor: '#14385D',
  },
  tabLabel: {
    color: Theme.colors.tabInactive,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.emphasis,
  },
  activeTabLabel: {
    color: Theme.colors.textInverse,
  },
});
