import type { DailyReport } from '@/types/market';

export type ReportSourceState = 'live' | 'delayed' | 'cached' | 'stale' | 'mock' | 'mixed' | 'unavailable';
export type ReportSessionPhase = 'pre_market' | 'market_open' | 'after_market' | 'weekend';
export type ReportStatus =
  | 'generating'
  | 'ready'
  | 'downloading'
  | 'downloaded'
  | 'generation_failed'
  | 'download_failed'
  | 'stale';

export type ReportMetadata = {
  generatedAt: string;
  generatedTimezone: string;
  id: string;
  marketDate: string;
  sessionPhase: ReportSessionPhase;
  downloadedAt: string | null;
  sourceUpdatedAt: string | null;
  sourceState: ReportSourceState;
  version: number;
};

export type DailyReportRecord = {
  errorCode: string | null;
  fileName: string | null;
  fileSizeBytes: number | null;
  id: string;
  localPdfUri: string | null;
  metadata: ReportMetadata;
  remotePdfUrl: string | null;
  snapshot: DailyReport | null;
  status: ReportStatus;
};

export function createReportRecord({
  existingRecords,
  now = new Date(),
  pdfUrl,
  report,
}: {
  existingRecords: DailyReportRecord[];
  now?: Date;
  pdfUrl: string;
  report: DailyReport;
}): DailyReportRecord {
  const marketDate = normalizeMarketDate(report.date, now);
  const version = nextVersionForDate(existingRecords, marketDate);
  const id = `daily-${marketDate}-v${version}`;
  const metadata: ReportMetadata = {
    downloadedAt: null,
    generatedAt: now.toISOString(),
    generatedTimezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'Local',
    id,
    marketDate,
    sessionPhase: getSessionPhase(now),
    sourceState: deriveReportSourceState(report),
    sourceUpdatedAt: getReportSourceUpdatedAt(report),
    version,
  };

  return {
    errorCode: null,
    fileName: buildReportFileName(marketDate, version),
    fileSizeBytes: null,
    id,
    localPdfUri: null,
    metadata,
    remotePdfUrl: pdfUrl,
    snapshot: report,
    status: 'ready',
  };
}

export function groupReportRecords(records: DailyReportRecord[]) {
  const sorted = [...records].sort(compareReportRecords);
  return {
    downloaded: sorted.filter((record) => record.status === 'downloaded'),
    ready: sorted.filter((record) => record.status !== 'downloaded'),
  };
}

export function compareReportRecords(left: DailyReportRecord, right: DailyReportRecord) {
  const dateCompare = right.metadata.marketDate.localeCompare(left.metadata.marketDate);
  if (dateCompare !== 0) {
    return dateCompare;
  }
  if (right.metadata.version !== left.metadata.version) {
    return right.metadata.version - left.metadata.version;
  }
  return right.metadata.generatedAt.localeCompare(left.metadata.generatedAt);
}

export function nextVersionForDate(records: DailyReportRecord[], marketDate: string) {
  const versions = records
    .filter((record) => record.metadata.marketDate === marketDate)
    .map((record) => record.metadata.version);
  return versions.length ? Math.max(...versions) + 1 : 1;
}

export function buildReportFileName(marketDate: string, version: number) {
  return `Market-Intelligence-Report-${marketDate}-v${version}.pdf`;
}

export function deriveReportSourceState(report: DailyReport): ReportSourceState {
  const marketHealthQuality = report.market_health?.data_quality as { overall_mode?: string } | null | undefined;
  const mode = marketHealthQuality?.overall_mode
    ?? (report.institutional_intelligence && 'overall_mode' in report.institutional_intelligence
      ? String(report.institutional_intelligence.overall_mode)
      : null)
    ?? 'mock';
  if (mode === 'live' || mode === 'cached' || mode === 'stale' || mode === 'mock' || mode === 'mixed') {
    return mode;
  }
  return 'unavailable';
}

export function getReportSourceUpdatedAt(report: DailyReport) {
  const marketHealthQuality = report.market_health?.data_quality as { as_of?: string | null } | null | undefined;
  return marketHealthQuality?.as_of
    ?? (report.sector_etfs as { as_of?: string | null } | null | undefined)?.as_of
    ?? (report.industry_groups as { as_of?: string | null } | null | undefined)?.as_of
    ?? report.date
    ?? null;
}

export function normalizeMarketDate(value: string | null | undefined, fallbackDate = new Date()) {
  if (!value) {
    return fallbackDate.toISOString().slice(0, 10);
  }
  const date = new Date(value);
  if (!Number.isNaN(date.getTime())) {
    return date.toISOString().slice(0, 10);
  }
  const isoLike = value.match(/\d{4}-\d{2}-\d{2}/);
  return isoLike?.[0] ?? fallbackDate.toISOString().slice(0, 10);
}

export function getSessionPhase(date: Date): ReportSessionPhase {
  const weekday = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York',
    weekday: 'short',
  }).format(date);
  const day = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].indexOf(weekday);
  if (day === 0 || day === 6) {
    return 'weekend';
  }
  const parts = new Intl.DateTimeFormat('en-US', {
    hour: '2-digit',
    hour12: false,
    minute: '2-digit',
    timeZone: 'America/New_York',
  }).formatToParts(date);
  const hour = Number(parts.find((part) => part.type === 'hour')?.value ?? '0');
  const minute = Number(parts.find((part) => part.type === 'minute')?.value ?? '0');
  const minutes = hour * 60 + minute;
  if (minutes < 9 * 60 + 30) {
    return 'pre_market';
  }
  if (minutes <= 16 * 60) {
    return 'market_open';
  }
  return 'after_market';
}

export function isMinimumViableReport(report: DailyReport | null) {
  if (!report) {
    return false;
  }
  return Boolean(
    report.date
      && (report.market_regime || report.market_health)
      && (report.market_health || report.sector_etfs || report.industry_groups)
      && (report.decision_dashboard || report.executive_summary)
      && report.title,
  );
}

export function migrateReportRecords(value: unknown): DailyReportRecord[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter(isReportRecord).map((record) => ({
    ...record,
    metadata: {
      ...record.metadata,
      downloadedAt: record.metadata.downloadedAt ?? null,
      sourceUpdatedAt: record.metadata.sourceUpdatedAt ?? null,
    },
  }));
}

function isReportRecord(value: unknown): value is DailyReportRecord {
  if (!value || typeof value !== 'object') {
    return false;
  }
  const record = value as Partial<DailyReportRecord>;
  return Boolean(
    typeof record.id === 'string'
      && record.metadata
      && typeof record.metadata.marketDate === 'string'
      && typeof record.metadata.version === 'number'
      && record.status,
  );
}
