import { normalizeThemeId } from './themeIds';
import { formatThemeTaxonomyLabel } from './presentation';

export type ThemeInterval = '1D' | '1W' | '1M' | '3M' | '6M' | '1Y';
export type ThemeRotationInterval = '1W' | '1M' | '3M';
export type ThemeRotationPoint = { date: string; dateLabel: string; relativeStrength: number; relativeMomentum: number; isSynthetic: boolean };
export type LiveThemeMember = { ticker: string; companyName: string; role: string; weight: number | null; purity: number | null; importance: number | null; inclusionReason: string; previousTicker: string | null; previousCompanyName: string | null; continuityStatus: string | null };
export type ThemeParticipation = { positiveReturnMemberCount: number | null; negativeReturnMemberCount: number | null; positiveReturnParticipationPct: number | null; positiveContributionSharePct: number | null; horizon: string | null; score: number | null; formulaVersion: string | null };
export type ThemeConcentration = { topOneSharePct: number | null; topThreeSharePct: number | null; hhi: number | null; classification: string | null; qualityScore: number | null; topContributors: { ticker: string; sharePct: number | null }[] };
export type ThemeScoreSemantics = { label: string | null; scale: string | null; relativeRankScope: string | null };
export type ThemeOverlap = { leftThemeId: string; rightThemeId: string; commonMembers: string[]; jaccardOverlap: number | null; weightedOverlap: number | null };
export type LiveThemeItem = {
  id: string;
  name: string;
  parentSector: string;
  returns: Record<ThemeInterval, number | null>;
  rotation: Record<ThemeRotationInterval, { relativeStrength: number | null; relativeMomentum: number | null; history: ThemeRotationPoint[] }>;
  rank: number | null;
  classification: string;
  compositeScore: number | null;
  coverageRatio: number | null;
  memberCount: number | null;
  participation: ThemeParticipation;
  concentration: ThemeConcentration;
  scoreSemantics: ThemeScoreSemantics;
  pilotScope: string | null;
  basketMethodology: string | null;
  sourceState: string;
  status: 'available' | 'partial' | 'unavailable' | string;
  warnings: string[];
  members: LiveThemeMember[];
  weightingPolicy: string | null;
  historicalDisclosure: string | null;
  corporateActionAmendment: boolean;
  reviewCommit: string | null;
};
export type ThemeSnapshotModel = { snapshotId: string; marketDate: string; sourceState: string; status: string; items: LiveThemeItem[]; alerts: Record<string, unknown>[]; warnings: string[]; overlap: ThemeOverlap[]; pilotScope: string | null };

type RecordValue = Record<string, unknown>;

export function adaptThemeSnapshot(value: unknown): ThemeSnapshotModel | null {
  if (!isRecord(value) || !text(value.snapshot_id)) return null;
  const items = list(value.items ?? value.rows).flatMap(adaptThemeItem);
  return {
    snapshotId: text(value.snapshot_id)!,
    marketDate: text(value.market_date) ?? '',
    sourceState: text(value.source_state) ?? 'unavailable',
    status: text(value.status) ?? 'unavailable',
    items,
    alerts: list(value.alerts).filter(isRecord),
    warnings: list(value.warnings).filter((item): item is string => typeof item === 'string'),
    overlap: list(value.overlap_matrix).map(overlap).filter((item): item is ThemeOverlap => item !== null),
    pilotScope: text(isRecord(value.pilot_scope) ? value.pilot_scope.rank_scope : undefined) ?? items[0]?.pilotScope ?? null,
  };
}

function adaptThemeItem(value: unknown): LiveThemeItem[] {
  const themeId = isRecord(value) ? normalizeThemeId(text(value.theme_id)) : null;
  if (!isRecord(value) || !themeId) return [];
  const series = isRecord(value.rotation_series) ? value.rotation_series : {};
  return [{
    id: themeId, name: text(value.display_name) ?? themeId,
    parentSector: parentSector(value),
    returns: returns(value.performance), rotation: { '1W': rotation(series['1W']), '1M': rotation(series['1M']), '3M': rotation(series['3M']) },
    rank: number(value.rank), classification: text(value.classification) ?? 'Unavailable', compositeScore: number(value.composite_score),
    coverageRatio: number(value.coverage_ratio), memberCount: number(value.member_count),
    participation: participation(value.participation), concentration: concentration(value.concentration),
    scoreSemantics: scoreSemantics(value.score_semantics), pilotScope: text(isRecord(value.pilot_scope) ? value.pilot_scope.rank_scope : undefined),
    basketMethodology: text(isRecord(value.basket_methodology) ? value.basket_methodology.policy : undefined),
    sourceState: text(isRecord(value.provenance) ? value.provenance.source_state : undefined) ?? text(value.source_state) ?? 'unavailable',
    status: text(value.status) ?? (text(value.coverage_status) === 'complete' ? 'available' : text(value.coverage_status) === 'partial' ? 'partial' : 'unavailable'),
    warnings: list(value.warnings).filter((item): item is string => typeof item === 'string'),
    members: list(value.members).map(member).filter((item): item is LiveThemeMember => item !== null),
    weightingPolicy: text(isRecord(value.definition) ? value.definition.weighting_policy : undefined),
    historicalDisclosure: text(isRecord(value.definition) ? value.definition.historical_disclosure : undefined),
    corporateActionAmendment: isRecord(value.provenance) && value.provenance.corporate_action_amendment === true,
    reviewCommit: text(isRecord(value.provenance) ? value.provenance.review_commit : undefined),
  }];
}

