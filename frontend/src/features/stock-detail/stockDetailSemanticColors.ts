import type { Tone } from '@/components/ui/StatusBadge';
import { Theme } from '@/constants/theme';
import type { StockDetailTone } from '@/features/stock-detail/stockDetailPresenter';

export function stockToneColor(tone: StockDetailTone): string {
  switch (tone) {
    case 'success':
      return Theme.colors.success;
    case 'accent':
      return Theme.colors.accent;
    case 'warning':
      return Theme.colors.warning;
    case 'danger':
      return Theme.colors.danger;
    default:
      return Theme.colors.textMuted;
  }
}

export function stockToneSoftColor(tone: StockDetailTone): string {
  switch (tone) {
    case 'success':
      return Theme.colors.successSoft;
    case 'accent':
      return Theme.colors.accentSoft;
    case 'warning':
      return Theme.colors.warningSoft;
    case 'danger':
      return Theme.colors.dangerSoft;
    default:
      return Theme.colors.cardMuted;
  }
}

export function stockToneToBadgeTone(tone: StockDetailTone): Tone {
  switch (tone) {
    case 'success':
      return 'success';
    case 'accent':
      return 'info';
    case 'warning':
      return 'warning';
    case 'danger':
      return 'danger';
    default:
      return 'muted';
  }
}

export function getRiskTone(riskLevel?: string | null): StockDetailTone {
  const normalized = (riskLevel ?? '').toLowerCase();
  if (normalized.includes('high') || normalized.includes('aggressive') || normalized.includes('elevated')) {
    return 'danger';
  }
  if (normalized.includes('medium') || normalized.includes('moderate') || normalized.includes('mixed')) {
    return 'warning';
  }
  if (normalized.includes('low') || normalized.includes('controlled')) {
    return 'success';
  }
  return 'neutral';
}

export function getQualitativeTone(label?: string | null): StockDetailTone {
  const normalized = (label ?? '').toLowerCase();
  if (normalized.includes('strong') || normalized.includes('supportive') || normalized.includes('high conviction')) {
    return 'success';
  }
  if (normalized.includes('constructive') || normalized.includes('live') || normalized.includes('cached')) {
    return 'accent';
  }
  if (normalized.includes('mixed') || normalized.includes('watch') || normalized.includes('weakening') || normalized.includes('fallback') || normalized.includes('stale')) {
    return 'warning';
  }
  if (normalized.includes('weak') || normalized.includes('negative') || normalized.includes('risk-off') || normalized.includes('high risk')) {
    return 'danger';
  }
  return 'neutral';
}
