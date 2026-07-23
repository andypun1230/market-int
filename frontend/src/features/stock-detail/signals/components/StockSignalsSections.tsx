import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { AppIcon } from '@/components/ui/AppIcon';
import { StatusBadge, type Tone } from '@/components/ui/StatusBadge';
import { DetailGrid, InfoTile } from '@/components/watchlist/WatchlistPrimitives';
import { Spacing, Theme, Typography } from '@/constants/theme';
import { MultiTimeframeTrend } from '@/features/stock-detail/technical/components/StockTechnicalSections';
import {
  buildSignalSummary,
  classifyComparison,
  comparisonLabel,
  formatLeadershipSignal,
  getActiveVolumeSignals,
  getVolumeParticipationState,
  leadershipPreview,
  relativeStrengthInterpretation,
  volumeInterpretation,
  volumeStateLabel,
} from '@/features/stock-detail/signals/signalPresenter';
import type {
  MultiTimeframeTechnicalSignals,
  RelativeStrengthItem,
  StockLeadershipSignal,
  VolumeAnalysis,
} from '@/types/market';
import { getSourceTone } from '@/utils/colors';
import {
  formatNullableNumber,
  formatNullablePercent,
  formatRelativeVolume,
  formatSourceLabel,
} from '@/utils/formatters';
import { formatLocalizedDateTime } from '@/features/trust/dateFreshnessPresentation';

type StockSignalsSectionsProps = {
  leadershipSignal?: StockLeadershipSignal;
  multiTimeframeSignals?: MultiTimeframeTechnicalSignals | null;
  relativeStrength?: RelativeStrengthItem;
  volumeAnalysis?: VolumeAnalysis;
};

export function StockSignalsSections({
  leadershipSignal,
  multiTimeframeSignals,
  relativeStrength,
  volumeAnalysis,
}: StockSignalsSectionsProps) {
  const summary = useMemo(
    () => buildSignalSummary({
      leadership: leadershipSignal,
      relativeStrength,
      timeframeSignals: multiTimeframeSignals,
      volume: volumeAnalysis,
    }),
    [leadershipSignal, multiTimeframeSignals, relativeStrength, volumeAnalysis],
  );

  return (
    <View style={styles.sections}>
      <SignalSurface>
        <Text style={styles.sectionTitle}>Market Signals</Text>
        <SignalSummary headline={summary.headline} body={summary.body} />
        <SignalDivider />
        <LeadershipSignalPanel leadershipSignal={leadershipSignal} />
        <SignalDivider />
        <MultiTimeframeTrend embedded signals={multiTimeframeSignals} />
        <SignalDivider />
        <RelativeStrengthPanel relativeStrength={relativeStrength} />
        <SignalDivider />
        <VolumeParticipationPanel volumeAnalysis={volumeAnalysis} />
      </SignalSurface>
      <SupportingSignalDetails
        leadershipSignal={leadershipSignal}
        multiTimeframeSignals={multiTimeframeSignals}
        relativeStrength={relativeStrength}
        volumeAnalysis={volumeAnalysis}
      />
    </View>
  );
}

function SignalSummary({ body, headline }: { body: string; headline: string }) {
  return (
    <View style={styles.embeddedSection}>
      <Text style={styles.summaryHeadline}>{headline}</Text>
      <Text style={styles.bodyText}>{body}</Text>
    </View>
  );
}

function RelativeStrengthPanel({ relativeStrength }: { relativeStrength?: RelativeStrengthItem }) {
  const comparisons = [
    { label: 'Overall RS', value: relativeStrength?.overall_rs_score },
    { label: 'SPY', value: relativeStrength?.rs_vs_spy },
    { label: 'QQQ', value: relativeStrength?.rs_vs_qqq },
    { label: 'Sector', value: relativeStrength?.rs_vs_sector },
  ];
  return (
    <View style={styles.embeddedSection}>
      <SectionHeader
        title="Relative Strength"
        badgeLabel={formatSourceLabel(relativeStrength)}
        badgeTone={getSourceTone(relativeStrength)}
      />
      <View style={styles.heroMetricRow}>
        <View style={styles.heroCopy}>
          <Text style={styles.heroLabel}>{relativeStrength?.status ?? 'Unavailable'}</Text>
          <Text style={styles.bodyText}>{relativeStrengthInterpretation(relativeStrength)}</Text>
        </View>
        <View style={styles.heroScorePill}>
          <Text style={styles.heroScore}>{formatScore(relativeStrength?.overall_rs_score)}</Text>
        </View>
      </View>
      <View style={styles.comparisonStack}>
        {comparisons.map((comparison) => (
          <ComparisonBar key={comparison.label} label={comparison.label} value={comparison.value} />
        ))}
      </View>
    </View>
  );
}

