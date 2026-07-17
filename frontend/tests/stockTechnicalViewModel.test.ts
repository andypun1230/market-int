import {
  buildPriceLevels,
  buildStockTechnicalViewModel,
  getLevelMismatchReason,
} from '../src/features/stock-detail/technical/technicalViewModel';
import type {
  DetectedPattern,
  SupportResistanceResponse,
  TrendlineResponse,
  VolumeAnalysis,
  WatchlistItem,
} from '../src/types/market';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function stock(overrides: Partial<WatchlistItem> = {}): WatchlistItem {
  return {
    change: 1,
    change_percent: 0.5,
    data_source: 'live',
    fallback_used: false,
    is_live: true,
    is_stale: false,
    price: 210.96,
    risk_flag: 'Moderate',
    setup: 'Near breakout',
    support_zone: '$205-$208',
    ticker: 'NVDA',
    trend: 'Constructive',
    ...overrides,
  };
}

function pattern(overrides: Partial<DetectedPattern> = {}): DetectedPattern {
  return {
    chart_data: [
      { close: 205, date: '2026-06-01', high: 207, low: 201, open: 202, volume: 100 },
      { close: 210, date: '2026-06-02', high: 212, low: 204, open: 205, volume: 120 },
    ],
    confidence: 80,
    data_source: 'live',
    description: 'A sharp advance is consolidating in a tightening range.',
    direction: 'bullish',
    id: 'nvda-bull-flag',
    is_live: true,
    key_levels: {
      breakout: 212.19,
      resistance: 216.82,
      stop_reference: 205.65,
      support: 208.78,
    },
    markers: [{ date: '2026-06-02', label: 'Flag', price: 210 }],
    name: 'Bull Flag',
    status: 'forming',
    symbol: 'NVDA',
    timeframe: 'Daily',
    type: 'continuation',
    ...overrides,
  };
}

function zones(overrides: Partial<SupportResistanceResponse> = {}): SupportResistanceResponse {
  return {
    analysis_is_live: true,
    as_of: '2026-07-12',
    breakout_level: 212.19,
    current_price: 210.96,
    data_source: 'live',
    fallback_used: false,
    moving_average_support: { ema_20: 202.77, ema_50: 203.86 },
    resistance_zones: [{ high: 217.2, low: 216.82, reason: 'prior high', strength: 80 }],
    stop_reference: 205.65,
    support_zones: [{ high: 208.78, low: 207.2, reason: 'near support', strength: 75 }],
    symbol: 'NVDA',
    ...overrides,
  };
}

function trend(overrides: Partial<TrendlineResponse> = {}): TrendlineResponse {
  return {
    current_price: 210.96,
    data_source: 'live',
    falling_resistance: {
      current_line_value: null,
      detected: false,
      distance_percent: null,
      end_date: null,
      end_price: null,
      slope: null,
      start_date: null,
      start_price: null,
      status: 'Not detected',
      touch_count: 0,
    },
    fallback_used: false,
    rising_support: {
      current_line_value: 202,
      detected: true,
      distance_percent: 4.3,
      end_date: '2026-07-12',
      end_price: 202,
      slope: 1.2,
      start_date: '2026-06-01',
      start_price: 180,
      status: 'Holding',
      touch_count: 10,
    },
    summary: 'Rising support is holding.',
    symbol: 'NVDA',
    trendline_break: { broken: false, description: 'No break', direction: 'none' },
    ...overrides,
  };
}

function volume(overrides: Partial<VolumeAnalysis> = {}): VolumeAnalysis {
  return {
    accumulation_volume: true,
    average_volume_20: 1000,
    breakout_volume: false,
    climax_run: false,
    data_source: 'live',
    distribution_volume: false,
    dry_up: false,
    fallback_used: false,
    relative_volume: 1,
    signals: ['Accumulation present'],
    status: 'Average',
    summary: 'Average participation.',
    symbol: 'NVDA',
    volume_quality: 'Average',
    volume_quality_score: 60,
    ...overrides,
  };
}

