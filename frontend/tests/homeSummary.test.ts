import { buildHomeSummary } from '../src/features/home/homeSummary';
import type { HistoryData, HomeDashboardResponse, IndexSnapshot, MarketHealthResponse } from '../src/types/market';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

function index(symbol: string, changePercent: number): IndexSnapshot {
  return {
    change: changePercent,
    change_percent: changePercent,
    ema_20: 100,
    ema_50: 95,
    ema_200: 90,
    previous_close: 104,
    price: 105,
    rsi_14: 60,
    sma_50: 95,
    symbol,
    volume: 1_000_000,
  };
}

function history(symbol: string, closes: number[], timeframe = '5'): HistoryData {
  return {
    as_of: '2026-07-20T09:30:00Z',
    candles: closes.map((close, index) => ({
      close,
      high: close + 1,
      low: close - 1,
      open: close - 0.5,
      timestamp: `2026-07-${String(index + 1).padStart(2, '0')}T00:00:00Z`,
      volume: 1_000,
    })),
    fallback_used: false,
    is_live: true,
    is_stale: false,
    source: 'polygon',
    symbol,
    timeframe,
  };
}

function health(score: number, status = 'Very Healthy', volatility = 74, breadth = 75): MarketHealthResponse {
  return {
    component_explanations: {},
    components: { breadth, institutional: 70, momentum: 80, sector_strength: 78, trend: 82, volatility, volume: 68 },
    improving_factors: [],
    overall_score: score,
    status,
    summary: 'Trend and leadership remain constructive.',
    weakening_factors: ['Participation is uneven'],
  };
}

function dashboard(overrides: Partial<HomeDashboardResponse> = {}): HomeDashboardResponse {
  return {
    cache_status: 'fresh',
    generated_at: '2026-07-20T09:30:00Z',
    core: {
      breadth_summary: { breadth_score: 72, breadth_status: 'Strong', percent_above_50ema: 61 },
      decision_summary: {
        aggressiveness: {
          cautions: ['Sentiment is elevated'],
          reasons: ['Leadership constructive'],
          score: 88,
          status: 'Moderately Aggressive',
          suggested_exposure: { cash: 22, margin: 'Light', options: 'Selective', stocks: 78 },
          summary: 'Stay selective.',
        },
        main_risk: 'Elevated sentiment',
        playbook: {
          action_guidelines: ['Prioritize leaders'], avoid: ['Chasing'], cap_rotation_leader: 'Mega Cap',
          disclaimer: 'Educational only.', headline: 'Stay selectively aggressive', main_risk: 'Elevated sentiment',
          preferred_strategy: 'Momentum', suggested_aggressiveness: 'Moderately Aggressive', summary: 'Constructive.',
          top_industry_group: 'Semiconductors', top_sector: 'Technology',
        },
        preferred_style: 'Momentum',
      },
      indexes: [index('SPY', 0.8), index('QQQ', 1.2), index('IWM', 0.3), index('DIA', 0.4)],
      lagging_sector: { change: '-0.4%', name: 'Materials', rank: 11, relative_strength_score: 22, status: 'Lagging' },
      market_health: health(85),
      overall_mode: 'live',
      top_industry_group: {
        breadth_above_50ema: 80, name: 'Memory', parent_sector: 'Technology', rank: 1,
        relative_strength_score: 92, return_1d: 1, return_1w: 4, return_mtd: 6, return_ytd: 40,
        score: 94, status: 'Leading',
      },
      top_sector: { change: '+1.2%', name: 'Consumer Discretionary', rank: 1, relative_strength_score: 88, status: 'Leading' },
    },
    risk_summary: {
      score: 22,
      status: 'Low',
      summary: 'Elevated sentiment',
      top_contributors: [
        { explanation: 'Sentiment is elevated', impact: 'warning', label: 'Sentiment' },
        { explanation: 'Participation is uneven', impact: 'warning', label: 'Participation' },
      ],
    },
    watchlist_summary: {
      items: [
        { change_percent: 1.1, symbol: 'MU' },
        { change_percent: 0.9, symbol: 'NVDA' },
        { change_percent: -0.2, symbol: 'ARM' },
        { change_percent: 0.1, symbol: 'SNDK' },
      ],
    },
    ...overrides,
  };
}

