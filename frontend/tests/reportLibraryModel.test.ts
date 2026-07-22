import {
  buildReportFileName,
  createReportRecord,
  deriveReportSourceState,
  getSessionPhase,
  groupReportRecords,
  isMinimumViableReport,
  migrateReportRecords,
  normalizeMarketDate,
} from '../src/features/reports/reportLibraryModel';
import type { DailyReport } from '../src/types/market';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function report(overrides: Partial<DailyReport> = {}): DailyReport {
  return {
    date: '2026-07-16',
    executive_summary: 'Constructive but selective market conditions.',
    key_drivers: ['Leadership remains constructive'],
    main_risks: ['Breadth is mixed'],
    market_health: {
      component_explanations: {},
      components: {
        breadth: 66,
        institutional: 70,
        momentum: 78,
        sector_strength: 75,
        trend: 80,
        volatility: 68,
        volume: 65,
      },
      data_quality: {
        overall_mode: 'mixed',
      },
      improving_factors: [],
      overall_score: 74,
      status: 'Healthy',
      summary: 'Market health is healthy.',
      weakening_factors: [],
    },
    market_regime: 'Confirmed Uptrend',
    sector_leaders: ['Technology'],
    strategy_note: 'Stay selective.',
    title: 'Daily Market Intelligence Briefing',
    tomorrow_watch: ['NVDA'],
    ...overrides,
  };
}

function run() {
  const first = createReportRecord({
    existingRecords: [],
    now: new Date('2026-07-16T14:00:00.000Z'),
    pdfUrl: 'http://localhost:8000/report/daily/pdf?report_id=daily-server-a',
    report: report({ report_id: 'daily-server-a', generated_at: '2026-07-16T14:00:00.000Z' }),
  });
  assert(first.status === 'ready', 'new report is ready to download');
  assert(first.metadata.version === 1, 'first report version is one');
  assert(first.id === 'daily-server-a', 'server report id is retained');
  assert(first.localPdfUri === null, 'new report is not downloaded automatically');
  assert(first.fileName === buildReportFileName('2026-07-16', 1, 'daily-server-a'), 'filename includes immutable report id');
  assert(first.metadata.sourceState === 'mixed', 'source state is derived from report data quality');

  const second = createReportRecord({
    existingRecords: [first],
    now: new Date('2026-07-16T18:00:00.000Z'),
    pdfUrl: 'http://localhost:8000/report/daily/pdf?report_id=daily-server-a',
    report: report({ report_id: 'daily-server-a' }),
  });
  assert(second.metadata.version === 1, 'same immutable report is not duplicated locally');
  assert(second.id === first.id, 'same snapshot result retains the same report id');
  const newer = createReportRecord({
    existingRecords: [first],
    now: new Date('2026-07-16T18:00:00.000Z'),
    pdfUrl: 'http://localhost:8000/report/daily/pdf?report_id=daily-server-b',
    report: report({ report_id: 'daily-server-b' }),
  });
  assert(newer.id === 'daily-server-b' && newer.metadata.version === 2, 'new server report id creates a distinct local record');

  const downloaded = {
    ...first,
    localPdfUri: 'file:///report.pdf',
    metadata: { ...first.metadata, downloadedAt: '2026-07-16T19:00:00.000Z' },
    status: 'downloaded' as const,
  };
  const grouped = groupReportRecords([newer, downloaded]);
  assert(grouped.ready[0]?.id === newer.id, 'ready reports are grouped separately');
  assert(grouped.downloaded[0]?.id === downloaded.id, 'downloaded reports are grouped separately');

  const temporal = groupReportRecords([
    { ...newer, metadata: { ...newer.metadata, generatedAt: '2026-07-24T10:00:00', marketDate: '2026-07-23' } },
    { ...first, id: 'week', metadata: { ...first.metadata, generatedAt: '2026-07-21T10:00:00', id: 'week', marketDate: '2026-07-20' } },
    { ...first, id: 'previous', metadata: { ...first.metadata, generatedAt: '2026-07-01T10:00:00', id: 'previous', marketDate: '2026-06-30' } },
    { ...first, id: 'archived', metadata: { ...first.metadata, generatedAt: '2026-05-01T10:00:00', id: 'archived', marketDate: '2026-04-30' } },
    downloaded,
  ], new Date('2026-07-24T12:00:00'));
  assert(temporal.today.length === 1, 'today reports are grouped by local generation date even when the market date is earlier');
  assert(temporal.thisWeek[0]?.id === 'week', 'current-week reports exclude today');
  assert(temporal.previous[0]?.id === 'previous', 'recent earlier reports are grouped separately');
  assert(temporal.archived[0]?.id === 'archived', 'reports older than thirty days are archived');
  assert(!temporal.today.some((item) => item.status === 'downloaded'), 'downloaded reports are not duplicated in time groups');

  assert(normalizeMarketDate('2026-07-16T21:30:00.000Z') === '2026-07-16', 'market date normalizes backend timestamp strings');
  assert(deriveReportSourceState(report({ market_health: undefined })) === 'mock', 'missing source defaults to mock/test data');
  assert(isMinimumViableReport(report()), 'minimum viable report accepts a useful report snapshot');
  assert(!isMinimumViableReport(null), 'minimum viable report rejects null');
  assert(getSessionPhase(new Date('2026-07-18T14:00:00.000Z')) === 'weekend', 'session phase detects weekends');

  const migrated = migrateReportRecords([
    downloaded,
    { ...newer, remotePdfUrl: 'http://localhost:8000/report/daily/pdf', status: 'ready' as const },
    { id: 'bad' },
    null,
  ]);
  assert(migrated.length === 2, 'migration keeps valid historical records');
  assert(migrated.find((item) => item.id === newer.id)?.status === 'stale', 'legacy unpinned report URLs cannot download the latest PDF by mistake');
}

run();
