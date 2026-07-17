import type { IndexSnapshot, MarketBreadthResponse, SectorBreadthItem } from '@/types/market';
import type { BreadthDashboardViewModel, BreadthState } from './breadthAnalysis';

export type BreadthMockScenarioKey =
  | 'healthyBull'
  | 'bearishDivergence'
  | 'broadCorrection'
  | 'bullishDivergence'
  | 'narrowLeadership'
  | 'choppyMarket'
  | 'lowConfidence';

export type BreadthMockHistoryPoint = {
  advanceDecline: number;
  above20EMA: number;
  above50EMA: number;
  above200EMA: number;
  breadthComposite: number;
  breadthReturn: number;
  coverage: number;
  date: string;
  newHighs: number;
  newLows: number;
  spyReturn: number;
};

type ConfirmationOverride = {
  confirmationLabel: string;
  explanation: string;
  risk: string;
  riskDirection: string;
  stateLabel: string;
  tone: BreadthDashboardViewModel['divergence']['tone'];
};

type BreadthScenarioDefinition = {
  adRatio: number;
  advancing: number;
  above20: number;
  above50: number;
  above200: number;
  breadthComposite: number;
  breadthReturn: number;
  coverage: number;
  declining: number;
  key: BreadthMockScenarioKey;
  label: string;
  newHighs: number;
  newLows: number;
  state: 'Strong' | 'Constructive' | 'Mixed' | 'Weak';
  spyReturn: number;
  unchanged: number;
  confirmation: ConfirmationOverride;
};

export type BreadthMockScenario = {
  breadth: MarketBreadthResponse;
  definition: BreadthScenarioDefinition;
  history: BreadthMockHistoryPoint[];
  indexes: IndexSnapshot[];
  key: BreadthMockScenarioKey;
  label: string;
};

export const BREADTH_MOCK_SCENARIOS: { key: BreadthMockScenarioKey; label: string }[] = [
  { key: 'healthyBull', label: 'Healthy Bull' },
  { key: 'bearishDivergence', label: 'Bearish Divergence' },
  { key: 'broadCorrection', label: 'Broad Correction' },
  { key: 'bullishDivergence', label: 'Bullish Divergence' },
  { key: 'narrowLeadership', label: 'Narrow Leadership' },
  { key: 'choppyMarket', label: 'Choppy Market' },
  { key: 'lowConfidence', label: 'Low Confidence' },
];

