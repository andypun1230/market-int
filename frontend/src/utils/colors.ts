import { Theme } from '@/constants/theme';
import type { Tone } from '@/components/ui/StatusBadge';

export function getRatingColor(rating?: string) {
  if (rating === 'A' || rating === 'A+') {
    return Theme.colors.success;
  }

  if (rating === 'B') {
    return Theme.colors.accent;
  }

  if (rating === 'C') {
    return Theme.colors.warning;
  }

  if (rating === 'D' || rating === 'F') {
    return Theme.colors.danger;
  }

  return Theme.colors.textMuted;
}

export function getRatingSoftColor(rating: string | null | undefined) {
  if (rating === 'A' || rating === 'A+') {
    return Theme.colors.successSoft;
  }

  if (rating === 'B') {
    return Theme.colors.accentSoft;
  }

  if (rating === 'C') {
    return Theme.colors.warningSoft;
  }

  if (rating === 'D' || rating === 'F') {
    return Theme.colors.dangerSoft;
  }

  return Theme.colors.cardMuted;
}

export function getRiskColor(riskLevel: string | null | undefined) {
  switch (riskLevel?.toLowerCase()) {
    case 'low':
      return Theme.colors.success;
    case 'moderate':
      return Theme.colors.accent;
    case 'elevated':
      return Theme.colors.warning;
    case 'high':
      return Theme.colors.danger;
    default:
      return Theme.colors.textMuted;
  }
}

export function getRiskTone(risk?: string): Tone {
  const value = risk?.toLowerCase();

  if (value === 'low') {
    return 'success';
  }

  if (value === 'moderate') {
    return 'info';
  }

  if (value === 'elevated') {
    return 'warning';
  }

  if (value === 'high') {
    return 'danger';
  }

  return 'muted';
}

export function getAlignmentColor(alignment?: string) {
  switch (alignment) {
    case 'Strong Bullish Alignment':
      return Theme.colors.success;
    case 'Bullish but Mixed':
      return Theme.colors.accent;
    case 'Neutral / Choppy':
      return Theme.colors.warning;
    case 'Bearish Alignment':
      return Theme.colors.danger;
    default:
      return Theme.colors.textMuted;
  }
}

export function getStatusColor(status: string | null | undefined) {
  switch (status?.toLowerCase()) {
    case 'leading':
    case 'bullish':
    case 'strong bullish alignment':
      return Theme.colors.success;
    case 'strong':
    case 'bullish but mixed':
      return Theme.colors.accent;
    case 'neutral':
    case 'neutral / choppy':
    case 'cautious':
      return Theme.colors.warning;
    case 'weak':
    case 'bearish':
    case 'bearish alignment':
      return Theme.colors.danger;
    default:
      return Theme.colors.textMuted;
  }
}

export function getStatusSoftColor(status: string | null | undefined) {
  switch (status?.toLowerCase()) {
    case 'leading':
    case 'bullish':
      return Theme.colors.successSoft;
    case 'strong':
      return Theme.colors.accentSoft;
    case 'weak':
    case 'bearish':
      return Theme.colors.dangerSoft;
    case 'cautious':
      return Theme.colors.warningSoft;
    default:
      return Theme.colors.cardMuted;
  }
}

export function getRelativeStrengthColor(status: string | null | undefined) {
  switch (status?.toLowerCase()) {
    case 'leading':
      return Theme.colors.success;
    case 'strong':
      return Theme.colors.accent;
    case 'weak':
      return Theme.colors.danger;
    case 'neutral':
      return Theme.colors.textMuted;
    default:
      return Theme.colors.textMuted;
  }
}

export function getRelativeStrengthSoftColor(status: string | null | undefined) {
  switch (status?.toLowerCase()) {
    case 'leading':
      return Theme.colors.successSoft;
    case 'strong':
      return Theme.colors.accentSoft;
    case 'weak':
      return Theme.colors.dangerSoft;
    default:
      return Theme.colors.cardMuted;
  }
}

export function getBiasColor(bias?: string) {
  switch (bias?.toLowerCase()) {
    case 'bullish':
      return Theme.colors.success;
    case 'cautious':
      return Theme.colors.warning;
    case 'bearish':
      return Theme.colors.danger;
    case 'neutral':
      return Theme.colors.textMuted;
    default:
      return Theme.colors.textMuted;
  }
}

export function getBiasSoftColor(bias: string | null | undefined) {
  switch (bias?.toLowerCase()) {
    case 'bullish':
      return Theme.colors.successSoft;
    case 'cautious':
      return Theme.colors.warningSoft;
    case 'bearish':
      return Theme.colors.dangerSoft;
    default:
      return Theme.colors.cardMuted;
  }
}

export function getSourceTone(source?: {
  is_live?: boolean | null;
  analysis_is_live?: boolean | null;
  quote_is_live?: boolean | null;
  history_is_live?: boolean | null;
  is_stale?: boolean | null;
  fallback_used?: boolean | null;
  overall_mode?: string | null;
  data_source?: string | null;
  source?: string | null;
  data_status?: string | null;
  dataStatus?: string | null;
  data_quality?: { overall_mode?: string | null } | null;
}): Tone {
  const dataSource = `${source?.data_source ?? source?.source ?? ''}`.toLowerCase();
  const dataStatus = `${source?.data_status ?? source?.dataStatus ?? ''}`.toLowerCase();
  if (dataStatus === 'test' || dataSource.includes('generated_test_data') || dataSource === 'test') {
    return 'muted';
  }

  if (source?.is_stale) {
    return 'warning';
  }

  if (source?.fallback_used) {
    return 'warning';
  }

  const mode = source?.overall_mode ?? source?.data_quality?.overall_mode;
  if (mode === 'mixed') {
    return 'info';
  }

  if (
    mode === 'live'
    || source?.is_live
    || source?.analysis_is_live
    || (source?.quote_is_live && source?.history_is_live)
  ) {
    return 'success';
  }

  if (source?.quote_is_live || source?.history_is_live) {
    return 'info';
  }

  return 'muted';
}
