import { useMemo, useState } from 'react';
import { useLocalSearchParams } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { AppScreen } from '@/components/ui/AppScreen';
import { DetailModal } from '@/components/ui/DetailModal';
import { EmptyState } from '@/components/ui/EmptyState';
import { SkeletonCard } from '@/components/ui/SkeletonCard';
import { Spacing, Theme } from '@/constants/theme';
import { createCopilotContext } from '@/features/copilot/context/buildScreenContext';
import { DailyBriefingPreview } from '@/features/reports/components/DailyBriefingPreview';
import { ReportHistorySection } from '@/features/reports/components/ReportHistorySection';
import { ReportLandingCard } from '@/features/reports/components/ReportLandingCard';
import { compareReportRecords, type DailyReportRecord } from '@/features/reports/reportLibraryModel';
import { useDailyReportLibrary } from '@/features/reports/useDailyReportLibrary';

export default function ReportScreen() {
  const {
    actionNonce: actionNonceParam,
    reportId: reportIdParam,
    sectionId: sectionIdParam,
  } = useLocalSearchParams<{
    actionNonce?: string | string[];
    reportId?: string | string[];
    sectionId?: string | string[];
  }>();
  const requestedReportId = firstParam(reportIdParam);
  const requestedSectionId = firstParam(sectionIdParam);
  const actionNonce = firstParam(actionNonceParam);
  const [selectedOverride, setSelectedRecord] = useState<DailyReportRecord | null>(null);
  const [dismissedDeepLinkKey, setDismissedDeepLinkKey] = useState<string | null>(null);
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
    workingId,
  } = useDailyReportLibrary();
  const latestRecord = useMemo(
    () => [...records].filter((record) => record.snapshot).sort(compareReportRecords)[0] ?? null,
    [records],
  );
  const sectionProps = {
    downloadReport,
    onPreview: setSelectedRecord,
    shareReport,
    workingId,
  };
  const deepLinkKey = `${requestedReportId}:${requestedSectionId}:${actionNonce}`;
  const deepLinkedRecord = useMemo(() => {
    if ((!requestedReportId && !requestedSectionId && !actionNonce) || dismissedDeepLinkKey === deepLinkKey) return null;
    const requested = records.find((record) => (
      record.id === requestedReportId
      || record.snapshot?.report_id === requestedReportId
    ));
    return requested ?? latestRecord;
  }, [actionNonce, deepLinkKey, dismissedDeepLinkKey, latestRecord, records, requestedReportId, requestedSectionId]);
  const selectedRecord = selectedOverride ?? deepLinkedRecord;
  const copilotContext = useMemo(() => createCopilotContext({
    payload: latestRecord?.snapshot ? {
      marketDate: latestRecord.metadata.marketDate,
      reportId: latestRecord.snapshot.report_id,
      reportNarrative: latestRecord.snapshot.report_narrative,
      researchFocus: latestRecord.snapshot.report_document?.research_focus,
      thesis: latestRecord.snapshot.report_document?.thesis,
    } : { availability: 'No generated report is loaded.' },
    routeName: '/report',
    screenTitle: latestRecord ? `Daily Report · ${latestRecord.metadata.marketDate}` : 'Daily Report Library',
    screenType: 'report',
    sourceState: latestRecord?.metadata.sourceState,
  }), [latestRecord]);

  return (
    <AppScreen
      copilotContext={copilotContext}
      copilotPrompt="Explain the latest report thesis, its main contradiction, and what matters next."
      showBackButton
      title="Daily Market Intelligence"
      subtitle="A decision-ready briefing built from market structure, leadership, risk, and your watchlist.">
      <ReportLandingCard
        generationMessage={generationMessage}
        isGenerating={workingId === 'generate'}
        latestRecord={latestRecord}
        onGenerate={() => void generateTodayReport()}
        onPreview={setSelectedRecord}
      />

      {error ? <View style={styles.errorBanner}><Text style={styles.errorText}>{error}</Text></View> : null}
      {loading ? <View style={styles.skeletonStack}><SkeletonCard rows={5} /><SkeletonCard compact rows={2} /></View> : null}

      {!loading ? (
        <View style={styles.historyStack}>
          <Text style={styles.sectionLabel}>REPORT HISTORY</Text>
          <ReportHistorySection {...sectionProps} defaultExpanded records={grouped.today} title="Today's Report" />
          <ReportHistorySection {...sectionProps} records={grouped.thisWeek} title="This Week" />
          <ReportHistorySection {...sectionProps} records={grouped.previous} title="Previous Reports" />
          <ReportHistorySection {...sectionProps} records={grouped.archived} title="Archived" />
          <ReportHistorySection
            {...sectionProps}
            records={grouped.downloaded}
            removeReport={removeReport}
            title="Downloaded"
          />
        </View>
      ) : null}

      {!loading && records.length === 0 ? (
        <EmptyState
          title="Your first briefing is ready to be built"
          message="Generate today's report to establish the baseline for future change analysis."
        />
      ) : null}

      <DetailModal
        onClose={() => {
          setSelectedRecord(null);
          setDismissedDeepLinkKey(deepLinkKey);
        }}
        subtitle={selectedRecord ? `${formatMarketDate(selectedRecord.metadata.marketDate)} · Version ${selectedRecord.metadata.version}` : undefined}
        title="Daily Market Intelligence Briefing"
        visible={Boolean(selectedRecord)}>
        {selectedRecord ? <DailyBriefingPreview initialSectionId={requestedSectionId || undefined} record={selectedRecord} /> : null}
      </DetailModal>
    </AppScreen>
  );
}

function firstParam(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] ?? '' : value ?? '';
}

function formatMarketDate(value: string) {
  const parsed = new Date(`${value}T12:00:00`);
  return Number.isNaN(parsed.getTime())
    ? value
    : new Intl.DateTimeFormat('en-US', { day: 'numeric', month: 'long', year: 'numeric' }).format(parsed);
}

const styles = StyleSheet.create({
  errorBanner: {
    backgroundColor: Theme.colors.dangerSoft,
    borderColor: Theme.colors.danger,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    padding: Spacing.twoAndHalf,
  },
  errorText: { color: Theme.colors.danger, fontSize: 13, fontWeight: '800' },
  historyStack: { gap: Spacing.twoAndHalf },
  sectionLabel: { color: Theme.colors.textMuted, fontSize: 11, fontWeight: '900', marginTop: Spacing.two },
  skeletonStack: { gap: Spacing.three },
});
