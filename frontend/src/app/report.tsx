import { useState } from 'react';
import {
  Alert,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { AIInsightCard } from '@/components/ai/AIInsightCard';
import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppScreen } from '@/components/ui/AppScreen';
import { DetailModal } from '@/components/ui/DetailModal';
import { EmptyState } from '@/components/ui/EmptyState';
import { ExpandableSection } from '@/components/ui/ExpandableSection';
import { SkeletonCard } from '@/components/ui/SkeletonCard';
import { StatusBadge, type Tone } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';
import { AskCopilotButton } from '@/features/copilot/components/AskCopilotButton';
import { createCopilotContext } from '@/features/copilot/context/buildScreenContext';
import { useDailyReportLibrary } from '@/features/reports/useDailyReportLibrary';
import type { DailyReportRecord, ReportSourceState, ReportStatus } from '@/features/reports/reportLibraryModel';
import type { DailyReportWithInstitutionalActivity } from '@/hooks/useReportDashboard';
import type { DailyReport, InstitutionalActivityBias } from '@/types/market';

export default function ReportScreen() {
  const [selectedRecord, setSelectedRecord] = useState<DailyReportRecord | null>(null);
  const {
    downloadReport,
    error,
    generateTodayReport,
    generationMessage,
    grouped,
    loading,
    records,
    removeReport,
    shareReport,
    todayRecordCount,
    workingId,
  } = useDailyReportLibrary();
  const isGenerating = workingId === 'generate';

  return (
    <AppScreen
      showBackButton
      title="Daily Market Reports"
      subtitle="Generate and manage point-in-time market report snapshots.">
      <DashboardCard title="Daily Market Reports" accentColor={Theme.colors.accent}>
        <Text style={styles.bodyText}>
          Generate a complete snapshot of today’s market conditions, leadership, risk, watchlist signals, and supporting charts.
        </Text>
        <Pressable
          accessibilityLabel={isGenerating ? 'Generating today’s report' : todayRecordCount ? 'Generate new report version' : 'Generate today’s report'}
          accessibilityRole="button"
          disabled={isGenerating}
          onPress={generateTodayReport}
          style={({ pressed }) => [
            styles.generateButton,
            pressed && styles.downloadButtonPressed,
            isGenerating && styles.downloadButtonDisabled,
          ]}>
          <Text style={styles.generateButtonText}>
            {isGenerating ? 'Generating…' : todayRecordCount ? 'Generate New Version' : 'Generate Today’s Report'}
          </Text>
        </Pressable>
        {generationMessage ? <Text style={styles.placeholderText}>{generationMessage}</Text> : null}
        {error ? <Text style={styles.errorText}>{error}</Text> : null}
      </DashboardCard>

      {loading ? <ReportSkeleton /> : null}

      {!loading && records.length === 0 ? (
        <EmptyState
          title="No reports generated yet"
          message="Generate today’s report to create a complete market snapshot with analysis and charts."
        />
      ) : null}

      {grouped.ready.length ? (
        <ReportRecordSection
          downloadReport={downloadReport}
          records={grouped.ready}
          onPreview={setSelectedRecord}
          shareReport={shareReport}
          title="Ready to Download"
          workingId={workingId}
        />
      ) : records.length ? null : null}

      {grouped.downloaded.length ? (
        <ReportRecordSection
          downloadReport={downloadReport}
          records={grouped.downloaded}
          removeReport={removeReport}
          onPreview={setSelectedRecord}
          shareReport={shareReport}
          title="Downloaded Reports"
          workingId={workingId}
        />
      ) : null}

      {records.length && !grouped.ready.length ? (
        <Text style={styles.placeholderText}>No reports are waiting to be downloaded.</Text>
      ) : null}
      {records.length && !grouped.downloaded.length ? (
        <Text style={styles.placeholderText}>No downloaded reports yet.</Text>
      ) : null}

      <DetailModal
        onClose={() => setSelectedRecord(null)}
        subtitle={selectedRecord ? `${formatMarketDate(selectedRecord.metadata.marketDate)} · Version ${selectedRecord.metadata.version}` : undefined}
        title="Daily Report Preview"
        visible={Boolean(selectedRecord)}>
        {selectedRecord?.snapshot ? <ReportPreview record={selectedRecord} /> : null}
      </DetailModal>
    </AppScreen>
  );
}

function ReportSkeleton() {
  return (
    <View style={styles.skeletonStack}>
      <SkeletonCard rows={5} />
      <SkeletonCard compact rows={2} />
    </View>
  );
}

function ReportRecordSection({
  downloadReport,
  onPreview,
  records,
  removeReport,
  shareReport,
  title,
  workingId,
}: {
  downloadReport: (record: DailyReportRecord) => Promise<DailyReportRecord | null>;
  onPreview: (record: DailyReportRecord) => void;
  records: DailyReportRecord[];
  removeReport?: (record: DailyReportRecord) => Promise<boolean>;
  shareReport: (record: DailyReportRecord) => Promise<void>;
  title: string;
  workingId: string | null;
}) {
  return (
    <DashboardCard title={title} accentColor={title === 'Downloaded Reports' ? Theme.colors.success : Theme.colors.accent}>
      <View style={styles.reportCardStack}>
        {records.map((record) => (
          <ReportRecordCard
            downloadReport={downloadReport}
            key={record.id}
            onPreview={onPreview}
            record={record}
            removeReport={removeReport}
            shareReport={shareReport}
            working={workingId === record.id}
          />
        ))}
      </View>
    </DashboardCard>
  );
}

