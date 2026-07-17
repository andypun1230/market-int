import type { MultiTimeframeItem, PriceZone, TrendlineResponse } from '@/types/market';

export function formatNullablePrice(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return 'N/A';
  }

  return value.toLocaleString('en-US', {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  });
}

export function formatZones(zones: PriceZone[] | undefined) {
  if (!zones?.length) {
    return 'N/A';
  }

  return zones
    .slice(0, 2)
    .map((zone) => `${formatNullablePrice(zone.low)}-${formatNullablePrice(zone.high)} (${zone.strength})`)
    .join('\n');
}

export function formatNullableNumber(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return 'N/A';
  }

  return value.toLocaleString('en-US', {
    maximumFractionDigits: 1,
  });
}

export function formatNullablePercent(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return 'N/A';
  }

  return `${formatNullableNumber(value)}%`;
}

export function formatRiskReward(value?: number | null) {
  if (value === null || value === undefined) {
    return 'N/A';
  }

  return `${value.toFixed(2)} : 1`;
}

export function formatNullableVolume(value?: number | null) {
  if (value === null || value === undefined) {
    return 'N/A';
  }

  if (value >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(1)}B`;
  }

  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  }

  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }

  return value.toLocaleString('en-US');
}

export function formatRelativeVolume(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return 'N/A';
  }

  return `${formatNullableNumber(value)}x`;
}

export function formatSignals(signals: string[] | undefined) {
  if (!signals?.length) {
    return 'N/A';
  }

  return signals.join('\n');
}

export function formatBooleanSignal(value: boolean | null | undefined) {
  if (value === null || value === undefined) {
    return 'N/A';
  }

  return value ? 'Yes' : 'No';
}

export function formatDetected(value?: boolean | null) {
  if (value === null || value === undefined) {
    return 'N/A';
  }

  return value ? 'Detected' : 'Not detected';
}

export function formatTrendlineBreak(value: TrendlineResponse['trendline_break'] | undefined) {
  if (!value) {
    return 'N/A';
  }

  if (!value.broken) {
    return value.description || 'Not broken';
  }

  return `${value.direction === 'up' ? 'Upside' : 'Downside'} break`;
}

export function formatTimeframeTile(
  multiTimeframe: MultiTimeframeItem | undefined,
  timeframe: string,
) {
  const item = multiTimeframe?.timeframes.find((timeframeItem) => timeframeItem.timeframe === timeframe);

  if (!item) {
    return 'N/A';
  }

  return `${item.trend} / ${formatNullableNumber(item.score)}`;
}

export function formatSourceLabel(source?: {
  data_source?: string | null;
  source?: string | null;
  data_status?: string | null;
  dataStatus?: string | null;
  is_live?: boolean | null;
  quote_is_live?: boolean | null;
  history_is_live?: boolean | null;
  analysis_is_live?: boolean | null;
  is_stale?: boolean | null;
  fallback_used?: boolean | null;
  overall_mode?: string | null;
  data_quality?: { overall_mode?: string | null } | null;
}) {
  const dataSource = `${source?.data_source ?? source?.source ?? ''}`.toLowerCase();
  const dataStatus = `${source?.data_status ?? source?.dataStatus ?? ''}`.toLowerCase();
  if (dataStatus === 'test' || dataSource.includes('generated_test_data') || dataSource === 'test') {
    return 'Test Data';
  }

  if (source?.is_stale) {
    return 'Stale';
  }

  const mode = source?.overall_mode ?? source?.data_quality?.overall_mode;
  if (mode) {
    return `${capitalize(mode)} data`;
  }

  if (source?.fallback_used) {
    if (source.quote_is_live && !source.history_is_live) {
      return 'Live quote · Fallback history';
    }

    return 'Mock fallback';
  }

  if (source?.quote_is_live && source.history_is_live) {
    return 'Live';
  }

  if (source?.quote_is_live) {
    return 'Live quote · Mock history';
  }

  if (source?.history_is_live) {
    return 'Live history';
  }

  if (source?.analysis_is_live) {
    return 'Live history';
  }

  if (source?.is_live) {
    return 'Live';
  }

  if (
    dataSource.includes('finnhub')
    || dataSource.includes('polygon')
    || dataSource.includes('twelve_data')
  ) {
    return 'Mixed data';
  }

  return 'Mock';
}

function capitalize(value: string) {
  if (!value) {
    return 'Mock';
  }

  return `${value.charAt(0).toUpperCase()}${value.slice(1)}`;
}
