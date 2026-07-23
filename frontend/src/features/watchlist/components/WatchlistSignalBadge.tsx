import { StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme, Typography } from '@/constants/theme';
import { getSignalLabel, shouldShowWatchlistStatusDot } from '@/features/watchlist/watchlistClassifier';
import type { WatchlistClassification, WatchlistDataStatus, WatchlistSignalType } from '@/features/watchlist/types';

type WatchlistSignalBadgeProps = {
  classification: WatchlistClassification;
};

export function WatchlistSignalBadge({ classification }: WatchlistSignalBadgeProps) {
  const palette = getSignalPalette(classification.primarySignal, classification.dataStatus);
  return (
    <View
      accessibilityLabel={`${getSignalLabel(classification.primarySignal)} signal`}
      style={[styles.badge, { backgroundColor: palette.background, borderColor: palette.border }]}
    >
      <Text numberOfLines={1} style={[styles.text, { color: palette.text }]}>
        {getSignalLabel(classification.primarySignal)}
      </Text>
    </View>
  );
}

export function DataStatusDot({ primarySignal, status }: { primarySignal?: WatchlistSignalType; status: WatchlistDataStatus }) {
  if (!shouldShowWatchlistStatusDot(status, primarySignal)) {
    return null;
  }
  const label = status === 'test' ? 'Test Data' : status.charAt(0).toUpperCase() + status.slice(1);
  const palette = getDataStatusPalette(status);
  return (
    <View
      accessibilityLabel={`Data status ${label}`}
      style={[styles.statusDot, { backgroundColor: palette.background, borderColor: palette.border }]}
    >
      <Text style={[styles.statusText, { color: palette.text }]}>{label}</Text>
    </View>
  );
}

function getSignalPalette(signal: WatchlistSignalType, status: WatchlistDataStatus) {
  if (status === 'unavailable') {
    return getDataStatusPalette(status);
  }
  if (['breakout', 'near_breakout', 'new_high'].includes(signal)) {
    return {
      background: Theme.colors.accentSoft,
      border: Theme.colors.accent,
      text: Theme.colors.accent,
    };
  }
  if (['earnings_soon', 'major_news', 'rating_upgrade'].includes(signal)) {
    return {
      background: Theme.colors.purpleSoft,
      border: Theme.colors.purple,
      text: Theme.colors.purple,
    };
  }
  if (['strong_momentum', 'relative_strength', 'volume_surge'].includes(signal)) {
    return {
      background: '#0F3835',
      border: '#14B8A6',
      text: '#2DD4BF',
    };
  }
  if (['lost_ema', 'stale_data'].includes(signal)) {
    return {
      background: Theme.colors.warningSoft,
      border: Theme.colors.warning,
      text: Theme.colors.warning,
    };
  }
  if (['lost_support', 'weak_momentum', 'earnings_risk'].includes(signal)) {
    return {
      background: Theme.colors.dangerSoft,
      border: Theme.colors.danger,
      text: Theme.colors.danger,
    };
  }
  return {
    background: Theme.colors.cardMuted,
    border: Theme.colors.border,
    text: Theme.colors.textMuted,
  };
}

function getDataStatusPalette(status: WatchlistDataStatus) {
  if (status === 'unavailable') {
    return {
      background: Theme.colors.dangerSoft,
      border: Theme.colors.danger,
      text: Theme.colors.danger,
    };
  }
  if (status === 'stale') {
    return {
      background: Theme.colors.warningSoft,
      border: Theme.colors.warning,
      text: Theme.colors.warning,
    };
  }
  if (status === 'pending' || status === 'partial') {
    return {
      background: Theme.colors.accentSoft,
      border: Theme.colors.accent,
      text: Theme.colors.accent,
    };
  }
  return {
    background: Theme.colors.cardMuted,
    border: Theme.colors.border,
    text: Theme.colors.textMuted,
  };
}

const styles = StyleSheet.create({
  badge: {
    alignItems: 'center',
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    maxWidth: 136,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.one,
  },
  statusDot: {
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    paddingHorizontal: Spacing.one,
    paddingVertical: Spacing.half,
  },
  statusText: {
    fontSize: Typography.chartAxis.fontSize,
    fontWeight: Typography.weights.strong,
  },
  text: {
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
  },
});
