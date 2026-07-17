import { StatusBadge, type Tone } from '@/components/ui/StatusBadge';
import {
  DetailGrid,
  InfoTile,
  SectionSummary,
  ZoneSection,
} from '@/components/watchlist/WatchlistPrimitives';
import type { VolumeAnalysis } from '@/types/market';
import { getSourceTone } from '@/utils/colors';
import {
  formatBooleanSignal,
  formatNullableVolume,
  formatRelativeVolume,
  formatSourceLabel,
  formatSignals,
} from '@/utils/formatters';

export function VolumeSection({
  showTitle = true,
  volumeAnalysis,
}: {
  showTitle?: boolean;
  volumeAnalysis?: VolumeAnalysis;
}) {
  const content = (
    <>
      <StatusBadge
        label={volumeAnalysis?.volume_quality ?? 'Volume Quality N/A'}
        tone={getVolumeQualityTone(volumeAnalysis?.volume_quality)}
      />
      <DetailGrid>
        <InfoTile
          label="Average Volume 20"
          value={formatNullableVolume(volumeAnalysis?.average_volume_20)}
        />
        <InfoTile
          label="Relative Volume"
          value={formatRelativeVolume(volumeAnalysis?.relative_volume)}
        />
        <InfoTile label="Status" value={volumeAnalysis?.status ?? 'N/A'} />
        <InfoTile label="Volume Quality" value={volumeAnalysis?.volume_quality ?? 'N/A'} />
        <InfoTile label="Signals" value={formatSignals(volumeAnalysis?.signals)} />
        <InfoTile
          label="Accumulation Volume"
          value={formatBooleanSignal(volumeAnalysis?.accumulation_volume)}
        />
        <InfoTile
          label="Distribution Volume"
          value={formatBooleanSignal(volumeAnalysis?.distribution_volume)}
        />
        <InfoTile label="Dry-up" value={formatBooleanSignal(volumeAnalysis?.dry_up)} />
        <InfoTile label="Climax Run" value={formatBooleanSignal(volumeAnalysis?.climax_run)} />
      </DetailGrid>
      <SectionSummary>{volumeAnalysis?.summary ?? 'N/A'}</SectionSummary>
    </>
  );

  if (!showTitle) {
    return content;
  }

  return (
    <ZoneSection
      title="Volume Analysis"
      titleAccessory={
        <StatusBadge
          label={formatSourceLabel(volumeAnalysis)}
          tone={getSourceTone(volumeAnalysis)}
        />
      }>
      {content}
    </ZoneSection>
  );
}

function getVolumeQualityTone(quality?: string): Tone {
  switch (quality?.toLowerCase()) {
    case 'excellent':
    case 'strong':
      return 'success';
    case 'average':
      return 'info';
    case 'weak':
      return 'warning';
    case 'poor':
      return 'danger';
    default:
      return 'muted';
  }
}
