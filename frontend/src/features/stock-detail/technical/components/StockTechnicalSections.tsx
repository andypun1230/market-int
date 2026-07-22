import { useState } from 'react';
import type { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { MiniCandlestickChart } from '@/components/charts/MiniCandlestickChart';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { DetailGrid, InfoTile } from '@/components/watchlist/WatchlistPrimitives';
import { Spacing, Theme } from '@/constants/theme';
import {
  stockToneColor,
  stockToneSoftColor,
  stockToneToBadgeTone,
} from '@/features/stock-detail/stockDetailSemanticColors';
import type { StockDetailTone } from '@/features/stock-detail/stockDetailPresenter';
import {
  formatCurrency,
  formatPercent,
  formatRelativeVolume,
  type StockTechnicalViewModel,
  type TechnicalChecklistItem,
  type TechnicalInvalidationItem,
  type TechnicalPriceLevel,
  type TechnicalSourceStatus,
} from '@/features/stock-detail/technical/technicalViewModel';
import {
  getTimeframeSignalRows,
  hasAnyTimeframeSignal,
} from '@/features/stock-detail/technical/timeframeSignalPresenter';
import type {
  DetectedPattern,
  MultiTimeframeTechnicalSignals,
  TimeframeSignalEvidence,
  TimeframeSignalName,
  TimeframeTechnicalSignal,
  SupportResistanceResponse,
  TrendlineResponse,
  VolumeAnalysis,
} from '@/types/market';

type StockTechnicalSectionsProps = {
  model: StockTechnicalViewModel;
  pattern?: DetectedPattern | null;
  supportResistance?: SupportResistanceResponse | null;
  trendline?: TrendlineResponse | null;
  volumeAnalysis?: VolumeAnalysis | null;
};

export function StockTechnicalSections({
  model,
  pattern,
  supportResistance,
  trendline,
  volumeAnalysis,
}: StockTechnicalSectionsProps) {
  const patternSection = <PatternAnalysis model={model} pattern={pattern} />;
  return (
    <View style={styles.sections}>
      <TechnicalSetup model={model} />
      {model.patternTrust.shouldLeadTechnicalTab ? patternSection : null}
      <PriceAndVolume model={model} />
      {!model.patternTrust.shouldLeadTechnicalTab ? patternSection : null}
      <SupportingTechnicalDetails
        model={model}
        pattern={pattern}
        supportResistance={supportResistance}
        trendline={trendline}
        volumeAnalysis={volumeAnalysis}
      />
    </View>
  );
}

export function MultiTimeframeTrend({ embedded = false, signals }: { embedded?: boolean; signals?: MultiTimeframeTechnicalSignals | null }) {
  const [infoVisible, setInfoVisible] = useState(false);
  if (!hasAnyTimeframeSignal(signals)) {
    return (
      <TimeframeContainer embedded={embedded}>
        <TimeframeSectionHeader
          infoVisible={infoVisible}
          onToggleInfo={() => setInfoVisible((current) => !current)}
          status="unavailable"
        />
        {infoVisible ? <TimeframeInfo /> : null}
        <Text style={styles.emptyText}>Timeframe signal data is unavailable.</Text>
      </TimeframeContainer>
    );
  }

  const rows = getTimeframeSignalRows(signals);
  const overallDataStatus = signals?.overallDataStatus;
  const sharedStatus = getSharedRowStatus(rows);
  return (
    <TimeframeContainer embedded={embedded}>
      <TimeframeSectionHeader
        infoVisible={infoVisible}
        onToggleInfo={() => setInfoVisible((current) => !current)}
        status={formatTimeframeProvenance(overallDataStatus, sharedStatus)}
      />
      {infoVisible ? <TimeframeInfo /> : null}
      <View style={styles.signalRows}>
        {rows.map((signal, index) => (
          <TimeframeSignalRow
            key={signal.timeframe}
            showStatus={sharedStatus == null || signal.dataStatus !== sharedStatus}
            signal={signal}
            showDivider={index > 0}
          />
        ))}
      </View>
    </TimeframeContainer>
  );
}

function TimeframeContainer({ children, embedded }: { children: ReactNode; embedded: boolean }) {
  return embedded ? <View style={styles.embeddedSection}>{children}</View> : <SectionSurface>{children}</SectionSurface>;
}

function TimeframeSectionHeader({
  infoVisible,
  onToggleInfo,
  status,
}: {
  infoVisible: boolean;
  onToggleInfo: () => void;
  status?: string | null;
}) {
  return (
    <View style={styles.sectionHeaderRow}>
      <View style={styles.timeframeTitleRow}>
        <Text style={styles.sectionTitle}>Multi-Timeframe Trend</Text>
        <Pressable
          accessibilityLabel={`${infoVisible ? 'Hide' : 'Show'} multi-timeframe trend information`}
          accessibilityRole="button"
          accessibilityState={{ expanded: infoVisible }}
          onPress={onToggleInfo}
          style={styles.infoButton}>
          <Text style={styles.infoButtonText}>i</Text>
        </Pressable>
      </View>
      <StatusBadge
        label={status || 'Unavailable'}
        tone={stockToneToBadgeTone(dataStatusTone(status))}
      />
    </View>
  );
}

function TimeframeInfo() {
  return (
    <Text style={styles.timeframeInfoText}>
      Technical direction can differ across short-, medium-, and long-term horizons. These signals summarize current conditions and do not predict future returns.
    </Text>
  );
}

function getSharedRowStatus(rows: TimeframeTechnicalSignal[]): string | null {
  if (!rows.length) {
    return null;
  }
  const statuses = new Set(rows.map((row) => row.dataStatus));
  return statuses.size === 1 ? rows[0]?.dataStatus ?? null : null;
}

function formatTimeframeProvenance(
  overallStatus?: string | null,
  sharedStatus?: string | null,
): string {
  if (sharedStatus) {
    return formatDataStatus(sharedStatus);
  }
  const normalized = (overallStatus ?? '').toLowerCase();
  if (normalized.includes('test')) {
    return 'Mixed Test Data';
  }
  return normalized ? 'Mixed sources' : 'Unavailable';
}

function TimeframeSignalRow({
  showDivider,
  showStatus,
  signal,
}: {
  showDivider: boolean;
  showStatus: boolean;
  signal: TimeframeTechnicalSignal;
}) {
  const [expanded, setExpanded] = useState(false);
  const tone = signalTone(signal.signal);
  const positiveEvidence = signal.positiveEvidence ?? [];
  const negativeEvidence = signal.negativeEvidence ?? [];
  const hasEvidence = Boolean(positiveEvidence.length || negativeEvidence.length);
  return (
    <View
      accessibilityLabel={`${displayTimeframe(signal.timeframe)} technical signal: ${formatSignal(signal.signal)}${signal.score == null ? '' : `, score ${signal.score} out of 100`}. ${signal.explanation}`}
      style={[styles.signalCard, showDivider && styles.signalCardDivider]}>
      <View style={styles.signalTopRow}>
        <View style={styles.signalTitleBlock}>
          <Text style={styles.signalTitle}>{displayTimeframe(signal.timeframe)}</Text>
          <Text style={styles.signalHorizon}>{signal.horizonLabel}</Text>
        </View>
        <View style={styles.signalStatusBlock}>
          <Text style={[styles.signalLabel, { color: stockToneColor(tone) }]}>{formatSignal(signal.signal)}</Text>
          <Text style={styles.signalScore}>{signal.score == null ? 'No score' : `${signal.score} / 100`}</Text>
          {showStatus ? <Text style={styles.signalStatusText}>{formatDataStatus(signal.dataStatus)}</Text> : null}
        </View>
      </View>
      <FiveStateSignalMeter signal={signal.signal} score={signal.score} />
      {hasEvidence ? (
        <>
          <Pressable
            accessibilityLabel={`${expanded ? 'Hide' : 'Show'} ${displayTimeframe(signal.timeframe)} signal evidence`}
            accessibilityRole="button"
            accessibilityState={{ expanded }}
            onPress={() => setExpanded((current) => !current)}
            style={styles.evidenceToggle}>
            <Text style={styles.evidenceToggleText}>{expanded ? 'Hide why' : 'Why this signal'}</Text>
            <Text style={styles.accordionIcon}>{expanded ? '⌄' : '›'}</Text>
          </Pressable>
          {expanded ? (
            <View style={styles.evidenceGrid}>
              <Text style={styles.evidenceExplanation}>{signal.explanation}</Text>
              <EvidenceGroup title="Positive" items={positiveEvidence} />
              <EvidenceGroup title="Limiting" items={negativeEvidence} />
            </View>
          ) : null}
        </>
      ) : null}
    </View>
  );
}

function FiveStateSignalMeter({ score, signal }: { score: number | null; signal: TimeframeSignalName }) {
  const states: TimeframeSignalName[] = ['strong_bearish', 'bearish', 'neutral', 'bullish', 'strong_bullish'];
  const activeIndex = states.indexOf(signal);
  return (
    <View>
      <View style={styles.segmentRow}>
        {states.map((state, index) => {
          const active = index === activeIndex && signal !== 'unavailable';
          return (
            <View
              accessibilityLabel={`${formatSignal(state)} segment${active ? ', active' : ''}`}
              key={state}
              style={[
                styles.signalSegment,
                { backgroundColor: active ? stockToneColor(signalTone(state)) : Theme.colors.backgroundMuted },
                active && styles.signalSegmentActive,
                signal === 'unavailable' && styles.signalSegmentUnavailable,
              ]}>
              {active ? <View style={styles.signalMarker} /> : null}
            </View>
          );
        })}
      </View>
      <View style={styles.segmentLabelRow}>
        <Text style={styles.segmentEndpoint}>Bearish</Text>
        <Text style={styles.segmentMidpoint}>{signal === 'unavailable' ? 'Unavailable' : score == null ? 'No score' : `${score}`}</Text>
        <Text style={styles.segmentEndpoint}>Bullish</Text>
      </View>
    </View>
  );
}

function EvidenceGroup({ items, title }: { items: TimeframeSignalEvidence[]; title: string }) {
  const visible = items.slice(0, 3);
  if (!visible.length) {
    return null;
  }
  return (
    <View style={styles.evidenceGroup}>
      <Text style={styles.evidenceTitle}>{title}</Text>
      {visible.map((item) => (
        <Text key={item.key} style={styles.evidenceItem}>• {item.label}</Text>
      ))}
    </View>
  );
}

function TechnicalSetup({ model }: { model: StockTechnicalViewModel }) {
  const rows = [
    ...(model.patternTrust.isCurrent ? [
      ['Pattern', model.pattern.name],
      ['Stage', model.pattern.stage],
      ['Direction', model.pattern.direction],
    ] : [['Current pattern', model.pattern.name ? 'Not reliably confirmed' : null]]),
    ['Confirmation', model.setup.confirmationLevel == null ? null : `Above ${formatCurrency(model.setup.confirmationLevel)}`],
    ['Invalidation', model.setup.invalidationLevel == null ? null : `Below ${formatCurrency(model.setup.invalidationLevel)}`],
    ['Volume', model.setup.volumeState],
    ['Trend', model.setup.trendState],
  ].filter((row): row is [string, string] => Boolean(row[1]));
  const hasTrend = model.trend.risingSupportDetected != null || model.trend.supportStatus || model.trend.touchCount != null || model.trend.distancePercent != null || model.trend.explanation;
  return (
    <SectionSurface accentColor={stockToneColor(stanceTone(model.summary.stance))}>
      <Text style={styles.sectionTitle}>Technical Setup</Text>
      <Text style={styles.summaryHeadline}>{model.summary.headline}</Text>
      <Text style={styles.summarySubtitle}>{model.summary.subtitle}</Text>
      <Text style={styles.bodyText}>{model.summary.body}</Text>
      {!model.provenance.sourcesCompatible && model.provenance.mismatchReason ? (
        <View style={styles.infoBox}>
          <Text style={styles.warningText}>{model.provenance.mismatchReason}</Text>
        </View>
      ) : null}
      {rows.length ? (
        <>
          <SubsectionDivider />
          <Text style={styles.subsectionTitle}>Current Setup</Text>
          <View style={styles.rowStack}>{rows.map(([label, value]) => <CompactRow key={label} label={label} value={value} />)}</View>
        </>
      ) : null}
      {model.confirmations.length || model.invalidations.length ? (
        <>
          <SubsectionDivider />
          <Text style={styles.subsectionTitle}>Confirmation</Text>
          {model.confirmations.length ? <ChecklistGroup items={model.confirmations} title="Confirms" /> : null}
          {model.invalidations.length ? <InvalidationGroup items={model.invalidations} title="Weakens" /> : null}
        </>
      ) : null}
      {hasTrend ? (
        <>
          <SubsectionDivider />
          <Text style={styles.subsectionTitle}>Trend Structure</Text>
          <View style={styles.rowStack}>
            {model.trend.risingSupportDetected != null ? <CompactRow label="Rising support" value={model.trend.risingSupportDetected ? 'Detected' : 'Not detected'} /> : null}
            {model.trend.supportStatus ? <CompactRow label="Support status" value={model.trend.supportStatus} /> : null}
            {model.trend.touchCount != null ? <CompactRow label="Confirmed touches" value={String(model.trend.touchCount)} /> : null}
            {model.trend.distancePercent != null ? <CompactRow label="Distance from line" value={formatPercent(Math.abs(model.trend.distancePercent))} /> : null}
          </View>
          {model.trend.explanation ? <Text style={styles.bodyText}>{model.trend.explanation}</Text> : null}
        </>
      ) : null}
    </SectionSurface>
  );
}

function SubsectionDivider() {
  return <View style={styles.subsectionDivider} />;
}

function PatternAnalysis({ model, pattern }: { model: StockTechnicalViewModel; pattern?: DetectedPattern | null }) {
  const score = model.pattern.score;
  const [expanded, setExpanded] = useState(model.patternTrust.shouldLeadTechnicalTab);
  const isCurrent = model.patternTrust.shouldLeadTechnicalTab;
  const title = isCurrent ? 'Pattern Analysis' : model.patternTrust.userLabel;
  return (
    <SectionSurface accentColor={isCurrent ? stockToneColor(sourceTone(model.pattern.sourceStatus)) : undefined}>
      <View style={styles.sectionHeaderRow}>
        <Text style={styles.sectionTitle}>{title}</Text>
        <StatusBadge
          label={sourceLabel(model.pattern.sourceStatus, 'pattern')}
          tone={stockToneToBadgeTone(sourceTone(model.pattern.sourceStatus))}
        />
      </View>
      {model.pattern.name ? (
        <>
          <View style={styles.patternTop}>
            <View style={styles.patternTitleBlock}>
              <Text style={styles.patternName}>{model.pattern.name}</Text>
              <Text style={styles.patternMeta}>
                {[model.pattern.detectedAt ? `Detected ${formatShortDate(model.pattern.detectedAt)}` : null, model.pattern.stage, isCurrent ? model.pattern.direction : null].filter(Boolean).join(' · ')}
              </Text>
            </View>
            <View style={[styles.patternScore, !model.patternTrust.shouldShowScoreProminently && styles.patternScoreSecondary]}>
              <Text style={styles.patternScoreValue}>{score == null ? 'N/A' : Math.round(score)}</Text>
              <Text style={styles.patternScoreLabel}>/ 100</Text>
            </View>
          </View>
          {model.patternTrust.shouldShowScoreProminently ? <ScoreMeter score={score} tone={sourceTone(model.pattern.sourceStatus)} /> : null}
          {!model.patternTrust.shouldShowScoreProminently && score != null ? (
            <Text style={styles.secondaryMeta}>Pattern match score {Math.round(score)} / 100. This is not a success probability.</Text>
          ) : null}
          {!isCurrent && model.patternTrust.explanation ? <Text style={styles.bodyText}>{model.patternTrust.explanation}</Text> : null}
          {pattern?.chart_data?.length && expanded ? (
            <MiniCandlestickChart
              candles={pattern.chart_data}
              height={220}
              keyLevels={model.provenance.sourcesCompatible ? pattern.key_levels : undefined}
              markers={pattern.markers ?? []}
            />
          ) : (
            pattern?.chart_data?.length ? null : <Text style={styles.emptyText}>Pattern chart unavailable.</Text>
          )}
          {pattern?.chart_data?.length && !isCurrent ? (
            <Pressable
              accessibilityLabel={`${expanded ? 'Hide' : 'Show'} pattern chart`}
              accessibilityRole="button"
              accessibilityState={{ expanded }}
              onPress={() => setExpanded((current) => !current)}
              style={styles.smallDisclosure}>
              <Text style={styles.smallDisclosureText}>{expanded ? 'Hide pattern chart' : 'Show pattern chart'}</Text>
              <Text style={styles.accordionIcon}>{expanded ? '⌄' : '›'}</Text>
            </Pressable>
          ) : null}
          <Text style={styles.bodyText}>
            {model.patternTrust.shouldLeadTechnicalTab
              ? model.pattern.description ?? 'Pattern details are available in supporting technical details.'
              : 'This pattern is retained for context and is not used for current live levels.'}
          </Text>
        </>
      ) : (
        <Text style={styles.bodyText}>No reliable current pattern is available. Current support, resistance, volume, and trend data remain available below.</Text>
      )}
    </SectionSurface>
  );
}

function PriceAndVolume({ model }: { model: StockTechnicalViewModel }) {
  const levels = model.priceLevels;
  const hasVolume = Boolean(model.volume.quality || model.volume.relativeVolume != null);
  if (!levels.length && !hasVolume) {
    return null;
  }
  const commonStatus = getCommonSourceStatus(levels);
  const relative = model.volume.relativeVolume;
  const meter = Math.max(0, Math.min(((relative ?? 0) / 2) * 100, 100));
  const tone = volumeTone(model.volume.quality, relative);
  return (
    <SectionSurface>
      <View style={styles.sectionHeaderRow}>
        <Text style={styles.sectionTitle}>Price & Volume</Text>
        {commonStatus ? (
          <StatusBadge label={sourceLabel(commonStatus, '')} tone={stockToneToBadgeTone(sourceTone(commonStatus))} />
        ) : null}
      </View>
      {levels.length ? <View accessibilityLabel={levels.map((level) => `${level.label} ${formatCurrency(level.value)}`).join(', ')} style={styles.ladder}>
        {levels.map((level) => (
          <View key={level.key} style={styles.levelRow}>
            <View style={[styles.levelLine, { backgroundColor: stockToneColor(levelTone(level.kind)) }]} />
            <Text style={[styles.levelPrice, { color: stockToneColor(levelTone(level.kind)) }]}>
              {formatCurrency(level.value)}
            </Text>
            <View style={styles.levelCopy}>
              <Text style={styles.levelLabel}>{level.label}</Text>
              <Text style={styles.levelSource}>
                {formatLevelPrice(level)}
                {commonStatus && level.sourceStatus === commonStatus ? '' : ` · ${sourceLabel(level.sourceStatus, '')}`}
              </Text>
            </View>
          </View>
        ))}
      </View> : null}
      {levels.length && hasVolume ? <SubsectionDivider /> : null}
      {hasVolume ? <View style={styles.embeddedSection}>
        <Text style={styles.subsectionTitle}>Volume Assessment</Text>
        <View style={styles.volumeHeader}>
        <Text style={[styles.volumeQuality, { color: stockToneColor(tone) }]}>{model.volume.quality ?? 'Volume unavailable'}</Text>
        <Text style={styles.volumeRelative}>{formatRelativeVolume(relative)} normal</Text>
      </View>
      <View style={styles.volumeMeter}>
        <View style={[styles.volumeMeterFill, { backgroundColor: stockToneColor(tone), width: `${meter}%` }]} />
      </View>
      {model.volume.signal ? <StatusBadge label={model.volume.signal} tone={stockToneToBadgeTone(tone)} /> : null}
        {model.volume.explanation ? <Text style={styles.bodyText}>{model.volume.explanation}</Text> : null}
      </View> : null}
    </SectionSurface>
  );
}

function SupportingTechnicalDetails({
  model,
  pattern,
  supportResistance,
  trendline,
  volumeAnalysis,
}: StockTechnicalSectionsProps) {
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const toggle = (key: string) => setOpen((current) => ({ ...current, [key]: !current[key] }));
  const showIllustrativeLevels = model.provenance.sourcesCompatible && model.pattern.sourceStatus !== 'mock' && model.pattern.sourceStatus !== 'fallback';

  return (
    <View style={styles.disclosurePanel}>
      <Text style={styles.sectionTitle}>Supporting Technical Details</Text>
      <AccordionRow expanded={Boolean(open.pattern)} label="Pattern Details" onPress={() => toggle('pattern')} />
      {open.pattern ? (
        <DetailGrid>
          <InfoTile label="Preview" value={patternPreview(model)} />
          <InfoTile label="Name" value={model.pattern.name ?? 'Unavailable'} />
          <InfoTile label="Stage" value={model.pattern.stage ?? 'Unavailable'} />
          <InfoTile label="Direction" value={model.pattern.direction ?? 'Unavailable'} />
          <InfoTile label="Timeframe" value={pattern?.timeframe ?? 'Unavailable'} />
          <InfoTile label="Detected" value={model.pattern.detectedAt ?? 'Unavailable'} />
          <InfoTile label="Source" value={sourceLabel(model.pattern.sourceStatus, 'pattern')} />
        </DetailGrid>
      ) : null}
      <Divider />
      <AccordionRow
        expanded={Boolean(open.zones)}
        label="Raw Calculated Zones"
        onPress={() => toggle('zones')}
        preview={`${supportResistance?.support_zones?.length ?? 0} support · ${supportResistance?.resistance_zones?.length ?? 0} resistance`}
      />
      {open.zones ? (
        <DetailGrid>
          <InfoTile label="Support zones" value={(supportResistance?.support_zones ?? []).map((zone) => formatPriceRange(zone.low, zone.high)).join('\n') || 'Unavailable'} />
          <InfoTile label="Resistance zones" value={(supportResistance?.resistance_zones ?? []).map((zone) => formatPriceRange(zone.low, zone.high)).join('\n') || 'Unavailable'} />
          <InfoTile label="Breakout" value={formatCurrency(supportResistance?.breakout_level)} />
          <InfoTile label="Stop reference" value={formatCurrency(supportResistance?.stop_reference)} />
          <InfoTile label="EMA20" value={formatCurrency(supportResistance?.moving_average_support?.ema_20)} />
          <InfoTile label="EMA50" value={formatCurrency(supportResistance?.moving_average_support?.ema_50)} />
        </DetailGrid>
      ) : null}
      <Divider />
      <AccordionRow expanded={Boolean(open.trend)} label="Trendline Diagnostics" onPress={() => toggle('trend')} preview={trendPreview(model)} />
      {open.trend ? (
        <DetailGrid>
          <InfoTile label="Rising support" value={model.trend.risingSupportDetected ? 'Detected' : 'Not detected'} />
          <InfoTile label="Support status" value={model.trend.supportStatus ?? 'Unavailable'} />
          <InfoTile label="Touch count" value={model.trend.touchCount == null ? 'Unavailable' : String(model.trend.touchCount)} />
          <InfoTile label="Falling resistance" value={model.trend.fallingResistanceDetected ? 'Detected' : 'Not detected'} />
          <InfoTile label="Break" value={trendline?.trendline_break?.description ?? 'Unavailable'} />
        </DetailGrid>
      ) : null}
      <Divider />
      <AccordionRow expanded={Boolean(open.indicators)} label="Indicator Values" onPress={() => toggle('indicators')} preview={indicatorPreview(volumeAnalysis)} />
      {open.indicators ? (
        <DetailGrid>
          <InfoTile label="Relative volume" value={formatRelativeVolume(volumeAnalysis?.relative_volume)} />
          <InfoTile label="Volume quality" value={volumeAnalysis?.volume_quality ?? 'Unavailable'} />
          <InfoTile label="Volume score" value={volumeAnalysis?.volume_quality_score == null ? 'Unavailable' : String(volumeAnalysis.volume_quality_score)} />
          <InfoTile label="Accumulation" value={volumeAnalysis?.accumulation_volume ? 'Yes' : 'No'} />
          <InfoTile label="Distribution" value={volumeAnalysis?.distribution_volume ? 'Yes' : 'No'} />
        </DetailGrid>
      ) : null}
      {showIllustrativeLevels ? (
        <>
          <Divider />
          <AccordionRow expanded={Boolean(open.levels)} label="Illustrative Setup Levels" onPress={() => toggle('levels')} />
          {open.levels ? (
            <View style={styles.educationalBox}>
              <Text style={styles.bodyText}>Educational example derived from compatible detected setup levels. Not a recommendation.</Text>
              <DetailGrid>
                <InfoTile label="Confirmation above" value={formatCurrency(pattern?.key_levels?.breakout ?? supportResistance?.breakout_level)} />
                <InfoTile label="Invalidation below" value={formatCurrency(pattern?.key_levels?.stop_reference ?? supportResistance?.stop_reference)} />
                <InfoTile label="Pattern support" value={formatCurrency(pattern?.key_levels?.support)} />
                <InfoTile label="Pattern resistance" value={formatCurrency(pattern?.key_levels?.resistance ?? pattern?.key_levels?.neckline)} />
              </DetailGrid>
            </View>
          ) : null}
        </>
      ) : null}
      <Divider />
      <AccordionRow expanded={Boolean(open.methodology)} label="Methodology" onPress={() => toggle('methodology')} />
      {open.methodology ? (
        <Text style={styles.bodyText}>
          Current levels come from the support/resistance and trend engines. Pattern levels remain separate when they are mock, fallback, historical, stale, or materially different from current calculated zones. Educational analysis only, not financial advice.
        </Text>
      ) : null}
    </View>
  );
}

function ChecklistGroup({ items, title }: { items: TechnicalChecklistItem[]; title: string }) {
  return (
    <View style={styles.checkGroup}>
      <Text style={styles.subsectionTitle}>{title}</Text>
      {items.map((item) => (
        <ChecklistRow key={item.key} item={item} />
      ))}
    </View>
  );
}

function InvalidationGroup({ items, title }: { items: TechnicalInvalidationItem[]; title: string }) {
  return (
    <View style={styles.checkGroup}>
      <Text style={styles.subsectionTitle}>{title}</Text>
      {items.map((item) => (
        <ChecklistRow
          item={{
            explanation: item.explanation,
            key: item.key,
            label: item.label,
            status: invalidationToChecklist(item.status),
          }}
          key={item.key}
        />
      ))}
    </View>
  );
}

function ChecklistRow({ item }: { item: TechnicalChecklistItem }) {
  const tone = checklistTone(item.status);
  return (
    <View accessibilityLabel={`${item.status}: ${item.label}`} style={styles.checkRow}>
      <Text style={[styles.checkIcon, { color: stockToneColor(tone) }]}>{checkIcon(item.status)}</Text>
      <View style={styles.checkCopy}>
        <Text style={styles.checkLabel}>{item.label}</Text>
        {item.explanation ? <Text style={styles.checkExplanation}>{item.explanation}</Text> : null}
      </View>
    </View>
  );
}

function CompactRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.compactRow}>
      <Text style={styles.compactLabel}>{label}</Text>
      <Text style={styles.compactValue}>{value}</Text>
    </View>
  );
}