function run() {
  const summary = buildHomeSummary(dashboard(), {
    SPY: history('SPY', [100, 101, 100.5, 103]),
    QQQ: history('QQQ', [100, 102, 101, 105]),
  });

  assert(summary.marketPulse.label === 'Risk On', 'constructive health, breadth, volatility, and low risk produce Risk On');
  assert(summary.marketPulse.factors.length === 3, 'Market Pulse has no more than three support factors');
  assert(summary.breadth?.direction === null && summary.volatility?.direction === null, 'direction stays hidden without published comparison data');
  assert(summary.marketEvents.length >= 5 && summary.marketEvents.length <= 8, 'Today’s Market contains five to eight factual observations');
  assert(summary.marketEvents.every((event) => event.endsWith('.')), 'market observations are complete concise sentences');
  assert(summary.marketEvents[0] === 'All four major indexes are higher.', 'the first observation compresses index participation');
  assert(summary.marketEvents[2] === 'Consumer Discretionary leads while Materials lags.', 'the third observation compresses leadership');
  assert(summary.indexes.map((item) => item.symbol).join(',') === 'SPY,QQQ,IWM,DIA', 'canonical index proxies are preserved');
  assert(summary.indexes.find((item) => item.symbol === 'SPY')?.sparkline.join(',') === '100,101,100.5,103', 'sparkline uses real recent history closes');
  assert(summary.indexes.find((item) => item.symbol === 'IWM')?.sparkline.length === 0, 'missing intraday history produces an unavailable sparkline');
  const dailyHistory = buildHomeSummary(dashboard(), { SPY: history('SPY', [100, 101, 102], 'D') });
  assert(dailyHistory.indexes.find((item) => item.symbol === 'SPY')?.sparkline.length === 0, 'daily bars are never presented as intraday');
  assert(summary.indexes.every((item) => item.trendLabel === 'Uptrend'), 'trend labels are simplified');
  assert(summary.leadership.map((item) => item.role).join(',') === 'Leading Sector,Leading Theme,Lagging Sector', 'leadership shows exactly the three requested roles');
  assert(summary.leadership.map((item) => item.label).join(',') === 'Consumer Discretionary,Memory,Materials', 'leadership labels contain names only');
  assert(summary.leadership.every((item) => !item.label.includes('#') && !item.label.includes('EMA') && !item.label.includes('Composite')), 'leadership removes rankings and technical details');
  assert(summary.riskDrivers.length >= 2 && summary.riskDrivers.length <= 3, 'Risk Dashboard exposes two to three concise drivers');
  assert(summary.stockIdeas.length === 4, 'compact ticker chips can show the available top ideas');
  assert(summary.dailyInsight?.category === 'Cross-Market', 'Daily Insight has a compact category');
  assert(summary.dailyInsight?.headline === 'Participation is broad', 'Daily Insight has one concise signal headline');
  assert(!summary.dailyInsight?.summary.includes('Consumer Discretionary'), 'Daily Insight does not repeat Leadership');
  assert(!summary.dailyInsight?.summary.includes('Sentiment'), 'Daily Insight does not repeat Risk drivers');
  assert(summary.updatedAt === '2026-07-20T09:30:00Z', 'freshness timestamp is preserved');

  const translatedRisk = buildHomeSummary(dashboard({
    risk_summary: {
      score: 40,
      status: 'Low',
      summary: 'Risk is contained',
      top_contributors: [
        { explanation: 'Market health is Mixed at 68/100.', impact: 'warning', label: 'Health' },
        { explanation: 'Only 56.0% of stocks are above the 50EMA.', impact: 'warning', label: 'Breadth' },
        { explanation: 'Market Health changed -8.0, Breadth changed -6.5, Fear & Greed changed -27.0.', impact: 'warning', label: 'Change' },
      ],
    },
  }));
  assert(translatedRisk.riskDrivers.join(',') === 'Mixed market health,Narrow participation,Sentiment cooling', 'raw risk deltas are translated into compact supported concepts');
  assert(translatedRisk.riskDrivers.every((driver) => !/[-+]\d+\.\d+/.test(driver)), 'risk drivers never expose raw score deltas');

  const directional = buildHomeSummary(dashboard({
    core: {
      ...dashboard().core,
      breadth_summary: { ...dashboard().core.breadth_summary!, trend: 'deteriorating' },
      top_sector: { ...dashboard().core.top_sector!, status: 'Improving' },
    },
  }));
  assert(directional.breadth?.direction === 'Narrowing', 'published breadth deterioration maps to Narrowing');
  assert(directional.marketPulse.factors[0]?.direction === 'Improving', 'published sector classification supplies leadership direction');

  const longLeadership = buildHomeSummary(dashboard({
    core: {
      ...dashboard().core,
      lagging_sector: { ...dashboard().core.lagging_sector!, name: 'Consumer Discretionary Services' },
      theme_intelligence: {
        available: true,
        leaders: [{ display_name: 'Next Generation Cybersecurity Infrastructure', theme_id: 'next-gen-cybersecurity' }],
      },
      top_sector: { ...dashboard().core.top_sector!, name: 'Communication Services' },
    },
  }));
  assert(longLeadership.leadership.map((item) => item.label).join('|') === 'Communication Services|Next Generation Cybersecurity Infrastructure|Consumer Discretionary Services', 'long published names are preserved without display metadata');

  const partial = buildHomeSummary({
    core: {
      decision_summary: {},
      indexes: [index('SPY', -0.4)],
      overall_mode: 'live',
    },
    risk_summary: { top_contributors: [] },
    watchlist_summary: { items: [] },
  } as unknown as HomeDashboardResponse);
  assert(partial.indexes.length === 1 && partial.indexes[0].sparkline.length === 0, 'partial data keeps available index state and an honest unavailable chart');
  assert(partial.marketEvents.length >= 5, 'partial data still produces a stable concise briefing');

  const selective = buildHomeSummary(dashboard({
    core: {
      ...dashboard().core,
      breadth_summary: { breadth_score: 52, breadth_status: 'Neutral', percent_above_50ema: 51 },
      market_health: health(58, 'Mixed', 55, 52),
    },
    risk_summary: { score: 48, status: 'Moderate', summary: 'Uneven breadth', top_contributors: [] },
  }));
  assert(selective.marketPulse.label === 'Selective Risk', 'mixed conditions produce Selective Risk');

  const defensive = buildHomeSummary(dashboard({
    core: {
      ...dashboard().core,
      breadth_summary: { breadth_score: 35, breadth_status: 'Weak', percent_above_50ema: 38 },
      indexes: [index('SPY', -1.1), index('QQQ', -1.6), index('IWM', -1.3), index('DIA', -0.8)],
      market_health: health(45, 'Weak', 35, 38),
    },
    risk_summary: { score: 78, status: 'High', summary: 'Volatility rising', top_contributors: [] },
  }));
  assert(defensive.marketPulse.label === 'Risk Off', 'high risk and weak volatility produce Risk Off');
  assert(defensive.todaysBias.toLowerCase().includes('protect capital'), 'Risk Off bias is defensive and concise');

  const empty = buildHomeSummary(null);
  assert(empty.sourceState === 'unavailable', 'missing dashboard has unavailable provenance');
}

run();