function returns(value: unknown): Record<ThemeInterval, number | null> { return { '1D': numberAt(value, '1d'), '1W': numberAt(value, '1w'), '1M': numberAt(value, '1m'), '3M': numberAt(value, '3m'), '6M': numberAt(value, '6m'), '1Y': numberAt(value, '1y') }; }
function parentSector(value: RecordValue) { const definition = isRecord(value.definition) ? value.definition : {}; const labels = list(definition.parent_sector_labels).filter((item): item is string => typeof item === 'string'); const ids = list(definition.parent_sector_ids).filter((item): item is string => typeof item === 'string'); return (labels.length ? labels : ids.map(formatThemeTaxonomyLabel)).join(', ') || 'Cross-sector'; }
function participation(value: unknown): ThemeParticipation { return { positiveReturnMemberCount: numberAt(value, 'positive_return_member_count') ?? numberAt(value, 'positive_member_count'), negativeReturnMemberCount: numberAt(value, 'negative_return_member_count') ?? numberAt(value, 'negative_member_count'), positiveReturnParticipationPct: numberAt(value, 'positive_return_participation_pct') ?? numberAt(value, 'positive_return_participation'), positiveContributionSharePct: numberAt(value, 'positive_contribution_share_pct') ?? numberAt(value, 'positive_contribution_share'), horizon: text(isRecord(value) ? value.participation_horizon : undefined), score: numberAt(value, 'participation_score'), formulaVersion: text(isRecord(value) ? value.formula_version : undefined) }; }
function concentration(value: unknown): ThemeConcentration { return { topOneSharePct: numberAt(value, 'top_one_absolute_contribution_share_pct') ?? numberAt(value, 'top_one_absolute_contribution_share'), topThreeSharePct: numberAt(value, 'top_three_absolute_contribution_share_pct') ?? numberAt(value, 'top_three_absolute_contribution_share'), hhi: numberAt(value, 'concentration_hhi') ?? numberAt(value, 'contribution_hhi'), classification: text(isRecord(value) ? value.classification : undefined), qualityScore: numberAt(value, 'concentration_quality_score') ?? numberAt(value, 'quality_score'), topContributors: list(isRecord(value) ? value.top_contributors : undefined).flatMap((item) => isRecord(item) && text(item.ticker) ? [{ ticker: text(item.ticker)!, sharePct: number(item.absolute_contribution_share_pct) ?? number(item.absolute_contribution_share) }] : []) }; }
function scoreSemantics(value: unknown): ThemeScoreSemantics { return { label: text(isRecord(value) ? value.display_label : undefined), scale: text(isRecord(value) ? value.scale : undefined), relativeRankScope: text(isRecord(value) ? value.relative_rank_scope : undefined) }; }
function rotation(value: unknown) { const data = isRecord(value) ? value : {}; const current = point(data.current_point); return { relativeStrength: current?.relativeStrength ?? number(data.relative_strength), relativeMomentum: current?.relativeMomentum ?? number(data.relative_momentum), history: list(data.trail_points).map(point).filter((item): item is ThemeRotationPoint => item !== null) }; }
function overlap(value: unknown): ThemeOverlap | null { if (!isRecord(value)) return null; const leftThemeId = text(value.left_theme_id); const rightThemeId = text(value.right_theme_id); return leftThemeId && rightThemeId ? { leftThemeId, rightThemeId, commonMembers: list(value.common_members).filter((item): item is string => typeof item === 'string'), jaccardOverlap: number(value.jaccard_overlap), weightedOverlap: number(value.weighted_overlap) } : null; }
function point(value: unknown): ThemeRotationPoint | null { if (!isRecord(value)) return null; const date = text(value.market_date) ?? text(value.date) ?? text(value.date_label); const relativeStrength = number(value.plotted_x) ?? number(value.relative_strength); const relativeMomentum = number(value.plotted_y) ?? number(value.relative_momentum); return date && relativeStrength !== null && relativeMomentum !== null ? { date, dateLabel: text(value.date_label) ?? date, relativeStrength, relativeMomentum, isSynthetic: value.is_synthetic === true } : null; }
function member(value: unknown): LiveThemeMember | null { if (!isRecord(value)) return null; const ticker = text(value.ticker); if (!ticker) return null; return { ticker, companyName: text(value.company_name) ?? ticker, role: text(value.role) ?? 'Member', weight: number(value.weight), purity: number(value.purity), importance: number(value.importance), inclusionReason: text(value.inclusion_reason) ?? '', previousTicker: text(value.previous_ticker), previousCompanyName: text(value.previous_company_name), continuityStatus: text(value.continuity_status) }; }
function isRecord(value: unknown): value is RecordValue { return Boolean(value) && typeof value === 'object' && !Array.isArray(value); }
function list(value: unknown): unknown[] { return Array.isArray(value) ? value : []; }
function text(value: unknown): string | null { return typeof value === 'string' ? value : null; }
function number(value: unknown): number | null { return typeof value === 'number' && Number.isFinite(value) ? value : null; }
function numberAt(value: unknown, key: string): number | null { return isRecord(value) ? number(value[key]) : null; }
