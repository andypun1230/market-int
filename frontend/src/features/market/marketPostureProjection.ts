export type MarketPostureLabel = 'Risk On' | 'Selective Risk' | 'Risk Off';

type PostureMetric = {
  direction: string | null;
  label: string;
  score: number | null;
  tone: 'positive' | 'warning' | 'negative' | 'neutral';
  value: string;
};

type PostureLeadershipItem = {
  direction: string | null;
  label: string;
  role: 'Leading Sector' | 'Leading Theme' | 'Lagging Sector';
  tone: 'positive' | 'warning' | 'negative' | 'neutral';
};

export type MarketPostureProjection = {
  factors: PostureMetric[];
  label: MarketPostureLabel;
  tone: 'positive' | 'warning' | 'negative' | 'neutral';
};

/**
 * Authoritative owner of the Home market-posture projection.
 * The thresholds are intentionally unchanged from the former Home implementation.
 */
export function buildMarketPostureProjection({
  breadth,
  healthScore,
  leadership,
  riskScore,
  volatility,
}: {
  breadth: PostureMetric | null;
  healthScore: number | null;
  leadership: PostureLeadershipItem[];
  riskScore: number | null;
  volatility: PostureMetric | null;
}): MarketPostureProjection {
  const riskOff = (riskScore !== null && riskScore >= 65)
    || (healthScore !== null && healthScore < 45)
    || (volatility?.score !== null && volatility?.score !== undefined && volatility.score < 40);
  const riskOn = !riskOff
    && (healthScore ?? 0) >= 70
    && (breadth?.score ?? 0) >= 60
    && (riskScore === null || riskScore <= 35)
    && (volatility?.score ?? 0) >= 60;
  const label: MarketPostureLabel = riskOff ? 'Risk Off' : riskOn ? 'Risk On' : 'Selective Risk';
  const leading = leadership.find((item) => item.role === 'Leading Sector');
  const factors = [
    leading ? {
      direction: leading.direction,
      label: 'Leadership',
      score: null,
      tone: leading.tone,
      value: leading.label,
    } satisfies PostureMetric : null,
    breadth,
    volatility,
  ].filter((item): item is PostureMetric => item !== null).slice(0, 3);

  return {
    factors,
    label,
    tone: label === 'Risk On' ? 'positive' : label === 'Risk Off' ? 'negative' : 'warning',
  };
}