const SCENARIOS: Record<BreadthMockScenarioKey, BreadthScenarioDefinition> = {
  healthyBull: {
    adRatio: 4.31,
    advancing: 410,
    above20: 94,
    above50: 89,
    above200: 82,
    breadthComposite: 91,
    breadthReturn: 4,
    confirmation: {
      confirmationLabel: 'Confirmed',
      explanation: 'SPY strength is confirmed by broad participation, expanding leadership, and high moving-average breadth.',
      risk: 'Low',
      riskDirection: 'Low',
      stateLabel: 'Confirmed Uptrend',
      tone: 'positive',
    },
    coverage: 96,
    declining: 95,
    key: 'healthyBull',
    label: 'Healthy Bull',
    newHighs: 146,
    newLows: 8,
    spyReturn: 4.2,
    state: 'Strong',
    unchanged: 18,
  },
  bearishDivergence: {
    adRatio: 0.79,
    advancing: 218,
    above20: 71,
    above50: 66,
    above200: 74,
    breadthComposite: 73,
    breadthReturn: 1.4,
    confirmation: {
      confirmationLabel: 'Diverging',
      explanation: 'SPY is rising faster than participation, creating a bearish divergence test case.',
      risk: 'Increasing',
      riskDirection: 'Increasing',
      stateLabel: 'Bearish Divergence',
      tone: 'warning',
    },
    coverage: 96,
    declining: 275,
    key: 'bearishDivergence',
    label: 'Bearish Divergence',
    newHighs: 42,
    newLows: 28,
    spyReturn: 5.3,
    state: 'Constructive',
    unchanged: 24,
  },
  broadCorrection: {
    adRatio: 0.14,
    advancing: 62,
    above20: 18,
    above50: 12,
    above200: 27,
    breadthComposite: 31,
    breadthReturn: -10.4,
    confirmation: {
      confirmationLabel: 'Confirmed',
      explanation: 'SPY weakness is confirmed by weak participation, rising new lows, and poor moving-average breadth.',
      risk: 'High',
      riskDirection: 'High',
      stateLabel: 'Broad Weakness',
      tone: 'negative',
    },
    coverage: 96,
    declining: 442,
    key: 'broadCorrection',
    label: 'Broad Correction',
    newHighs: 3,
    newLows: 165,
    spyReturn: -8.5,
    state: 'Weak',
    unchanged: 19,
  },
  bullishDivergence: {
    adRatio: 1.45,
    advancing: 305,
    above20: 63,
    above50: 55,
    above200: 47,
    breadthComposite: 67,
    breadthReturn: 2.6,
    confirmation: {
      confirmationLabel: 'Diverging',
      explanation: 'Participation is improving while SPY remains weak, creating a bullish divergence test case.',
      risk: 'Potential Reversal',
      riskDirection: 'Potential Reversal',
      stateLabel: 'Bullish Divergence',
      tone: 'positive',
    },
    coverage: 95,
    declining: 210,
    key: 'bullishDivergence',
    label: 'Bullish Divergence',
    newHighs: 52,
    newLows: 24,
    spyReturn: -3.8,
    state: 'Mixed',
    unchanged: 11,
  },
  narrowLeadership: {
    adRatio: 0.65,
    advancing: 188,
    above20: 58,
    above50: 54,
    above200: 61,
    breadthComposite: 69,
    breadthReturn: -1.2,
    confirmation: {
      confirmationLabel: 'Diverging',
      explanation: 'SPY is being carried by narrow leadership while the broader universe lags.',
      risk: 'Narrow Leadership',
      riskDirection: 'Narrow Leadership',
      stateLabel: 'Bearish Divergence',
      tone: 'warning',
    },
    coverage: 95,
    declining: 291,
    key: 'narrowLeadership',
    label: 'Narrow Leadership',
    newHighs: 61,
    newLows: 39,
    spyReturn: 7.1,
    state: 'Mixed',
    unchanged: 16,
  },
  choppyMarket: {
    adRatio: 1.03,
    advancing: 255,
    above20: 54,
    above50: 48,
    above200: 46,
    breadthComposite: 52,
    breadthReturn: 0.2,
    confirmation: {
      confirmationLabel: 'Unclear',
      explanation: 'SPY and breadth are both near flat, so confirmation remains unclear.',
      risk: 'Neutral',
      riskDirection: 'Neutral',
      stateLabel: 'Unclear',
      tone: 'neutral',
    },
    coverage: 95,
    declining: 247,
    key: 'choppyMarket',
    label: 'Choppy Market',
    newHighs: 26,
    newLows: 24,
    spyReturn: 0.4,
    state: 'Mixed',
    unchanged: 18,
  },
  lowConfidence: {
    adRatio: 2.33,
    advancing: 7,
    above20: 100,
    above50: 100,
    above200: 100,
    breadthComposite: 82,
    breadthReturn: 0.6,
    confirmation: {
      confirmationLabel: 'Low Confidence',
      explanation: 'The sampled breadth data is strong, but coverage is too low for high-confidence conclusions.',
      risk: 'Moderately Elevated',
      riskDirection: 'Moderately Elevated',
      stateLabel: 'Low Confidence',
      tone: 'warning',
    },
    coverage: 18,
    declining: 3,
    key: 'lowConfidence',
    label: 'Low Confidence',
    newHighs: 2,
    newLows: 0,
    spyReturn: 0.5,
    state: 'Strong',
    unchanged: 0,
  },
};

export function buildBreadthMockScenario(key: BreadthMockScenarioKey): BreadthMockScenario {
  const definition = SCENARIOS[key];
  const history = generateBreadthHistory(definition);
  return {
    breadth: {
      market: {
        advance_decline_ratio: definition.adRatio,
        advancing_stocks: definition.advancing,
        as_of: '2026-07-15T00:00:00Z',
        breadth_score: definition.breadthComposite,
        breadth_status: definition.state,
        coverage_percent: definition.coverage,
        data_source: 'mock-scenario',
        declining_stocks: definition.declining,
        fallback_used: false,
        is_live: false,
        new_52w_highs: definition.newHighs,
        new_52w_lows: definition.newLows,
        overall_mode: 'mock',
        percent_above_20ema: definition.above20,
        percent_above_50ema: definition.above50,
        percent_above_200ema: definition.above200,
        successful_symbols: definition.advancing + definition.declining + definition.unchanged,
        total_stocks: definition.advancing + definition.declining + definition.unchanged,
        unchanged_stocks: definition.unchanged,
        universe: 'breadth mock scenario',
        universe_size: definition.advancing + definition.declining + definition.unchanged,
      },
      sectors: buildMockSectorBreadth(definition),
    },
    definition,
    history,
    indexes: [buildMockIndex('SPY', definition.spyReturn), buildMockIndex('QQQ', definition.spyReturn * 1.1), buildMockIndex('DJI', definition.spyReturn * 0.75)],
    key,
    label: definition.label,
  };
}

export function applyBreadthMockScenarioDashboard(
  dashboard: BreadthDashboardViewModel,
  scenario: BreadthMockScenario,
): BreadthDashboardViewModel {
  const state = scenario.definition.state;
  const stateKey = state.toLowerCase() as BreadthState;
  return {
    ...dashboard,
    composite: {
      ...dashboard.composite,
      score: scenario.definition.breadthComposite,
    },
    divergence: {
      ...dashboard.divergence,
      confirmationLabel: scenario.definition.confirmation.confirmationLabel,
      confirmationScore: scenario.definition.breadthComposite,
      explanation: scenario.definition.confirmation.explanation,
      riskDirection: scenario.definition.confirmation.riskDirection,
      stateLabel: scenario.definition.confirmation.stateLabel,
      tone: scenario.definition.confirmation.tone,
    },
    overview: {
      ...dashboard.overview,
      score: scenario.definition.breadthComposite,
      state: stateKey,
      status: state,
      tone: scenario.definition.confirmation.tone,
    },
    riskLabel: scenario.definition.confirmation.risk,
    takeaway: {
      ...dashboard.takeaway,
      conclusion: scenario.definition.confirmation.explanation,
      confirmation: scenario.definition.confirmation.confirmationLabel,
      risk: scenario.definition.confirmation.risk,
      tone: scenario.definition.confirmation.tone,
    },
  };
}

