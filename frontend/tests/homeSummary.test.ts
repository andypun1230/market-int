import { buildHomeSummary } from '../src/features/home/homeSummary';
import type { HomeDashboardResponse, IndexSnapshot, MarketHealthResponse } from '../src/types/market';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function index(symbol: string, changePercent: number): IndexSnapshot {
  return {
    change: changePercent,
    change_percent: changePercent,
    ema_20: 100,
    ema_50: 95,
    ema_200: 90,
    price: 105,
    rsi_14: 60,
    sma_50: 95,
    symbol,
    volume: 1_000_000,
  };
}

function health(score: number, status = 'Very Healthy', volatility = 74, breadth = 75): MarketHealthResponse {
  return {
    component_explanations: {},
    components: {
      breadth,
      institutional: 70,
      momentum: 80,
      sector_strength: 78,
      trend: 82,
      volatility,
      volume: 68,
    },
    improving_factors: [],
    overall_score: score,
    status,
    summary: 'Trend and leadership remain constructive, but mixed breadth argues against chasing extended names.',
    weakening_factors: [],
  };
}

function dashboard(overrides: Partial<HomeDashboardResponse> = {}): HomeDashboardResponse {
  return {
    cache_status: 'fresh',
    core: {
      breadth_summary: {
        breadth_score: 72,
        breadth_status: 'Strong',
        coverage_percent: 88,
        overall_mode: 'mixed',
        percent_above_50ema: 61,
        universe: 'core',
      },
      decision_summary: {
        aggressiveness: {
          cautions: ['Sentiment elevated'],
          reasons: ['Leadership constructive'],
          score: 88,
          status: 'Moderately Aggressive',
          suggested_exposure: {
            cash: 22,
            margin: 'Light / selective',
            options: 'Suitable for strong setups only',
            stocks: 78,
          },
          summary: 'Stay selectively aggressive while confirmation is mixed.',
        },
        main_risk: 'Elevated sentiment',
        playbook: {
          action_guidelines: ['Prioritize leaders'],
          avoid: ['Chasing extended names'],
          cap_rotation_leader: 'Mega Cap',
          disclaimer: 'Educational market decision support only, not financial advice.',
          headline: 'Stay selectively aggressive',
          main_risk: 'Elevated sentiment',
          preferred_strategy: 'Momentum Breakouts',
          suggested_aggressiveness: 'Moderately Aggressive',
          summary: 'Trend and leadership remain constructive, but mixed breadth argues against chasing extended names.',
          top_industry_group: 'Semiconductors',
          top_sector: 'Technology',
        },
        preferred_style: 'Momentum Breakouts',
      },
      indexes: [index('SPY', 0.8), index('QQQ', 1.2), index('IWM', 0.3), index('DIA', 0.4)],
      market_health: health(85),
      overall_mode: 'mixed',
      top_industry_group: {
        breadth_above_50ema: 80,
        name: 'Memory',
        parent_sector: 'Technology',
        rank: 1,
        relative_strength_score: 92,
        return_1d: 1,
        return_1w: 4,
        return_mtd: 6,
        return_ytd: 40,
        score: 94,
        status: 'Leading',
      },
      top_sector: {
        change: '+1.2%',
        name: 'Consumer Discretionary',
        rank: 1,
        relative_strength_score: 88,
        status: 'Leading',
      },
    },
    risk_summary: {
      score: 22,
      status: 'Low',
      summary: 'Elevated sentiment',
      top_contributors: [{ explanation: 'Sentiment is elevated', impact: 'warning', label: 'Sentiment' }],
    },
    watchlist_summary: {
      items: [
        { change_percent: 1.1, main_setup: 'Near breakout', score: 88, source: 'mock', symbol: 'MU' },
        { change_percent: 0.9, main_setup: 'Momentum', score: 86, source: 'mock', symbol: 'NVDA' },
        { change_percent: -0.2, main_setup: 'Watching', score: 70, source: 'mock', symbol: 'ARM' },
        { change_percent: 0.1, main_setup: 'Watching', score: 65, source: 'mock', symbol: 'SNDK' },
      ],
    },
    ...overrides,
  };
}