function AccordionRow({ expanded, label, onPress, preview }: { expanded: boolean; label: string; onPress: () => void; preview?: string | null }) {
  return (
    <Pressable
      accessibilityLabel={`${expanded ? 'Hide' : 'Show'} ${label}`}
      accessibilityRole="button"
      accessibilityState={{ expanded }}
      onPress={onPress}
      style={styles.accordionRow}>
      <View style={styles.accordionCopy}>
        <Text style={styles.accordionText}>{label}</Text>
        {preview ? <Text style={styles.accordionPreview}>{preview}</Text> : null}
      </View>
      <Text style={styles.accordionIcon}>{expanded ? '⌄' : '›'}</Text>
    </Pressable>
  );
}

function SectionSurface({ accentColor, children }: { accentColor?: string; children: ReactNode }) {
  return (
    <View style={[styles.surface, accentColor ? { borderTopColor: accentColor, borderTopWidth: 2 } : null]}>
      {children}
    </View>
  );
}

function ScoreMeter({ score, tone }: { score: number | null; tone: StockDetailTone }) {
  if (score == null) {
    return null;
  }
  return (
    <View style={styles.scoreTrack}>
      <View style={[styles.scoreFill, { backgroundColor: stockToneColor(tone), width: `${Math.max(0, Math.min(score, 100))}%` }]} />
    </View>
  );
}