function run() {
  const compatible = buildStockTechnicalViewModel({
    pattern: pattern(),
    stock: stock(),
    supportResistance: zones(),
    trendline: trend(),
    volumeAnalysis: volume(),
  });
  assert(compatible.provenance.sourcesCompatible, 'live pattern and live levels may be shown together');
  assert(compatible.patternTrust.state === 'live_compatible', 'compatible live pattern is trusted as current');
  assert(compatible.patternTrust.shouldLeadTechnicalTab, 'compatible current pattern may lead the technical tab');
  assert(compatible.patternTrust.shouldShowScoreProminently, 'compatible current pattern may show score prominently');
  assert(compatible.pattern.sourceStatus === 'live', 'live pattern is labelled live');
  assert(compatible.setup.confirmationLevel === 212.19, 'current confirmation level is primary');
  assert(compatible.setup.invalidationLevel === 205.65, 'current invalidation level is primary');
  assert(compatible.confirmations.length <= 4, 'confirmation checklist is capped');
  assert(compatible.invalidations.length <= 4, 'invalidation checklist is capped');
  assert(compatible.summary.body.includes('$212.19'), 'technical summary includes current confirmation');
  assert(!compatible.summary.body.toLowerCase().includes('80% confidence'), 'pattern score is not called probability');

  const mismatchedPattern = pattern({ key_levels: { breakout: 163.5, stop_reference: 154, support: 156 } });
  const mismatch = buildStockTechnicalViewModel({
    pattern: mismatchedPattern,
    stock: stock(),
    supportResistance: zones(),
    trendline: trend(),
    volumeAnalysis: volume(),
  });
  assert(!mismatch.provenance.sourcesCompatible, 'material level mismatch marks sources incompatible');
  assert(getLevelMismatchReason(mismatchedPattern, zones())?.includes('differs materially'), 'mismatch reason is explicit');
  assert(mismatch.patternTrust.state === 'historical_incompatible', 'mismatched pattern is demoted to historical context');
  assert(!mismatch.patternTrust.shouldLeadTechnicalTab, 'mismatched pattern does not lead technical tab');
  assert(!mismatch.patternTrust.shouldShowScoreProminently, 'mismatched pattern score is not prominent');
  assert(mismatch.provenance.detailedMismatchReason?.includes('differs materially'), 'developer mismatch reason is retained');
  assert(!mismatch.provenance.mismatchReason?.includes('differs materially'), 'user mismatch copy is softened');
  assert(mismatch.priceLevels.every((level) => Math.abs(level.value - 163.5) > 0.01), 'historical pattern breakout is excluded from current ladder');
  assert(mismatch.summary.body.includes('secondary context'), 'summary explains demoted pattern context');

  const mock = buildStockTechnicalViewModel({
    pattern: pattern({ data_source: 'mock', is_live: false }),
    stock: stock(),
    supportResistance: zones(),
    trendline: trend(),
    volumeAnalysis: volume(),
  });
  assert(mock.pattern.sourceStatus === 'mock', 'mock pattern is labelled mock');
  assert(!mock.provenance.sourcesCompatible, 'mock pattern is not compatible with current levels');
  assert(mock.patternTrust.state === 'mock', 'mock pattern has an explicit trust state');
  assert(!mock.patternTrust.shouldLeadTechnicalTab, 'mock pattern does not lead the technical tab');
  assert(!mock.patternTrust.shouldShowScoreProminently, 'mock pattern score is secondary');

  const ladder = buildPriceLevels(stock(), zones());
  assert(ladder.length >= 5, 'price ladder includes current levels');
  for (let index = 1; index < ladder.length; index += 1) {
    assert(ladder[index - 1].value >= ladder[index].value, 'price ladder sorts high to low');
  }
  assert(ladder.some((level) => level.kind === 'current'), 'current price is distinct');
  assert(ladder.some((level) => level.kind === 'confirmation' || level.kinds?.includes('confirmation')), 'confirmation level is present');
  assert(ladder.some((level) => level.kind === 'invalidation'), 'invalidation level is present');

  const mergedLadder = buildPriceLevels(stock(), zones({
    resistance_zones: [{ high: 212.31, low: 212.3, reason: 'near breakout', strength: 72 }],
  }));
  const mergedResistance = mergedLadder.find((level) => level.kinds?.includes('confirmation') && level.kinds.includes('resistance'));
  if (!mergedResistance) {
    throw new Error('nearby confirmation and resistance levels merge');
  }
  assert(mergedResistance.label === 'Confirmation / resistance zone', 'merged level has combined label');
  assert(mergedResistance.zoneLow === 212.19 && mergedResistance.zoneHigh === 212.3, 'merged level preserves the range');

  const noPattern = buildStockTechnicalViewModel({
    pattern: null,
    stock: stock(),
    supportResistance: zones(),
    trendline: trend(),
    volumeAnalysis: volume(),
  });
  assert(noPattern.pattern.sourceStatus === 'unavailable', 'missing pattern is unavailable');
  assert(noPattern.summary.headline === 'Current setup needs confirmation.', 'missing pattern falls back to current levels when available');

  const weakVolume = buildStockTechnicalViewModel({
    pattern: pattern(),
    stock: stock(),
    supportResistance: zones(),
    trendline: trend(),
    volumeAnalysis: volume({ relative_volume: 0.6, volume_quality: 'Weak' }),
  });
  assert(weakVolume.volume.explanation === 'Participation is below normal and does not confirm the setup.', 'weak volume has concise explanation');

  const averageAccumulation = buildStockTechnicalViewModel({
    pattern: pattern(),
    stock: stock(),
    supportResistance: zones(),
    trendline: trend(),
    volumeAnalysis: volume({ accumulation_volume: true, relative_volume: 1, volume_quality: 'Average' }),
  });
  assert(averageAccumulation.volume.explanation === 'Accumulation signs are present, but participation remains near normal.', 'average accumulation avoids overstatement');
  assert(averageAccumulation.trend.explanation?.includes('10 confirmed touches'), 'trend explanation keeps touch evidence');
  assert(averageAccumulation.trend.explanation?.includes('4.3% above the trendline'), 'trend explanation keeps distance evidence');
}

run();
