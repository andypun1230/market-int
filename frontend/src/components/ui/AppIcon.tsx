import { SymbolView } from 'expo-symbols';
import { View } from 'react-native';
import type { ColorValue } from 'react-native';

import { Theme } from '@/constants/theme';

export type AppIconName =
  | 'add'
  | 'back'
  | 'chevronDown'
  | 'chevronRight'
  | 'chevronUp'
  | 'check'
  | 'close'
  | 'compactList'
  | 'compare'
  | 'filter'
  | 'info'
  | 'neutralDot'
  | 'pending'
  | 'refresh'
  | 'remove'
  | 'saved'
  | 'savedOutline'
  | 'search'
  | 'sparkles'
  | 'warning';

const ICONS: Record<AppIconName, { android: string; ios: string; web: string }> = {
  add: { android: 'add', ios: 'plus', web: 'add' },
  back: { android: 'arrow_back', ios: 'chevron.left', web: 'arrow_back' },
  chevronDown: { android: 'expand_more', ios: 'chevron.down', web: 'expand_more' },
  chevronRight: { android: 'chevron_right', ios: 'chevron.right', web: 'chevron_right' },
  chevronUp: { android: 'expand_less', ios: 'chevron.up', web: 'expand_less' },
  check: { android: 'check', ios: 'checkmark', web: 'check' },
  close: { android: 'close', ios: 'xmark', web: 'close' },
  compactList: { android: 'view_headline', ios: 'list.bullet', web: 'view_headline' },
  compare: { android: 'compare_arrows', ios: 'arrow.left.arrow.right', web: 'compare_arrows' },
  filter: { android: 'tune', ios: 'slider.horizontal.3', web: 'tune' },
  info: { android: 'info', ios: 'info.circle', web: 'info' },
  neutralDot: { android: 'circle', ios: 'circle.fill', web: 'circle' },
  pending: { android: 'radio_button_unchecked', ios: 'circle', web: 'radio_button_unchecked' },
  refresh: { android: 'refresh', ios: 'arrow.clockwise', web: 'refresh' },
  remove: { android: 'remove', ios: 'minus', web: 'remove' },
  saved: { android: 'star', ios: 'star.fill', web: 'star' },
  savedOutline: { android: 'star_outline', ios: 'star', web: 'star_outline' },
  search: { android: 'search', ios: 'magnifyingglass', web: 'search' },
  sparkles: { android: 'auto_awesome', ios: 'sparkles', web: 'auto_awesome' },
  warning: { android: 'warning', ios: 'exclamationmark.triangle.fill', web: 'warning' },
};

export function AppIcon({ color = Theme.colors.textMuted, name, size = 16 }: { color?: ColorValue; name: AppIconName; size?: number }) {
  return (
    <View accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      <SymbolView name={ICONS[name] as never} size={size} tintColor={color} weight="bold" />
    </View>
  );
}