function ComparisonBar({ label, value }: { label: string; value?: number | null }) {
  const bounded = typeof value === 'number' ? Math.max(0, Math.min(100, value)) : 0;
  const strength = classifyComparison(value);
  return (
    <View style={styles.comparisonRow}>
      <View style={styles.comparisonTopRow}>
        <Text style={styles.comparisonLabel}>{label}</Text>
        <Text style={styles.comparisonValue}>
          {value == null ? 'N/A' : `${Math.round(value)}`} · {comparisonLabel(strength)}
        </Text>
      </View>
      <View style={styles.barTrack}>
        <View style={styles.neutralMarker} />
        <View
          style={[
            styles.barFill,
            { width: `${bounded}%`, backgroundColor: comparisonColor(strength) },
          ]}
        />
      </View>
    </View>
  );
}

function VolumeParticipationPanel({ volumeAnalysis }: { volumeAnalysis?: VolumeAnalysis }) {
  const state = getVolumeParticipationState(volumeAnalysis);
  const activeSignals = getActiveVolumeSignals(volumeAnalysis);
  return (
    <View style={styles.embeddedSection}>
      <SectionHeader
        title="Volume Participation"
        badgeLabel={formatSourceLabel(volumeAnalysis)}
        badgeTone={getSourceTone(volumeAnalysis)}
      />
      <View style={styles.heroMetricRow}>
        <View style={styles.heroCopy}>
          <Text style={styles.heroLabel}>{volumeStateLabel(state)}</Text>
          <Text style={styles.bodyText}>{formatRelativeVolume(volumeAnalysis?.relative_volume)} normal volume</Text>
        </View>
        <View style={styles.heroScorePill}>
          <Text style={styles.heroScore}>{formatScore(volumeAnalysis?.volume_quality_score)}</Text>
        </View>
      </View>
      <ParticipationMeter state={state} />
      {activeSignals.length ? (
        <View style={styles.signalChipRow}>
          {activeSignals.map((signal) => (
            <StatusBadge key={signal} label={signal} tone={volumeSignalTone(signal)} />
          ))}
        </View>
      ) : (
        <Text style={styles.emptyText}>No active volume condition is confirmed.</Text>
      )}
      <Text style={styles.bodyText}>{volumeInterpretation(volumeAnalysis)}</Text>
    </View>
  );
}

function ParticipationMeter({ state }: { state: ReturnType<typeof getVolumeParticipationState> }) {
  const states: ReturnType<typeof getVolumeParticipationState>[] = ['weak', 'below_average', 'average', 'strong', 'exceptional'];
  const activeIndex = states.indexOf(state);
  return (
    <View accessibilityLabel={`Volume participation is ${volumeStateLabel(state)}`} style={styles.segmentStack}>
      <View style={styles.segmentRow}>
        {states.map((item, index) => (
          <View
            key={item}
            style={[
              styles.segment,
              index <= activeIndex && state !== 'unavailable'
                ? { backgroundColor: participationColor(item) }
                : null,
            ]}
          />
        ))}
      </View>
      <View style={styles.segmentLabelRow}>
        <Text style={styles.segmentLabel}>Weak</Text>
        <Text style={styles.segmentLabel}>Strong</Text>
      </View>
    </View>
  );
}

