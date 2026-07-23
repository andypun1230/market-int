import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { AppIcon } from '@/components/ui/AppIcon';
import { StatusBadge } from '@/components/ui/StatusBadge';
import {
  DetailGrid,
  InfoTile,
  SectionSummary,
  ZoneSection,
} from '@/components/watchlist/WatchlistPrimitives';
import { Spacing, Theme, Typography } from '@/constants/theme';
import {
  buildRiskDashboard,
  type PositionGuidance,
  type RewardInterpretation,
  type RiskDashboardModel,
  type RiskFactor,
  type RiskLevelItem,
  type ModeledRisk,
} from '@/features/stock-detail/risk/riskPresenter';
import type { RiskPlan, SupportResistanceResponse } from '@/types/market';
import type { CurrentPriceSelection } from '@/features/stock-detail/currentPrice';
import { getRiskColor, getSourceTone } from '@/utils/colors';
import {
  formatNullablePercent,
  formatNullablePrice,
  formatRiskReward,
} from '@/utils/formatters';

export function RiskPlanSection({
  currentPrice,
  riskPlan,
  showTitle = true,
  supportResistance,
}: {
  currentPrice?: CurrentPriceSelection | null;
  riskPlan?: RiskPlan;
  showTitle?: boolean;
  supportResistance?: SupportResistanceResponse;
}) {
  const [supportingDetailsOpen, setSupportingDetailsOpen] = useState(false);
  const model = useMemo(
    () => buildRiskDashboard({ currentPrice, riskPlan, supportResistance }),
    [currentPrice, riskPlan, supportResistance],
  );
  const riskColor = getRiskColor(model.riskLevel);
  const sourceObject = {
    data_quality: riskPlan?.data_quality,
    data_source: supportResistance?.data_source,
    fallback_used: supportResistance?.fallback_used,
  };
  const content = (
    <View style={styles.dashboardStack}>
      <RiskOverview model={model} riskColor={riskColor} />
      <RiskRewardSection model={model} />
      <PositionGuidanceSection guidance={model.positionGuidance} />
      <IllustrativeRiskExample model={model} />
      <SupportingRiskDetails
        model={model}
        open={supportingDetailsOpen}
        riskPlan={riskPlan}
        riskColor={riskColor}
        setOpen={setSupportingDetailsOpen}
      />
    </View>
  );

  if (!showTitle) {
    return content;
  }

  return (
    <ZoneSection
      title="Risk Dashboard"
      titleAccessory={
        <View style={styles.badgeStack}>
          <Text style={[styles.riskLevelBadge, { color: riskColor }]}>
            {model.riskLevel ?? 'N/A'}
          </Text>
          {model.trust.state === 'test_compatible' ? (
            <TestScenarioBadge />
          ) : (
            <StatusBadge
              label={model.trust.userLabel}
              tone={getSourceTone(sourceObject)}
            />
          )}
        </View>
      }>
      {content}
    </ZoneSection>
  );
}

function RiskOverview({ model, riskColor }: { model: RiskDashboardModel; riskColor: string }) {
  return (
    <View style={styles.sectionCard}>
      <View style={styles.inlineHeader}>
        <Text style={styles.sectionLabel}>Risk Overview</Text>
        <Text style={[styles.meterLabel, { color: riskColor }]}>{model.riskLevel ?? 'N/A'}</Text>
      </View>
      <RiskSummary model={model} riskColor={riskColor} />
      <View style={styles.overviewDivider} />
      <RiskMeter model={model} riskColor={riskColor} />
      <View style={styles.overviewDivider} />
      <CurrentRiskLevels model={model} />
      {model.factors.length ? (
        <>
          <View style={styles.overviewDivider} />
          <RiskFactorsSection factors={model.factors} />
        </>
      ) : null}
    </View>
  );
}

function RiskSummary({ model, riskColor }: { model: RiskDashboardModel; riskColor: string }) {
  return (
    <View style={styles.overviewSubsection}>
      <View style={styles.summaryHeader}>
        <View style={styles.summaryTitleBlock}>
          <Text style={styles.summaryTitle}>{model.headline}</Text>
        </View>
        <View style={styles.summaryScoreBlock}>
          <Text style={[styles.summaryScore, { color: riskColor }]}>
            {model.riskPercent != null ? `${model.riskPercent.toFixed(1)}%` : 'N/A'}
          </Text>
          <Text style={styles.summaryScoreLabel}>downside to invalidation</Text>
        </View>
      </View>
      <Text style={styles.summaryBody}>{model.summary}</Text>
      {model.trust.explanation && !model.trust.shouldLeadRiskTab ? (
        <View style={styles.trustNotice}>
          <Text style={styles.trustNoticeText}>{model.trust.explanation}</Text>
        </View>
      ) : null}
    </View>
  );
}