function ReportRecordCard({
  downloadReport,
  onPreview,
  record,
  removeReport,
  shareReport,
  working,
}: {
  downloadReport: (record: DailyReportRecord) => Promise<DailyReportRecord | null>;
  onPreview: (record: DailyReportRecord) => void;
  record: DailyReportRecord;
  removeReport?: (record: DailyReportRecord) => Promise<boolean>;
  shareReport: (record: DailyReportRecord) => Promise<void>;
  working: boolean;
}) {
  const status = getStatusPresentation(working ? 'downloading' : record.status);
  const confirmRemove = () => {
    if (!removeReport) {
      return;
    }
    Alert.alert(
      'Remove downloaded report?',
      'This deletes the saved PDF from this device and removes it from the downloaded list.',
      [
        { style: 'cancel', text: 'Cancel' },
        { onPress: () => void removeReport(record), style: 'destructive', text: 'Remove' },
      ],
    );
  };
  return (
    <View
      accessibilityLabel={`${formatMarketDate(record.metadata.marketDate)} report. ${status.label}. ${sourceStateLabel(record.metadata.sourceState)}.`}
      accessible
      style={styles.reportRecordCard}>
      <View style={styles.reportRecordHeader}>
        <View style={styles.reportRecordTitleBlock}>
          <Text style={styles.reportRecordTitle}>Daily Market Report</Text>
          <Text style={styles.reportRecordDate}>{formatMarketDate(record.metadata.marketDate)}</Text>
        </View>
        <StatusBadge label={status.label} tone={status.tone} />
      </View>
      <Text style={styles.reportRecordMeta}>
        Generated {formatDateTime(record.metadata.generatedAt)} · {sessionPhaseLabel(record.metadata.sessionPhase)}
      </Text>
      <View style={styles.reportBadgeRow}>
        <StatusBadge label={sourceStateLabel(record.metadata.sourceState)} tone={sourceTone(record.metadata.sourceState)} />
        <StatusBadge label={`Version ${record.metadata.version}`} showDot={false} tone="muted" />
        {record.metadata.downloadedAt ? <StatusBadge label="Saved on device" showDot={false} tone="success" /> : null}
      </View>
      {record.errorCode ? <Text style={styles.errorText}>{record.errorCode === 'download_failed' ? 'Report generated, but the PDF could not be downloaded.' : 'Unable to generate the report.'}</Text> : null}
      <View style={styles.recordActions}>
        {record.snapshot ? (
          <SmallAction label="Preview" onPress={() => onPreview(record)} />
        ) : null}
        {record.status === 'downloaded' ? (
          <>
            <SmallAction label="Open" onPress={() => shareReport(record)} />
            <SmallAction label="Share" onPress={() => shareReport(record)} />
            <SmallAction label="Download Again" onPress={() => downloadReport(record)} />
            {removeReport ? <SmallAction danger disabled={working} label="Remove" onPress={confirmRemove} /> : null}
          </>
        ) : (
          <SmallAction
            disabled={working}
            label={working ? 'Downloading…' : record.status === 'download_failed' ? 'Retry Download' : 'Download PDF'}
            onPress={() => downloadReport(record)}
            primary
          />
        )}
      </View>
      {record.fileSizeBytes ? <Text style={styles.reportRecordMeta}>File size {formatFileSize(record.fileSizeBytes)}</Text> : null}
    </View>
  );
}

function SmallAction({
  danger = false,
  disabled = false,
  label,
  onPress,
  primary = false,
}: {
  danger?: boolean;
  disabled?: boolean;
  label: string;
  onPress: () => void;
  primary?: boolean;
}) {
  return (
    <Pressable
      accessibilityLabel={label}
      accessibilityRole="button"
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        primary ? styles.smallPrimaryButton : danger ? styles.smallDangerButton : styles.smallButton,
        pressed && styles.downloadButtonPressed,
        disabled && styles.downloadButtonDisabled,
      ]}>
      <Text style={primary ? styles.smallPrimaryButtonText : danger ? styles.smallDangerButtonText : styles.smallButtonText}>{label}</Text>
    </Pressable>
  );
}

function ReportPreview({ record }: { record: DailyReportRecord }) {
  const report = record.snapshot;
  if (!report) {
    return <EmptyState title="Preview unavailable" message="This report snapshot is not available." />;
  }
  const copilotContext = createCopilotContext({
    payload: {
      confidence: report.recommendation_confidence,
      conviction: report.market_conviction,
      hiddenConfirmations: report.hidden_confirmations,
      hiddenWarnings: report.hidden_warnings,
      marketDate: record.metadata.marketDate,
      marketEvolution: report.market_evolution,
      playbook: report.decision_dashboard?.playbook,
      previousPlaybookReview: report.previous_playbook_review,
      reportChanges: report.report_changes,
      reportId: report.report_id,
      reportNarrative: report.report_narrative,
      scenarioPlan: report.scenario_plan,
      signalConvergence: report.signal_convergence,
      version: record.metadata.version,
      watchlistRanking: report.watchlist_summary?.items,
    },
    routeName: '/report',
    screenTitle: `Daily Market Report · ${formatMarketDate(record.metadata.marketDate)} · v${record.metadata.version}`,
    screenType: 'report',
    sourceState: record.metadata.sourceState,
  });
  return (
    <View style={styles.detailStack}>
      <AskCopilotButton
        context={copilotContext}
        prompt="Explain this report in simple terms."
      />
      <DashboardCard title="Cover" accentColor={Theme.colors.accent}>
        <View style={styles.metricGrid}>
          <ReportMetricTile label="Market Date" value={formatMarketDate(record.metadata.marketDate)} />
          <ReportMetricTile label="Generated" value={formatDateTime(record.metadata.generatedAt)} />
          <ReportMetricTile label="Session" value={sessionPhaseLabel(record.metadata.sessionPhase)} />
          <ReportMetricTile label="Data" value={sourceStateLabel(record.metadata.sourceState)} />
          <ReportMetricTile label="Condition" value={report.market_regime || report.market_health?.status || 'N/A'} />
          <ReportMetricTile label="Positioning" value={report.decision_dashboard?.playbook.headline || 'N/A'} />
          <ReportMetricTile label="Health" value={report.market_health ? `${report.market_health.overall_score}/100` : 'N/A'} />
          <ReportMetricTile label="Risk" value={report.risk_dashboard ? `${report.risk_dashboard.score}/100` : 'N/A'} />
        </View>
        <Text style={styles.placeholderText}>Informational and educational use only. Not financial advice.</Text>
      </DashboardCard>
      <ReportDetails report={report as DailyReportWithInstitutionalActivity} />
    </View>
  );
}

