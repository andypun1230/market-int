import { StyleSheet, Text, View } from 'react-native';

import {
  DetailGrid,
  InfoTile,
  SectionSummary,
  ZoneSection,
} from '@/components/watchlist/WatchlistPrimitives';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Spacing, Theme, Typography } from '@/constants/theme';
import type { MultiTimeframeItem } from '@/types/market';
import { getAlignmentColor } from '@/utils/colors';
import { formatNullableNumber, formatTimeframeTile } from '@/utils/formatters';

export function MultiTimeframeSection({
  multiTimeframe,
  showTitle = true,
}: {
  multiTimeframe?: MultiTimeframeItem;
  showTitle?: boolean;
}) {
  const alignmentColor = getAlignmentColor(multiTimeframe?.alignment);
  const content = (
    <>
      <View style={styles.alignmentBox}>
        <Text style={[styles.alignmentText, { color: alignmentColor }]}>
          {multiTimeframe?.alignment ?? 'N/A'}
        </Text>
      </View>
      <DetailGrid>
        <InfoTile
          label="Alignment"
          value={multiTimeframe?.alignment ?? 'N/A'}
          valueColor={alignmentColor}
        />
        <InfoTile
          label="Alignment Score"
          value={formatNullableNumber(multiTimeframe?.alignment_score)}
          valueColor={alignmentColor}
        />
        <InfoTile label="Weekly" value={formatTimeframeTile(multiTimeframe, 'Weekly')} />
        <InfoTile label="Daily" value={formatTimeframeTile(multiTimeframe, 'Daily')} />
        <InfoTile label="4H" value={formatTimeframeTile(multiTimeframe, '4H')} />
        <InfoTile label="1H" value={formatTimeframeTile(multiTimeframe, '1H')} />
      </DetailGrid>
      <SectionSummary>{multiTimeframe?.summary ?? 'N/A'}</SectionSummary>
    </>
  );

  if (!showTitle) {
    return content;
  }

  return (
    <ZoneSection
      title="Multi-Timeframe"
      titleAccessory={
        <View style={styles.badgeStack}>
          <Text style={[styles.scoreBadge, { color: alignmentColor }]}>
            {formatNullableNumber(multiTimeframe?.alignment_score)}
          </Text>
          <StatusBadge
            label={multiTimeframe?.is_live ? 'Live intraday' : 'Mock intraday'}
            tone={multiTimeframe?.is_live ? 'success' : 'muted'}
          />
        </View>
      }>
      {content}
    </ZoneSection>
  );
}

const styles = StyleSheet.create({
  scoreBadge: {
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
  },
  badgeStack: {
    alignItems: 'flex-end',
    gap: Spacing.one,
  },
  alignmentBox: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    padding: Spacing.twoAndHalf,
  },
  alignmentText: {
    fontSize: Typography.supportTitle.fontSize,
    fontWeight: Typography.weights.strong,
  },
});