function RiskMeter({ model, riskColor }: { model: RiskDashboardModel; riskColor: string }) {
  const segments: ModeledRisk[] = ['low', 'moderate', 'high', 'very_high'];
  const activeRisk = model.decisionContext.modeledRisk;
  return (
    <View
      accessibilityLabel={`Modeled risk level: ${modeledRiskLabel(activeRisk)}.`}
      accessible
      style={styles.overviewSubsection}>
      <View style={styles.inlineHeader}>
        <Text style={styles.sectionLabel}>Risk Meter</Text>
        <Text style={[styles.meterLabel, { color: riskColor }]}>{modeledRiskLabel(activeRisk)}</Text>
      </View>
      <View style={styles.segmentTrack}>
        {segments.map((segment) => {
          const active = segment === activeRisk;
          return (
            <View
              key={segment}
              style={[
                styles.segment,
                active ? { backgroundColor: riskColor, borderColor: riskColor } : null,
              ]}>
              <Text style={[styles.segmentText, active ? styles.segmentTextActive : null]}>
                {segmentLabel(segment)}
              </Text>
            </View>
          );
        })}
      </View>
      <View style={styles.meterSupportRows}>
        <Text style={styles.legendText}>
          Downside {model.downsidePercent != null ? `${model.downsidePercent.toFixed(1)}%` : 'N/A'}
        </Text>
        <Text style={styles.legendText}>
          Volatility {model.volatilityLevel ?? 'N/A'}
        </Text>
      </View>
    </View>
  );
}

function CurrentRiskLevels({ model }: { model: RiskDashboardModel }) {
  if (!model.trust.shouldLeadRiskTab) {
    return (
      <View style={styles.overviewSubsection}>
        <Text style={styles.sectionLabel}>Current Risk Levels</Text>
        <SectionSummary>
          Current calculations are unavailable because the available trade levels are not compatible with current risk context.
        </SectionSummary>
      </View>
    );
  }
  return (
    <View style={styles.sectionCard}>
      <Text style={styles.sectionLabel}>Current Risk Levels</Text>
      <LevelList levels={model.riskLevels} />
    </View>
  );
}

function RiskRewardSection({ model }: { model: RiskDashboardModel }) {
  if (!model.trust.shouldShowRiskReward || !model.rewards.length) {
    return (
      <View style={styles.sectionCard}>
        <Text style={styles.sectionLabel}>Risk / Reward</Text>
        <SectionSummary>Risk / reward is hidden until trusted targets and invalidation levels are available.</SectionSummary>
      </View>
    );
  }
  return (
    <View style={styles.sectionCard}>
      <Text style={styles.sectionLabel}>Risk / Reward</Text>
      <Text style={styles.basisText}>
        Based on current price and invalidation at ${formatNullablePrice(model.invalidationLevel)}
      </Text>
      <View style={styles.rewardStack}>
        {model.rewards.map((reward) => (
          <RewardRow key={reward.key} reward={reward} />
        ))}
      </View>
    </View>
  );
}

function RiskFactorsSection({ factors }: { factors: RiskFactor[] }) {
  const protective = factors.filter((factor) => factor.tone === 'success');
  const cautions = factors.filter((factor) => factor.tone !== 'success');
  return (
    <View style={styles.overviewSubsection}>
      <Text style={styles.sectionLabel}>Risk Drivers</Text>
      <View style={styles.factorStack}>
        <RiskFactorGroup items={protective} title="Protective" />
        <RiskFactorGroup items={cautions} title="Cautions" />
      </View>
    </View>
  );
}

function RiskFactorGroup({ items, title }: { items: RiskFactor[]; title: string }) {
  if (!items.length) {
    return null;
  }
  return (
    <View style={styles.factorGroup}>
      <Text style={styles.factorGroupTitle}>{title}</Text>
      {items.map((factor) => (
        <View key={factor.key} style={styles.factorRow}>
          <View style={styles.factorIcon}>
            <AppIcon
              color={factorToneColor(factor.tone)}
              name={factor.tone === 'success' ? 'check' : factor.tone === 'neutral' ? 'neutralDot' : 'warning'}
              size={14}
            />
          </View>
          <View style={styles.factorTextBlock}>
            <Text style={styles.factorLabel}>{factor.label}</Text>
            {factor.detail ? <Text style={styles.factorDetail}>{factor.detail}</Text> : null}
          </View>
        </View>
      ))}
    </View>
  );
}

