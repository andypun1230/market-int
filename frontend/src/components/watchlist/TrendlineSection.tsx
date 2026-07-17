import {
  DetailGrid,
  InfoTile,
  SectionSummary,
  ZoneSection,
} from '@/components/watchlist/WatchlistPrimitives';
import { StatusBadge } from '@/components/ui/StatusBadge';
import type { TrendlineResponse } from '@/types/market';
import { getSourceTone } from '@/utils/colors';
import {
  formatDetected,
  formatNullableNumber,
  formatNullablePercent,
  formatSourceLabel,
  formatTrendlineBreak,
} from '@/utils/formatters';

export function TrendlineSection({
  showTitle = true,
  trendline,
}: {
  showTitle?: boolean;
  trendline?: TrendlineResponse;
}) {
  const content = (
    <>
      <DetailGrid>
        <InfoTile
          label="Rising support"
          value={formatDetected(trendline?.rising_support.detected)}
        />
        <InfoTile
          label="Support status"
          value={trendline?.rising_support.status ?? 'N/A'}
        />
        <InfoTile
          label="Touch count"
          value={formatNullableNumber(trendline?.rising_support.touch_count)}
        />
        <InfoTile
          label="Distance"
          value={formatNullablePercent(trendline?.rising_support.distance_percent)}
        />
        <InfoTile
          label="Falling resistance"
          value={formatDetected(trendline?.falling_resistance.detected)}
        />
        <InfoTile
          label="Resistance status"
          value={trendline?.falling_resistance.status ?? 'N/A'}
        />
        <InfoTile
          label="Break status"
          value={formatTrendlineBreak(trendline?.trendline_break)}
        />
      </DetailGrid>
      <SectionSummary>{trendline?.summary ?? 'N/A'}</SectionSummary>
    </>
  );

  if (!showTitle) {
    return content;
  }

  return (
    <ZoneSection
      title="Trendline"
      titleAccessory={
        <StatusBadge
          label={formatSourceLabel(trendline)}
          tone={getSourceTone(trendline)}
        />
      }>
      {content}
    </ZoneSection>
  );
}