function ReportDetails({ report }: { report: DailyReportWithInstitutionalActivity }) {
  return (
    <>
      <ExpandableSection
        defaultExpanded
        summary={report.title || 'Daily Market Report'}
        title="Executive Summary">
        <DashboardCard style={styles.heroCard} accentColor={Theme.colors.accent}>
          <Text style={styles.reportDate}>{report.date || 'N/A'}</Text>
          <Text style={styles.reportTitle}>{report.title || 'Daily Market Report'}</Text>
          <Text style={styles.executiveSummary}>{report.executive_summary || 'N/A'}</Text>
        </DashboardCard>

        <DashboardCard title="Market Regime" accentColor={Theme.colors.success}>
          <View style={styles.regimePill}>
            <View style={styles.regimeDot} />
            <Text style={styles.regimeText}>{report.market_regime || 'N/A'}</Text>
          </View>
        </DashboardCard>
      </ExpandableSection>

      <ExpandableSection
        defaultExpanded
        summary={report.ai_summary?.headline || 'N/A'}
        title="Executive AI Brief">
        {report.ai_summary ? (
          <AIInsightCard
            title="Executive AI Brief"
            headline={report.ai_summary.headline}
            summary={report.ai_summary.summary}
            confidence={report.ai_summary.confidence}
            generatedBy={report.ai_summary.generated_by}
            nextUpdate={report.ai_summary.next_update}
            keyPoints={report.ai_summary.key_points}
            opportunities={report.ai_summary.opportunities}
            risks={report.ai_summary.risks}
            whatToWatch={report.ai_summary.what_to_watch}
            disclaimer={report.ai_summary.disclaimer}
          />
        ) : (
          <DashboardCard>
            <Text style={styles.bodyText}>N/A</Text>
          </DashboardCard>
        )}
      </ExpandableSection>

      <ExpandableSection
        summary={
          report.market_health
            ? `${report.market_health.status} · ${formatNullableNumber(report.market_health.overall_score)}`
            : 'N/A'
        }
        title="Market Health">
        {report.market_health ? (
          <MarketHealthSection marketHealth={report.market_health} />
        ) : (
          <DashboardCard>
            <Text style={styles.bodyText}>N/A</Text>
          </DashboardCard>
        )}
      </ExpandableSection>

      <ExpandableSection
        summary={report.decision_dashboard?.playbook.headline || 'N/A'}
        title="Decision Intelligence">
        {report.decision_dashboard ? (
          <DecisionIntelligenceSection decisionDashboard={report.decision_dashboard} />
        ) : (
          <DashboardCard>
            <Text style={styles.bodyText}>N/A</Text>
          </DashboardCard>
        )}
      </ExpandableSection>

      <ExpandableSection
        summary={report.institutional_intelligence?.summary || 'N/A'}
        title="Institutional Intelligence">
        {report.institutional_intelligence ? (
          <InstitutionalIntelligenceSection
            institutionalIntelligence={report.institutional_intelligence}
          />
        ) : (
          <DashboardCard>
            <Text style={styles.bodyText}>N/A</Text>
          </DashboardCard>
        )}
      </ExpandableSection>

      <ExpandableSection
        summary={`${safeCount(report.key_drivers)} drivers · ${safeCount(report.main_risks)} risks`}
        title="Key Drivers & Risks">
        <View style={styles.detailStack}>
          <ReportList title="Key Drivers" items={report.key_drivers} accentColor={Theme.colors.success} />
          <ReportList title="Main Risks" items={report.main_risks} accentColor={Theme.colors.warning} />
        </View>
      </ExpandableSection>

      <ExpandableSection summary={report.sector_leaders?.[0] || 'N/A'} title="Sector Leadership">
        <ReportList
          title="Sector Leadership"
          items={report.sector_leaders}
          accentColor={Theme.colors.accent}
        />
      </ExpandableSection>

      <ExpandableSection summary={report.industry_groups?.summary || 'N/A'} title="Theme Leadership">
        {report.industry_groups ? (
          <IndustryGroupsSection industryGroups={report.industry_groups} />
        ) : (
          <DashboardCard>
            <Text style={styles.bodyText}>N/A</Text>
          </DashboardCard>
        )}
      </ExpandableSection>

      <ExpandableSection summary={report.sector_etfs?.summary || 'N/A'} title="Sector ETF Rotation">
        {report.sector_etfs ? (
          <SectorEtfsSection sectorEtfs={report.sector_etfs} />
        ) : (
          <DashboardCard>
            <Text style={styles.bodyText}>N/A</Text>
          </DashboardCard>
        )}
      </ExpandableSection>

      <ExpandableSection summary={report.cap_rotation?.summary || 'N/A'} title="Market Cap Rotation">
        {report.cap_rotation ? (
          <CapRotationSection capRotation={report.cap_rotation} />
        ) : (
          <DashboardCard>
            <Text style={styles.bodyText}>N/A</Text>
          </DashboardCard>
        )}
      </ExpandableSection>

      <ExpandableSection
        summary={
          report.fear_greed
            ? `${report.fear_greed.score} · ${report.fear_greed.status}`
            : 'N/A'
        }
        title="Fear & Greed Index">
        {report.fear_greed ? (
          <FearGreedSection fearGreed={report.fear_greed} />
        ) : (
          <DashboardCard>
            <Text style={styles.bodyText}>N/A</Text>
          </DashboardCard>
        )}
      </ExpandableSection>

      <ExpandableSection summary={report.institutional_activity?.bias || 'N/A'} title="Institutional Activity">
        {report.institutional_activity ? (
          <InstitutionalActivitySection institutionalActivity={report.institutional_activity} />
        ) : (
          <DashboardCard>
            <Text style={styles.bodyText}>N/A</Text>
          </DashboardCard>
        )}
      </ExpandableSection>

      <ExpandableSection summary={report.volume_analysis?.best_volume_setup || 'N/A'} title="Volume Analysis">
        {report.volume_analysis ? (
          <VolumeAnalysisSection volumeAnalysis={report.volume_analysis} />
        ) : (
          <DashboardCard>
            <Text style={styles.bodyText}>N/A</Text>
          </DashboardCard>
        )}
      </ExpandableSection>

      <ExpandableSection summary={report.risk_plans?.best_risk_reward_setup || 'N/A'} title="Risk Plans">
        {report.risk_plans ? (
          <RiskPlansSection riskPlans={report.risk_plans} />
        ) : (
          <DashboardCard>
            <Text style={styles.bodyText}>N/A</Text>
          </DashboardCard>
        )}
      </ExpandableSection>

      <ExpandableSection summary={report.multi_timeframe?.strongest_alignment_stock || 'N/A'} title="Multi-Timeframe">
        {report.multi_timeframe ? (
          <MultiTimeframeSection multiTimeframe={report.multi_timeframe} />
        ) : (
          <DashboardCard>
            <Text style={styles.bodyText}>N/A</Text>
          </DashboardCard>
        )}
      </ExpandableSection>

      <ExpandableSection summary={report.tomorrow_watch?.[0] || 'N/A'} title="Tomorrow Watch">
        <ReportList
          title="Tomorrow Watch"
          items={report.tomorrow_watch}
          accentColor={Theme.colors.warning}
        />
      </ExpandableSection>

      <ExpandableSection summary={report.strategy_note || 'N/A'} title="Strategy Note">
        <DashboardCard title="Strategy Note" accentColor={Theme.colors.accent}>
          <Text style={styles.bodyText}>{report.strategy_note || 'N/A'}</Text>
        </DashboardCard>
      </ExpandableSection>
    </>
  );
}