function LeadershipSignalPanel({ leadershipSignal }: { leadershipSignal?: StockLeadershipSignal }) {
  return (
    <View style={styles.embeddedSection}>
      <SectionHeader
        title="Leadership Signal"
        badgeLabel={leadershipSignal?.dataStatus ? formatDataStatus(leadershipSignal.dataStatus) : 'Unavailable'}
        badgeTone={dataStatusTone(leadershipSignal?.dataStatus)}
      />
      <View style={styles.heroMetricRow}>
        <View style={styles.heroCopy}>
          <Text style={styles.heroLabel}>{formatLeadershipSignal(leadershipSignal?.signal)}</Text>
          <Text style={styles.bodyText}>{compactSentence(leadershipSignal?.explanation ?? 'Leadership signal is unavailable.')}</Text>
        </View>
        <View style={styles.heroScorePill}>
          <Text style={styles.heroScore}>{formatScore(leadershipSignal?.score)}</Text>
        </View>
      </View>
      <EvidenceList
        positive={leadershipSignal?.positiveEvidence ?? []}
        limiting={leadershipSignal?.limitingEvidence ?? []}
      />
    </View>
  );
}

function SupportingSignalDetails(props: StockSignalsSectionsProps) {
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const toggle = (key: string) => setOpen((current) => ({ ...current, [key]: !current[key] }));
  return (
    <View style={styles.disclosurePanel}>
      <Text style={styles.sectionTitle}>Supporting Signal Details</Text>
      <Text style={styles.bodyText}>Advanced diagnostics</Text>
      <DiagnosticsRow
        expanded={Boolean(open.rs)}
        label="Relative Strength Metrics"
        onPress={() => toggle('rs')}
        preview={`Overall ${formatNullableNumber(props.relativeStrength?.overall_rs_score)} · SPY ${formatNullableNumber(props.relativeStrength?.rs_vs_spy)} · QQQ ${formatNullableNumber(props.relativeStrength?.rs_vs_qqq)} · Sector ${formatNullableNumber(props.relativeStrength?.rs_vs_sector)}`}
      />
      {open.rs ? (
        <DetailGrid>
          <InfoTile label="Status" value={props.relativeStrength?.status ?? 'N/A'} />
          <InfoTile label="Rank" value={formatNullableNumber(props.relativeStrength?.rank)} />
          <InfoTile label="Universe" value="Watchlist comparison" />
          <InfoTile label="Sector" value={props.relativeStrength?.sector ?? 'N/A'} />
        </DetailGrid>
      ) : null}
      <DiagnosticsRow
        expanded={Boolean(open.returns)}
        label="Return Windows"
        onPress={() => toggle('returns')}
        preview={`20D ${formatNullablePercent(props.relativeStrength?.return_20d)} · 60D ${formatNullablePercent(props.relativeStrength?.return_60d)}`}
      />
      {open.returns ? (
        <DetailGrid>
          <InfoTile label="5D Return" value={formatNullablePercent(props.relativeStrength?.return_5d)} />
          <InfoTile label="20D Return" value={formatNullablePercent(props.relativeStrength?.return_20d)} />
          <InfoTile label="60D Return" value={formatNullablePercent(props.relativeStrength?.return_60d)} />
          <InfoTile label="Benchmark 20D" value={formatNullablePercent(props.relativeStrength?.benchmark_return_20d)} />
          <InfoTile label="Sector 20D" value={formatNullablePercent(props.relativeStrength?.sector_return_20d)} />
        </DetailGrid>
      ) : null}
      <DiagnosticsRow
        expanded={Boolean(open.volume)}
        label="Volume Diagnostics"
        onPress={() => toggle('volume')}
        preview={`Relative volume ${formatRelativeVolume(props.volumeAnalysis?.relative_volume)} · ${props.volumeAnalysis?.accumulation_volume ? 'Accumulation present' : 'No accumulation flag'}`}
      />
      {open.volume ? (
        <DetailGrid>
          <InfoTile label="Average Volume 20" value={formatNullableNumber(props.volumeAnalysis?.average_volume_20)} />
          <InfoTile label="Status" value={props.volumeAnalysis?.status ?? 'N/A'} />
          <InfoTile label="Quality" value={props.volumeAnalysis?.volume_quality ?? 'N/A'} />
          <InfoTile label="Breakout Volume" value={formatBoolean(props.volumeAnalysis?.breakout_volume)} />
          <InfoTile label="Accumulation" value={formatBoolean(props.volumeAnalysis?.accumulation_volume)} />
          <InfoTile label="Distribution" value={formatBoolean(props.volumeAnalysis?.distribution_volume)} />
          <InfoTile label="Dry-Up" value={formatBoolean(props.volumeAnalysis?.dry_up)} />
          <InfoTile label="Climax Run" value={formatBoolean(props.volumeAnalysis?.climax_run)} />
        </DetailGrid>
      ) : null}
      <DiagnosticsRow
        expanded={Boolean(open.leadership)}
        label="Leadership Inputs"
        onPress={() => toggle('leadership')}
        preview={leadershipPreview(props.leadershipSignal)}
      />
      {open.leadership ? (
        <DetailGrid>
          <InfoTile label="Signal" value={formatLeadershipSignal(props.leadershipSignal?.signal)} />
          <InfoTile label="Score" value={formatScore(props.leadershipSignal?.score)} />
          <InfoTile label="Inputs" value={`${props.leadershipSignal?.availableInputs ?? 0}/${props.leadershipSignal?.requiredInputs ?? 0}`} />
          <InfoTile label="Methodology" value={props.leadershipSignal?.methodologyVersion ?? 'N/A'} />
        </DetailGrid>
      ) : null}
      <DiagnosticsRow
        expanded={Boolean(open.timeframes)}
        label="Multi-Timeframe Signal Inputs"
        onPress={() => toggle('timeframes')}
        preview={timeframePreview(props.multiTimeframeSignals)}
      />
      {open.timeframes ? (
        <DetailGrid>
          {timeframeTiles(props.multiTimeframeSignals).map((tile) => (
            <InfoTile key={tile.label} label={tile.label} value={tile.value} />
          ))}
        </DetailGrid>
      ) : null}
      <DiagnosticsRow
        expanded={Boolean(open.source)}
        label="Methodology and Data Source"
        onPress={() => toggle('source')}
        preview={`RS ${formatSourceLabel(props.relativeStrength)} · Volume ${formatSourceLabel(props.volumeAnalysis)}`}
      />
      {open.source ? (
        <DetailGrid>
          <InfoTile label="RS Source" value={formatSourceLabel(props.relativeStrength)} />
          <InfoTile label="Volume Source" value={formatSourceLabel(props.volumeAnalysis)} />
          <InfoTile label="Leadership Source" value={props.leadershipSignal?.dataStatus ? formatDataStatus(props.leadershipSignal.dataStatus) : 'Unavailable'} />
          <InfoTile label="Timeframe Source" value={props.multiTimeframeSignals?.overallDataStatus ? formatDataStatus(props.multiTimeframeSignals.overallDataStatus) : 'Unavailable'} />
          <InfoTile label="Timeframe Method" value={props.multiTimeframeSignals?.methodologyVersion ?? 'N/A'} />
          <InfoTile label="Generated" value={props.multiTimeframeSignals?.generatedAt ? formatLocalizedDateTime(props.multiTimeframeSignals.generatedAt) : 'Unavailable'} />
        </DetailGrid>
      ) : null}
    </View>
  );
}