function buildMockIndex(symbol: string, changePercent: number): IndexSnapshot {
  const price = symbol === 'SPY' ? 625 : symbol === 'QQQ' ? 555 : 445;
  return {
    change: (price * changePercent) / 100,
    change_percent: changePercent,
    data_source: 'mock-scenario',
    ema_20: null,
    ema_50: null,
    ema_200: null,
    fallback_used: false,
    is_live: false,
    price,
    rsi_14: null,
    sma_50: null,
    symbol,
    volume: null,
  };
}

function buildMockSectorBreadth(definition: BreadthScenarioDefinition): SectorBreadthItem[] {
  const sectors = ['Technology', 'Financials', 'Healthcare', 'Industrials', 'Energy', 'Utilities'];
  return sectors.map((sector, index) => {
    const adjustment = (index - 2) * 3;
    const total = Math.max(8, Math.round((definition.advancing + definition.declining) / sectors.length));
    const above50 = clamp(definition.above50 + adjustment, 0, 100);
    const advancing = Math.round((total * clamp((definition.advancing / Math.max(1, definition.advancing + definition.declining)) * 100 + adjustment, 0, 100)) / 100);
    return {
      advancing_stocks: advancing,
      as_of: '2026-07-15T00:00:00Z',
      data_source: 'mock-scenario',
      declining_stocks: Math.max(0, total - advancing),
      fallback_used: false,
      is_live: false,
      overall_mode: 'mock',
      percent_above_50ema: above50,
      sector,
      total_stocks: total,
    };
  });
}

function generateBreadthHistory(definition: BreadthScenarioDefinition): BreadthMockHistoryPoint[] {
  const length = 30;
  return Array.from({ length }, (_, index) => {
    const progress = index / (length - 1);
    const isLatest = index === length - 1;
    const wobble = isLatest ? 0 : Math.sin(index * 0.9 + seedFromKey(definition.key)) * 1.8;
    return {
      advanceDecline: isLatest ? definition.adRatio : roundTo(interpolate(startFor(definition.adRatio), definition.adRatio, progress, wobble * 0.03), 2),
      above20EMA: isLatest ? definition.above20 : roundTo(interpolate(startFor(definition.above20), definition.above20, progress, wobble), 1),
      above50EMA: isLatest ? definition.above50 : roundTo(interpolate(startFor(definition.above50), definition.above50, progress, wobble * 0.75), 1),
      above200EMA: isLatest ? definition.above200 : roundTo(interpolate(startFor(definition.above200), definition.above200, progress, wobble * 0.35), 1),
      breadthComposite: isLatest ? definition.breadthComposite : roundTo(interpolate(startFor(definition.breadthComposite), definition.breadthComposite, progress, wobble * 0.45), 1),
      breadthReturn: isLatest ? definition.breadthReturn : roundTo(interpolate(0, definition.breadthReturn, progress, wobble * 0.08), 2),
      coverage: isLatest ? definition.coverage : roundTo(interpolate(Math.max(5, definition.coverage - 3), definition.coverage, progress, 0), 1),
      date: dateOffset(index - length + 1),
      newHighs: isLatest ? definition.newHighs : Math.max(0, Math.round(interpolate(startFor(definition.newHighs), definition.newHighs, progress, wobble))),
      newLows: isLatest ? definition.newLows : Math.max(0, Math.round(interpolate(startFor(definition.newLows), definition.newLows, progress, -wobble))),
      spyReturn: isLatest ? definition.spyReturn : roundTo(interpolate(0, definition.spyReturn, progress, wobble * 0.08), 2),
    };
  });
}

function startFor(value: number) {
  if (value >= 90) {
    return Math.max(5, value - 28);
  }
  if (value >= 70) {
    return value - 18;
  }
  if (value <= 20) {
    return value + 28;
  }
  if (value <= 40) {
    return value + 18;
  }
  return value + 8;
}

function interpolate(start: number, end: number, progress: number, wobble = 0) {
  const eased = progress * progress * (3 - 2 * progress);
  return clamp(start + (end - start) * eased + wobble, 0, 100);
}

function seedFromKey(key: string) {
  return key.split('').reduce((sum, character) => sum + character.charCodeAt(0), 0) / 10;
}

function dateOffset(offset: number) {
  const date = new Date(Date.UTC(2026, 6, 15 + offset));
  return date.toISOString().slice(0, 10);
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function roundTo(value: number, decimals: number) {
  const scale = 10 ** decimals;
  return Math.round(value * scale) / scale;
}
