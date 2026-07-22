import { SymbolView } from 'expo-symbols';
import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';

import { ExpandableSection } from '@/components/ui/ExpandableSection';
import { StatusBadge, type Tone } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';
import type { DailyReportRecord, ReportSourceState, ReportStatus } from '@/features/reports/reportLibraryModel';

export function ReportHistorySection({
  defaultExpanded = false,
  downloadReport,
  onPreview,
  records,
  removeReport,
  shareReport,
  title,
  workingId,
}: {
  defaultExpanded?: boolean;
  downloadReport: (record: DailyReportRecord) => Promise<DailyReportRecord | null>;
  onPreview: (record: DailyReportRecord) => void;
  records: DailyReportRecord[];
  removeReport?: (record: DailyReportRecord) => Promise<boolean>;
  shareReport: (record: DailyReportRecord) => Promise<void>;
  title: string;
  workingId: string | null;
}) {
  const latest = records[0]?.metadata.generatedAt;
  return (
    <ExpandableSection
      defaultExpanded={defaultExpanded}
      summary={`${records.length} ${records.length === 1 ? 'report' : 'reports'}${latest ? ` · Latest ${formatDateTime(latest)}` : ''}`}
      title={title}>
      <View style={styles.stack}>
        {records.length ? records.map((record) => (
          <ReportHistoryRow
            downloadReport={downloadReport}
            key={record.id}
            onPreview={onPreview}
            record={record}
            removeReport={removeReport}
            shareReport={shareReport}
            working={workingId === record.id}
          />
        )) : <Text style={styles.emptyText}>No reports in this period.</Text>}
      </View>
    </ExpandableSection>
  );
}

function ReportHistoryRow({
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
  const status = statusPresentation(working ? 'downloading' : record.status);
  const confirmRemove = () => {
    if (!removeReport) return;
    Alert.alert(
      'Delete downloaded copy?',
      'The frozen report remains in history and can be downloaded again.',
      [
        { style: 'cancel', text: 'Cancel' },
        { onPress: () => void removeReport(record), style: 'destructive', text: 'Delete Copy' },
      ],
    );
  };
  return (
    <View style={styles.row}>
      <Pressable
        accessibilityLabel={`Preview report from ${record.metadata.marketDate}`}
        accessibilityRole="button"
        disabled={!record.snapshot}
        onPress={() => onPreview(record)}
        style={({ pressed }) => [styles.rowMain, pressed && styles.pressed]}>
        <View style={styles.dateBlock}>
          <Text style={styles.date}>{formatMarketDate(record.metadata.marketDate)}</Text>
          <Text style={styles.meta}>v{record.metadata.version} · {formatDateTime(record.metadata.generatedAt)}</Text>
        </View>
        <View style={styles.badges}>
          <StatusBadge label={sourceLabel(record.metadata.sourceState)} tone={sourceTone(record.metadata.sourceState)} />
          <StatusBadge label={status.label} tone={status.tone} />
        </View>
      </Pressable>
      <View style={styles.actions}>
        <IconAction icon="eye.fill" label="Preview" onPress={() => onPreview(record)} />
        <IconAction
          disabled={working}
          icon="arrow.down.circle.fill"
          label={working ? 'Downloading report' : 'Download PDF'}
          onPress={() => void downloadReport(record)}
        />
        {record.status === 'downloaded' ? <IconAction icon="square.and.arrow.up" label="Share report" onPress={() => void shareReport(record)} /> : null}
        {record.status === 'downloaded' && removeReport ? <IconAction danger icon="trash.fill" label="Delete downloaded copy" onPress={confirmRemove} /> : null}
      </View>
    </View>
  );
}

function IconAction({ danger = false, disabled = false, icon, label, onPress }: { danger?: boolean; disabled?: boolean; icon: string; label: string; onPress: () => void }) {
  return (
    <Pressable
      accessibilityLabel={label}
      accessibilityRole="button"
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [styles.iconButton, danger && styles.dangerButton, pressed && styles.pressed, disabled && styles.disabled]}>
      <SymbolView name={icon as never} size={16} tintColor={danger ? Theme.colors.danger : Theme.colors.textMuted} weight="bold" />
    </Pressable>
  );
}

function statusPresentation(status: ReportStatus): { label: string; tone: Tone } {
  if (status === 'downloaded') return { label: 'Downloaded', tone: 'success' };
  if (status === 'downloading') return { label: 'Downloading', tone: 'warning' };
  if (status === 'download_failed' || status === 'generation_failed') return { label: 'Retry', tone: 'danger' };
  if (status === 'stale') return { label: 'Archived', tone: 'muted' };
  return { label: 'Ready', tone: 'success' };
}

function sourceLabel(state: ReportSourceState) {
  return state === 'mock' ? 'Test data' : state.charAt(0).toUpperCase() + state.slice(1);
}

function sourceTone(state: ReportSourceState): Tone {
  if (state === 'live') return 'success';
  if (state === 'mock' || state === 'unavailable') return 'danger';
  return 'warning';
}

function formatMarketDate(value: string) {
  const date = new Date(`${value}T12:00:00`);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('en-US', { day: 'numeric', month: 'short', year: 'numeric' }).format(date);
}

function formatDateTime(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: '2-digit', month: 'short', day: 'numeric' }).format(date);
}

const styles = StyleSheet.create({
  actions: { flexDirection: 'row', gap: Spacing.one },
  badges: { alignItems: 'flex-end', gap: Spacing.one },
  dangerButton: { backgroundColor: Theme.colors.dangerSoft },
  date: { color: Theme.colors.text, fontSize: 14, fontWeight: '900' },
  dateBlock: { flex: 1, gap: Spacing.one, minWidth: 0 },
  disabled: { opacity: 0.5 },
  emptyText: { color: Theme.colors.textMuted, fontSize: 13, lineHeight: 19 },
  iconButton: { alignItems: 'center', backgroundColor: Theme.colors.card, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, height: 38, justifyContent: 'center', width: 38 },
  meta: { color: Theme.colors.textMuted, fontSize: 11, fontWeight: '700' },
  pressed: { opacity: 0.7 },
  row: { alignItems: 'center', borderBottomColor: Theme.colors.border, borderBottomWidth: 1, flexDirection: 'row', gap: Spacing.two, paddingBottom: Spacing.twoAndHalf },
  rowMain: { alignItems: 'center', flex: 1, flexDirection: 'row', gap: Spacing.two, minWidth: 0 },
  stack: { gap: Spacing.twoAndHalf },
});
