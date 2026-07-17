import { NativeTabs } from 'expo-router/unstable-native-tabs';

import { Theme } from '@/constants/theme';

export default function AppTabs() {
  return (
    <NativeTabs
      backgroundColor={Theme.colors.tabBar}
      iconColor={Theme.colors.tabInactive}
      indicatorColor="#14385D"
      labelStyle={{
        default: { color: Theme.colors.tabInactive, fontSize: 11, fontWeight: '600' },
        selected: { color: Theme.colors.textInverse, fontSize: 11, fontWeight: '700' },
      }}>
      <NativeTabs.Trigger name="index">
        <NativeTabs.Trigger.Label>Home</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon sf={{ default: 'house', selected: 'house.fill' }} />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="market">
        <NativeTabs.Trigger.Label>Market</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon
          sf={{ default: 'chart.line.uptrend.xyaxis', selected: 'chart.line.uptrend.xyaxis' }}
        />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="sectors">
        <NativeTabs.Trigger.Label>Sectors</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon
          sf={{ default: 'square.grid.2x2', selected: 'square.grid.2x2.fill' }}
        />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="watchlist">
        <NativeTabs.Trigger.Label>Watchlist</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon sf={{ default: 'star', selected: 'star.fill' }} />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="more">
        <NativeTabs.Trigger.Label>More</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon sf={{ default: 'ellipsis.circle', selected: 'ellipsis.circle.fill' }} />
      </NativeTabs.Trigger>
    </NativeTabs>
  );
}