function SignalDivider() {
  return <View style={styles.signalDivider} />;
}

function EvidenceList({ limiting, positive }: { limiting: string[]; positive: string[] }) {
  const rows = [
    ...positive.slice(0, 2).map((item) => ({ icon: 'check' as const, item, tone: 'success' as Tone })),
    ...limiting.slice(0, 2).map((item) => ({ icon: 'pending' as const, item, tone: 'warning' as Tone })),
  ];
  if (!rows.length) {
    return <Text style={styles.emptyText}>No leadership evidence is available.</Text>;
  }
  return (
    <View style={styles.evidenceStack}>
      {rows.map((row) => (
        <View key={`${row.icon}-${row.item}`} style={styles.evidenceRow}>
          <AppIcon color={row.tone === 'success' ? Theme.colors.success : Theme.colors.warning} name={row.icon} size={13} />
          <Text style={[styles.evidenceText, { color: row.tone === 'success' ? Theme.colors.success : Theme.colors.warning }]}>{row.item}</Text>
        </View>
      ))}
    </View>
  );
}

function SectionHeader({ badgeLabel, badgeTone, title }: { badgeLabel: string; badgeTone: Tone; title: string }) {
  return (
    <View style={styles.sectionHeaderRow}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <StatusBadge label={badgeLabel} tone={badgeTone} />
    </View>
  );
}