function MarketHealthSection({
  marketHealth,
}: {
  marketHealth: NonNullable<DailyReport['market_health']>;
}) {
  return (
    <DashboardCard title="Market Health" accentColor={Theme.colors.success}>
      <View style={styles.metricGrid}>
        <ReportMetricTile label="Score" value={formatNullableNumber(marketHealth.overall_score)} />
        <ReportMetricTile label="Status" value={marketHealth.status || 'N/A'} />
        <ReportMetricTile label="Momentum" value={formatNullableNumber(marketHealth.components.momentum)} />
        <ReportMetricTile label="Breadth" value={formatNullableNumber(marketHealth.components.breadth)} />
        <ReportMetricTile label="Trend" value={formatNullableNumber(marketHealth.components.trend)} />
        <ReportMetricTile label="Volume" value={formatNullableNumber(marketHealth.components.volume)} />
        <ReportMetricTile label="Institutional" value={formatNullableNumber(marketHealth.components.institutional)} />
        <ReportMetricTile label="Volatility" value={formatNullableNumber(marketHealth.components.volatility)} />
        <ReportMetricTile label="Sector Strength" value={formatNullableNumber(marketHealth.components.sector_strength)} />
      </View>
      <View style={styles.summaryBox}>
        <Text style={styles.summaryLabel}>Summary</Text>
        <Text style={styles.bodyText}>{marketHealth.summary || 'N/A'}</Text>
      </View>
      <View style={styles.summaryBox}>
        <Text style={styles.summaryLabel}>Improving Factors</Text>
        <Text style={styles.bodyText}>{marketHealth.improving_factors?.join(' · ') || 'N/A'}</Text>
      </View>
      <View style={styles.summaryBox}>
        <Text style={styles.summaryLabel}>Weakening Factors</Text>
        <Text style={styles.bodyText}>{marketHealth.weakening_factors?.join(' · ') || 'N/A'}</Text>
      </View>
    </DashboardCard>
  );
}

