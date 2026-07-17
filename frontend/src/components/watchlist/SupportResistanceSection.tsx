import {
  DetailGrid,
  InfoTile,
  ZoneSection,
} from '@/components/watchlist/WatchlistPrimitives';
import { StatusBadge } from '@/components/ui/StatusBadge';
import type { SupportResistanceResponse } from '@/types/market';
import { getSourceTone } from '@/utils/colors';
import { formatNullablePrice, formatSourceLabel, formatZones } from '@/utils/formatters';

export function SupportResistanceSection({
  supportResistance,
  showTitle = true,
}: {
  supportResistance?: SupportResistanceResponse;
  showTitle?: boolean;
}) {
  const content = (
    <DetailGrid>
      <InfoTile
        label="Support zones"
        value={formatZones(supportResistance?.support_zones)}
      />
      <InfoTile
        label="Resistance zones"
        value={formatZones(supportResistance?.resistance_zones)}
      />
      <InfoTile
        label="Breakout level"
        value={formatNullablePrice(supportResistance?.breakout_level)}
      />
      <InfoTile
        label="Stop reference"
        value={formatNullablePrice(supportResistance?.stop_reference)}
      />
      <InfoTile
        label="EMA20 support"
        value={formatNullablePrice(supportResistance?.moving_average_support.ema_20)}
      />
      <InfoTile
        label="EMA50 support"
        value={formatNullablePrice(supportResistance?.moving_average_support.ema_50)}
      />
    </DetailGrid>
  );

  if (!showTitle) {
    return content;
  }

  return (
    <ZoneSection
      title="Calculated Zones"
      titleAccessory={
        <StatusBadge
          label={formatSourceLabel(supportResistance)}
          tone={getSourceTone(supportResistance)}
        />
      }>
      {content}
    </ZoneSection>
  );
}
