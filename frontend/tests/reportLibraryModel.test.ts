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
    title: 'Daily Market Report',
    tomorrow_watch: ['NVDA'],
    ...overrides,
  };
}

function run() {
  const first = createReportRecord({
    existingRecords: [],
    now: new Date('2026-07-16T14:00:00.000Z'),
    pdfUrl: 'http://localhost:8000/report/daily/pdf',
    report: report(),
  });
  assert(first.status === 'ready', 'new report is ready to download');
  assert(first.metadata.version === 1, 'first report version is one');
  assert(first.localPdfUri === null, 'new report is not downloaded automatically');
  assert(first.fileName === buildReportFileName('2026-07-16', 1), 'filename includes market date and version');
  assert(first.metadata.sourceState === 'mixed', 'source state is derived from report data quality');

  const second = createReportRecord({
    existingRecords: [first],
    now: new Date('2026-07-16T18:00:00.000Z'),
    pdfUrl: 'http://localhost:8000/report/daily/pdf',
    report: report(),
  });
  assert(second.metadata.version === 2, 'same-day generation creates a new version');

  const downloaded = {
    ...first,
    localPdfUri: 'file:///report.pdf',
    metadata: { ...first.metadata, downloadedAt: '2026-07-16T19:00:00.000Z' },
    status: 'downloaded' as const,
  };
  const grouped = groupReportRecords([second, downloaded]);
  assert(grouped.ready[0]?.id === second.id, 'ready reports are grouped separately');
  assert(grouped.downloaded[0]?.id === downloaded.id, 'downloaded reports are grouped separately');

  assert(normalizeMarketDate('2026-07-16T21:30:00.000Z') === '2026-07-16', 'market date normalizes backend timestamp strings');
  assert(deriveReportSourceState(report({ market_health: undefined })) === 'mock', 'missing source defaults to mock/test data');
  assert(isMinimumViableReport(report()), 'minimum viable report accepts a useful report snapshot');
  assert(!isMinimumViableReport(null), 'minimum viable report rejects null');
  assert(getSessionPhase(new Date('2026-07-18T14:00:00.000Z')) === 'weekend', 'session phase detects weekends');

  const migrated = migrateReportRecords([
    downloaded,
    { id: 'bad' },
    null,
  ]);
  assert(migrated.length === 1 && migrated[0]?.id === downloaded.id, 'migration keeps only valid report records');
}

run();