function PositionGuidanceSection({ guidance }: { guidance: PositionGuidance }) {
  return (
    <View style={styles.sectionCard}>
      <View style={styles.inlineHeader}>
        <Text style={styles.sectionLabel}>Position Size Guidance</Text>
        <StatusBadge label={guidance.label} tone={positionTone(guidance.state)} />
      </View>
      <Text style={styles.bodyText}>{guidance.explanation}</Text>
    </View>
  );
}

function IllustrativeRiskExample({ model }: { model: RiskDashboardModel }) {
  if (!model.illustrativeLevels.length) {
    return null;
  }
  return (
    <View style={styles.sectionCard}>
      <View style={styles.inlineHeader}>
        <Text style={styles.sectionLabel}>Illustrative Risk Example</Text>
        <StatusBadge label="Not current guidance" tone="warning" />
      </View>
      <SectionSummary>
        These are the existing entry, stop, and target values, but they are not promoted as current actionable levels.
      </SectionSummary>
      <LevelList levels={model.illustrativeLevels} />
    </View>
  );
}

function SupportingRiskDetails({
  model,
  open,
  riskColor,
  riskPlan,
  setOpen,
}: {
  model: RiskDashboardModel;
  open: boolean;
  riskColor: string;
  riskPlan?: RiskPlan;
  setOpen: (value: boolean) => void;
}) {
  return (
    <View style={styles.disclosurePanel}>
      <Pressable
        accessibilityLabel={`${open ? 'Hide' : 'Show'} supporting risk details`}
        accessibilityRole="button"
        onPress={() => setOpen(!open)}
        style={styles.collapseHeader}>
        <Text style={styles.sectionLabel}>Supporting Risk Details</Text>
        <Text style={styles.collapseChevron}>{open ? 'Hide' : 'Show'}</Text>
      </Pressable>
      {open ? (
        <>
          <DetailGrid>
            {model.supportingMetrics.map((metric) => (
              <InfoTile key={metric.label} label={metric.label} value={metric.value} />
            ))}
            <InfoTile label="Entry" value={formatNullablePrice(riskPlan?.entry)} valueColor={Theme.colors.accent} />
            <InfoTile label="Stop Loss" value={formatNullablePrice(riskPlan?.stop_loss)} valueColor={Theme.colors.danger} />
            <InfoTile label="Target 1" value={formatNullablePrice(riskPlan?.target_1)} valueColor={Theme.colors.success} />
            <InfoTile label="Target 2" value={formatNullablePrice(riskPlan?.target_2)} valueColor={Theme.colors.success} />
            <InfoTile label="Risk / Reward T1" value={formatRiskReward(riskPlan?.risk_reward_target_1)} />
            <InfoTile label="Risk / Reward T2" value={formatRiskReward(riskPlan?.risk_reward_target_2)} />
            <InfoTile label="Reward % T1" value={formatNullablePercent(riskPlan?.reward_percent_target_1)} />
            <InfoTile label="Reward % T2" value={formatNullablePercent(riskPlan?.reward_percent_target_2)} />
            <InfoTile label="Risk Level" value={riskPlan?.risk_level ?? 'N/A'} valueColor={riskColor} />
          </DetailGrid>
          {riskPlan?.position_size_note ? (
            <View style={styles.noteBox}>
              <Text style={styles.noteLabel}>Original Position Note</Text>
              <Text style={styles.noteText}>{riskPlan.position_size_note}</Text>
            </View>
          ) : null}
        </>
      ) : null}
    </View>
  );
}

function LevelList({ levels }: { levels: RiskLevelItem[] }) {
  if (!levels.length) {
    return <SectionSummary>No compatible levels are available.</SectionSummary>;
  }
  return (
    <View style={styles.levelStack}>
      {levels.map((level, index) => (
        <View
          key={level.key}
          style={[
            styles.levelRow,
            level.role === 'current' ? styles.currentLevelRow : null,
            index < levels.length - 1 ? styles.dividerRow : null,
          ]}>
          <Text style={[styles.levelValue, { color: levelColor(level.role) }]}>
            ${formatNullablePrice(level.value)}
          </Text>
          <View style={styles.levelTextBlock}>
            <Text style={styles.levelLabel}>{level.label}</Text>
            <Text style={styles.levelDescription}>{level.description}</Text>
          </View>
        </View>
      ))}
    </View>
  );
}