function DecisionIntelligenceSection({
  decisionDashboard,
}: {
  decisionDashboard: NonNullable<DailyReport['decision_dashboard']>;
}) {
  const { aggressiveness, checklist, playbook, trading_styles } = decisionDashboard;
  const probabilities = decisionDashboard.probabilities;
  const leadership = decisionDashboard.leadership;
  const decisionConfidence = decisionDashboard.decision_confidence;
  const comparison = decisionDashboard.comparison;
  const riskDashboard = decisionDashboard.risk_dashboard;
  const industryRotation = decisionDashboard.industry_rotation;

  return (
    <DashboardCard title="Decision Intelligence" accentColor={Theme.colors.accent}>
      <View style={styles.metricGrid}>
        <ReportMetricTile label="Playbook" value={playbook.headline || 'N/A'} />
        <ReportMetricTile label="Preferred Strategy" value={playbook.preferred_strategy || 'N/A'} />
        <ReportMetricTile label="Aggressiveness" value={`${aggressiveness.status} · ${formatNullableNumber(aggressiveness.score)}`} />
        <ReportMetricTile label="Decision Confidence" value={`${decisionConfidence.status} · ${formatNullableNumber(decisionConfidence.score)}`} />
        <ReportMetricTile
          label="Top Probability"
          value={
            probabilities.items[0]
              ? `${probabilities.items[0].strategy} · ${probabilities.items[0].probability}%`
              : 'N/A'
          }
        />
        <ReportMetricTile label="Checklist" value={`${checklist.score}/${checklist.max_score} · ${checklist.grade}`} />
        <ReportMetricTile label="Stocks / Cash" value={`${aggressiveness.suggested_exposure.stocks}% / ${aggressiveness.suggested_exposure.cash}%`} />
        <ReportMetricTile label="Preferred Style" value={trading_styles.preferred_style || 'N/A'} />
        <ReportMetricTile label="Risk Score" value={formatNullableNumber(riskDashboard.score)} />
      </View>
      <View style={styles.summaryBox}>
        <Text style={styles.summaryLabel}>Summary</Text>
        <Text style={styles.bodyText}>{playbook.summary || 'N/A'}</Text>
      </View>
      <View style={styles.summaryBox}>
        <Text style={styles.summaryLabel}>Main Risk</Text>
        <Text style={styles.bodyText}>{playbook.main_risk || 'N/A'}</Text>
      </View>
      <View style={styles.summaryBox}>
        <Text style={styles.summaryLabel}>Leadership</Text>
        <Text style={styles.bodyText}>{leadership.summary || 'N/A'}</Text>
      </View>
      <View style={styles.summaryBox}>
        <Text style={styles.summaryLabel}>Comparison</Text>
        <Text style={styles.bodyText}>{comparison.summary || 'N/A'}</Text>
      </View>
      <View style={styles.summaryBox}>
        <Text style={styles.summaryLabel}>Industry Rotation</Text>
        <Text style={styles.bodyText}>{industryRotation.summary || 'N/A'}</Text>
      </View>
      <View style={styles.alertList}>
        <Text style={styles.alertTitle}>Action Guidelines</Text>
        {(playbook.action_guidelines?.length ? playbook.action_guidelines : ['N/A']).map((item, index) => (
          <View key={`${formatPrimitiveText(item)}-${index}`} style={styles.listItem}>
            <View style={[styles.bullet, { backgroundColor: Theme.colors.accent }]} />
            <Text style={styles.bodyText}>{formatPrimitiveText(item)}</Text>
          </View>
        ))}
      </View>
    </DashboardCard>
  );
}

function InstitutionalIntelligenceSection({
  institutionalIntelligence,
}: {
  institutionalIntelligence: NonNullable<DailyReport['institutional_intelligence']>;
}) {
  return (
    <DashboardCard title="Institutional Intelligence" accentColor={Theme.colors.accent}>
      <View style={styles.metricGrid}>
        <ReportMetricTile
          label="Sentiment"
          value={`${institutionalIntelligence.sentiment.score} · ${institutionalIntelligence.sentiment.status}`}
        />
        <ReportMetricTile
          label="Money Flow"
          value={`${institutionalIntelligence.money_flow.score} · ${institutionalIntelligence.money_flow.status}`}
        />
        <ReportMetricTile
          label="Institutional"
          value={`${institutionalIntelligence.institutional.score} · ${institutionalIntelligence.institutional.status}`}
        />
        <ReportMetricTile
          label="Options"
          value={`${institutionalIntelligence.options.score} · ${institutionalIntelligence.options.status}`}
        />
        <ReportMetricTile
          label="Liquidity"
          value={`${institutionalIntelligence.liquidity.score} · ${institutionalIntelligence.liquidity.status}`}
        />
      </View>
      <View style={styles.summaryBox}>
        <Text style={styles.summaryLabel}>Summary</Text>
        <Text style={styles.bodyText}>{formatPrimitiveText(institutionalIntelligence.summary)}</Text>
      </View>
      <View style={styles.summaryBox}>
        <Text style={styles.summaryLabel}>Money Flow Leader</Text>
        <Text style={styles.bodyText}>
          {institutionalIntelligence.money_flow.items[0]
            ? `${institutionalIntelligence.money_flow.items[0].area}: ${formatPrimitiveText(institutionalIntelligence.money_flow.items[0].summary)}`
            : 'N/A'}
        </Text>
      </View>
      <View style={styles.summaryBox}>
        <Text style={styles.summaryLabel}>Options Sentiment</Text>
        <Text style={styles.bodyText}>{formatPrimitiveText(institutionalIntelligence.options.summary)}</Text>
      </View>
      <View style={styles.alertList}>
        <Text style={styles.alertTitle}>Liquidity Warnings</Text>
        {(institutionalIntelligence.liquidity.warnings?.length
          ? institutionalIntelligence.liquidity.warnings
          : ['N/A']
        ).map((item, index) => (
          <View key={`${formatPrimitiveText(item)}-${index}`} style={styles.listItem}>
            <View style={[styles.bullet, { backgroundColor: Theme.colors.warning }]} />
            <Text style={styles.bodyText}>{formatPrimitiveText(item)}</Text>
          </View>
        ))}
      </View>
    </DashboardCard>
  );
}