function Divider() {
  return <View style={styles.divider} />;
}

function sourceLabel(status: TechnicalSourceStatus, label: string) {
  if (status === 'test') {
    return 'Test Data';
  }
  const formatted = status.charAt(0).toUpperCase() + status.slice(1);
  return label ? `${formatted} ${label}` : formatted;
}

function displayTimeframe(timeframe: TimeframeTechnicalSignal['timeframe']): string {
  if (timeframe === 'short') {
    return 'Short Term';
  }
  if (timeframe === 'medium') {
    return 'Medium Term';
  }
  return 'Long Term';
}

function formatSignal(signal: TimeframeSignalName): string {
  if (signal === 'unavailable') {
    return 'Unavailable';
  }
  return signal
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function signalTone(signal: TimeframeSignalName): StockDetailTone {
  if (signal === 'strong_bullish' || signal === 'bullish') {
    return 'success';
  }
  if (signal === 'neutral') {
    return 'accent';
  }
  if (signal === 'bearish') {
    return 'warning';
  }
  if (signal === 'strong_bearish') {
    return 'danger';
  }
  return 'neutral';
}

function dataStatusTone(status?: string | null): StockDetailTone {
  const normalized = (status ?? '').toLowerCase();
  if (normalized === 'live' || normalized === 'cached') {
    return 'success';
  }
  if (normalized === 'partial' || normalized === 'mixed') {
    return 'accent';
  }
  if (normalized === 'fallback' || normalized === 'stale') {
    return 'warning';
  }
  return 'neutral';
}

function formatDataStatus(status?: string | null): string {
  if (!status) {
    return 'Unavailable';
  }
  if (status === 'test') {
    return 'Test Data';
  }
  return status
    .replace(/_/g, ' ')
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function sourceTone(status: TechnicalSourceStatus) {
  if (status === 'test') {
    return 'neutral';
  }
  if (status === 'live' || status === 'cached') {
    return 'accent';
  }
  if (status === 'fallback' || status === 'stale' || status === 'historical') {
    return 'warning';
  }
  if (status === 'mock' || status === 'unavailable') {
    return 'neutral';
  }
  return 'neutral';
}

function stanceTone(stance: StockTechnicalViewModel['summary']['stance']) {
  if (stance === 'bullish') {
    return 'success';
  }
  if (stance === 'constructive' || stance === 'neutral') {
    return 'accent';
  }
  if (stance === 'weakening') {
    return 'warning';
  }
  if (stance === 'bearish') {
    return 'danger';
  }
  return 'neutral';
}

function checklistTone(status: TechnicalChecklistItem['status']) {
  if (status === 'met') {
    return 'success';
  }
  if (status === 'failed') {
    return 'danger';
  }
  if (status === 'watch') {
    return 'warning';
  }
  if (status === 'pending') {
    return 'accent';
  }
  return 'neutral';
}

function checkIcon(status: TechnicalChecklistItem['status']) {
  if (status === 'met') {
    return '✓';
  }
  if (status === 'failed') {
    return '×';
  }
  if (status === 'watch') {
    return '!';
  }
  if (status === 'pending') {
    return '○';
  }
  return '–';
}

function invalidationToChecklist(status: TechnicalInvalidationItem['status']): TechnicalChecklistItem['status'] {
  if (status === 'triggered') {
    return 'failed';
  }
  if (status === 'active') {
    return 'watch';
  }
  if (status === 'watch') {
    return 'watch';
  }
  return 'unavailable';
}

function levelTone(kind: TechnicalPriceLevel['kind']) {
  if (kind === 'resistance' || kind === 'confirmation') {
    return 'accent';
  }
  if (kind === 'current') {
    return 'success';
  }
  if (kind === 'invalidation') {
    return 'danger';
  }
  if (kind === 'support') {
    return 'warning';
  }
  return 'neutral';
}

function volumeTone(quality?: string | null, relativeVolume?: number | null) {
  const normalized = quality?.toLowerCase() ?? '';
  if (normalized.includes('excellent') || normalized.includes('strong') || (relativeVolume ?? 0) >= 1.5) {
    return 'success';
  }
  if (normalized.includes('average') || (relativeVolume ?? 0) >= 0.9) {
    return 'accent';
  }
  if (normalized.includes('weak')) {
    return 'warning';
  }
  if (normalized.includes('poor')) {
    return 'danger';
  }
  return 'neutral';
}

function getCommonSourceStatus(levels: TechnicalPriceLevel[]): TechnicalSourceStatus | null {
  const statuses = new Set(levels.map((level) => level.sourceStatus));
  return statuses.size === 1 ? levels[0]?.sourceStatus ?? null : null;
}

function formatLevelPrice(level: TechnicalPriceLevel): string {
  if (level.zoneLow != null && level.zoneHigh != null && Math.abs(level.zoneHigh - level.zoneLow) > 0.01) {
    return formatPriceRange(level.zoneLow, level.zoneHigh);
  }
  return formatCurrency(level.value);
}

function formatPriceRange(low?: number | null, high?: number | null): string {
  if (low == null && high == null) {
    return 'Unavailable';
  }
  if (low == null || high == null || Math.abs(high - low) <= 0.01) {
    return formatCurrency(low ?? high ?? null);
  }
  return `${formatCurrency(low)}–${formatCurrency(high)}`;
}

function patternPreview(model: StockTechnicalViewModel): string {
  return [
    model.pattern.name,
    sourceLabel(model.pattern.sourceStatus, 'pattern'),
    model.pattern.detectedAt ? formatShortDate(model.pattern.detectedAt) : null,
  ].filter(Boolean).join(' · ') || 'Pattern unavailable';
}

function trendPreview(model: StockTechnicalViewModel): string {
  const parts = [
    model.trend.risingSupportDetected ? 'Rising support detected' : null,
    model.trend.touchCount != null ? `${model.trend.touchCount} touches` : null,
  ].filter(Boolean);
  return parts.join(' · ') || 'Trend diagnostics';
}

function indicatorPreview(volumeAnalysis?: VolumeAnalysis | null): string {
  return [
    volumeAnalysis?.volume_quality ? `Volume ${volumeAnalysis.volume_quality}` : null,
    volumeAnalysis?.relative_volume != null ? `${formatRelativeVolume(volumeAnalysis.relative_volume)} relative volume` : null,
  ].filter(Boolean).join(' · ') || 'Indicator values';
}

function formatShortDate(value: string): string {
  const date = new Date(value);
  if (!Number.isNaN(date.getTime())) {
    return date.toLocaleDateString('en-US', { day: 'numeric', month: 'short' });
  }
  const [, month, day] = value.split('-');
  return month && day ? `${month}/${day}` : value;
}

const styles = StyleSheet.create({
  accordionIcon: {
    color: Theme.colors.textMuted,
    fontSize: 20,
    fontWeight: '900',
  },
  accordionRow: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    minHeight: 44,
  },
  accordionCopy: {
    flex: 1,
    gap: Spacing.half,
    minWidth: 0,
  },
  accordionPreview: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '800',
    textAlign: 'right',
  },
  accordionText: {
    color: Theme.colors.text,
    fontSize: 13,
    fontWeight: '900',
  },
  bodyText: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    fontWeight: '700',
    lineHeight: 19,
  },
  checkCopy: {
    flex: 1,
    gap: Spacing.half,
  },
  checkExplanation: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '700',
  },
  checkGroup: {
    gap: Spacing.one,
  },
  checkIcon: {
    fontSize: 13,
    fontWeight: '900',
    width: 18,
  },
  checkLabel: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '800',
    lineHeight: 17,
  },
  checkRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.one,
  },
  compactLabel: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  compactRow: {
    alignItems: 'center',
    borderBottomColor: Theme.colors.border,
    borderBottomWidth: 1,
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
    paddingVertical: Spacing.one,
  },
  compactValue: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: 13,
    fontWeight: '900',
    textAlign: 'right',
  },
  divider: {
    backgroundColor: Theme.colors.border,
    height: 1,
  },
  disclosurePanel: {
    gap: Spacing.one,
    paddingHorizontal: Spacing.one,
  },
  educationalBox: {
    gap: Spacing.two,
  },
  embeddedSection: {
    gap: Spacing.two,
  },
  emptyText: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    fontWeight: '700',
  },
  evidenceGrid: {
    gap: Spacing.one,
  },
  evidenceExplanation: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
    lineHeight: 17,
  },
  evidenceGroup: {
    gap: Spacing.half,
  },
  evidenceItem: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
    lineHeight: 17,
  },
  evidenceTitle: {
    color: Theme.colors.text,
    fontSize: 11,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  evidenceToggle: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    minHeight: 28,
  },
  evidenceToggleText: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '900',
  },
  infoBox: {
    backgroundColor: stockToneSoftColor('warning'),
    borderRadius: Theme.radii.small,
    padding: Spacing.two,
  },
  infoButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    height: 24,
    justifyContent: 'center',
    width: 24,
  },
  infoButtonText: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    fontWeight: '900',
  },
  ladder: {
    gap: Spacing.one,
  },
  levelCopy: {
    flex: 1,
    gap: Spacing.half,
  },
  levelLabel: {
    color: Theme.colors.text,
    fontSize: 13,
    fontWeight: '900',
  },
  levelLine: {
    borderRadius: Theme.radii.pill,
    height: 28,
    width: 3,
  },
  levelPrice: {
    fontSize: 14,
    fontWeight: '900',
    width: 82,
  },
  levelRow: {
    alignItems: 'center',
    backgroundColor: Theme.colors.backgroundMuted,
    borderRadius: Theme.radii.small,
    flexDirection: 'row',
    gap: Spacing.two,
    minHeight: 44,
    paddingHorizontal: Spacing.two,
  },
  levelSource: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '800',
  },
  patternMeta: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '800',
  },
  patternName: {
    color: Theme.colors.text,
    fontSize: 18,
    fontWeight: '900',
  },
  patternScore: {
    alignItems: 'baseline',
    flexDirection: 'row',
  },
  patternScoreSecondary: {
    opacity: 0.72,
  },
  patternScoreLabel: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '900',
  },
  patternScoreValue: {
    color: Theme.colors.text,
    fontSize: 25,
    fontWeight: '900',
  },
  patternTitleBlock: {
    flex: 1,
    gap: Spacing.half,
    minWidth: 0,
  },
  patternTop: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  rowStack: {
    gap: Spacing.half,
  },
  secondaryMeta: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '800',
    lineHeight: 16,
  },
  scoreFill: {
    borderRadius: Theme.radii.pill,
    height: 8,
  },
  scoreTrack: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderRadius: Theme.radii.pill,
    height: 8,
    overflow: 'hidden',
  },
  sectionHeaderRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  sectionTitle: {
    color: Theme.colors.text,
    fontSize: 15,
    fontWeight: '900',
  },
  sectionTitleBlock: {
    flex: 1,
    gap: Spacing.half,
    minWidth: 0,
  },
  sections: {
    gap: Spacing.three,
  },
  segmentEndpoint: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '800',
  },
  segmentLabelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: Spacing.half,
  },
  segmentMidpoint: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '900',
  },
  segmentRow: {
    flexDirection: 'row',
    gap: 3,
  },
  signalCard: {
    gap: Spacing.one,
    paddingVertical: Spacing.one,
  },
  signalCardDivider: {
    borderTopColor: Theme.colors.border,
    borderTopWidth: 1,
    paddingTop: Spacing.two,
  },
  signalHorizon: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '800',
  },
  signalLabel: {
    fontSize: 13,
    fontWeight: '900',
    textAlign: 'right',
  },
  signalMarker: {
    alignSelf: 'center',
    backgroundColor: Theme.colors.text,
    borderRadius: Theme.radii.pill,
    height: 4,
    marginTop: 5,
    width: 4,
  },
  signalMetaRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
  },
  signalRows: {
    gap: Spacing.one,
  },
  signalScore: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '800',
    textAlign: 'right',
  },
  signalSegment: {
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    flex: 1,
    height: 11,
  },
  signalSegmentActive: {
    borderColor: Theme.colors.text,
    borderWidth: 2,
  },
  signalSegmentUnavailable: {
    opacity: 0.42,
  },
  signalStatusBlock: {
    alignItems: 'flex-end',
    gap: 2,
  },
  signalStatusText: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '800',
  },
  signalTitle: {
    color: Theme.colors.text,
    fontSize: 14,
    fontWeight: '900',
  },
  signalTitleBlock: {
    flex: 1,
    gap: Spacing.half,
    minWidth: 0,
  },
  signalTopRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  timeframeInfoText: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
    lineHeight: 17,
  },
  timeframeTitleRow: {
    alignItems: 'center',
    flex: 1,
    flexDirection: 'row',
    gap: Spacing.one,
    minWidth: 0,
  },
  smallDisclosure: {
    alignItems: 'center',
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
    minHeight: 40,
    paddingHorizontal: Spacing.two,
  },
  smallDisclosureText: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '900',
  },
  subsectionTitle: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  subsectionDivider: {
    backgroundColor: Theme.colors.border,
    height: 1,
    marginVertical: Spacing.half,
  },
  summaryHeadline: {
    color: Theme.colors.text,
    fontSize: 18,
    fontWeight: '900',
    lineHeight: 23,
  },
  summarySubtitle: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '900',
  },
  surface: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.two,
    padding: Spacing.twoAndHalf,
  },
  volumeHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  volumeMeter: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderRadius: Theme.radii.pill,
    height: 8,
    overflow: 'hidden',
  },
  volumeMeterFill: {
    borderRadius: Theme.radii.pill,
    height: 8,
  },
  volumeQuality: {
    fontSize: 16,
    fontWeight: '900',
  },
  volumeRelative: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '900',
  },
  warningBox: {
    backgroundColor: stockToneSoftColor('warning'),
    borderRadius: Theme.radii.small,
    padding: Spacing.two,
  },
  warningText: {
    color: stockToneColor('warning'),
    fontSize: 12,
    fontWeight: '800',
    lineHeight: 17,
  },
});
