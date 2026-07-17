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

import { MaxContentWidth, Spacing, Theme } from '@/constants/theme';

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
    <Pressable {...props} style={({ pressed }) => pressed && styles.pressed}>
      <View style={[styles.tabButtonView, isFocused && styles.activeTab]}>
        <SymbolView tintColor={tintColor} name={{ web: icon.web, ios: icon.ios } as never} size={18} />
        <Text style={[styles.tabLabel, isFocused && styles.activeTabLabel]}>{children}</Text>
      </View>
    </Pressable>
  );
}

export function CustomTabList(props: TabListProps) {
  return (
    <View {...props} style={styles.tabListContainer}>
      <View style={styles.innerContainer}>{props.children}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  tabListContainer: {
    bottom: 0,
    position: 'absolute',
    width: '100%',
    padding: Spacing.two,
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
    maxWidth: MaxContentWidth,
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
    fontSize: 11,
    fontWeight: '700',
  },
  activeTabLabel: {
    color: Theme.colors.textInverse,
  },
});