function SectorEtfsSection({
  sectorEtfs,
}: {
  sectorEtfs: NonNullable<DailyReport['sector_etfs']>;
}) {
  return (
    <DashboardCard title="Sector ETF Rotation" accentColor={Theme.colors.purple}>
      <Text style={styles.bodyText}>{sectorEtfs.summary}</Text>
      <View style={styles.metricGrid}>
        {sectorEtfs.items.slice(0, 6).map((item) => (
          <ReportMetricTile
            key={item.symbol}
            label={`${item.symbol} · ${item.sector}`}
            value={`${item.status} · RS ${item.relative_strength_score}`}
          />
        ))}
      </View>
    </DashboardCard>
  );
}

function IndustryGroupsSection({
  industryGroups,
}: {
  industryGroups: NonNullable<DailyReport['industry_groups']>;
}) {
  return (
    <DashboardCard title="Theme Leadership" accentColor={Theme.colors.accent}>
      <Text style={styles.bodyText}>{industryGroups.summary}</Text>
      <View style={styles.metricGrid}>
        {industryGroups.items.slice(0, 6).map((item) => (
          <ReportMetricTile
            key={item.name}
            label={`${item.name} · ${item.parent_sector}`}
            value={`${item.status} · RS ${item.relative_strength_score}`}
          />
        ))}
      </View>
    </DashboardCard>
  );
}

function CapRotationSection({
  capRotation,
}: {
  capRotation: NonNullable<DailyReport['cap_rotation']>;
}) {
  return (
    <DashboardCard title="Market Cap Rotation" accentColor={Theme.colors.accent}>
      <View style={styles.metricGrid}>
        <ReportMetricTile label="Leader" value={capRotation.leader} />
        <ReportMetricTile label="Laggard" value={capRotation.laggard} />
      </View>
      <View style={styles.summaryBox}>
        <Text style={styles.summaryLabel}>Summary</Text>
        <Text style={styles.bodyText}>{capRotation.summary}</Text>
      </View>
      <View style={styles.metricGrid}>
        {capRotation.items.map((item) => (
          <ReportMetricTile
            key={item.category}
            label={`${item.category} · ${item.symbol}`}
            value={`${item.status} · ${formatNullableNumber(item.score)}`}
          />
        ))}
      </View>
    </DashboardCard>
  );
}

function FearGreedSection({
  fearGreed,
}: {
  fearGreed: NonNullable<DailyReport['fear_greed']>;
}) {
  return (
    <DashboardCard title="Fear & Greed Index" accentColor={Theme.colors.warning}>
      <View style={styles.metricGrid}>
        <ReportMetricTile label="Score" value={formatNullableNumber(fearGreed.score)} />
        <ReportMetricTile label="Status" value={fearGreed.status} />
      </View>
      <View style={styles.summaryBox}>
        <Text style={styles.summaryLabel}>Summary</Text>
        <Text style={styles.bodyText}>{fearGreed.summary}</Text>
      </View>
      <View style={styles.metricGrid}>
        {fearGreed.components.map((component) => (
          <ReportMetricTile
            key={component.key}
            label={component.label}
            value={`${formatNullableNumber(component.score)} · ${component.status}`}
          />
        ))}
      </View>
    </DashboardCard>
  );
}

function InstitutionalActivitySection({
  institutionalActivity,
}: {
  institutionalActivity: InstitutionalActivityBias;
}) {
  return (
    <DashboardCard title="Institutional Activity" accentColor={Theme.colors.accent}>
      <View style={styles.metricGrid}>
        <ReportMetricTile label="Bias" value={institutionalActivity.bias || 'N/A'} />
        <ReportMetricTile
          label="Distribution Days"
          value={formatNullableNumber(institutionalActivity.distribution_count)}
        />
        <ReportMetricTile
          label="Accumulation Days"
          value={formatNullableNumber(institutionalActivity.accumulation_count)}
        />
        <ReportMetricTile
          label="Stall Days"
          value={formatNullableNumber(institutionalActivity.stall_count)}
        />
        <ReportMetricTile
          label="Churning Days"
          value={formatNullableNumber(institutionalActivity.churning_count)}
        />
        <ReportMetricTile
          label="Follow-Through Day"
          value={institutionalActivity.follow_through_day?.triggered ? 'Triggered' : 'Not triggered'}
        />
      </View>
      <View style={styles.summaryBox}>
        <Text style={styles.summaryLabel}>Institutional Summary</Text>
        <Text style={styles.bodyText}>{institutionalActivity.summary || 'N/A'}</Text>
      </View>
    </DashboardCard>
  );
}

