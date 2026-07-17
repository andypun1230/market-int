import { useState } from 'react';
import type { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { StatusBadge } from '@/components/ui/StatusBadge';
import { DetailGrid, InfoTile } from '@/components/watchlist/WatchlistPrimitives';
import { Spacing, Theme } from '@/constants/theme';
import {
  getRiskTone,
  stockToneColor,
  stockToneSoftColor,
  stockToneToBadgeTone,
} from '@/features/stock-detail/stockDetailSemanticColors';
import type {
  StockAssessmentEvidence,
  StockDetailOverviewModel,
  StockDetailTone,
} from '@/features/stock-detail/stockDetailPresenter';

export function StockOverviewSections({ model }: { model: StockDetailOverviewModel }) {
  const [metricsOpen, setMetricsOpen] = useState(false);
  const [methodologyOpen, setMethodologyOpen] = useState(false);

  return (
    <View style={styles.sections}>
      <SectionSurface accentColor={stockToneColor(model.assessmentTone)}>
        <View style={styles.sectionHeaderRow}>
          <Text style={styles.sectionTitle}>Executive Summary</Text>
          <Text style={styles.sourceLabel}>{summarySourceLabel(model.executiveSummary.source)}</Text>
        </View>
        <Text style={styles.summaryHeadline}>{model.executiveSummary.headline}</Text>
        <Text style={styles.summaryBody}>{model.executiveSummary.body}</Text>
      </SectionSurface>

      <SectionSurface>
        <Text style={styles.sectionTitle}>Overall Assessment</Text>
        <View style={styles.assessmentTop}>
          <View style={styles.assessmentStatusBlock}>
            <Text style={[styles.assessmentStatus, { color: stockToneColor(model.assessmentTone) }]}>
              {model.assessmentLabel}
            </Text>
            <Text style={styles.assessmentStage}>{model.rating}</Text>
          </View>
          <View style={styles.scoreBlock}>
            <Text style={styles.scoreValue}>{formatScore(model.overallScore)}</Text>
            <Text style={styles.scoreLabel}>/ 100</Text>
          </View>
        </View>
        <ScoreMeter score={model.overallScore} tone={model.assessmentTone} />
        <View style={styles.badgeRow}>
          <StatusBadge label={model.status} tone={stockToneToBadgeTone(model.assessmentTone)} />
          <StatusBadge label={`${model.riskLevel} risk`} tone={stockToneToBadgeTone(getRiskTone(model.riskLevel))} />
        </View>
        {model.assessmentEvidence.length ? (
          <View style={styles.evidenceStack}>
            {model.assessmentEvidence.map((item) => (
              <EvidenceRow key={item.label} item={item} />
            ))}
          </View>
        ) : null}
      </SectionSurface>

      <SectionSurface>
        <Text style={styles.sectionTitle}>Key Takeaways</Text>
        <View style={styles.takeawayGrid}>
          <TakeawayColumn title="Strengths" items={model.strengths} tone="success" />
          <TakeawayColumn title="Risks" items={model.risks} tone="warning" />
        </View>
      </SectionSurface>

      <SectionSurface>
        <Text style={styles.sectionTitle}>Visual Factor Breakdown</Text>
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
      </SectionSurface>

      <SectionSurface>
        <Text style={styles.sectionTitle}>What to Watch Next</Text>
        <View style={styles.watchGrid}>
          {model.watchItems.map((item) => (
            <View key={`${item.label}-${item.value}`} style={[styles.watchTile, { backgroundColor: stockToneSoftColor(item.tone) }]}>
              <Text style={styles.watchLabel}>{item.label}</Text>
              <Text style={[styles.watchValue, { color: stockToneColor(item.tone) }]}>{item.value}</Text>
            </View>
          ))}
        </View>
      </SectionSurface>

      <SectionSurface>
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
      </SectionSurface>
    </View>
  );
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

function ScoreMeter({ score, tone }: { score: number | null; tone: StockDetailTone }) {
  const clamped = Math.max(0, Math.min(score ?? 0, 100));
  return (
    <View accessibilityLabel={score == null ? 'Score unavailable' : `Score ${Math.round(score)} out of 100`} style={styles.scoreMeterTrack}>
      {score == null ? null : (
        <View
          style={[
            styles.scoreMeterFill,
            {
              backgroundColor: stockToneColor(tone),
              width: `${clamped}%`,
            },
          ]}
        />
      )}
    </View>
  );
}

function EvidenceRow({ item }: { item: StockAssessmentEvidence }) {
  const symbol = item.tone === 'success' || item.tone === 'accent' ? '✓' : item.tone === 'danger' ? '!' : '⚠';
  return (
    <View style={styles.evidenceRow}>
      <Text style={[styles.evidenceIcon, { color: stockToneColor(item.tone) }]}>{symbol}</Text>
      <Text style={styles.evidenceText}>{item.label}</Text>
    </View>
  );
}

function TakeawayColumn({
  items,
  title,
  tone,
}: {
  items: string[];
  title: string;
  tone: StockDetailTone;
}) {
  return (
    <View style={styles.takeawayColumn}>
      <Text style={[styles.takeawayTitle, { color: stockToneColor(tone) }]}>{title}</Text>
      {items.slice(0, 4).map((item) => (
        <View key={item} style={styles.takeawayRow}>
          <Text style={[styles.takeawayIcon, { color: stockToneColor(tone) }]}>
            {tone === 'success' ? '✓' : '⚠'}
          </Text>
          <Text style={styles.takeawayText}>{shortenText(item, 14)}</Text>
        </View>
      ))}
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

function summarySourceLabel(source: StockDetailOverviewModel['executiveSummary']['source']): string {
  if (source === 'backend') {
    return 'Engine summary';
  }
  if (source === 'rule_based') {
    return 'Rule-based';
  }
  return 'Unavailable';
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