function DiagnosticsRow({
  expanded,
  label,
  onPress,
  preview,
}: {
  expanded: boolean;
  label: string;
  onPress: () => void;
  preview: string;
}) {
  return (
    <Pressable accessibilityRole="button" accessibilityState={{ expanded }} onPress={onPress} style={styles.diagnosticsRow}>
      <View style={styles.diagnosticsText}>
        <Text style={styles.diagnosticsLabel}>{label}</Text>
        <Text style={styles.diagnosticsPreview}>{preview}</Text>
      </View>
      <AppIcon name={expanded ? 'chevronDown' : 'chevronRight'} size={17} />
    </Pressable>
  );
}

function SignalSurface({ children }: { children: React.ReactNode }) {
  return <View style={styles.surface}>{children}</View>;
}

function timeframePreview(signals?: MultiTimeframeTechnicalSignals | null): string {
  if (!signals) {
    return 'No signal inputs';
  }
  return [signals.short, signals.medium, signals.long]
    .map((signal) => `${displayTimeframe(signal.timeframe)} ${signal.availableInputs}/${signal.requiredInputs}`)
    .join(' · ');
}

function timeframeTiles(signals?: MultiTimeframeTechnicalSignals | null): { label: string; value: string }[] {
  if (!signals) {
    return [{ label: 'Inputs', value: 'Unavailable' }];
  }
  return [signals.short, signals.medium, signals.long].flatMap((signal) => [
    {
      label: displayTimeframe(signal.timeframe),
      value: `${formatSignal(signal.signal)} · ${signal.score == null ? 'No score' : `${signal.score}/100`} · ${signal.availableInputs}/${signal.requiredInputs} inputs`,
    },
    ...(signal.inputs ?? []).map((input) => ({
      label: `${displayTimeframe(signal.timeframe)} · ${input.label}`,
      value: [
        input.available ? 'Available' : 'Unavailable',
        input.value == null ? null : `${input.value}`,
        input.contribution == null ? null : `Contribution ${input.contribution}`,
        input.sourceStatus ? formatDataStatus(input.sourceStatus) : null,
      ].filter(Boolean).join(' · '),
    })),
  ]);
}

function displayTimeframe(value: string): string {
  if (value === 'short') {
    return 'Short';
  }
  if (value === 'medium') {
    return 'Medium';
  }
  return 'Long';
}