function MultiTimeframeSection({
  multiTimeframe,
}: {
  multiTimeframe: NonNullable<DailyReport['multi_timeframe']>;
}) {
  return (
    <DashboardCard title="Multi-Timeframe" accentColor={Theme.colors.accent}>
      <View style={styles.metricGrid}>
        <ReportMetricTile
          label="Strongest Alignment Stock"
          value={multiTimeframe.strongest_alignment_stock || 'N/A'}
        />
        <ReportMetricTile
          label="Weakest Alignment Stock"
          value={multiTimeframe.weakest_alignment_stock || 'N/A'}
        />
      </View>
      <View style={styles.summaryBox}>
        <Text style={styles.summaryLabel}>Alignment Summary</Text>
        <Text style={styles.bodyText}>{multiTimeframe.summary || 'N/A'}</Text>
      </View>
    </DashboardCard>
  );
}

function RiskPlansSection({
  riskPlans,
}: {
  riskPlans: NonNullable<DailyReport['risk_plans']>;
}) {
  return (
    <DashboardCard title="Risk Plans" accentColor={Theme.colors.warning}>
      <View style={styles.metricGrid}>
        <ReportMetricTile
          label="Best Risk/Reward Setup"
          value={riskPlans.best_risk_reward_setup || 'N/A'}
        />
        <ReportMetricTile
          label="Highest Risk Stock"
          value={riskPlans.highest_risk_stock || 'N/A'}
        />
      </View>
      <View style={styles.summaryBox}>
        <Text style={styles.summaryLabel}>Risk Summary</Text>
        <Text style={styles.bodyText}>{riskPlans.risk_summary || 'N/A'}</Text>
      </View>
    </DashboardCard>
  );
}

function VolumeAnalysisSection({
  volumeAnalysis,
}: {
  volumeAnalysis: NonNullable<DailyReport['volume_analysis']>;
}) {
  return (
    <DashboardCard title="Volume Analysis" accentColor={Theme.colors.success}>
      <View style={styles.metricGrid}>
        <ReportMetricTile
          label="Highest Relative Volume"
          value={volumeAnalysis.highest_relative_volume || 'N/A'}
        />
        <ReportMetricTile
          label="Best Volume Setup"
          value={volumeAnalysis.best_volume_setup || 'N/A'}
        />
      </View>

      <View style={styles.alertList}>
        <Text style={styles.alertTitle}>Distribution Volume Alerts</Text>
        {(volumeAnalysis.distribution_volume_alerts?.length
          ? volumeAnalysis.distribution_volume_alerts
          : ['N/A']
        ).map((item, index) => (
          <View key={`${formatPrimitiveText(item)}-${index}`} style={styles.listItem}>
            <View style={[styles.bullet, { backgroundColor: Theme.colors.warning }]} />
            <Text style={styles.bodyText}>{formatPrimitiveText(item)}</Text>
          </View>
        ))}
      </View>
    </DashboardCard>
  );
}

function ReportMetricTile({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.metricTile}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>{value}</Text>
    </View>
  );
}

function formatPrimitiveText(value: unknown, fallback = 'N/A') {
  if (typeof value === 'string' || typeof value === 'number') {
    return String(value);
  }
  return fallback;
}

function ReportList({
  accentColor,
  items,
  title,
}: {
  accentColor: string;
  items: string[];
  title: string;
}) {
  return (
    <DashboardCard title={title} accentColor={accentColor}>
      <View style={styles.list}>
        {(items?.length ? items : ['N/A']).map((item, index) => (
          <View key={`${formatPrimitiveText(item)}-${index}`} style={styles.listItem}>
            <View style={[styles.bullet, { backgroundColor: accentColor }]} />
            <Text style={styles.bodyText}>{formatPrimitiveText(item)}</Text>
          </View>
        ))}
      </View>
    </DashboardCard>
  );
}

function formatNullableNumber(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return 'N/A';
  }

  return value.toLocaleString('en-US', {
    maximumFractionDigits: 0,
  });
}

function safeCount(items?: unknown[]) {
  return items?.length ?? 0;
}

function getStatusPresentation(status: ReportStatus): { label: string; tone: Tone } {
  switch (status) {
    case 'generating':
      return { label: 'Generating', tone: 'info' };
    case 'downloading':
      return { label: 'Downloading', tone: 'info' };
    case 'downloaded':
      return { label: 'Downloaded', tone: 'success' };
    case 'generation_failed':
      return { label: 'Generation failed', tone: 'danger' };
    case 'download_failed':
      return { label: 'Download failed', tone: 'danger' };
    case 'stale':
      return { label: 'Stale', tone: 'warning' };
    case 'ready':
    default:
      return { label: 'Ready to download', tone: 'info' };
  }
}

function sourceStateLabel(source: ReportSourceState) {
  switch (source) {
    case 'live':
      return 'Live data';
    case 'delayed':
      return 'Delayed data';
    case 'cached':
      return 'Cached data';
    case 'stale':
      return 'Stale data';
    case 'mock':
      return 'Test data';
    case 'mixed':
      return 'Mixed sources';
    default:
      return 'Source unavailable';
  }
}

function sourceTone(source: ReportSourceState): Tone {
  switch (source) {
    case 'live':
      return 'success';
    case 'cached':
    case 'mixed':
      return 'info';
    case 'mock':
    case 'stale':
    case 'delayed':
      return 'warning';
    default:
      return 'muted';
  }
}

function sessionPhaseLabel(phase: DailyReportRecord['metadata']['sessionPhase']) {
  switch (phase) {
    case 'pre_market':
      return 'Pre-market';
    case 'market_open':
      return 'Market hours';
    case 'after_market':
      return 'After market';
    case 'weekend':
      return 'Weekend';
    default:
      return 'Session unavailable';
  }
}