function run() {
  const summary = buildHomeSummary(dashboard());
  assert(summary.recommendation === 'Stay Selectively Aggressive', 'playbook headline becomes the primary recommendation');
  assert(summary.healthScore === 85, 'health score is preserved');
  assert(summary.riskLabel === 'Low', 'risk label is preserved');
  assert(summary.positioningLabel === 'Moderately Aggressive', 'positioning label comes from aggressiveness');
  assert(summary.indexes.map((item) => item.symbol).join(',') === 'SPY,QQQ,IWM,DJI', 'market snapshot normalizes display indexes');
  assert(summary.indexes.map((item) => item.changePercent).join(',') === '0.8,1.2,0.3,0.4', 'constructive test index moves are coherent');
  assert(summary.indexes.every((item) => item.trendLabel === 'Bullish'), 'structural index trend remains separate from daily move');
  assert(summary.breadth?.value === 'Strong', 'breadth metric uses core breadth summary');
  assert(summary.volatility?.value === 'Contained', 'volatility metric derives from health component');
  assert(summary.leaders.map((item) => item.label).join(',') === 'Consumer Discretionary,Memory', 'leadership includes coherent sector and theme');
  assert(summary.laggardState === 'evaluated_empty', 'laggard empty state is only positive when leadership data was evaluated');
  assert(summary.stockIdeas.length === 3, 'watchlist snapshot keeps only top three ideas');
  assert(summary.upcomingEvents.length === 0, 'empty macro calendar is represented as no events');
  assert(summary.summary === 'Trend and leadership remain constructive. Stay with leaders, but avoid chasing extended names.', 'playbook summary is generated as complete compact copy');
  assert(!summary.summary.endsWith('...'), 'playbook summary does not end with ellipsis');
  assert(summary.riskDriver === 'Main driver: Elevated sentiment and concentrated leadership.', 'risk driver is compact and factor-based');
  assert(!(summary.riskDriver ?? '').includes('22/100'), 'risk driver does not repeat the score');
  assert(summary.dailyInsight?.headline !== summary.recommendation, 'daily insight headline differs from playbook recommendation');
  assert(summary.dailyInsight?.summary !== summary.summary, 'daily insight does not duplicate Today’s Playbook text exactly');
  assert(summary.dailyInsight?.summary.includes('confirmed leaders'), 'daily insight adds interpretive guidance');
  assert(!summary.dailyInsight?.summary.includes('22/100'), 'daily insight does not repeat visible scores');
  assert(!summary.dailyInsight?.summary.endsWith('...'), 'daily insight is a complete sentence without ellipsis');

  const mockSummary = buildHomeSummary(dashboard({ core: { ...dashboard().core, overall_mode: 'mock' } }));
  assert(mockSummary.sourceState === 'mock', 'mock source state is labelled');

  const emptyWatchlist = buildHomeSummary(dashboard({ watchlist_summary: { items: [] } }));
  assert(emptyWatchlist.stockIdeas.length === 0, 'empty watchlist is handled cleanly');

  const defensive = buildHomeSummary(dashboard({
    core: {
      ...dashboard().core,
      breadth_summary: {
        ...dashboard().core.breadth_summary!,
        breadth_score: 35,
        breadth_status: 'Weak',
        percent_above_50ema: 38,
      },
      indexes: [index('SPY', -1.1), index('QQQ', -1.6), index('IWM', -1.3), index('DIA', -0.8)],
      decision_summary: {
        ...dashboard().core.decision_summary,
        aggressiveness: {
          ...dashboard().core.decision_summary.aggressiveness!,
          score: 32,
          status: 'Defensive',
        },
        playbook: {
          ...dashboard().core.decision_summary.playbook!,
          headline: 'Remain Defensive',
          suggested_aggressiveness: 'Defensive',
        },
      },
      market_health: health(45, 'Weak', 35, 38),
    },
    risk_summary: {
      score: 78,
      status: 'High',
      summary: 'Volatility rising',
      top_contributors: [],
    },
  }));
  assert(defensive.recommendation === 'Remain Defensive', 'defensive playbook headline is preserved');
  assert(defensive.riskLabel === 'High', 'high risk state is preserved');
  assert(defensive.summary.includes('Risk is elevated'), 'defensive state gets coherent defensive summary copy');
  assert(defensive.volatility?.value === 'Rising', 'defensive state reflects elevated volatility');

  const mixed = buildHomeSummary(dashboard({
    core: {
      ...dashboard().core,
      breadth_summary: {
        ...dashboard().core.breadth_summary!,
        breadth_score: 52,
        breadth_status: 'Neutral',
        percent_above_50ema: 51,
      },
      indexes: [index('SPY', 0.1), index('QQQ', -0.2), index('IWM', 0), index('DIA', 0.2)],
      market_health: health(58, 'Mixed', 55, 52),
    },
    risk_summary: {
      score: 48,
      status: 'Moderate',
      summary: 'Uneven breadth',
      top_contributors: [],
    },
  }));
  assert(mixed.summary.includes('Market conditions are mixed') || mixed.riskLabel === 'Moderate', 'mixed state remains selective rather than aggressive');

  const unavailableLeadership = buildHomeSummary(dashboard({
    core: {
      ...dashboard().core,
      top_industry_group: null,
      top_sector: undefined,
    },
  }));
  assert(unavailableLeadership.laggardState === 'unavailable', 'missing leadership data does not imply no major laggards');

  const canonicalLaggard = buildHomeSummary(dashboard({
    core: {
      ...dashboard().core,
      lagging_sector: {
        ...dashboard().core.top_sector!,
        composite_score: 22.8,
        eligible_members: 1,
        name: 'Materials',
        rank: 11,
        status: 'Lagging',
        total_members: 1,
      },
    },
  }));
  assert(canonicalLaggard.laggardState === 'canonical', 'a published lowest-ranked sector is used as the Home laggard');
  assert(canonicalLaggard.laggards[0]?.label.includes('Materials · #11 overall · Lagging'), 'Home preserves canonical rank and classification for the laggard');
  assert(canonicalLaggard.laggards[0]?.label.includes('limited breadth sample (1)'), 'small-sector reliability is visible without changing the rank');
}

run();
