import { useState } from 'react';
import type { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { DecisionSummaryCard } from '@/components/ui/DecisionSummaryCard';
import { DetailGrid, InfoTile } from '@/components/watchlist/WatchlistPrimitives';
import { Spacing, Theme } from '@/constants/theme';
import { stockToneColor } from '@/features/stock-detail/stockDetailSemanticColors';
import type { StockDetailOverviewModel, StockDetailTone } from '@/features/stock-detail/stockDetailPresenter';
import { decisionSummary } from '@/features/trust/decisionSummary';

export function StockOverviewSections({ model }: { model: StockDetailOverviewModel }) {
  const [metricsOpen, setMetricsOpen] = useState(false);
  const [methodologyOpen, setMethodologyOpen] = useState(false);

  return (
    <View style={styles.sections}>
      <DecisionSummaryCard summary={decisionSummary({
        id: `stock.${model.symbol}`, title: `${model.symbol} decision summary`, currentState: `${model.rating} · ${model.assessmentLabel}`,
        whatChanged: shortenText(model.executiveSummary.body, 30), preferredAction: model.tradePlan.trend,
        mainRisk: model.risks[0] ?? `${model.riskLevel} risk`, invalidation: model.tradePlan.stop === 'N/A' ? null : `Stop reference ${model.tradePlan.stop}`,
        freshness: model.quote.timestamp ? `Updated ${model.quote.timestamp}` : model.sourceLabel, confidence: null, confidenceLabel: 'Signal confidence by evidence',
        evidence: null, availability: model.overallScore === null ? 'partial' : 'available', contradiction: null,
        whatWouldChange: model.watchItems[0]?.value ?? null, methodology: [model.methodology, ...model.strengths.slice(0, 3)],
      })} />

      <SectionSurface>
        <Text style={styles.sectionTitle}>Trade Plan</Text>
        <View style={styles.tradeLevelGrid}>
          <PlanMetric label="Entry" value={model.tradePlan.entry} tone="accent" />
          <PlanMetric label="Current" value={model.tradePlan.currentPrice} tone="neutral" />
          <PlanMetric label="Stop" value={model.tradePlan.stop} tone="danger" />
          <PlanMetric label="Targets" value={model.tradePlan.targets.join(' · ') || 'N/A'} tone="success" />
        </View>
        <SubsectionLabel>Factor Scores</SubsectionLabel>
        <View style={styles.factorStack}>
          {model.factors.map((factor) => (
            <View key={factor.key} style={styles.factorRow}>
              <View style={styles.factorTopRow}>
                <View style={styles.factorLabelBlock}>
                  <Text style={styles.factorLabel}>{factor.label}</Text>
                  <Text style={styles.factorInterpretation}>{factor.interpretation}</Text>
                </View>
                <Text style={[styles.factorScore, { color: stockToneColor(factor.tone) }]}>
                  {formatScore(factor.score)}
                </Text>
              </View>
              <View style={styles.factorTrack}>
                <View
                  style={[
                    styles.factorFill,
                    {
                      backgroundColor: stockToneColor(factor.tone),
                      width: `${Math.max(0, Math.min(factor.score ?? 0, 100))}%`,
                    },
                  ]}
                />
              </View>
            </View>
          ))}
        </View>
        <View style={styles.tradeStateRow}>
          <PlanMetric label="Volume" value={model.tradePlan.volume} tone="neutral" />
          <PlanMetric label="Trend" value={model.tradePlan.trend} tone="neutral" />
        </View>
      </SectionSurface>

      <View style={styles.disclosurePanel}>
        <Text style={styles.sectionTitle}>Supporting Details</Text>
        <AccordionRow
          expanded={metricsOpen}
          label="Supporting Metrics"
          onPress={() => setMetricsOpen((open) => !open)}
        />
        {metricsOpen ? (
          <View style={styles.metricsGrid}>
            <DetailGrid>
              {model.supportingMetrics.map((metric) => (
                <InfoTile key={metric.label} label={metric.label} value={metric.value} />
              ))}
            </DetailGrid>
          </View>
        ) : null}
        <View style={styles.divider} />
        <AccordionRow
          expanded={methodologyOpen}
          label="Data Source and Methodology"
          onPress={() => setMethodologyOpen((open) => !open)}
        />
        {methodologyOpen ? <Text style={styles.methodText}>{model.methodology}</Text> : null}
      </View>
    </View>
  );
}

function PlanMetric({ label, tone, value }: { label: string; tone: StockDetailTone; value: string }) {
  return (
    <View style={styles.planMetric}>
      <Text style={styles.watchLabel}>{label}</Text>
      <Text numberOfLines={2} style={[styles.watchValue, { color: stockToneColor(tone) }]}>{value}</Text>
    </View>
  );
}

function SubsectionLabel({ children }: { children: ReactNode }) {
  return <Text style={styles.subsectionLabel}>{children}</Text>;
}

function SectionSurface({
  accentColor,
  children,
}: {
  accentColor?: string;
  children: ReactNode;
}) {
  return (
    <View style={[styles.surface, accentColor ? { borderTopColor: accentColor, borderTopWidth: 2 } : null]}>
      {children}
    </View>
  );
}

function AccordionRow({
  expanded,
  label,
  onPress,
}: {
  expanded: boolean;
  label: string;
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityLabel={`${expanded ? 'Hide' : 'Show'} ${label}`}
      accessibilityRole="button"
      accessibilityState={{ expanded }}
      onPress={onPress}
      style={styles.accordionRow}>
      <Text style={styles.accordionText}>{expanded ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}</Text>
      <Text style={styles.accordionIcon}>{expanded ? '⌄' : '›'}</Text>
    </Pressable>
  );
}

function formatScore(value?: number | null): string {
  return typeof value === 'number' && Number.isFinite(value) ? Math.round(value).toString() : 'N/A';
}

function shortenText(value: string, maxWords: number): string {
  const words = value.trim().split(/\s+/);
  return words.length > maxWords ? `${words.slice(0, maxWords).join(' ')}...` : value;
}

const styles = StyleSheet.create({
  accordionIcon: {
    color: Theme.colors.textMuted,
    fontSize: 20,
    fontWeight: '900',
  },
  accordionRow: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    minHeight: 44,
  },
  accordionText: {
    color: Theme.colors.text,
    fontSize: 13,
    fontWeight: '900',
  },
  assessmentStage: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '800',
  },
  assessmentStatus: {
    fontSize: 20,
    fontWeight: '900',
  },
  assessmentStatusBlock: {
    flex: 1,
    gap: Spacing.half,
    minWidth: 0,
  },
  assessmentTop: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  badgeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.one,
  },
  divider: {
    backgroundColor: Theme.colors.border,
    height: 1,
  },
  disclosurePanel: {
    gap: Spacing.one,
    paddingHorizontal: Spacing.one,
  },
  evidenceIcon: {
    fontSize: 12,
    fontWeight: '900',
    width: 18,
  },
  evidenceRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.one,
  },
  evidenceStack: {
    gap: Spacing.one,
  },
  evidenceText: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: 12,
    fontWeight: '800',
    lineHeight: 17,
  },
  factorFill: {
    borderRadius: Theme.radii.pill,
    height: 8,
  },
  factorInterpretation: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '800',
  },
  factorLabel: {
    color: Theme.colors.text,
    fontSize: 13,
    fontWeight: '900',
  },
  factorLabelBlock: {
    flex: 1,
    gap: Spacing.half,
    minWidth: 0,
  },
  factorRow: {
    gap: Spacing.one,
  },
  factorScore: {
    fontSize: 13,
    fontWeight: '900',
  },
  factorStack: {
    gap: Spacing.twoAndHalf,
  },
  factorTopRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  factorTrack: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderRadius: Theme.radii.pill,
    height: 8,
    overflow: 'hidden',
  },
  methodText: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    fontWeight: '700',
    lineHeight: 20,
  },
  planMetric: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderRadius: Theme.radii.small,
    flexGrow: 1,
    minWidth: '47%',
    padding: Spacing.two,
  },
  metricsGrid: {
    paddingTop: Spacing.one,
  },
  scoreBlock: {
    alignItems: 'baseline',
    flexDirection: 'row',
  },
  scoreLabel: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '900',
  },
  scoreMeterFill: {
    borderRadius: Theme.radii.pill,
    height: 9,
  },
  scoreMeterTrack: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderRadius: Theme.radii.pill,
    height: 9,
    overflow: 'hidden',
  },
  scoreValue: {
    color: Theme.colors.text,
    fontSize: 32,
    fontWeight: '900',
  },
  sectionHeaderRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  sectionTitle: {
    color: Theme.colors.text,
    fontSize: 15,
    fontWeight: '900',
  },
  sections: {
    gap: Spacing.three,
  },
  sourceLabel: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  subsectionLabel: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '900',
    paddingTop: Spacing.one,
    textTransform: 'uppercase',
  },
  summaryBody: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    fontWeight: '700',
    lineHeight: 20,
  },
  summaryHeadline: {
    color: Theme.colors.text,
    fontSize: 17,
    fontWeight: '900',
    lineHeight: 22,
  },
  surface: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.two,
    padding: Spacing.twoAndHalf,
  },
  takeawayColumn: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderRadius: Theme.radii.small,
    flexGrow: 1,
    gap: Spacing.one,
    minWidth: '47%',
    padding: Spacing.two,
  },
  takeawayGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  takeawayIcon: {
    fontSize: 12,
    fontWeight: '900',
    width: 16,
  },
  takeawayRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.one,
  },
  takeawayText: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: 12,
    fontWeight: '800',
    lineHeight: 17,
  },
  takeawayTitle: {
    fontSize: 12,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  tradeLevelGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  tradeStateRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  watchGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  watchLabel: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '900',
    marginBottom: Spacing.half,
    textTransform: 'uppercase',
  },
  watchTile: {
    borderRadius: Theme.radii.small,
    flexGrow: 1,
    minWidth: '47%',
    padding: Spacing.two,
  },
  watchValue: {
    fontSize: 13,
    fontWeight: '900',
  },
});