function RewardRow({ reward }: { reward: RewardInterpretation }) {
  return (
    <View style={styles.rewardRow}>
      <View style={styles.rewardMain}>
        <View style={styles.rewardTitleRow}>
          <Text style={styles.rewardTitle}>{reward.label}</Text>
          <Text style={styles.rewardPrice}>${formatNullablePrice(reward.target)}</Text>
        </View>
        <Text style={styles.rewardInterpretation}>{reward.interpretation}</Text>
      </View>
      <View style={styles.rewardMetric}>
        <Text style={[styles.rewardRatio, { color: rewardToneColor(reward.quality) }]}>
          {reward.ratio.toFixed(2)} : 1
        </Text>
        <Text style={styles.rewardQuality}>+{reward.rewardPercent.toFixed(1)}%</Text>
      </View>
    </View>
  );
}

function TestScenarioBadge() {
  return (
    <View
      accessibilityLabel="Generated Test Data represents a test scenario and is not live market guidance."
      accessible
      style={styles.testScenarioBadge}>
      <Text style={styles.testScenarioText}>ⓘ Test scenario</Text>
    </View>
  );
}

function levelColor(role: RiskLevelItem['role']) {
  switch (role) {
    case 'target':
      return Theme.colors.text;
    case 'confirmation':
      return Theme.colors.accent;
    case 'support':
      return Theme.colors.warning;
    case 'invalidation':
      return Theme.colors.danger;
    default:
      return Theme.colors.text;
  }
}

function modeledRiskLabel(risk: ModeledRisk) {
  switch (risk) {
    case 'very_high':
      return 'Very High';
    case 'high':
      return 'High';
    case 'moderate':
      return 'Moderate';
    case 'low':
      return 'Low';
    default:
      return 'Unavailable';
  }
}

function segmentLabel(risk: ModeledRisk) {
  return risk === 'very_high' ? 'Very High' : modeledRiskLabel(risk);
}

function factorToneColor(tone: RiskFactor['tone']) {
  switch (tone) {
    case 'success':
      return Theme.colors.success;
    case 'warning':
      return Theme.colors.warning;
    case 'danger':
      return Theme.colors.danger;
    default:
      return Theme.colors.textMuted;
  }
}

function rewardToneColor(quality: RewardInterpretation['quality']) {
  switch (quality) {
    case 'strong':
    case 'favorable':
      return Theme.colors.success;
    case 'balanced':
      return Theme.colors.accent;
    case 'limited':
      return Theme.colors.warning;
    case 'unfavorable':
      return Theme.colors.danger;
    default:
      return Theme.colors.textMuted;
  }
}

function positionTone(state: PositionGuidance['state']) {
  switch (state) {
    case 'standard':
      return 'success' as const;
    case 'reduced':
      return 'warning' as const;
    case 'conservative':
      return 'danger' as const;
    default:
      return 'muted' as const;
  }
}