function formatMarketDate(value: string) {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return 'N/A';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString(undefined, {
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    month: 'short',
  });
}

function formatFileSize(value: number) {
  if (value < 1024 * 1024) {
    return `${Math.max(1, Math.round(value / 1024))} KB`;
  }
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: Theme.colors.background,
    flex: 1,
  },
  content: {
    gap: Spacing.three,
    padding: Spacing.three,
    paddingBottom: Spacing.six,
  },
  header: {
    gap: Spacing.one,
    paddingTop: Spacing.two,
  },
  title: {
    color: Theme.colors.textInverse,
    fontSize: 29,
    fontWeight: '900',
  },
  subtitle: {
    color: Theme.colors.textInverseMuted,
    fontSize: 15,
    lineHeight: 22,
  },
  heroCard: {
    backgroundColor: Theme.colors.cardElevated,
  },
  reportDate: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    fontWeight: '800',
    marginBottom: Spacing.two,
  },
  reportTitle: {
    color: Theme.colors.text,
    fontSize: 27,
    fontWeight: '900',
    marginBottom: Spacing.two,
  },
  executiveSummary: {
    color: Theme.colors.textMuted,
    fontSize: 15,
    lineHeight: 23,
  },
  summaryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  skeletonStack: {
    gap: Spacing.three,
  },
  generateButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.accent,
    borderRadius: Theme.radii.small,
    minHeight: 44,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.twoAndHalf,
  },
  generateButtonText: {
    color: Theme.colors.background,
    fontSize: 15,
    fontWeight: '900',
  },
  reportCardStack: {
    gap: Spacing.two,
  },
  reportRecordCard: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.two,
    padding: Spacing.twoAndHalf,
  },
  reportRecordHeader: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  reportRecordTitleBlock: {
    flex: 1,
    gap: 2,
    minWidth: 0,
  },
  reportRecordTitle: {
    color: Theme.colors.text,
    fontSize: 15,
    fontWeight: '900',
  },
  reportRecordDate: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '800',
  },
  reportRecordMeta: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
    lineHeight: 17,
  },
  reportBadgeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.one,
  },
  recordActions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  smallButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    minHeight: 38,
    paddingHorizontal: Spacing.twoAndHalf,
    paddingVertical: Spacing.two,
  },
  smallButtonText: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '900',
  },
  smallPrimaryButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.accent,
    borderRadius: Theme.radii.small,
    minHeight: 38,
    paddingHorizontal: Spacing.twoAndHalf,
    paddingVertical: Spacing.two,
  },
  smallPrimaryButtonText: {
    color: Theme.colors.background,
    fontSize: 12,
    fontWeight: '900',
  },
  smallDangerButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.dangerSoft,
    borderColor: Theme.colors.danger,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    minHeight: 38,
    paddingHorizontal: Spacing.twoAndHalf,
    paddingVertical: Spacing.two,
  },
  smallDangerButtonText: {
    color: Theme.colors.danger,
    fontSize: 12,
    fontWeight: '900',
  },
  detailStack: {
    gap: Spacing.three,
  },
  regimePill: {
    alignItems: 'center',
    alignSelf: 'flex-start',
    backgroundColor: Theme.colors.successSoft,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.two,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
  },
  regimeDot: {
    backgroundColor: Theme.colors.success,
    borderRadius: 5,
    height: 10,
    width: 10,
  },
  regimeText: {
    color: Theme.colors.text,
    fontSize: 15,
    fontWeight: '900',
  },
  list: {
    gap: Spacing.two,
  },
  listItem: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
  },
  bullet: {
    borderRadius: 4,
    height: 8,
    marginTop: 7,
    width: 8,
  },
  bodyText: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: 15,
    lineHeight: 23,
  },
  metricGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  metricTile: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexGrow: 1,
    minWidth: '47%',
    padding: Spacing.twoAndHalf,
  },
  metricLabel: {
    color: Theme.colors.textMuted,
    fontSize: 11,
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
  alertList: {
    gap: Spacing.two,
    marginTop: Spacing.three,
  },
  alertTitle: {
    color: Theme.colors.warning,
    fontSize: 12,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  summaryBox: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    marginTop: Spacing.three,
    padding: Spacing.twoAndHalf,
  },
  summaryLabel: {
    color: Theme.colors.warning,
    fontSize: 11,
    fontWeight: '900',
    marginBottom: Spacing.one,
    textTransform: 'uppercase',
  },
  downloadButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.accent,
    borderRadius: Theme.radii.small,
    minHeight: 44,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.twoAndHalf,
  },
  downloadButtonDisabled: {
    opacity: 0.55,
  },
  downloadButtonPressed: {
    opacity: 0.78,
  },
  downloadButtonText: {
    color: Theme.colors.background,
    fontSize: 15,
    fontWeight: '900',
  },
  placeholderText: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    lineHeight: 19,
    marginTop: Spacing.two,
  },
  errorText: {
    color: Theme.colors.danger,
    fontSize: 13,
    fontWeight: '800',
    lineHeight: 19,
    marginTop: Spacing.two,
  },
  actionRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  secondaryButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    minHeight: 44,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.twoAndHalf,
  },
  secondaryButtonText: {
    color: Theme.colors.text,
    fontSize: 13,
    fontWeight: '900',
  },
});
