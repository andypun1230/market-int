import {
  buildBreadthDashboard,
  buildBreadthProfile,
  calculateBreadthComposite,
  classifyBreadthConfidence,
  deriveAdvanceDeclineState,
  deriveHighLowState,
  deriveMovingAverageBreadthProfile,
  formatBreadthPercent,
  formatHighLowRatio,
} from '../src/features/market/breadthAnalysis';
import type { IndexSnapshot, MarketBreadth } from '../src/types/market';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function market(overrides: Partial<MarketBreadth> = {}): MarketBreadth {
  return {
    advance_decline_ratio: 2,
    advancing_stocks: 70,
    declining_stocks: 25,
    new_52w_highs: 20,
    new_52w_lows: 5,
    percent_above_20ema: 75,
    percent_above_50ema: 72,
    percent_above_200ema: 68,
    total_stocks: 100,
    unchanged_stocks: 5,
    coverage_percent: 80,
    overall_mode: 'mock',
    universe_size: 100,
    successful_symbols: 100,
    ...overrides,
  };
}

function spy(changePercent: number): IndexSnapshot {
  return {
    change: changePercent,
    change_percent: changePercent,
    ema_20: null,
    ema_50: null,
    ema_200: null,
    price: 100,
    rsi_14: null,
    sma_50: null,
    symbol: 'SPY',
    volume: null,
  };
}

