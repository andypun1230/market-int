import { useState } from 'react';
import type { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { MiniCandlestickChart } from '@/components/charts/MiniCandlestickChart';
import { DashboardCard } from '@/components/cards/DashboardCard';
import { ScoreGauge } from '@/components/ui/ScoreGauge';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';
import type { DetectedPattern, PatternKeyLevels } from '@/types/market';

type PatternCardProps = {
  defaultExpanded?: boolean;
  embedded?: boolean;
  pattern: DetectedPattern;
};

type TradePlan = {
  entry: string;
  stopLoss: string;
  targetOne: string;
  targetTwo: string;
  riskReward: string;
};

export function PatternCard({
  defaultExpanded = false,
  embedded = false,
  pattern,
}: PatternCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const accentColor = pattern.direction === 'bullish' ? Theme.colors.success : Theme.colors.warning;
  const confidence = getSafeConfidence(pattern.confidence);
  const tradePlan = buildTradePlan(pattern.key_levels);
  const candleCount = pattern.chart_data?.slice(-30).length ?? 0;
  const content = (
    <>
      <View style={styles.header}>
        <View style={styles.titleBlock}>
          <Text style={styles.symbol}>{pattern.symbol}</Text>
          <Text style={styles.patternName}>{pattern.name}</Text>
        </View>
        <ConfidenceBadge confidence={confidence} />
      </View>

      <View style={styles.metaRow}>
        <MetaPill label={formatTitle(pattern.direction)} tone="success" />
        <MetaPill label={formatTitle(pattern.status)} />
        <MetaPill label={pattern.is_live ? 'Live pattern' : 'Mock pattern'} />
        {expanded ? <MetaPill label={pattern.timeframe || 'Daily'} /> : null}
      </View>

      <Pressable
        accessibilityRole="button"
        accessibilityState={{ expanded }}
        onPress={() => setExpanded((current) => !current)}
        style={styles.detailsButton}>
        <Text style={styles.detailsButtonText}>
          {expanded ? 'Hide Pattern Details' : 'View Pattern Details'}
        </Text>
        <Text style={styles.detailsChevron}>{expanded ? '▾' : '▸'}</Text>
      </Pressable>

      {expanded ? (
        <>
          <Text style={styles.description}>{pattern.description}</Text>

          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Pattern Analysis</Text>
            <Text style={styles.sectionHint}>Candles, volume, EMA20/EMA50, and key levels</Text>
          </View>

          <MiniCandlestickChart
            candles={pattern.chart_data ?? []}
            height={246}
            keyLevels={pattern.key_levels}
            markers={pattern.markers ?? []}
          />

          {pattern.volume_confirmation ? (
            <AnalysisSection title="Volume Confirmation">
              <View style={styles.statsGrid}>
                <MetricTile
                  label="Relative Volume"
                  value={formatRelativeVolume(pattern.volume_confirmation.relative_volume)}
                />
                <MetricTile
                  label="Volume Quality"
                  value={pattern.volume_confirmation.volume_quality || 'N/A'}
                />
                <MetricTile
                  label="Signals"
                  value={formatSignals(pattern.volume_confirmation.signals)}
                />
              </View>
            </AnalysisSection>
          ) : null}

          <AnalysisSection title="Key Levels">
            <View style={styles.levelGrid}>
              {Object.entries(formatKeyLevels(pattern.key_levels)).map(([label, value]) => (
                <MetricTile key={label} label={label} value={value} />
              ))}
            </View>
          </AnalysisSection>

          <AnalysisSection title="Trade Plan Example">
            <View style={styles.planGrid}>
              <MetricTile label="Entry" value={tradePlan.entry} />
              <MetricTile label="Stop Loss" value={tradePlan.stopLoss} />
              <MetricTile label="Target 1" value={tradePlan.targetOne} />
              <MetricTile label="Target 2" value={tradePlan.targetTwo} />
            </View>
            <View style={styles.riskRewardBox}>
              <Text style={styles.riskRewardLabel}>Risk / Reward</Text>
              <Text style={styles.riskRewardValue}>{tradePlan.riskReward}</Text>
            </View>
          </AnalysisSection>

          <AnalysisSection title="Pattern Stats">
            <View style={styles.statsGrid}>
              <MetricTile label="Type" value={formatTitle(pattern.type)} />
              <MetricTile label="Direction" value={formatTitle(pattern.direction)} />
              <MetricTile label="Timeframe" value={pattern.timeframe || 'Daily'} />
              <MetricTile label="Candles Shown" value={String(candleCount)} />
              <MetricTile label="Status" value={formatTitle(pattern.status)} />
            </View>
          </AnalysisSection>

          <View style={styles.disclaimer}>
            <Text style={styles.disclaimerText}>Educational analysis only. Not financial advice.</Text>
          </View>
        </>
      ) : null}
    </>
  );

  if (embedded) {
    return <View style={[styles.embeddedCard, { borderLeftColor: accentColor }]}>{content}</View>;
  }

  return (
    <DashboardCard accentColor={accentColor}>
      {content}
    </DashboardCard>
  );
}

function ConfidenceBadge({ confidence }: { confidence: number | null }) {
  return (
    <ScoreGauge label="Confidence" size="small" value={confidence} />
  );
}

function MetaPill({ label, tone }: { label: string; tone?: 'success' }) {
  return <StatusBadge label={label} tone={tone === 'success' ? 'success' : 'muted'} />;
}

function AnalysisSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <View style={styles.analysisSection}>
      <Text style={styles.analysisTitle}>{title}</Text>
      {children}
    </View>
  );
}