function formatSignal(value: string): string {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatScore(value?: number | null): string {
  return value == null ? 'N/A' : `${Math.round(value)} / 100`;
}

function compactSentence(value: string): string {
  const stops = ['.', '!', '?']
    .map((character) => value.indexOf(character))
    .filter((index) => index >= 0);
  const firstStop = stops.length ? Math.min(...stops) : -1;
  const firstSentence = firstStop >= 0 ? value.slice(0, firstStop + 1) : value;
  return firstSentence.length > 118 ? `${firstSentence.slice(0, 115).trim()}…` : firstSentence;
}

function formatBoolean(value?: boolean | null): string {
  if (value == null) {
    return 'N/A';
  }
  return value ? 'Yes' : 'No';
}

function formatDataStatus(value?: string | null): string {
  if (!value) {
    return 'Unavailable';
  }
  if (value === 'test') {
    return 'Test Data';
  }
  return value.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function comparisonColor(strength: ReturnType<typeof classifyComparison>): string {
  if (strength === 'strongly_stronger' || strength === 'stronger') {
    return Theme.colors.success;
  }
  if (strength === 'in_line') {
    return Theme.colors.accent;
  }
  if (strength === 'weaker') {
    return Theme.colors.warning;
  }
  if (strength === 'strongly_weaker') {
    return Theme.colors.danger;
  }
  return Theme.colors.border;
}

function participationColor(state: ReturnType<typeof getVolumeParticipationState>): string {
  if (state === 'exceptional' || state === 'strong') {
    return Theme.colors.success;
  }
  if (state === 'average') {
    return Theme.colors.accent;
  }
  if (state === 'below_average') {
    return Theme.colors.warning;
  }
  if (state === 'weak') {
    return Theme.colors.danger;
  }
  return Theme.colors.border;
}

function volumeSignalTone(signal: string): Tone {
  if (signal.includes('Distribution') || signal.includes('Climax')) {
    return 'warning';
  }
  if (signal.includes('dry-up')) {
    return 'muted';
  }
  return 'success';
}

function dataStatusTone(status?: string | null): Tone {
  const normalized = status?.toLowerCase();
  if (normalized === 'live' || normalized === 'cached') {
    return 'success';
  }
  if (normalized === 'mixed' || normalized === 'partial') {
    return 'info';
  }
  if (normalized === 'fallback' || normalized === 'stale') {
    return 'warning';
  }
  return 'muted';
}

const styles = StyleSheet.create({
  barFill: {
    borderRadius: Theme.radii.pill,
    height: '100%',
  },
  barTrack: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderRadius: Theme.radii.pill,
    height: 8,
    overflow: 'hidden',
    position: 'relative',
  },
  bodyText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.control.fontSize,
    lineHeight: 18,
  },
  chevron: {
    color: Theme.colors.textMuted,
    fontSize: Typography.sectionTitle.fontSize,
    fontWeight: Typography.weights.strong,
  },
  comparisonLabel: {
    color: Theme.colors.text,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
  },
  comparisonRow: {
    gap: Spacing.one,
  },
  comparisonStack: {
    gap: Spacing.two,
  },
  comparisonTopRow: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  comparisonValue: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.emphasis,
  },
  diagnosticsLabel: {
    color: Theme.colors.text,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
  },
  diagnosticsPreview: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    lineHeight: 17,
  },
  diagnosticsRow: {
    alignItems: 'center',
    borderTopColor: Theme.colors.border,
    borderTopWidth: 1,
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
    minHeight: 48,
    paddingVertical: Spacing.two,
  },
  diagnosticsText: {
    flex: 1,
    gap: 2,
  },
  disclosurePanel: {
    gap: Spacing.one,
    paddingHorizontal: Spacing.one,
  },
  embeddedSection: {
    gap: Spacing.two,
  },
  emptyText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    fontStyle: 'italic',
  },
  evidenceStack: {
    gap: Spacing.one,
  },
  evidenceRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.one,
  },
  evidenceText: {
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 18,
  },
  heroLabel: {
    color: Theme.colors.text,
    fontSize: Typography.cardTitle.fontSize,
    fontWeight: Typography.weights.strong,
  },
  heroCopy: {
    flex: 1,
    minWidth: 0,
  },
  heroMetricRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  heroScorePill: {
    alignItems: 'center',
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    justifyContent: 'center',
    minWidth: 48,
    paddingHorizontal: Spacing.two,
    paddingVertical: 4,
  },
  heroScore: {
    color: Theme.colors.text,
    fontSize: Typography.bodyLarge.fontSize,
    fontWeight: Typography.weights.strong,
    textAlign: 'center',
  },
  neutralMarker: {
    backgroundColor: Theme.colors.textMuted,
    height: '100%',
    left: '50%',
    opacity: 0.45,
    position: 'absolute',
    width: 1,
    zIndex: 1,
  },
  sectionHeaderRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  sections: {
    gap: Spacing.three,
  },
  sectionTitle: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: Typography.cardTitle.fontSize,
    fontWeight: Typography.weights.strong,
  },
  signalDivider: {
    backgroundColor: Theme.colors.border,
    height: 1,
  },
  segment: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderRadius: Theme.radii.small,
    flex: 1,
    height: 9,
  },
  segmentLabel: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.emphasis,
  },
  segmentLabelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  segmentRow: {
    flexDirection: 'row',
    gap: Spacing.one,
  },
  segmentStack: {
    gap: Spacing.one,
  },
  signalChipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.one,
  },
  summaryHeadline: {
    color: Theme.colors.text,
    fontSize: Typography.bodyLarge.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 20,
  },
  surface: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.card,
    borderWidth: 1,
    gap: Spacing.two,
    padding: Spacing.three,
  },
});