const styles = StyleSheet.create({
  badgeStack: {
    alignItems: 'flex-end',
    gap: Spacing.one,
  },
  bodyText: {
    color: Theme.colors.text,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.emphasis,
    lineHeight: 19,
  },
  collapseChevron: {
    color: Theme.colors.accent,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
  },
  collapseHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    minHeight: 44,
  },
  dashboardStack: {
    gap: Spacing.twoAndHalf,
  },
  basisText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 16,
  },
  currentLevelRow: {
    backgroundColor: Theme.colors.accentSoft,
  },
  dividerRow: {
    borderBottomColor: Theme.colors.border,
    borderBottomWidth: 1,
  },
  disclosurePanel: {
    gap: Spacing.one,
    paddingHorizontal: Spacing.one,
  },
  factorDetail: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.emphasis,
    lineHeight: 17,
  },
  factorIcon: {
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 1,
    width: 14,
  },
  factorGroup: {
    gap: Spacing.one,
  },
  factorGroupTitle: {
    color: Theme.colors.textMuted,
    fontSize: Typography.chartLabel.fontSize,
    fontWeight: Typography.weights.strong,
    textTransform: 'uppercase',
  },
  factorLabel: {
    color: Theme.colors.text,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
  },
  factorRow: {
    flexDirection: 'row',
    gap: Spacing.two,
  },
  factorStack: {
    gap: Spacing.two,
  },
  factorTextBlock: {
    flex: 1,
    gap: Spacing.half,
  },
  inlineHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  kicker: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
    textTransform: 'uppercase',
  },
  legendText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
  },
  levelDescription: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.emphasis,
    lineHeight: 17,
  },
  levelLabel: {
    color: Theme.colors.text,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
  },
  levelRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    minHeight: 48,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.two,
  },
  levelStack: {
    backgroundColor: Theme.colors.cardMuted,
    borderRadius: Theme.radii.small,
    overflow: 'hidden',
  },
  levelTextBlock: {
    flex: 1,
    gap: Spacing.half,
  },
  levelValue: {
    minWidth: 76,
    fontSize: Typography.bodyLarge.fontSize,
    fontWeight: Typography.weights.strong,
  },
  meterLabel: {
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
  },
  meterSupportRows: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: Spacing.two,
  },
  segment: {
    alignItems: 'center',
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flex: 1,
    justifyContent: 'center',
    minHeight: 28,
    paddingHorizontal: Spacing.one,
  },
  segmentText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.chartAxis.fontSize,
    fontWeight: Typography.weights.strong,
    textAlign: 'center',
  },
  segmentTextActive: {
    color: Theme.colors.background,
  },
  segmentTrack: {
    flexDirection: 'row',
    gap: Spacing.one,
  },
  noteBox: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    marginTop: Spacing.two,
    padding: Spacing.twoAndHalf,
  },
  noteLabel: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
    marginBottom: Spacing.one,
    textTransform: 'uppercase',
  },
  noteText: {
    color: Theme.colors.text,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 19,
  },
  overviewDivider: {
    backgroundColor: Theme.colors.border,
    height: 1,
  },
  overviewSubsection: {
    gap: Spacing.two,
  },
  rewardDetail: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
  },
  rewardInterpretation: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 17,
  },
  rewardMain: {
    flex: 1,
    gap: Spacing.half,
  },
  rewardMetric: {
    alignItems: 'flex-end',
    minWidth: 76,
  },
  rewardPrice: {
    color: Theme.colors.text,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
  },
  rewardQuality: {
    color: Theme.colors.textMuted,
    fontSize: Typography.chartLabel.fontSize,
    fontWeight: Typography.weights.strong,
    textTransform: 'uppercase',
  },
  rewardRatio: {
    fontSize: Typography.bodyLarge.fontSize,
    fontWeight: Typography.weights.strong,
  },
  rewardRow: {
    alignItems: 'center',
    borderBottomColor: Theme.colors.border,
    borderBottomWidth: 1,
    flexDirection: 'row',
    gap: Spacing.two,
    paddingBottom: Spacing.two,
  },
  rewardStack: {
    gap: Spacing.two,
  },
  rewardTitle: {
    color: Theme.colors.text,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
  },
  rewardTitleRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  riskLevelBadge: {
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
  },
  sectionCard: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.two,
    padding: Spacing.twoAndHalf,
  },
  sectionLabel: {
    color: Theme.colors.text,
    fontSize: Typography.body.fontSize,
    fontWeight: Typography.weights.strong,
  },
  summaryBody: {
    color: Theme.colors.textMuted,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.emphasis,
    lineHeight: 20,
  },
  summaryCard: {
    backgroundColor: Theme.colors.cardAlt,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.two,
    padding: Spacing.twoAndHalf,
  },
  summaryHeader: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  summaryScore: {
    fontSize: Typography.detailTitle.fontSize,
    fontWeight: Typography.weights.strong,
  },
  summaryScoreBlock: {
    alignItems: 'flex-end',
    maxWidth: 104,
  },
  summaryScoreLabel: {
    color: Theme.colors.textMuted,
    fontSize: Typography.chartAxis.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 12,
    textAlign: 'right',
    textTransform: 'uppercase',
  },
  summaryTitle: {
    color: Theme.colors.text,
    fontSize: Typography.cardTitle.fontSize,
    fontWeight: Typography.weights.strong,
  },
  summaryTitleBlock: {
    flex: 1,
    gap: Spacing.half,
  },
  trustNotice: {
    backgroundColor: Theme.colors.warningSoft,
    borderColor: Theme.colors.warning,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    padding: Spacing.two,
  },
  trustNoticeText: {
    color: Theme.colors.warning,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 17,
  },
  testScenarioBadge: {
    alignSelf: 'flex-start',
    backgroundColor: Theme.colors.cardMuted,
    borderRadius: Theme.radii.pill,
    paddingHorizontal: Spacing.two,
    paddingVertical: 4,
  },
  testScenarioText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
  },
});