function run() {
  const positive = deriveAdvanceDeclineState(market());
  assert(positive.state === 'Positive', 'positive participation classifies');
  assert(positive.unchangedPercent === 5, 'unchanged stocks are included in denominator');
  assert(positive.ratio !== null, 'A/D ratio is present');

  const negative = deriveAdvanceDeclineState(market({ advancing_stocks: 20, declining_stocks: 70, unchanged_stocks: 10 }));
  assert(negative.state === 'Negative', 'negative participation classifies');
  const mixed = deriveAdvanceDeclineState(market({ advancing_stocks: 45, declining_stocks: 45, unchanged_stocks: 10 }));
  assert(mixed.state === 'Mixed', 'mixed participation classifies');
  assert(deriveAdvanceDeclineState(market({ total_stocks: 0 })).state === 'Unavailable', 'invalid denominator is unavailable');

  const highLow = deriveHighLowState(market({ new_52w_highs: 24, new_52w_lows: 6 }));
  assert(highLow.differential === 18, 'high-low differential calculates');
  assert(highLow.ratioLabel === '4.0×', 'high-low ratio formats');
  assert(formatHighLowRatio(5, 0) === 'Highs dominant', 'zero new lows handled without infinity');
  assert(deriveHighLowState(market({ new_52w_highs: 2, new_52w_lows: 16 })).state === 'Deteriorating', 'internal deterioration classifies');
  const inactiveHighLow = deriveHighLowState(market({ new_52w_highs: 0, new_52w_lows: 0 }));
  assert(inactiveHighLow.state === 'Inactive', 'zero highs and lows returns inactive');
  assert(inactiveHighLow.differential === null && inactiveHighLow.showDetails === false, 'inactive high-low hides ratio and differential details');
  assert(deriveHighLowState(market({ new_52w_highs: 0, new_52w_lows: 4 })).state === 'Deteriorating', 'zero highs with lows classifies deteriorating');

  assert(classifyBreadthConfidence(72) === 'high', 'high coverage confidence');
  assert(classifyBreadthConfidence(55) === 'moderate', 'moderate coverage confidence');
  assert(classifyBreadthConfidence(20) === 'low', 'low coverage confidence');
  assert(classifyBreadthConfidence(null) === 'unavailable', 'invalid coverage confidence');

  const allHigh = deriveMovingAverageBreadthProfile(market({ percent_above_20ema: 82, percent_above_50ema: 78, percent_above_200ema: 74 }));
  assert(allHigh.summary === 'Fully aligned across all horizons', 'all-high structural breadth has aligned summary');
  const improving = deriveMovingAverageBreadthProfile(market({ percent_above_20ema: 70, percent_above_50ema: 60, percent_above_200ema: 50 }));
  assert(improving.summary === 'Short-term breadth improving', '20 > 50 > 200 profile classifies as improving');
  const deteriorating = deriveMovingAverageBreadthProfile(market({ percent_above_20ema: 40, percent_above_50ema: 55, percent_above_200ema: 65 }));
  assert(deteriorating.summary === 'Short-term breadth weakening', '20 < 50 < 200 profile classifies as deteriorating');
  assert(formatBreadthPercent(100) === '100%', 'whole percentages format without decimals');

  const profile = buildBreadthProfile(positive, highLow, allHigh, {
    confidence: 'low',
    confidenceLabel: 'Low Confidence',
    coveragePercent: 22,
    expectedUniverse: 100,
    limitation: 'Low coverage',
    sourceLabel: 'Mock Data',
    strengthLabel: 'Strong',
    trackedStocks: 22,
  });
  assert(profile.length === 6, 'breadth profile includes all six metrics');
  assert(profile.find((item) => item.key === 'coverage')?.value === 22, 'coverage is a profile metric but remains separate from strength');
  assert(profile.every((item) => item.value === null || Number.isFinite(item.value)), 'profile metrics do not produce NaN');

  const composite = calculateBreadthComposite(market(), 'high');
  assert(composite.score !== null && composite.score >= 0 && composite.score <= 100, 'composite remains within 0-100');
  assert(composite.factors.length === 5, 'composite uses all valid components');
  const partialComposite = calculateBreadthComposite(market({ percent_above_20ema: Number.NaN }), 'moderate');
  assert(partialComposite.factors.length === 4, 'missing component weight is omitted');
  assert(partialComposite.score !== null, 'missing component redistributes across valid factors');
  assert(calculateBreadthComposite(null).score === null, 'no valid components returns unavailable');

  const confirmed = buildBreadthDashboard({ market: market(), sectors: [] }, [spy(1.2)]);
  assert(confirmed.divergence.state === 'confirmed_uptrend', 'confirmed uptrend classifies');
  assert(confirmed.divergence.confirmationLabel === 'Confirmed', 'confirmed terminology maps');
  const bearish = buildBreadthDashboard({ market: market({ percent_above_20ema: 25, percent_above_50ema: 30, percent_above_200ema: 35, advancing_stocks: 25, declining_stocks: 70, new_52w_highs: 2, new_52w_lows: 15 }), sectors: [] }, [spy(1.2)]);
  assert(bearish.divergence.state === 'bearish_divergence', 'bearish divergence classifies');
  const bullish = buildBreadthDashboard({ market: market({ percent_above_20ema: 80, percent_above_50ema: 75, percent_above_200ema: 70 }), sectors: [] }, [spy(-1.2)]);
  assert(bullish.divergence.state === 'bullish_divergence', 'bullish divergence classifies');
  const weak = buildBreadthDashboard({ market: market({ percent_above_20ema: 20, percent_above_50ema: 25, percent_above_200ema: 30, advancing_stocks: 20, declining_stocks: 75, new_52w_highs: 1, new_52w_lows: 20 }), sectors: [] }, [spy(-1.2)]);
  assert(weak.divergence.state === 'broad_weakness', 'broad weakness classifies');
  const unavailable = buildBreadthDashboard({ market: market(), sectors: [] }, []);
  assert(unavailable.divergence.state === 'unavailable', 'insufficient SPY input is unavailable');
  assert(unavailable.divergence.confirmationLabel !== 'Mixed / No Clear Signal', 'old unclear terminology is not used');

  assert(confirmed.takeaway.conclusion.length > 0, 'takeaway is generated');
  assert(!confirmed.takeaway.conclusion.toLowerCase().includes('undefined'), 'takeaway has no malformed copy');
  assert(!bearish.takeaway.conclusion.toLowerCase().includes('guarantee'), 'takeaway avoids reversal guarantees');
  const strongLowConfidence = buildBreadthDashboard({ market: market({ coverage_percent: 20 }), sectors: [] }, [spy(1.2)]);
  assert(strongLowConfidence.quality.confidenceLabel === 'Low Confidence', 'low confidence label is standardized');
  assert(strongLowConfidence.takeaway.risk === 'Moderately Elevated', 'low confidence affects risk label without changing strength');
}

run();
