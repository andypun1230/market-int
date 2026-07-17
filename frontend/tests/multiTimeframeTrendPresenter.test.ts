import {
  getTimeframeSignalRows,
  hasAnyTimeframeSignal,
  isRenderableDirectionalSignal,
} from '../src/features/stock-detail/technical/timeframeSignalPresenter';
import type {
  MultiTimeframeTechnicalSignals,
  TimeframeSignalName,
  TimeframeTechnicalSignal,
} from '../src/types/market';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function signal(
  timeframe: 'short' | 'medium' | 'long',
  state: TimeframeSignalName,
  score: number | null,
): TimeframeTechnicalSignal {
  return {
    asOf: '2026-07-12T20:00:00Z',
    availableInputs: score == null ? 2 : 7,
    dataStatus: score == null ? 'unavailable' : 'mixed',
    explanation: score == null ? 'Not enough inputs are available.' : `${timeframe} trend is ${state}.`,
    headline: `${timeframe} signal`,
    horizonLabel: timeframe === 'short' ? '1–10 trading days' : timeframe === 'medium' ? '2–8 weeks' : '3–12 months',
    negativeEvidence: [],
    positiveEvidence: score == null ? [] : [{ key: 'trend', label: 'Trend confirmation' }],
    requiredInputs: timeframe === 'long' ? 10 : 8,
    score,
    signal: state,
    strength: score == null ? 'unavailable' : 'strong',
    timeframe,
  };
}

function run() {
  const signals: MultiTimeframeTechnicalSignals = {
    generatedAt: '2026-07-12T20:00:00Z',
    long: signal('long', 'unavailable', null),
    medium: signal('medium', 'strong_bullish', 90),
    methodologyVersion: '2',
    overallDataStatus: 'mixed',
    short: signal('short', 'strong_bullish', 87),
  };

  const rows = getTimeframeSignalRows(signals);
  assert(hasAnyTimeframeSignal(signals), 'partial timeframe data should not show blanket unavailable');
  assert(rows.length === 3, 'short, medium, and unavailable long rows render independently');
  assert(rows[0].timeframe === 'short', 'short row renders first');
  assert(rows[1].timeframe === 'medium', 'medium row renders second');
  assert(rows[2].timeframe === 'long', 'long row renders third');
  assert(isRenderableDirectionalSignal(rows[0]), 'short strong bullish with mixed data is renderable');
  assert(isRenderableDirectionalSignal(rows[1]), 'medium strong bullish with mixed data is renderable');
  assert(!isRenderableDirectionalSignal(rows[2]), 'unavailable long is not treated as neutral or directional');

  assert(!hasAnyTimeframeSignal(null), 'missing signal object still shows blanket unavailable');
}

run();
