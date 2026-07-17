import type {
  MultiTimeframeTechnicalSignals,
  TimeframeSignalName,
  TimeframeTechnicalSignal,
} from '@/types/market';

const DIRECTIONAL_SIGNALS: TimeframeSignalName[] = [
  'strong_bearish',
  'bearish',
  'neutral',
  'bullish',
  'strong_bullish',
];

export function getTimeframeSignalRows(
  signals?: MultiTimeframeTechnicalSignals | null,
): TimeframeTechnicalSignal[] {
  if (!signals) {
    return [];
  }
  return [signals.short, signals.medium, signals.long].filter(isDisplayableTimeframeSignal);
}

export function hasAnyTimeframeSignal(signals?: MultiTimeframeTechnicalSignals | null): boolean {
  return getTimeframeSignalRows(signals).length > 0;
}

export function isRenderableDirectionalSignal(signal?: TimeframeTechnicalSignal | null): boolean {
  if (!signal) {
    return false;
  }
  return DIRECTIONAL_SIGNALS.includes(signal.signal) && isValidScore(signal.score);
}

function isDisplayableTimeframeSignal(signal?: TimeframeTechnicalSignal | null): signal is TimeframeTechnicalSignal {
  if (!signal) {
    return false;
  }
  if (isRenderableDirectionalSignal(signal)) {
    return true;
  }
  return signal.signal === 'unavailable';
}

function isValidScore(score: number | null): boolean {
  return typeof score === 'number' && Number.isFinite(score) && score >= 0 && score <= 100;
}