function MetricTile({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.metricTile}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>{value}</Text>
    </View>
  );
}

function formatKeyLevels(levels?: PatternKeyLevels) {
  return {
    Support: formatNullablePrice(levels?.support),
    Neckline: formatNullablePrice(levels?.neckline),
    Breakout: formatNullablePrice(levels?.breakout),
    'Stop Reference': formatNullablePrice(levels?.stop_reference),
  };
}

function buildTradePlan(levels?: PatternKeyLevels): TradePlan {
  const entry = levels?.breakout ?? levels?.neckline ?? null;
  const support = levels?.support ?? null;
  const stop = levels?.stop_reference ?? null;
  const measuredMove = entry !== null && support !== null ? Math.max(entry - support, 0) : null;
  const targetOne = entry !== null && measuredMove !== null ? entry + measuredMove : null;
  const targetTwo = entry !== null && measuredMove !== null ? entry + measuredMove * 2 : null;
  const risk = entry !== null && stop !== null ? Math.max(entry - stop, 0) : null;
  const reward = entry !== null && targetOne !== null ? targetOne - entry : null;
  const riskReward =
    risk !== null && risk > 0 && reward !== null
      ? `${(reward / risk).toFixed(1)}:1 example`
      : 'Example only';

  return {
    entry: entry === null ? 'Above breakout/neckline' : `Above ${formatNullablePrice(entry)}`,
    stopLoss: stop === null ? 'Below stop reference' : `Below ${formatNullablePrice(stop)}`,
    targetOne: formatNullablePrice(targetOne),
    targetTwo: formatNullablePrice(targetTwo),
    riskReward,
  };
}

function formatNullablePrice(value?: number | null) {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return 'N/A';
  }

  return value.toLocaleString('en-US', {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  });
}

function formatRelativeVolume(value?: number | null) {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return 'N/A';
  }

  return `${value.toFixed(2)}x`;
}

function formatSignals(signals?: string[]) {
  if (!signals?.length) {
    return 'N/A';
  }

  return signals.join('\n');
}

function getSafeConfidence(value?: number | null) {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return null;
  }

  return Math.max(0, Math.min(100, Math.round(value)));
}

function formatTitle(value?: string) {
  if (!value) {
    return 'N/A';
  }

  return value
    .replace(/_/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

const styles = StyleSheet.create({
  embeddedCard: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderLeftWidth: 3,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    padding: Spacing.twoAndHalf,
  },
  header: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
    marginBottom: Spacing.two,
  },
  titleBlock: {
    flex: 1,
  },
  symbol: {
    color: Theme.colors.accent,
    fontSize: 13,
    fontWeight: '900',
    letterSpacing: 0,
    marginBottom: Spacing.one,
  },
  patternName: {
    color: Theme.colors.text,
    fontSize: 21,
    fontWeight: '900',
    lineHeight: 26,
  },
  metaRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
    marginBottom: Spacing.two,
  },
  description: {
    color: Theme.colors.textMuted,
    fontSize: 14,
    lineHeight: 21,
    marginTop: Spacing.three,
    marginBottom: Spacing.three,
  },
  detailsButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.twoAndHalf,
    paddingVertical: Spacing.two,
  },
  detailsButtonText: {
    color: Theme.colors.accent,
    fontSize: 13,
    fontWeight: '900',
  },
  detailsChevron: {
    color: Theme.colors.accent,
    fontSize: 16,
    fontWeight: '900',
  },
  sectionHeader: {
    marginBottom: Spacing.two,
  },
  sectionTitle: {
    color: Theme.colors.text,
    fontSize: 15,
    fontWeight: '900',
  },
  sectionHint: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
    marginTop: Spacing.half,
  },
  analysisSection: {
    gap: Spacing.two,
    marginTop: Spacing.three,
  },
  analysisTitle: {
    color: Theme.colors.text,
    fontSize: 15,
    fontWeight: '900',
  },
  levelGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  planGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  metricTile: {
    backgroundColor: '#0B1220',
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexGrow: 1,
    minWidth: '45%',
    padding: Spacing.two,
  },
  metricLabel: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '900',
    marginBottom: Spacing.one,
    textTransform: 'uppercase',
  },
  metricValue: {
    color: Theme.colors.text,
    fontSize: 14,
    fontWeight: '900',
    lineHeight: 20,
  },
  riskRewardBox: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: Spacing.two,
  },
  riskRewardLabel: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  riskRewardValue: {
    color: Theme.colors.warning,
    fontSize: 13,
    fontWeight: '900',
  },
  disclaimer: {
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    marginTop: Spacing.three,
    padding: Spacing.two,
  },
  disclaimerText: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
    lineHeight: 18,
  },
});
